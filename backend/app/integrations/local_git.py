"""Local-git ingestion adapter.

Builds normalized review events from a local git repository using plain ``git``
commands, so the pipeline runs with no deployment and no inbound webhooks
(no port forwarding). The adapter is shared by the polling watcher
(``scripts/watch_repo.py``) and the bare-repo ``post-receive`` hook.

The produced event flows into the same pipeline as a GitHub webhook:
triage -> review/security agents -> HITL -> summarizer -> dashboard.
"""

import subprocess
from pathlib import Path

from ..domain.events import CommitRef, IngestEvent, RepositoryInfo


class GitCommandError(RuntimeError):
    pass


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise GitCommandError(result.stderr.strip())
    return result.stdout


def rev_parse(repo: Path, ref: str) -> str:
    """Resolve a git ref (``HEAD``, ``HEAD~1``, …) to its full commit SHA."""
    return _git(repo, "rev-parse", ref).strip()


def diff_between(repo: Path, base_sha: str, head_sha: str) -> str:
    """Unified diff between two commits. ``head_sha`` may be ``HEAD``."""
    return _git(repo, "diff", f"{base_sha}..{head_sha}", "--no-color")


def changed_files(repo: Path, base_sha: str, head_sha: str) -> list[str]:
    out = _git(repo, "diff", "--name-only", f"{base_sha}..{head_sha}")
    return [line for line in out.splitlines() if line.strip()]


def commit_message(repo: Path, sha: str) -> str:
    return _git(repo, "log", "-1", "--format=%s", sha).strip()


def commit_author(repo: Path, sha: str) -> str:
    return _git(repo, "log", "-1", "--format=%an", sha).strip()


def build_push_event(
    repo: Path,
    base_sha: str,
    head_sha: str,
    provider: str = "local_git",
) -> IngestEvent:
    """Create a normalized ``push`` event for the change ``base_sha..head_sha``."""
    repo_abs = Path(repo).resolve()
    return IngestEvent(
        event="push",
        provider=provider,
        repository=RepositoryInfo(
            name=repo_abs.name,
            owner=None,
            path=str(repo_abs),
            clone_url=f"file://{repo_abs}",
        ),
        commit=CommitRef(
            sha=head_sha,
            base_sha=base_sha,
            message=commit_message(repo_abs, head_sha),
            author=commit_author(repo_abs, head_sha),
            files=changed_files(repo_abs, base_sha, head_sha),
            diff=diff_between(repo_abs, base_sha, head_sha),
        ),
    )
