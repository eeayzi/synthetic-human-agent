"""Run the connected synthetic office workflow; defaults to simulation."""
import argparse
import importlib.util
import json
from pathlib import Path
import signal
import sys
import threading

from simulation_scheduler import positive_seconds
from workflow import run_workflow


def preflight(mode):
    checks = {"python": sys.version.split()[0], "mode": mode, "ready": True, "issues": []}
    if mode == "live":
        if sys.platform != "win32":
            checks["issues"].append("Live workflow requires Windows with desktop Word and Excel.")
        for module in ("playwright", "pythoncom", "win32com"):
            if importlib.util.find_spec(module) is None:
                checks["issues"].append(f"Missing dependency: {module}")
        if sys.platform == "win32":
            import winreg
            for progid in ("Word.Application", "Excel.Application"):
                try:
                    with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, progid + "\\CLSID"):
                        pass
                except OSError:
                    checks["issues"].append(f"Office registration missing: {progid}")
        if importlib.util.find_spec("playwright") is not None:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                if not Path(p.chromium.executable_path).is_file():
                    checks["issues"].append("Chromium missing: run python -m playwright install chromium")
    checks["ready"] = not checks["issues"]
    return checks


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("simulation", "live"), default="simulation")
    parser.add_argument("--scenario", type=Path, default=Path(__file__).with_name("scenario.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("runs"))
    parser.add_argument("--duration", type=positive_seconds, default=900, help="Maximum work budget, not a minimum runtime")
    parser.add_argument("--pace", type=positive_seconds, default=1, help="Multiplier for sampled pauses")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--headless", action="store_true", help="Hide browser only; Office remains visible")
    parser.add_argument("--check", action="store_true", help="Report prerequisites without opening desktop apps")
    args = parser.parse_args(argv)
    try:
        checks = preflight(args.mode)
    except Exception as error:
        parser.exit(2, f"Preflight failed: {error}\n")
    if args.check or not checks["ready"]:
        print(json.dumps(checks, indent=2))
        return 0 if checks["ready"] else 2
    stop = threading.Event()
    handlers = {}
    def request_stop(*_):
        stop.set()
    for sig in (signal.SIGINT, signal.SIGTERM):
        handlers[sig] = signal.signal(sig, request_stop)
    try:
        code, workspace = run_workflow(args.scenario, args.output_dir, stop,
                                      mode=args.mode, duration=args.duration, pace=args.pace,
                                      seed=args.seed, headless=args.headless)
        print(f"Run outputs: {workspace}")
        print((workspace / "summary.json").read_text(encoding="utf-8"))
        return code
    except (ValueError, OSError) as error:
        print(f"Run could not start or persist audit output: {error}", file=sys.stderr)
        return 2
    finally:
        for sig, handler in handlers.items():
            signal.signal(sig, handler)


if __name__ == "__main__":
    raise SystemExit(main())


          
                
