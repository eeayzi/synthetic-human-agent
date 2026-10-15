"""Per-run controls shared by every adapter. No global input or process killing."""
from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
import time


class Cancelled(Exception):
    pass


@dataclass
class RunControl:
    stop: object
    deadline: float
    rng: object
    audit: object
    pace: float = 1.0

    def check(self):
        if self.stop.is_set():
            raise Cancelled("stop_requested")
        if time.monotonic() >= self.deadline:
            raise Cancelled("deadline_reached")

    def timeout_ms(self):
        self.check()
        return max(1, min(10000, int((self.deadline - time.monotonic()) * 1000)))

    def pause(self, seconds=None):
        self.check()
        delay = seconds if seconds is not None else min(3, max(.15, self.rng.lognormvariate(-.4, .5)))
        delay *= self.pace
        if not math.isfinite(delay) or delay < 0:
            raise ValueError("pause must be finite and nonnegative")
        self.stop.wait(min(delay, max(0, self.deadline - time.monotonic())))
        self.check()


def artifact(path):
    path = Path(path)
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"Missing or empty artifact: {path.name}")
    return {"path": str(path.resolve()), "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
