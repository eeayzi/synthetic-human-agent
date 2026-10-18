import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

MAIN = Path(__file__).with_name('main.py')


class CliTests(unittest.TestCase):
    def test_default_mode_is_virtual_and_has_consistent_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, str(MAIN), '--output-dir', tmp],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            folder = next(Path(tmp).glob('run-*'))
            summary = json.loads((folder/'summary.json').read_text())
            records = [json.loads(line) for line in (folder/'audit.jsonl').read_text().splitlines()]
            self.assertEqual(summary['status'], 'simulated')
            self.assertEqual(summary['activity_seconds'], 900)
            self.assertEqual(records[-1]['event'], 'run_finished')
            self.assertEqual([r['sequence'] for r in records], list(range(1,len(records)+1)))
            self.assertTrue(all(r['run_id']==summary['run_id'] for r in records))
            self.assertFalse(any(r['details'].get('backend')=='pyautogui' for r in records))

    def test_tiny_duration_does_not_report_completion(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, str(MAIN), '--output-dir', tmp, '--duration', '1'],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 130, result.stderr)

    def test_invalid_duration_creates_no_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, str(MAIN), '--output-dir', tmp, '--duration', 'nan'],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(list(Path(tmp).iterdir()), [])


if __name__=='__main__': unittest.main()
