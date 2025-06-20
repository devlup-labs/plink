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
                
    elif p.is_dir():
        
        chunk_id = 1
        buffer = b""
        
        for file in p.rglob("*"):
            
            if file.is_file():
                with file.open("rb") as f:
                    while True:
                        chunk_part = f.read(CHUNK_SIZE)
                        if chunk_part == False:
                            break
                        buffer += chunk_part
                        
                        while len(buffer) >= CHUNK_SIZE:
                            
                            yield str(chunk_id), buffer[:CHUNK_SIZE]
                            buffer = buffer[CHUNK_SIZE:]
                            chunk_id += 1
            
        if buffer:
            yield str(chunk_id), buffer
            
    else:
        print("Give appropriate path")
    