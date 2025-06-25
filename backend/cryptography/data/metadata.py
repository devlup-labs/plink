"""
Function Name: retrieve_metadata  
Purpose: Calculate size and total number of chunks required for a file or folder  
Inputs:  
    - path: Path to the file or folder  
    - CHUNK_SIZE: Size of each chunk in bytes  
Outputs:  
    - Dictionary with keys:  
        - "size": total size in bytes  
        - "total_chunks": number of chunks required  
"""
from pathlib import Path
from math import ceil

def retrieve_metadata(path, CHUNK_SIZE):
    p = Path(path)

    if p.exists() == False:
        raise FileNotFoundError(f"Path doesn't exists : {path}")
    
    if p.is_file():
        size = p.stat().st_size

    elif p.is_dir():
        size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())

    else:
        raise ValueError(f"Unsupported path type : {path}")
    
    total_chunks = ceil(size/CHUNK_SIZE)

    return {"size": size,
            "total_chunks": total_chunks}
