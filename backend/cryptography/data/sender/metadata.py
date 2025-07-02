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

from utils.logging import LogType, log

def retrieve_metadata(file_path,chunk_size,public_ip,ports,general_logfile_path):

    p = Path(file_path)
    file_size = 0
    if p.is_file():
            file_size = p.stat().st_size

    if file_size >0 :
        log(
            "file metadata retrived",
            LogType.INFO,
            "Success",
            general_logfile_path,
            False
        )
    else :
        log(
            "file metadata retrived",
            LogType.INFO,
            "Failure",
            general_logfile_path,
            False
        )

    total_chunks = ceil(file_size/chunk_size)

    return {
        "file_name": os.path.basename(file_path),
        "file_size": file_size,
        "chunk_size": chunk_size,
        "total_chunks": total_chunks,
        "timestamp": datetime.now().isoformat(),
    }
