
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
    """
    Full-Cone -> Port-Restricted-Cone
    Port-restricted requires mapping to the exact (IP, PORT) tuple used.
    We therefore strictly pair each of our data ports to the peer's port,
    and maintain those bindings with scheduled keepalives.
    """

    KEEPALIVE_INTERVAL = 10

    def __init__(self, self_info, peer_info, self_private_key, peer_public_key, log_path):
        self.self_ip = self_info["external_ip"]
        self.self_ports = list(self_info["open_ports"])

        self.peer_ip = peer_info["external_ip"]
        self.peer_ports = list(peer_info["open_ports"])

        self.private_key = self_private_key
        self.public_key = peer_public_key

        self.log_path = log_path

        if len(self.self_ports) != 64 or len(self.peer_ports) != 64:
            raise ValueError("Exactly 64 ports required for both peers (1 control + 63 data).")

        self.worker_count = min(max(cpu_count(), 2), len(self.self_ports))

        self.control_port_self = self.self_ports[0]
        self.control_port_peer = self.peer_ports[0]

        self.data_ports_self = self.self_ports[1:]
        self.data_ports_peer = self.peer_ports[1:]

        self._keepalive_active = False
        self._keepalive_process = None

        log("FC->PRC session initialized. Control channel established.", general_logfile_path=self.log_path)

    def _punch_exact(self):
        """
        PRC needs exact (ip,port) to be opened. We send from each local data port
        to the matching peer data port. Also punch control channel.
        """
        # Data ports
        for i, lp in enumerate(self.data_ports_self):
            rp = self.data_ports_peer[i]
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.bind(('', lp))
                    s.sendto(b'p', (self.peer_ip, rp))
            except Exception as e:
                log(f"PRC punch failed {lp}->{rp}: {e}", LogType.WARNING, "Failure", self.log_path)

        # Control
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.bind(('', self.control_port_self))
                s.sendto(b'control', (self.peer_ip, self.control_port_peer))
        except Exception as e:
            log(f"Control punch failed: {e}", LogType.WARNING, "Failure", self.log_path)

    def _start_keepalive(self):
        if self._keepalive_process is not None:
            return
        self._keepalive_active = True
        p = Process(target=self._keepalive_worker, daemon=True)
        p.start()
        self._keepalive_process = p

    def _stop_keepalive(self):
        if self._keepalive_process is None:
            return
        self._keepalive_active = False
        self._keepalive_process.join(timeout=self.KEEPALIVE_INTERVAL + 2)
        self._keepalive_process = None

    def _keepalive_worker(self):
        while self._keepalive_active:
            try:
                self._punch_exact()
            finally:
                time.sleep(self.KEEPALIVE_INTERVAL)

    # ------------------- SENDING -------------------
    def send(self, filepath, chunk_size=8192):
        if not os.path.isfile(filepath):
            log(f"File not found: {filepath}", LogType.CRITICAL, "Failure", self.log_path)
            return

        temp_dir = f"temp_sender_{os.getpid()}"
        os.makedirs(temp_dir, exist_ok=True)
        compressed_path = compress_file(filepath, temp_dir, self.log_path)
        log(f"File compressed to {compressed_path}", general_logfile_path=self.log_path)

        self._start_keepalive()

        metadata = retrieve_sender_metadata(
            file_path=str(compressed_path),
            chunk_size=chunk_size,
            public_ip=self.self_ip,
            ports=self.self_ports,
            general_logfile_path=self.log_path
        )
        encrypted_metadata = encryption(metadata, self.public_key, self.log_path)

        # Control channel exchange
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.bind(('', self.control_port_self))
                log("Sending file metadata. Awaiting confirmation from receiver...", general_logfile_path=self.log_path)
                sock.sendto(b"[META_START]" + json.dumps(encrypted_metadata).encode() + b"[META_END]", (self.peer_ip, self.control_port_peer))
                sock.settimeout(60.0)
                ack, _ = sock.recvfrom(1024)
                if ack != b"META_OK":
                    raise ConnectionAbortedError("Receiver sent an invalid acknowledgment.")
                log("Receiver confirmed metadata. Starting data transfer.", status="Success", general_logfile_path=self.log_path)
        except Exception as e:
            self._stop_keepalive()
            log(f"Metadata exchange failed: {e}", LogType.CRITICAL, "Failure", self.log_path)
            return

        # Exact punch then transfer
        self._punch_exact()
        time.sleep(1.0)

        all_chunks = list(yield_chunks(compressed_path, chunk_size, self.log_path))

        processes = []
        for i in range(self.worker_count):
            worker_chunks = all_chunks[i::self.worker_count]
            p = Process(target=self._send_worker, args=(worker_chunks,))
            processes.append(p)
            p.start()

        for p in processes:
            p.join()

        self._stop_keepalive()
        log("File data sent successfully.", status="Success", general_logfile_path=self.log_path)

        os.remove(compressed_path)
        os.rmdir(temp_dir)

    def _send_worker(self, chunks):
        sockets = [socket.socket(socket.AF_INET, socket.SOCK_DGRAM) for _ in self.data_ports_self]
        try:
            for i, sock in enumerate(sockets):
                sock.bind(('', self.data_ports_self[i]))
            for i, (chunk_num, chunk_data) in enumerate(chunks):
                header = f"[{chunk_num}]".encode()
                idx = i % len(sockets)
                sockets[idx].sendto(header + chunk_data, (self.peer_ip, self.data_ports_peer[idx]))
        finally:
            for s in sockets:
                s.close()

    # ------------------- RECEIVING -------------------
    def recv(self, output_path="received_file", chunk_size=8192):
        self._start_keepalive()

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.bind(('', self.control_port_self))
                sock.settimeout(300.0)

                # pre-punch (PRC)
                self._punch_exact()

                log("Ready to receive. Listening for incoming metadata...", general_logfile_path=self.log_path)
                data, _ = sock.recvfrom(65536)

                if not data.startswith(b"[META_START]"):
                    raise ValueError("Received invalid metadata format.")

                metadata_raw = data.split(b"[META_START]")[1].split(b"[META_END]")[0]
                metadata = decryption(json.loads(metadata_raw.decode()), self.private_key, self.log_path)
                log(f"Metadata decrypted successfully: {metadata}", general_logfile_path=self.log_path)

                sock.sendto(b"META_OK", (self.peer_ip, self.control_port_peer))
        except Exception as e:
            self._stop_keepalive()
            log(f"Failed to receive or decrypt metadata: {e}", LogType.CRITICAL, "Failure", self.log_path)
            return

        temp_dir = f"temp_receiver_{os.getpid()}"
        os.makedirs(temp_dir, exist_ok=True)

        with Manager() as manager:
            received_chunks = manager.list()
            total_chunks = metadata.get("total_chunks")

            processes = []
            for _ in range(self.worker_count):
                p = Process(target=self._recv_worker, args=(received_chunks, total_chunks))
                processes.append(p)
                p.start()

            for p in processes:
                p.join()

            if len(received_chunks) != total_chunks:
                log(f"Incomplete transfer: Got {len(received_chunks)} of {total_chunks}.", LogType.ERROR, "Failure", self.log_path)
            else:
                log("All chunks received. Reassembling.", status="Success", general_logfile_path=self.log_path)

            chunk_logfile = os.path.join(temp_dir, "chunks.json")
            collect_chunks_parallel(list(received_chunks), chunk_logfile, self.log_path, temp_dir)
            joined_path = join_chunks(temp_dir, chunk_logfile, self.log_path, chunk_size=chunk_size)
            decompress_final_chunk(joined_path, output_path, self.log_path)
            log(f"File successfully saved to {output_path}", status="Success", general_logfile_path=self.log_path)

        try:
            os.remove(chunk_logfile)
            os.rmdir(temp_dir)
        finally:
            self._stop_keepalive()

    def _recv_worker(self, received_chunks, total_chunks):
        sockets = [socket.socket(socket.AF_INET, socket.SOCK_DGRAM) for _ in self.data_ports_self]
        try:
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
        finally:
            for s in sockets:
                s.close()
