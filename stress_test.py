import os
import timeit
import time

# Stress test for various components of the backend
# Full file transfer stress test is at the bottom of the file
# Test logs are stored in "test_log.txt"
# Test file is "test.pdf" in the current directory
# Chunk logs are stored in "chunk_log.json"

#code to generate a test file of your size
def generate_test_file(size_in_kb):
    with open("test.pdf", 'wb') as f:
        f.write(os.urandom(size_in_kb * 1024))
# --------------------------------------------------------------------------------------------

# # Chunking stress test

# from backend.cryptography.data.receiver.chunk_manager import collect_chunks, join_chunks

# # Setup
# output_dir = "stress_chunks"
# chunk_log_path = os.path.join(output_dir, "chunk_log.json")
# general_log_path = os.path.join(output_dir, "general_log.txt")
# chunk_size = 8192  # 8 KB
# total_size = 1024 * 1024  # 5 MB of data
# original_data = b"ABCDE" * total_size

# # Prepare clean environment
# def setup_env():
#     os.makedirs(output_dir, exist_ok=True)
#     for f in os.listdir(output_dir):
#         os.remove(os.path.join(output_dir, f))

# # Wrapper to collect all chunks
# def run_collect_chunks():
#     setup_env()
#     j = 0
#     for i in range(0, len(original_data), chunk_size):
#         chunk = original_data[i:i+chunk_size]
#         collect_chunks(chunk_log_path, general_log_path, chunk, output_dir,j)
#         j += 1

# # Wrapper to only join (requires data already chunked)
# def run_join_chunks():
#     join_chunks(output_dir, chunk_log_path, general_log_path)

# # Run timeit

# collect_time = 0
# join_time = 0

# for _ in range(10):  # Run multiple times to get average
#     collect_time += timeit.timeit(run_collect_chunks, number=1)
#     join_time += timeit.timeit(run_join_chunks, number=1)

# print(f"Average time to collect chunks (5MB, 8KB/chunk): {collect_time / 10:.6f} seconds")
# print(f"Average time to join chunks             : {join_time / 10:.6f} seconds")
# --------------------------------------------------------------------------------------------

# # Chunking stress test

# from backend.cryptography.data.sender.chunk_manager import yield_chunks

# chunk_size = 8192  # 8 KB
# path = "test.pdf"  # Path to a large file
# general_logfile_path = "test_log.txt"  # Path to the log file
# offset = 0  # Start from the beginning

# def stress_test_yield_chunks():
#     chunk_generator = yield_chunks(path, chunk_size, general_logfile_path, offset)
#     for chunk_num, chunk_data in chunk_generator:
#         pass  
    

# # Run the stress test
# run_time = timeit.timeit(stress_test_yield_chunks, number=100)

# print("Stress test completed.")
# print(f"Average time per run : {run_time:.6f} seconds")

#--------------------------------------------------------------------------------------------

# # Compression and Decompression stress test

# from backend.cryptography.data.sender.compression import compress_file
# from backend.cryptography.data.receiver.compression import decompress_final_chunk

# def setup_env():
#     #if compressed_files directory exists, remove it
#     if os.path.exists("compressed_files"):
#         for f in os.listdir("compressed_files"):
#             os.remove(os.path.join("compressed_files", f))
#     if os.path.exists("decompressed_files"):
#         for f in os.listdir("decompressed_files"):
#             os.remove(os.path.join("decompressed_files", f))
#     # Create directories if they don't exist
#     os.makedirs("compressed_files", exist_ok=True)
#     os.makedirs("decompressed_files", exist_ok=True)
    

# def stress_test_compression():
#     path = "test.pdf"  # Path to a large file
#     output_dir = "compressed_files"  # Directory to store compressed files
#     general_logfile_path = "test_log.txt"  # Path to the log file
#     compress_file(path, output_dir, general_logfile_path)

# def stress_test_decompression():
#     compressed_path = "compressed_files/docusaurus-social-card.jpg.zstd"  # Path to the compressed file
#     output_dir = "decompressed_files"  # Directory to store decompressed files
#     general_logfile_path = "test_log.txt"  # Path to the log file
#     decompress_final_chunk(compressed_path, output_dir, general_logfile_path)

# collect_time = 0
# join_time = 0

# # Run the stress test for compression
# for _ in range(10):  # Run multiple times to get average
#     setup_env()  # Ensure a clean environment for each run
#     collect_time += timeit.timeit(stress_test_compression, number=1)
#     join_time += timeit.timeit(stress_test_decompression, number=1)

# print(f"Average time to compress file: {collect_time / 10:.6f} seconds")
# print(f"Average time to decompress file: {join_time / 10:.6f} seconds")


#--------------------------------------------------------------------------------------------

# # Network detection stress test

# from backend.networking.utils.network_utils import is_NAT_present, is_UPnP_present

# nat_time = 0
# upnp_time = 0



# def stress_test_nat_detection():
#     general_logfile_path = "test_log.txt"  # Path to the log file
#     nat_detected = is_NAT_present(general_logfile_path)

# def stress_test_upnp_detection():
#     general_logfile_path = "test_log.txt"  # Path to the log file
#     upnp_available = is_UPnP_present(general_logfile_path)

# # Run the stress test for network detection
# for _ in range(10):  # Run multiple times to get average
    
#     nat_time += timeit.timeit(stress_test_nat_detection, number=1)
#     upnp_time += timeit.timeit(stress_test_upnp_detection, number=1)

# print(f"Average time to detect NAT: {nat_time / 10:.6f} seconds")
# print(f"Average time to detect UPnP: {upnp_time / 10:.6f} seconds")
    

#--------------------------------------------------------------------------------------------

#full file transfer test

from backend.cryptography.data.sender.chunk_manager import yield_chunks
from backend.cryptography.data.receiver.chunk_manager import collect_chunks, join_chunks
from backend.cryptography.data.sender.compression import compress_file
from backend.cryptography.data.receiver.compression import decompress_final_chunk
from backend.cryptography.core.cipher import encryption, decryption

generate_test_file(1024 * 5)  # Generate a test file of 1 MB size

def setup_env():
    # Create a temporary directory for the test
    if not os.path.exists("compressed_files"):
        os.makedirs("compressed_files")
    if not os.path.exists("decompressed_files"):
        os.makedirs("decompressed_files")
    # Clear previous files if they exist
    for file in os.listdir("compressed_files"):
        os.remove(os.path.join("compressed_files", file))
    for file in os.listdir("decompressed_files"):
        os.remove(os.path.join("decompressed_files", file))


def stress_test_full_file_transfer():
    times1 = time.perf_counter()
    compressed_path = compress_file("test.pdf", "compressed_files", "test_log.txt")
    times2 = time.perf_counter()
    chunks = yield_chunks(compressed_path, 8192, "test_log.txt", 0)
    times3 = time.perf_counter()
    for chunk_num, chunk_data in chunks:
        with open(f"compressed_files/chunk_{chunk_num}.pchunk", "wb") as file:
            file.write(chunk_data)
        file.close()
    #now sending files to receiver
    times4 = time.perf_counter()
    for file in os.listdir("compressed_files"):
        if file.endswith(".pchunk"):
            with open(os.path.join("compressed_files", file), "rb") as f:
                chunk_data = f.read()
            collect_chunks("chunk_log.json", "test_log.txt", chunk_data, "decompressed_files", int(file.split('_')[1].split('.')[0]))
    times5 = time.perf_counter()
    for files in os.listdir("compressed_files"):
        os.remove(os.path.join("compressed_files", files))
    times6 = time.perf_counter()
    # Join all chunks into a final file
    final_file_path = join_chunks("decompressed_files", "chunk_log.json", "test_log.txt")
    times7 = time.perf_counter()
    # Decompress the final file
    decompress_final_chunk(final_file_path, "decompressed_files", "test_log.txt")
    times8 = time.perf_counter()
    print(f"Full file transfer completed in {times8 - times1:.6f} seconds")
    print(f"Compression time: {times2 - times1:.6f} seconds")
    print(f"Yield time: {times3 - times2:.6f} seconds")
    print(f"Writing chunks time: {times4 - times3:.6f} seconds")
    print(f"Collecting chunks time: {times5 - times4:.6f} seconds")
    print(f"removing chunks time: {times6 - times5:.6f} seconds")
    print(f"Joining chunks time: {times7 - times6:.6f} seconds")
    print(f"Decompression time: {times8 - times7:.6f} seconds")
    print(f"Decompression time: {times8 - times7:.6f} seconds")

full_time = 0
print("Starting full file transfer stress test...")
# Run the full file transfer stress test
for _ in range(50):  # Run multiple times to get average
    setup_env()  # Ensure a clean environment for each run
    stress_test_full_file_transfer()
    print("completed successfully run ", _ + 1)
# setup_env()  # Ensure a clean environment for each run
print(f"Average time for full file transfer (compression, chunking, transfer, decompression): {full_time / 10:.6f} seconds")

# --------------------------------------------------------------------------------------------
