"""Cloning and updating the Omarchy manual repository."""

import subprocess
from pathlib import Path

REPO_URL = "https://github.com/basecamp/omarchy"
BRANCH = "quattro"
SUBDIR = "manual"


def _git(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )


def clone_manual(dest: Path, remote: str = REPO_URL, branch: str = BRANCH) -> None:
    """Shallow, sparse, blob-filtered clone of just the manual directory."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    _git(
        "clone",
        "--depth",
        "1",
        "--branch",
        branch,
        "--filter=blob:none",
        "--sparse",
        remote,
        str(dest),
    )
    _git("-C", str(dest), "sparse-checkout", "set", SUBDIR)


def ensure_manual(repo: Path, remote: str = REPO_URL, branch: str = BRANCH) -> Path:
    """Clone the manual repo if it does not exist yet. Returns the manual dir."""
    if not (repo / ".git").exists():
        clone_manual(repo, remote, branch)
    return repo / SUBDIR


def update_manual(repo: Path, remote: str = REPO_URL, branch: str = BRANCH) -> bool:
    """Pull the latest manual. Clones if missing. Returns True on success."""
    if not (repo / ".git").exists():
        clone_manual(repo, remote, branch)
        return True
    try:
        _git("-C", str(repo), "pull", "--ff-only")
        return True
    except subprocess.CalledProcessError:
        return False
