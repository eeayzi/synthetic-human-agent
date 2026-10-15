import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

MAIN = Path(__file__).with_name('main.py')


class CliTests(unittest.TestCase):
    def test_default_simulation_and_audit_are_consistent(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, str(MAIN), '--output-dir', tmp, '--pace', '.001'],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            folder = next(Path(tmp).glob('run-*'))
            summary = json.loads((folder/'summary.json').read_text())
            records = [json.loads(line) for line in (folder/'audit.jsonl').read_text().splitlines()]
            self.assertEqual(summary['status'], 'simulated')
            self.assertEqual(records[0]['event'], 'run_started')
            self.assertEqual(records[-1]['event'], 'run_finished')
            self.assertEqual([r['sequence'] for r in records], list(range(1, len(records)+1)))
            self.assertTrue(all(r['run_id'] == summary['run_id'] for r in records))
            self.assertTrue(all(r['mode'] == 'simulation' for r in records))

    def test_deadline_is_non_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, str(MAIN), '--output-dir', tmp, '--duration', '0.000001'],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 130, result.stderr)
            folder = next(Path(tmp).glob('run-*'))
            self.assertEqual(json.loads((folder/'summary.json').read_text())['status'], 'cancelled')

    def test_invalid_input_does_not_create_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, str(MAIN), '--output-dir', tmp, '--duration', 'nan'],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(list(Path(tmp).iterdir()), [])


if __name__ == '__main__': unittest.main()
