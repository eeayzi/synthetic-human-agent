from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from office_agent import OfficeAgent
from web_agent import WebAgent
from test_submission import control


class OfficeTests(unittest.TestCase):
    def make_agent(self, folder):
        c, desktop = control(), Mock()
        agent = OfficeAgent(desktop, c, Path(folder), .12)
        agent.app = Mock()
        agent.app.Documents.Count = 0
        agent.document = Mock()
        agent.document.Content.Text = '\r'
        agent.document.Content.End = 1
        agent.document.FullName = 'OwnedDocument'
        agent.document.ActiveWindow.Hwnd = 100
        agent.app.ActiveDocument.FullName = 'OwnedDocument'
        agent.owned = [agent.document]
        return agent

    def test_content_is_entered_through_typing_function(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent = self.make_agent(tmp)
            def simulate_native_typing(text, ui, c, probability):
                agent.document.Content.Text = text.replace('\n','\r')+'\r'
            with patch('office_agent.type_text', side_effect=simulate_native_typing) as typing:
                agent.append('Typed update\n')
            typing.assert_called_once()
            agent.document.Content.InsertAfter.assert_not_called()
            agent.document.Range.return_value.InsertAfter.assert_not_called()
            self.assertEqual(agent.expected, 'Typed update\n')

    def test_save_reopen_verifies_content_and_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent = self.make_agent(tmp)
            agent.expected = 'Expected report\n'
            agent.document.Content.Text = 'Expected report\r'
            agent.document.SaveAs2.side_effect = lambda **kwargs: Path(kwargs['FileName']).write_bytes(b'fake-docx-for-test')
            saved = Mock()
            saved.Content.Text = 'Expected report\r'
            agent.app.Documents.Open.return_value = saved
            result = agent.verify_saved()
            self.assertEqual(len(result['sha256']), 64)
            self.assertEqual(agent.owned, [saved])
            agent.app.Documents.Open.assert_called_once_with(FileName=str(agent.path), ReadOnly=True, AddToRecentFiles=False)

    def test_corrupted_reopened_file_is_not_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent = self.make_agent(tmp)
            agent.expected = 'Expected'
            agent.document.Content.Text = 'Expected\r'
            agent.document.SaveAs2.side_effect = lambda **kwargs: Path(kwargs['FileName']).write_bytes(b'fake')
            agent.app.Documents.Open.return_value.Content.Text = 'Wrong\r'
            with self.assertRaisesRegex(RuntimeError, 'differs'): agent.verify_saved()
            self.assertFalse(any(call.args[0]=='artifact_verified' for call in agent.control.audit.emit.call_args_list))

    def test_failed_save_never_reopens(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent = self.make_agent(tmp)
            agent.document.SaveAs2.side_effect = OSError('disk full')
            with self.assertRaises(OSError): agent.verify_saved()
            agent.app.Documents.Open.assert_not_called()

    def test_cleanup_closes_only_owned_document(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent = self.make_agent(tmp)
            app, doc = agent.app, agent.document
            app.Documents.Count = 1  # An unrelated document remains after our document is closed.
            agent.close()
            doc.Close.assert_called_once_with(SaveChanges=False)
            app.Quit.assert_not_called()
            app.Documents.Close.assert_not_called()

    def test_cleanup_failure_is_visible(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent = self.make_agent(tmp)
            agent.document.Close.side_effect = RuntimeError('busy')
            agent.app.Documents.Count = 1
            with self.assertRaisesRegex(RuntimeError, 'cleanup failed'): agent.close()
            self.assertTrue(agent.control.audit.emit.call_args.kwargs['errors'])

    def test_modified_text_is_not_silently_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent = self.make_agent(tmp)
            agent.document.Content.Text = 'User changed this'
            with patch('office_agent.type_text') as typing:
                with self.assertRaises(RuntimeError): agent.append('new')
                typing.assert_not_called()


class WebTests(unittest.TestCase):
    def make_agent(self):
        c, desktop = control(), Mock()
        agent = WebAgent(desktop,c,{'brief_url':'https://www.coursera.org/browse/computer-science',
                                   'reference_url':'https://www.coursera.org/learn/learning-how-to-learn'},Path('.'))
        agent.ui = Mock()
        agent.page = Mock()
        agent.activate = Mock()
        agent.check_access = Mock()
        agent.screen_point = Mock(return_value=(400,300))
        agent.page.locator.return_value.bounding_box.return_value={'x':100,'y':50,'width':40,'height':20}
        return agent

    def test_miscalibrated_pointer_never_clicks(self):
        agent=self.make_agent()
        agent.page.evaluate.side_effect=[{'x':100,'y':50,'width':40,'height':20},{'x':900,'y':900}]
        with patch('web_agent.move_mouse_human'):
            with self.assertRaisesRegex(RuntimeError,'calibration'): agent.click_reference_link()
        agent.ui.click.assert_not_called()

    def test_pointer_must_be_over_verified_link(self):
        agent=self.make_agent()
        agent.page.evaluate.side_effect=[{'x':100,'y':50,'width':40,'height':20},{'x':120,'y':60},False]
        with patch('web_agent.move_mouse_human'):
            with self.assertRaisesRegex(RuntimeError,'not over'): agent.click_reference_link()
        agent.ui.click.assert_not_called()

    def test_verified_pointer_click_uses_native_input(self):
        agent=self.make_agent()
        agent.page.evaluate.side_effect=[{'x':100,'y':50,'width':40,'height':20},{'x':120,'y':60},True]
        with patch('web_agent.move_mouse_human'): agent.click_reference_link()
        agent.ui.click.assert_called_once()
        agent.page.mouse.click.assert_not_called()
        agent.page.wait_for_url.assert_called_once()

    def test_browser_cleanup_stops_driver_even_when_close_fails(self):
        agent=self.make_agent()
        agent.browser, agent.manager=Mock(),Mock()
        manager=agent.manager
        agent.browser.close.side_effect=RuntimeError('close failed')
        with self.assertRaises(RuntimeError): agent.close()
        manager.stop.assert_called_once()


if __name__=='__main__': unittest.main()
