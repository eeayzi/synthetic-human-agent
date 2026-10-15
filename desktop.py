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


class GuardedInput:
    def __init__(self, desktop, hwnd, pid, control, word=False, verify=None):
        self.desktop, self.hwnd, self.pid, self.control = desktop, hwnd, pid, control
        self.word, self.verify = word, verify

    def guard(self):
        self.control.check()
        gui, process = self.desktop.gui, self.desktop.process
        if not gui.IsWindow(self.hwnd) or gui.GetForegroundWindow() != self.hwnd:
            raise FocusLost('Owned window lost foreground focus; input stopped')
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
