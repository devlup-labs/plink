from pathlib import Path

def divide_in_chunks(path, CHUNK_SIZE):
    
    p = Path(path)
    
    if p.is_file():
        
        with p.open("rb") as f:
            chunk_id = 1
            while True:
                chunk = f.read(CHUNK_SIZE)
                if chunk ==False:
                    break
                yield str(chunk_id), chunk
                chunk_id += 1
            
    else:
        print("Give appropriate path")
    