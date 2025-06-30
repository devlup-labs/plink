'''
Function name: parsing_argument
Purpose: To parse command line arguments of receiver for a file transfer application.
Input: None
Output: Parsed arguments as an object.
'''

import argparse

def parsing_argument() :
    
    #creating a parser
    parser=argparse.ArgumentParser("plink")

    #creating a subparser for command of receive
    subparsers=parser.add_subparsers(dest="command",help="give command of receive")

    #creating subparser for receive and giving optional arguments
    receive_parser=subparsers.add_parser("receive", help="give command of receive")
    receive_parser.add_argument("--output-dir", "-o", help = "Output directory (default: current directory)", default=".")
    receive_parser.add_argument("--port", "-p", help = "Port number (default: 8080)", default=8080, type=int)
    receive_parser.add_argument("--method", "-m", help = "Preferred connection method")
    receive_parser.add_argument("--password", help  = "Transfer password")
    receive_parser.add_argument("--auto-accept", help = "Automatically accept transfers",action="store_true")
    receive_parser.add_argument("--max-size", help = "Maximum file size to accept (MB)", type=int, default=1)

    args=parser.parse_args()

    return args

