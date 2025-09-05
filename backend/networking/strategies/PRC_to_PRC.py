import socket
import os
import json
import time
from multiprocessing import Process, Manager, cpu_count
from utils.logging import log, LogType
from backend.cryptography.data.sender.chunk_manager import yield_chunks
from backend.cryptography.data.receiver.chunk_manager import collect_chunks_parallel, join_chunks
from backend.cryptography.data.sender.compression import compress_file
from backend.cryptography.data.receiver.compression import decompress_final_chunk
from backend.cryptography.data.sender.metadata import retrieve_metadata as retrieve_sender_metadata
from backend.cryptography.core.cipher import encryption, decryption

class PortRestrictedToPortRestrictedNAT:

    def __init__(self, self_info, peer_info, self_private_key, peer_public_key, log_path, is_initiator=True):
        """
        Initializes the file transfer session for PRC to PRC NAT scenario.

        Args:
            self_info (dict): Network metadata for the local peer.
            peer_info (dict): Network metadata for the remote peer, received out-of-band.
            self_private_key: The local peer's private key for decryption.
            peer_public_key: The remote peer's public key for encryption, received out-of-band.
            log_path (str): The file path for logging.
            is_initiator (bool): Whether this peer initiates the connection (important for PRC synchronization).
        """
        # Self network details
        self.self_ip = self_info["external_ip"]
        self.self_ports = self_info["open_ports"]

        # Peer network details
        self.peer_ip = peer_info["external_ip"]
        self.peer_ports = peer_info["open_ports"]

        # Cryptographic keys
        self.private_key = self_private_key
        self.public_key = peer_public_key

        # System and logging configuration
        self.log_path = log_path
        self.is_initiator = is_initiator
        self.worker_count = min(cpu_count() * 2, len(self.self_ports))

        # The first port pair is the dedicated control channel for metadata
        self.control_port_self = self.self_ports[0]
        self.control_port_peer = self.peer_ports[0]

        # The rest of the ports are for high-speed data transfer
        self.data_ports_self = self.self_ports[1:]
        self.data_ports_peer = self.peer_ports[1:]

        # Track successful port mappings
        self.established_mappings = []

        log("PRC to PRC session initialized. Control channel established.", general_logfile_path=self.log_path)
        log(f"Peer role: {'Initiator' if is_initiator else 'Responder'}", general_logfile_path=self.log_path)

    def _synchronized_hole_punch(self, ports_self, ports_peer, rounds=7, base_delay=0.3):
        """
        Synchronized hole punching for PRC to PRC NAT traversal.
        Both sides must coordinate exactly to establish bidirectional communication.
        """
        log("Starting synchronized PRC to PRC hole punching", general_logfile_path=self.log_path)
        successful_mappings = []
        sockets = []

        try:
            # Create bound sockets for each port
            for port in ports_self:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.bind(('', port))
                sock.settimeout(0.8)
                sockets.append(sock)

            for round_num in range(rounds):
                delay = base_delay + (round_num * 0.1)  # Progressive delay
                log(f"PRC hole punching round {round_num + 1}/{rounds} (delay: {delay}s)", general_logfile_path=self.log_path)

                if self.is_initiator:
                    # Initiator sends first, then listens
                    self._send_hole_punch_packets(sockets, ports_self, ports_peer, round_num)
                    time.sleep(delay)
                    received_mappings = self._receive_hole_punch_packets(sockets, ports_self, ports_peer)
                    successful_mappings.extend(received_mappings)
                else:
                    # Responder listens first, then responds
                    time.sleep(delay / 2)  # Small offset to ensure initiator sends first
                    received_mappings = self._receive_hole_punch_packets(sockets, ports_self, ports_peer)
                    self._send_hole_punch_packets(sockets, ports_self, ports_peer, round_num)
                    successful_mappings.extend(received_mappings)

                # Additional delay between rounds
                time.sleep(delay)

            # Remove duplicates and validate mappings
            unique_mappings = list(set(successful_mappings))
            validated_mappings = self._validate_mappings(unique_mappings, sockets)

        finally:
            for sock in sockets:
                sock.close()

        self.established_mappings = validated_mappings

        if validated_mappings:
            log(f"Successfully established {len(validated_mappings)} PRC port mappings: {validated_mappings}",
                LogType.INFO, "Success", self.log_path)
        else:
            log("Failed to establish any PRC port mappings", LogType.ERROR, "Failure", self.log_path)

        return validated_mappings

    def _send_hole_punch_packets(self, sockets, ports_self, ports_peer, round_num):
        """Send hole punch packets with round-specific identifiers."""
        for i, (sock, src_port) in enumerate(zip(sockets, ports_self)):
            if i < len(ports_peer):
                dst_port = ports_peer[i]
                try:
                    message = f"PRC-PUNCH-{round_num}-{src_port}".encode()
                    sock.sendto(message, (self.peer_ip, dst_port))
                except Exception as e:
                    log(f"Send error from {src_port} to {dst_port}: {e}", LogType.WARNING, "Failure", self.log_path)

    def _receive_hole_punch_packets(self, sockets, ports_self, ports_peer):
        """Receive and validate hole punch packets."""
        received_mappings = []

        for i, (sock, src_port) in enumerate(zip(sockets, ports_self)):
            if i < len(ports_peer):
                expected_peer_port = ports_peer[i]
                try:
                    data, addr = sock.recvfrom(1024)
                    sender_ip, sender_port = addr

                    if (sender_ip == self.peer_ip and
                        sender_port == expected_peer_port and
                        data.startswith(b"PRC-PUNCH-")):

                        received_mappings.append((src_port, sender_port))
                        log(f"Valid hole punch received: {src_port} <-> {self.peer_ip}:{sender_port}",
                            LogType.INFO, "Success", self.log_path)

                        # Send acknowledgment
                        ack_message = f"PRC-ACK-{src_port}".encode()
                        sock.sendto(ack_message, (self.peer_ip, sender_port))

                except socket.timeout:
                    continue
                except Exception as e:
                    log(f"Receive error on port {src_port}: {e}", LogType.WARNING, "Failure", self.log_path)

        return received_mappings

    def _validate_mappings(self, mappings, sockets):
        """Validate that mappings are truly bidirectional."""
        validated = []

        for src_port, dst_port in mappings:
            try:
                # Find the corresponding socket
                sock = None
                for s in sockets:
                    if s.getsockname()[1] == src_port:
                        sock = s
                        break

                if sock:
                    # Send validation packet
                    validation_msg = f"PRC-VALIDATE-{src_port}".encode()
                    sock.sendto(validation_msg, (self.peer_ip, dst_port))

                    # Wait for validation response
                    sock.settimeout(2.0)
                    try:
                        data, addr = sock.recvfrom(1024)
                        if (addr[0] == self.peer_ip and
                            addr[1] == dst_port and
                            data.startswith(b"PRC-VALIDATE-ACK")):
                            validated.append((src_port, dst_port))
                    except socket.timeout:
                        continue

            except Exception as e:
                log(f"Validation error for mapping {src_port}->{dst_port}: {e}", LogType.WARNING, "Failure", self.log_path)

        return validated

    # --------------------------------------------------- #
    #                     SENDING LOGIC                   #
    # --------------------------------------------------- #
    def send(self, filepath, chunk_size=8192):
        """
        Coordinates the entire file sending process for PRC to PRC scenario.

        1. Establishes synchronized hole punching
        2. Compresses the file and generates metadata
        3. Sends metadata over the control channel and waits for acknowledgment
        4. Transfers file data using established port mappings
        """
        # --- Stage 1: Synchronized Hole Punching ---
        log("Establishing PRC to PRC port mappings...", general_logfile_path=self.log_path)
        established_mappings = self._synchronized_hole_punch(self.data_ports_self, self.data_ports_peer)

        if not established_mappings:
            log("Cannot proceed: No port mappings established", LogType.CRITICAL, "Failure", self.log_path)
            return

        # --- Stage 2: File Preparation & Metadata Exchange ---
        if not os.path.isfile(filepath):
            log(f"File not found: {filepath}", LogType.CRITICAL, "Failure", self.log_path)
            return

        temp_dir = f"temp_sender_{os.getpid()}"
        os.makedirs(temp_dir, exist_ok=True)
        compressed_path = compress_file(filepath, temp_dir, self.log_path)
        log(f"File compressed to {compressed_path}", general_logfile_path=self.log_path)

        metadata = retrieve_sender_metadata(
            file_path=str(compressed_path),
            chunk_size=chunk_size,
            public_ip=self.self_ip,
            ports=self.self_ports,
            general_logfile_path=self.log_path
        )
        encrypted_metadata = encryption(metadata, self.public_key, self.log_path)

        # --- Stage 3: Control Channel Communication ---
        if not self._establish_control_channel():
            log("Failed to establish control channel", LogType.CRITICAL, "Failure", self.log_path)
            return

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.bind(('', self.control_port_self))
                log("Sending file metadata to PRC peer...", general_logfile_path=self.log_path)

                metadata_packet = b"[META_START]" + json.dumps(encrypted_metadata).encode() + b"[META_END]"
                sock.sendto(metadata_packet, (self.peer_ip, self.control_port_peer))

                sock.settimeout(90.0)  # Extended timeout for PRC
                ack, addr = sock.recvfrom(1024)

                if ack != b'META_OK' or addr[0] != self.peer_ip:
                    raise ConnectionAbortedError("Invalid acknowledgment from PRC peer.")

                log("PRC peer confirmed metadata. Starting data transfer.", status="Success", general_logfile_path=self.log_path)

        except Exception as e:
            log(f"Metadata exchange failed: {e}", LogType.CRITICAL, "Failure", self.log_path)
            return

        # --- Stage 4: Parallel Data Transfer ---
        all_chunks = list(yield_chunks(compressed_path, chunk_size, self.log_path))

        # Use only established port mappings for data transfer
        active_mappings = established_mappings[:self.worker_count]  # Limit to worker count

        processes = []
        for i in range(len(active_mappings)):
            worker_chunks = all_chunks[i::len(active_mappings)]
            worker_mapping = active_mappings[i]
            p = Process(target=self._send_worker_prc, args=(worker_chunks, worker_mapping))
            processes.append(p)
            p.start()

        for p in processes:
            p.join()

        log("File data sent successfully via PRC mappings.", status="Success", general_logfile_path=self.log_path)

        # Cleanup
        os.remove(compressed_path)
        os.rmdir(temp_dir)

    def _establish_control_channel(self):
        """Establish control channel for PRC to PRC communication."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.bind(('', self.control_port_self))
                sock.settimeout(5.0)

                if self.is_initiator:
                    # Initiator establishes control channel first
                    for attempt in range(5):
                        sock.sendto(b'CONTROL_INIT', (self.peer_ip, self.control_port_peer))
                        try:
                            response, addr = sock.recvfrom(1024)
                            if response == b'CONTROL_ACK' and addr[0] == self.peer_ip:
                                log("Control channel established (initiator)", general_logfile_path=self.log_path)
                                return True
                        except socket.timeout:
                            continue
                else:
                    # Responder waits for control channel init
                    try:
                        data, addr = sock.recvfrom(1024)
                        if data == b'CONTROL_INIT' and addr[0] == self.peer_ip:
                            sock.sendto(b'CONTROL_ACK', (self.peer_ip, self.control_port_peer))
                            log("Control channel established (responder)", general_logfile_path=self.log_path)
                            return True
                    except socket.timeout:
                        pass

        except Exception as e:
            log(f"Control channel establishment error: {e}", LogType.ERROR, "Failure", self.log_path)

        return False

    def _send_worker_prc(self, chunks, port_mapping):
        """Worker process for sending chunks using established PRC port mapping."""
        src_port, dst_port = port_mapping
        sock = None

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(('', src_port))

            for chunk_num, chunk_data in chunks:
                header = f"[{chunk_num}]".encode()
                packet = header + chunk_data
                sock.sendto(packet, (self.peer_ip, dst_port))

        except Exception as e:
            log(f"Send worker error on mapping {port_mapping}: {e}", LogType.ERROR, "Failure", self.log_path)
        finally:
            if sock:
                sock.close()

    # --------------------------------------------------- #
    #                    RECEIVING LOGIC                  #
    # --------------------------------------------------- #
    def recv(self, output_path="received_file", chunk_size=8192):
        """
        Coordinates the entire file receiving process for PRC to PRC scenario.

        1. Establishes synchronized hole punching
        2. Listens on the control channel for file metadata
        3. Decrypts metadata and sends acknowledgment
        4. Receives file data using established port mappings
        5. Reassembles and decompresses the file
        """
        # --- Stage 1: Synchronized Hole Punching ---
        log("Establishing PRC to PRC port mappings (receiver)...", general_logfile_path=self.log_path)
        established_mappings = self._synchronized_hole_punch(self.data_ports_self, self.data_ports_peer)

        if not established_mappings:
            log("Cannot proceed: No port mappings established", LogType.CRITICAL, "Failure", self.log_path)
            return

        # --- Stage 2: Control Channel Communication ---
        if not self._establish_control_channel():
            log("Failed to establish control channel", LogType.CRITICAL, "Failure", self.log_path)
            return

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.bind(('', self.control_port_self))
                sock.settimeout(300.0)  # Extended timeout for PRC

                log("Ready to receive from PRC peer. Listening for metadata...", general_logfile_path=self.log_path)
                data, peer_addr = sock.recvfrom(4096)

                if not data.startswith(b"[META_START]") or peer_addr[0] != self.peer_ip:
                    raise ValueError("Invalid metadata format or sender.")

                metadata_raw = data.split(b"[META_START]")[1].split(b"[META_END]")[0]
                metadata = decryption(json.loads(metadata_raw.decode()), self.private_key, self.log_path)
                log(f"Metadata decrypted successfully: {metadata}", general_logfile_path=self.log_path)

                # Acknowledge successful decryption
                sock.sendto(b'META_OK', (self.peer_ip, self.control_port_peer))

        except Exception as e:
            log(f"Failed to receive or decrypt metadata: {e}", LogType.CRITICAL, "Failure", self.log_path)
            return

        # --- Stage 3: Parallel Data Reception ---
        temp_dir = f"temp_receiver_{os.getpid()}"
        os.makedirs(temp_dir, exist_ok=True)

        with Manager() as manager:
            received_chunks = manager.list()
            total_chunks = metadata.get("total_chunks")

            # Use established mappings for receiving
            active_mappings = established_mappings[:self.worker_count]

            processes = []
            for mapping in active_mappings:
                p = Process(target=self._recv_worker_prc, args=(received_chunks, total_chunks, mapping))
                processes.append(p)
                p.start()

            for p in processes:
                p.join()

            # --- Stage 4: Reassembly and Cleanup ---
            if len(received_chunks) != total_chunks:
                log(f"Incomplete transfer: Got {len(received_chunks)} of {total_chunks} chunks.", LogType.ERROR, "Failure", self.log_path)
            else:
                log("All chunks received from PRC peer. Reassembling file.", status="Success", general_logfile_path=self.log_path)

            chunk_logfile = os.path.join(temp_dir, "chunks.json")
            collect_chunks_parallel(list(received_chunks), chunk_logfile, self.log_path, temp_dir)
            joined_path = join_chunks(temp_dir, chunk_logfile, self.log_path, chunk_size=chunk_size)
            decompress_final_chunk(joined_path, output_path, self.log_path)
            log(f"File successfully saved to {output_path}", status="Success", general_logfile_path=self.log_path)

        # Cleanup
        os.remove(chunk_logfile)
        os.rmdir(temp_dir)

    def _recv_worker_prc(self, received_chunks, total_chunks, port_mapping):
        """Worker process for receiving chunks using established PRC port mapping."""
        src_port, expected_peer_port = port_mapping
        sock = None

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(('', src_port))
            sock.settimeout(60)  # Extended timeout for PRC

            while len(received_chunks) < total_chunks:
                try:
                    data, addr = sock.recvfrom(8192 + 100)

                    # Verify sender matches expected mapping
                    if addr[0] != self.peer_ip or addr[1] != expected_peer_port:
                        continue

                    header_end = data.find(b"]")
                    if header_end == -1:
                        continue

                    chunk_num = int(data[1:header_end])
                    chunk_data = data[header_end + 1:]
                    received_chunks.append((chunk_data, chunk_num))

                except socket.timeout:
                    continue
                except (ValueError, IndexError):
                    continue

        except Exception as e:
            log(f"Recv worker error on mapping {port_mapping}: {e}", LogType.ERROR, "Failure", self.log_path)
        finally:
            if sock:
                sock.close()
