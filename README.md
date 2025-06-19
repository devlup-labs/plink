# Plink - Peer-to-Peer File Transfer


Plink is a secure, efficient peer-to-peer file transfer tool that enables direct file sharing between devices without relying on centralized servers. Built with modularity and security in mind, Plink implements multiple connection strategies and robust encryption to ensure safe and reliable file transfers.

## Features

-  **Multiple Connection Methods**: Direct connection, UPnP, NAT hole punching, and role reversal
-  **End-to-End Encryption**: AES-256 encryption with secure key exchange
-  **Smart Chunking**: Efficient data chunking for large file transfers
-  **Cross-Platform**: Works on Windows, macOS, and Linux
-  **Secure by Default**: All transfers are encrypted and verified

## Project Structure

```
plink/
├── README.md
├── LICENSE
├── requirements.txt
├── setup.py
├── .gitignore
├── docs/
│   ├── API.md
│   ├── ARCHITECTURE.md
│   └── EXAMPLES.md
├── backend/
│   ├── __init__.py
│   ├── networking/
│   │   ├── __init__.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── connection_manager.py
│   │   │   ├── peer_discovery.py
│   │   │   └── transfer_session.py
│   │   ├── strategies/
│   │   │   ├── __init__.py
│   │   │   ├── direct_connection.py
│   │   │   ├── upnp_connection.py
│   │   │   ├── hole_punching.py
│   │   │   └── role_reversal.py
│   │   ├── protocols/
│   │   │   ├── __init__.py
│   │   │   ├── handshake.py
│   │   │   ├── file_metadata.py
│   │   │   └── transfer_protocol.py
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── network_utils.py
│   │       └── port_scanner.py
│   └── cryptography/
│       ├── __init__.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── encryption.py
│       │   ├── key_exchange.py
│       │   └── hash_verification.py
│       ├── chunking/
│       │   ├── __init__.py
│       │   ├── chunk_manager.py
│       │   ├── chunk_validator.py
│       │   └── compression.py
│       └── utils/
│           ├── __init__.py
│           ├── crypto_utils.py
│           └── random_generator.py
├── frontend/
    ├── __init__.py
    ├── cli/
    │   ├── __init__.py
    │   ├── argument_parser.py
    │   ├── command_handler.py
    │   └── output_formatter.py
    │  
    └── config/
        ├── __init__.py
        ├── settings.py
        └── validators.py
```

### Prerequisites

- Python 3.8 or higher
- pip package manager

## Quick Start

### Basic File Transfer

**Sender:**
```bash
plink send /path/to/file.txt
```

**Receiver:**
```bash
plink receive
```

### Advanced Usage

**Send with specific connection method:**
```bash
plink send /path/to/file.txt --method upnp --port 8080
```

**Receive with custom settings:**
```bash
plink receive --output-dir /downloads --method hole-punch
```

## Command Line Interface

### Sender Commands

```bash
plink send <file_path> [OPTIONS]

OPTIONS:
  --method, -m          Connection method (direct, upnp, hole-punch, role-reverse)
  --port, -p           Port number (default: 8080)
  --encryption, -e     Encryption method (aes256, chacha20)
  --chunk-size, -c     Chunk size in KB (default: 1024)
  --compress           Enable compression
  --password           Set transfer password
  --timeout            Connection timeout in seconds
  --resume             Resume interrupted transfer
  --verify             Verify file integrity after transfer
```

### Receiver Commands

```bash
plink receive [OPTIONS]

OPTIONS:
  --output-dir, -o     Output directory (default: current directory)
  --port, -p           Port number (default: 8080)
  --method, -m         Preferred connection method
  --password           Transfer password
  --auto-accept        Automatically accept transfers
  --max-size           Maximum file size to accept (MB)
```

## Connection Methods

### 1. Direct Connection
- **Use Case**: Same network, known IP addresses
- **Advantages**: Fastest, most reliable
- **Requirements**: Open ports, direct network access

### 2. UPnP (Universal Plug and Play)
- **Use Case**: Behind NAT with UPnP-enabled router
- **Advantages**: Automatic port forwarding
- **Requirements**: UPnP-enabled router

### 3. NAT Hole Punching
- **Use Case**: Both peers behind NAT
- **Advantages**: Works through most NAT configurations
- **Requirements**: STUN server access

### 4. Role Reversal
- **Use Case**: Asymmetric NAT situations
- **Advantages**: Fallback when other methods fail
- **Requirements**: One peer with open connectivity

### Pull Request Process

1. Create a feature branch from `main`
2. Make your changes with appropriate tests
3. Update documentation if needed
4. Ensure all tests pass
5. Submit pull request with clear description
