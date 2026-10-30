"""États de job persistants (fichiers JSON dans jobs/). Un job reprend là où il s'est arrêté."""
import json
import time
from pathlib import Path

STATES = ["queued", "building", "rendering", "encoding", "qa", "done", "failed"]


class Job:
    def __init__(self, path):
        self.path = Path(path)
        self.data = json.loads(self.path.read_text(encoding="utf-8"))
        self.data.setdefault("status", "queued")
        self.data.setdefault("history", [])

    @property
    def id(self):
        return self.data["id"]

    @property
    def status(self):
        return self.data["status"]

    def set(self, status, **info):
        assert status in STATES, status
        self.data["status"] = status
        self.data["history"].append({"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "status": status, **info})
        self.save()

    def update(self, **fields):
        self.data.update(fields)
        self.save()

    def save(self):
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)  # écriture atomique
