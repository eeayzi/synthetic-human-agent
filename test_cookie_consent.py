"""Cookie/consent banner handling: answer it with a click instead of stopping the run."""
import random
import unittest
from unittest.mock import Mock, patch

from web_agent import WebAgent
from web_policy import AccessRestricted


def make_agent(snapshots, choice='reject'):
    agent = WebAgent.__new__(WebAgent)
    agent.page = Mock(url='https://www.coursera.org/learn/x')
    agent.page.evaluate.side_effect = lambda *a: dict(snapshots.pop(0) if len(snapshots) > 1 else snapshots[0])
    agent.restriction, agent.restriction_logged, agent.last_access_check = None, False, -1e9
    agent.consent_choice, agent.consent_attempts, agent._handling_consent = choice, 0, False
    agent.control = Mock(clock=lambda: 0, rng=random.Random(1))
    agent.ui = Mock()
    agent.screen_point = lambda x, y: (x, y)
    return agent


BASE = {'title': 'Course', 'body': 'text', 'captcha': False, 'overlay': False,
        'consent_visible': False, 'consent_button': None}
BANNER = dict(BASE, consent_visible=True, consent_button={'x': 100, 'y': 600, 'label': 'Reject All'})


class CookieConsentTests(unittest.TestCase):
    @patch('web_agent.move_mouse_human')
    def test_banner_is_clicked_not_blocked(self, move):
        agent = make_agent([BANNER, BASE])
        agent.check_access(force=True)
        move.assert_called_once()
        agent.ui.click.assert_called_once()
        self.assertIsNone(agent.restriction)
        events = [c.args[0] for c in agent.control.audit.emit.call_args_list]
        self.assertEqual(events, ['cookie_consent_detected', 'cookie_consent_answered'])

    def test_stop_mode_keeps_old_behaviour(self):
        agent = make_agent([BANNER], choice='stop')
        with self.assertRaisesRegex(AccessRestricted, 'cookie_consent'):
            agent.check_access(force=True)
        agent.ui.click.assert_not_called()

    def test_banner_without_matching_button_blocks(self):
        agent = make_agent([dict(BANNER, consent_button=None)])
        with self.assertRaisesRegex(AccessRestricted, 'cookie_consent'):
            agent.check_access(force=True)

    @patch('web_agent.move_mouse_human')
    def test_gives_up_after_repeated_attempts(self, move):
        agent = make_agent([BANNER])
        for _ in range(3):
            agent.check_access(force=True)
        with self.assertRaises(AccessRestricted):
            agent.check_access(force=True)
        self.assertEqual(agent.ui.click.call_count, 3)

    def test_other_dialogs_still_block(self):
        agent = make_agent([dict(BASE, overlay=True)])
        with self.assertRaisesRegex(AccessRestricted, 'page_dialog_requires_attention'):
            agent.check_access(force=True)

    @patch('web_agent.move_mouse_human')
    def test_ordinary_popup_is_dismissed_not_blocked(self, move):
        popup = dict(BASE, overlay=True, dialog_info='Deliver to Singapore',
                     dialog_button={'x': 300, 'y': 120, 'label': 'Dismiss'})
        agent = make_agent([popup, BASE])
        agent.check_access(force=True)
        agent.ui.click.assert_called_once()
        self.assertIsNone(agent.restriction)
        events = [c.args[0] for c in agent.control.audit.emit.call_args_list]
        self.assertEqual(events, ['page_dialog_detected', 'page_dialog_dismissed'])

    def test_popup_without_button_gets_escape(self):
        agent = make_agent([dict(BASE, overlay=True, dialog_info='Promo'), BASE])
        agent.check_access(force=True)
        agent.ui.press.assert_called_once_with('escape')
        self.assertIsNone(agent.restriction)

    def test_signin_dialog_still_blocks(self):
        agent = make_agent([dict(BASE, overlay=True, signin_dialog=True,
                                 dialog_button={'x': 1, 'y': 1, 'label': 'Close'})])
        with self.assertRaisesRegex(AccessRestricted, 'page_dialog_requires_attention'):
            agent.check_access(force=True)
        agent.ui.click.assert_not_called()

    @patch('web_agent.move_mouse_human')
    def test_intercepted_physical_click_falls_back_to_page_mouse(self, move):
        # Banner stays after the OS click (12 checks), then goes away after page.mouse.click.
        agent = make_agent([BANNER] + [BANNER] * 12 + [BASE])
        agent.check_access(force=True)
        agent.ui.click.assert_called_once()
        agent.page.mouse.click.assert_called_once_with(100, 600)
        events = [c.args[0] for c in agent.control.audit.emit.call_args_list]
        self.assertIn('physical_click_intercepted', events)
        answered = agent.control.audit.emit.call_args_list[-1]
        self.assertEqual(answered.kwargs['backend'], 'playwright_mouse_fallback')
        self.assertTrue(answered.kwargs['banner_closed'])

    def test_captcha_still_wins_over_banner(self):
        agent = make_agent([dict(BANNER, captcha=True)])
        with self.assertRaisesRegex(AccessRestricted, 'captcha'):
            agent.check_access(force=True)
        agent.ui.click.assert_not_called()


if __name__ == '__main__':
    unittest.main()
