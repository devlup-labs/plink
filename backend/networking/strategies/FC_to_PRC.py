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

class FullConeToPortRestrictedConeNAT:

    def __init__(self, self_info, peer_info, self_private_key, peer_public_key, log_path):
        """
        Initializes the file transfer session for Full Cone to Port Restricted Cone NAT scenario.

        Args:
            self_info (dict): Network metadata for the local peer (Full Cone).
            peer_info (dict): Network metadata for the remote peer (Port Restricted Cone), received out-of-band.
            self_private_key: The local peer's private key for decryption.
            peer_public_key: The remote peer's public key for encryption, received out-of-band.
            log_path (str): The file path for logging.
        """
        # Self network details (Full Cone NAT)
        self.self_ip = self_info["external_ip"]
        self.self_ports = self_info["open_ports"]

        # Peer network details (Port Restricted Cone NAT)
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

        log("FC to PRC session initialized. Control channel established.", general_logfile_path=self.log_path)

    def _punch_hole_prc(self, ports_self, ports_peer):
        """
        Punches holes for Port Restricted Cone NAT.
        For PRC, we need to establish bidirectional communication by sending initial packets
        and waiting for responses to establish the port mapping.
        """
        established_ports = []

        for i in range(len(ports_self)):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    sock.bind(('', ports_self[i]))
                    sock.settimeout(5.0)

                    # Send initial packet to establish mapping
                    sock.sendto(b'HOLE_PUNCH_INIT', (self.peer_ip, ports_peer[i]))
                    log(f"Sent hole punch init to {self.peer_ip}:{ports_peer[i]} from port {ports_self[i]}", general_logfile_path=self.log_path)

                    try:
                        # Wait for response to confirm bidirectional communication
                        response, addr = sock.recvfrom(1024)
                        if response == b'HOLE_PUNCH_ACK' and addr[0] == self.peer_ip and addr[1] == ports_peer[i]:
                            established_ports.append(i)
                            log(f"Port {ports_self[i]} successfully established with PRC peer", general_logfile_path=self.log_path)
                        else:
                            log(f"Invalid hole punch response from port {ports_self[i]}", LogType.WARNING, "Failure", self.log_path)
                    except socket.timeout:
                        log(f"Timeout waiting for hole punch response on port {ports_self[i]}", LogType.WARNING, "Failure", self.log_path)

            except Exception as e:
                log(f"Hole punch failed for port {ports_self[i]}: {e}", LogType.WARNING, "Failure", self.log_path)

        log(f"Hole punching complete. {len(established_ports)}/{len(ports_self)} ports established.", general_logfile_path=self.log_path)
        return established_ports

    def _listen_for_hole_punch(self, ports_self, ports_peer):
        """
        Listens for incoming hole punch requests and responds appropriately.
        This is used when acting as the PRC peer.
        """
        processes = []
        for i in range(len(ports_self)):
            p = Process(target=self._hole_punch_listener, args=(ports_self[i], ports_peer[i]))
            processes.append(p)
            p.start()

        # Wait a reasonable time for hole punching to complete
        time.sleep(10)

        for p in processes:
            if p.is_alive():
                p.terminate()
            p.join()

    def _hole_punch_listener(self, local_port, peer_port):
        """Worker process to handle hole punch requests on a specific port."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.bind(('', local_port))
                sock.settimeout(15.0)

                while True:
                    try:
                        data, addr = sock.recvfrom(1024)
                        if data == b'HOLE_PUNCH_INIT' and addr[0] == self.peer_ip:
                            # Respond to establish bidirectional communication
                            sock.sendto(b'HOLE_PUNCH_ACK', (self.peer_ip, peer_port))
                            log(f"Responded to hole punch on port {local_port}", general_logfile_path=self.log_path)
                            break
                    except socket.timeout:
                        break
        except Exception as e:
            log(f"Hole punch listener error on port {local_port}: {e}", LogType.WARNING, "Failure", self.log_path)

    # --------------------------------------------------- #
    #                     SENDING LOGIC                   #
    # --------------------------------------------------- #
    def send(self, filepath, chunk_size=8192):
        """
        Coordinates the entire file sending process for FC to PRC scenario.

        1. Compresses the file.
        2. Generates and encrypts the file metadata.
        3. Establishes port mappings with PRC peer.
        4. Sends metadata over the control channel and waits for acknowledgment.
        5. Upon acknowledgment, starts the parallel transfer of file data.
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

        # --- Stage 2: Port Mapping Establishment ---
        log("Establishing port mappings with Port Restricted Cone NAT peer...", general_logfile_path=self.log_path)
        established_data_ports = self._punch_hole_prc(self.data_ports_self, self.data_ports_peer)

        if not established_data_ports:
            log("Failed to establish any data port mappings with PRC peer", LogType.CRITICAL, "Failure", self.log_path)
            return

        # --- Stage 3: Control Channel Communication ---
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.bind(('', self.control_port_self))

                # First establish control channel mapping
                sock.sendto(b'CONTROL_INIT', (self.peer_ip, self.control_port_peer))
                sock.settimeout(10.0)

                try:
                    ack, _ = sock.recvfrom(1024)
                    if ack != b'CONTROL_ACK':
                        raise ConnectionAbortedError("Failed to establish control channel with PRC peer.")
                except socket.timeout:
                    raise ConnectionAbortedError("Timeout establishing control channel with PRC peer.")

                log("Sending file metadata. Awaiting confirmation from PRC receiver...", general_logfile_path=self.log_path)
                sock.sendto(b"[META_START]" + json.dumps(encrypted_metadata).encode() + b"[META_END]", (self.peer_ip, self.control_port_peer))

                sock.settimeout(60.0) # Wait up to 60 seconds for the receiver's 'OK'
                ack, _ = sock.recvfrom(1024)
                if ack != b'META_OK':
                    raise ConnectionAbortedError("PRC receiver sent an invalid acknowledgment.")
                log("PRC receiver confirmed metadata. Starting data transfer.", status="Success", general_logfile_path=self.log_path)
        except Exception as e:
            log(f"Metadata exchange failed with PRC peer: {e}", LogType.CRITICAL, "Failure", self.log_path)
            return

        # --- Stage 4: Parallel Data Transfer ---
        all_chunks = list(yield_chunks(compressed_path, chunk_size, self.log_path))

        # Only use established ports for data transfer
        active_data_ports_self = [self.data_ports_self[i] for i in established_data_ports]
        active_data_ports_peer = [self.data_ports_peer[i] for i in established_data_ports]

        worker_count = min(self.worker_count, len(active_data_ports_self))

        # Distribute chunks among worker processes
        processes = []
        for i in range(worker_count):
            worker_chunks = all_chunks[i::worker_count]
            worker_ports_self = [active_data_ports_self[j] for j in range(i, len(active_data_ports_self), worker_count)]
            worker_ports_peer = [active_data_ports_peer[j] for j in range(i, len(active_data_ports_peer), worker_count)]
            p = Process(target=self._send_worker_prc, args=(worker_chunks, worker_ports_self, worker_ports_peer))
            processes.append(p)
            p.start()

        for p in processes:
            p.join()

        log("File data sent successfully to PRC peer.", status="Success", general_logfile_path=self.log_path)
        os.remove(compressed_path)
        os.rmdir(temp_dir)

    def _send_worker_prc(self, chunks, ports_self, ports_peer):
        """A worker process that sends chunks over established PRC connections."""
        sockets = []
        try:
            for i in range(len(ports_self)):
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.bind(('', ports_self[i]))
                sockets.append(sock)

            for i, (chunk_num, chunk_data) in enumerate(chunks):
                header = f"[{chunk_num}]".encode()
                sock_index = i % len(sockets)
                sockets[sock_index].sendto(header + chunk_data, (self.peer_ip, ports_peer[sock_index]))

        finally:
            for sock in sockets:
                sock.close()

    # --------------------------------------------------- #
    #                    RECEIVING LOGIC                  #
    # --------------------------------------------------- #
    def recv(self, output_path="received_file", chunk_size=8192):
        """
        Coordinates the entire file receiving process for PRC peer.

        1. Listens for hole punch requests and establishes port mappings.
        2. Listens on the control channel for file metadata.
        3. Decrypts metadata; if successful, sends an acknowledgment.
        4. Listens on all established data ports in parallel for the file chunks.
        5. Reassembles and decompresses the file.
        """
        # --- Stage 1: Port Mapping Establishment ---
        log("Starting hole punch listeners for PRC behavior...", general_logfile_path=self.log_path)
        self._listen_for_hole_punch(self.data_ports_self, self.data_ports_peer)

        # --- Stage 2: Control Channel Communication ---
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.bind(('', self.control_port_self))
                sock.settimeout(300.0) # Wait up to 5 minutes for a transfer to start

                log("Ready to receive from FC peer. Listening for control channel init...", general_logfile_path=self.log_path)

                # Wait for control channel establishment
                while True:
                    try:
                        data, peer_addr = sock.recvfrom(1024)
                        if data == b'CONTROL_INIT' and peer_addr[0] == self.peer_ip:
                            sock.sendto(b'CONTROL_ACK', (self.peer_ip, self.control_port_peer))
                            log("Control channel established with FC peer", general_logfile_path=self.log_path)
                            break
                    except socket.timeout:
                        log("Timeout waiting for control channel init", LogType.ERROR, "Failure", self.log_path)
                        return

                # Now wait for metadata
                log("Listening for incoming metadata...", general_logfile_path=self.log_path)
                data, peer_addr = sock.recvfrom(4096)

                if not data.startswith(b"[META_START]"):
                    raise ValueError("Received invalid metadata format.")

                metadata_raw = data.split(b"[META_START]")[1].split(b"[META_END]")[0]
                metadata = decryption(json.loads(metadata_raw.decode()), self.private_key, self.log_path)
                log(f"Metadata decrypted successfully: {metadata}", general_logfile_path=self.log_path)

                # Acknowledge successful decryption to start the transfer
                sock.sendto(b'META_OK', (self.peer_ip, self.control_port_peer))
        except Exception as e:
            log(f"Failed to receive or decrypt metadata from FC peer: {e}", LogType.CRITICAL, "Failure", self.log_path)
            return

        # --- Stage 3: Parallel Data Reception ---
        temp_dir = f"temp_receiver_{os.getpid()}"
        os.makedirs(temp_dir, exist_ok=True)

        with Manager() as manager:
            received_chunks = manager.list()
            total_chunks = metadata.get("total_chunks")

            processes = []
            for i in range(self.worker_count):
                p = Process(target=self._recv_worker_prc, args=(received_chunks, total_chunks))
                processes.append(p)
                p.start()

            for p in processes:
                p.join()

            # --- Stage 4: Reassembly and Cleanup ---
            if len(received_chunks) != total_chunks:
                log(f"Incomplete transfer: Got {len(received_chunks)} of {total_chunks} chunks.", LogType.ERROR, "Failure", self.log_path)
            else:
                log("All chunks received from FC peer. Reassembling file.", status="Success", general_logfile_path=self.log_path)

            chunk_logfile = os.path.join(temp_dir, "chunks.json")
            collect_chunks_parallel(list(received_chunks), chunk_logfile, self.log_path, temp_dir)
            joined_path = join_chunks(temp_dir, chunk_logfile, self.log_path, chunk_size=chunk_size)
            decompress_final_chunk(joined_path, output_path, self.log_path)
            log(f"File successfully saved to {output_path}", status="Success", general_logfile_path=self.log_path)

        os.remove(chunk_logfile)
        os.rmdir(temp_dir)

    def _recv_worker_prc(self, received_chunks, total_chunks):
        """A worker process that listens on assigned ports and collects chunks for PRC."""
        sockets = []
        try:
            for port in self.data_ports_self:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.bind(('', port))
                sock.settimeout(45)
                sockets.append(sock)

            while len(received_chunks) < total_chunks:
                for sock in sockets:
                    try:
                        data, addr = sock.recvfrom(8192 + 100)
                        # Verify the sender is the expected FC peer
                        if addr[0] != self.peer_ip:
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

        finally:
            for sock in sockets:
                sock.close()


def fc_to_rp(TypeOfNat, OurPort, TheirPort, TheirIP, TestData, general_logfile_path):
    """
    Legacy function for basic FC to PRC NAT traversal testing.
    Maintained for backwards compatibility.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5)
    sock.bind(('', OurPort))

    # Encode data for sending
    data_bytes = TestData.encode()

    if TypeOfNat == 1:
        log("Initiating Restricted Cone Nat Behaviour", log_type=LogType.INFO, status="Success", general_logfile_path=general_logfile_path)
        sock.sendto(data_bytes, (TheirIP, TheirPort))
        log("Sent test data to their IP and port", log_type=LogType.INFO, status="Success", general_logfile_path=general_logfile_path)

        try:
            recv_data, addr = sock.recvfrom(1024)
            sender_ip, sender_port = addr
            log(f"Received data from {sender_ip}:{sender_port}", log_type=LogType.INFO, status="Success", general_logfile_path=general_logfile_path)

            # Validate
            if recv_data == data_bytes and sender_ip == TheirIP and sender_port == TheirPort:
                print("OK")
                # connection established
                log("Data received matches sent data and sender IP/Port", log_type=LogType.INFO, status="Success", general_logfile_path=general_logfile_path)
            else:
                log("Mismatch in data or sender!", log_type=LogType.ERROR, status="Failure", general_logfile_path=general_logfile_path)
        except socket.timeout:
            log("Timeout waiting for incoming data.", log_type=LogType.ERROR, status="Failure", general_logfile_path=general_logfile_path)

    elif TypeOfNat == 2:
        # Full Cone NAT behavior
        log("Initiating Full Cone Nat Behaviour", log_type=LogType.INFO, status="Success", general_logfile_path=general_logfile_path)
        try:
            recv_data, addr = sock.recvfrom(1024)
            sender_ip, sender_port = addr
            log(f"Received data from {sender_ip}:{sender_port}", log_type=LogType.INFO, status="Success", general_logfile_path=general_logfile_path)

            if recv_data == data_bytes and sender_ip == TheirIP and sender_port == TheirPort:
                # Send back the same data
                sock.sendto(data_bytes, (TheirIP, TheirPort))
                log("Sent back the received data to their IP and port", log_type=LogType.INFO, status="Success", general_logfile_path=general_logfile_path)
                print("OK")
                # connection established
            else:
                log("Mismatch in data or sender!", log_type=LogType.ERROR, status="Failure", general_logfile_path=general_logfile_path)
        except socket.timeout:
            log("Timeout waiting for incoming data.", log_type=LogType.ERROR, status="Failure", general_logfile_path=general_logfile_path)

    else:
        log("Unsupported NAT type specified.", log_type=LogType.ERROR, status="Failure", general_logfile_path=general_logfile_path)
    sock.close()
