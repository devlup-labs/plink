import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from utils import log, LogType
from command_handler import get_args, handle_command

if __name__ == "__main__":
    general_logfile_path = "app.log"

    log("Application started", log_type=LogType.INFO, status="Initiated", general_logfile_path=general_logfile_path)

    args = get_args(general_logfile_path)
    log("Arguments successfully parsed", log_type=LogType.INFO, status="Success", general_logfile_path=general_logfile_path)

    log("Calling command handler", log_type=LogType.DEBUG, status="InProgress", general_logfile_path=general_logfile_path)
    handle_command(args, general_logfile_path)
    log("Command handler execution complete", log_type=LogType.INFO, status="Completed", general_logfile_path=general_logfile_path)
