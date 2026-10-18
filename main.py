"""Synthetic Human Agent submission: simulated by default, explicit live Windows mode."""
import argparse
import importlib.util
import json
from pathlib import Path
import signal
import sys
import threading
from settings import load_config, load_scenario, number
from session import run_session


def preflight(mode):
    issues = []
    if mode == 'live':
        if sys.platform != 'win32':
            issues.append('Live mode requires Windows with desktop Word installed.')
        for module in ('pyautogui', 'playwright', 'pythoncom', 'win32gui', 'win32process', 'win32com'):
            if importlib.util.find_spec(module) is None:
                issues.append('Missing dependency: '+module)
        if sys.platform == 'win32':
            import winreg
            try:
                with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, 'Word.Application\\CLSID'): pass
            except OSError:
                issues.append('Microsoft Word COM registration not found.')
        if importlib.util.find_spec('playwright'):
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                if not Path(p.chromium.executable_path).is_file():
                    issues.append('Run: python -m playwright install chromium')
    return {'mode': mode, 'ready': not issues, 'issues': issues,
            'manual_checks': ['US English keyboard layout', 'Primary monitor at 100% scaling',
                              'Word activated with initial dialogs dismissed', 'No interaction with run windows']
                             if mode == 'live' else []}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('simulation', 'live'), default='simulation')
    parser.add_argument('--config', type=Path, default=Path(__file__).with_name('config.json'))
    parser.add_argument('--scenario', type=Path, default=Path(__file__).with_name('scenario.json'))
    parser.add_argument('--output-dir', type=Path, default=Path('runs'))
    parser.add_argument('--duration', type=float, help='Override the 900-second session duration')
    parser.add_argument('--seed', type=int, help='Override the configured random seed')
    parser.add_argument('--check', action='store_true', help='Check prerequisites without starting desktop apps')
    args = parser.parse_args(argv)
    try:
        config, scenario = load_config(args.config), load_scenario(args.scenario)
        if args.duration is not None:
            config['duration_seconds'] = number(args.duration, 'duration')
        if args.seed is not None:
            config['seed'] = args.seed
        checks = preflight(args.mode)
    except Exception as exc:
        print(f'Configuration/preflight error: {exc}', file=sys.stderr)
        return 2
    if args.check or not checks['ready']:
        print(json.dumps(checks, indent=2))
        return 0 if checks['ready'] else 2
    if args.mode == 'live':
        # Establish consistent Windows screen coordinates before importing PyAutoGUI.
        import ctypes
        ctypes.windll.user32.SetProcessDPIAware()
        print('Live desktop session. F8 or a screen corner stops input. Do not use the desktop during the run.')
    stop = threading.Event()
    previous = {}
    for sig in (signal.SIGINT, signal.SIGTERM):
        previous[sig] = signal.signal(sig, lambda *_: stop.set())
    try:
        code, path = run_session(config, scenario, args.output_dir, args.mode, stop)
        print(f'Run outputs: {path}')
        print((path/'summary.json').read_text(encoding='utf-8'))
        return code
    except (ValueError, OSError) as exc:
        print(f'Could not create or persist run output: {exc}', file=sys.stderr)
        return 2
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


if __name__ == '__main__':
    raise SystemExit(main())
