import base64, zlib, json, struct
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import os

def pack_metadata(metadata: dict) -> bytes:
    """Pack metadata into a compact binary format."""
    open_ports = metadata.get("open_ports", [])[:64]
    ports_bytes = b",".join(str(p).encode() for p in open_ports)

    parts = [
        metadata.get("network_type", "Unknown").encode(),
        metadata.get("nat_type", "Unknown").encode(),
        b"1" if metadata.get("upnp_enabled") else b"0",
        (metadata.get("external_ip") or "").encode(),
        (metadata.get("local_ip") or "").encode(),
        b"1" if metadata.get("firewall_enabled") else b"0",
        ports_bytes
    ]
    return b"|".join(parts)

def unpack_metadata(data: bytes) -> dict:
    """Unpack binary format back into dict."""
    parts = data.split(b"|")
    return {
        "network_type": parts[0].decode(),
        "nat_type": parts[1].decode(),
        "upnp_enabled": parts[2] == b"1",
        "external_ip": parts[3].decode(),
        "local_ip": parts[4].decode(),
        "firewall_enabled": parts[5] == b"1",
        "open_ports": [int(p) for p in parts[6].split(b",") if p]
    }

def generate_link(metadata: dict, peer_public_key) -> str:
    # Step 1: pack and compress
    print(metadata)
    packed = pack_metadata(metadata)
    compressed = zlib.compress(packed, level=9)

    # Step 2: generate random AES key
    aes_key = os.urandom(32)  # AES-256
    iv = os.urandom(16)

    # Step 3: AES encrypt
    cipher = Cipher(algorithms.AES(aes_key), modes.CFB(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(compressed) + encryptor.finalize()

    # Step 4: RSA encrypt AES key
    encrypted_key = peer_public_key.encrypt(
        aes_key,
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),
                     algorithm=hashes.SHA256(),
                     label=None)
    )

    # Step 5: concat & base64
    blob = encrypted_key + iv + ciphertext
    encoded = base64.urlsafe_b64encode(blob).decode("utf-8").rstrip("=")

    return f"plink://{encoded}"

def decrypt_link(link: str, private_key) -> dict:
    # Step 1: strip and decode
    encoded = link[len("plink://"):]
    blob = base64.urlsafe_b64decode(encoded + "==")  # add padding back

    # Step 2: extract encrypted_key, iv, ciphertext
    key_size = private_key.key_size // 8
    encrypted_key, iv, ciphertext = blob[:key_size], blob[key_size:key_size+16], blob[key_size+16:]

    # Step 3: RSA decrypt AES key
    aes_key = private_key.decrypt(
        encrypted_key,
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),
                     algorithm=hashes.SHA256(),
                     label=None)
    )

    # Step 4: AES decrypt
    cipher = Cipher(algorithms.AES(aes_key), modes.CFB(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    compressed = decryptor.update(ciphertext) + decryptor.finalize()

    # Step 5: decompress and unpack
    packed = zlib.decompress(compressed)
    return unpack_metadata(packed)
