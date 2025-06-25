'''Test file for compression.py'''

import pytest
from pathlib import Path
import zstandard as zstd
import shutil
import tarfile

from backend.cryptography.data.compression import compress_file

def decompress_file(compressed_path, decompressed_path):
    dctx = zstd.ZstdDecompressor()
    with open(compressed_path, 'rb') as compressed, open(decompressed_path, 'wb') as decompressed:
        dctx.copy_stream(compressed, decompressed)

def extract_tar(tar_path, extract_to):
    with tarfile.open(tar_path, 'r') as tar:
        tar.extractall(path=extract_to)

def test_compress_text_file(tmp_path):
    file = tmp_path/"sample.txt"
    file.write_text("This is a sample file for testing purpose")

    output_dir = tmp_path/"output"
    compressed_path = compress_file(file, output_dir)

    assert compressed_path.exists()
    assert compressed_path.suffix == ".zst"

    decompressed_path = tmp_path/"decompressed.txt"
    decompress_file(compressed_path, decompressed_path)

    assert decompressed_path.read_text() == "This is a sample file for testing purpose"

def test_compress_folder(tmp_path):
    folder = tmp_path/"sample_folder"
    folder.mkdir()
    (folder/"file1.txt").write_text("File 1")
    (folder/"file2.txt").write_text("File 2")

    output_dir = tmp_path/"output"
    compressed_path = compress_file(folder, output_dir)

    assert compressed_path.exists()
    assert compressed_path.suffix == ".zst"

    decompressed_tar = tmp_path/"decompressed.tar"
    decompress_file(compressed_path, decompressed_tar)

    extract_dir = tmp_path/"extracted"
    extract_tar(decompressed_tar, extract_dir)

    files = sorted([f.name for f in (extract_dir/"sample_folder").iterdir()])
    assert "file1.txt" in files
    assert "file2.txt" in files

def test_invalid_path_type(tmp_path):
    invalid_path = tmp_path/"invalid.txt"
    with pytest.raises(ValueError) as exc_info:
        compress_file(invalid_path, tmp_path)
            
    assert "Unsupported path type" in str(exc_info.value)

