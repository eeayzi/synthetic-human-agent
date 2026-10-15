import json
from pathlib import Path
import random
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

from desktop import GuardedInput, FocusLost
from fixtures import pages
from metrics import summarize
from mouse_behavior import human_scroll, move_mouse_human
from runtime import RunControl, StopRequested
from session import VirtualClock, SimulatedInput, run_session
from settings import load_config, load_scenario
from typing_behavior import type_text, get_fatigue_multiplier

ROOT = Path(__file__).parent


def control(seed=42, duration=10000):
    clock = VirtualClock()
    return RunControl(threading.Event(), random.Random(seed), Mock(), duration, clock=clock, wait=clock.wait)


class TypingTests(unittest.TestCase):
    def test_typo_corrections_preserve_every_character(self):
        text = 'Quick brown fox jumps.\nBudget USD 559.00!\n'
        for seed in range(20):
            c, ui = control(seed), SimulatedInput()
            type_text(text, ui, c, typo_probability=1)
            self.assertEqual(ui.text, text)
            self.assertTrue(any(call.args[0] == 'typo_corrected' for call in c.audit.emit.call_args_list))

    def test_no_typo_mode_is_exact(self):
        c, ui = control(), SimulatedInput()
        type_text('Read the report.\n', ui, c, 0)
        self.assertEqual(ui.text, 'Read the report.\n')
        self.assertFalse(any(call.args[0] == 'typo_started' for call in c.audit.emit.call_args_list))

    def test_deadline_stops_typing(self):
        c, ui = control(duration=.15), SimulatedInput()
        with self.assertRaises(StopRequested): type_text('abcdef', ui, c, 0)
        self.assertLess(len(ui.text), 6)

    def test_emergency_stops_before_any_input(self):
        c, ui = control(), Mock()
        c.emergency = lambda: 'F8_pressed'
        with self.assertRaisesRegex(StopRequested, 'F8'): type_text('test', ui, c)
        ui.write.assert_not_called()

    def test_seed_repeats_timing(self):
        first, second = control(7), control(7)
        type_text('Workshop update.', SimulatedInput(), first, .8)
        type_text('Workshop update.', SimulatedInput(), second, .8)
        self.assertEqual(first.audit.emit.call_args_list, second.audit.emit.call_args_list)
        self.assertEqual(first.clock(), second.clock())

    def test_fatigue_capped(self):
        self.assertEqual(get_fatigue_multiplier(10000, 10), 1.3)

    def test_rejects_non_ascii_before_input(self):
        ui = Mock()
        with self.assertRaises(ValueError): type_text('hello é', ui, control())
        ui.write.assert_not_called()


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.desktop = Mock()
        self.desktop.gui.IsWindow.return_value = True
        self.desktop.gui.GetForegroundWindow.return_value = 100
        self.desktop.process.GetWindowThreadProcessId.return_value = (12, 34)
        self.desktop.gui.GetClassName.return_value = '_WwG'
        self.ui = GuardedInput(self.desktop, 100, 34, control())

    def test_foreground_loss_sends_nothing(self):
        self.desktop.gui.GetForegroundWindow.return_value = 200
        for action in (lambda: self.ui.write('x'), lambda: self.ui.press('enter'), self.ui.click,
                       lambda: self.ui.scroll(2), lambda: self.ui.hotkey('ctrl','s')):
            with self.assertRaises(FocusLost): action()
        self.assertEqual(self.desktop.input.method_calls, [])

    def test_pid_change_sends_nothing(self):
        self.desktop.process.GetWindowThreadProcessId.return_value = (12, 99)
        with self.assertRaises(FocusLost): self.ui.write('x')
        self.desktop.input.write.assert_not_called()

    def test_ribbon_focus_is_rejected(self):
        self.ui.word = True
        self.desktop.gui.GetClassName.return_value = 'Ribbon'
        with patch('desktop.gui_focus', return_value=101):
            with self.assertRaises(FocusLost): self.ui.write('x')
        self.desktop.input.write.assert_not_called()

    def test_valid_body_focus_sends_single_character(self):
        self.ui.word = True
        with patch('desktop.gui_focus', return_value=101): self.ui.write('x')
        self.desktop.input.write.assert_called_once_with('x', _pause=False)

    def test_wrong_active_document_stops_input(self):
        self.ui.verify = Mock(side_effect=RuntimeError('wrong document'))
        with self.assertRaises(RuntimeError): self.ui.write('x')
        self.desktop.input.write.assert_not_called()


class MouseTests(unittest.TestCase):
    def test_wheel_chunks_are_small_and_preserve_total(self):
        for amount in (-7, 0, 5):
            ui, c = Mock(), control()
            human_scroll(ui, amount, c)
            values = [call.args[0] for call in ui.scroll.call_args_list]
            self.assertEqual(sum(values), amount)
            self.assertTrue(all(1 <= abs(v) <= 3 for v in values))

    def test_curve_reaches_target_and_uses_guarded_steps(self):
        ui, c = Mock(), control()
        ui.desktop.input.position.return_value = (100,100)
        ui.desktop.input.size.return_value = (1920,1080)
        move_mouse_human(ui, 700,400,c)
        self.assertEqual(ui.move_to.call_args.args, (700,400))
        self.assertGreater(ui.move_to.call_count, 20)
        self.assertGreater(c.clock(), 0)

    def test_stop_prevents_cursor_path(self):
        ui, c = Mock(), control()
        ui.desktop.input.position.return_value = (100,100)
        ui.desktop.input.size.return_value = (1920,1080)
        ui.guard.side_effect = FocusLost('stop')
        with self.assertRaises(FocusLost): move_mouse_human(ui,200,200,c)
        ui.move_to.assert_not_called()


class SessionTests(unittest.TestCase):
    def test_full_virtual_session_and_metrics(self):
        cfg, scenario = load_config(ROOT/'config.json'), load_scenario(ROOT/'scenario.json')
        with tempfile.TemporaryDirectory() as tmp:
            code, folder = run_session(cfg, scenario, tmp)
            result = json.loads((folder/'summary.json').read_text())
            self.assertEqual((folder/'intended-report.txt').read_text(), scenario['draft']+scenario['completion'])
            self.assertFalse((folder/'workshop-report.docx').exists())
            metrics = summarize(folder/'audit.jsonl')
        self.assertEqual(code, 0)
        self.assertEqual(result['session_seconds'], 900)
        self.assertEqual(result['time_basis'], 'virtual')
        self.assertFalse(result['desktop_actions_verified'])
        self.assertEqual(metrics['event_counts']['phase_completed'], 5)
        self.assertGreater(metrics['event_counts']['typo_corrected'], 0)
        self.assertEqual(metrics['observed_key_event_intervals_seconds']['count'], 0)

    def test_insufficient_time_is_cancelled_not_success(self):
        cfg, scenario = load_config(ROOT/'config.json'), load_scenario(ROOT/'scenario.json')
        cfg['duration_seconds'] = 1
        with tempfile.TemporaryDirectory() as tmp:
            code, folder = run_session(cfg, scenario, tmp)
            result = json.loads((folder/'summary.json').read_text())
        self.assertEqual(code, 130)
        self.assertEqual(result['status'], 'cancelled')

    def test_preexisting_stop(self):
        stop = threading.Event(); stop.set()
        with tempfile.TemporaryDirectory() as tmp:
            code, folder = run_session(load_config(ROOT/'config.json'), load_scenario(ROOT/'scenario.json'), tmp, stop=stop)
            result = json.loads((folder/'summary.json').read_text())
        self.assertEqual(code, 130)
        self.assertEqual(result['session_seconds'], 0)

    def test_idle_normal_boundary_vs_stop(self):
        c = control(duration=10)
        c.idle_until(10, 'done')
        self.assertEqual(c.clock(), 10)
        c = control(duration=10)
        c.stop.set()
        with self.assertRaises(StopRequested): c.idle_until(10, 'cancel')

    def test_fixture_escapes_content(self):
        scenario = load_scenario(ROOT/'scenario.json')
        scenario['brief'] = '<script>bad</script>'
        result = pages(scenario, 'run-1')['/brief'].decode()
        self.assertNotIn('<script>', result)
        self.assertIn('&lt;script&gt;', result)

    def test_invalid_config_phase_order(self):
        cfg = json.loads((ROOT/'config.json').read_text())
        cfg['phases'].reverse()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'config.json'; path.write_text(json.dumps(cfg))
            with self.assertRaises(ValueError): load_config(path)

    def test_invalid_scenario_encoding(self):
        scenario=json.loads((ROOT/'scenario.json').read_text()); scenario['draft']='é'
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'scenario.json'; path.write_text(json.dumps(scenario))
            with self.assertRaises(ValueError): load_scenario(path)


if __name__ == '__main__': unittest.main()
