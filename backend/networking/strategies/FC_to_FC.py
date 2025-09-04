import socket
import os
import json
from multiprocessing import Process, Manager, cpu_count
from utils.logging import log, LogType
from backend.cryptography.data.sender.chunk_manager import yield_chunks
from backend.cryptography.data.receiver.chunk_manager import collect_chunks_parallel, join_chunks
from backend.cryptography.data.sender.compression import compress_file
from backend.cryptography.data.receiver.compression import decompress_final_chunk
from backend.cryptography.data.sender.metadata import retrieve_metadata as retrieve_sender_metadata
from backend.cryptography.core.cipher import encryption, decryption

class FullConeToFullConeNAT:

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
        self.worker_count = min(cpu_count() * 2, len(self.self_ports))

        # The first port pair is the dedicated control channel for metadata
        self.control_port_self = self.self_ports[0]
        self.control_port_peer = self.peer_ports[0]

        # The rest of the ports are for high-speed data transfer
        self.data_ports_self = self.self_ports[1:]
        self.data_ports_peer = self.peer_ports[1:]

        log("Session initialized. Control channel established.", general_logfile_path=self.log_path)

    def _punch_hole(self, ports_self, ports_peer):
        """Punches holes for a given list of port pairs."""
        for i in range(len(ports_self)):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    sock.bind(('', ports_self[i]))
                    sock.sendto(b'o', (self.peer_ip, ports_peer[i]))
            except Exception as e:
                log(f"Hole punch failed for port {ports_self[i]}: {e}", LogType.WARNING, "Failure", self.log_path)
        log(f"Hole punching complete for {len(ports_self)} data ports.", general_logfile_path=self.log_path)

    # --------------------------------------------------- #
    #                     SENDING LOGIC                   #
    # --------------------------------------------------- #
    def send(self, filepath, chunk_size=8192):
        """
        Coordinates the entire file sending process.

        1. Compresses the file.
        2. Generates and encrypts the file metadata.
        3. Sends metadata over the control channel and waits for acknowledgment.
        4. Upon acknowledgment, starts the parallel transfer of file data.
        """
        # --- Stage 1: File Preparation & Metadata Exchange ---
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

        # --- Stage 2: Control Channel Communication ---
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.bind(('', self.control_port_self))
                log("Sending file metadata. Awaiting confirmation from receiver...", general_logfile_path=self.log_path)
                sock.sendto(b"[META_START]" + json.dumps(encrypted_metadata).encode() + b"[META_END]", (self.peer_ip, self.control_port_peer))

                sock.settimeout(60.0) # Wait up to 60 seconds for the receiver's 'OK'
                ack, _ = sock.recvfrom(1024)
                if ack != b'META_OK':
                    raise ConnectionAbortedError("Receiver sent an invalid acknowledgment.")
                log("Receiver confirmed metadata. Starting data transfer.", status="Success", general_logfile_path=self.log_path)
        except Exception as e:
            log(f"Metadata exchange failed: {e}", LogType.CRITICAL, "Failure", self.log_path)
            return

        # --- Stage 3: Parallel Data Transfer ---
        self._punch_hole(self.data_ports_self, self.data_ports_peer)

        all_chunks = list(yield_chunks(compressed_path, chunk_size, self.log_path))

        # Distribute chunks among worker processes
        processes = []
        for i in range(self.worker_count):
            worker_chunks = all_chunks[i::self.worker_count]
            p = Process(target=self._send_worker, args=(worker_chunks,))
            processes.append(p)
            p.start()

        for p in processes:
            p.join()

        log("File data sent successfully.", status="Success", general_logfile_path=self.log_path)
        os.remove(compressed_path)
        os.rmdir(temp_dir)

    def _send_worker(self, chunks):
        """A worker process that sends an assigned list of chunks over the data ports."""
        with Manager() as manager:
            sockets = [socket.socket(socket.AF_INET, socket.SOCK_DGRAM) for _ in self.data_ports_self]
            for i, sock in enumerate(sockets):
                sock.bind(('', self.data_ports_self[i]))

            for i, (chunk_num, chunk_data) in enumerate(chunks):
                header = f"[{chunk_num}]".encode()
                sock_index = i % len(sockets) # Round-robin socket usage
                sockets[sock_index].sendto(header + chunk_data, (self.peer_ip, self.data_ports_peer[sock_index]))

            for sock in sockets:
                sock.close()

    # --------------------------------------------------- #
    #                    RECEIVING LOGIC                  #
    # --------------------------------------------------- #
    def _recv_worker(self, received_chunks, total_chunks):
        """A worker process that listens on assigned ports and collects chunks."""
        sockets = [socket.socket(socket.AF_INET, socket.SOCK_DGRAM) for _ in self.data_ports_self]
        for i, sock in enumerate(sockets):
            sock.bind(('', self.data_ports_self[i]))
            sock.settimeout(45)

        while len(received_chunks) < total_chunks:
            for sock in sockets:
                try:
                    data, _ = sock.recvfrom(8192 + 100)
                    header_end = data.find(b"]")
                    chunk_num = int(data[1:header_end])
                    chunk_data = data[header_end + 1:]
                    received_chunks.append((chunk_data, chunk_num))
                except socket.timeout:
                    continue
                except (ValueError, IndexError):
                    continue

        for sock in sockets:
            sock.close()
