import sys
import time
from typing import Optional

# ---------------------------------------------------------------------------
# Windows backend (COM/pycaw)
# ---------------------------------------------------------------------------
if sys.platform.startswith("win"):
    from ctypes import POINTER, cast

    import pythoncom
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

    def _get_endpoint() -> POINTER(IAudioEndpointVolume):
        """Return **IAudioEndpointVolume** for the current default output."""
        pythoncom.CoInitialize()
        device = AudioUtilities.GetSpeakers()
        interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return cast(interface, POINTER(IAudioEndpointVolume))

    def get_level() -> float:
        """Current output volume as a percentage (0–100)."""
        ep = _get_endpoint()
        try:
            return ep.GetMasterVolumeLevelScalar() * 100.0
        finally:
            try:
                ep.Release()
            except Exception:
                pass
            pythoncom.CoUninitialize()

    def set_level(percent: float) -> None:
        """Set output volume to percent (0–100)."""
        ep = _get_endpoint()
        try:
            scalar = max(0.0, min(100.0, percent)) / 100.0
            ep.SetMasterVolumeLevelScalar(scalar, None)
        finally:
            try:
                ep.Release()
            except Exception:
                pass
            pythoncom.CoUninitialize()


# ---------------------------------------------------------------------------
# macOS backend (AppleScript via `osascript`)
# ---------------------------------------------------------------------------
elif sys.platform == "darwin":
    # This is a bit slow (100's of ms).
    # You can also use PyObjC's packages and should get <10 ms results.
    import subprocess

    def _osascript(script: str) -> str:
        result = subprocess.run(
            [
                "osascript",
                "-e",
                script,
            ],
            capture_output=True,
            check=True,
            text=True,
        )
        return result.stdout.strip()

    def get_level() -> float:
        return float(_osascript("output volume of (get volume settings)"))

    def set_level(percent: float) -> None:
        vol = int(max(0.0, min(100.0, percent)))
        _osascript(f"set volume output volume {vol}")


# ---------------------------------------------------------------------------
# Linux / other – fall‑back stubs
# ---------------------------------------------------------------------------
else:

    def get_level() -> float:
        """Return a dummy level (100%). Modify for PulseAudio, etc."""
        return 100.0

    def set_level(_percent: float) -> None:
        """No‑op on unsupported platforms."""
        pass


# ---------------------------------------------------------------------------
# Common helpers – duck / restore
# ---------------------------------------------------------------------------
_prev_level: Optional[float] = None


def duck(factor: float = 0.3) -> None:
    """Lower the current system volume by *factor* (0–1) and remember it."""
    global _prev_level
    current = get_level()
    _prev_level = current
    set_level(current * factor)


def restore() -> None:
    """Restore volume to the level captured by the last :pyfunc:`duck`."""
    if _prev_level is not None:
        set_level(_prev_level)


if __name__ == "__main__":
    duck()
    time.sleep(1)
    restore()
