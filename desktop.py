"""Windows input guard. GUI dependencies are loaded only in live mode."""
import ctypes
from ctypes import wintypes


class FocusLost(RuntimeError):
    pass


def gui_focus(thread_id):
    class GUIInfo(ctypes.Structure):
        _fields_ = [('cbSize', wintypes.DWORD), ('flags', wintypes.DWORD),
                    ('hwndActive', wintypes.HWND), ('hwndFocus', wintypes.HWND),
                    ('hwndCapture', wintypes.HWND), ('hwndMenuOwner', wintypes.HWND),
                    ('hwndMoveSize', wintypes.HWND), ('hwndCaret', wintypes.HWND),
                    ('rcCaret', wintypes.RECT)]
    fn = ctypes.windll.user32.GetGUIThreadInfo
    fn.argtypes = [wintypes.DWORD, ctypes.POINTER(GUIInfo)]
    fn.restype = wintypes.BOOL
    info = GUIInfo()
    info.cbSize = ctypes.sizeof(info)
    if not fn(thread_id, ctypes.byref(info)):
        raise FocusLost('Cannot determine keyboard focus')
    return info.hwndFocus


class WindowsDesktop:
    def __init__(self):
        import win32api
        import win32gui
        import win32process
        import pyautogui
        self.api, self.gui, self.process, self.input = win32api, win32gui, win32process, pyautogui
        # Preserve the fail-safe; do not disable it or move to a fail-safe corner.
        self.input.FAILSAFE = True

    def emergency(self):
        if self.api.GetAsyncKeyState(0x77) & 0x8000:  # F8
            return 'F8_pressed'
        try:
            self.input.failSafeCheck()
        except self.input.FailSafeException:
            return 'mouse_corner_failsafe'
        return None

    def find_window(self, marker):
        matches = []
        def collect(hwnd, _):
            if self.gui.IsWindowVisible(hwnd) and marker in self.gui.GetWindowText(hwnd):
                matches.append(hwnd)
        self.gui.EnumWindows(collect, None)
        if len(matches) != 1:
            raise FocusLost('Expected exactly one owned browser window with its unique title')
        return matches[0]

    def find_window_by_pid(self, pid):
        matches = []
        def collect(hwnd, _):
            if (self.gui.IsWindowVisible(hwnd)
                    and self.process.GetWindowThreadProcessId(hwnd)[1] == pid
                    and self.gui.GetClassName(hwnd) == 'Chrome_WidgetWin_1'):
                matches.append(hwnd)
        self.gui.EnumWindows(collect, None)
        if len(matches) != 1:
            raise FocusLost('Expected one visible window for the observed browser PID')
        return matches[0]

    def activate(self, hwnd, control):
        control.check()
        self.gui.ShowWindow(hwnd, 9)
        self.gui.MoveWindow(hwnd, 20, 20, 1000, 750, True)
        self.gui.ShowWindow(hwnd, 3)  # Maximize on the primary monitor.
        self.gui.SetForegroundWindow(hwnd)
        control.pause(.3)
        if self.gui.GetForegroundWindow() != hwnd:
            raise FocusLost('Windows refused foreground activation; no input sent')

    def owned_input(self, hwnd, control, *, word=False, verify=None):
        _, pid = self.process.GetWindowThreadProcessId(hwnd)
        return GuardedInput(self, hwnd, pid, control, word=word, verify=verify)


# How many times per window the agent may pull focus back after something else
# (a closed popup, a Chrome prompt bubble, a Word/Explorer window) took the foreground.
# F8 / mouse-corner still stop the run immediately.
MAX_FOCUS_RECOVERIES = 8


class GuardedInput:
    def __init__(self, desktop, hwnd, pid, control, word=False, verify=None):
        self.desktop, self.hwnd, self.pid, self.control = desktop, hwnd, pid, control
        self.word, self.verify = word, verify
        self.focus_recoveries = 0

    def _describe(self, hwnd):
        gui, process = self.desktop.gui, self.desktop.process
        try:
            return {'hwnd': int(hwnd or 0), 'title': gui.GetWindowText(hwnd)[:120],
                    'class': gui.GetClassName(hwnd), 'pid': process.GetWindowThreadProcessId(hwnd)[1]}
        except Exception:
            return {'hwnd': int(hwnd or 0)}

    def _recover_focus(self):
        """Something else is in front. Log what it is, then bring the owned window back."""
        gui = self.desktop.gui
        thief = self._describe(gui.GetForegroundWindow())
        self.control.audit.emit('focus_lost', owned_hwnd=int(self.hwnd), foreground=thief,
                                recovery_attempt=self.focus_recoveries + 1)
        if self.focus_recoveries >= MAX_FOCUS_RECOVERIES:
            raise FocusLost(f'Owned window lost foreground focus too many times; last taken by {thief}')
        self.focus_recoveries += 1
        for _ in range(3):
            self.control.check()
            try:
                if gui.IsIconic(self.hwnd):
                    gui.ShowWindow(self.hwnd, 9)   # restore
                    gui.ShowWindow(self.hwnd, 3)   # maximize
                gui.SetForegroundWindow(self.hwnd)
            except Exception:
                pass
            self.control.pause(.4)
            if gui.GetForegroundWindow() == self.hwnd:
                self.control.audit.emit('focus_recovered', owned_hwnd=int(self.hwnd), taken_by=thief)
                return
        raise FocusLost(f'Owned window lost foreground focus and could not get it back; taken by {thief}')

    def guard(self):
        self.control.check()
        gui, process = self.desktop.gui, self.desktop.process
        if not gui.IsWindow(self.hwnd):
            raise FocusLost('Owned window was closed; input stopped')
        if gui.GetForegroundWindow() != self.hwnd:
            self._recover_focus()
        tid, pid = process.GetWindowThreadProcessId(self.hwnd)
        if pid != self.pid:
            raise FocusLost('Window ownership changed')
        if self.word:
            focused = gui_focus(tid)
            if not focused or gui.GetClassName(focused) != '_WwG':
                raise FocusLost('Word document body does not have keyboard focus')
        if self.verify:
            self.verify()

    def write(self, char):
        self.guard()
        self.desktop.input.write(char, _pause=False)

    def press(self, key):
        self.guard()
        self.desktop.input.press(key, _pause=False)

    def hotkey(self, *keys):
        self.guard()
        self.desktop.input.hotkey(*keys, _pause=False)

    def move_to(self, x, y):
        self.guard()
        width, height = self.desktop.input.size()
        if not (2 <= x < width-2 and 2 <= y < height-2):
            raise FocusLost('Cursor target is outside the primary screen safe area')
        self.desktop.input.moveTo(x, y, _pause=False)

    def click(self):
        self.guard()
        self.desktop.input.click(_pause=False)

    def scroll(self, clicks):
        self.guard()
        self.desktop.input.scroll(clicks, _pause=False)
