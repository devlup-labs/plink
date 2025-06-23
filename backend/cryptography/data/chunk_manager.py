from pathlib import Path

def divide_in_chunks(path, CHUNK_SIZE):
    p = Path(path)

    if p.is_file():
        with open(p, 'rb') as f:
            chunk_num = 1
            while True:
                chunk_data = f.read(CHUNK_SIZE)
                if not chunk_data:
                    break
                yield (chunk_num, chunk_data)
                chunk_num += 1
            
    else:
        raise ValueError("Path must be a file")
