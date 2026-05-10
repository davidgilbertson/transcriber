import ctypes
from ctypes import wintypes
import time

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
WM_TIMER = 0x0113

LISTEN_SECONDS = 60

LLKHF_EXTENDED = 0x01
LLKHF_LOWER_IL_INJECTED = 0x02
LLKHF_INJECTED = 0x10
LLKHF_ALTDOWN = 0x20
LLKHF_UP = 0x80

VK_NAMES = {
    0x10: "SHIFT",
    0x11: "CTRL",
    0x12: "ALT",
    0xA0: "LSHIFT",
    0xA1: "RSHIFT",
    0xA2: "LCTRL",
    0xA3: "RCTRL",
    0xA4: "LALT",
    0xA5: "RALT",
    0x51: "Q",
    0x7C: "F13",
    0x7D: "F14",
    0x7E: "F15",
    0x7F: "F16",
}


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


HOOKPROC = ctypes.WINFUNCTYPE(
    wintypes.LPARAM,
    ctypes.c_int,
    wintypes.WPARAM,
    wintypes.LPARAM,
)
UINT_PTR = ctypes.c_size_t

user32.SetWindowsHookExW.argtypes = [
    ctypes.c_int,
    HOOKPROC,
    wintypes.HINSTANCE,
    wintypes.DWORD,
]
user32.SetWindowsHookExW.restype = wintypes.HHOOK
user32.CallNextHookEx.argtypes = [
    wintypes.HHOOK,
    ctypes.c_int,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
user32.CallNextHookEx.restype = wintypes.LPARAM
user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
user32.UnhookWindowsHookEx.restype = wintypes.BOOL
user32.GetMessageW.argtypes = [
    ctypes.POINTER(wintypes.MSG),
    wintypes.HWND,
    wintypes.UINT,
    wintypes.UINT,
]
user32.GetMessageW.restype = wintypes.BOOL
user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.TranslateMessage.restype = wintypes.BOOL
user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.DispatchMessageW.restype = wintypes.LPARAM
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = wintypes.SHORT
user32.SetTimer.argtypes = [
    wintypes.HWND,
    UINT_PTR,
    wintypes.UINT,
    ctypes.c_void_p,
]
user32.SetTimer.restype = UINT_PTR
user32.KillTimer.argtypes = [wintypes.HWND, UINT_PTR]
user32.KillTimer.restype = wintypes.BOOL


def key_state(vk):
    return bool(user32.GetAsyncKeyState(vk) & 0x8000)


def flags_text(flags):
    names = []
    if flags & LLKHF_EXTENDED:
        names.append("EXTENDED")
    if flags & LLKHF_LOWER_IL_INJECTED:
        names.append("LOWER_IL_INJECTED")
    if flags & LLKHF_INJECTED:
        names.append("INJECTED")
    if flags & LLKHF_ALTDOWN:
        names.append("ALTDOWN")
    if flags & LLKHF_UP:
        names.append("UP")
    return "|".join(names) or "-"


def event_name(wparam):
    return {
        WM_KEYDOWN: "KEYDOWN",
        WM_KEYUP: "KEYUP",
        WM_SYSKEYDOWN: "SYSKEYDOWN",
        WM_SYSKEYUP: "SYSKEYUP",
    }.get(wparam, hex(wparam))


def hook_proc(nCode, wParam, lParam):
    if nCode >= 0:
        kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
        vk = kb.vkCode
        name = VK_NAMES.get(vk, chr(vk) if 32 <= vk <= 126 else "?")

        print(
            f"{time.time():.3f} "
            f"{event_name(wParam):10} "
            f"vk=0x{vk:02X} {name:8} "
            f"scan=0x{kb.scanCode:02X} "
            f"flags={kb.flags:02X} {flags_text(kb.flags):25} "
            f"mods="
            f"ctrl={key_state(0x11)} "
            f"alt={key_state(0x12)} "
            f"shift={key_state(0x10)}",
            flush=True,
        )

    return user32.CallNextHookEx(None, nCode, wParam, lParam)


callback = HOOKPROC(hook_proc)

hook = user32.SetWindowsHookExW(
    WH_KEYBOARD_LL,
    callback,
    None,
    0,
)

if not hook:
    raise ctypes.WinError(ctypes.get_last_error())

timer_id = user32.SetTimer(None, 0, LISTEN_SECONDS * 1000, None)

print(f"Listening for {LISTEN_SECONDS} seconds. Press Ctrl+C to stop.", flush=True)

msg = wintypes.MSG()
try:
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
        if msg.message == WM_TIMER and msg.wParam == timer_id:
            break
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))
except KeyboardInterrupt:
    pass
finally:
    user32.KillTimer(None, timer_id)
    user32.UnhookWindowsHookEx(hook)
    print("Stopped.", flush=True)
