"""Page navigating while the agent reads it should be waited out, not crash the run."""
import random
import unittest
from unittest.mock import Mock

from web_agent import WebAgent, is_navigation_race

RACE = Exception('Page.evaluate: Execution context was destroyed, most likely because of a navigation')


def make_agent():
    agent = WebAgent.__new__(WebAgent)
    agent.page = Mock(url='https://www.coursera.org/learn/x')
    agent.control = Mock(clock=lambda: 0, rng=random.Random(1))
    return agent


class NavigationRaceTests(unittest.TestCase):
    def test_detects_race_errors(self):
        self.assertTrue(is_navigation_race(RACE))
        self.assertFalse(is_navigation_race(RuntimeError('DOM target outside viewport')))

    def test_eval_retries_after_navigation(self):
        agent = make_agent()
        agent.page.evaluate.side_effect = [RACE, RACE, 42]
        self.assertEqual(agent._eval('scrollY'), 42)
        self.assertEqual(agent.page.wait_for_load_state.call_count, 2)

    def test_eval_gives_up_eventually(self):
        agent = make_agent()
        agent.page.evaluate.side_effect = RACE
        with self.assertRaises(Exception):
            agent._eval('scrollY')
        self.assertEqual(agent.page.evaluate.call_count, 4)

    def test_other_errors_are_not_swallowed(self):
        agent = make_agent()
        agent.page.evaluate.side_effect = ValueError('bad script')
        with self.assertRaises(ValueError):
            agent._eval('scrollY')
        self.assertEqual(agent.page.evaluate.call_count, 1)

    def test_browse_loop_survives_navigation_mid_step(self):
        agent = make_agent()
        times = iter([0, 0, 100, 100, 100])
        agent.control.clock = lambda: next(times, 100)
        agent.check_access = Mock()
        agent.activate = Mock()
        agent.ui = Mock()
        agent._browse_step = Mock(side_effect=RACE)
        agent.browse_until(60)
        self.assertGreaterEqual(agent._browse_step.call_count, 1)  # loop kept going, no crash
        events = [c.args[0] for c in agent.control.audit.emit.call_args_list]
        self.assertIn('page_navigated_during_step', events)


if __name__ == '__main__':
    unittest.main()
