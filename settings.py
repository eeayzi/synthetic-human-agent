import json
import math
from pathlib import Path

PHASES = ('read_brief', 'draft_report', 'check_reference', 'finish_report', 'verify_and_review')


def number(value, name, minimum=0, inclusive=False):
    if (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
            or value < minimum or (value == minimum and not inclusive)):
        raise ValueError(f'{name} must be a finite number greater than {minimum}')
    return value


def load_config(path):
    data = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if not isinstance(data, dict) or set(data) != {'duration_seconds', 'seed', 'typo_probability', 'phases', 'websites'}:
        raise ValueError('Invalid config keys')
    number(data['duration_seconds'], 'duration_seconds')
    if isinstance(data['seed'], bool) or not isinstance(data['seed'], int):
        raise ValueError('seed must be an integer')
    number(data['typo_probability'], 'typo_probability', inclusive=True)
    if data['typo_probability'] > 1:
        raise ValueError('typo_probability must not exceed 1')
    if not isinstance(data['websites'], list) or not data['websites']:
        raise ValueError('config websites must be a non-empty list of URLs')
    phases = data['phases']
    if not isinstance(phases, list) or len(phases) != len(PHASES):
        raise ValueError('All five phases are required')
    for phase, expected in zip(phases, PHASES):
        if not isinstance(phase, dict) or set(phase) != {'name', 'share'} or phase['name'] != expected:
            raise ValueError('Phases must be in dependency order')
        number(phase['share'], 'phase share')
    if not math.isclose(sum(p['share'] for p in phases), 1, abs_tol=1e-9):
        raise ValueError('Phase shares must sum to 1')
    return data


def load_scenario(path):
    data = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if not isinstance(data, dict) or set(data) != {'title', 'brief', 'reference', 'draft', 'completion'}:
        raise ValueError('Invalid scenario keys')
    for name, value in data.items():
        if not isinstance(value, str) or not value.strip() or len(value) > 6000:
            raise ValueError(f'{name} must contain 1–6000 characters')
        if any((ord(c) < 32 and c != '\n') or ord(c) > 126 for c in value):
            raise ValueError('The keyboard demo supports printable ASCII and newlines only')
    if '\n' in data['title'] or len(data['title']) > 100:
        raise ValueError('title must be a single line up to 100 characters')
    return data
