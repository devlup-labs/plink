'''
Function Name: retrieve_metadata 
Purpose: to collect sender's metadata : public_ip, port, sile_name, chunk_size, total_chunks, timestamp, session_id
Inputs:
    -file_path : path of the file to be sent
    -chunnk_size : size of the chunks to be sent in bytes
    -public_ip : public ip of the receiver
    -port : opened port for connection
    -session_id : session id of the operation
     
Outputs:  
    - returns dictionary which contains metadata : public_ip, port, file_name, file_size, chunk_size, total_chunks, timestamp, session_id 

'''

import os
from datetime import datetime
from math import ceil
from pathlib import Path

def retrieve_metadata(file_path,chunk_size,public_ip,port,session_id):
    
    p = Path(file_path)
    
    if p.is_file():
            file_size = p.stat().st_size
            
    total_chunks = ceil(file_size/chunk_size)

    return {
        "public_ip": public_ip,
        "port": port,
        "file_name": os.path.basename(file_path),
        "file_size": file_size,
        "chunk_size": chunk_size,
        "total_chunks": total_chunks,
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id
    }