"""Launch an executable normally, preserving its real process ancestry.

Returns the child PID for compatibility with office_agent. Launch success is
not evidence that the application is ready, a document exists, or work saved.
"""
import logging
import os
from pathlib import Path
import subprocess


def launch_process(app_path, args=(), *, audit=None):
    executable = Path(app_path).expanduser()
    if not executable.is_absolute() or not executable.is_file():
        raise ValueError("app_path must name an existing absolute executable path")
    if isinstance(args, (str, bytes)):
        raise TypeError("args must be a sequence of individual arguments")
    command = [str(executable), *map(str, args)]
    if audit is not None:
        audit.emit("process_launch_requested", executable=str(executable))
    try:
        process = subprocess.Popen(command, shell=False)
    except OSError as error:
        if audit is not None:
            audit.emit("process_launch_failed", error_type=type(error).__name__)
        raise
    logging.getLogger(__name__).info(
        "Process created: pid=%s launcher_pid=%s executable=%s",
        process.pid, os.getpid(), executable,
    )
    if audit is not None:
        audit.emit("process_created", child_pid=process.pid,
                   launcher_pid=os.getpid(), executable=str(executable))
    return process.pid

