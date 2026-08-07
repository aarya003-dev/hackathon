"""Tests for the local-git ingestion adapter."""

import subprocess
from pathlib import Path

import pytest
from app.integrations.local_git import (
    GitCommandError,
    build_push_event,
    changed_files,
    diff_between,
)


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    git_repo = tmp_path / "sample-repo"
    git_repo.mkdir()
    subprocess.run(["git", "-C", str(git_repo), "init", "-q", "-b", "main"], check=True)
    subprocess.run(
        ["git", "-C", str(git_repo), "config", "user.email", "test@example.com"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(git_repo), "config", "user.name", "Test User"],
        check=True,
    )

    (git_repo / "app.py").write_text("def greet():\n    return 'hello'\n")
    subprocess.run(["git", "-C", str(git_repo), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(git_repo), "commit", "-q", "-m", "initial commit"],
        check=True,
    )
    return git_repo


def test_build_push_event_contains_diff_and_files(repo: Path) -> None:
    base = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    (repo / "app.py").write_text("def greet():\n    return 'hello world'\n")
    (repo / "new.py").write_text("x = 1\n")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-q", "-m", "improve greeting"],
        check=True,
    )
    head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    event = build_push_event(repo, base, head)

    assert event.provider == "local_git"
    assert event.event == "push"
    assert event.commit.sha == head
    assert event.commit.base_sha == base
    assert event.commit.message == "improve greeting"
    assert event.commit.author == "Test User"
    assert set(event.commit.files) == {"app.py", "new.py"}
    assert "+    return 'hello world'" in event.commit.diff
    assert "+x = 1" in event.commit.diff
    assert event.repository.name == "sample-repo"
    assert event.repository.clone_url == f"file://{repo.resolve()}"


def test_changed_files_empty_on_identical_commits(repo: Path) -> None:
    base = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert changed_files(repo, base, base) == []
    assert diff_between(repo, base, base) == ""


def test_build_push_event_on_missing_repo(tmp_path: Path) -> None:
    with pytest.raises(GitCommandError):
        build_push_event(tmp_path / "does-not-exist", "a" * 40, "b" * 40)
