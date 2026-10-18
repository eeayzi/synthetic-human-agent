"""Application ground truth. These records are not Windows/Sysmon events."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import threading
import time
import uuid


class AuditLog:
    def __init__(self, path, mode="simulation"):
        self.run_id = str(uuid.uuid4())
        self.mode = mode
        self.started = time.monotonic()
        self.sequence = 0
        self._lock = threading.Lock()
        self._file = Path(path).open("a", encoding="utf-8")

    def emit(self, event, **details):
        with self._lock:
            self.sequence += 1
            record = {
                "schema_version": 1, "run_id": self.run_id,
                "sequence": self.sequence,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "elapsed_seconds": time.monotonic() - self.started,
                "pid": os.getpid(), "ppid": os.getppid(),
                "mode": self.mode, "event": event, "details": details,
            }
            self._file.write(json.dumps(record, allow_nan=False) + "\n")
            self._file.flush()

    def close(self):
        self._file.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
