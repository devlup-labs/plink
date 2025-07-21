import socket
import threading
import time
import os

"""
example for dictionary of self_info and peer_info (network metadata) :-
{
    "network_type": "NAT",
    "nat_type": "Restricted Cone NAT",
    "upnp_enabled": False,
    "external_ip": "152.59.21.64",
    "local_ip": "192.168.231.112",
    "firewall_enabled": True,
    "open_ports": [80, 900, 800, 443, ...]  # total of 64 ports
}
"""

class RestrictedToRestrictedNAT:
    def __init__(self, self_info, peer_info):
        self.public_ip = self_info["external_ip"]
        self.public_port = self_info["open_ports"][0]

        self.peer_ip = peer_info["external_ip"]
        self.peer_port = peer_info["open_ports"][0]

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', self.public_port)) 

        print(f"[Init] Listening for connection on {self.public_ip}:{self.public_port}")
        print(f"[Init] Targeting peer at {self.peer_ip}:{self.peer_port}")



    def _start_punching(self):#Punch holes to peer periodically to maintain the mapping
        def punch():
            while True:
                try:
                    self.sock.sendto(b"punch", (self.peer_ip, self.peer_port))
                    print(f"Punching sent to {self.peer_ip}:{self.peer_port}")
                    time.sleep(0.5)
                except Exception as e:
                    print(f"[Error] Punching failed: {e}")
                    break

        threading.Thread(target=punch, daemon=True).start()

    def send(self, filepath=None):
        if not filepath or not os.path.isfile(filepath):
            print(f"[Send] Invalid file path: {filepath}")
            return

        # Start punching before sending file
        self._start_punching()
        time.sleep(3) #giving time for making sure connection is established


        print(f"[Send] Sending file: {filepath}")
        with open(filepath, 'rb') as f:
            while True:
                chunk = f.read(1024)
                if not chunk:
                    break
                self.sock.sendto(chunk, (self.peer_ip, self.peer_port))
                time.sleep(0.01) #adding delay

        self.sock.sendto(b"[END]", (self.peer_ip, self.peer_port))
        print("[Send] File transfer complete.")



    def recv(self, output_path=None):
        if not output_path:
            output_path = "received_file"

        # Start punching from this side too
        self._start_punching()

        print(f"[Recv] Waiting for incoming data. Saving to: {output_path}")

        with open(output_path, 'wb') as f:
            while True:
                try:
                    data, addr = self.sock.recvfrom(1024) #receiving the chunk
                    if data == b"[END]":
                        print("[Recv] File transfer complete.")
                        break
                    f.write(data) #writing the chunk data 
                except Exception as e:
                    print(f"[Error] Receive failed: {e}")
                    break
