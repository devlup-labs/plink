### Enum : LogType

- `INFO` : Normal operations
- `ERROR` : Failures that interrupt the current task
- `DEBUG` : Internal details for debugging
- `WARNING` : Recoverable issues or fallbacks
- `CRITICAL` : Severe errors — application may crash


### Function: log

**Purpose:** Appends a formatted log entry to the specified log file and optionally prints it.

**Parameters:**
- `message` (`str`): The log message to record.
- `log_type` (`LogType`, optional): The type/severity of the log (e.g., INFO, ERROR). Defaults to `LogType.INFO`.
- `status` (`str`, optional): Status label to indicate result (e.g., "Success", "Failure"). Defaults to `"Success"`.
- `general_logfile_path` (`str`, optional): Path to the log file where the entry will be appended. Defaults to `"app.log"`.
- `print_log` (`bool`, optional): If `True`, prints the log entry to stdout. Defaults to `True`.

**Returns:**
- `None`: This function does not return a value.

**Raises:**
- `ValueError`: If `log_type` is not an instance of `LogType`.

**Side Effects:**
- Appends a log entry to the specified file.
- Optionally prints the log entry to the console.

**Example:**
```python
from utils.logger import log, LogType

def fetch_user(user_id):
    log(f"Fetched user with ID {user_id}", log_type=LogType.INFO, status="Success", general_logfile_path="app.log")

fetch_user("abc123")
