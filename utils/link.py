import json
import base64
import zlib


def generate_link(metadata: dict) -> str:
    """
    Take network metadata (IP + 64 ports) and return a plink://<hash>-style string.
    """
    # Serialize to JSON
    raw_json = json.dumps(metadata)

    # Compress
    compressed = zlib.compress(raw_json.encode("utf-8"))

    # Base64 encode (URL safe, no + or /)
    encoded = base64.urlsafe_b64encode(compressed).decode("utf-8")

    # Return as plink://hash
    return f"plink://{encoded}"


def decrypt_link(link: str) -> dict:
    """
    Take plink://<hash> and recover the original metadata (IP + ports).
    """
    if not link.startswith("plink://"):
        raise ValueError("Invalid link format")

    # Strip scheme
    encoded = link[len("plink://"):]

    # Decode and decompress
    compressed = base64.urlsafe_b64decode(encoded.encode("utf-8"))
    raw_json = zlib.decompress(compressed).decode("utf-8")

    # Back to dict
    return json.loads(raw_json)
