import socket
import sys
import time
from utils.logging import LogType, log

def fc_to_rp(TypeOfNat, OurPort, TheirPort, TheirIP, TestData, general_logfile_path):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5)
    sock.bind(('', OurPort))

    # Encode data for sending
    data_bytes = TestData.encode()

    if TypeOfNat == 1:
        log("Initiating Restricted Cone Nat Behaviour", log_type=LogType.INFO, status="Success", general_logfile_path=general_logfile_path)
        sock.sendto(data_bytes, (TheirIP, TheirPort))
        log("Sent test data to their IP and port", log_type=LogType.INFO, status="Success", general_logfile_path=general_logfile_path)

        try:
            recv_data, addr = sock.recvfrom(1024)
            sender_ip, sender_port = addr
            log(f"Received data from {sender_ip}:{sender_port}", log_type=LogType.INFO, status="Success", general_logfile_path=general_logfile_path)

            # Validate
            if recv_data == data_bytes and sender_ip == TheirIP and sender_port == TheirPort:
                print("OK")
                # connection established
                log("Data received matches sent data and sender IP/Port", log_type=LogType.INFO, status="Success", general_logfile_path=general_logfile_path)
            else:
                log("Mismatch in data or sender!", log_type=LogType.ERROR, status="Failure", general_logfile_path=general_logfile_path)
        except socket.timeout:
            log("Timeout waiting for incoming data.", log_type=LogType.ERROR, status="Failure", general_logfile_path=general_logfile_path)

    elif TypeOfNat == 2:
        # Full Cone NAT behavior
        log("Initiating Full Cone Nat Behaviour", log_type=LogType.INFO, status="Success", general_logfile_path=general_logfile_path)
        try:
            recv_data, addr = sock.recvfrom(1024)
            sender_ip, sender_port = addr
            log(f"Received data from {sender_ip}:{sender_port}", log_type=LogType.INFO, status="Success", general_logfile_path=general_logfile_path)

            if recv_data == data_bytes and sender_ip == TheirIP and sender_port == TheirPort:
                # Send back the same data
                sock.sendto(data_bytes, (TheirIP, TheirPort))
                log("Sent back the received data to their IP and port", log_type=LogType.INFO, status="Success", general_logfile_path=general_logfile_path)
                print("OK")
                # connection established
            else:
                log("Mismatch in data or sender!", log_type=LogType.ERROR, status="Failure", general_logfile_path=general_logfile_path)
        except socket.timeout:
            log("Timeout waiting for incoming data.", log_type=LogType.ERROR, status="Failure", general_logfile_path=general_logfile_path)

    else:
        log("Unsupported NAT type specified.", log_type=LogType.ERROR, status="Failure", general_logfile_path=general_logfile_path)
    sock.close()
