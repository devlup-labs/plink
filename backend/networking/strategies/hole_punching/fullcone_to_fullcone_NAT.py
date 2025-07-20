import socket
import threading
import time
import os

class FullConeToFullConeNAT:
    def __init__(self, self_info, peer_info):
        self.public_ip = self_info["external_ip"]
        self.public_port = self_info["open_ports"][0]

        self.peer_ip = peer_info["external_ip"]
        self.peer_port = peer_info["open_ports"][0]

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', self.public_port))

        print(f"[Init] Bound to {self.public_ip}:{self.public_port}")
        print(f"[Init] Targeting peer at {self.peer_ip}:{self.peer_port}")

    def _punch_hole(self):
        for _ in range(5):
            try:
                self.sock.sendto(b'hello', (self.peer_ip, self.peer_port))
                time.sleep(0.5)
            except Exception as e:
                print(f"[Error] Punching failed: {e}")

    def send(self, filepath=None):
        if not filepath or not os.path.isfile(filepath):
            print(f"[Send] Invalid file path: {filepath}")
            return

        self._punch_hole()

        print(f"[Send] Sending file: {filepath}")
        with open(filepath, 'rb') as f:
            while True:
                chunk = f.read(1024)
                if not chunk:
                    break
                self.sock.sendto(chunk, (self.peer_ip, self.peer_port))
                time.sleep(0.05)

        self.sock.sendto(b"[END]", (self.peer_ip, self.peer_port))
        print("[Send] File transfer complete.")

    def recv(self, output_path=None):
        if not output_path:
            output_path = "received_file"

        self._punch_hole()

        print(f"[Recv] Waiting for incoming data. Saving to: {output_path}")
        with open(output_path, 'wb') as f:
            while True:
                try:
                    data, addr = self.sock.recvfrom(1024)
                    if data == b"[END]":
                        print("[Recv] File transfer complete.")
                        break
                    f.write(data)
                except Exception as e:
                    print(f"[Error] Receive failed: {e}")
                    break