import socket
import multiprocessing
from backend.cryptography.data.sender.chunk_manager import yield_chunks
from backend.cryptography.data.receiver.chunk_manager import collect_chunks, join_chunks
from utils.logging import log, LogType


# Send


def send_chunk(chunk_data, chunk_num, sender_port, receiver_ip, receiver_port):
    """
    Sends a single chunk from sender to receiver
    """
    try:
        # first 4 bytes with represent chunk number
        header = chunk_num.to_bytes(4, 'big')
        payload = header + chunk_data

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind(('', sender_port))
            sock.sendto(payload, (receiver_ip, receiver_port))
    except Exception as e:
        log(f"Failed to send chunk {chunk_num}: {e}", LogType.ERROR, "Failure", "", True)


def send_file_chunks(file_path, file_metadata, network_metadata,
                     receiver_local_ip, receiver_external_ip,
                     receiver_ports, general_logfile_path,
                     resume_from_chunk=1):
    """
    Send a file in chunks using 64 ports in parallel over UDP.
    """
    sender_external_ip = network_metadata.get("external_ip")
    sender_ports = network_metadata.get("open_ports", [])[:64]

    # Validate direct connection
    if sender_external_ip != receiver_external_ip:
        log("Connection is not direct - IPs differ.", LogType.ERROR, "Failure", general_logfile_path, True)
        return False

    if not receiver_local_ip or len(sender_ports) < 64 or len(receiver_ports) < 64:
        log("Missing receiver IP or insufficient ports.", LogType.ERROR, "Failure", general_logfile_path, True)
        return False

    log(f"Starting file transfer from chunk {resume_from_chunk}.", LogType.INFO, "Initiated", general_logfile_path, True)

    processes = []
    chunk_size = file_metadata["chunk_size"]

    for chunk_num, chunk_data in yield_chunks(file_path, chunk_size, general_logfile_path, offset=resume_from_chunk):
        index = (chunk_num - 1) % 64
        sender_port = sender_ports[index]
        receiver_port = receiver_ports[index]

        p = multiprocessing.Process(target=send_chunk,
                                    args=(chunk_data, chunk_num, sender_port, receiver_local_ip, receiver_port))
        p.start()
        processes.append(p)

        log(f"Dispatching chunk {chunk_num} from port {sender_port} to port {receiver_port}.",
            LogType.INFO, "In-Progress", general_logfile_path)

    for p in processes:
        p.join()

    log("File transfer completed successfully.", LogType.INFO, "Success", general_logfile_path, True)
    return True


# Receive

def receive_on_port(port, shared_dict, chunk_logfile_path, general_logfile_path, total_chunks, chunk_output_dir):
    """
    Listens on a specific port and stores received chunk in a shared dictionary and on disk.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', port))

    while True:
        try:
            data, _ = sock.recvfrom(65536)
            chunk_num = int.from_bytes(data[:4], 'big')
            chunk_data = data[4:]

            if chunk_num not in shared_dict:
                shared_dict[chunk_num] = chunk_data
                collect_chunks(chunk_logfile_path, general_logfile_path, chunk_data, chunk_output_dir, chunk_num)
        except Exception as e:
            log(f"Receive error on port {port}: {e}", LogType.ERROR, "Failure", general_logfile_path)

        if len(shared_dict) == total_chunks:
            break

    sock.close()


def send_success_to_all(sender_ip, sender_ports):
    """
    Sends SUCCESS message to all sender ports after transfer completion.
    """
    for port in sender_ports:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.sendto(b"SUCCESS", (sender_ip, port))
        except:
            continue


def receive_file_chunks(output_file_path, file_metadata, network_metadata,
                        sender_local_ip, sender_external_ip,
                        sender_ports, chunk_logfile_path,
                        chunk_output_dir, general_logfile_path):
    """
    Receives chunks in parallel over 64 ports
    """
    receiver_external_ip = network_metadata.get("external_ip")
    receiver_ports = network_metadata.get("open_ports", [])[:64]
    total_chunks = file_metadata.get("num_chunks")

    if receiver_external_ip != sender_external_ip:
        log("Connection is not direct - IPs differ.", LogType.ERROR, "Failure", general_logfile_path, True)
        return False

    if not sender_local_ip or len(receiver_ports) < 64 or len(sender_ports) < 64:
        log("Missing sender IP or insufficient ports.", LogType.ERROR, "Failure", general_logfile_path, True)
        return False

    log("Starting chunk reception.", LogType.INFO, "Initiated", general_logfile_path, True)

    manager = multiprocessing.Manager()
    shared_chunks = manager.dict()
    processes = []

    for port in receiver_ports:
        p = multiprocessing.Process(
            target=receive_on_port,
            args=(port, shared_chunks, chunk_logfile_path, general_logfile_path, total_chunks, chunk_output_dir)
        )
        p.start()
        processes.append(p)

    for p in processes:
        p.join()

    # Making the final file
    ordered_chunks = [shared_chunks[i + 1] for i in range(total_chunks)]
    join_chunks(output_file_path, ordered_chunks)

    send_success_to_all(sender_local_ip, sender_ports)

    log("File received and reassembled successfully.", LogType.INFO, "Success", general_logfile_path, True)
    return True
