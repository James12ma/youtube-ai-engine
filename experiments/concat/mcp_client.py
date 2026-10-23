"""Minimal MCP stdio client for Concat (`concat --mcp headless`): newline-delimited JSON-RPC 2.0.

Concat is an external AGPL-3.0 program. It runs as a separate process and is spoken to over stdio, so
nothing of it is linked into or copied into this repository.
"""
from __future__ import annotations

import json
import os
import subprocess
import threading
import time


class McpError(RuntimeError):
    pass


class ConcatMcp:
    def __init__(self, binary: str = "concat", mode: str = "headless", env: dict | None = None, log=None):
        self.log = log or (lambda m: print(m, flush=True))
        e = {**os.environ, **(env or {})}
        self.proc = subprocess.Popen([binary, "--mcp", mode], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, env=e, text=True, bufsize=1)
        self.stderr: list[str] = []
        threading.Thread(target=self._drain, daemon=True).start()
        self._id = 0

    def _drain(self):
        for line in self.proc.stderr:
            self.stderr.append(line.rstrip())
            self.log("[concat] " + line.rstrip())

    def request(self, method: str, params: dict | None = None, timeout: float = 600) -> dict:
        self._id += 1
        msg = {"jsonrpc": "2.0", "id": self._id, "method": method, "params": params or {}}
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()
        deadline = time.time() + timeout
        while time.time() < deadline:
            line = self.proc.stdout.readline()
            if not line:
                raise McpError(f"concat exited (code {self.proc.poll()}) during {method}")
            reply = json.loads(line)
            if reply.get("id") != self._id:  # progress notifications etc.
                continue
            if "error" in reply:
                raise McpError(f"{method}: {reply['error']}")
            return reply["result"]
        raise McpError(f"{method}: no answer in {timeout}s")

    def initialize(self) -> dict:
        r = self.request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                        "clientInfo": {"name": "youtube-ai-engine", "version": "0"}})
        self.proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        self.proc.stdin.flush()
        return r

    def call(self, tool: str, args: dict | None = None, timeout: float = 600):
        """Call a tool; returns its structured content (or parsed text). Tool-level errors raise."""
        r = self.request("tools/call", {"name": tool, "arguments": args or {}}, timeout)
        if r.get("isError"):
            raise McpError(f"{tool}: " + " ".join(c.get("text", "") for c in r.get("content", [])))
        if "structuredContent" in r:
            return r["structuredContent"]
        texts = [c.get("text", "") for c in r.get("content", []) if c.get("type") == "text"]
        try:
            return json.loads(texts[0]) if len(texts) == 1 else texts
        except (json.JSONDecodeError, IndexError):
            return texts

    def close(self):
        try:
            self.proc.stdin.close()
            self.proc.wait(timeout=20)
        except Exception:  # noqa: BLE001
            self.proc.kill()
