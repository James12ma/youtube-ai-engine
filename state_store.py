"""Durable task state for Router V3.

State lives on a dedicated branch (default `router-state`), materialised
as a git worktree. Atomic single-writer semantics are provided by
optimistic concurrency: sync to remote HEAD, mutate, commit, push,
retry on non-fast-forward. No credentials are ever read or written.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

try:
    import fcntl  # POSIX
    _HAS_FCNTL = True
except ImportError:  # pragma: no cover
    _HAS_FCNTL = False


STATE_SCHEMA_VERSION = "1.0"
MAX_RESULT_BYTES = 256 * 1024          # 256 KiB per task
MAX_STATE_BYTES  = 8 * 1024 * 1024     # 8 MiB total state file
PUSH_ATTEMPTS    = 4

_GIT_IDENTITY_ENV = {
    "GIT_AUTHOR_NAME":     "Router Bot",
    "GIT_AUTHOR_EMAIL":    "router-bot@users.noreply.github.com",
    "GIT_COMMITTER_NAME":  "Router Bot",
    "GIT_COMMITTER_EMAIL": "router-bot@users.noreply.github.com",
    "GIT_TERMINAL_PROMPT": "0",
}

_SENSITIVE_KEY = re.compile(
    r"(?i)(?:^|_)(?:password|passwd|pwd|secret|secrets|"
    r"api_key|apikey|authorization|bearer|private_key|access_key|"
    r"client_secret|ssh_key|auth_token|access_token|refresh_token|"
    r"id_token|token|credential|credentials|session_cookie|cookie)$"
)
_SENSITIVE_VALUE = re.compile(
    r"(BEGIN (RSA|OPENSSH|EC|DSA|PGP) PRIVATE KEY|"
    r"ghp_[A-Za-z0-9]{20,}|gho_[A-Za-z0-9]{20,}|"
    r"sk-[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]+|"
    r"AKIA[0-9A-Z]{16}|authorization\s*:\s*bearer\s+\S+)",
    re.IGNORECASE,
)


def _normalize_key(value: str) -> str:
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value).lower().replace("-", "_")



def compute_task_id(task_type: str, input_data: Any, schema_version: str) -> str:
    payload = {
        "task_type": task_type,
        "input": input_data,
        "schema_version": schema_version,
    }
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class StateStoreError(RuntimeError):
    pass


class SensitiveStateError(StateStoreError):
    pass


class OversizedStateError(StateStoreError):
    pass


class ConcurrentUpdateError(StateStoreError):
    pass


def _check_sensitive(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, sub in value.items():
            if _SENSITIVE_KEY.search(_normalize_key(str(key))):
                raise SensitiveStateError(
                    f"Sensitive key at {path}: {key!r}"
                )
            _check_sensitive(sub, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _check_sensitive(item, f"{path}[{index}]")
    elif isinstance(value, str):
        if _SENSITIVE_VALUE.search(value):
            raise SensitiveStateError(f"Sensitive value at {path}")


class StateStore:
    def __init__(
        self,
        repo_path: Path,
        state_branch: str = "router-state",
        state_file: str = "state.json",
        worktree_dirname: str = ".router-state",
        lock_dirname: str = ".router-locks",
        remote: str = "origin",
        push_required: bool = True,
    ) -> None:
        self.repo_path = Path(repo_path).resolve()
        self.state_branch = state_branch
        self.state_file = state_file
        self.worktree_path = self.repo_path / worktree_dirname
        # Locks live outside the worktree so `git clean -fd` cannot remove them.
        self.lock_dir = self.repo_path / lock_dirname
        self.lock_dir.mkdir(exist_ok=True)
        self.lock_path = self.lock_dir / (state_branch + ".lock")
        self.state_path = self.worktree_path / state_file
        self.remote = remote
        self.push_required = push_required
        self._env = {**os.environ, **_GIT_IDENTITY_ENV}
        self._lock_handle = None
        self._ensure_worktree()

    # ---------------- git plumbing ----------------

    def _git(self, *args: str, cwd: Optional[Path] = None,
             check: bool = True, input_: Optional[str] = None
             ) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", *args],
            cwd=str(cwd if cwd is not None else self.repo_path),
            check=check,
            capture_output=True,
            text=True,
            env=self._env,
            input=input_,
        )

    def _has_remote(self) -> bool:
        remotes = self._git("remote", check=False).stdout.split()
        return self.remote in remotes

    def _remote_branch_exists(self) -> bool:
        if not self._has_remote():
            return False
        probe = self._git(
            "ls-remote", "--heads", self.remote, self.state_branch, check=False
        )
        if probe.returncode != 0:
            raise StateStoreError("Cannot inspect remote state branch: " + probe.stderr.strip())
        return bool(probe.stdout.strip())

    def _ensure_worktree(self) -> None:
        self._git("worktree", "prune", check=False)

        valid = False
        if self.worktree_path.exists():
            probe = self._git(
                "rev-parse", "--git-dir",
                cwd=self.worktree_path, check=False,
            )
            valid = probe.returncode == 0

        if not valid:
            if self.worktree_path.exists():
                shutil.rmtree(self.worktree_path, ignore_errors=True)

            local_branches = self._git(
                "branch", "--list", self.state_branch
            ).stdout.split()

            if self._remote_branch_exists():
                # Recover the existing remote state branch first.
                self._git("fetch", self.remote, self.state_branch)
                self._git(
                    "branch", "-f", self.state_branch,
                    self.remote + "/" + self.state_branch,
                )
                self._git(
                    "worktree", "add",
                    str(self.worktree_path), self.state_branch,
                )
            elif self.state_branch in local_branches:
                self._git(
                    "worktree", "add",
                    str(self.worktree_path), self.state_branch,
                )
            else:
                # Orphan branch with no remote and no local copy.
                empty_tree = self._git("mktree", input_="").stdout.strip()
                seed = self._git(
                    "commit-tree", empty_tree, "-m", "Initialize router state"
                ).stdout.strip()
                self._git("branch", self.state_branch, seed)
                self._git(
                    "worktree", "add",
                    str(self.worktree_path), self.state_branch,
                )

        # Discard any uncommitted garbage from a killed runner.
        self._git("reset", "--hard", "HEAD", cwd=self.worktree_path)
        self._git("clean", "-fd", cwd=self.worktree_path)

        if not self.state_path.exists():
            self._write_state(
                {"schema_version": STATE_SCHEMA_VERSION, "tasks": {}}
            )
            self._commit("Initialize state file")

    # ---------------- state I/O ----------------

    def _read_state(self) -> dict:
        with self.state_path.open("r", encoding="utf-8") as handle:
            state = json.load(handle)
        found = state.get("schema_version")
        if found != STATE_SCHEMA_VERSION:
            raise StateStoreError(
                "Unsupported state schema: " + repr(found)
            )
        if not isinstance(state.get("tasks"), dict):
            raise StateStoreError("Corrupted state: 'tasks' is not an object")
        return state

    def _write_state(self, state: dict) -> None:
        fd, tmp_name = tempfile.mkstemp(
            dir=str(self.worktree_path),
            prefix=".state-", suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(state, handle, indent=2, sort_keys=True)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, self.state_path)
        except Exception:
            try:
                os.unlink(tmp_name)
            except FileNotFoundError:
                pass
            raise

    def _commit(self, message: str) -> bool:
        self._git("add", self.state_file, cwd=self.worktree_path)
        diff = self._git(
            "diff", "--cached", "--quiet",
            cwd=self.worktree_path, check=False,
        )
        if diff.returncode == 0:
            return False
        self._git("commit", "-m", message, cwd=self.worktree_path)
        return True

    def _sync_to_remote_head(self) -> bool:
        """Refresh local worktree from remote when available.

        Return True only when a remote state branch was actually fetched.
        A missing branch is normal during first initialization. Network/auth
        failures are never silently treated as a missing branch.
        """
        if not self._has_remote():
            if self.push_required:
                raise StateStoreError("Remote required but not configured")
            return False
        probe = self._git(
            "ls-remote", "--heads", self.remote, self.state_branch,
            cwd=self.worktree_path, check=False,
        )
        if probe.returncode != 0:
            raise StateStoreError("Remote state query failed: " + probe.stderr.strip())
        if not probe.stdout.strip():
            return False
        fetch = self._git(
            "fetch", self.remote, self.state_branch,
            cwd=self.worktree_path, check=False,
        )
        if fetch.returncode != 0:
            raise StateStoreError("Remote state fetch failed: " + fetch.stderr.strip())
        self._git(
            "reset", "--hard",
            self.remote + "/" + self.state_branch,
            cwd=self.worktree_path,
        )
        self._git("clean", "-fd", cwd=self.worktree_path)
        return True

    # ---------------- locking ----------------

    def _acquire_lock(self) -> None:
        if not _HAS_FCNTL:
            return
        self._lock_handle = open(self.lock_path, "w", encoding="utf-8")
        fcntl.flock(self._lock_handle.fileno(), fcntl.LOCK_EX)

    def _release_lock(self) -> None:
        if self._lock_handle is None:
            return
        try:
            fcntl.flock(self._lock_handle.fileno(), fcntl.LOCK_UN)
        finally:
            self._lock_handle.close()
            self._lock_handle = None

    # ---------------- public API ----------------

    def get_task(self, task_id: str) -> Optional[dict]:
        return self._read_state()["tasks"].get(task_id)

    def is_completed(self, task_id: str) -> bool:
        return self.get_task(task_id) is not None

    def get_cached_result(self, task_id: str) -> Optional[dict]:
        task = self.get_task(task_id)
        if task is None:
            return None
        return task["result"]

    def record_completion(
        self, task_id: str, task_type: str, result: dict
    ) -> bool:
        """Durably record a task. Returns True iff this call persisted it.

        The method returns only after the state branch has been pushed to
        the remote (when one is configured). If the task already exists,
        returns False and does not overwrite.
        """
        _check_sensitive(result)
        serialized = json.dumps(result, sort_keys=True, ensure_ascii=False)
        if len(serialized.encode("utf-8")) > MAX_RESULT_BYTES:
            raise OversizedStateError(
                "Result size " + str(len(serialized))
                + " exceeds limit " + str(MAX_RESULT_BYTES)
            )

        self._acquire_lock()
        try:
            # Keep a checkpoint to discard locally committed but rejected
            # bootstrap writes. Such writes are NOT durable remote state.
            initial_head = self._git(
                "rev-parse", "HEAD", cwd=self.worktree_path
            ).stdout.strip()
            last_error: Optional[str] = None
            for attempt in range(PUSH_ATTEMPTS):
                remote_branch_found = self._sync_to_remote_head()

                state = self._read_state()
                if task_id in state["tasks"]:
                    # A task in the fetched remote branch is durable. But on
                    # first initialization, it may exist *only locally* after
                    # a failed push, and must be pushed again, not cached.
                    if remote_branch_found or not self._has_remote():
                        return False
                else:
                    completed_at = datetime.now(timezone.utc).isoformat()
                    state["tasks"][task_id] = {
                        "task_type": task_type,
                        "completed_at": completed_at,
                        "result": result,
                    }

                    total = json.dumps(state, sort_keys=True).encode("utf-8")
                    if len(total) > MAX_STATE_BYTES:
                        raise OversizedStateError(
                            "State file would exceed "
                            + str(MAX_STATE_BYTES) + " bytes"
                        )

                    self._write_state(state)
                    self._commit(
                        "Complete " + task_type + " " + task_id[:12]
                    )

                if not self._has_remote():
                    if self.push_required:
                        raise StateStoreError(
                            "No remote configured but push_required=True"
                        )
                    return True

                push = self._git(
                    "push", self.remote,
                    "HEAD:" + self.state_branch,
                    cwd=self.worktree_path, check=False,
                )
                if push.returncode == 0:
                    return True

                last_error = push.stderr.strip() or push.stdout.strip()
                # Non-fast-forward: loop will re-sync and retry.
                time.sleep(0.25 * (attempt + 1))

            # Final reconciliation MUST validate the remote, not a stale
            # local commit. A remote task written by another worker is cached,
            # but never falsely reported as this writer's successful push.
            remote_branch_found = self._sync_to_remote_head()
            if remote_branch_found and task_id in self._read_state()["tasks"]:
                return False
            if not remote_branch_found:
                # No remote state exists. The rejected local commits cannot
                # be exposed as successful cached completions.
                self._git("reset", "--hard", initial_head,
                          cwd=self.worktree_path)
                self._git("clean", "-fd", cwd=self.worktree_path)
            raise ConcurrentUpdateError(
                "Failed to persist task after "
                + str(PUSH_ATTEMPTS) + " attempts: " + str(last_error)
            )
        finally:
            self._release_lock()

    def completed_task_ids(self) -> list:
        return sorted(self._read_state()["tasks"].keys())

    def last_completed_at(self) -> Optional[str]:
        tasks = self._read_state()["tasks"].values()
        if not tasks:
            return None
        stamps = [entry["completed_at"] for entry in tasks]
        return max(stamps)

    def pull(self) -> None:
        self._sync_to_remote_head()

    def push(self) -> None:
        if not self._has_remote():
            return
        self._git(
            "push", self.remote,
            "HEAD:" + self.state_branch,
            cwd=self.worktree_path,
        )
