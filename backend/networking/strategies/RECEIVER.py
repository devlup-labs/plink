import os
import socket
import json
from backend.cryptography.data.receiver.chunk_manager import collect_chunks_parallel, join_chunks
from backend.cryptography.data.receiver.compression import decompress_final_chunk

# Configuration
RECEIVER_IP = "0.0.0.0"
RECEIVER_PORT = 7000
SENDER_IP = "127.0.0.1"  # Change to sender's IP if needed
SENDER_PORT = 7001

CHUNK_OUTPUT_DIR = "received_chunks"
CHUNK_LOG_PATH = "received_chunk_log.json"
GENERAL_LOG_PATH = "receiver_log.txt"
DECOMPRESS_DIR = "decompressed_files"
CHUNK_SIZE = 8192
BATCH_SIZE = 100

def send_ack(sock, message):
    sock.sendto(message.encode(), (SENDER_IP, SENDER_PORT))

def receive_chunks():
    os.makedirs(CHUNK_OUTPUT_DIR, exist_ok=True)
    os.makedirs(DECOMPRESS_DIR, exist_ok=True)
    chunk_list = []
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((RECEIVER_IP, RECEIVER_PORT))
    print(f"Receiver listening on {RECEIVER_IP}:{RECEIVER_PORT}")

    # Receive chunks until 'END' message
    while True:
        data, addr = sock.recvfrom(CHUNK_SIZE + 256)
        if data == b'END':
            print("All chunks received.")
            break
        # Expecting: header + chunk_data, header format: [chunk_num]|filename|
        try:
            header_end = data.find(b"|")
            chunk_num = int(data[1:header_end])
            rest = data[header_end+1:]
            fname_end = rest.find(b"|")
            fname = rest[:fname_end].decode()
            chunk_data = rest[fname_end+1:]
        except Exception:
            print("Malformed chunk received, skipping.")
            continue

        chunk_path = os.path.join(CHUNK_OUTPUT_DIR, fname)
        with open(chunk_path, "wb") as f:
            f.write(chunk_data)
        chunk_list.append((chunk_data, chunk_num))
        # Send ACK to sender
        send_ack(sock, f"RECEIVED:{fname}")
        print(f"Received and saved chunk: {fname}")

    sock.close()
    return chunk_list

def main():
    # Step 1: Receive all chunks and ACK each
    chunk_list = receive_chunks()

    # Step 2: Collect chunks in parallel
    collect_chunks_parallel(chunk_list, CHUNK_LOG_PATH, GENERAL_LOG_PATH, CHUNK_OUTPUT_DIR)
    print("Chunks collected.")

    # Step 3: Join chunks
    final_file_path = join_chunks(CHUNK_OUTPUT_DIR, CHUNK_LOG_PATH, GENERAL_LOG_PATH, chunk_size=CHUNK_SIZE, batch_size=BATCH_SIZE)
    print("Chunks joined into:", final_file_path)

    # Step 4: Notify sender of success
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    send_ack(sock, "JOIN_SUCCESS")
    sock.close()
    print("Sent JOIN_SUCCESS to sender.")

    # Step 5: Delete previous chunk files
    for f in os.listdir(CHUNK_OUTPUT_DIR):
        os.remove(os.path.join(CHUNK_OUTPUT_DIR, f))
    print("Deleted chunk files.")

    # Step 6: Decompress final file
    decompress_final_chunk(final_file_path, DECOMPRESS_DIR, GENERAL_LOG_PATH)
    print("Decompression complete. Output in:", DECOMPRESS_DIR)

if __name__ == "__main__":
    main()