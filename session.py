"""One five-phase session, preserving physical input and honest telemetry."""
from contextlib import ExitStack
import json
from pathlib import Path
import random
import threading
import time
import uuid

from audit import AuditLog
from runtime import RunControl, StopRequested
from typing_behavior import type_text


class VirtualClock:
    def __init__(self): self.now = 0.0
    def __call__(self): return self.now
    def wait(self, seconds): self.now += seconds


class SimulatedInput:
    backend = 'simulation'
    def __init__(self): self.text = ''
    def write(self, char): self.text += char
    def press(self, key):
        if key == 'backspace': self.text = self.text[:-1]
        elif key == 'enter': self.text += '\n'
        else: raise ValueError(key)


def run_session(config, scenario, output_root, mode='simulation', stop=None):
    if mode not in ('simulation', 'live'):
        raise ValueError('Unsupported mode')
    stop = stop or threading.Event()
    workspace = Path(output_root).resolve()/('run-'+uuid.uuid4().hex)
    workspace.mkdir(parents=True, exist_ok=False)
    status, error, evidence = 'failed', None, None
    cleanup_errors = []
    clock = VirtualClock() if mode == 'simulation' else time.monotonic
    started = clock()
    audit_path = workspace/'audit.jsonl'
    with AuditLog(audit_path, mode=mode) as audit:
        control = RunControl(stop, random.Random(config['seed']), audit,
                             started+config['duration_seconds'], clock=clock,
                             wait=clock.wait if mode == 'simulation' else None)
        audit.emit('run_started', config=config, scenario=scenario, mode=mode,
                   time_basis='virtual' if mode == 'simulation' else 'wall_clock', workspace=str(workspace))
        resources = ExitStack()
        web = office = None
        fake_input = SimulatedInput()
        try:
            control.check()
            if mode == 'live':
                from desktop import WindowsDesktop
                # from fixtures import pages, serve_pages
                from web_agent import WebAgent
                from office_agent import OfficeAgent
                desktop = WindowsDesktop()
                control.emergency = desktop.emergency
                marker = 'Synthetic-'+audit.run_id
                # origin = resources.enter_context(serve_pages(pages(scenario, marker)))
                web = WebAgent(desktop, control, marker, config)
                office = OfficeAgent(desktop, control, workspace, config['typo_probability'])
            boundary = started
            for index, phase in enumerate(config['phases']):
                boundary += config['duration_seconds']*phase['share']
                if index == len(config['phases'])-1:
                    boundary = control.deadline
                control.phase_deadline = boundary
                control.check()
                name = phase['name']
                audit.emit('phase_started', phase=name, scheduled_end_seconds=boundary-started,
                           session_elapsed_seconds=clock()-started)
                if mode == 'simulation':
                    audit.emit('action_simulated', phase=name, desktop_action_performed=False)
                    if name in ('draft_report', 'finish_report'):
                        text = scenario['draft' if name == 'draft_report' else 'completion']
                        type_text(text, fake_input, control, config['typo_probability'])
                    if name == 'verify_and_review':
                        if fake_input.text != scenario['draft']+scenario['completion']:
                            raise RuntimeError('Simulated typo correction changed intended text')
                        (workspace/'intended-report.txt').write_text(fake_input.text, encoding='utf-8')
                    control.idle_until(boundary, 'simulated_'+name)
                elif name == 'read_brief':
                    target_url = control.rng.choice(config['websites'])
                    web.open()
                    web.navigate(target_url)
                    web.browse_until(boundary)
                elif name == 'draft_report':
                    office.open()
                    office.append(scenario['draft'])
                    office.save_checkpoint()
                    office.review_until(boundary)
                elif name == 'check_reference':
                    target_url = control.rng.choice(config['websites'])
                    web.navigate(target_url)  # Navigate to a different real URL
                    web.browse_until(boundary)
                elif name == 'finish_report':
                    office.append(scenario['completion'])
                    office.save_checkpoint()
                    office.review_until(boundary)
                else:
                    evidence = office.verify_saved()
                    office.review_until(boundary)
                audit.emit('phase_completed', phase=name, session_elapsed_seconds=clock()-started)
            status = 'simulated' if mode == 'simulation' else 'completed'
        except StopRequested as exc:
            status, error = 'cancelled', str(exc)
        except KeyboardInterrupt:
            stop.set()
            status, error = 'cancelled', 'keyboard_interrupt'
        except Exception as exc:
            status, error = 'failed', f'{type(exc).__name__}: {exc}'
            audit.emit('action_failed', error=error)
        finally:
            activity_finished = clock()
            # Always attempt every cleanup, even if one adapter fails to close.
            for resource in (office, web, resources):
                if resource is not None:
                    try:
                        resource.close()
                    except Exception as exc:
                        cleanup_errors.append(f'{type(exc).__name__}: {exc}')
            if cleanup_errors and status in ('completed', 'simulated'):
                status, error = 'failed', 'resource_cleanup_failed'
            summary = {'schema_version': 1, 'run_id': audit.run_id, 'mode': mode, 'status': status,
                       'error': error, 'cleanup_errors': cleanup_errors, 'artifact': evidence,
                       'session_seconds': clock()-started,
                       'activity_seconds': activity_finished-started,
                       'cleanup_seconds': clock()-activity_finished,
                       'time_basis': 'virtual' if mode == 'simulation' else 'wall_clock',
                       'desktop_actions_verified': mode == 'live' and status == 'completed'}
            (workspace/'summary.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
            audit.emit('run_finished', **summary)
    return {'completed': 0, 'simulated': 0, 'failed': 1, 'cancelled': 130}[status], workspace
