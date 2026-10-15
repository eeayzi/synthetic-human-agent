import json
import logging
from pathlib import Path
import random
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

from audit import AuditLog
from simulation_scheduler import load_config, run_scheduler
from process_prep import launch_process


class VirtualClock:
    def __init__(self):
        self.now = 0.0
        self.stopped = False
    def monotonic(self):
        return self.now
    def wait(self, seconds):
        self.now += seconds
    def is_set(self):
        return self.stopped
    def set(self):
        self.stopped = True


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config(Path(__file__).with_name("config.json"))
        self.logger = Mock()

    def run_virtual(self, seed=42, stopped=False):
        clock = VirtualClock()
        clock.stopped = stopped
        audit = Mock()
        with patch("simulation_scheduler.time.monotonic", clock.monotonic):
            result = run_scheduler(self.config, self.logger, clock,
                                   duration=20, interval=1, time_scale=.05,
                                   seed=seed, audit=audit)
        return result, audit, clock

    def test_seed_deadline_and_truthful_simulation(self):
        result, audit, clock = self.run_virtual()
        _, other, _ = self.run_virtual()
        self.assertEqual(result, 0)
        self.assertEqual(clock.now, 20)
        self.assertEqual(audit.mock_calls, other.mock_calls)
        states = [c.kwargs["state"] for c in audit.emit.call_args_list
                  if c.args[0] == "state_entered"]
        self.assertGreater(len(states), 2)
        self.assertTrue(all(a != b for a, b in zip(states, states[1:])))
        steps = [c for c in audit.emit.call_args_list if c.args[0] == "simulation_step"]
        self.assertTrue(steps)
        self.assertTrue(all(c.kwargs["desktop_action_performed"] is False for c in steps))

    def test_preexisting_stop_performs_no_steps(self):
        result, audit, clock = self.run_virtual(stopped=True)
        self.assertEqual(result, 0)
        self.assertEqual(clock.now, 0)
        self.assertFalse(any(c.args[0] == "simulation_step" for c in audit.emit.call_args_list))
        self.assertEqual(audit.emit.call_args.kwargs["reason"], "Stop signal received")

    def test_task_failure_is_not_success(self):
        with patch("simulation_scheduler.simulate_step", side_effect=RuntimeError("test failure")):
            result, audit, _ = self.run_virtual()
        self.assertEqual(result, 1)
        self.assertGreater(audit.emit.call_args.kwargs["failed_steps"], 0)

    def test_invalid_overrides(self):
        for bad in [0, -1, float("nan"), float("inf"), True]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                run_scheduler(self.config, self.logger, threading.Event(), duration=bad)

    def test_config_rejects_bad_weights(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"config.json"
            for bad in [True, -1, float("inf")]:
                self.config["states"]["web"]["weight"] = bad
                path.write_text(json.dumps(self.config))
                with self.assertRaises(ValueError):
                    load_config(path)

    def test_audit_append_and_run_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"audit.jsonl"
            for _ in range(2):
                with AuditLog(path) as audit:
                    audit.emit("run_started")
                    audit.emit("run_finished")
            records = [json.loads(line) for line in path.read_text().splitlines()]
        self.assertEqual([r["sequence"] for r in records], [1, 2, 1, 2])
        self.assertNotEqual(records[0]["run_id"], records[2]["run_id"])
        self.assertTrue(all(r["mode"] == "simulation" for r in records))
        self.assertTrue(all(r["timestamp_utc"].endswith("+00:00") for r in records))

    def test_launcher_keeps_literal_arguments_and_real_ancestry(self):
        audit = Mock()
        with patch("process_prep.subprocess.Popen", return_value=Mock(pid=123)) as popen:
            pid = launch_process(sys.executable, ["a b", "& literal"], audit=audit)
        self.assertEqual(pid, 123)
        popen.assert_called_once_with([sys.executable, "a b", "& literal"], shell=False)
        self.assertEqual(audit.emit.call_args.args[0], "process_created")

    def test_launch_failure_is_recorded_and_raised(self):
        audit = Mock()
        with patch("process_prep.subprocess.Popen", side_effect=OSError("failed")):
            with self.assertRaises(OSError):
                launch_process(sys.executable, audit=audit)
        self.assertEqual(audit.emit.call_args.args[0], "process_launch_failed")

    def test_launcher_rejects_ambiguous_inputs(self):
        with self.assertRaises(ValueError):
            launch_process("relative.exe")
        with self.assertRaises(TypeError):
            launch_process(sys.executable, "--one-string")


if __name__ == "__main__":
    unittest.main()
