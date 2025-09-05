#!/usr/bin/env python3
import sys
import os
import argparse
from pathlib import Path
import datetime

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import utilities
from utils.logging import log, LogType
from utils.link import generate_link, decrypt_link
from utils.plink_file import create_plink_file, read_plink_file
from backend.networking.analyze_network import NetworkAnalyzer
from backend.cryptography.utils.key_generation import GenKey

# Import cryptographic utilities
from cryptography.hazmat.primitives import serialization

# Import all available P2P strategies
from backend.networking.strategies.direct_connection import DirectConnection
from backend.networking.strategies.FC_to_FC import FullConeToFullConeNAT
from backend.networking.strategies.FC_to_RC import FullConeToRestrictedConeNAT
from backend.networking.strategies.FC_to_PRC import FullConeToPortRestrictedNAT
from backend.networking.strategies.FC_to_SYM import FullConeToSymmetricNAT
from backend.networking.strategies.RC_to_RC import RestrictedToRestrictedNAT
from backend.networking.strategies.RC_to_PRC import RestrictedToPortRestrictedNAT
# from backend.networking.strategies.RC_to_SYM import RestrictedToSymmetricNAT
from backend.networking.strategies.PRC_to_PRC import PortRestrictedToPortRestrictedNAT


def choose_strategy(self_info, peer_info, self_private_key, peer_public_key, log_path, is_sender=True):
    """
    Selects the appropriate P2P strategy based on the network metadata of both peers.
    """
    log("Analyzing network types to choose strategy", LogType.INFO, "Started", log_path)

    self_nat = self_info.get('nat_type', 'Unknown')
    peer_nat = peer_info.get('nat_type', 'Unknown')
    self_external_ip = self_info.get('external_ip', '')
    peer_external_ip = peer_info.get('external_ip', '')

    print(f"\nNetwork Analysis:")
    print(f"    Your NAT type: {self_nat}")
    print(f"    Peer's NAT type: {peer_nat}")
    print(f"    Your external IP: {self_external_ip}")
    print(f"    Peer's external IP: {peer_external_ip}")

    # Strategy 1: Same network detection (highest priority)
    if self_external_ip == peer_external_ip and self_external_ip:
        print("Strategy: Direct Connection (Same Network)")
        log("Using DirectConnection strategy - same network", LogType.INFO, "Success", log_path)
        return DirectConnection(self_info, peer_info, self_private_key, peer_public_key, log_path)

    def get_nat_category(nat_string):
        if 'Full Cone' in nat_string or 'Open Internet' in nat_string:
            return 'fc'
        if 'Restricted Cone' in nat_string:
            return 'rc'
        if 'Port Restricted Cone' in nat_string:
            return 'prc'
        if 'Symmetric' in nat_string:
            return 'sym'
        return 'unknown'

    self_cat = get_nat_category(self_nat)
    peer_cat = get_nat_category(peer_nat)

    nat_pair_key = tuple(sorted((self_cat, peer_cat)))

    strategy_map = {
        ('fc', 'fc'): ('Full Cone to Full Cone NAT Traversal', FullConeToFullConeNAT),
        ('fc', 'prc'): ('Full Cone to Port-Restricted NAT Traversal', FullConeToPortRestrictedNAT),
        ('fc', 'rc'): ('Full Cone to Restricted Cone NAT Traversal', FullConeToRestrictedConeNAT),
        ('fc', 'sym'): ('Full Cone to Symmetric NAT Traversal', FullConeToSymmetricNAT),
        ('prc', 'prc'): ('Port Restricted to Port Restricted NAT Traversal', PortRestrictedToPortRestrictedNAT),
        ('prc', 'rc'): ('Restricted Cone to Port-Restricted NAT Traversal', RestrictedToPortRestrictedNAT),
        ('rc', 'rc'): ('Restricted Cone to Restricted Cone NAT Traversal', RestrictedToRestrictedNAT),
        # ('rc', 'sym'): ('Restricted Cone to Symmetric NAT Traversal', RestrictedToSymmetricNAT),
    }

    if nat_pair_key in strategy_map:
        (strategy_name, strategy_class) = strategy_map[nat_pair_key]
        print(f"Strategy: {strategy_name}")
        log(f"Using {strategy_class.__name__} strategy", LogType.INFO, "Success", log_path)

        if strategy_class in [PortRestrictedToPortRestrictedNAT]:
            return strategy_class(
                self_info, peer_info, self_private_key, peer_public_key,
                log_path, is_initiator=is_sender
            )
        else:
            return strategy_class(self_info, peer_info, self_private_key, peer_public_key, log_path)

    if 'sym' in nat_pair_key or 'unknown' in nat_pair_key:
        print("Warning: No specific strategy for this NAT combination. Attempting fallback.")
        log(f"Unsupported or unknown NAT combination: {nat_pair_key}. Attempting fallback.", LogType.WARNING, "Fallback", log_path)

    print("Strategy: Generic NAT Traversal (Fallback)")
    log("Using FullConeToFullConeNAT as fallback", LogType.WARNING, "Fallback", log_path)
    return FullConeToFullConeNAT(self_info, peer_info, self_private_key, peer_public_key, log_path)


# ----------------- Helper utils for main flow -----------------

def validate_file_path(file_path):
    """Validate that the file exists and is readable."""
    path = Path(file_path)
    if not path.exists():
        print(f"Error: File '{file_path}' does not exist.")
        return False
    if not path.is_file():
        print(f"Error: '{file_path}' is not a file.")
        return False
    if not os.access(file_path, os.R_OK):
        print(f"Error: Cannot read file '{file_path}'. Check permissions.")
        return False

    size_mb = path.stat().st_size / (1024 * 1024)
    print(f"File size: {size_mb:.2f} MB")

    return True


def validate_output_dir(output_dir):
    """Validate and create output directory if needed."""
    path = Path(output_dir)

    try:
        path.mkdir(parents=True, exist_ok=True)
        if not os.access(path, os.W_OK):
            print(f"Error: Cannot write to directory '{output_dir}'. Check permissions.")
            return False
        return True
    except Exception as e:
        print(f"Error: Cannot create/access directory '{output_dir}': {e}")
        return False


def _write_text_file(content: str, prefix: str, ext: str):
    """Write `content` to a timestamped file and return path."""
    ts = datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    filename = f"{prefix}_{ts}.{ext}"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    return os.path.abspath(filename)


# ----------------- Sender and Receiver flows -----------------

def sender_flow(file_path, log_path):
    """Handle the sender flow with .plink file key exchange process.

    This flow follows the requested sequence:
     1) Validate file to send
     2) Generate key pair and write .plink public-key file (tell user to share it)
     3) Ask user to provide receiver's .plink file (path)
     4) Analyze network
     5) Encrypt network metadata with receiver's public key and write a link file (binary/text)
     6) Ask user to provide receiver's encrypted link file (path) - read & decrypt
     7) Choose strategy and start sending
    """
    print("\nStarting plink sender...")
    log("Sender mode initiated", LogType.INFO, "Started", log_path)

    if not validate_file_path(file_path):
        return False

    # Step 1: Generate cryptographic keys
    print("\nGenerating encryption keys...")
    try:
        private_pem, public_pem = GenKey()
        private_key = serialization.load_pem_private_key(private_pem.encode(), password=None)
        log("Cryptographic keys generated", LogType.INFO, "Success", log_path)
    except Exception as e:
        print(f"Key generation failed: {e}")
        log(f"Key generation failed: {e}", LogType.ERROR, "Failure", log_path)
        return False

    # Step 2: Create .plink file with public key
    print("\nCreating your .plink key file...")
    try:
        plink_file_path = create_plink_file(public_pem, "sender", log_path)
        print("\n" + "="*80)
        print("YOUR .PLINK KEY FILE CREATED:")
        print("="*80)
        print(f"File location: {os.path.abspath(plink_file_path)}")
        print("="*80)
        print("\nPlease share this .plink file with the receiver.")
        print("You will also need to get the receiver's .plink file (path).\n")
        log(".plink file created successfully", LogType.INFO, "Success", log_path)
    except Exception as e:
        print(f"Failed to create .plink file: {e}")
        log(f".plink file creation failed: {e}", LogType.ERROR, "Failure", log_path)
        return False

    # Step 3: Get peer's .plink file (path)
    while True:
        print("Please provide the receiver's .plink file (path)...")
        peer_plink_path = input("Enter the path to receiver's .plink file: ").strip()

        if peer_plink_path and os.path.exists(peer_plink_path):
            try:
                peer_public_key_pem = read_plink_file(peer_plink_path, log_path)
                peer_public_key = serialization.load_pem_public_key(peer_public_key_pem.encode())
                print("Receiver's public key loaded successfully from .plink file!")
                log("Peer's public key loaded from .plink file", LogType.INFO, "Success", log_path)
                break
            except Exception as e:
                print(f"Invalid .plink file: {e}")
                print("Please provide a valid .plink file")
                continue
        else:
            print("File not found. Please enter a valid path to the receiver's .plink file")

    # Step 4: Analyze network
    print("\nAnalyzing your network...")
    try:
        analyzer = NetworkAnalyzer()
        network_metadata = analyzer.analyze_network()
        print(f"Network analysis completed. Found {len(network_metadata.get('open_ports', []))} available ports.")
        log("Network analysis completed", LogType.INFO, "Success", log_path)
    except Exception as e:
        print(f"Network analysis failed: {e}")
        log(f"Network analysis failed: {e}", LogType.ERROR, "Failure", log_path)
        return False

    # Step 5: Generate encrypted link (string) and write to a file for sharing
    print("\nGenerating your encrypted plink link and writing to file...")
    try:
        my_link = generate_link(network_metadata, peer_public_key)
        link_file_path = _write_text_file(my_link, "plink_link_sender", "plinklink")
        print("\n" + "="*80)
        print("YOUR ENCRYPTED PLINK LINK FILE (share this with the receiver):")
        print("="*80)
        print(f"File location: {link_file_path}")
        print("="*80)
        print("\nPlease give this file to the receiver and then ask them to give you their encrypted link file (path).\n")
        log("Link file created successfully", LogType.INFO, "Success", log_path)
    except Exception as e:
        print(f"Failed to generate link file: {e}")
        log(f"Link generation failed: {e}", LogType.ERROR, "Failure", log_path)
        return False

    # Step 6: Get peer's encrypted link file (path) and decrypt
    while True:
        print("Waiting for receiver's encrypted link file (path)...")
        peer_link_file = input("Enter the path to the receiver's encrypted link file: ").strip()

        if peer_link_file and os.path.exists(peer_link_file):
            try:
                with open(peer_link_file, 'r', encoding='utf-8') as f:
                    peer_link_content = f.read().strip()

                peer_metadata = decrypt_link(peer_link_content, private_key)
                print("Receiver's link decrypted successfully!")
                log("Peer link decrypted successfully", LogType.INFO, "Success", log_path)
                break
            except Exception as e:
                print(f"Invalid or undecryptable link file: {e}")
                print("Please provide a valid encrypted link file from the receiver.")
                continue
        else:
            print("File not found. Please enter a valid path to the receiver's encrypted link file")

    # Step 7: Choose and execute strategy
    print("\nEstablishing connection...")
    strategy = choose_strategy(network_metadata, peer_metadata, private_key, peer_public_key, log_path, is_sender=True)

    if not strategy:
        print("Could not establish a P2P connection for the given network configuration.")
        log("No suitable strategy found", LogType.ERROR, "Failure", log_path)
        return False

    try:
        print("\nStarting file transfer...")
        strategy.send(file_path)
        print("File transfer completed successfully!")
        log("File transfer completed successfully", LogType.INFO, "Success", log_path)
        return True

    except Exception as e:
        print(f"File transfer failed: {e}")
        log(f"File transfer failed: {e}", LogType.ERROR, "Failure", log_path)
        return False


def receiver_flow(output_dir, log_path):
    """Handle the receiver flow with .plink file key exchange process.

    Mirror of the sender flow but waits to receive the file.
    """
    print("\nStarting plink receiver...")
    log("Receiver mode initiated", LogType.INFO, "Started", log_path)

    if not validate_output_dir(output_dir):
        return False
    print(f"Output directory: {os.path.abspath(output_dir)}")

    # Step 1: Generate cryptographic keys
    print("\nGenerating encryption keys...")
    try:
        private_pem, public_pem = GenKey()
        private_key = serialization.load_pem_private_key(private_pem.encode(), password=None)
        log("Cryptographic keys generated", LogType.INFO, "Success", log_path)
    except Exception as e:
        print(f"Key generation failed: {e}")
        log(f"Key generation failed: {e}", LogType.ERROR, "Failure", log_path)
        return False

    # Step 2: Create .plink file with public key
    print("\nCreating your .plink key file...")
    try:
        plink_file_path = create_plink_file(public_pem, "receiver", log_path)
        print("\n" + "="*80)
        print("YOUR .PLINK KEY FILE CREATED:")
        print("="*80)
        print(f"File location: {os.path.abspath(plink_file_path)}")
        print("="*80)
        print("\nPlease share this .plink file with the sender.")
        print("You will also need to get the sender's .plink file (path).\n")
        log(".plink file created successfully", LogType.INFO, "Success", log_path)
    except Exception as e:
        print(f"Failed to create .plink file: {e}")
        log(f".plink file creation failed: {e}", LogType.ERROR, "Failure", log_path)
        return False

    # Step 3: Get peer's .plink file (path)
    while True:
        print("Please provide the sender's .plink file (path)...")
        peer_plink_path = input("Enter the path to sender's .plink file: ").strip()

        if peer_plink_path and os.path.exists(peer_plink_path):
            try:
                peer_public_key_pem = read_plink_file(peer_plink_path, log_path)
                peer_public_key = serialization.load_pem_public_key(peer_public_key_pem.encode())
                print("Sender's public key loaded successfully from .plink file!")
                log("Peer's public key loaded from .plink file", LogType.INFO, "Success", log_path)
                break
            except Exception as e:
                print(f"Invalid .plink file: {e}")
                print("Please provide a valid .plink file")
                continue
        else:
            print("File not found. Please enter a valid path to the sender's .plink file")

    # Step 4: Analyze network
    print("\nAnalyzing your network...")
    try:
        analyzer = NetworkAnalyzer()
        network_metadata = analyzer.analyze_network()
        print(f"Network analysis completed. Found {len(network_metadata.get('open_ports', []))} available ports.")
        log("Network analysis completed", LogType.INFO, "Success", log_path)
    except Exception as e:
        print(f"Network analysis failed: {e}")
        log(f"Network analysis failed: {e}", LogType.ERROR, "Failure", log_path)
        return False

    # Step 5: Generate encrypted link and write to file
    print("\nGenerating your encrypted plink link and writing to file...")
    try:
        my_link = generate_link(network_metadata, peer_public_key)
        link_file_path = _write_text_file(my_link, "plink_link_receiver", "plinklink")
        print("\n" + "="*80)
        print("YOUR ENCRYPTED PLINK LINK FILE (share this with the sender):")
        print("="*80)
        print(f"File location: {link_file_path}")
        print("="*80)
        print("\nPlease give this file to the sender and then ask them to give you their encrypted link file (path).\n")
        log("Link file created successfully", LogType.INFO, "Success", log_path)
    except Exception as e:
        print(f"Failed to generate link file: {e}")
        log(f"Link generation failed: {e}", LogType.ERROR, "Failure", log_path)
        return False

    # Step 6: Get peer's encrypted link file and decrypt
    while True:
        print("Waiting for sender's encrypted link file (path)...")
        peer_link_file = input("Enter the path to the sender's encrypted link file: ").strip()

        if peer_link_file and os.path.exists(peer_link_file):
            try:
                with open(peer_link_file, 'r', encoding='utf-8') as f:
                    peer_link_content = f.read().strip()

                peer_metadata = decrypt_link(peer_link_content, private_key)
                print("Sender's link decrypted successfully!")
                log("Peer link decrypted successfully", LogType.INFO, "Success", log_path)
                break
            except Exception as e:
                print(f"Invalid or undecryptable link file: {e}")
                print("Please provide a valid encrypted link file from the sender.")
                continue
        else:
            print("File not found. Please enter a valid path to the sender's encrypted link file")

    # Step 7: Choose and execute strategy
    print("\nEstablishing connection...")
    strategy = choose_strategy(network_metadata, peer_metadata, private_key, peer_public_key, log_path, is_sender=False)

    if not strategy:
        print("Could not establish a P2P connection for the given network configuration.")
        log("No suitable strategy found", LogType.ERROR, "Failure", log_path)
        return False

    try:
        print("\nWaiting for incoming file...")
        strategy.recv(output_dir)
        print(f"File received successfully! Saved to: {os.path.abspath(output_dir)}")
        log("File reception completed successfully", LogType.INFO, "Success", log_path)
        return True

    except Exception as e:
        print(f"File reception failed: {e}")
        log(f"File reception failed: {e}", LogType.ERROR, "Failure", log_path)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="plink - Secure Peer-to-Peer File Transfer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 main.py send /path/to/file.txt
  python3 main.py receive /path/to/output/directory
  python3 main.py receive  # Uses current directory
        """
    )

    subparsers = parser.add_subparsers(dest='command', required=True, help='Commands')

    sender_parser = subparsers.add_parser('send', help='Send a file')
    sender_parser.add_argument('file_path', type=str, help='Path to the file to send')

    receiver_parser = subparsers.add_parser('receive', help='Receive a file')
    receiver_parser.add_argument('output_dir', type=str, nargs='?', default='.',
                                 help='Directory to save the received file (default: current directory)')

    args = parser.parse_args()

    log_path = "app.log"
    log("Application started", LogType.INFO, "Started", log_path)
    print("plink - Secure Peer-to-Peer File Transfer")
    print("=" * 50)

    try:
        if args.command == 'send':
            success = sender_flow(args.file_path, log_path)
        elif args.command == 'receive':
            success = receiver_flow(args.output_dir, log_path)

        if success:
            print("\nTransfer completed successfully! Exiting...")
            log("Application completed successfully", LogType.INFO, "Success", log_path)
            sys.exit(0)
        else:
            print("\nTransfer failed. Check the logs for details.")
            log("Application completed with errors", LogType.ERROR, "Failure", log_path)
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\nTransfer cancelled by user.")
        log("Application cancelled by user", LogType.WARNING, "Cancelled", log_path)
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        log(f"Unexpected error: {e}", LogType.CRITICAL, "Failure", log_path)
        sys.exit(1)


if __name__ == '__main__':
    main()
