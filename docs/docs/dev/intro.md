---
sidebar_position: 1
title: Developer Documentation Standards
---

## Purpose

This documentation defines the standard for writing and organizing developer-facing documentation for this project. It includes **rules for folders, files, and functions**, and provides a consistent structure that every contributor must follow.

---

## Folder-Level Rules

-  **Folder structure must exactly match the layout defined in the GitHub repository.**
-  Every folder must contain an `intro.md` file.
- `intro.md` must document:
  -  **Purpose** of the folder
  -  **Main operations** or logic handled

### Example: `auth/intro.md`

```md
# Folder: `auth`

Handles user authentication and token management.

## Operations
- Generate and validate JWT tokens.
- Middleware for securing routes.
- User session verification.

---

## File-Level Rules

- Every file must begin with a file-level header comment or markdown block.
- This should include:
  - **File Name**
  - **Purpose**
  - **Dependencies (if any)**
  - **Authorship / creation date** (optional)

### Example: Python File Header

```python
# File: jwt_handler.py
# Purpose: Implements encode/decode for JWT tokens and token validation logic.
# Dependencies: pyjwt, datetime
```

### Example: `jwt_handler.md` (Alternative)

```md
## File: jwt_handler.py

Handles JWT generation and verification logic.

### Functions
- `encode_token`: Encodes payload to JWT
- `decode_token`: Verifies and decodes token
- `is_token_valid`: Checks for expiry and integrity
```

---

## 🔧 Function-Level Documentation

Every function **must** be documented using the following format.

###  Universal Format

```md
### Function: <function_name>

**Purpose:** <1-liner explanation of what this function does>

**Parameters:**
- `<name>` (`<type>`): <what it means or expects>

**Returns:**
- `<type>`: <what the function returns>

**Raises:**
- `<ErrorType>`: <when/why it's raised>

**Side Effects:**
- e.g., Logs, DB writes, network calls

**Example:**
```python
result = function_name(arg1, arg2)
```
```

---

### Python Example

```python
def generate_token(user_id: str) -> str:
    """
    Generates a JWT token for a given user ID.

    Parameters:
        user_id (str): Unique identifier of the user.

    Returns:
        str: JWT token string.

    Raises:
        ValueError: If the user ID is invalid.

    Side Effects:
        Logs the token generation.

    Example:
        >>> generate_token("abc123")
        'eyJ0eXAiOiJKV1QiLCJhbGci...'
    """
```
