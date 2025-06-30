import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from command_handler import get_args, handle_command

if __name__ == "__main__":
    args = get_args()
    handle_command(args)