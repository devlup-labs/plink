""" Test file for test_metadata.py """

import pytest
from pathlib import Path
from backend.cryptography.data.metadata import retrieve_metadata

def test_metadata_file(tmp_path):
    
    # Create a test file
    
    test_file = tmp_path / "test.txt"
    content = b"A" * 1024  # 1 KB
    test_file.write_bytes(content)

    result = retrieve_metadata(test_file, CHUNK_SIZE=256)

    assert result["size"] == 1024
    assert result["total_chunks"] == 4
    
    #################################################
    
    # another test with 1 kb of data and 250 bytes of chucksize so chunk should be created as 4 chunks with 250 bytes and 1 chunk with 24 bytes
    
    test_file = tmp_path / "test.txt"
    content = b"A" * 1024  # 1 KB
    test_file.write_bytes(content)

    result = retrieve_metadata(test_file, CHUNK_SIZE=250)

    assert result["size"] == 1024
    assert result["total_chunks"] == 5
    


def test_metadata_folder(tmp_path):
    
    # Create a folder with 3 files (each 100 bytes)
    
    folder = tmp_path / "folder"
    folder.mkdir()
    for i in range(3):
        (folder / f"file_{i}.bin").write_bytes(b"x" * 100)

    result = retrieve_metadata(folder, CHUNK_SIZE=150)

    # 300 bytes total → ceil(300 / 150) = 2 chunks
    
    assert result["size"] == 300
    assert result["total_chunks"] == 2


def test_invalid_path(capsys):
    result = retrieve_metadata("non_existing_path", CHUNK_SIZE=512)
    captured = capsys.readouterr()

    assert "Invalid Path Provided" in captured.out
