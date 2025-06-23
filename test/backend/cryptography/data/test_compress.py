""" Test file for compress.py """

import pytest
from pathlib import Path
import shutil
import zstandard as zstd
from backend.cryptography.data.compress import compress_file

def test_compress_file(tmp_path):
    
    # creating temp files
    
    test_file = tmp_path / "testfile.txt"
    content = b"Hello world! This is some test data."
    test_file.write_bytes(content)

    output_dir = tmp_path / "out"
    compressed_path = compress_file(test_file, output_dir)
    compressed_path = Path(compressed_path)

    # checking if compressed file exists and if it has suffix as .zst
    
    assert compressed_path.exists()
    assert compressed_path.suffix == ".zst"

    # decompressing this ,zst file and checking is the content is the same as input file
    
    dctx = zstd.ZstdDecompressor()
    decompressed_path = tmp_path / "decompressed.txt"
    with compressed_path.open('rb') as comp, decompressed_path.open('wb') as out:
        dctx.copy_stream(comp, out)

    assert decompressed_path.read_bytes() == content


def test_compress_folder(tmp_path):
    
    # creating temp folder
    
    folder = tmp_path / "folder"
    folder.mkdir()
    (folder / "a.txt").write_text("file A")
    (folder / "b.txt").write_text("file B")

    output_dir = tmp_path / "out"
    compressed_path = compress_file(folder, output_dir)
    compressed_path = Path(compressed_path)
    
    
    # checking if compressed files exists and if it has suffix as .zst and .tar

    assert compressed_path.exists()
    assert compressed_path.suffixes == [".tar", ".zst"]

    # decompress .tar.zst to verify content
    
    dctx = zstd.ZstdDecompressor()
    tar_path = tmp_path / "folder.tar"
    with compressed_path.open("rb") as comp, tar_path.open("wb") as out_tar:
        dctx.copy_stream(comp, out_tar)

    extract_dir = tmp_path / "extracted"
    extract_dir.mkdir()
    shutil.unpack_archive(str(tar_path), extract_dir)

    extracted_files = sorted(f.name for f in (extract_dir / folder.name).iterdir())
    assert extracted_files == ["a.txt", "b.txt"]


def test_invalid_path(capsys, tmp_path):
    output_dir = tmp_path / "out"
    result = compress_file("non_existent_path", output_dir)
    captured = capsys.readouterr()
    
    assert "Invalid path" in captured.out
    assert result is None
