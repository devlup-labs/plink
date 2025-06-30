# Function: retrieve_metadata

## Purpose:  
Collects and returns metadata about the file to be sent.

### Parameters:
file_path: Path to the file that will be sent.
chunk_size : Size of each chunk (in bytes) the file should be divided into.
public_ip : The public IP address of the sender.
port : The port from which the sender is sharing the file.
session_id : Unique identifier for the file transfer session.

### Returns:
dict A dictionary containing:
    public_ip: Sender’s public IP
    port: Sender’s port
    file_name: Name of the file
    file_size: Size of the file in bytes
    chunk_size: Size of each chunk
    total_chunks: Number of chunks the file will be split into
    timestamp: timestamp when metadata was generated
    session_id: Transfer session identifier

### Raises:
FileNotFoundError: If the provided file path does not exist.
PermissionError: If the file is not accessible for reading.

### Example:
python
metadata = retrieve_metadata(
    "docs/files/sample.pdf",  
    chunk_size=1024 * 256,  
    public_ip="103.12.45.99",  
    port=8000,  
    session_id="session-xyz"  
)