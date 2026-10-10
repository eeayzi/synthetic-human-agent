"""Standalone simulated scheduler: log messages without controlling apps or the mouse."""

import argparse
import json
import logging
import math
from pathlib import Path
import random
import signal
import threading
import time


STATES = ("web", "office", "pause")


def load_config(path):
    with open(path, encoding="utf-8-sig") as file:
        config = json.load(file)
    if not isinstance(config, dict) or set(config) != {"total_duration", "log_interval", "states"}:
        raise ValueError("Config must contain exactly total_duration, log_interval, and states")

    def check_number(value, name, allow_zero=False):
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or value < 0
                or (not allow_zero and value == 0)):
            raise ValueError(f"{name} must be a finite {'nonnegative' if allow_zero else 'positive'} number")

    check_number(config["total_duration"], "Total duration")
    check_number(config["log_interval"], "Log interval")
    states = config["states"]
    if not isinstance(states, dict) or set(states) != set(STATES):
        raise ValueError("states must contain exactly web, office, and pause")
    for name, settings in states.items():
        if not isinstance(settings, dict) or set(settings) != {"weight", "duration_range"}:
            raise ValueError(f"{name} must contain exactly weight and duration_range")
        check_number(settings["weight"], f"{name} weight", allow_zero=True)
        bounds = settings["duration_range"]
        if not isinstance(bounds, list) or len(bounds) != 2:
            raise ValueError(f"{name} duration_range must be [minimum seconds, maximum seconds]")
        for value in bounds:
            check_number(value, f"{name} duration")
        if bounds[0] > bounds[1]:
            raise ValueError(f"{name} minimum duration cannot exceed maximum duration")
    weights = [settings["weight"] for settings in states.values()]
    if sum(weight > 0 for weight in weights) < 2:
        raise ValueError("At least two states must have positive weights to allow switching")
    if not math.isfinite(sum(weights)):
        raise ValueError("Total weight is too large")
    return config


def positive_seconds(value):
    number = float(value)
    if not 0 < number < float("inf"):
        raise argparse.ArgumentTypeError("Seconds must be a finite positive number")
    return number


def setup_logging(log_file):
    logger = logging.getLogger("scheduler")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger


def simulate_step(state, logger, deadline, stop_event):
    if stop_event.is_set() or time.monotonic() >= deadline:
        return
    if state == "web":
        logger.info("Simulated web task: browsing a webpage (logging only)")
        # 未来在这里接入队友的网页短操作函数。
        # 函数应接收 deadline 和 stop_event，并设置操作超时，不能无限等待输入。
    elif state == "office":
        logger.info("Simulated office task: working on a document (logging only)")
        # 未来在这里接入队友的办公短操作函数；空模块暂不导入。
        # 同样需要遵守 deadline，并及时响应 stop_event。
    else:
        logger.info("Pause: no task activity; the total timer continues")


def run_scheduler(config, logger, stop_event, duration=None, interval=None, time_scale=1):
    duration = config["total_duration"] if duration is None else duration
    interval = config["log_interval"] if interval is None else interval
    started = time.monotonic()
    total_deadline = started + duration
    previous_state = None
    reason = "Total duration reached"
    logger.info("Scheduler started: %.2f seconds; all tasks are simulated", duration)
    try:
        while time.monotonic() < total_deadline:
            if stop_event.is_set():
                reason = "Stop signal received"
                break
            if time.monotonic() >= total_deadline:
                break
            # 排除上一个状态，确保每次真正切换；权重在剩余候选中计算。
            candidates = [name for name in STATES
                          if name != previous_state and config["states"][name]["weight"] > 0]
            state = random.choices(candidates, weights=[config["states"][name]["weight"]
                                                       for name in candidates], k=1)[0]
            settings = config["states"][state]
            state_duration = random.uniform(*settings["duration_range"]) * time_scale
            deadline = min(total_deadline, time.monotonic() + state_duration)
            previous_state = state
            logger.info("Entering state: %s; duration %.2f seconds (limited by the total deadline)",
                        state, max(0, deadline - time.monotonic()))
            consecutive_errors = 0
            while not stop_event.is_set() and time.monotonic() < deadline:
                try:
                    simulate_step(state, logger, deadline, stop_event)
                    consecutive_errors = 0
                except Exception:
                    consecutive_errors += 1
                    logger.exception("%s task failed (consecutive failure %d)", state, consecutive_errors)
                    if consecutive_errors >= 3:
                        logger.error("Three consecutive failures; skipping remaining operations in this phase")
                        stop_event.wait(max(0, deadline - time.monotonic()))
                        break
                stop_event.wait(min(interval, max(0, deadline - time.monotonic())))
            if stop_event.is_set():
                reason = "Stop signal received"
                break
    except KeyboardInterrupt:
        stop_event.set()
        reason = "Stopped by Ctrl+C"
    except Exception:
        stop_event.set()
        reason = "Scheduler error"
        logger.exception("The scheduler encountered an error")
        return 1
    finally:
        # 未来在这里关闭本任务创建的浏览器或办公会话。
        # 不关闭用户原有窗口，不结束不属于本任务的进程。
        logger.info("Scheduler finished: %s; elapsed %.2f seconds", reason, time.monotonic() - started)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(Path(__file__).with_name("config.json")), help="Configuration file path")
    parser.add_argument("--duration", type=positive_seconds, help="Override total duration in seconds")
    parser.add_argument("--interval", type=positive_seconds, help="Override log interval in seconds")
    parser.add_argument("--time-scale", type=positive_seconds, default=1, help="State duration multiplier; use 0.01 for short tests; total duration is unaffected")
    parser.add_argument("--log-file", default=str(Path(__file__).with_name("scheduler.log")), help="Log file path; use an empty string for console output only")
    args = parser.parse_args()
    try:
        config = load_config(args.config)
    except (OSError, ValueError, OverflowError) as error:
        parser.exit(2, f"Configuration error: {error}\n")
    try:
        logger = setup_logging(args.log_file)
    except OSError as error:
        parser.exit(1, f"Cannot create log file: {error}\n")
    stop_event = threading.Event()
    previous_handler = signal.getsignal(signal.SIGINT)

    def request_stop(signum, frame):
        stop_event.set()

    signal.signal(signal.SIGINT, request_stop)
    try:
        return run_scheduler(config, logger, stop_event, args.duration, args.interval, args.time_scale)
    finally:
        signal.signal(signal.SIGINT, previous_handler)
        logging.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
