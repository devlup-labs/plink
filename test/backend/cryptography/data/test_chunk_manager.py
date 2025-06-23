""" Test file for chunk_manager.py """

import pytest
from pathlib import Path
from backend.cryptography.data.chunk_manager import divide_in_chunks

def test_divide_in_chunks_file(tmp_path):
    
    # Create a test file
    
    test_file = tmp_path / "sample.txt"
    content = b"ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    test_file.write_bytes(content)

    # Define chunk size
    
    chunk_size = 5

    # Collect chunks
    
    chunks = list(divide_in_chunks(str(test_file), chunk_size))

    # Expected number of chunks
    
    expected_chunks = [(str(i + 1), content[i * chunk_size:(i + 1) * chunk_size])
                       for i in range((len(content) + chunk_size - 1) // chunk_size)]

    assert chunks == expected_chunks
    assert len(chunks) == 6
    assert chunks[0] == ('1', b'ABCDE')
    assert chunks[-1] == ('6', b'Z')

def test_divide_in_chunks_non_file(tmp_path, capsys):
    test_dir = tmp_path / "folder"
    test_dir.mkdir()

    result = list(divide_in_chunks(str(test_dir), 10))

    # Function should print error and yield nothing
    
    captured = capsys.readouterr()
    assert "Give appropriate path" in captured.out
    assert result == []
