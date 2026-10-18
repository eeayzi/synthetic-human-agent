import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from explorer_launcher import browser_arguments, read_debug_port
from web_agent import WebAgent
from web_policy import canonical_url, allowed_url, restriction_reason, AccessRestricted
from test_submission import control

URLS={'brief_url':'https://www.coursera.org/browse/computer-science',
      'reference_url':'https://www.coursera.org/learn/learning-how-to-learn'}


class PolicyTests(unittest.TestCase):
    def test_only_configured_public_pages(self):
        self.assertTrue(allowed_url(URLS['brief_url']+'/?utm_source=test',URLS.values()))
        for url in ('http://www.coursera.org/browse/computer-science',
                    'https://www.coursera.org.evil.example/browse/computer-science',
                    'https://user:pass@www.coursera.org/browse/computer-science',
                    'https://www.coursera.org/login','https://www.coursera.org/learn/not-configured',
                    'https://www.coursera.org:8443/browse/computer-science',
                    'https://www.coursera.org/browse/computer-science\n',None):
            self.assertFalse(allowed_url(url,URLS.values()),url)

    def test_visible_captcha_and_access_messages_stop(self):
        self.assertEqual(restriction_reason('Page','Text',captcha=True),'visible_captcha_or_challenge')
        self.assertIsNotNone(restriction_reason('Access Denied',''))
        self.assertIsNotNone(restriction_reason('Page','Please verify you are human.'))
        self.assertIsNotNone(restriction_reason('Page','',overlay=True))
        self.assertIsNone(restriction_reason('Security course','Learn how to build a CAPTCHA.'))

    def test_launch_retains_automation_and_uses_isolated_profile(self):
        args=browser_arguments(Path('C:/run/browser-profile'))
        self.assertIn('--enable-automation',args)
        self.assertIn('--remote-debugging-address=127.0.0.1',args)
        self.assertTrue(any(arg.startswith('--user-data-dir=') for arg in args))
        self.assertEqual(args[-1],'about:blank')
        self.assertFalse(any('disable-blink' in arg or 'user-agent' in arg for arg in args))

    def test_debug_port_requires_valid_endpoint_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'DevToolsActivePort'
            self.assertIsNone(read_debug_port(tmp))
            for content in ('','oops','70000\n/devtools/browser/x','1234\n/other'):
                path.write_text(content)
                self.assertIsNone(read_debug_port(tmp))
            path.write_text('1234\n/devtools/browser/unique')
            self.assertEqual(read_debug_port(tmp),1234)


class AccessTests(unittest.TestCase):
    def make_agent(self):
        agent=WebAgent(Mock(),control(),URLS,Path('.'))
        agent.page=Mock()
        agent.page.url=URLS['brief_url']
        agent.page.evaluate.return_value={'title':'Coursera','body':'Public catalogue','captcha':False,'overlay':False}
        return agent

    def test_captcha_stops_before_more_input(self):
        agent=self.make_agent()
        agent.page.evaluate.return_value['captcha']=True
        with self.assertRaises(AccessRestricted): agent.check_access(force=True)
        with self.assertRaises(AccessRestricted): agent._verify_before_input()
        events=[call.args[0] for call in agent.control.audit.emit.call_args_list]
        self.assertEqual(events.count('website_access_stopped'),1)

    def test_http_access_denial_is_not_retried(self):
        agent=self.make_agent()
        response=Mock(status=403)
        response.request.is_navigation_request.return_value=True
        response.request.frame=agent.page.main_frame
        agent._response(response)
        with self.assertRaisesRegex(AccessRestricted,'403'): agent.check_access()
        agent.page.reload.assert_not_called()

    def test_login_redirect_is_aborted(self):
        agent=self.make_agent()
        route=Mock()
        route.request.is_navigation_request.return_value=True
        route.request.frame=agent.page.main_frame
        route.request.url='https://www.coursera.org/login'
        agent._route_request(route)
        route.abort.assert_called_once()
        route.continue_.assert_not_called()
        with self.assertRaises(AccessRestricted): agent.check_access()

    def test_third_party_assets_can_load(self):
        agent=self.make_agent()
        route=Mock()
        route.request.is_navigation_request.return_value=False
        route.request.url='https://cdn.example/course-image.png'
        agent._route_request(route)
        route.continue_.assert_called_once()

    def test_missing_link_uses_typed_configured_url(self):
        agent=self.make_agent()
        agent.activate=Mock()
        agent.page.evaluate.return_value=None
        agent.navigate=Mock()
        agent.click_reference_link()
        agent.navigate.assert_called_once_with('reference')
        agent.page.mouse.click.assert_not_called()

    def test_owns_browser_before_closing_it(self):
        agent=self.make_agent()
        agent.browser,agent.cdp,agent.manager=Mock(),Mock(),Mock()
        cdp=agent.cdp
        agent.owned=True
        agent.close()
        cdp.send.assert_called_once_with('Browser.close')

    def test_unproven_browser_is_not_sent_close_command(self):
        agent=self.make_agent()
        agent.browser,agent.cdp=Mock(),Mock()
        cdp=agent.cdp
        agent.launcher.browser_requested=True
        agent.close()
        cdp.send.assert_not_called()
        self.assertTrue(agent.control.audit.emit.call_args.kwargs['manual_inspection_needed'])



class ExplorerLaunchTests(unittest.TestCase):
    def test_browser_is_started_by_enter_in_explorer_not_direct_popen(self):
        import types
        from explorer_launcher import ExplorerLauncher
        with tempfile.TemporaryDirectory() as tmp:
            executable=Path(tmp)/'chrome.exe';executable.write_bytes(b'placeholder')
            workspace=Path(tmp)/'run';workspace.mkdir()
            desktop=Mock();c=control();launcher=ExplorerLauncher(desktop,c,workspace)
            window=Mock();window.HWND=100
            window.Document.Folder.Self.Path=str(workspace)
            selected=window.Document.SelectedItems.return_value
            selected.Count=1;selected.Item.return_value.Path=str(launcher.shortcut)
            shell=Mock();shell.Windows.return_value=[window]
            script=Mock();link=script.CreateShortcut.return_value
            client=types.ModuleType('win32com.client')
            client.Dispatch=lambda name: script if name=='WScript.Shell' else shell
            com=Mock()
            modules={'pythoncom':com,'win32com':types.ModuleType('win32com'),'win32com.client':client}
            def entered(key):
                self.assertEqual(key,'enter')
                (launcher.profile/'DevToolsActivePort').write_text('1234\n/devtools/browser/run')
            desktop.owned_input.return_value.press.side_effect=entered
            with patch.dict('sys.modules',modules),patch('explorer_launcher.subprocess.Popen') as popen:
                endpoint=launcher.launch(executable)
                launcher.close()
            self.assertEqual(endpoint,'http://127.0.0.1:1234')
            self.assertEqual(link.TargetPath,str(executable))
            self.assertIn('--enable-automation',link.Arguments)
            self.assertEqual(Path(popen.call_args.args[0][0]).name.lower(),'explorer.exe')
            self.assertEqual(popen.call_args.kwargs,{'shell':False})
            desktop.owned_input.return_value.press.assert_called_once_with('enter')
            com.CoUninitialize.assert_called_once()

    def test_changed_explorer_selection_prevents_enter(self):
        import types
        from explorer_launcher import ExplorerLauncher
        with tempfile.TemporaryDirectory() as tmp:
            executable=Path(tmp)/'chrome.exe';executable.write_bytes(b'placeholder')
            workspace=Path(tmp)/'run';workspace.mkdir()
            desktop=Mock();launcher=ExplorerLauncher(desktop,control(),workspace)
            window=Mock();window.Document.Folder.Self.Path=str(workspace)
            window.HWND=100;window.Document.SelectedItems.return_value.Count=2
            shell=Mock();shell.Windows.return_value=[window]
            client=types.ModuleType('win32com.client');client.Dispatch=lambda name: Mock() if name=='WScript.Shell' else shell
            modules={'pythoncom':Mock(),'win32com':types.ModuleType('win32com'),'win32com.client':client}
            with patch.dict('sys.modules',modules),patch('explorer_launcher.subprocess.Popen'):
                try:
                    with self.assertRaisesRegex(RuntimeError,'selection changed'):launcher.launch(executable)
                finally:launcher.close()
            desktop.owned_input.return_value.press.assert_not_called()

class BlockedSessionTests(unittest.TestCase):
    def test_access_restriction_stops_before_office_work(self):
        from settings import load_config,load_scenario
        from session import run_session
        root=Path(__file__).parent
        web,office=Mock(),Mock()
        web.open.side_effect=AccessRestricted('visible_captcha_or_challenge')
        with tempfile.TemporaryDirectory() as tmp, patch('desktop.WindowsDesktop',return_value=Mock(emergency=Mock(return_value=None))), \
                patch('web_agent.WebAgent',return_value=web), patch('office_agent.OfficeAgent',return_value=office):
            code,folder=run_session(load_config(root/'config.json'),load_scenario(root/'scenario.json'),tmp,mode='live')
            summary=json.loads((folder/'summary.json').read_text())
        self.assertEqual(code,3)
        self.assertEqual(summary['status'],'blocked')
        self.assertFalse(summary['desktop_actions_verified'])
        office.open.assert_not_called()
        web.close.assert_called_once()


if __name__=='__main__': unittest.main()
