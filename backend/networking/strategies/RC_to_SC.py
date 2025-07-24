import socket
import threading
import random
import time
import os

"""
example for dictionary of self_info and peer_info (network metadata) :-
{
    "network_type": "NAT",
    "nat_type": "Symmetric NAT",
    "upnp_enabled": False,
    "external_ip": "152.59.21.64",
    "local_ip": "192.168.231.112",
    "firewall_enabled": True,
    "open_ports": [80, 900, 800, 443, ...]  # total of 64 ports
}

APPROACH:
--------
first restricted cone sends a dummy packet to symmetric NAT
the dummy packet is not recieved by the symmetric NAT but the symmetric NAT gets the IP of the restricted cone
then the symmetric cone sends a dummy packet to restricted cone
the restricted cone recieves the dummy packet and a connection is established

--------
restricted cone side should use RC_to_SC
symmetric cone side should use SC_to_RC

"""

class RC_to_SC:
    def __init__(self, self_info, peer_info):
        self.public_ip = self_info["external_ip"]
        self.public_port = self_info["open_ports"][0]

        self.peer_ip = peer_info["external_ip"]

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', self.public_port))

        print(f"[Restricted] Bound to {self.public_ip}:{self.public_port}")
        print(f"[Restricted] Will send dummy to Symmetric NAT at {self.peer_ip}:<random_port>")

    def punch_and_listen(self):
        def recv_loop():
            while True:
                try:
                    data, addr = self.sock.recvfrom(1024)
                    print(f"[Restricted] Received from {addr}: {data}")
                except Exception as e:
                    print(f"[Restricted] Error: {e}")
                    break

        threading.Thread(target=recv_loop, daemon=True).start()

        # Send a dummy message to random port of symmetric NAT
        dummy_port = random.randint(10000, 60000)
        self.sock.sendto(b"dummy", (self.peer_ip, dummy_port))
        print(f"[Restricted] Sent dummy to {self.peer_ip}:{dummy_port}")

    def send(self, filepath=None):
        if not filepath or not os.path.isfile(filepath):
            print(f"[Send] Invalid file path: {filepath}")
            return

        # Initial packet to establish NAT mapping
        self.sock.sendto(b'hello', (self.peer_ip, self.peer_port))
        self._punch_hole()
        time.sleep(2)

        print(f"[Send] Sending file: {filepath}")
        with open(filepath, 'rb') as f:
            while True:
                chunk = f.read(1024)
                if not chunk:
                    break
                self.sock.sendto(chunk, (self.peer_ip, self.peer_port))
                time.sleep(0.01)

        self.sock.sendto(b"[END]", (self.peer_ip, self.peer_port))
        print("[Send] File transfer complete.")

    def recv(self, output_path=None):
        if not output_path:
            output_path = "received_file"

        # Send to peer once to help punch back
        self.sock.sendto(b'hello', (self.peer_ip, self.peer_port))
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

class SC_to_RC:
    def __init__(self, self_info, peer_info):
        self.public_ip = self_info["external_ip"]
        self.public_port = self_info["open_ports"][0]

        self.peer_ip = peer_info["external_ip"]

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', self.public_port))

        print(f"[Restricted] Bound to {self.public_ip}:{self.public_port}")
        print(f"[Restricted] Will send dummy to Symmetric NAT at {self.peer_ip}:<random_port>")

    def punch_and_listen(self):
        def recv_loop():
            while True:
                try:
                    data, addr = self.sock.recvfrom(1024)
                    print(f"[Restricted] Received from {addr}: {data}")
                except Exception as e:
                    print(f"[Restricted] Error: {e}")
                    break

        threading.Thread(target=recv_loop, daemon=True).start()

        # Send a dummy message to random port of symmetric NAT
        dummy_port = random.randint(10000, 60000)
        self.sock.sendto(b"dummy", (self.peer_ip, dummy_port))
        print(f"[Restricted] Sent dummy to {self.peer_ip}:{dummy_port}")

    def send(self, filepath=None):
        if not filepath or not os.path.isfile(filepath):
            print(f"[Send] Invalid file path: {filepath}")
            return

        # Initial packet to establish NAT mapping
        self.sock.sendto(b'hello', (self.peer_ip, self.peer_port))
        self._punch_hole()
        time.sleep(2)

        print(f"[Send] Sending file: {filepath}")
        with open(filepath, 'rb') as f:
            while True:
                chunk = f.read(1024)
                if not chunk:
                    break
                self.sock.sendto(chunk, (self.peer_ip, self.peer_port))
                time.sleep(0.01)

        self.sock.sendto(b"[END]", (self.peer_ip, self.peer_port))
        print("[Send] File transfer complete.")

    def recv(self, output_path=None):
        if not output_path:
            output_path = "received_file"

        # Send to peer once to help punch back
        self.sock.sendto(b'hello', (self.peer_ip, self.peer_port))
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
