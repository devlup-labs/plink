import sys
import os
import argparse
from cryptography.hazmat.primitives import serialization

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from utils.link import generate_link, decrypt_link
from backend.networking.utils.network_utils import get_network_details
from backend.cryptography.utils.key_generation import GenKey

# Import all available strategies
from backend.networking.strategies.direct_connection import DirectConnection
from backend.networking.strategies.FC_to_FC import FullConeToFullConeNAT
from backend.networking.strategies.FC_to_RC import FullConeToRestrictedConeNAT
from backend.networking.strategies.FC_to_SYM import FullConeToSymmetricNAT
from backend.networking.strategies.PRC_to_PRC import PortRestrictedToPortRestrictedNAT
from backend.networking.strategies.RC_to_PRC import RestrictedToPortRestrictedNAT
from backend.networking.strategies.RC_to_SYM import RC_to_SC
from backend.networking.strategies.RC_to_RC import RestrictedToRestrictedNAT


def choose_strategy(self_info, peer_info, self_private_key, peer_public_key, log_path, file_path=None):
    """
    Selects the appropriate P2P strategy based on the network metadata of both peers.
    """
    self_nat = self_info.get('nat_type', 'Unknown')
    peer_nat = peer_info.get('nat_type', 'Unknown')

    print(f"Your NAT type: {self_nat}, Peer's NAT type: {peer_nat}")

    # Strategy 1: Direct Connection (Same Network)
    if self_info['external_ip'] == peer_info['external_ip']:
        print("Strategy: Direct Connection (Same Network)")
        return DirectConnection(self_info, peer_info, self_private_key, peer_public_key, log_path)

    # Strategy 2: Full Cone to Full Cone
    if 'Full Cone' in self_nat and 'Full Cone' in peer_nat:
        print("Strategy: Full Cone to Full Cone NAT Traversal")
        return FullConeToFullConeNAT(self_info, peer_info, self_private_key, peer_public_key, log_path)

    # Strategy 3: Full Cone to Restricted Cone (and vice-versa)
    if 'Full Cone' in self_nat and 'Restricted Cone' in peer_nat:
        print("Strategy: Full Cone to Restricted Cone NAT Traversal")
        return FullConeToRestrictedConeNAT(self_info, peer_info, self_private_key, peer_public_key, log_path)
    if 'Restricted Cone' in self_nat and 'Full Cone' in peer_nat:
        print("Strategy: Restricted Cone to Full Cone NAT Traversal")
        # Can reuse the same class, roles are symmetrical for this strategy
        return FullConeToRestrictedConeNAT(self_info, peer_info, self_private_key, peer_public_key, log_path)

    # Strategy 4: Restricted Cone to Restricted Cone
    if 'Restricted Cone' in self_nat and 'Restricted Cone' in peer_nat:
        print("Strategy: Restricted Cone to Restricted Cone NAT Traversal")
        return RestrictedToRestrictedNAT(self_info, peer_info, self_private_key, peer_public_key, log_path)

    # Strategy 5: Port Restricted to Port Restricted
    if 'Port Restricted Cone' in self_nat and 'Port Restricted Cone' in peer_nat:
        print("Strategy: Port Restricted to Port Restricted NAT Traversal")
        return PortRestrictedToPortRestrictedNAT(self_info, peer_info, self_private_key, peer_public_key, log_path)

    # Strategy 6: Restricted Cone to Port Restricted Cone (and vice-versa)
    if 'Restricted Cone' in self_nat and 'Port Restricted Cone' in peer_nat:
        print("Strategy: Restricted Cone to Port Restricted Cone NAT Traversal")
        return RestrictedToPortRestrictedNAT(self_info, peer_info, self_private_key, peer_public_key, log_path)
    if 'Port Restricted Cone' in self_nat and 'Restricted Cone' in peer_nat:
        print("Strategy: Port Restricted Cone to Restricted Cone NAT Traversal")
        return RestrictedToPortRestrictedNAT(peer_info, self_info, self_private_key, peer_public_key, log_path) # Swapped for role reversal

    # Strategy 7: Symmetric NAT involved
    if 'Symmetric' in self_nat and 'Full Cone' in peer_nat:
         print("Strategy: Symmetric to Full Cone NAT Traversal")
         return SymmetricToFullConeNAT(self_info, peer_info) # Note: Keys and log path need to be added
    if 'Full Cone' in self_nat and 'Symmetric' in peer_nat:
         print("Strategy: Full Cone to Symmetric NAT Traversal")
         return FullConeToSymmetricNAT(self_info, peer_info)

    if 'Symmetric' in self_nat and 'Restricted Cone' in peer_nat:
        print("Strategy: Symmetric to Restricted Cone NAT Traversal")
        return SC_to_RC(self_info, peer_info)
    if 'Restricted Cone' in self_nat and 'Symmetric' in peer_nat:
        print("Strategy: Restricted Cone to Symmetric NAT Traversal")
        return RC_to_SC(self_info, peer_info)


    print("No direct P2P strategy found for this NAT combination. Falling back to relay (not implemented).")
    return None

def main():
    parser = argparse.ArgumentParser(description="plink - Peer-to-Peer File Transfer")
    subparsers = parser.add_subparsers(dest='command', required=True)

    # Sender command
    sender_parser = subparsers.add_parser('send', help='Send a file')
    sender_parser.add_argument('file_path', type=str, help='Path to the file to send')

    # Receiver command
    receiver_parser = subparsers.add_parser('receive', help='Receive a file')
    receiver_parser.add_argument('output_dir', type=str, nargs='?', default='.', help='Directory to save the received file')

    args = parser.parse_args()

    # Generate keys
    private_pem, public_pem = GenKey()
    private_key = serialization.load_pem_private_key(private_pem.encode(), password=None)

    # Get network details
    print("Analyzing your network...")
    network_metadata = get_network_details('app.log')
    network_metadata['public_key'] = public_pem

    # Generate and display the link
    my_link = generate_link(network_metadata)
    print("\nYour plink link (share with the other person):")
    print(my_link)

    # Get the other person's link
    peer_link = input("\nEnter the other person's plink link: ")
    try:
        peer_metadata = decrypt_link(peer_link)
        peer_public_key_pem = peer_metadata.get('public_key')
        if not peer_public_key_pem:
            print("Error: Peer's public key not found in the link.")
            sys.exit(1)
        peer_public_key = serialization.load_pem_public_key(peer_public_key_pem.encode())

    except Exception as e:
        print(f"Invalid link provided: {e}")
        sys.exit(1)

    # Choose and execute the strategy
    strategy = choose_strategy(network_metadata, peer_metadata, private_key, peer_public_key, 'app.log', file_path=args.file_path if args.command == 'send' else None)

    if strategy:
        if args.command == 'send':
            strategy.send(args.file_path)
        elif args.command == 'receive':
            strategy.recv(args.output_dir)
        print("\nFile transfer complete. Exiting.")
    else:
        print("\nCould not establish a P2P connection for the given NAT types.")

if __name__ == '__main__':
    main()
