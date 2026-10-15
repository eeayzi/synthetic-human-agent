"""Word content is typed through PyAutoGUI; COM is setup/save/readback only."""
from runtime import file_evidence
from typing_behavior import type_text


def normalized(text):
    return text.replace('\r\n', '\n').replace('\r', '\n').rstrip('\n')


class OfficeAgent:
    def __init__(self, desktop, control, workspace, typo_probability):
        self.desktop, self.control, self.workspace = desktop, control, workspace
        self.typo_probability = typo_probability
        self.app = self.document = self.pythoncom = self.ui = None
        self.expected = ''
        self.owned = []
        self.settings = {}
        self.path = (workspace/'workshop-report.docx').resolve()

    def open(self):
        import pythoncom
        from win32com.client import DispatchEx
        self.control.check()
        pythoncom.CoInitialize()
        self.pythoncom = pythoncom
        try:
            self.app = DispatchEx('Word.Application')
            self.app.Visible = True
            for name in ('DisplayAlerts', 'AutomationSecurity'):
                self.settings[name] = getattr(self.app, name)
            self.app.DisplayAlerts = 0
            self.app.AutomationSecurity = 3
            self.document = self.app.Documents.Add()
            self.owned.append(self.document)
            self.activate_for_typing()
            self.control.audit.emit('office_opened', backend='word_com_setup', input_backend='pyautogui',
                                    observed_pid=self.ui.pid, window_handle=int(self.ui.hwnd))
        except BaseException:
            self.close()
            raise

    def verify_active(self):
        if self.app.ActiveDocument.FullName != self.document.FullName:
            raise RuntimeError('Active Word document changed; no more input sent')

    def activate_for_typing(self):
        self.control.check()
        self.document.Activate()
        hwnd = int(self.document.ActiveWindow.Hwnd)
        self.desktop.activate(hwnd, self.control)
        # Select the insertion point, not document content. Content entry remains OS input.
        end = max(0, self.document.Content.End-1)
        self.document.Range(end, end).Select()
        self.control.pause(.2)
        self.ui = self.desktop.owned_input(hwnd, self.control, word=True, verify=self.verify_active)
        self.ui.guard()

    def append(self, text):
        self.activate_for_typing()
        self.verify_text()
        self.control.audit.emit('typing_started', backend='pyautogui', characters=len(text))
        type_text(text, self.ui, self.control, self.typo_probability)
        self.expected += text
        self.verify_text()
        self.control.audit.emit('typing_verified', backend='word_com_readback', characters=len(self.expected))

    def verify_text(self):
        if normalized(self.document.Content.Text) != normalized(self.expected):
            raise RuntimeError('Typed text differs from expected text; check keyboard layout, AutoCorrect or focus')

    def save_checkpoint(self):
        self.control.check()
        self.verify_text()
        if self.path.exists():
            self.document.Save()
        else:
            self.document.SaveAs2(FileName=str(self.path), FileFormat=12, AddToRecentFiles=False)
        self.control.audit.emit('document_saved', backend='word_com_save', **file_evidence(self.path))

    def verify_saved(self):
        self.save_checkpoint()
        self.document.Close(SaveChanges=False)
        self.owned.remove(self.document)
        self.document = None
        self.control.check()
        self.document = self.app.Documents.Open(FileName=str(self.path), ReadOnly=True, AddToRecentFiles=False)
        self.owned.append(self.document)
        self.verify_text()
        evidence = file_evidence(self.path)
        self.control.audit.emit('artifact_verified', backend='word_com_reopen', **evidence)
        return evidence

    def review_until(self, target):
        self.document.Activate()
        hwnd = int(self.document.ActiveWindow.Hwnd)
        self.desktop.activate(hwnd, self.control)
        ui = self.desktop.owned_input(hwnd, self.control, verify=self.verify_active)
        self.control.idle_until(target, 'reviewing_word_document', guard=ui.guard)

    def close(self):
        errors = []
        for doc in reversed(self.owned):
            try:
                doc.Close(SaveChanges=False)
            except Exception as exc:
                errors.append(type(exc).__name__)
        self.owned.clear()
        self.document = None
        preserved = False
        if self.app is not None:
            for name, value in self.settings.items():
                try:
                    setattr(self.app, name, value)
                except Exception as exc:
                    errors.append(type(exc).__name__)
            try:
                if self.app.Documents.Count == 0:
                    self.app.Quit()
                else:
                    preserved = True
            except Exception as exc:
                errors.append(type(exc).__name__)
            self.app = None
        if self.pythoncom is not None:
            self.pythoncom.CoUninitialize()
            self.pythoncom = None
        self.control.audit.emit('office_cleanup', errors=errors, instance_preserved=preserved)
        if errors:
            raise RuntimeError('Office cleanup failed: '+', '.join(errors))
