"""Describe observed audit events; no human-equivalence or evasion score."""
import argparse
from collections import Counter
import json
from pathlib import Path
import statistics


def describe(values):
    if not values:
        return {'count': 0}
    ordered = sorted(values)
    return {'count': len(values), 'minimum': ordered[0], 'median': statistics.median(ordered),
            'p95': ordered[min(len(ordered)-1, int(.95*(len(ordered)-1)))], 'maximum': ordered[-1]}


def summarize(path):
    records = [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]
    if not records:
        raise ValueError('Empty audit log')
    run = records[0]['run_id']
    if any(r['run_id'] != run for r in records):
        raise ValueError('Metrics require a single run log')
    if [r['sequence'] for r in records] != list(range(1, len(records)+1)):
        raise ValueError('Audit sequence is incomplete')
    events = Counter(r['event'] for r in records)
    pauses = [r['details']['sampled_pause_seconds'] for r in records
              if r['event'] == 'key_sent' and 'sampled_pause_seconds' in r['details']]
    physical_keys = [r['elapsed_seconds'] for r in records
                     if r['event'] == 'key_sent' and r['details'].get('backend') == 'pyautogui']
    intervals = [b-a for a,b in zip(physical_keys, physical_keys[1:])]
    terminal = records[-1]['details'] if records[-1]['event'] == 'run_finished' else None
    return {'run_id': run, 'mode': records[0]['mode'], 'terminal_status': terminal.get('status') if terminal else 'incomplete',
            'event_counts': dict(events), 'sampled_key_pauses_seconds': describe(pauses),
            'observed_key_event_intervals_seconds': describe(intervals),
            'note': 'Inter-event intervals include correction delays and phase breaks. Samples are not evidence of human equivalence.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('audit_file', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(summarize(args.audit_file), indent=2))
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(2, f'Metrics error: {exc}\n')


if __name__ == '__main__':
    main()
