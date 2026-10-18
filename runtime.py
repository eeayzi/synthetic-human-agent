"""Deadline-aware controls and auditable waits for one desktop session."""
import hashlib
from pathlib import Path
import time


class StopRequested(Exception):
    pass


class RunControl:
    def __init__(self, stop, rng, audit, deadline, clock=time.monotonic, wait=None, emergency=None):
        self.stop, self.rng, self.audit = stop, rng, audit
        self.deadline, self.clock = deadline, clock
        self.wait = wait or stop.wait
        self.emergency = emergency or (lambda: None)
        self.phase_deadline = deadline

    def wait_for(self, condition_callable, timeout_seconds, description="condition"):
        """Waits for a condition to become true, checking periodically."""
        start_time = self.clock()
        while self.clock() - start_time < timeout_seconds:
            self.check() # Check for session stop requests
            if condition_callable():
                return
            self.wait(0.1) # Brief pause between checks
        raise TimeoutError(f"Timed out waiting for {description}")

    def check(self):
        reason = self.emergency()
        if reason:
            self.stop.set()
            raise StopRequested(reason)
        if self.stop.is_set():
            raise StopRequested("stop_requested")
        if self.clock() >= min(self.deadline, self.phase_deadline):
            raise StopRequested("action_deadline_reached")

    def pause(self, seconds):
        target = self.clock() + seconds
        while self.clock() < target:
            self.check()
            self.wait(min(.1, target - self.clock(), max(0, self.phase_deadline - self.clock())))
        self.check()

    def idle_until(self, target, label, guard=None):
        """Normal completion at the phase boundary; cancellation is still polled."""
        self.audit.emit("reading_pause_started", label=label, planned_seconds=max(0, target-self.clock()))
        while self.clock() < target:
            self.check()
            if guard:
                guard()
            self.wait(min(.1, target - self.clock()))
        # A stop at the boundary must not be mistaken for successful completion.
        reason = self.emergency()
        if reason or self.stop.is_set():
            raise StopRequested(reason or "stop_requested")
        self.audit.emit("reading_pause_finished", label=label)

    def timeout_ms(self):
        self.check()
        return max(1, min(10000, int((min(self.deadline, self.phase_deadline)-self.clock())*1000)))


def file_evidence(path):
    path = Path(path)
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError("Missing or empty saved document")
    return {"path": str(path.resolve()), "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
