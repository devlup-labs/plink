'''Test file for metadata.py'''

import pytest
from pathlib import Path
from math import ceil

from backend.cryptography.data.metadata import retrieve_metadata

def test_metadata_file(tmp_path):
    file = tmp_path/"sample.txt"
    file.write_text("This is sample file for testing purpose.")

    CHUNK_SIZE = 16
    result = retrieve_metadata(file, CHUNK_SIZE)

    assert result["size"] == 40
    assert result["total_chunks"] == 3

def test_metadata_folder(tmp_path):
    folder = tmp_path/"sample_folder"
    folder.mkdir()
    (folder/"file1.txt").write_text("Sample file 1")
    (folder/"file2.txt").write_text("Sample file 2")

    CHUNK_SIZE = 8
    result = retrieve_metadata(folder, CHUNK_SIZE)

    assert result["size"] == 26
    assert result["total_chunks"] == 4

def test_invalid_path(tmp_path):
    invalid_path = tmp_path/"invalid.txt"
    with pytest.raises(FileNotFoundError) as exc_info:
        retrieve_metadata(invalid_path, 1024)

    assert f"Path doesn't exists : {invalid_path}" in str(exc_info.value)