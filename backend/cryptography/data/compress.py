"""
Function Name: compress_file
Purpose: compress a file given file/folder path
Inputs: path
Outputs: output_path of output_file which compressed file of file/folder of which pth is given

"""
from pathlib import Path
import zstandard as zstd
import tarfile

def compress_file(path,output_dir):
    
    APP_COMPRESSED_DIR = Path(output_dir)
    APP_COMPRESSED_DIR.mkdir(parents=True, exist_ok=True)
    
    path = Path(path)
    cctx = zstd.ZstdCompressor(level=3)
    
    output_path = None
    
    if path.is_file():
        
        output_path = APP_COMPRESSED_DIR / (path.name + '.zst')
        with path.open('rb') as input_file, output_path.open('wb') as output_file :
            cctx.copy_stream(input_file,output_file)
            
    elif path.is_dir():
        
        # make temporary tar file
        
        temp_tar_path = APP_COMPRESSED_DIR / (path.name + '.tar')
        
        with tarfile.open(temp_tar_path, mode='w') as tar:
            tar.add(path, arcname=path.name)

        # compress tar file
        
        output_path = APP_COMPRESSED_DIR / (path.name + '.tar.zst')
        with temp_tar_path.open('rb') as input_file, output_path.open('wb') as output_file:
            cctx.copy_stream(input_file, output_file)

        # delete tar file
        
        temp_tar_path.unlink()
        
    else:
        print("Invalid path")
        
    return str(output_path) if output_path else None
    