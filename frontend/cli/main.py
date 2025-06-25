from argument_parser import parsing_argument
from command_handler import handle_command

if __name__ == "__main__":
    args = parsing_argument()
    handle_command(args)