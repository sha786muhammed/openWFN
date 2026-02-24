# src/openwfn/utils.py

import sys
from typing import List, Tuple

def print_header(text: str):
    """Print a professional themed header."""
    print(f"\n\033[1;36m{text}\033[0m")
    print("\033[1;36m" + "-" * len(text) + "\033[0m")

def print_table_header(columns: List[Tuple[str, int]]):
    """Print the header for a table with specified column widths."""
    header = ""
    separator = ""
    for name, width in columns:
        header += f"{name:<{width}}  "
        separator += "-" * width + "  "
    print(header.rstrip())
    print(separator.rstrip())

def print_table_row(data: List[Tuple[str, int]]):
    """Print a row in a table."""
    row = ""
    for val, width in data:
        row += f"{val:<{width}}  "
    print(row.rstrip())

def print_success(text: str):
    """Print a success message in green."""
    print(f"\033[32m{text}\033[0m")

def print_warning(text: str):
    """Print a warning message in yellow."""
    print(f"\033[33mWarning: {text}\033[0m")

def print_error(text: str):
    """Print an error message in red."""
    print(f"\033[1;31mError: {text}\033[0m", file=sys.stderr)

def highlight(text: str) -> str:
    """Return text wrapped in a highlight color (cyan)."""
    return f"\033[1;36m{text}\033[0m"
