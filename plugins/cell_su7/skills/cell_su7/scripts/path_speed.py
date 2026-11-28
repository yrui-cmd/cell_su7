"""Calibrate and pace the visible cursor tips in the PowerPoint tracing preview."""

from contextlib import contextmanager
from dataclasses import dataclass
import ctypes
import math
import time


MAX_CURSOR_CM_PER_SECOND = 3.0
TRACE_SAMPLE_SECONDS = 1 / 20
MM_PER_POINT = 25.4 / 72


def trace_speed(value=None):
    speed = MAX_CURSOR_CM_PER_SECOND if value is None else float(value)
    if not math.isfinite(speed) or not 0 < speed <= MAX_CURSOR_CM_PER_SECOND:
        raise ValueError("Trace cursor speed must be greater than 0 and at most 3 cm/s")
    return speed


@dataclass(frozen=True)
class DisplayScale:
    mm_per_point: float
    basis: str


@contextmanager
def office_dpi_context(hwnd):
    """Read monitor pixels in the same DPI coordinates as the Office window."""
    user32 = ctypes.windll.user32
    try:
        context_for_window = user32.GetWindowDpiAwarenessContext
        set_context = user32.SetThreadDpiAwarenessContext
    except AttributeError:
        yield
        return
    context_for_window.argtypes = [ctypes.c_void_p]
    context_for_window.restype = ctypes.c_void_p
    set_context.argtypes = [ctypes.c_void_p]
    set_context.restype = ctypes.c_void_p
    context = context_for_window(hwnd)
    previous = set_context(context) if context else None
    try:
        yield
    finally:
        if previous:
            set_context(previous)


def display_scale(window, hwnd):
    """Use PowerPoint's view scale and the selected Windows display's reported size."""
    import win32api
    import win32gui

    get_cap = ctypes.windll.gdi32.GetDeviceCaps
    get_cap.argtypes = [ctypes.c_void_p, ctypes.c_int]
    try:
        with office_dpi_context(hwnd):
            monitor = win32api.GetMonitorInfo(win32api.MonitorFromWindow(hwnd, 2))
            dc = win32gui.CreateDC("DISPLAY", monitor["Device"], None)
            try:
                width_mm, height_mm, width_px, height_px, dpi_x, dpi_y = (
                    get_cap(int(dc), index) for index in (4, 6, 8, 10, 88, 90)
                )
            finally:
                win32gui.DeleteDC(dc)
    except (OSError, win32gui.error):
        width_mm = height_mm = width_px = height_px = dpi_x = dpi_y = 0
    x_pixels_per_point = abs(window.PointsToScreenPixelsX(720) - window.PointsToScreenPixelsX(0)) / 720
    y_pixels_per_point = abs(window.PointsToScreenPixelsY(720) - window.PointsToScreenPixelsY(0)) / 720
    if min(width_mm, height_mm, width_px, height_px, x_pixels_per_point, y_pixels_per_point) > 0:
        mm_per_point = max(x_pixels_per_point * width_mm / width_px,
                           y_pixels_per_point * height_mm / height_px)
        return DisplayScale(mm_per_point, "windows-display")
    if min(dpi_x, dpi_y, x_pixels_per_point, y_pixels_per_point) > 0:
        mm_per_point = 25.4 * max(x_pixels_per_point / dpi_x, y_pixels_per_point / dpi_y)
        return DisplayScale(mm_per_point, "nominal-dpi")
    return DisplayScale(MM_PER_POINT * window.View.Zoom / 100, "nominal-view")


class TracePacer:
    """Schedule actual display updates and cursor transfers at the selected ceiling."""

    def __init__(self, speed, scale, overlay_pixels_per_point, *, clock=None, sleep=None):
        self.speed_cm = trace_speed(speed)
        self.speed_mm = self.speed_cm * 10
        self.scale = scale
        self.overlay_pixels_per_point = overlay_pixels_per_point
        self.clock = clock or time.perf_counter
        self.sleep = sleep or time.sleep
        self.last_display = None
        self.last_tips = {}
        self.peak_cm = 0.0

    @property
    def step_points(self):
        return self.speed_mm * TRACE_SAMPLE_SECONDS / self.scale.mm_per_point

    def overlay_point(self, position):
        return tuple(round(value * self.overlay_pixels_per_point) for value in position)

    def travel_seconds(self, start, end):
        distance_mm = math.dist(start, end) * self.scale.mm_per_point / self.overlay_pixels_per_point
        return distance_mm / self.speed_mm

    def relocate(self, index, cursor, position):
        previous = self.last_tips.get(index)
        if previous is not None:
            point, shown = previous
            destination = self.overlay_point(position)
            if point != destination:
                cursor.Visible = 0
                yield
                # Other workers continue while this pointer is between contours.
                while self.clock() < shown + self.travel_seconds(point, destination):
                    yield
        cursor.Left, cursor.Top = position
        cursor.Visible = -1

    def move(self, cursor, destination):
        """Limit continuous motion between the editable label's glyph positions."""
        start = (cursor.Left, cursor.Top)
        distance = math.dist(start, destination)
        advanced = 0.0
        while distance - advanced > self.step_points:
            advanced += self.step_points
            fraction = advanced / distance
            cursor.Left, cursor.Top = (
                a + (b - a) * fraction for a, b in zip(start, destination)
            )
            yield
        cursor.Left, cursor.Top = destination

    def before_display(self, points):
        deadline = self.clock()
        if self.last_display is not None:
            deadline = max(deadline, self.last_display + TRACE_SAMPLE_SECONDS)
        for index, point in enumerate(points):
            previous = self.last_tips.get(index)
            if point is not None and previous is not None:
                old_point, shown = previous
                deadline = max(deadline, shown + self.travel_seconds(old_point, point))
        remaining = deadline - self.clock()
        while remaining > 0:
            self.sleep(remaining)
            remaining = deadline - self.clock()

    def displayed(self, points):
        now = self.clock()
        for index, point in enumerate(points):
            if point is None:
                continue
            previous = self.last_tips.get(index)
            if previous is not None and previous[0] != point:
                old_point, shown = previous
                if now > shown:
                    speed = self.travel_seconds(old_point, point) * self.speed_cm / (now - shown)
                    self.peak_cm = max(self.peak_cm, speed)
            self.last_tips[index] = point, now
        self.last_display = now
