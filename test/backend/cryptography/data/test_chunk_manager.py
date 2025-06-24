'''Test file for chunk_manager.py'''

import pytest
from pathlib import Path

from backend.cryptography.data.chunk_manager import divide_in_chunks
from backend.cryptography.data.compression import compress_file

def test_chunk_manager_file(tmp_path):
    file = tmp_path/"sample.txt"
    file.write_text("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

    chunks = list(divide_in_chunks(file, 10))
    
    assert chunks[0][0] == 1
    assert chunks[0][1] == b"ABCDEFGHIJ"
    assert chunks[1][0] == 2
    assert chunks[1][1] == b"KLMNOPQRST"
    assert chunks[2][0] == 3
    assert chunks[2][1] == b"UVWXYZ"

def test_chunk_manager_folder(tmp_path):
    folder = tmp_path/"sample_folder"
    folder.mkdir()
    (folder/"file1.txt").write_text("File 1")
    (folder/"file2.txt").write_text("File 2")

    output_dir = tmp_path/"output"
    compressed_path = compress_file(folder, output_dir)

    chunks = list(divide_in_chunks(compressed_path, 5))

    assert all(isinstance(chunk[0], int) for chunk in chunks)
    assert all(isinstance(chunk[1], bytes) for chunk in chunks)

    total_data = b"".join(chunk[1] for chunk in chunks)

    with open(compressed_path, 'rb') as f:
        original_data = f.read()
    
    assert total_data == original_data

def test_chunk_smaller_than_file(tmp_path):
    file = tmp_path / "tiny.txt"
    file.write_text("abc")

    chunks = list(divide_in_chunks(file, 10))

    assert len(chunks) == 1
    assert chunks[0][0] == 1
    assert chunks[0][1] == b"abc"

def test_invalid_path(tmp_path):
    invalid_path = tmp_path/"invalid.txt"
    with pytest.raises(ValueError) as exc_info:
        list(divide_in_chunks(invalid_path, 1024))

    assert "Path must be a file" in str(exc_info.value)