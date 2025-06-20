"""
Function Name: retrieve_metadata
Purpose: Given file/folder path and CHUNK_SIZE Determine basic properties of file/folder like size and total_chunks(based on size/CHUNK_SIZE)
Inputs: path, CHUNK_SIZE
Outputs: size, total_chunks

"""

from pathlib import Path
import math

def retrieve_metadata(path ,CHUNK_SIZE):

    p = Path(path)
    
    if p.exists():
        if p.is_file():
            size = p.stat().st_size
        
        else:
            
            size = sum(file.stat().st_size for file in p.rglob("*") if file.isfile())
    
    else:
        print("Invalid Path Provided")
            
            
    total_chunks = math.ceil(size/CHUNK_SIZE)
    
    return {"size": size, "total_chunks": total_chunks}