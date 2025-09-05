import json
import base64
import zlib
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from utils.logging import log, LogType


def generate_link(metadata: dict, peer_public_key, general_logfile_path="app.log") -> str:
    """
    Take network metadata and encrypt it with peer's public key, then return a plink://<hash>-style string.

    Args:
        metadata (dict): Network metadata to be encrypted and encoded
        peer_public_key: The peer's RSA public key for encryption
        general_logfile_path (str): Path to log file

    Returns:
        str: Encrypted and encoded link in plink://hash format
    """
    log("Generating encrypted plink link", LogType.INFO, "Started", general_logfile_path)

    try:
        # Serialize to JSON
        raw_json = json.dumps(metadata)
        log("Metadata serialized to JSON", LogType.DEBUG, "Success", general_logfile_path)

        # Compress first to reduce size before encryption
        compressed = zlib.compress(raw_json.encode("utf-8"))
        log("Metadata compressed", LogType.DEBUG, "Success", general_logfile_path)

        # Encrypt with peer's public key using OAEP padding
        encrypted = peer_public_key.encrypt(
            compressed,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        log("Metadata encrypted with peer's public key", LogType.INFO, "Success", general_logfile_path)

        # Base64 encode (URL safe, no + or /)
        encoded = base64.urlsafe_b64encode(encrypted).decode("utf-8")
        log("Encrypted metadata base64 encoded", LogType.DEBUG, "Success", general_logfile_path)

        # Return as plink://hash
        link = f"plink://{encoded}"
        log("Plink link generated successfully", LogType.INFO, "Success", general_logfile_path)
        return link

    except Exception as e:
        log(f"Failed to generate link: {e}", LogType.ERROR, "Failure", general_logfile_path)
        raise


def decrypt_link(link: str, private_key, general_logfile_path="app.log") -> dict:
    """
    Take plink://<hash> and decrypt it with own private key to recover the original metadata.

    Args:
        link (str): The encrypted plink link
        private_key: Own RSA private key for decryption
        general_logfile_path (str): Path to log file

    Returns:
        dict: Decrypted network metadata
    """
    log("Decrypting plink link", LogType.INFO, "Started", general_logfile_path)

    try:
        if not link.startswith("plink://"):
            raise ValueError("Invalid link format - must start with plink://")

        # Strip scheme
        encoded = link[len("plink://"):]
        log("Link scheme stripped", LogType.DEBUG, "Success", general_logfile_path)

        # Base64 decode
        encrypted = base64.urlsafe_b64decode(encoded.encode("utf-8"))
        log("Link base64 decoded", LogType.DEBUG, "Success", general_logfile_path)

        # Decrypt with own private key
        compressed = private_key.decrypt(
            encrypted,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        log("Link decrypted with private key", LogType.INFO, "Success", general_logfile_path)

        # Decompress
        raw_json = zlib.decompress(compressed).decode("utf-8")
        log("Decrypted data decompressed", LogType.DEBUG, "Success", general_logfile_path)

        # Back to dict
        metadata = json.loads(raw_json)
        log("Plink link decrypted successfully", LogType.INFO, "Success", general_logfile_path)
        return metadata

    except Exception as e:
        log(f"Failed to decrypt link: {e}", LogType.ERROR, "Failure", general_logfile_path)
        raise
