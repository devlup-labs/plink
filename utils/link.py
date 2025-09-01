import json
import hashlib
import base64

# Session cache: maps short hash -> metadata
# this is used since we can't make a function to directly decrpyt the sha256, so it is used to store.
_HASH_STORE = {}

def generate_link(metadata: dict) -> str:
    """
    Takes network metadata (IP + 64 open ports),
    converts to SHA-256 hash, shortens it,
    stores mapping, and returns a plink:// link.
    """
    # Step 1: Convert metadata dict to JSON string
    meta_str = json.dumps(metadata, sort_keys=True)

    # Step 2: Compute SHA-256 hash
    digest = hashlib.sha256(meta_str.encode()).digest()

    # Step 3: Shorten (128-bit = first 16 bytes, then base64-url)
    short_hash = base64.urlsafe_b64encode(digest[:16]).decode().rstrip("=")

    # Step 4: Store mapping in memory
    _HASH_STORE[short_hash] = metadata

    # Step 5: Return plink link
    return f"plink://{short_hash}"


def decrypt_link(link: str) -> dict | None:
    """
    Takes plink:// link, extracts hash,
    and returns original metadata (if available).
    """
    short_hash = link.replace("plink://", "")
    return _HASH_STORE.get(short_hash)


"""
TO use it:

from utils.link import generate_link, decrypt_link
metadata = {
    "ip": "......",
    "ports": list(range(8000, 8064))  # 64 ports
}

link = generate_link(metadata)
print("Generated link:", link)
restored_metadata = decrypt_link(link)
print("Restored metadata:", restored_metadata)
"""
