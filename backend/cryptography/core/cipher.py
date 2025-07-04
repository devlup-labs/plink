import json
import base64
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from utils.logging import log, LogType

def encryption(metadata: dict, public_key, general_logfile_path) -> str:
    
    '''
    Function Name: encryption
    Purpose: To encrypt the metadata using RSA public key
    Inputs:
        - metadata (dict): (dictionary containing metadata which is to be encrypted)
        - public_key (which will be used to encrypt)
        - general_logfile_path (path to the log file)
    Outputs:
        - returns base64-encoded (str) string for encrypted metadata
    '''

    log("Metadata encryption initiated", log_type=LogType.INFO, status = "Started", general_logfile_path=general_logfile_path)

    json_string = json.dumps(metadata)
    log("Metadata converted to JSON string", log_type=LogType.DEBUG, status = "Success", general_logfile_path=general_logfile_path)

    data_bytes = json_string.encode('utf-8')
    log("JSON string converted to bytes for encryption", log_type=LogType.DEBUG, status = "Success", general_logfile_path=general_logfile_path)

    encrypted = public_key.encrypt(
        data_bytes,
        padding.OAEP(
            mgf=padding.MGF1(algorithm = hashes.SHA256()),
            algorithm = hashes.SHA256(),
            label = None
        )
    )
    log("Metadata encrypted using RSA public key", log_type=LogType.INFO, status = "Success", general_logfile_path=general_logfile_path)


    encrypted_b64 = base64.b64encode(encrypted).decode('utf-8')
    log("Encrypted metadata base64 encoded", log_type=LogType.INFO, status = "Success", general_logfile_path=general_logfile_path)

    return encrypted_b64

def decryption(base64_encrypted_string: str, private_key, general_logfile_path) -> dict:
    '''
    Function Name: decryption
    Purpose: To decrypt the encrypted metadata using RSA private key
    Inputs:
        - base64_encrypted_string (str): (base64-encoded string of encrypted metadata)
        - private_key (which will be used to decrypt)
        - general_logfile_path (path to the log file)
    Outputs:
        - returns decrypted metadata as a dictionary
    '''

    log("Metadata decryption initiated", log_type=LogType.INFO, status = "Started", general_logfile_path=general_logfile_path)

    encrypted_bytes = base64.b64decode(base64_encrypted_string.encode('utf-8'))
    log("Encrypted metadata base64 decoded", log_type=LogType.DEBUG, status = "Success", general_logfile_path=general_logfile_path)

    decrypted = private_key.decrypt(
        encrypted_bytes,
        padding.OAEP(
            mgf=padding.MGF1(algorithm = hashes.SHA256()),
            algorithm = hashes.SHA256(),
            label = None
        )
    )
    log("Metadata decrypted using RSA private key", log_type=LogType.INFO, status = "Success", general_logfile_path=general_logfile_path)

    json_string = decrypted.decode('utf-8')
    log("Decrypted bytes converted to JSON string", log_type=LogType.DEBUG, status = "Success", general_logfile_path=general_logfile_path)

    metadata = json.loads(json_string)
    log("JSON string converted back to dictionary", log_type=LogType.DEBUG, status = "Success", general_logfile_path=general_logfile_path)

    return metadata 