'''
Function name: parsing_argument
Purpose: To parse command line arguments of sender for a file transfer application.
Input: None
Output: Parsed arguments as an object.
'''

import argparse

def parsing_argument() :
    
    #creating a parser
    parser=argparse.ArgumentParser("plink")

    #creating a subparser for command of send
    subparsers=parser.add_subparsers(dest="command",help="give command of send")

    #creating subparser for send and giving optional arguments
    send_parser=subparsers.add_parser("send", help="give command of send")
    send_parser.add_argument("filepath", help="path of the file to send")
    send_parser.add_argument("--method", "-m", help = "Connection method (direct, upnp, hole-punch, role-reverse)",choices=["direct","upnp","hole-punch","role-reverse"])
    send_parser.add_argument("--port", "-p", help= "Port number (default: 8080)",default=8080, type=int)
    send_parser.add_argument("--encryption", "-e", help = "Encryption method (aes256, chacha20)")
    send_parser.add_argument("--chunk-size", "-c", help = "Chunk size in KB (default: 1024)", default=1024, type=int)
    send_parser.add_argument("--compress", help = "Enable compression", action="store_true")
    send_parser.add_argument("--password", help = "Set transfer password")
    send_parser.add_argument("--timeout", help = "Connection timeout in seconds", type=int) 
    send_parser.add_argument("--resume", help = "Resume interrupted transfer",action="store_true")
    send_parser.add_argument("--verify", help = "Verify file integrity after transfer", action="store_true")

    args=parser.parse_args()

    return args