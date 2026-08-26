"""Project-owned launcher for the local Agent Server."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import NoReturn


def repository_root() -> Path:
    """Return the checkout containing the package and server configuration."""
    return Path(__file__).resolve().parents[2]


def server_arguments(root: Path) -> list[str]:
    """Build the fixed local-development Agent Server arguments."""
    return [
        sys.executable,
        "-m",
        "langgraph_cli",
        "dev",
        "--config",
        str(root / "langgraph.json"),
        "--host",
        "127.0.0.1",
        "--port",
        "2024",
        "--no-browser",
    ]


def main() -> NoReturn:
    """Replace this process with the configured loopback Agent Server."""
    root = repository_root()
    os.chdir(root)
    os.execv(sys.executable, server_arguments(root))
