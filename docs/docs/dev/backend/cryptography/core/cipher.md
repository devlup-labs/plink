## File: 'cipher.py'

This file contains functions to **encrypt and decrypt metadata** using RSA public and private keys.  

---

## Functions

- `encryption`: Encrypts a metadata dictionary using the RSA public key.
- `decryption`: Decrypts a base64-encoded string back into a metadata dictionary using the private key.

---

### Function: 'encryption'

**Purpose:** Encrypts the metadata dictionary using an RSA public key so that it can be securely transferred.

**Parameters:**
- `metadata` (`dict`): The metadata dictionary which is to be encrypted.
- `public_key` (`RSAPublicKey`): The RSA public key used to encrypt the metadata.
- `general_logfile_path` (`str`): Path to the log file where logging messages are recorded.

**Returns:**
- `str`: The encrypted metadata in base64-encoded string format.

**Raises:**
- This function assumes correct inputs and does not explicitly raise errors.
- Internal exceptions from encryption may occur if keys are invalid or input is malformed.

**Side Effects:**
- Logs various steps like:
  - When encryption starts
  - When metadata is converted to JSON
  - When JSON is converted to bytes
  - After successful encryption
  - After base64 encoding is done

---

### Function: 'decryption'

**Purpose:**  
Decrypts the base64-encoded encrypted metadata using an RSA private key and converts it back to a dictionary.

**Parameters:**
- `base64_encrypted_string` (`str`): The encrypted metadata string (base64 format).
- `private_key` (`RSAPrivateKey`): The RSA private key used to decrypt the metadata.
- `general_logfile_path` (`str`): Path to the log file where logging messages are recorded.

**Returns:**
- `dict`: The decrypted metadata as a Python dictionary.

**Raises:**
- This function assumes the data is properly encrypted and keys are correct.
- Internal exceptions may occur if the string is tampered with or key mismatch happens.

**Side Effects:**
- Logs different steps like:
  - When decryption starts
  - When base64 string is decoded
  - When actual decryption is done
  - When bytes are converted to JSON string
  - When JSON is turned back into a dictionary

---

## Notes

- Encryption uses `RSA` with `OAEP` padding and `SHA256` hashing.
- Base64 is used so that encrypted bytes can be safely stored or transmitted.
- Logging is done using the custom `log()` function and helps in debugging or tracking status.
