"""
function: GenKey
Purpose: Generate a new RSA private key for encryption/decryption of data.
Input: None
Returns: A new key in hexadecimal format.
"""

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

def GenKey():
    # Generate RSA private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048  # You can use 4096 for higher security
    )

    # Convert private key to PEM format (string)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    return private_pem.decode('utf-8')