import datetime
import inspect
from enum import Enum

# enum type for log
# INFO : Normal operations
# ERROR : Failures that interrupt the current task
# DEBUG : Internal details for debugging
# WARNING : Recoverable issues or fallbacks
# CRITICAL : Severe errors — application may crash

class LogType(Enum):
    INFO = "INFO"
    ERROR = "ERROR"
    DEBUG = "DEBUG"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


"""
Appends a formatted log entry to the specified log file.

Argumnets:
    message (str): The log message to record.
    log_type (LogType): The type/severity of the log.
    status (str): Status label (e.g., 'Success', 'Failure').
    general_logfile_path (str): Path to the log file where entry is appended.
    print_log (bool) : Prints the log line if true.
"""

def log(message, log_type=LogType.INFO, status="Success", general_logfile_path="app.log",print_log = False):
    if not isinstance(log_type, LogType):
        raise ValueError(f"log_type must be an instance of LogType Enum, got {type(log_type)}")

    timestamp = datetime.datetime.now().isoformat()

    frame = inspect.currentframe()
    caller_frame = frame.f_back
    function_name = caller_frame.f_code.co_name

    log_entry = f"{timestamp} {log_type.value} {function_name} {status} {message}\n"

    if print_log:
        print(print_log)

    with open(general_logfile_path, "a") as f:
        f.write(log_entry)
