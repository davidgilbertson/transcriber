# ===========================================================================
# Volume control helpers (pycaw) – duck / restore API
# ===========================================================================
from ctypes import cast, POINTER
import pythoncom
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume  # type: ignore

_prev_level: float | None = None  # remembered volume for restore()


def _get_endpoint() -> POINTER(IAudioEndpointVolume):
    """Return IAudioEndpointVolume for the current default render device."""
    # _get_endpoint may run in worker threads triggered by hot‑key callbacks.
    # Ensure the *calling* thread is in an apartment; if it already is, this is
    # a no‑op.
    pythoncom.CoInitialize()
    device = AudioUtilities.GetSpeakers()
    interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return cast(interface, POINTER(IAudioEndpointVolume))


def get_level() -> float:
    # We call this every time in case a user case switched audio outputs
    endpoint = _get_endpoint()
    try:
        return endpoint.GetMasterVolumeLevelScalar()
    finally:
        endpoint.Release()


def set_level(scalar: float) -> None:
    endpoint = _get_endpoint()
    try:
        endpoint.SetMasterVolumeLevelScalar(max(0.0, min(1.0, scalar)), None)
    finally:
        endpoint.Release()


def duck(factor: float = 0.3) -> None:
    """
    Lower the current system volume by `factor` (0‒1) and remember it.
    Does not make a quack sound.
    """
    global _prev_level
    current = get_level()
    _prev_level = current
    set_level(current * factor)


def restore() -> None:
    """Restore volume to the level captured by the last `duck`."""
    if _prev_level is not None:
        set_level(_prev_level)


if __name__ == "__main__":
    import time

    duck()
    time.sleep(1)
    restore()
