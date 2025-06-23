"""
Function Name: divide_in_chunks
Purpose: divide given file/folder in chunks given path and CHUNK_SIZE
Inputs: CHUNK_SIZE
Outputs: yield tuple of (chunk_name : chunk_data) and chunk_name being 1,2,3…n

"""
from pathlib import Path

def divide_in_chunks(path, CHUNK_SIZE):
    
    p = Path(path)
    
    if p.is_file():
        
        with p.open("rb") as f:
            chunk_id = 1
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                yield str(chunk_id), chunk
                chunk_id += 1
            
    else:
        print("Give appropriate path")
    