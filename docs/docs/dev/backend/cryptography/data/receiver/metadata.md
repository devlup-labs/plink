# Function: retreive_metadata

## Purpose:   
Retreives system and network metadata on the receiver's side.

### Parameters:   
public_ip : The receiver's public IP address.   
port : The port on which the receiver's listening.  
session_id : Unique identifier for the ongoing file transfer.

### Returns:  
dict: A metadata dictionary with the following    fields:
    public_ip: IP address of the receiver  
    port: Listening port number  
    free_space: Available disk space on the receiver’s machine (in bytes)  
    timestamp: current timestamp  
    session_id: Session ID associated with this connection

### Raises:  
OSError : If disk usage information cannot be retrieved (e.g., permission denied or invalid path).

### Example:   
python
metadata = retrieve_metadata(    
    public_ip="92.168.0.12",  
    port=9000,  
    session_id="session-xyz"  
)