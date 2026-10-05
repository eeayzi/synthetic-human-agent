import psutil
import ctypes
from ctypes import wintypes

class STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR),
        ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD),
        ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD),
        ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD),
        ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD),
        ("cbReserved2", wintypes.WORD),
        ("lpReserved2", wintypes.LPBYTE),
        ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE)
    ]

class STARTUPINFOEXW(ctypes.Structure):
    _fields_ = [
        ("StartupInfo", STARTUPINFOW),
        ("lpAttributeList", ctypes.c_void_p)
    ]

class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD)
    ]


kernel32 = ctypes.windll.kernel32

PROCESS_CREATE_PROCESS = 0x0080
PROC_THREAD_ATTRIBUTE_PARENT_PROCESS = 0x00020000
EXTENDED_STARTUPINFO_PRESENT = 0x00080000

kernel32.InitializeProcThreadAttributeList.argtypes = [ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.c_size_t)]
kernel32.InitializeProcThreadAttributeList.restype = wintypes.BOOL

kernel32.UpdateProcThreadAttribute.argtypes = [ctypes.c_void_p, wintypes.DWORD, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_void_p]
kernel32.UpdateProcThreadAttribute.restype = wintypes.BOOL

kernel32.CreateProcessW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, ctypes.c_void_p, ctypes.c_void_p, wintypes.BOOL, wintypes.DWORD, ctypes.c_void_p, wintypes.LPCWSTR, ctypes.POINTER(STARTUPINFOEXW), ctypes.POINTER(PROCESS_INFORMATION)]
kernel32.CreateProcessW.restype = wintypes.BOOL


def get_explorer_pid():
    explorer_pid = None
    for p in psutil.process_iter(['pid', 'name']):
        try:
            if p.name().lower() == "explorer.exe":
                explorer_pid = p.pid
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if not explorer_pid:
        raise Exception("Could not find a running explorer.exe instance")

    return explorer_pid

def launch_process(app_path):
    explorer_pid = get_explorer_pid()

    explorer_handle = kernel32.OpenProcess(
        PROCESS_CREATE_PROCESS,
        False,
        explorer_pid
    )

    attr_buffer_size = ctypes.c_size_t(0)
    # determine the buffer size required to support the specified number of attributes (1)
    # byref passes the pointer
    kernel32.InitializeProcThreadAttributeList(
        None,
        1,
        0,
        ctypes.byref(attr_buffer_size)
    )

    attr_list = ctypes.create_string_buffer(attr_buffer_size.value)
    if not kernel32.InitializeProcThreadAttributeList(
        ctypes.byref(attr_list),
        1,
        0,
        ctypes.byref(attr_buffer_size)
    ):
        raise Exception("Failed to initialize process thread attribute list")

    explorer_pointer = wintypes.HANDLE(explorer_handle)
    if not kernel32.UpdateProcThreadAttribute(
        ctypes.byref(attr_list), #lpAttributeList
        0, #dwFlags
        PROC_THREAD_ATTRIBUTE_PARENT_PROCESS, #Attribute
        ctypes.byref(explorer_pointer), #lpValue
        ctypes.sizeof(explorer_pointer), #cbSize
        None, #lpPreviousValue
        None #lpReturnSize
    ):
        raise Exception("Failed to update parent process attribute list")


    startup_info = STARTUPINFOEXW()
    startup_info.StartupInfo.cb = ctypes.sizeof(STARTUPINFOEXW)
    startup_info.lpAttributeList = ctypes.cast(attr_list, ctypes.c_void_p)

    process_info = PROCESS_INFORMATION()

    if not kernel32.CreateProcessW(
        app_path, #lpApplicationName
        None, #lpCommandLine
        None, #lpProcessAttributes
        None, #lpThreadAttributes
        False, #bInheritHandles
        EXTENDED_STARTUPINFO_PRESENT, #dwCreationFlags
        None, #lpEnvironment
        None, #lpCurrentDirectory
        ctypes.byref(startup_info), #lpStartupInfo
        ctypes.byref(process_info) #lpProcessInformation
    ):
        raise Exception(f"Failed to launch spoofed process. Windows Error: {kernel32.GetLastError()}")

    kernel32.CloseHandle(process_info.hProcess)
    kernel32.CloseHandle(process_info.hThread)
    kernel32.CloseHandle(startup_info.StartupInfo.hStdInput)
    kernel32.CloseHandle(startup_info.StartupInfo.hStdOutput)
    kernel32.CloseHandle(startup_info.StartupInfo.hStdError)
    kernel32.CloseHandle(explorer_handle)

    return process_info.dwProcessId

    # print(f"PID: {process_info.dwProcessId}")
    # print(f"PPID: {psutil.Process(process_info.dwProcessId).ppid()}")

# launch_process(r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE")