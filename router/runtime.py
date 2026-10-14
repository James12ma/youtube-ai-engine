"""Durable runtime mutations using the Task 1 state branch.

All read-modify-write transactions fetch the latest remote state and retry
non-fast-forward pushes. No private LLM data or credentials are persisted.
"""
from __future__ import annotations
import copy
import json
import os
import tempfile
import time
from typing import Any, Callable, TypeVar
from state_store import ConcurrentUpdateError, StateStore, _check_sensitive

RUNTIME_FILE = 'router_runtime.json'
V = TypeVar('V')

class RouterRuntimeStore:
    def __init__(self, state_store: StateStore):
        self._store = state_store
        self._path = state_store.worktree_path / RUNTIME_FILE

    def load(self) -> dict[str, Any]:
        if not self._path.exists():
            return {}
        with self._path.open('r', encoding='utf-8') as handle:
            value = json.load(handle)
        if not isinstance(value, dict):
            raise ValueError('Malformed runtime state; refusing to overwrite')
        return value

    def _write(self, data: dict[str, Any]) -> None:
        _check_sensitive(data)
        payload = json.dumps(data, sort_keys=True, allow_nan=False).encode('utf-8')
        if len(payload) > 1024 * 1024:
            raise ValueError('Runtime state > 1 MiB')
        fd, name = tempfile.mkstemp(dir=str(self._path.parent), prefix='.rt-', suffix='.tmp')
        try:
            with os.fdopen(fd, 'wb') as f:
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())
            os.replace(name, self._path)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def transact(self, mutate: Callable[[dict[str, Any]], V], *, operation_id: str = 'runtime', attempts: int = 5) -> V:
        """Execute a pure mutator; return only after a durable remote push.

        Mutator may be called more than once following a racing remote update.
        Any counters/reservations must use stable IDs for retry safety.
        """
        self._store._acquire_lock()
        try:
            for n in range(attempts):
                self._store._sync_to_remote_head()
                before = self.load()
                after = copy.deepcopy(before)
                value = mutate(after)
                if after == before:
                    return value
                self._write(after)
                self._store._git('add', RUNTIME_FILE, cwd=self._store.worktree_path)
                self._store._git('commit', '-m', 'Router runtime: ' + operation_id[:60], cwd=self._store.worktree_path)
                if not self._store._has_remote():
                    if self._store.push_required:
                        raise RuntimeError('Durable remote required but no remote configured')
                    return value
                push = self._store._git('push', self._store.remote,
                                       'HEAD:' + self._store.state_branch,
                                       cwd=self._store.worktree_path, check=False)
                if push.returncode == 0:
                    return value
                # Retry all changes from the latest remote state. No force-push.
                time.sleep(.10 * (n + 1))
            self._store._sync_to_remote_head()
            raise ConcurrentUpdateError('Runtime remote push conflicted after retries')
        finally:
            self._store._release_lock()

    def save(self, data: dict[str, Any]) -> None:
        """Compatibility convenience method, not for concurrent read/modify/write."""
        self.transact(lambda state: (state.clear(), state.update(data)), operation_id='save')
