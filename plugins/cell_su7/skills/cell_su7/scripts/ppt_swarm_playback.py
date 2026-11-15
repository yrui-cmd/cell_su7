"""Cell native PowerPoint reconstruction preview, adapted from the local Cell PPT player.

Stages an isolated single-slide copy, then expands graphic frames and reveals
editable lettering through temporary native PowerPoint helpers.
"""

import json
import time
from pathlib import Path
from hashlib import sha256
from contextlib import contextmanager
from pptx import Presentation
from typing import NamedTuple

from cursor_overlay import CursorOverlay

SKILL_ID = Path(__file__).resolve().parents[1].name.replace("_", "-")
COLORS = [
    "0284C7",
    "7C3AED",
    "16A34A",
    "EA580C",
    "DB2777",
    "0891B2",
    "4F46E5",
    "CA8A04",
    "0D9488",
    "BE123C",
    "9333EA",
    "DC2626",
]
WORKER_COUNT = 12
FRAME_DELAY = 1 / 60


class PreparedPage(NamedTuple):
    texts: dict
    graphics: dict
    info: dict
    clones: dict
    paste_assets: set
    pointers: list
    bubbles: list
    boxes: list
    frame_ids: set
    presenter: object = None
    text_steps: dict = None
    shape_keys: dict = None
    clone_keys: dict = None


def cache_text_steps(source, clone, full):
    source_range = source.TextFrame.TextRange
    target = clone.TextFrame2.TextRange._oleobj_
    characters_id = target.GetIDsOfNames("Characters")
    result = []
    for offset, units, character, syllable in character_steps(full):
        bounds = source_range.Characters(offset, units)
        x = float(bounds.BoundLeft) + float(bounds.BoundWidth)
        y = float(bounds.BoundTop)
        character_range = target.InvokeTypes(characters_id, 0, 2, (9, 0),
                                             ((3, 49), (3, 49)), offset, units)
        font = character_range.InvokeTypes(character_range.GetIDsOfNames("Font"), 0, 2, (9, 0), ())
        fill = font.InvokeTypes(font.GetIDsOfNames("Fill"), 0, 2, (9, 0), ())
        result.append((character, syllable, x, y, fill, fill.GetIDsOfNames("Transparency")))
    return result


def split_path_sequence(sequence):
    """Split source order into twelve contiguous, nearly equal slices."""
    parts = []
    for index in range(WORKER_COUNT):
        start = index * len(sequence) // WORKER_COUNT
        stop = (index + 1) * len(sequence) // WORKER_COUNT
        parts.append(sequence[start:stop])
    return parts


def preview_has_focus(gui, preview_hwnd):
    if not gui.IsWindow(preview_hwnd):
        raise RuntimeError("The PowerPoint preview window was closed")
    foreground = gui.GetForegroundWindow()
    if not foreground:
        return False
    try:
        return gui.GetAncestor(foreground, 2) == preview_hwnd and not gui.IsIconic(preview_hwnd)
    except Exception as error:
        if error.args and error.args[0] == 1400:
            return False
        raise


def matches_preview_title(title, path):
    path = Path(path)
    return any(title.startswith(name + " - ") for name in (path.name, path.stem))


def fit_preview(window):
    window.View.ZoomToFit = True
    fitted_zoom = window.View.Zoom
    window.View.ZoomToFit = False
    window.View.Zoom = fitted_zoom


def configure_preview_window(app, window, fullscreen=True):
    """Prepare the editor before revealing anything; HideRibbon is a toggle."""
    window.Activate()
    window.WindowState = 3
    window.ViewType = 1
    if fullscreen:
        # Maximizing only DocumentWindow leaves the outer application window small.
        app.WindowState = 3
        if not app.CommandBars.GetPressedMso("HideRibbon"):
            app.CommandBars.ExecuteMso("HideRibbon")
        # Ribbon changes can restore the application's previous normal bounds.
        app.WindowState = 3
        if not app.CommandBars.GetPressedMso("HideRibbon"):
            raise RuntimeError("PowerPoint did not enter the full-screen editor")
    fit_preview(window)


def request_preview_foreground(window, gui, hwnd):
    """Try once at startup; Windows may require a user or desktop-tool activation."""
    window.Activate()
    try:
        gui.SetForegroundWindow(hwnd)
    except gui.error:
        pass


def wait_for_start(gate, cancel, timeout=900):
    deadline = time.monotonic() + timeout
    while not gate.exists():
        if cancel.exists():
            raise RuntimeError("Playback cancelled before starting")
        if time.monotonic() >= deadline:
            raise RuntimeError("Playback start signal did not arrive")
        time.sleep(0.05)


def is_frame_shape(shape):
    """Recognize native rectangles, including rounded rectangles from SVG tracing."""
    if int(shape.shape_type) in {3, 6, 11, 13, 19, 28, 29}:
        return True
    geometry = shape._element.find("{http://schemas.openxmlformats.org/presentationml/2006/main}spPr")
    if geometry is None:
        return False
    drawing = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
    if int(shape.shape_type) == 17:
        fill = any(geometry.find(drawing + kind) is not None
                   for kind in ("solidFill", "gradFill", "pattFill", "blipFill"))
        line = geometry.find(drawing + "ln")
        return fill or (line is not None and line.find(drawing + "noFill") is None)
    preset = geometry.find(drawing + "prstGeom")
    if preset is not None and "rect" in preset.get("prst", "").lower():
        return True
    if shape.has_text_frame and shape.text.strip() and shape.fill.type is not None:
        return True
    paths = geometry.findall(drawing + "custGeom/" + drawing + "pathLst/" + drawing + "path")
    if len(paths) != 1:
        return False
    commands = list(paths[0])
    if not 5 <= len(commands) <= 48 or commands[-1].tag != drawing + "close":
        return False
    horizontal = vertical = False
    previous = None
    all_points = paths[0].findall(".//" + drawing + "pt")
    extent_x = max(int(point.get("x")) for point in all_points) - min(int(point.get("x")) for point in all_points)
    extent_y = max(int(point.get("y")) for point in all_points) - min(int(point.get("y")) for point in all_points)
    for command in commands:
        points = command.findall(drawing + "pt")
        if not points:
            continue
        coordinates = [tuple(int(point.get(key)) for key in ("x", "y")) for point in points]
        point = coordinates[-1]
        if command.tag in {drawing + "lnTo", drawing + "cubicBezTo"} and previous is not None:
            horizontal |= (all(abs(value[1] - previous[1]) <= extent_y * 0.015 for value in coordinates)
                           and abs(point[0] - previous[0]) >= extent_x * 0.05)
            vertical |= (all(abs(value[0] - previous[0]) <= extent_x * 0.015 for value in coordinates)
                         and abs(point[1] - previous[1]) >= extent_y * 0.05)
        previous = point
    return horizontal and vertical


def prepare_manifest(source, destination, *, fullscreen=True, wait_for_start=False):
    import uuid
    from prepare_path_playback import prepare

    source, destination = Path(source).resolve(), Path(destination).resolve()
    # Check dependencies before staging a hidden file or opening PowerPoint.
    import win32com.client
    import pypinyin

    original = Presentation(source)
    width, height = original.slide_width, original.slide_height
    targets, frames = {}, {}
    for slide in original.slides:
        page = str(slide.slide_id)
        targets[page] = [shape.shape_id for shape in slide.shapes]
        frames[page] = [shape.shape_id for shape in slide.shapes
                        if shape.width >= 12 * 12700 and shape.height >= 8 * 12700
                        and shape.width * shape.height < width * height * 0.9
                        and is_frame_shape(shape)]
    prepare(source, destination)
    state = {
        "job_id": SKILL_ID, "run_id": uuid.uuid4().hex,
        "source": str(source), "copy": str(destination),
        "copy_sha256": sha256(destination.read_bytes()).hexdigest(),
        "targets": targets, "frame_ids": frames,
        "fullscreen": bool(fullscreen), "wait_for_start": bool(wait_for_start),
    }
    manifest = destination.with_suffix(".playback.json")
    manifest.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return manifest


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-pptx", required=True, type=Path)
    parser.add_argument("--output-pptx", required=True, type=Path)
    parser.add_argument("--windowed", action="store_true",
                        help="Use the current editor layout without requesting full screen")
    parser.add_argument("--wait-for-start", action="store_true",
                        help="Prepare the view, then wait for the start file in window-ready.json")
    args = parser.parse_args()
    return run(prepare_manifest(args.input_pptx, args.output_pptx,
                                fullscreen=not args.windowed,
                                wait_for_start=args.wait_for_start))


BUSY_ERRORS = {-2147418111, -2147417846}


def com_retry(action, timeout=8.0):
    """Retry only explicit RPC busy/rejected calls; other failures stay visible."""
    deadline = time.monotonic() + timeout
    while True:
        try:
            return action()
        except Exception as error:
            if (
                getattr(error, "hresult", None) not in BUSY_ERRORS
                or time.monotonic() >= deadline
            ):
                raise
            time.sleep(0.04)


class ComObject:
    """Bounded busy-call recovery for nested Office objects and methods."""

    def __init__(self, obj):
        object.__setattr__(self, "_obj", obj)

    def __getattr__(self, name):
        value = com_retry(lambda: getattr(self._obj, name))
        if name == "_oleobj_":
            return value
        if hasattr(value, "_oleobj_"):
            return wrap_com(value)
        if callable(value):
            return lambda *a, **kw: wrap_com(com_retry(lambda: value(*a, **kw)))
        return wrap_com(value)

    def __setattr__(self, name, value):
        com_retry(lambda: setattr(self._obj, name, value))

    def __iter__(self):
        for n in range(1, self.Count + 1):
            yield self.Item(n)


def wrap_com(value):
    return ComObject(value) if hasattr(value, "_oleobj_") else value


def rgb(h):
    return int(h[:2], 16) + (int(h[2:4], 16) << 8) + (int(h[4:], 16) << 16)


def character_steps(text):
    from pypinyin import lazy_pinyin

    syllables = lazy_pinyin(text, errors=lambda chars: list(chars))
    if len(syllables) != len(text):
        raise ValueError("Pinyin character mapping is incomplete")
    offset = 1
    for char, syllable in zip(text, syllables):
        units = len(char.encode("utf-16-le")) // 2
        yield offset, units, char, syllable
        offset += units


def advance(streams):
    """Advance every independent cursor once, rather than drain one cursor first."""
    active = []
    for stream in streams:
        try:
            next(stream)
            active.append(stream)
        except StopIteration:
            pass
    return active


def content_signature(path):
    def shape(s):
        result = [
            s.shape_id,
            s.name,
            int(s.shape_type),
            *[round(v / 12700, 2) for v in (s.left, s.top, s.width, s.height)],
            round(s.rotation, 2),
        ]
        if s.has_text_frame:
            result.append(
                [
                    [
                        p.text,
                        [
                            [
                                r.text,
                                r.font.name,
                                r.font.size,
                                r.font.bold,
                                r.font.italic,
                            ]
                            for r in p.runs
                            if r.text
                        ],
                    ]
                    for p in s.text_frame.paragraphs
                ]
            )
        if s.shape_type == 6:
            result.append([shape(child) for child in s.shapes])
        return result

    return [[shape(s) for s in page.shapes] for page in Presentation(path).slides]


def validate_targets(deck, targets):
    slides = {str(s.SlideID): s for s in deck.Slides}
    if not isinstance(targets, dict):
        raise ValueError("Invalid playback targets")
    mapped = {}
    for page, ids in targets.items():
        if page not in slides or len(ids) != len(set(ids)):
            raise ValueError("Invalid playback slide or duplicate element")
        shapes = {s.Id: s for s in slides[page].Shapes}
        if any(type(i) is not int or i not in shapes for i in ids):
            raise ValueError("Preview element is missing")
        if any(shapes[i].Visible for i in ids):
            raise ValueError("Preview content must be hidden before opening")
        mapped[page] = [shapes[i] for i in ids]
    return slides, mapped


@contextmanager
def exclusive_playback():
    import win32event, win32api

    handle = win32event.CreateMutex(None, False, r"Local\CellPptElementPlayback")
    locked = False
    try:
        locked = win32event.WaitForSingleObject(handle, 0) in (0, 128)
        if not locked:
            raise RuntimeError("A PowerPoint playback session is already running")
        yield
    finally:
        if locked:
            win32event.ReleaseMutex(handle)
        win32api.CloseHandle(handle)


def prepare_page(slide, shapes, W, H, helpers, frame_ids):
    """Build helpers while the presentation has no window, never on page entry."""
    # Cache COM properties once. Keep all geometry inside the slide bounds.
    texts, graphics, info, clones, text_steps = {}, {}, {}, {}, {}
    paste_assets = set()
    for shape in shapes:
        sid = shape.Id
        x, y, w, h = map(float, (shape.Left, shape.Top, shape.Width, shape.Height))
        text = (
            shape.TextFrame.TextRange.Text
            if shape.HasTextFrame and shape.TextFrame.HasText
            else ""
        )
        info[sid] = (x, y, w, h, shape.ZOrderPosition, text)
        if text.strip():
            texts[sid] = shape
            clone = shape.Duplicate().Item(1)
            helpers.append(clone)
            clone.Visible = 0
            clone.Left, clone.Top = x, y
            clone.TextFrame2.TextRange.Font.Fill.Transparency = 1.0
            clones[sid] = clone
            text_steps[sid] = cache_text_steps(shape, clone, text)
        else:
            graphics[sid] = shape
            # Pictures, linked pictures, grouped illustrations, charts/tables and SVGs.
            if int(shape.Type) in {3, 6, 11, 13, 19, 28, 29}:
                paste_assets.add(sid)
        if text.strip() and sid in frame_ids:
            graphics[sid] = shape
    path_parts = split_path_sequence(sorted(info, key=lambda sid: info[sid][4]))
    presenter = CursorOverlay(slide, W, H, COLORS)
    helpers.append(presenter.shape)
    for index, part in enumerate(path_parts):
        if part:
            x, y, w, h, *_ = info[part[0]]
            pointer = presenter.pointers[index]
            pointer.Left = max(0, min(W - 16, x + w / 2))
            pointer.Top = max(0, min(H - 22, y + h / 2))
    shapes = {**graphics, **texts}
    shape_keys = {sid: shape.ZOrderPosition for sid, shape in shapes.items()}
    clone_keys = {sid: clone.ZOrderPosition for sid, clone in clones.items()}
    return PreparedPage(texts, graphics, info, clones, paste_assets,
                        presenter.pointers, presenter.bubbles, presenter.boxes,
                        frame_ids, presenter, text_steps, shape_keys, clone_keys)



def page_stream(prepared, W, H, helpers, metrics):
    texts, graphics, info, clones, paste_assets, pointers, bubbles, boxes, frame_ids = prepared[:9]
    graphic_ids = sorted(graphics, key=lambda sid: info[sid][4])
    ordered_ids = sorted(info, key=lambda sid: info[sid][4])
    path_parts = split_path_sequence(ordered_ids)
    graphic_shapes, text_shapes = graphics, texts
    native_shapes = {**graphics, **texts}

    def show_shape(sid, visible=True, clone=False):
        if prepared.presenter is not None:
            keys = prepared.clone_keys if clone else prepared.shape_keys
            prepared.presenter.show(keys[sid], visible)
        else:
            shape = clones[sid] if clone else native_shapes[sid]
            shape.Visible = -1 if visible else 0

    metrics.update(partition_count=WORKER_COUNT,
                   partition_sizes=[len(part) for part in path_parts],
                   max_active_workers=0)
    drawn, active_kind = set(), {}
    parallel_text_frames = parallel_frames = 0

    def motion(i, tx, ty, steps=2):
        c = pointers[i]
        tx, ty = max(0, min(W - 16, tx)), max(0, min(H - 22, ty))
        c.Visible = -1
        x0, y0 = float(c.Left), float(c.Top)
        for n in range(1, steps + 1):
            q = n / steps
            q = q * q * (3 - 2 * q)
            c.Left = x0 + (tx - x0) * q
            c.Top = y0 + (ty - y0) * q
            yield

    def graphic_worker(i, queue):
        c = pointers[i]
        bubble = bubbles[i]
        for sid in queue:
            active_kind[i] = "graphic"
            x, y, sw, sh, *_ = info[sid]
            if sid in frame_ids or sid in paste_assets:
                yield from motion(i, x, y, steps=1)
                box = boxes[i]
                left, top = max(0, x), max(0, y)
                width = max(1, min(W, x + sw) - left)
                height = max(1, min(H, y + sh) - top)
                box.Left, box.Top = left, top
                box.Width = box.Height = 1
                box.Visible = -1
                bubble.Visible = -1
                for frame in range(1, 9):
                    progress = frame / 8
                    progress = progress * progress * (3 - 2 * progress)
                    current_w, current_h = max(1, width * progress), max(1, height * progress)
                    box.Width, box.Height = current_w, current_h
                    c.Left = max(0, min(W - 16, left + current_w))
                    c.Top = max(0, min(H - 22, top + current_h))
                    bubble.Left = max(0, min(W - 88, c.Left - 88))
                    bubble.Top = max(0, min(H - 24, c.Top + 4))
                    bubble.TextFrame.TextRange.Text = f"{round(current_w)} × {round(current_h)} pt"
                    metrics["graphic_drag_frames"] = metrics.get("graphic_drag_frames", 0) + 1
                    yield
                box.Visible = 0
                bubble.Visible = 0
                metrics["dragged_graphics"] = metrics.get("dragged_graphics", 0) + 1
            else:
                c.Left = max(0, min(W - 16, x + sw / 2))
                c.Top = max(0, min(H - 22, y + sh / 2))
            # A text-bearing frame uses its existing text-hidden clone until typing ends.
            if sid in clones:
                show_shape(sid, clone=True)
            else:
                show_shape(sid)
            drawn.add(sid)
            yield
        active_kind.pop(i, None)
        bubble.Visible = 0

    def text_worker(i, queue):
        c = pointers[i]
        b = bubbles[i]
        for sid in queue:
            # Wait for overlapping background graphics to avoid text appearing on an absent card.
            x, y, sw, sh, z, full = info[sid]
            parents = [
                identifier
                for identifier in graphic_ids
                if (
                    lambda a: a[2] > 20
                    and a[3] > 15
                    and a[4] < z
                    and a[0] <= x + 2
                    and a[1] <= y + 2
                    and a[0] + a[2] >= x + sw - 2
                    and a[1] + a[3] >= y + sh - 2
                )(info[identifier])
            ]
            if sid in frame_ids:
                parents.append(sid)
            while any(k not in drawn for k in parents):
                active_kind[i] = "waiting"
                yield
            active_kind[i] = "text"
            yield from motion(i, x, y, steps=1)
            show_shape(sid, clone=True)
            bubble_range = b.TextFrame.TextRange
            for ch, py, x, y, fill, transparency_id in prepared.text_steps[sid]:
                cx = max(0, min(W - 18, x))
                cy = max(0, min(H - 24, y))
                c.Left = cx
                c.Top = cy
                if "\u4e00" <= ch <= "\u9fff":
                    b.Left = max(0, min(W - 88, cx))
                    b.Top = max(0, min(H - 24, cy + 24))
                    for k in [len(py)]:
                        bubble_range.Text = py[:k]
                        b.Visible = -1
                        yield
                com_retry(lambda: fill.InvokeTypes(
                    transparency_id, 0, 4, (24, 0), ((4, 1),), 0.0
                ))
                b.Visible = 0
                yield
            show_shape(sid)
            show_shape(sid, visible=False, clone=True)
        active_kind.pop(i, None)
        b.Visible = 0

    def path_worker(i, part):
        if not part:
            return
        pointers[i].Visible = -1
        yield
        for sid in part:
            if sid in graphic_shapes:
                yield from graphic_worker(i, [sid])
            if sid in text_shapes:
                yield from text_worker(i, [sid])
        pointers[i].Visible = 0
        bubbles[i].Visible = 0
        boxes[i].Visible = 0

    agents = [path_worker(index, part) for index, part in enumerate(path_parts)]
    while agents:
        agents = advance(agents)
        active_workers = sum(value != "waiting" for value in active_kind.values())
        metrics["max_active_workers"] = max(metrics["max_active_workers"], active_workers)
        if active_workers > 1:
            parallel_frames += 1
        if sum(v == "text" for v in active_kind.values()) > 1:
            parallel_text_frames += 1
        if prepared.presenter is not None:
            prepared.presenter.publish()
        yield
    # Hide only here. Delete in one final cleanup, never during typing.
    for helper in helpers:
        helper.Visible = 0

    metrics.update(
        parallel_frames=parallel_frames, parallel_text_frames=parallel_text_frames
    )


def run(manifest):
    import win32com.client, win32gui

    # Fail before opening PowerPoint if the optional platform dependency is missing.
    import pypinyin

    manifest = Path(manifest).resolve()
    state = json.loads(manifest.read_text(encoding="utf-8-sig"))
    copy, source = Path(state["copy"]).resolve(), Path(state["source"]).resolve()
    if (
        copy.parent != manifest.parent
        or copy == source
        or sha256(copy.read_bytes()).hexdigest() != state["copy_sha256"]
    ):
        raise ValueError("Invalid isolated preview copy")
    original_hash = sha256(source.read_bytes()).hexdigest()
    expected = content_signature(copy)
    helpers = {}
    metrics = {}
    app = deck = None
    presenters = []
    completed = False
    with exclusive_playback():
        try:
            app = wrap_com(win32com.client.Dispatch("PowerPoint.Application"))
            app.Visible = True
            # No visible window while duplicating text or constructing cursor helpers.
            # These COM mutations otherwise repaint and re-fit the active slide repeatedly.
            deck = app.Presentations.Open(str(copy), False, False, False)
            slides, pending = validate_targets(deck, state["targets"])
            pending = {k: v for k, v in pending.items() if v}
            width, height = float(deck.PageSetup.SlideWidth), float(
                deck.PageSetup.SlideHeight
            )
            prepared = {}
            for page in pending:
                helpers[page] = []
                metrics[page] = {}
                prepared[page] = prepare_page(
                    slides[page], pending[page], width, height, helpers[page],
                    set(state["frame_ids"].get(page, []))
                )
                presenters.append(prepared[page].presenter)
            window = deck.NewWindow()
            fullscreen = state.get("fullscreen", True)
            configure_preview_window(app, window, fullscreen)
            if pending:
                window.View.GotoSlide(min(slides[k].SlideIndex for k in pending))
            import win32process
            preview_windows = []
            win32gui.EnumWindows(
                lambda hwnd, _: preview_windows.append(hwnd)
                if matches_preview_title(win32gui.GetWindowText(hwnd), copy) else None,
                None,
            )
            if len(preview_windows) != 1:
                raise RuntimeError("Cannot uniquely identify the PowerPoint preview window")
            preview_hwnd = preview_windows[0]
            start_file = (manifest.parent / f"{copy.stem}.{state['run_id']}.start"
                          if state.get("wait_for_start") else None)
            (manifest.parent / "window-ready.json").write_text(json.dumps({
                "job_id": state["job_id"], "run_id": state["run_id"],
                "hwnd": preview_hwnd,
                "pid": win32process.GetWindowThreadProcessId(preview_hwnd)[1],
                "copy": str(copy), "fullscreen": fullscreen,
                "start_file": str(start_file) if start_file else None,
            }), encoding="utf-8")
            request_preview_foreground(window, win32gui, preview_hwnd)
            print("ELEMENT_PLAYBACK_EDITOR_OPEN", flush=True)
            if fullscreen:
                print("ELEMENT_PLAYBACK_FULLSCREEN_READY", flush=True)
            if start_file is not None:
                print("ELEMENT_PLAYBACK_WAITING_FOR_START|" + str(start_file), flush=True)
                wait_for_start(start_file, manifest.parent / "playback.cancel")
            if state.get("recording_gate"):
                wait_for_start(manifest.parent / "recording.started",
                               manifest.parent / "playback.cancel")
            streams = {}
            render_samples = {}
            started = time.monotonic()
            waiting = False
            view_fitted = False
            last_view_check = 0.0
            slide = window.View.Slide
            active = window
            while pending:
                if (manifest.parent / "playback.cancel").exists():
                    raise RuntimeError("Playback cancelled")
                if not preview_has_focus(win32gui, preview_hwnd):
                    if not waiting:
                        print("ELEMENT_PLAYBACK_WAITING_FOR_FOREGROUND", flush=True)
                        waiting = True
                    time.sleep(0.1)
                    continue
                if waiting:
                    print("ELEMENT_PLAYBACK_FOREGROUND_READY", flush=True)
                    waiting = False
                if not view_fitted:
                    # A gated desktop setup may have changed the available canvas.
                    fit_preview(window)
                    view_fitted = True
                    if not preview_has_focus(win32gui, preview_hwnd):
                        continue
                if time.monotonic() - last_view_check > 0.25:
                    slide = active.View.Slide
                    last_view_check = time.monotonic()
                page = str(slide.SlideID)
                if page not in pending:
                    time.sleep(0.1)
                    continue
                if page not in streams:
                    streams[page] = page_stream(
                        prepared[page],
                        width,
                        height,
                        helpers[page],
                        metrics[page],
                    )
                    print(
                        f"ELEMENT_PLAYBACK_PAGE_BEGIN|{slide.SlideIndex}|{int((time.monotonic()-started)*1000)}",
                        flush=True,
                    )
                frame_started = time.perf_counter()
                try:
                    next(streams[page])
                    render_samples.setdefault(page, []).append(time.perf_counter() - frame_started)
                except StopIteration:
                    del pending[page]
                    print(
                        f"ELEMENT_PLAYBACK_PAGE_DONE|{slide.SlideIndex}|{int((time.monotonic()-started)*1000)}",
                        flush=True,
                    )
                    # Respect a manual page switch; resume the other page on its next frame.
                    if pending and str(active.View.Slide.SlideID) == page:
                        later = sorted(pending, key=lambda p: slides[p].SlideIndex)
                        next_page = next(
                            (
                                p
                                for p in later
                                if slides[p].SlideIndex > slide.SlideIndex
                            ),
                            later[0],
                        )
                        active.View.GotoSlide(slides[next_page].SlideIndex)
                        slide = slides[next_page]
                        last_view_check = time.monotonic()
                remaining = FRAME_DELAY - (time.perf_counter() - frame_started)
                if remaining > 0:
                    time.sleep(remaining)
            # All helpers are already hidden. One cleanup after every page has finished.
            for page, samples in render_samples.items():
                ordered = sorted(samples)
                metrics[page].update(
                    rendered_frames=len(samples),
                    active_render_seconds=round(sum(samples), 3),
                    median_frame_ms=round(ordered[len(ordered) // 2] * 1000, 2),
                    p95_frame_ms=round(ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))] * 1000, 2),
                )
            for page_helpers in helpers.values():
                for helper in page_helpers:
                    helper.Delete()
                page_helpers.clear()
            deck.Save()
            if content_signature(copy) != expected:
                raise RuntimeError("Preview content or geometry changed during output")
            if sha256(source.read_bytes()).hexdigest() != original_hash:
                raise RuntimeError("Received source changed during output")
            restored = Presentation(copy)
            for page in restored.slides:
                ids = state["targets"].get(str(page.slide_id), [])
                for shape in page.shapes:
                    if shape.shape_id in ids and shape._element[0].find(
                        "{http://schemas.openxmlformats.org/presentationml/2006/main}cNvPr"
                    ).get("hidden") in {"1", "true"}:
                        raise RuntimeError("A preview element remains hidden")
            print("ELEMENT_PLAYBACK_SWARM_METRICS|" + json.dumps(metrics), flush=True)
            print("ELEMENT_PLAYBACK_WORKER_FINISHED", flush=True)
            completed = True
            print(f"PATH_PLAYBACK_OK|objects={sum(len(ids) for ids in state['targets'].values())}"
                  f"|seconds={time.monotonic() - started:.3f}|file={copy}|mode=drag", flush=True)
        finally:
            # Failed previews stay recoverable; never leave simulated cursors in saved output.
            if deck is not None:
                for page_helpers in helpers.values():
                    for helper in page_helpers:
                        try:
                            helper.Delete()
                        except Exception:
                            pass
                if not completed:
                    try:
                        for slide in deck.Slides:
                            ids = state["targets"].get(str(slide.SlideID), [])
                            for shape in slide.Shapes:
                                if shape.Id in ids:
                                    shape.Visible = -1
                        deck.Save()
                    except Exception:
                        pass
            for presenter in presenters:
                presenter.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
