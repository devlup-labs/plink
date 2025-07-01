## File : 'argument_parser.py'

Parses command-line arguments specific to the sender in the plink application.

## Functions:-
- 'parsing_argument' : Parses and logs command-line arguments for sending files.

### Function : 'parsing_argument'

**Purpose:** Parses CLI arguments for initiating a file transfer in sender mode and logs the process.

**Parameters:** 
- 'general_logfile_path' (`str`) : Path to the log file for recording parsing and all other activities.

**Returns:**
- `argparse.Namespace` : Parsed arguments as an object with attributes matching the command-line inputs.

**Raises:**
- `SystemExit` : Raised internally by argparse if argument parsing fails (e.g., invalid arguments or --help flag used).

**Side Effects:**
- Logs messages at various stages using the log utility:
    - Logs before starting argument parsing (`DEBUG`, `INFO`)
    - Logs parsed argument values (`INFO`)
    - Logs failure if parsing fails (`ERROR`)