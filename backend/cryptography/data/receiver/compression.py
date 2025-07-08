import os
import zstandard as zstd
import tarfile

from utils.logging import LogType, log

def decompress_final_chunk(final_chunk_file_path, output_dir, general_logfile_path):

    os.makedirs(output_dir, exist_ok=True)
    final_file_path = os.path.join(output_dir, os.path.basename(final_chunk_file_path).replace('.zstd', ''))
    log(f"Starting decompression of {final_file_path} to {output_dir}", LogType.INFO, "Decompression", general_logfile_path, True)
    # Decompress .zstd to .tar
    try:
        with open(final_chunk_file_path, 'rb') as compressed_file, open(final_file_path, 'wb') as final_file:
            dctx = zstd.ZstdDecompressor()
            dctx.copy_stream(compressed_file, final_file)
    except Exception as e:
        log(
            f"Error decompressing .zstd file : {e}",
            LogType.ERROR,
            "Failure",
            general_logfile_path,
            True
        )
        return

    # Delete the .zstd file after successful decompression
    try:
        os.remove(final_chunk_file_path)
    except OSError as e:
        log(
            f"Error deleting .zstd file: {e}",
            LogType.ERROR,
            "Failure",
            general_logfile_path,
            True
        )

    # You are left with a file without any extension

    # # Extract .tar file
    # try:
    #     with tarfile.open(final_file_path, 'r') as tar:
    #         tar.extractall(path=output_dir)
    # except Exception as e:
    #     log(
    #         f"Error extracting .tar file: {e}",
    #         LogType.ERROR,
    #         "Failure",
    #         general_logfile_path,
    #         True
    #     )
    #     return

    # # Delete the .tar file after extraction
    # try:
    #     os.remove(final_file_path)
    # except OSError as e:
    #     log(
    #         f"Error deleting .tar file: {e}",
    #         LogType.ERROR,
    #         "Failure",
    #         general_logfile_path,
    #         True
    #     )

    # log(
    #     f"Decompression and extraction complete. Output at: {output_dir}",
    #     LogType.INFO,
    #     "Success",
    #     general_logfile_path,
    #     True
    # )
