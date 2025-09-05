import sys
import os
import argparse
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import utilities
from utils.logging import log, LogType
from utils.link import generate_link, decrypt_link
from backend.networking.analyse_network import analyse_network
from backend.cryptography.utils.key_generation import GenKey

# Import cryptographic utilities
from cryptography.hazmat.primitives import serialization

# Import all available P2P strategies
from backend.networking.strategies.direct_connection import DirectConnection
from backend.networking.strategies.FC_to_FC import FullConeToFullConeNAT
from backend.networking.strategies.PRC_to_PRC import PortRestrictedToPortRestrictedNAT
from backend.networking.strategies.RC_to_PRC import RestrictedToPortRestrictedNAT

def choose_strategy(self_info, peer_info, self_private_key, peer_public_key, log_path, is_sender=True):
    """
    Selects the appropriate P2P strategy based on the network metadata of both peers.

    Args:
        self_info (dict): Local peer's network information
        peer_info (dict): Remote peer's network information
        self_private_key: Local peer's private key
        peer_public_key: Remote peer's public key
        log_path (str): Path to log file
        is_sender (bool): Whether this peer is the sender

    Returns:
        Strategy instance or None if no suitable strategy found
    """
    log("Analyzing network types to choose strategy", LogType.INFO, "Started", log_path)

    self_nat = self_info.get('nat_type', 'Unknown')
    peer_nat = peer_info.get('nat_type', 'Unknown')
    self_external_ip = self_info.get('external_ip', '')
    peer_external_ip = peer_info.get('external_ip', '')

    print(f"\n Network Analysis:")
    print(f"   Your NAT type: {self_nat}")
    print(f"   Peer's NAT type: {peer_nat}")
    print(f"   Your external IP: {self_external_ip}")
    print(f"   Peer's external IP: {peer_external_ip}")

    # Strategy 1: Same network detection (same external IP)
    if self_external_ip == peer_external_ip:
        print(" Strategy: Direct Connection (Same Network)")
        log("Using DirectConnection strategy - same network", LogType.INFO, "Success", log_path)
        return DirectConnection(self_info, peer_info, self_private_key, peer_public_key, log_path)

    # Strategy 2: Full Cone to Full Cone NAT
    if ('Full Cone' in self_nat or 'Open Internet' in self_nat) and \
       ('Full Cone' in peer_nat or 'Open Internet' in peer_nat):
        print(" Strategy: Full Cone to Full Cone NAT Traversal")
        log("Using FullConeToFullConeNAT strategy", LogType.INFO, "Success", log_path)
        return FullConeToFullConeNAT(self_info, peer_info, self_private_key, peer_public_key, log_path)

    # Strategy 3: Port Restricted to Port Restricted NAT
    if 'Port Restricted Cone' in self_nat and 'Port Restricted Cone' in peer_nat:
        print(" Strategy: Port Restricted to Port Restricted NAT Traversal")
        log("Using PortRestrictedToPortRestrictedNAT strategy", LogType.INFO, "Success", log_path)
        return PortRestrictedToPortRestrictedNAT(
            self_info, peer_info, self_private_key, peer_public_key,
            log_path, is_initiator=is_sender
        )

    # Strategy 4: Restricted Cone to Port Restricted (and vice versa)
    if ('Restricted Cone' in self_nat and 'Port Restricted Cone' in peer_nat) or \
       ('Port Restricted Cone' in self_nat and 'Restricted Cone' in peer_nat):
        print(" Strategy: Restricted/Port-Restricted NAT Traversal")
        log("Using RestrictedToPortRestrictedNAT strategy", LogType.INFO, "Success", log_path)
        return RestrictedToPortRestrictedNAT(self_info, peer_info, self_private_key, peer_public_key, log_path)

    # Strategy 5: Any NAT to Full Cone (fallback)
    if 'Full Cone' in self_nat or 'Full Cone' in peer_nat or \
       'Open Internet' in self_nat or 'Open Internet' in peer_nat:
        print(" Strategy: NAT to Full Cone (Fallback)")
        log("Using FullConeToFullConeNAT strategy as fallback", LogType.INFO, "Success", log_path)
        return FullConeToFullConeNAT(self_info, peer_info, self_private_key, peer_public_key, log_path)

    # Strategy 6: Generic fallback for unknown NAT types
    print(" Strategy: Generic NAT Traversal (Fallback)")
    log("Using DirectConnection as last resort fallback", LogType.WARNING, "Fallback", log_path)
    return DirectConnection(self_info, peer_info, self_private_key, peer_public_key, log_path)

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

    # Check file size
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

def sender_flow(file_path, log_path):
    """Handle the sender flow."""
    print("Starting plink sender...")
    log("Sender mode initiated", LogType.INFO, "Started", log_path)

    # Validate file
    if not validate_file_path(file_path):
        return False

    # Generate cryptographic keys
    print(" Generating encryption keys...")
    private_pem, public_pem = GenKey()
    private_key = serialization.load_pem_private_key(private_pem.encode(), password=None)
    log("Cryptographic keys generated", LogType.INFO, "Success", log_path)

    # Analyze network
    print(" Analyzing your network...")
    try:
        network_metadata = analyse_network(log_path)
        network_metadata['public_key'] = public_pem
        log("Network analysis completed", LogType.INFO, "Success", log_path)
    except Exception as e:
        print(f" Network analysis failed: {e}")
        log(f"Network analysis failed: {e}", LogType.ERROR, "Failure", log_path)
        return False

    # Generate and display link
    print("\n Generating your plink link...")
    try:
        my_link = generate_link(network_metadata)
        print("\n" + "="*80)
        print(" YOUR PLINK LINK (share this with the receiver):")
        print("="*80)
        print(my_link)
        print("="*80)
        log("Link generated successfully", LogType.INFO, "Success", log_path)
    except Exception as e:
        print(f" Failed to generate link: {e}")
        log(f"Link generation failed: {e}", LogType.ERROR, "Failure", log_path)
        return False

    # Get peer's link
    print("\n Waiting for receiver's plink link...")
    while True:
        peer_link = input("Enter the receiver's plink link: ").strip()
        if peer_link:
            try:
                peer_metadata = decrypt_link(peer_link)
                peer_public_key_pem = peer_metadata.get('public_key')
                if not peer_public_key_pem:
                    print("❌ Error: Peer's public key not found in link. Please check the link.")
                    continue

                peer_public_key = serialization.load_pem_public_key(peer_public_key_pem.encode())
                log("Peer link decrypted successfully", LogType.INFO, "Success", log_path)
                break

            except Exception as e:
                print(f" Invalid link format: {e}")
                print("Please enter a valid plink:// link")
                continue
        else:
            print("Please enter a link")

    # Choose and execute strategy
    print("\n Establishing connection...")
    strategy = choose_strategy(network_metadata, peer_metadata, private_key, peer_public_key, log_path, is_sender=True)

    if not strategy:
        print(" Could not establish a P2P connection for the given network configuration.")
        log("No suitable strategy found", LogType.ERROR, "Failure", log_path)
        return False

    try:
        print(" Starting file transfer...")
        strategy.send(file_path)
        print(" File transfer completed successfully!")
        log("File transfer completed successfully", LogType.INFO, "Success", log_path)
        return True

    except Exception as e:
        print(f" File transfer failed: {e}")
        log(f"File transfer failed: {e}", LogType.ERROR, "Failure", log_path)
        return False

def receiver_flow(output_dir, log_path):
    """Handle the receiver flow."""
    print(" Starting plink receiver...")
    log("Receiver mode initiated", LogType.INFO, "Started", log_path)

    # Validate output directory
    if not validate_output_dir(output_dir):
        return False

    # Generate cryptographic keys
    print(" Generating encryption keys...")
    private_pem, public_pem = GenKey()
    private_key = serialization.load_pem_private_key(private_pem.encode(), password=None)
    log("Cryptographic keys generated", LogType.INFO, "Success", log_path)

    # Analyze network
    print(" Analyzing your network...")
    try:
        network_metadata = analyse_network(log_path)
        network_metadata['public_key'] = public_pem
        log("Network analysis completed", LogType.INFO, "Success", log_path)
    except Exception as e:
        print(f" Network analysis failed: {e}")
        log(f"Network analysis failed: {e}", LogType.ERROR, "Failure", log_path)
        return False

    # Generate and display link
    print("\n Generating your plink link...")
    try:
        my_link = generate_link(network_metadata)
        print("\n" + "="*80)
        print(" YOUR PLINK LINK (share this with the sender):")
        print("="*80)
        print(my_link)
        print("="*80)
        log("Link generated successfully", LogType.INFO, "Success", log_path)
    except Exception as e:
        print(f"❌ Failed to generate link: {e}")
        log(f"Link generation failed: {e}", LogType.ERROR, "Failure", log_path)
        return False

    # Get peer's link
    print("\n Waiting for sender's plink link...")
    while True:
        peer_link = input("Enter the sender's plink link: ").strip()
        if peer_link:
            try:
                peer_metadata = decrypt_link(peer_link)
                peer_public_key_pem = peer_metadata.get('public_key')
                if not peer_public_key_pem:
                    print("❌ Error: Peer's public key not found in link. Please check the link.")
                    continue

                peer_public_key = serialization.load_pem_public_key(peer_public_key_pem.encode())
                log("Peer link decrypted successfully", LogType.INFO, "Success", log_path)
                break

            except Exception as e:
                print(f"❌ Invalid link format: {e}")
                print("Please enter a valid plink:// link")
                continue
        else:
            print("Please enter a link")

    # Choose and execute strategy
    print("\n Establishing connection...")
    strategy = choose_strategy(network_metadata, peer_metadata, private_key, peer_public_key, log_path, is_sender=False)

    if not strategy:
        print("❌ Could not establish a P2P connection for the given network configuration.")
        log("No suitable strategy found", LogType.ERROR, "Failure", log_path)
        return False

    try:
        print(" Waiting for incoming file...")
        strategy.recv(output_dir)
        print(f" File received successfully! Saved to: {output_dir}")
        log("File reception completed successfully", LogType.INFO, "Success", log_path)
        return True

    except Exception as e:
        print(f"❌ File reception failed: {e}")
        log(f"File reception failed: {e}", LogType.ERROR, "Failure", log_path)
        return False

def main():
    """Main entry point of the application."""
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

    # Sender command
    sender_parser = subparsers.add_parser('send', help='Send a file')
    sender_parser.add_argument('file_path', type=str, help='Path to the file to send')

    # Receiver command
    receiver_parser = subparsers.add_parser('receive', help='Receive a file')
    receiver_parser.add_argument('output_dir', type=str, nargs='?', default='.',
                               help='Directory to save the received file (default: current directory)')

    args = parser.parse_args()

    # Setup logging
    log_path = "app.log"
    log("Application started", LogType.INFO, "Started", log_path)
    print(" plink - Secure Peer-to-Peer File Transfer")
    print("=" * 50)

    try:
        if args.command == 'send':
            success = sender_flow(args.file_path, log_path)
        elif args.command == 'receive':
            success = receiver_flow(args.output_dir, log_path)

        if success:
            print("\n Transfer completed successfully! Exiting...")
            log("Application completed successfully", LogType.INFO, "Success", log_path)
            sys.exit(0)
        else:
            print("\n Transfer failed. Check the logs for details.")
            log("Application completed with errors", LogType.ERROR, "Failure", log_path)
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n  Transfer cancelled by user.")
        log("Application cancelled by user", LogType.WARNING, "Cancelled", log_path)
        sys.exit(1)
    except Exception as e:
        print(f"\n Unexpected error: {e}")
        log(f"Unexpected error: {e}", LogType.CRITICAL, "Failure", log_path)
        sys.exit(1)

if __name__ == '__main__':
    main()
