import multiprocessing
import os
import time
from backend.networking.strategies.PRC_to_PRC import FullConeToFullConeNAT

SENDER_INFO = {
    "external_ip": "59.145.92.85",
    "open_ports": [5000, 5001, 5002, 5003]
}

RECEIVER_INFO = {
    "external_ip": "59.145.92.84",
    "open_ports": [6000, 6001, 6002, 6003]
}

# Logging path
LOG_PATH = "test_transfer.log"

# Dummy file to send
TEST_FILE = "test_data.txt"

def generate_dummy_file():
    with open(TEST_FILE, "w") as f:
        f.write("This is a test file.\n" * 100)

def receiver_process():
    # Receiver keypair
    priv_key, pub_key = "172.31.118.189", "59.145.92.84"
    
    # Create receiver session
    receiver = FullConeToFullConeNAT(
        self_info=RECEIVER_INFO,
        peer_info=SENDER_INFO,
        self_private_key=priv_key,
        peer_public_key=None,  # We don't need to encrypt anything to sender
        log_path=LOG_PATH
    )

    receiver.recv(output_path="received_data.txt")

def sender_process(sender_private_key, receiver_public_key):
    # Create sender session
    sender = FullConeToFullConeNAT(
        self_info=SENDER_INFO,
        peer_info=RECEIVER_INFO,
        self_private_key=sender_private_key,
        peer_public_key=receiver_public_key,
        log_path=LOG_PATH
    )

    sender.send(filepath=TEST_FILE)

def run_test():
    generate_dummy_file()

    # Generate key pairs for sender and receiver
    sender_priv, sender_pub = "172.31.112.232", "59.145.92.85"
    receiver_priv, receiver_pub = "172.31.118.189", "59.145.92.84"

    # Receiver starts first to listen
    receiver = multiprocessing.Process(target=receiver_process)
    receiver.start()

    time.sleep(2)  # Give receiver time to bind sockets

    sender = multiprocessing.Process(target=sender_process, args=(sender_priv, receiver_pub))
    sender.start()

    sender.join()
    receiver.join()

    # Check if the file was transferred correctly
    if os.path.exists("received_data.txt"):
        with open("received_data.txt", "r") as f:
            content = f.read()
        if "This is a test file." in content:
            print("✅ File transferred successfully!")
        else:
            print("❌ File content mismatch.")
    else:
        print("❌ File was not received.")

if __name__ == "__main__":
    run_test()
