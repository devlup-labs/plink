import os
from argument_parser import get_parser
from argument_parser import parsing_argument

def arguments_dictionary():
    parser = get_parser()
    args = parser.parse_args()
    
    args_dictionary = {
        'method': args.method,
        'port': args.port,
        'encryption': args.encryption,
        'chunk_size': args.chunk_size,
        'compress': args.compress,
        'password': args.password,
        'resume': args.resume,
        'verify': args.verify,
        'output_directory': args.output_directory,
        'auto_accept': args.auto_accept,
        'max_size': args.max_size
    }

    return args_dictionary

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
def handle_command(args):
    try:
        if args.command == 'send':
            handle_send(args)
        elif args.command == 'receive':
            handle_receive(args)
        else:
            raise InvalidCommandError(f"Unknown command: {args.command}. Use 'send' or 'receive'.")
    except Exception as e:
        print(f"Unexpected error: {e}")


#Handling the "send" command
def handle_send(args):
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

    # Validation completed
    args_dict = vars(args)
    print("Command received:")
    for key, value in args_dict.items():
        print(f"{key}: {value}") #for debugging purpose, to see the command and its parameters
    


# Handling the "receive" command
def handle_receive(args):
    # Validation
    if not os.path.isdir(args.output_dir):
        raise InvalidCommandError(f"Output directory '{args.output_dir}' does not exist.")

    if args.max_size < 0:
        raise InvalidCommandError("Max file size must be non-negative.")

    if args.port < 0 or args.port > 65535:
        raise InvalidCommandError("Port must be between 0 and 65535.")
    if args.method not in ["direct", "upnp", "hole-punch", "role-reverse"]:
        raise InvalidCommandError("Invalid connection method. Choose from: direct, upnp, hole-punch, role-reverse.")
    
    # validation completed
    args_dict = vars(args)
    print("Command receieved : ")
    for key, value in args_dict.items():
        print(f"{key}: {value}") #for debugging purpose, to see the command and its parameters
