import os
import json
from datetime import datetime
from utils.logging import log, LogType


def create_plink_file(public_key_pem: str, role: str, general_logfile_path="app.log") -> str:
    """
    Create a .plink file containing the public key and metadata.

    Args:
        public_key_pem (str): The public key in PEM format
        role (str): Role of the user ("sender" or "receiver")
        general_logfile_path (str): Path to log file

    Returns:
        str: Path to the created .plink file
    """
    log("Creating .plink file", LogType.INFO, "Started", general_logfile_path)

    try:
        # Create filename with timestamp and role
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"plink_{role}_{timestamp}.plink"

        # Create the .plink file content
        plink_content = {
            "version": "1.0",
            "role": role,
            "created_at": datetime.now().isoformat(),
            "public_key": public_key_pem
        }

        # Write the .plink file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(plink_content, f, indent=2)

        log(f".plink file created: {filename}", LogType.INFO, "Success", general_logfile_path)
        return filename

    except Exception as e:
        log(f"Failed to create .plink file: {e}", LogType.ERROR, "Failure", general_logfile_path)
        raise


def read_plink_file(file_path: str, general_logfile_path="app.log") -> str:
    """
    Read a .plink file and extract the public key.

    Args:
        file_path (str): Path to the .plink file
        general_logfile_path (str): Path to log file

    Returns:
        str: The public key in PEM format

    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the file format is invalid
    """
    log(f"Reading .plink file: {file_path}", LogType.INFO, "Started", general_logfile_path)

    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f".plink file not found: {file_path}")

        if not file_path.endswith('.plink'):
            raise ValueError("File must have .plink extension")

        with open(file_path, 'r', encoding='utf-8') as f:
            plink_content = json.load(f)

        # Validate .plink file structure
        required_fields = ["version", "role", "created_at", "public_key"]
        for field in required_fields:
            if field not in plink_content:
                raise ValueError(f"Invalid .plink file: missing field '{field}'")

        public_key = plink_content["public_key"]

        # Validate that it looks like a PEM key
        if not (public_key.startswith("-----BEGIN PUBLIC KEY-----") and
                public_key.endswith("-----END PUBLIC KEY-----")):
            raise ValueError("Invalid public key format in .plink file")

        log(f".plink file read successfully: {plink_content['role']} key from {plink_content['created_at']}",
            LogType.INFO, "Success", general_logfile_path)

        return public_key

    except json.JSONDecodeError as e:
        log(f"Invalid JSON in .plink file: {e}", LogType.ERROR, "Failure", general_logfile_path)
        raise ValueError(f"Invalid .plink file format: {e}")
    except Exception as e:
        log(f"Failed to read .plink file: {e}", LogType.ERROR, "Failure", general_logfile_path)
        raise


def validate_plink_file(file_path: str, general_logfile_path="app.log") -> dict:
    """
    Validate a .plink file and return its metadata.

    Args:
        file_path (str): Path to the .plink file
        general_logfile_path (str): Path to log file

    Returns:
        dict: Metadata from the .plink file

    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the file format is invalid
    """
    log(f"Validating .plink file: {file_path}", LogType.INFO, "Started", general_logfile_path)

    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f".plink file not found: {file_path}")

        if not file_path.endswith('.plink'):
            raise ValueError("File must have .plink extension")

        with open(file_path, 'r', encoding='utf-8') as f:
            plink_content = json.load(f)

        # Validate .plink file structure
        required_fields = ["version", "role", "created_at", "public_key"]
        for field in required_fields:
            if field not in plink_content:
                raise ValueError(f"Invalid .plink file: missing field '{field}'")

        # Validate version
        if plink_content["version"] != "1.0":
            raise ValueError(f"Unsupported .plink file version: {plink_content['version']}")

        # Validate role
        if plink_content["role"] not in ["sender", "receiver"]:
            raise ValueError(f"Invalid role in .plink file: {plink_content['role']}")

        # Validate public key format
        public_key = plink_content["public_key"]
        if not (public_key.startswith("-----BEGIN PUBLIC KEY-----") and
                public_key.endswith("-----END PUBLIC KEY-----")):
            raise ValueError("Invalid public key format in .plink file")

        log(f".plink file validation successful", LogType.INFO, "Success", general_logfile_path)

        return {
            "version": plink_content["version"],
            "role": plink_content["role"],
            "created_at": plink_content["created_at"],
            "file_path": file_path,
            "file_size": os.path.getsize(file_path)
        }

    except json.JSONDecodeError as e:
        log(f"Invalid JSON in .plink file: {e}", LogType.ERROR, "Failure", general_logfile_path)
        raise ValueError(f"Invalid .plink file format: {e}")
    except Exception as e:
        log(f"Failed to validate .plink file: {e}", LogType.ERROR, "Failure", general_logfile_path)
        raise
