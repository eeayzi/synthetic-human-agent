from pathlib import Path
import random
import tempfile
import threading
import time
import types
import unittest
from unittest.mock import Mock, patch

from runtime import RunControl
from scenario import load_scenario
from web_agent import read_brief


class BrowserTests(unittest.TestCase):
    def environment(self, mismatch=False):
        browser = Mock()
        context = browser.new_context.return_value
        page = context.new_page.return_value
        def locator(selector):
            result = Mock()
            if selector == 'h1':
                result.inner_text.return_value = 'wrong' if mismatch else 'Synthetic team workshop'
            elif selector == 'table tr': result.count.return_value = 4
            else: result.inner_text.return_value = 'Instructions'
            return result
        page.locator.side_effect = locator
        manager = Mock()
        manager.__enter__ = Mock(return_value=manager)
        manager.__exit__ = Mock(return_value=False)
        manager.chromium.launch.return_value = browser
        api = types.ModuleType('playwright.sync_api')
        api.sync_playwright = Mock(return_value=manager)
        modules = {'playwright': types.ModuleType('playwright'), 'playwright.sync_api': api}
        control = RunControl(threading.Event(), time.monotonic()+10, random.Random(1), Mock(), .00001)
        return modules, browser, context, control

    def test_local_brief_verification_and_network_policy(self):
        modules, browser, context, control = self.environment()
        data = load_scenario(Path(__file__).with_name('scenario.json'))
        with tempfile.TemporaryDirectory() as tmp, patch.dict('sys.modules', modules):
            result = read_brief(data, Path(tmp), control, headless=True)
            handler = context.route.call_args.args[1]
            allowed = Mock()
            allowed.request.url = 'https://synthetic.invalid/brief'
            allowed.request.is_navigation_request.return_value = True
            handler(allowed)
            allowed.fulfill.assert_called_once()
            denied = Mock()
            denied.request.url = 'https://external.example/'
            handler(denied)
            denied.abort.assert_called_once()
        self.assertEqual(result['rows'], 3)
        browser.new_context.assert_called_once_with(accept_downloads=False, service_workers='block')
        browser.close.assert_called_once()

    def test_verification_failure_still_closes_browser(self):
        modules, browser, context, control = self.environment(mismatch=True)
        data = load_scenario(Path(__file__).with_name('scenario.json'))
        with tempfile.TemporaryDirectory() as tmp, patch.dict('sys.modules', modules):
            with self.assertRaisesRegex(RuntimeError, 'title'):
                read_brief(data, Path(tmp), control)
        browser.close.assert_called_once()


if __name__ == '__main__': unittest.main()
