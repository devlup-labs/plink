## File : 'main.py'
- Entry point for the CLI-based plink file transfer application.
- Initializes logging, parses arguments, and transfers commands for further processing.

### Functions:
No any function is defined in this file, it is for initializing the application.

**Purpose:**
Starts the application by:
- Initializing the log system.
- Parsing CLI arguments (send/receive mode).
- Passing arguments to the command handler for validation and execution

**Execution Flow:**
- Sets `app.log` as the default log file path and logs application startup.
- Calls `get_args()` to parse CLI arguments and logs the result.
- Calls `handle_command()` to execute based on the parsed arguments and logs its completion.

**Side Effects:**
- Writes multiple log entries to `app.log` using the `log()` utility:
- `INFO` log on startup and completion.
- `INFO` log after successful argument parsing.
- `DEBUG` log before invoking the command handler.

**Note:**
This script uses `sys.path.insert()` to allow relative imports from higher-level directories.