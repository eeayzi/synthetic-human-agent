"""Focus stolen by a popup/prompt/other app: recover and log instead of failing the run."""
import unittest
from unittest.mock import Mock

from desktop import GuardedInput, FocusLost, MAX_FOCUS_RECOVERIES

OWNED, OTHER = 100, 200


def make(foreground_sequence):
    desktop, control = Mock(), Mock()
    seq = list(foreground_sequence)
    desktop.gui.GetForegroundWindow.side_effect = lambda: seq.pop(0) if len(seq) > 1 else seq[0]
    desktop.gui.IsWindow.return_value = True
    desktop.gui.IsIconic.return_value = False
    desktop.gui.GetWindowText.return_value = 'Document1 - Word'
    desktop.gui.GetClassName.return_value = 'OpusApp'
    desktop.process.GetWindowThreadProcessId.return_value = (1, 42)
    return GuardedInput(desktop, OWNED, 42, control), desktop, control


def events(control):
    return [c.args[0] for c in control.audit.emit.call_args_list]


class FocusRecoveryTests(unittest.TestCase):
    def test_focus_is_taken_back_and_logged(self):
        ui, desktop, control = make([OTHER, OTHER, OWNED])
        ui.guard()
        desktop.gui.SetForegroundWindow.assert_called_with(OWNED)
        self.assertEqual(events(control), ['focus_lost', 'focus_recovered'])
        self.assertEqual(control.audit.emit.call_args_list[0].kwargs['foreground']['title'], 'Document1 - Word')

    def test_fails_if_windows_refuses_to_give_focus_back(self):
        ui, desktop, control = make([OTHER])
        with self.assertRaisesRegex(FocusLost, 'could not get it back'):
            ui.guard()

    def test_recoveries_are_capped(self):
        ui, desktop, control = make([OWNED])
        ui.focus_recoveries = MAX_FOCUS_RECOVERIES
        desktop.gui.GetForegroundWindow.side_effect = None
        desktop.gui.GetForegroundWindow.return_value = OTHER
        with self.assertRaisesRegex(FocusLost, 'too many times'):
            ui.guard()
        desktop.gui.SetForegroundWindow.assert_not_called()

    def test_closed_window_still_fails_immediately(self):
        ui, desktop, control = make([OWNED])
        desktop.gui.IsWindow.return_value = False
        with self.assertRaisesRegex(FocusLost, 'closed'):
            ui.guard()

    def test_no_recovery_needed_when_in_front(self):
        ui, desktop, control = make([OWNED])
        ui.guard()
        desktop.gui.SetForegroundWindow.assert_not_called()
        self.assertEqual(events(control), [])


if __name__ == '__main__':
    unittest.main()
