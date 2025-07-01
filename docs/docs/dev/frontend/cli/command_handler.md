## File: 'command_handler.py'

Handles command selection, validation, and execution logic for sending and receiving files.

## Functions:-
- 'get_args' : Determines the command (send/receive) and transfers to the correct argument parser.
- 'handle_command' : Assigns handling to handle_send or handle_receive based on parsed command.
- 'handle_send' : Validates and logs parameters for sending a file.
- 'handle_receive' : Validates and logs parameters for receiving a file.

### Function: 'get_args'

**Purpose:** Determines which command (send or receive) is used and activates the appropriate argument parser.

**Parameters:**
- 'general_logfile_path' (`str`) : Path to the general log file for logging events.

**Returns:**
- `argparse.Namespace` : Parsed command-line arguments.

**Raises:**
- `InvalidCommandError` : If an unknown command is provided.

**Side Effects:**
- Logs command detection and parser routing decisions.

### Function: 'handle_command'

**Purpose:** Assigns execution to handle_send or handle_receive based on the parsed arguments.

**Parameters:**
- 'args' (`argparse.Namespace`) : Parsed arguments.
- 'general_logfile_path' (`str`) : Path to the log file.

**Returns:**
- `None`

**Raises:**
- `InvalidCommandError` : If the command is not recognized.

**Side Effects:**
- Logs the start and result of command handling.

### Function: 'handle_send'

**Purpose:** Performs validation checks on send-related arguments and logs the results.

**Parameters:**
- 'args' (`argparse.Namespace`) : Parsed arguments from sender parser.
- 'general_logfile_path' (`str`) : Log file path for writing logs.

**Returns:**
- `None`

**Raises:**
- `InvalidCommandError` : If filepath is invalid or does not exists, chunk size is not positive, or connection method or encryption is invalid.

**Side Effects:**
- Logs validation progress and results.

### Function: 'handle_receive'

**Purpose:** Performs validation checks on receive-related arguments and logs the results.

**Parameters:**
- 'args' (`argparse.Namespace`) : Parsed arguments from receiver parser.
- 'general_logfile_path' (`str`) : Path to the general log file.

**Returns:**
- `None`

**Raises:**
- `InvalidCommandError` : If output directory, port, max size or connection method is invalid.

**Side Effects:**
- Logs validation flow and extracted argument details.