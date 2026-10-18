"""Entry point for the packaged SyntheticHumanAgent.exe.

Double-click (no arguments) = same as RUN_LIVE.bat: prerequisite check, then the live session.
With arguments it behaves exactly like `python main.py ...`, e.g.
    SyntheticHumanAgent.exe --mode simulation
    SyntheticHumanAgent.exe --mode live --check
    SyntheticHumanAgent.exe install-browser      (download Playwright's Chromium once)
config.json / scenario.json are read from the folder the .exe is in, and runs\\ is created there.
"""
import os
import subprocess
import sys
from pathlib import Path


def app_dir():
    return Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent


def install_browser():
    from playwright._impl._driver import compute_driver_executable, get_driver_env
    driver = compute_driver_executable()
    command = [str(part) for part in driver] if isinstance(driver, (tuple, list)) else [str(driver)]
    return subprocess.call(command + ['install', 'chromium'], env=get_driver_env())


def chromium_missing():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        return not Path(p.chromium.executable_path).is_file()


def with_defaults(argv, base):
    argv = list(argv)
    for flag, name in (('--config', 'config.json'), ('--scenario', 'scenario.json')):
        if not any(a == flag or a.startswith(flag + '=') for a in argv):
            argv += [flag, str(base / name)]
    return argv


def run(argv):
    base = app_dir()
    os.chdir(base)  # so the default runs\ folder is created next to the .exe
    if argv[:1] == ['install-browser']:
        return install_browser()
    import main as agent
    if argv:
        return agent.main(with_defaults(argv, base))
    # Double-click: behave like RUN_LIVE.bat.
    if sys.platform == 'win32' and chromium_missing():
        print('Chromium for Playwright is not installed yet. Downloading it once (about 150 MB)...')
        if install_browser() != 0:
            print('Chromium download failed. Check the internet connection and try again.')
            return 2
    if agent.main(with_defaults(['--mode', 'live', '--check'], base)) != 0:
        return 2
    print('Starting the 15-minute session. F8 or a screen corner stops input.')
    code = agent.main(with_defaults(['--mode', 'live'], base))
    print(f'Session exit code: {code}')
    return code


if __name__ == '__main__':
    code = run(sys.argv[1:])
    if len(sys.argv) == 1 and sys.stdin is not None and sys.stdin.isatty():
        input('Press Enter to close this window...')
    raise SystemExit(code)
