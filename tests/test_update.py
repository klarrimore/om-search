"""Tests for manual clone/update git operations.

These run against a throwaway local git repo, not the network.
"""

import subprocess
from pathlib import Path

import pytest

from om_search.update import ensure_manual, update_manual


@pytest.fixture()
def source_repo(tmp_path: Path) -> Path:
    """A local git repo with a manual/ dir, committed on branch 'quattro'."""
    src = tmp_path / "source"
    src.mkdir()
    (src / "manual").mkdir()
    (src / "manual" / "01-page.md").write_text("# Page One\n\nContent.")
    subprocess.run(["git", "init", "-b", "quattro", str(src)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(src), "add", "."], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(src), "commit", "-m", "init"],
        check=True,
        capture_output=True,
        env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t", **__import__("os").environ},
    )
    return src


class TestEnsureManual:
    def test_clones_when_missing(self, tmp_path, source_repo):
        dest = tmp_path / "dest"
        manual = ensure_manual(dest, remote=str(source_repo))
        assert manual.exists()
        files = list(manual.glob("*.md"))
        assert len(files) == 1
        assert files[0].name == "01-page.md"

    def test_noop_when_already_cloned(self, tmp_path, source_repo):
        dest = tmp_path / "dest"
        ensure_manual(dest, remote=str(source_repo))
        m2 = ensure_manual(dest, remote=str(source_repo))
        assert m2.exists()


class TestUpdateManual:
    def test_pull_brings_new_commits(self, tmp_path, source_repo):
        dest = tmp_path / "dest"
        ensure_manual(dest, remote=str(source_repo))

        # Add a new page upstream and commit it
        (source_repo / "manual" / "02-page.md").write_text("# Page Two\n\nMore.")
        subprocess.run(["git", "-C", str(source_repo), "add", "."], check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(source_repo), "commit", "-m", "add page"],
            check=True,
            capture_output=True,
            env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t", **__import__("os").environ},
        )

        ok = update_manual(dest, remote=str(source_repo))
        assert ok is True
        files = sorted(f.name for f in (dest / "manual").glob("*.md"))
        assert files == ["01-page.md", "02-page.md"]

    def test_update_on_missing_repo_clones(self, tmp_path, source_repo):
        dest = tmp_path / "dest"
        ok = update_manual(dest, remote=str(source_repo))
        assert ok is True
        assert (dest / "manual" / "01-page.md").exists()
