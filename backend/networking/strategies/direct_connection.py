import socket
import os
import json
import time
import threading
from multiprocessing import Process, Manager, cpu_count
from utils.logging import log, LogType
from backend.cryptography.data.sender.chunk_manager import yield_chunks
from backend.cryptography.data.receiver.chunk_manager import collect_chunks_parallel, join_chunks
from backend.cryptography.data.sender.compression import compress_file
from backend.cryptography.data.receiver.compression import decompress_final_chunk
from backend.cryptography.data.sender.metadata import retrieve_metadata as retrieve_sender_metadata
from backend.cryptography.core.cipher import encryption, decryption

class DirectConnection:

    def __init__(self, self_info, peer_info, self_private_key, peer_public_key, log_path):
        """
        Initializes the file transfer session.

        Args:
            self_info (dict): Network metadata for the local peer.
            peer_info (dict): Network metadata for the remote peer, received out-of-band.
            self_private_key: The local peer's private key for decryption.
            peer_public_key: The remote peer's public key for encryption, received out-of-band.
            log_path (str): The file path for logging.
        """
        # Self network details
        self.self_ip = self_info.get("external_ip", self_info.get("local_ip", "127.0.0.1"))
        self.self_ports = self_info.get("open_ports", [])

        # Peer network details
        self.peer_ip = peer_info.get("external_ip", peer_info.get("local_ip", "127.0.0.1"))
        self.peer_ports = peer_info.get("open_ports", [])

        # Cryptographic keys
        self.private_key = self_private_key
        self.public_key = peer_public_key

        # System and logging configuration
        self.log_path = log_path
        self.worker_count = min(cpu_count() * 2, len(self.self_ports), len(self.peer_ports))

        # Ensure we have at least one port for control channel
        if not self.self_ports or not self.peer_ports:
            raise ValueError("No ports available for communication")

        # The first port pair is the dedicated control channel for metadata
        self.control_port_self = self.self_ports[0]
        self.control_port_peer = self.peer_ports[0]

        # The rest of the ports are for high-speed data transfer
        self.data_ports_self = self.self_ports[1:] if len(self.self_ports) > 1 else []
        self.data_ports_peer = self.peer_ports[1:] if len(self.peer_ports) > 1 else []

        # Use at least the control port for data if no other ports available
        if not self.data_ports_self:
            self.data_ports_self = [self.control_port_self]
            self.data_ports_peer = [self.control_port_peer]

        # Limit worker count to available ports
        self.worker_count = min(self.worker_count, len(self.data_ports_self), len(self.data_ports_peer))

        log("DirectConnection session initialized", LogType.INFO, "Success", self.log_path)
        log(f"Control ports: self={self.control_port_self}, peer={self.control_port_peer}",
            LogType.DEBUG, "Success", self.log_path)
        log(f"Data ports: self={self.data_ports_self}, peer={self.data_ports_peer}",
            LogType.DEBUG, "Success", self.log_path)
        log(f"Worker count: {self.worker_count}", LogType.DEBUG, "Success", self.log_path)

    def _establish_connection(self, is_sender=True):
        """
        Establish initial connection handshake between sender and receiver.
        Returns True if connection is established successfully.
        """
        log("Establishing connection handshake", LogType.INFO, "Started", self.log_path)

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', self.control_port_self))
            sock.settimeout(30.0)  # 30 second timeout for handshake

            if is_sender:
                # Sender initiates handshake
                for attempt in range(5):
                    log(f"Handshake attempt {attempt + 1}/5", LogType.DEBUG, "Started", self.log_path)
                    try:
                        sock.sendto(b'PLINK_HELLO', (self.peer_ip, self.control_port_peer))

                        # Wait for response
                        response, addr = sock.recvfrom(1024)
                        if response == b'PLINK_ACK' and addr[0] == self.peer_ip:
                            # Send final confirmation
                            sock.sendto(b'PLINK_READY', (self.peer_ip, self.control_port_peer))
                            log("Connection handshake successful (sender)", LogType.INFO, "Success", self.log_path)
                            sock.close()
                            return True
                    except socket.timeout:
                        log(f"Handshake timeout on attempt {attempt + 1}", LogType.WARNING, "Retry", self.log_path)
                        time.sleep(1)
                        continue
                    except Exception as e:
                        log(f"Handshake error on attempt {attempt + 1}: {e}", LogType.WARNING, "Retry", self.log_path)
                        time.sleep(1)
                        continue
            else:
                # Receiver waits for handshake
                try:
                    log("Waiting for sender handshake", LogType.INFO, "Started", self.log_path)
                    data, addr = sock.recvfrom(1024)

                    if data == b'PLINK_HELLO' and addr[0] == self.peer_ip:
                        # Send acknowledgment
                        sock.sendto(b'PLINK_ACK', (self.peer_ip, self.control_port_peer))

                        # Wait for final confirmation
                        sock.settimeout(10.0)
                        confirm, addr = sock.recvfrom(1024)
                        if confirm == b'PLINK_READY' and addr[0] == self.peer_ip:
                            log("Connection handshake successful (receiver)", LogType.INFO, "Success", self.log_path)
                            sock.close()
                            return True
                except socket.timeout:
                    log("Handshake timeout while waiting for sender", LogType.ERROR, "Failure", self.log_path)
                except Exception as e:
                    log(f"Handshake error: {e}", LogType.ERROR, "Failure", self.log_path)

            sock.close()
            return False

        except Exception as e:
            log(f"Connection establishment failed: {e}", LogType.ERROR, "Failure", self.log_path)
            return False

    def send(self, filepath, chunk_size=8192):
        """
        Coordinates the entire file sending process.

        1. Establishes connection with receiver
        2. Compresses the file.
        3. Generates and encrypts the file metadata.
        4. Sends metadata over the control channel and waits for acknowledgment.
        5. Upon acknowledgment, starts the parallel transfer of file data.
        """
        log("Starting file send process", LogType.INFO, "Started", self.log_path)

        # Stage 0: Establish connection
        if not self._establish_connection(is_sender=True):
            log("Failed to establish connection with receiver", LogType.CRITICAL, "Failure", self.log_path)
            return False

        # Stage 1: File Preparation & Metadata Exchange
        if not os.path.isfile(filepath):
            log(f"File not found: {filepath}", LogType.CRITICAL, "Failure", self.log_path)
            return False

        temp_dir = f"temp_sender_{os.getpid()}"
        try:
            os.makedirs(temp_dir, exist_ok=True)
            compressed_path = compress_file(filepath, temp_dir, self.log_path)
            log(f"File compressed to {compressed_path}", LogType.INFO, "Success", self.log_path)

            metadata = retrieve_sender_metadata(
                file_path=str(compressed_path),
                chunk_size=chunk_size,
                public_ip=self.self_ip,
                ports=self.self_ports,
                general_logfile_path=self.log_path
            )
            encrypted_metadata = encryption(metadata, self.public_key, self.log_path)

        except Exception as e:
            log(f"File preparation failed: {e}", LogType.CRITICAL, "Failure", self.log_path)
            return False

        # Stage 2: Control Channel Communication
        success = False
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', self.control_port_self))
            sock.settimeout(60.0)

            log("Sending file metadata to receiver", LogType.INFO, "Started", self.log_path)

            # Send metadata with retries
            metadata_packet = b"[META_START]" + encrypted_metadata.encode() + b"[META_END]"

            for attempt in range(3):
                try:
                    sock.sendto(metadata_packet, (self.peer_ip, self.control_port_peer))

                    # Wait for acknowledgment
                    ack, addr = sock.recvfrom(1024)
                    if ack == b'META_OK' and addr[0] == self.peer_ip:
                        log("Receiver confirmed metadata. Starting data transfer", LogType.INFO, "Success", self.log_path)
                        success = True
                        break
                    else:
                        log(f"Invalid acknowledgment received: {ack}", LogType.WARNING, "Retry", self.log_path)

                except socket.timeout:
                    log(f"Metadata send timeout on attempt {attempt + 1}", LogType.WARNING, "Retry", self.log_path)
                    if attempt < 2:
                        time.sleep(2)
                        continue
                    else:
                        raise

            sock.close()

            if not success:
                raise ConnectionAbortedError("Failed to get valid acknowledgment from receiver")

        except Exception as e:
            log(f"Metadata exchange failed: {e}", LogType.CRITICAL, "Failure", self.log_path)
            return False

        # Stage 3: Parallel Data Transfer
        try:
            all_chunks = list(yield_chunks(compressed_path, chunk_size, self.log_path))
            log(f"Generated {len(all_chunks)} chunks for transfer", LogType.INFO, "Success", self.log_path)

            # Small delay to ensure receiver is ready
            time.sleep(2)

            # Distribute chunks among worker processes
            processes = []
            for i in range(self.worker_count):
                worker_chunks = all_chunks[i::self.worker_count]
                if worker_chunks:  # Only start process if it has chunks to send
                    p = Process(target=self._send_worker, args=(worker_chunks, i))
                    processes.append(p)
                    p.start()

            # Wait for all processes to complete
            for p in processes:
                p.join()

            log("File data sent successfully", LogType.INFO, "Success", self.log_path)
            success = True

        except Exception as e:
            log(f"Data transfer failed: {e}", LogType.CRITICAL, "Failure", self.log_path)
            success = False

        # Cleanup
        try:
            if os.path.exists(compressed_path):
                os.remove(compressed_path)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        except OSError as e:
            log(f"Cleanup warning: {e}", LogType.WARNING, "Warning", self.log_path)

        return success

    def _send_worker(self, chunks, worker_id):
        """A worker process that sends an assigned list of chunks over the data ports."""
        sockets = []
        try:
            log(f"Send worker {worker_id} starting with {len(chunks)} chunks", LogType.DEBUG, "Started", self.log_path)

            # Create sockets for this worker
            port_pairs = list(zip(self.data_ports_self, self.data_ports_peer))
            worker_port_pairs = port_pairs[worker_id::self.worker_count] if len(port_pairs) > self.worker_count else port_pairs

            for self_port, peer_port in worker_port_pairs:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    sock.bind(('', self_port))
                    sock.settimeout(5.0)
                    sockets.append((sock, peer_port))
                except Exception as e:
                    log(f"Worker {worker_id}: Failed to bind to port {self_port}: {e}", LogType.WARNING, "Warning", self.log_path)

            if not sockets:
                log(f"Worker {worker_id}: No sockets available", LogType.ERROR, "Failure", self.log_path)
                return

            # Send chunks using round-robin across sockets
            for i, (chunk_num, chunk_data) in enumerate(chunks):
                sock, peer_port = sockets[i % len(sockets)]
                header = f"[{chunk_num}]".encode()
                packet = header + chunk_data

                try:
                    sock.sendto(packet, (self.peer_ip, peer_port))
                except Exception as e:
                    log(f"Worker {worker_id}: Failed to send chunk {chunk_num}: {e}", LogType.WARNING, "Warning", self.log_path)

            log(f"Send worker {worker_id} completed", LogType.DEBUG, "Success", self.log_path)

        except Exception as e:
            log(f"Send worker {worker_id} error: {e}", LogType.ERROR, "Failure", self.log_path)
        finally:
            for sock, _ in sockets:
                try:
                    sock.close()
                except:
                    pass

    def recv(self, output_path="received_file", chunk_size=8192):
        """
        Coordinates the entire file receiving process.

        1. Establishes connection with sender
        2. Listens on the control channel for file metadata.
        3. Decrypts metadata; if successful, sends an acknowledgment.
        4. Listens on all data ports in parallel for the file chunks.
        5. Reassembles and decompresses the file.
        """
        log("Starting file receive process", LogType.INFO, "Started", self.log_path)

        # Stage 0: Establish connection
        if not self._establish_connection(is_sender=False):
            log("Failed to establish connection with sender", LogType.CRITICAL, "Failure", self.log_path)
            return False

        # Stage 1: Control Channel Communication
        metadata = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', self.control_port_self))
            sock.settimeout(120.0)  # 2 minute timeout for metadata

            log("Ready to receive. Listening for incoming metadata", LogType.INFO, "Started", self.log_path)

            data, peer_addr = sock.recvfrom(4096)

            if not data.startswith(b"[META_START]") or peer_addr[0] != self.peer_ip:
                raise ValueError(f"Received invalid metadata format from {peer_addr[0]}")

            metadata_raw = data.split(b"[META_START]")[1].split(b"[META_END]")[0]
            metadata = decryption(metadata_raw.decode(), self.private_key, self.log_path)
            log(f"Metadata decrypted successfully: file={metadata.get('file_name')}, chunks={metadata.get('total_chunks')}",
                LogType.INFO, "Success", self.log_path)

            # Acknowledge successful decryption to start the transfer
            sock.sendto(b'META_OK', (self.peer_ip, self.control_port_peer))
            sock.close()

        except Exception as e:
            log(f"Failed to receive or decrypt metadata: {e}", LogType.CRITICAL, "Failure", self.log_path)
            return False

        # Stage 2: Parallel Data Reception
        temp_dir = f"temp_receiver_{os.getpid()}"
        success = False

        try:
            os.makedirs(temp_dir, exist_ok=True)

            with Manager() as manager:
                received_chunks = manager.list()
                total_chunks = metadata.get("total_chunks", 0)

                log(f"Starting {self.worker_count} receiver workers for {total_chunks} chunks",
                    LogType.INFO, "Started", self.log_path)

                # Small delay to ensure sender is ready
                time.sleep(1)

                processes = []
                for i in range(self.worker_count):
                    p = Process(target=self._recv_worker, args=(received_chunks, total_chunks, i))
                    processes.append(p)
                    p.start()

                # Wait for all processes with timeout
                start_time = time.time()
                for p in processes:
                    remaining_time = max(0, 300 - (time.time() - start_time))  # 5 minute total timeout
                    p.join(timeout=remaining_time)
                    if p.is_alive():
                        log(f"Terminating stuck receiver process", LogType.WARNING, "Warning", self.log_path)
                        p.terminate()
                        p.join(timeout=5)

                # Stage 3: Reassembly and Cleanup
                received_count = len(received_chunks)
                log(f"Received {received_count} of {total_chunks} chunks", LogType.INFO, "Success", self.log_path)

                if received_count != total_chunks:
                    log(f"Incomplete transfer: Got {received_count} of {total_chunks} chunks",
                        LogType.ERROR, "Failure", self.log_path)
                else:
                    log("All chunks received. Reassembling file", LogType.INFO, "Success", self.log_path)

                    chunk_logfile = os.path.join(temp_dir, "chunks.json")
                    collect_chunks_parallel(list(received_chunks), chunk_logfile, self.log_path, temp_dir)
                    joined_path = join_chunks(temp_dir, chunk_logfile, self.log_path, chunk_size=chunk_size)
                    decompress_final_chunk(joined_path, output_path, self.log_path)
                    log(f"File successfully saved to {output_path}", LogType.INFO, "Success", self.log_path)
                    success = True

        except Exception as e:
            log(f"Data reception failed: {e}", LogType.CRITICAL, "Failure", self.log_path)
            success = False

        # Cleanup
        try:
            chunk_logfile = os.path.join(temp_dir, "chunks.json")
            if os.path.exists(chunk_logfile):
                os.remove(chunk_logfile)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        except OSError as e:
            log(f"Cleanup warning: {e}", LogType.WARNING, "Warning", self.log_path)

        return success

    def _recv_worker(self, received_chunks, total_chunks, worker_id):
        """A worker process that listens on assigned ports and collects chunks."""
        sockets = []
        chunks_received = 0

        try:
            log(f"Recv worker {worker_id} starting", LogType.DEBUG, "Started", self.log_path)

            # Create sockets for this worker
            port_pairs = list(zip(self.data_ports_self, self.data_ports_peer))
            worker_port_pairs = port_pairs[worker_id::self.worker_count] if len(port_pairs) > self.worker_count else port_pairs

            for self_port, peer_port in worker_port_pairs:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    sock.bind(('', self_port))
                    sock.settimeout(45.0)  # 45 second timeout per socket
                    sockets.append(sock)
                except Exception as e:
                    log(f"Worker {worker_id}: Failed to bind to port {self_port}: {e}", LogType.WARNING, "Warning", self.log_path)

            if not sockets:
                log(f"Worker {worker_id}: No sockets available", LogType.ERROR, "Failure", self.log_path)
                return

            # Receive chunks
            start_time = time.time()
            consecutive_timeouts = 0
            max_consecutive_timeouts = 10

            while len(received_chunks) < total_chunks and consecutive_timeouts < max_consecutive_timeouts:
                received_this_round = False

                for sock in sockets:
                    try:
                        data, addr = sock.recvfrom(8192 + 100)

                        # Verify sender IP
                        if addr[0] != self.peer_ip:
                            continue

                        header_end = data.find(b"]")
                        if header_end == -1:
                            continue

                        chunk_num = int(data[1:header_end])
                        chunk_data = data[header_end + 1:]
                        received_chunks.append((chunk_data, chunk_num))
                        chunks_received += 1
                        received_this_round = True
                        consecutive_timeouts = 0  # Reset timeout counter

                    except socket.timeout:
                        continue
                    except (ValueError, IndexError):
                        continue
                    except Exception as e:
                        log(f"Worker {worker_id}: Receive error: {e}", LogType.WARNING, "Warning", self.log_path)
                        continue

                if not received_this_round:
                    consecutive_timeouts += 1

                # Check if we should continue waiting
                if time.time() - start_time > 300:  # 5 minute total timeout
                    log(f"Worker {worker_id}: Total timeout reached", LogType.WARNING, "Warning", self.log_path)
                    break

            log(f"Recv worker {worker_id} completed, received {chunks_received} chunks",
                LogType.DEBUG, "Success", self.log_path)

        except Exception as e:
            log(f"Recv worker {worker_id} error: {e}", LogType.ERROR, "Failure", self.log_path)
        finally:
            for sock in sockets:
                try:
                    sock.close()
                except:
                    pass
