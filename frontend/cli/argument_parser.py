import argparse

def get_parser():
    parser = argparse.ArgumentParser(description="PLINK CLI Argument Parser")
    
    parser.add_argument('-m','--method',help = 'method to use for networking',choices = ['direct', 'hole-punch', 'upnp', 'role-reversal'])
    parser.add_argument('-p', '--port', type=int, default=8080, help='Port to use for networking (default: 8080)')
    parser.add_argument('-e', '--encryption', choices = ['aes256', 'chacha20'], default = 'chacha20', help = 'Encryption method to use')
    parser.add_argument('-c','--chunk-size', type=int, default=1024, help='Size of data chunks to send (default: 1024 bytes)')
    parser.add_argument('--compress' , action='store_true', help='Enable compression for data transfer')
    parser.add_argument('--password', type=str, help='set transfer password')
    parser.add_argument('--resume', action='store_true', help='Resume interrupted transfers')
    parser.add_argument('--verify', action='store_true', help='Verify file integrity after transfer')

    parser.add_argument('-o', '--output-directory', type=str, default='.', help='Directory to save received files (default: current directory)')
    parser.add_argument('--auto-accept', action='store_true', help='Automatically accept transfers')
    parser.add_argument('--max-size', type=int, default=0, help='Maximum size of files to accept (default: 0, for no limit)')

    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')

    return parser