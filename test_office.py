from contextlib import contextmanager
from pathlib import Path
import random
import tempfile
import threading
import time
import types
import unittest
from unittest.mock import Mock, patch

import office_agent
from runtime import RunControl
from scenario import load_scenario


class Cell:
    def __init__(self):
        self.Value = None
        self.Formula = None


class Sheet:
    def __init__(self):
        self.cells = {}
    def Cells(self, row, col):
        return self.cells.setdefault((row, col), Cell())
    def Range(self, *args): return Mock()
    def Columns(self, *args): return Mock()
    def calculate(self):
        for (row, col), cell in self.cells.items():
            if cell.Formula and cell.Formula.startswith('=B'):
                cell.Value = self.Cells(row, 2).Value * self.Cells(row, 3).Value
        for (row, col), cell in self.cells.items():
            if cell.Formula and cell.Formula.startswith('=SUM'):
                cell.Value = sum(self.Cells(r, 4).Value for r in range(2, row))


class Book:
    def __init__(self): self.sheet = Sheet()
    def Worksheets(self, *args): return self.sheet
    def SaveAs(self, Filename, FileFormat):
        Path(Filename).write_bytes(b'fake xlsx for orchestration test')
    def Close(self, **kwargs): pass


class Text:
    Text = ''
    def InsertAfter(self, value): self.Text += value


class Document:
    def __init__(self): self.Content = Text()
    def SaveAs2(self, FileName, **kwargs):
        Path(FileName).write_bytes(b'fake docx for orchestration test')
    def Close(self, **kwargs): pass


class OfficeTests(unittest.TestCase):
    def setUp(self):
        observer = patch.object(office_agent, 'observe_office_process')
        observer.start()
        self.addCleanup(observer.stop)
        self.data = load_scenario(Path(__file__).with_name('scenario.json'))
        self.audit = Mock(run_id='test-run')
        self.control = RunControl(threading.Event(), time.monotonic()+60, random.Random(1), self.audit, .00001)

    def test_budget_reopens_and_checks_formulas_and_values(self):
        book = Book()
        app = Mock()
        app.Workbooks.Add.return_value = book
        app.Workbooks.Open.return_value = book
        app.Calculate.side_effect = book.sheet.calculate
        @contextmanager
        def session(*args): yield app, []
        with tempfile.TemporaryDirectory() as tmp, patch.object(office_agent, 'office_session', session):
            result = office_agent.create_budget(self.data, Path(tmp), self.control)
            self.assertEqual(result['total'], '559.00')
            self.assertEqual(len(result['sha256']), 64)
            app.Workbooks.Open.assert_called_once()
            self.assertEqual(book.sheet.Cells(5, 4).Formula, '=SUM(D2:D4)')

    def test_corrupt_saved_budget_fails_verification(self):
        book = Book()
        app = Mock()
        app.Workbooks.Add.return_value = book
        app.Calculate.side_effect = book.sheet.calculate
        def corrupt(**kwargs):
            book.sheet.Cells(2, 4).Value = 0
            return book
        app.Workbooks.Open.side_effect = corrupt
        @contextmanager
        def session(*args): yield app, []
        with tempfile.TemporaryDirectory() as tmp, patch.object(office_agent, 'office_session', session):
            with self.assertRaisesRegex(RuntimeError, 'row 2'):
                office_agent.create_budget(self.data, Path(tmp), self.control)
        self.assertFalse(any(c.args[0] == 'artifact_verified' for c in self.audit.emit.call_args_list))

    def test_report_reopens_and_verifies_all_content(self):
        doc = Document()
        app = Mock()
        app.Documents.Add.return_value = doc
        app.Documents.Open.return_value = doc
        @contextmanager
        def session(*args): yield app, []
        with tempfile.TemporaryDirectory() as tmp, patch.object(office_agent, 'office_session', session):
            result = office_agent.create_report(self.data, {'total': '559.00'}, Path(tmp), self.control)
            self.assertIn('USD 559.00', doc.Content.Text)
            self.assertEqual(len(result['sha256']), 64)
            app.Documents.Open.assert_called_once()

    def test_corrupt_saved_report_fails(self):
        doc = Document()
        wrong = Document()
        wrong.Content.Text = 'wrong saved content'
        app = Mock()
        app.Documents.Add.return_value = doc
        app.Documents.Open.return_value = wrong
        @contextmanager
        def session(*args): yield app, []
        with tempfile.TemporaryDirectory() as tmp, patch.object(office_agent, 'office_session', session):
            with self.assertRaisesRegex(RuntimeError, 'content'):
                office_agent.create_report(self.data, {'total': '559.00'}, Path(tmp), self.control)

    def test_cleanup_closes_only_owned_documents_and_preserves_other_documents(self):
        app = Mock()
        app.Documents.Count = 1
        doc = Mock()
        pythoncom = Mock()
        client = types.ModuleType('win32com.client')
        client.DispatchEx = Mock(return_value=app)
        modules = {'pythoncom': pythoncom, 'win32com': types.ModuleType('win32com'), 'win32com.client': client}
        with patch.dict('sys.modules', modules), patch.object(office_agent.sys, 'platform', 'win32'):
            with self.assertRaisesRegex(RuntimeError, 'action failed'):
                with office_agent.office_session('Word.Application', 'Documents', self.control) as (_, owned):
                    owned.append(doc)
                    raise RuntimeError('action failed')
        doc.Close.assert_called_once_with(SaveChanges=False)
        app.Quit.assert_not_called()
        pythoncom.CoUninitialize.assert_called_once()

    def test_failed_initialization_still_quits_empty_owned_instance(self):
        app = Mock()
        app.Documents.Count = 0
        pythoncom = Mock()
        client = types.ModuleType('win32com.client')
        client.DispatchEx = Mock(return_value=app)
        modules = {'pythoncom': pythoncom, 'win32com': types.ModuleType('win32com'), 'win32com.client': client}
        self.audit.emit.side_effect = OSError('disk full')
        with patch.dict('sys.modules', modules), patch.object(office_agent.sys, 'platform', 'win32'):
            with self.assertRaises(OSError):
                with office_agent.office_session('Word.Application', 'Documents', self.control): pass
        app.Quit.assert_called_once()
        pythoncom.CoUninitialize.assert_called_once()


if __name__ == '__main__': unittest.main()
