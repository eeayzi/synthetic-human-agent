"""Dependency-ordered workflow with explicit simulation and live results."""
import json
from pathlib import Path
import random
import time
import uuid

from audit import AuditLog
from runtime import Cancelled, RunControl
from scenario import load_scenario


def run_workflow(scenario_path, output_root, stop, *, mode="simulation", duration=900,
                 pace=1, seed=42, headless=False, adapters=None):
    import math
    if mode not in ("simulation", "live"):
        raise ValueError("Unknown mode")
    for name, value in (("duration", duration), ("pace", pace)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be finite and positive")
    data = load_scenario(scenario_path)
    workspace = Path(output_root).resolve() / ("run-" + uuid.uuid4().hex)
    workspace.mkdir(parents=True, exist_ok=False)
    status = "failed"
    results = {}
    error = None
    with AuditLog(workspace / "audit.jsonl", mode=mode) as audit:
        control = RunControl(stop, time.monotonic() + duration, random.Random(seed), audit, pace)
        audit.emit("run_started", seed=seed, duration=duration, pace=pace,
                   scenario=data, workspace=str(workspace), backend="simulation" if mode == "simulation" else "playwright_and_office_com")
        try:
            control.check()
            if mode == "simulation":
                for step in ("read_brief", "create_budget", "create_report"):
                    control.check()
                    audit.emit("action_simulated", action=step, desktop_action_performed=False)
                    control.pause(.01)
                results = {"planned_total": data["total"], "currency": data["currency"]}
                status = "simulated"
            else:
                if adapters is None:
                    from web_agent import read_brief
                    from office_agent import create_budget, create_report
                    adapters = (read_brief, create_budget, create_report)
                web, budget, report = adapters
                steps = (("read_brief", lambda: web(data, workspace, control, headless=headless)),
                         ("create_budget", lambda: budget(data, workspace, control)),
                         ("create_report", lambda: report(data, results["create_budget"], workspace, control)))
                for name, action in steps:
                    control.check()
                    audit.emit("action_started", action=name)
                    results[name] = action()
                    control.check()
                    audit.emit("action_completed", action=name, result=results[name])
                status = "completed"
        except Cancelled as exc:
            status, error = "cancelled", str(exc)
        except KeyboardInterrupt:
            stop.set()
            status, error = "cancelled", "keyboard_interrupt"
        except Exception as exc:
            status, error = "failed", f"{type(exc).__name__}: {exc}"
            audit.emit("action_failed", error=error)
        finally:
            summary = {"schema_version": 1, "run_id": audit.run_id, "mode": mode,
                       "status": status, "error": error, "results": results,
                       "desktop_actions_verified": mode == "live" and status == "completed"}
            (workspace / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
            audit.emit("run_finished", **summary)
    return {"completed": 0, "simulated": 0, "cancelled": 130, "failed": 1}[status], workspace
