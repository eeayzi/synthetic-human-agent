"""Activate a declared automation-browser shortcut from the real Explorer UI.
No custom process-parent attributes or automation-marker suppression are used.
"""
import os
from pathlib import Path
import subprocess


def browser_arguments(profile):
    return ['--enable-automation', '--remote-debugging-address=127.0.0.1',
            '--remote-debugging-port=0', '--user-data-dir='+str(profile),
            '--no-first-run', '--no-default-browser-check', '--new-window',
            '--window-position=0,0', '--start-maximized',
            # Block browser-level permission bubbles (notifications, location, camera...) before they render.
            '--disable-notifications', '--deny-permission-prompts', 'about:blank']


def read_debug_port(profile):
    try:
        lines=(Path(profile)/'DevToolsActivePort').read_text(encoding='utf-8').splitlines()
        port=int(lines[0])
        if len(lines)<2 or not lines[1].startswith('/devtools/browser/') or not 1 <= port <= 65535:
            return None
        return port
    except (OSError, ValueError, IndexError):
        return None


class ExplorerLauncher:
    def __init__(self, desktop, control, workspace):
        self.desktop,self.control=desktop,control
        self.workspace=Path(workspace).resolve()
        self.profile=self.workspace/'browser-profile'
        self.shortcut=self.workspace/'Launch training browser.lnk'
        self.pythoncom=None
        self.browser_requested=False

    def launch(self, executable):
        import pythoncom
        from win32com.client import Dispatch
        self.control.check()
        if not Path(executable).is_file():
            raise ValueError('Installed Chromium executable not found')
        self.profile.mkdir(exist_ok=False)
        pythoncom.CoInitialize()
        self.pythoncom=pythoncom
        link=Dispatch('WScript.Shell').CreateShortcut(str(self.shortcut))
        link.TargetPath=str(executable)
        link.Arguments=subprocess.list2cmdline(browser_arguments(self.profile))
        link.WorkingDirectory=str(Path(executable).parent)
        link.Description='Synthetic training browser - automation enabled'
        link.Save()
        shell=Dispatch('Shell.Application')
        explorer=Path(os.environ.get('WINDIR',r'C:\Windows'))/'explorer.exe'
        subprocess.Popen([str(explorer), '/select,', str(self.shortcut)], shell=False)
        window=None
        until=min(self.control.phase_deadline,self.control.clock()+15)
        while self.control.clock()<until:
            self.control.check()
            for candidate in shell.Windows():
                try:
                    folder=Path(candidate.Document.Folder.Self.Path).resolve()
                    if folder==self.workspace:
                        window=candidate
                        break
                except Exception:
                    continue
            if window is not None:
                break
            self.control.pause(.1)
        if window is None:
            raise RuntimeError('File Explorer did not open the run folder')
        item=window.Document.Folder.ParseName(self.shortcut.name)
        window.Document.SelectItem(item,17)  # select and deselect other items
        def verify_selection():
            selected=window.Document.SelectedItems()
            if (Path(window.Document.Folder.Self.Path).resolve()!=self.workspace
                    or selected.Count!=1 or Path(selected.Item(0).Path).resolve()!=self.shortcut):
                raise RuntimeError('Explorer selection changed; browser launch stopped')
        hwnd=int(window.HWND)
        self.desktop.activate(hwnd,self.control)
        ui=self.desktop.owned_input(hwnd,self.control,verify=verify_selection)
        verify_selection()
        self.control.audit.emit('browser_launch_requested',backend='explorer_shortcut_enter',
                                shortcut=str(self.shortcut), automation_enabled=True,
                                explorer_observed_pid=ui.pid)
        ui.press('enter')
        self.browser_requested=True
        until=min(self.control.phase_deadline,self.control.clock()+30)
        while self.control.clock()<until:
            self.control.check()
            port=read_debug_port(self.profile)
            if port:
                return f'http://127.0.0.1:{port}'
            self.control.pause(.1)
        raise RuntimeError('Browser did not expose its declared automation endpoint; inspect the run-owned window')

    def close(self):
        if self.pythoncom is not None:
            self.pythoncom.CoUninitialize()
            self.pythoncom=None
        self.control.audit.emit('explorer_launcher_cleanup', folder_window_left_open=True,
                                profile=str(self.profile), browser_launch_requested=self.browser_requested)
