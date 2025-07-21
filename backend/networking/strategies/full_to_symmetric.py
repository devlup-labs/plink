import socket
import threading
import time
import os

"""
example for dictionary of self_info and peer_info :-
{
    "network_type": "NAT",
    "nat_type": "Symmetric NAT",
    "upnp_enabled": False,
    "external_ip": "152.59.21.64",
    "local_ip": "192.168.231.112",
    "firewall_enabled": True,
    "open_ports": [80, 900, 800, 443, ...]  # total of 64 ports
}
"""

class SymmetricToFullConeNAT:
    def __init__(self, self_info, peer_info):
        
        # Use first open port
        self.local_ip = self_info["local_ip"]
        self.public_ip = self_info["external_ip"] if self_info["external_ip"] else None
        self.public_port = self_info["open_ports"][0] if self_info["open_ports"] else None
        self.peer_ip = peer_info["external_ip"] if peer_info["external_ip"] else None
        self.peer_port = peer_info["open_ports"][0] if peer_info["open_ports"] else None

        # Create UDP socket

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if self_info["nat_type"] == "Symmetric NAT":
            self.sock.bind((self.local_ip, 0))
        elif self_info["nat_type"] == "Full Cone NAT":
            self.sock.bind(('', self.public_port)) 

        print(f"[Symmetric] Local socket bound to {self.sock.getsockname()}")
        print(f"[Symmetric] Targeting peer at {self.peer_ip}:{self.peer_port}")
    def keep_connection_active(self):
        """send messages continuously to keep the connection active"""
        def punch():
            while True:
                try:
                    self.sock.sendto(b'keep-alive', (self.peer_ip, self.peer_port))
                    time.sleep(0.5)
                except Exception as e:
                    print(f"[Error] Error in keep-alive: {e}")
                    break
        threading.Thread(target=punch, daemon=True).start()
                
    def send(self, filepath=None):
        if not filepath or not os.path.isfile(filepath):
            print(f"[Error] Invalid file path {filepath}")
            return

        # Initial packet to establish the mapping
        self.sock.sendto(b"Hello", (self.peer_ip, self.peer_port))
        self.keep_connection_active()
        time.sleep(0.5)

        print(f"[Symmetric] Sending file {filepath} to {self.peer_ip}:{self.peer_port}")
        with open(filepath, 'rb') as f:
            while True:
                chunk = f.read(1024)
                if not chunk:
                    break
                self.sock.sendto(chunk, (self.peer_ip, self.peer_port))
                time.sleep(0.01)

        self.sock.sendto(b"[END]", (self.peer_ip, self.peer_port))
        print("[Send] File transfer complete.")
        print("[Send] File transfer complete.")

    def recieve(self, output_path="received_file"):
        print(f"[FullCone] Waiting for data...")

        with open(output_path, 'wb') as f:
            while True:
                data, addr = self.sock.recvfrom(1024)
                if not self.peer_addr:
                    self.peer_addr = addr
                    print(f"[FullCone] Peer detected: {self.peer_addr}")
                if data == b"[END]":
                    print("[FullCone] File transfer complete.")
                    break
                f.write(data)