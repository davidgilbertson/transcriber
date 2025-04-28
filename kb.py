import ctypes
import threading
from typing import Callable, Final, Set, List

# ---------------------------------------------------------------------------
# Win32 constants
# ---------------------------------------------------------------------------
WH_KEYBOARD_LL: Final = 13
WM_KEYDOWN: Final = 0x0100
WM_KEYUP: Final = 0x0101
WM_SYSKEYDOWN: Final = 0x0104
WM_SYSKEYUP: Final = 0x0105
WM_QUIT: Final = 0x0012
LLKHF_INJECTED: Final = 0x00000010  # event came from SendInput / keybd_event

# Map generic modifiers → left/right variants
_MOD_VARIANTS: dict[int, set[int]] = {
    0x11: {0xA2, 0xA3},  # CTRL
    0x12: {0xA4, 0xA5},  # ALT
    0x10: {0xA0, 0xA1},  # SHIFT
    0x5B: {0x5B, 0x5C},  # WIN
}
_ALIAS_TO_GENERIC = {vk: gen for gen, vs in _MOD_VARIANTS.items() for vk in vs}

# Human‑readable names → generic VKs
VK_NAMES: dict[str, int] = {
    "ctrl": 0x11,
    "alt": 0x12,
    "shift": 0x10,
    "win": 0x5B,
    "cmd": 0x5B,
    "esc": 0x1B,
}

user32 = ctypes.windll.user32  # type: ignore[attr-defined]
_kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# C types
# ---------------------------------------------------------------------------


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", ctypes.c_uint32),
        ("scanCode", ctypes.c_uint32),
        ("flags", ctypes.c_uint32),
        ("time", ctypes.c_uint32),
        ("dwExtraInfo", ctypes.c_ulonglong),
    ]


LowLevelProc = ctypes.WINFUNCTYPE(
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.POINTER(KBDLLHOOKSTRUCT)
)

VkKeyScanW = user32.VkKeyScanW

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _key_name_to_vk(name: str) -> int:
    """Translate human key name (‘a’, ‘ctrl’) → virtual‑key code."""
    name = name.lower()
    if name in VK_NAMES:
        return VK_NAMES[name]
    vk = VkKeyScanW(ord(name))
    if vk == -1:
        raise ValueError(f"Unrecognised key: {name}")
    return vk & 0xFF


# ---------------------------------------------------------------------------
# Hook thread
# ---------------------------------------------------------------------------


class _HookThread(threading.Thread):
    """Runs the message loop and dispatches events to registered instances."""

    def __init__(self):
        super().__init__(daemon=True)
        self._instances: Set["HotKeyHook"] = set()
        self._stop_evt = threading.Event()
        self._hook: int | None = None

    # Registration helpers ------------------------------------------------------
    def register(self, inst: "HotKeyHook") -> None:
        self._instances.add(inst)

    def unregister(self, inst: "HotKeyHook") -> None:
        self._instances.discard(inst)
        if not self._instances:
            self._stop_evt.set()
            user32.PostThreadMessageW(self.ident, WM_QUIT, 0, 0)  # type: ignore[arg-type]

    # Thread main ----------------------------------------------------------------
    def run(self) -> None:  # noqa: D401
        proc = LowLevelProc(self._callback)
        self._hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, proc, 0, 0)
        if not self._hook:
            raise OSError(_kernel32.GetLastError())
        self._proc_ref = proc  # prevent GC

        msg = ctypes.wintypes.MSG()
        while not self._stop_evt.is_set() and user32.GetMessageW(
            ctypes.byref(msg), 0, 0, 0
        ):
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        user32.UnhookWindowsHookEx(self._hook)
        self._hook = None

    # Low‑level callback ---------------------------------------------------------
    def _callback(self, nCode: int, wParam: int, lParam):  # noqa: N802, ANN001
        if nCode == 0:  # HC_ACTION
            kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            if kb.flags & LLKHF_INJECTED:
                return user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

            vk = _ALIAS_TO_GENERIC.get(kb.vkCode, kb.vkCode)
            down = wParam in (WM_KEYDOWN, WM_SYSKEYDOWN)
            up = wParam in (WM_KEYUP, WM_SYSKEYUP)

            swallow = False
            for inst in tuple(self._instances):
                swallow |= inst._handle(vk, down, up)
            if swallow:
                return 1
        return user32.CallNextHookEx(self._hook, nCode, wParam, lParam)


# Singleton hook thread --------------------------------------------------------
_hook_thread: _HookThread | None = None


def _ensure_thread() -> _HookThread:
    global _hook_thread  # noqa: PLW0603
    if _hook_thread is None or not _hook_thread.is_alive():
        _hook_thread = _HookThread()
        _hook_thread.start()
    return _hook_thread


# ---------------------------------------------------------------------------
# Core class
# ---------------------------------------------------------------------------


class HotKeyHook:
    """Internal object representing a registered global hot‑key."""

    __slots__ = ("_combo", "_callback", "_held", "_active", "_thread")

    def __init__(self, combo: str, callback: Callable[[], None]):
        self._combo = {_key_name_to_vk(k) for k in combo.split("+")}
        self._callback = callback
        self._held: set[int] = set()
        self._active = False
        self._thread = _ensure_thread()
        self._thread.register(self)

    # Event handler -------------------------------------------------------------
    def _handle(self, vk: int, down: bool, up: bool) -> bool:
        if down:
            self._held.add(vk)
        elif up:
            self._held.discard(vk)

        if not self._active and self._combo.issubset(self._held):
            self._active = True

        if self._active and not (self._held & self._combo):
            self._active = False
            self._held.clear()
            threading.Timer(0.02, self._callback).start()

        return self._active and down and vk in self._combo

    # Cleanup -------------------------------------------------------------------
    def close(self) -> None:
        self._thread.unregister(self)


# ---------------------------------------------------------------------------
# Module‑level public helpers
# ---------------------------------------------------------------------------

_hotkeys: List[HotKeyHook] = []


def add_hotkey(combo: str, callback: Callable[[], None]) -> HotKeyHook:
    """Register *combo*, return the underlying object and keep a module ref."""
    hk = HotKeyHook(combo, callback)
    _hotkeys.append(hk)
    return hk


def clear_all_hotkeys() -> None:
    """Unregister every hot‑key added via :pyfunc:`add_hotkey`."""
    while _hotkeys:
        _hotkeys.pop().close()


def wait():
    while True:
        threading.Event().wait(1)


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import keyboard

    add_hotkey("ctrl+alt+shift+q", lambda: keyboard.write("hello🔴🔴"))
    add_hotkey("esc", lambda: print("ESC"))

    print("Press combos – others pass through. Ctrl+C quits.")
    try:
        while True:
            threading.Event().wait(1)
    except KeyboardInterrupt:
        clear_all_hotkeys()
