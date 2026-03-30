# src/openwfn/utils.py

import sys
from typing import List, Sequence, Tuple

def print_header(text: str):
    """Print a professional themed header."""
    print(f"\n\033[1;36m{text}\033[0m")
    print("\033[1;36m" + "-" * len(text) + "\033[0m")


def print_subheader(text: str):
    """Print a compact section title."""
    print(f"\n\033[1m{text}\033[0m")

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


def print_key_value_rows(rows: Sequence[Tuple[str, str]]) -> None:
    """Print aligned key-value pairs."""
    if not rows:
        return
    width = max(len(label) for label, _ in rows)
    for label, value in rows:
        print(f"{highlight(label + ':'):<{width + 12}}{value}")


def print_menu_section(title: str, entries: Sequence[Tuple[str, str]]) -> None:
    """Print a titled menu section."""
    print_subheader(title)
    for key, description in entries:
        print(f"  {highlight(key):<18} {description}")


def print_panel(title: str, lines: Sequence[str]) -> None:
    """Print a simple ASCII panel."""
    content = list(lines)
    width = max([len(title), *(len(line) for line in content)]) if content else len(title)
    border = "+" + "-" * (width + 2) + "+"
    print(border)
    print(f"| {title.ljust(width)} |")
    print(border)
    for line in content:
        print(f"| {line.ljust(width)} |")
    print(border)


def print_banner(text: str, width: int = 68) -> None:
    """Print a centered ASCII banner line."""
    inner_width = max(width, len(text) + 2)
    border = "+" + "=" * inner_width + "+"
    print(border)
    print(f"|{text.center(inner_width)}|")
    print(border)
