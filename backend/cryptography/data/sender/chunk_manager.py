"""
Function Name: yield_chunks
Purpose: Divide a file into chunks of a given size and yield them one by one
Inputs:
    - path: Path to the file
    - CHUNK_SIZE: Size of each chunk in bytes
    - general_logfile_path
    - offset - From which byte to start yielding chunks
Outputs:
    - Yields tuples in the format (chunk_num, chunk_data)
"""
from pathlib import Path

def yield_chunks(path, CHUNK_SIZE, general_logfile_path, offset=0) :
    p = Path(path)

    if p.is_file():
        with open(p, 'rb') as f:
            chunk_num = 1
            while True:
                chunk_data = f.read(CHUNK_SIZE)
                if not chunk_data:
                    break
                if chunk_num>=offset :
                    yield (chunk_num, chunk_data)
                chunk_num += 1
    else:
        raise ValueError("Path must be a file")
