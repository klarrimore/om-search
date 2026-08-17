"""XDG data directory resolution for om-search."""

import os
from pathlib import Path


def data_dir() -> Path:
    """Return the om-search data directory, creating it if needed."""
    xdg = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    d = Path(xdg) / "om-search"
    d.mkdir(parents=True, exist_ok=True)
    return d


def repo_dir() -> Path:
    """Return the path to the cloned omarchy repository."""
    return data_dir() / "omarchy-repo"


def manual_dir() -> Path:
    """Return the path to the manual files inside the cloned repo."""
    return repo_dir() / "manual"