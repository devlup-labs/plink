import os
import sys
from utils import log, LogType

from frontend.cli.sender.argument_parser import parsing_argument as sender_parsing_argument
from frontend.cli.receiver.argument_parser import parsing_argument as receiver_parsing_argument

# Get arguments using appropriate parser
def get_args(general_logfile_path):
    command = sys.argv[1] if len(sys.argv) > 1 else None
    log("Fetching command-line arguments", log_type=LogType.DEBUG, status="Started", general_logfile_path=general_logfile_path)

    if command == "send":
        log("Command is 'send'", log_type=LogType.INFO, status="Success", general_logfile_path=general_logfile_path)
        return sender_parsing_argument(general_logfile_path)
    elif command == "receive":
        log("Command is 'receive'", log_type=LogType.INFO, status="Success", general_logfile_path=general_logfile_path)
        return receiver_parsing_argument(general_logfile_path)
    else:
        raise InvalidCommandError("Unknown command. Use 'send' or 'receive'")

'''
Function name: handle_command
Purpose: To handle the command line arguments for sending or receiving files.
Input: Parsed arguments as an object.
Output: None, but prints the command and its parameters.
'''

# Exceptions Class
class InvalidCommandError(Exception):
    def __init__(self, message):
        super().__init__(message)


#Seperating the Send and Receive commands
def handle_command(args, general_logfile_path):
    try:
        log(f"Handling command: {args.command}", log_type=LogType.INFO, status="Started", general_logfile_path=general_logfile_path)
        if args.command == 'send':
            handle_send(args, general_logfile_path)
        elif args.command == 'receive':
            handle_receive(args, general_logfile_path)
        else:
            raise InvalidCommandError(f"Unknown command: {args.command}. Use 'send' or 'receive'.")
    except Exception as e:
        print(f"Unexpected error: {e}")


#Handling the "send" command
def handle_send(args, general_logfile_path):

    log("Send command validation started", log_type=LogType.DEBUG, status="Started", general_logfile_path=general_logfile_path)
    # Validation
    if not hasattr(args, 'filepath') or not args.filepath:
        raise InvalidCommandError("Missing required file path.")
    
    if not os.path.exists(args.filepath):
        raise InvalidCommandError(f"File '{args.filepath}' does not exist.")

    if not os.path.isfile(args.filepath):
        raise InvalidCommandError(f"'{args.filepath}' is not a file.")

    if args.chunk_size <= 0:
        raise InvalidCommandError("Chunk size must be a positive integer.")
    
    if args.method not in ["direct", "upnp", "hole-punch", "role-reverse"]:
        raise InvalidCommandError("Invalid connection method. Choose from: direct, upnp, hole-punch, role-reverse.")
    if args.encryption and args.encryption not in ["aes256", "chacha20"]:
        raise InvalidCommandError("Invalid encryption method. Choose from: aes256, chacha20.")
    # if args.timeout is not None and args.timeout <= 0:
    #     raise InvalidCommandError("Timeout must be a positive number.")

    log("Send command validation passed", log_type=LogType.INFO, status="Success", general_logfile_path=general_logfile_path)
    # Validation completed
    args_dict = vars(args)
    print("Command received:")
    for key, value in args_dict.items():
        print(f"{key}: {value}") #for debugging purpose, to see the command and its parameters
    


# Handling the "receive" command
def handle_receive(args, general_logfile_path):

    log("Receive command validation started", log_type=LogType.DEBUG, status="Started", general_logfile_path=general_logfile_path)
    # Validation
    if not os.path.isdir(args.output_dir):
        raise InvalidCommandError(f"Output directory '{args.output_dir}' does not exist.")

    if args.max_size < 0:
        raise InvalidCommandError("Max file size must be non-negative.")

    if args.port < 0 or args.port > 65535:
        raise InvalidCommandError("Port must be between 0 and 65535.")
    if args.method not in ["direct", "upnp", "hole-punch", "role-reverse"]:
        raise InvalidCommandError("Invalid connection method. Choose from: direct, upnp, hole-punch, role-reverse.")
    
    log("Receive command validation passed", log_type=LogType.INFO, status="Success", general_logfile_path=general_logfile_path)
    # validation completed
    args_dict = vars(args)
    print("Command receieved : ")
    for key, value in args_dict.items():
        print(f"{key}: {value}") #for debugging purpose, to see the command and its parameters
