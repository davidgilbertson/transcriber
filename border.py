# %%
import tkinter as tk
import time
import sys
from typing import List, Tuple, Optional

if sys.platform.startswith("win"):
    import ctypes
    from ctypes import wintypes


class Border:
    def __init__(self, root: tk.Tk):
        """
        Initialize a border indicator overlay using the provided Tk root.

        Windows: shows the border on all detected monitors.
        Other OS: shows the border on the primary screen only.

        Parameters:
        - root: the Tk instance managing the mainloop
        """
        self.root = root
        self.thickness = 10
        self.alpha = 0.8
        transparent_color = "magenta"

        # Hide the main root window (we only want our overlays)
        root.withdraw()

        # Determine monitor rectangles: list of (left, top, width, height)
        monitors: List[Tuple[int, int, int, int]] = []

        if sys.platform.startswith("win"):
            # Enumerate monitors via WinAPI
            monitors = self._enumerate_windows_monitors()
        if not monitors:
            # Fallback: single monitor using Tk's primary screen
            width = root.winfo_screenwidth()
            height = root.winfo_screenheight()
            monitors = [(0, 0, width, height)]

        # Create one overlay per monitor
        self._overlays = []  # list of dicts: {win, canvas, rect, bounds}
        for left, top, width, height in monitors:
            win = tk.Toplevel(root)
            win.overrideredirect(True)
            win.attributes("-topmost", True)
            win.attributes("-alpha", self.alpha)
            win.config(bg=transparent_color)
            try:
                # On Windows: make the transparent_color fully transparent
                win.wm_attributes("-transparentcolor", transparent_color)
            except tk.TclError:
                pass
            # Position to match the monitor bounds
            win.geometry(f"{width}x{height}+{left}+{top}")

            canvas = tk.Canvas(win, highlightthickness=0, bg=transparent_color)
            canvas.pack(fill="both", expand=True)
            half = self.thickness / 2
            rect = canvas.create_rectangle(
                half,
                half,
                width - half,
                height - half,
                width=self.thickness,
                outline="black",
            )

            # Start hidden; use show() to display
            win.withdraw()
            self._overlays.append(
                {
                    "win": win,
                    "canvas": canvas,
                    "rect": rect,
                    "bounds": (left, top, width, height),
                }
            )

    def _enumerate_windows_monitors(self) -> List[Tuple[int, int, int, int]]:
        """Return a list of (left, top, width, height) for each Windows monitor."""
        if not sys.platform.startswith("win"):
            return []

        user32 = ctypes.windll.user32
        # Ensure coordinates reflect actual pixels per-monitor when possible
        try:
            # Make the process per-monitor DPI aware (best effort)
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                user32.SetProcessDPIAware()
            except Exception:
                pass

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long),
            ]

        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_ulong),
                ("rcMonitor", RECT),
                ("rcWork", RECT),
                ("dwFlags", ctypes.c_ulong),
            ]

        MonitorEnumProc = ctypes.WINFUNCTYPE(
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.POINTER(RECT),
            ctypes.c_longlong,
        )

        monitors: List[Tuple[int, int, int, int]] = []

        def _callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
            info = MONITORINFO()
            info.cbSize = ctypes.sizeof(MONITORINFO)
            user32.GetMonitorInfoW(ctypes.c_void_p(hMonitor), ctypes.byref(info))
            left = int(info.rcMonitor.left)
            top = int(info.rcMonitor.top)
            right = int(info.rcMonitor.right)
            bottom = int(info.rcMonitor.bottom)
            monitors.append((left, top, right - left, bottom - top))
            return 1  # continue enumeration

        # EnumDisplayMonitors(NULL, NULL, callback, dwData)
        user32.EnumDisplayMonitors(0, 0, MonitorEnumProc(_callback), 0)
        return monitors

    def show(self, color: str):
        """Show the overlay with the specified border color."""
        monitor_index = self.get_active_monitor_index()
        for index, item in enumerate(self._overlays):
            item["canvas"].itemconfig(item["rect"], outline=color)
            if monitor_index is None or index == monitor_index:
                item["win"].deiconify()
            else:
                item["win"].withdraw()
        # immediate redraw without mainloop
        # self.root.update()

    def hide(self):
        """Hide the overlay border."""
        for item in self._overlays:
            item["win"].withdraw()
        # self.root.update()

    def get_active_monitor_index(self) -> Optional[int]:
        """Return the index of the monitor containing the foreground window.

        Windows-only. Returns 0 on non-Windows or when detection fails.
        """
        if not sys.platform.startswith("win"):
            return 0 if self._overlays else None

        try:
            user32 = ctypes.windll.user32

            # Structures local to this function (duplicated to avoid refactoring)
            class RECT(ctypes.Structure):
                _fields_ = [
                    ("left", ctypes.c_long),
                    ("top", ctypes.c_long),
                    ("right", ctypes.c_long),
                    ("bottom", ctypes.c_long),
                ]

            class MONITORINFO(ctypes.Structure):
                _fields_ = [
                    ("cbSize", ctypes.c_ulong),
                    ("rcMonitor", RECT),
                    ("rcWork", RECT),
                    ("dwFlags", ctypes.c_ulong),
                ]

            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return 0 if self._overlays else None

            MONITOR_DEFAULTTONEAREST = 2
            hmon = user32.MonitorFromWindow(
                ctypes.c_void_p(hwnd), MONITOR_DEFAULTTONEAREST
            )
            if not hmon:
                return 0 if self._overlays else None

            info = MONITORINFO()
            info.cbSize = ctypes.sizeof(MONITORINFO)
            user32.GetMonitorInfoW(ctypes.c_void_p(hmon), ctypes.byref(info))

            left = int(info.rcMonitor.left)
            top = int(info.rcMonitor.top)
            right = int(info.rcMonitor.right)
            bottom = int(info.rcMonitor.bottom)
            width = right - left
            height = bottom - top

            # First try exact bounds match
            for idx, item in enumerate(self._overlays):
                l, t, w, h = item.get("bounds", (0, 0, 0, 0))
                if (l, t, w, h) == (left, top, width, height):
                    return idx

            # Fallback: use center-point containment
            cx = (left + right) // 2
            cy = (top + bottom) // 2
            for idx, item in enumerate(self._overlays):
                l, t, w, h = item.get("bounds", (0, 0, 0, 0))
                if l <= cx < l + w and t <= cy < t + h:
                    return idx

            return 0 if self._overlays else None
        except Exception:
            return 0 if self._overlays else None

    # def destroy(self):
    #     """Destroy the overlay and quit the application."""
    #     self.win.destroy()
    #     self.root.destroy()


if __name__ == "__main__":
    # 1. Create the Tk root (no mainloop yet)
    root = tk.Tk()

    # 2. Instantiate our indicator
    indicator = Border(root)

    # 3. Use show/hide synchronously; show() already calls update()
    indicator.show("red")
    time.sleep(2)
    indicator.show("orange")
    time.sleep(2)
    indicator.hide()

    # 4. Enter the Tk event loop:
    #    - Processes UI events (clicks, redraws)
    #    - Keeps the window alive until closed or destroy() is called
    root.mainloop()
