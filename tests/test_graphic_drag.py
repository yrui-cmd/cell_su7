"""Regression checks for graphic dragging in the native Cell preview."""
import importlib.util
import math
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls, qn
from pptx.util import Inches, Pt

SKILL_ROOT = Path(__file__).resolve().parents[1]
if not (SKILL_ROOT / 'scripts/ppt_swarm_playback.py').is_file():
    SKILL_ROOT = SKILL_ROOT / 'plugins/cell_su7/skills/cell_su7'
sys.path.insert(0, str(SKILL_ROOT / 'scripts'))
SPEC = importlib.util.spec_from_file_location(
    SKILL_ROOT.name + '_playback_test_target', SKILL_ROOT / 'scripts/ppt_swarm_playback.py')
playback = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = playback
SPEC.loader.exec_module(playback)
from prepare_path_playback import prepare
from path_trace import PathTrace, drawable_trace
from path_speed import DisplayScale, TracePacer, trace_speed


class GraphicDragTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == 'win32', 'Windows playback dependencies')
    def test_manifest_preserves_its_skill_identity_and_start_settings(self):
        with TemporaryDirectory() as folder:
            source, output = Path(folder) / 'source.pptx', Path(folder) / 'playback.pptx'
            deck = Presentation()
            slide = deck.slides.add_slide(deck.slide_layouts[6])
            slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(1), Inches(1))
            deck.save(source)
            original = source.read_bytes()
            manifest = playback.prepare_manifest(source, output, wait_for_start=True)
            import json
            state = json.loads(manifest.read_text())
            self.assertEqual(state['job_id'], SKILL_ROOT.name.replace('_', '-'))
            self.assertTrue(state['fullscreen'])
            self.assertTrue(state['wait_for_start'])
            self.assertEqual(state['mode'], 'drag')
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(sum(map(len, state['targets'].values())), 1)
            traced = playback.prepare_manifest(source, Path(folder) / 'trace.pptx', mode='trace')
            trace_state = json.loads(traced.read_text())
            self.assertEqual(trace_state['mode'], 'trace')
            self.assertEqual(trace_state['max_cursor_cm_per_second'], 3.0)
            self.assertNotIn('max_cursor_cm_per_second', state)
            slower = playback.prepare_manifest(source, Path(folder) / 'slow.pptx',
                                               mode='trace', max_cursor_cm_per_second=1.5)
            self.assertEqual(json.loads(slower.read_text())['max_cursor_cm_per_second'], 1.5)

    def test_fullscreen_startup_is_idempotent_and_fits_after_layout(self):
        events = []
        class Commands:
            pressed = False
            def GetPressedMso(self, command):
                self.assert_command(command)
                return self.pressed
            def ExecuteMso(self, command):
                self.assert_command(command)
                self.pressed = not self.pressed
                events.append('ribbon')
            def assert_command(self, command):
                if command != 'HideRibbon':
                    raise AssertionError(command)
        commands = Commands()
        class View:
            Zoom = 170
            def __setattr__(self, name, value):
                if name == 'ZoomToFit' and value:
                    events.append(('fit', commands.pressed))
                object.__setattr__(self, name, value)
        app = SimpleNamespace(WindowState=1, CommandBars=commands)
        window = SimpleNamespace(Activate=lambda: None, WindowState=1,
                                 ViewType=0, View=View())
        playback.configure_preview_window(app, window)
        playback.configure_preview_window(app, window)
        self.assertEqual(events, ['ribbon', ('fit', True), ('fit', True)])
        self.assertEqual(app.WindowState, 3)
        self.assertEqual((window.WindowState, window.ViewType), (3, 1))
        self.assertFalse(window.View.ZoomToFit)
        self.assertEqual(window.View.Zoom, 170)

    def test_denied_foreground_request_keeps_preview_waiting(self):
        class ForegroundDenied(Exception):
            pass
        def deny(hwnd):
            raise ForegroundDenied()
        gui = SimpleNamespace(error=ForegroundDenied, SetForegroundWindow=deny,
                              IsWindow=lambda hwnd: True,
                              GetForegroundWindow=lambda: 100,
                              GetAncestor=lambda hwnd, flag: 100)
        window = SimpleNamespace(Activate=lambda: None)
        playback.request_preview_foreground(window, gui, 200)
        self.assertFalse(playback.preview_has_focus(gui, 200))

    def test_start_gate_requires_its_own_signal_and_honors_cancellation(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'previous-run.start').touch()
            gate, cancel = root / 'current-run.start', root / 'playback.cancel'
            with self.assertRaisesRegex(RuntimeError, 'did not arrive'):
                playback.wait_for_start(gate, cancel, timeout=0)
            cancel.touch()
            with self.assertRaisesRegex(RuntimeError, 'cancelled'):
                playback.wait_for_start(gate, cancel)
            cancel.unlink()
            gate.touch()
            playback.wait_for_start(gate, cancel, timeout=0)

    def test_twelve_contiguous_segments_preserve_source_path_order(self):
        self.assertEqual(playback.WORKER_COUNT, 12)
        self.assertEqual(len(set(playback.COLORS)), 12)
        for count in [0, 3, 12, 13, 2086]:
            original = list(range(count))
            parts = playback.split_path_sequence(original)
            self.assertEqual(len(parts), 12)
            self.assertEqual([path for part in parts for path in part], original)
            self.assertLessEqual(max(map(len, parts)) - min(map(len, parts)), 1)
        parts = playback.split_path_sequence(list(range(2086)))
        self.assertEqual(parts[0], list(range(173)))
        self.assertEqual(parts[-1], list(range(1912, 2086)))

    def test_transient_foreground_handle_does_not_abort_playback(self):
        def invalid_handle(*args):
            raise RuntimeError(1400, 'GetAncestor', 'Invalid window handle')
        gui = SimpleNamespace(IsWindow=lambda hwnd: True,
                              GetForegroundWindow=lambda: 123,
                              GetAncestor=invalid_handle)
        self.assertFalse(playback.preview_has_focus(gui, 456))
        gui.GetForegroundWindow = lambda: 0
        self.assertFalse(playback.preview_has_focus(gui, 456))
        gui.GetForegroundWindow = lambda: 123
        gui.GetAncestor = lambda hwnd, flag: 456
        gui.IsIconic = lambda hwnd: False
        self.assertTrue(playback.preview_has_focus(gui, 456))
        gui.IsWindow = lambda hwnd: False
        with self.assertRaises(RuntimeError):
            playback.preview_has_focus(gui, 456)

    def test_twelve_pointers_advance_their_contiguous_slices_together(self):
        events = []
        class RecordedShape:
            def __init__(self, identifier):
                self.Id = identifier
                self.Visible = 0
            def __setattr__(self, name, value):
                if name == 'Visible' and value == -1:
                    events.append(self.Id)
                object.__setattr__(self, name, value)

        graphics = [RecordedShape(index + 1) for index in range(60)]
        info = {shape.Id: (index % 10 * 30, index // 10 * 30, 20, 20, index, '')
                for index, shape in enumerate(graphics)}
        pointers = [SimpleNamespace(Left=0, Top=0, Visible=0) for _ in playback.COLORS]
        bubbles = [SimpleNamespace(Visible=0) for _ in playback.COLORS]
        boxes = [SimpleNamespace(Visible=0) for _ in playback.COLORS]
        prepared = playback.PreparedPage({}, {shape.Id: shape for shape in graphics},
                                         info, {}, set(), pointers, bubbles, boxes, set())
        metrics = {}
        for _ in playback.page_stream(prepared, 400, 300, [], metrics):
            pass
        for step in range(5):
            self.assertEqual(events[step * 12:(step + 1) * 12], list(range(step + 1, 61, 5)))
        self.assertEqual(metrics['partition_sizes'], [5] * 12)
        self.assertEqual(metrics['max_active_workers'], 12)

    def test_trace_uses_native_curve_coordinates_and_separate_contours(self):
        deck = Presentation()
        slide = deck.slides.add_slide(deck.slide_layouts[6])
        shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Pt(100), Pt(70), Pt(120), Pt(60))
        props = shape._element.find(qn('p:spPr'))
        preset = props.find(qn('a:prstGeom'))
        props.replace(preset, parse_xml(f'<a:custGeom {nsdecls("a")}><a:pathLst>'
                                        '<a:path w="12" h="6"><a:moveTo><a:pt x="0" y="0"/></a:moveTo>'
                                        '<a:cubicBezTo><a:pt x="0" y="6"/><a:pt x="12" y="6"/>'
                                        '<a:pt x="12" y="0"/></a:cubicBezTo></a:path>'
                                        '</a:pathLst></a:custGeom>'))
        trace = drawable_trace(shape)
        self.assertEqual(trace.at(0), ((100, 70), (((100, 70),),)))
        tip, outline = trace.at(0.5)
        self.assertAlmostEqual(tip[0], 160)
        self.assertAlmostEqual(tip[1], 115)
        self.assertEqual(outline[-1][-1], tip)
        self.assertEqual(trace.at(1)[0], (220, 70))
        disconnected = PathTrace((((10, 30), (14, 30)), ((71, 54), (77, 54))))
        self.assertEqual(disconnected.at(0.4), ((71, 54), (((10, 30), (14, 30)), ((71, 54),))))

    def test_trace_workers_show_at_path_starts_and_reveal_after_tracing(self):
        graphics = {sid: SimpleNamespace(Visible=0) for sid in range(1, 13)}
        info = {sid: (30, 30, 40, 30, sid, '') for sid in graphics}
        paths = {sid: PathTrace((((sid * 17, 80), (sid * 17 + 12, 80), (sid * 17 + 12, 92)),))
                 for sid in graphics}
        pointers = [SimpleNamespace(Left=0, Top=0, Visible=0) for _ in graphics]
        boxes = [SimpleNamespace(Visible=0) for _ in graphics]
        bubbles = [SimpleNamespace(Visible=0) for _ in graphics]
        shown = []
        presenter = SimpleNamespace(trace_paths=[()] * 12, show=lambda key, visible: shown.append(key),
                                    publish=lambda: None)
        prepared = playback.PreparedPage({}, graphics, info, {}, set(), pointers, bubbles, boxes, set(),
                                         presenter=presenter, shape_keys={sid: sid for sid in graphics},
                                         traces=paths)
        stats = {}
        frames = playback.page_stream(prepared, 400, 300, [], stats)
        next(frames)
        self.assertEqual(shown, [])
        for cursor, outline, trace in zip(pointers, presenter.trace_paths, paths.values()):
            self.assertEqual((cursor.Left, cursor.Top), trace.at(0)[0])
            self.assertEqual(outline, trace.at(0)[1])
        next(frames)
        self.assertEqual(shown, [])
        for cursor, outline in zip(pointers, presenter.trace_paths):
            self.assertEqual((cursor.Left, cursor.Top), outline[-1][-1])
        for _ in frames:
            pass
        self.assertEqual(shown, list(graphics))
        self.assertEqual(stats['max_active_workers'], 12)
        self.assertEqual(stats['traced_graphics'], 12)
        self.assertFalse(any(p.Visible for p in pointers))
        self.assertFalse(any(presenter.trace_paths))

    def test_trace_speed_accepts_only_a_positive_ceiling_up_to_three(self):
        self.assertEqual(trace_speed(), 3.0)
        self.assertEqual(trace_speed('1.5'), 1.5)
        for invalid in (0, -1, 3.01, float('inf'), float('nan')):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                trace_speed(invalid)

    def test_paced_trace_keeps_the_cap_during_contours_and_transfers(self):
        first = PathTrace((((10, 20), (20, 20)), ((50, 20), (60, 20))))
        second = PathTrace((((10, 80), (100, 80)),))
        pointers = [SimpleNamespace(Left=0, Top=0, Visible=0) for _ in playback.COLORS]
        boxes = [SimpleNamespace(Visible=0) for _ in playback.COLORS]
        bubbles = [SimpleNamespace(Visible=0) for _ in playback.COLORS]
        now = [0.0]
        events = []
        shown = []

        def sleep(duration):
            now[0] += duration

        pacer = TracePacer(3, DisplayScale(1, 'test-display'), 1, clock=lambda: now[0], sleep=sleep)

        def publish(rate):
            points = [rate.overlay_point((p.Left, p.Top)) if p.Visible else None for p in pointers]
            rate.before_display(points)
            rate.displayed(points)
            events.append((now[0], points, tuple(presenter.trace_paths)))

        presenter = SimpleNamespace(trace_paths=[()] * 12, show=lambda key, visible: shown.append(key),
                                    publish=publish)
        info = {10: (10, 20, 50, 1, 1, ''), 20: (10, 80, 90, 1, 2, '')}
        prepared = playback.PreparedPage({}, {10: object(), 20: object()}, info, {}, set(),
                                         pointers, bubbles, boxes, set(), presenter=presenter,
                                         shape_keys={10: 10, 20: 20}, traces={10: first, 20: second})
        stats = {}
        for _ in playback.page_stream(prepared, 300, 200, [], stats, pacer=pacer):
            sleep(.02)
        first_owner, second_owner = [i for i, part in enumerate(playback.split_path_sequence([10, 20]))
                                     if part]
        visible = [(stamp, points[first_owner]) for stamp, points, _ in events if points[first_owner]]
        self.assertEqual(visible[0][1], (10, 20))
        self.assertEqual(visible[-1][1], (60, 20))
        for (t0, p0), (t1, p1) in zip(visible, visible[1:]):
            self.assertLessEqual(math.dist(p0, p1), 30 * (t1 - t0) + 1e-8)
        self.assertTrue(any(points[first_owner] is None and points[second_owner] is not None
                            and outlines[first_owner] == (((10, 20), (20, 20)),)
                            for _, points, outlines in events))
        self.assertEqual(shown, [10, 20])
        self.assertEqual(stats['cursor_speed_limit_cm_per_second'], 3)
        self.assertLessEqual(stats['peak_cursor_cm_per_second'], 3.00001)
        self.assertFalse(any(pointer.Visible for pointer in pointers))

    def test_pacer_bounds_glyph_motion_and_allows_a_lower_speed(self):
        pacer = TracePacer(1.5, DisplayScale(0.75, 'test-display'), 2)
        cursor = SimpleNamespace(Left=0, Top=0)
        points = [(0, 0)]
        for _ in pacer.move(cursor, (9, 12)):
            points.append((cursor.Left, cursor.Top))
        points.append((cursor.Left, cursor.Top))
        self.assertEqual(points[-1], (9, 12))
        self.assertTrue(all(math.dist(a, b) <= pacer.step_points + 1e-8
                            for a, b in zip(points, points[1:])))

    def test_finished_pointer_disappears_while_other_segments_continue(self):
        graphics = {index: SimpleNamespace(Id=index, Visible=0) for index in range(1, 25)}
        info = {index: (index * 10, 20, 20, 20, index, '') for index in graphics}
        pointers = [SimpleNamespace(Left=0, Top=0, Visible=0) for _ in playback.COLORS]
        bubbles = [SimpleNamespace(Visible=0, TextFrame=SimpleNamespace(
            TextRange=SimpleNamespace(Text=''))) for _ in playback.COLORS]
        boxes = [SimpleNamespace(Visible=0) for _ in playback.COLORS]
        prepared = playback.PreparedPage({}, graphics, info, {}, set(), pointers, bubbles, boxes, {23})
        observed_finished_pointer = False
        for _ in playback.page_stream(prepared, 400, 300, [], {}):
            if pointers[0].Visible == 0 and pointers[-1].Visible == -1:
                observed_finished_pointer = True
        self.assertTrue(observed_finished_pointer)
        self.assertTrue(all(pointer.Visible == 0 for pointer in pointers))

    def test_cursor_layer_publishes_once_and_batches_native_visibility(self):
        pictures, visibility = [], []
        class Range:
            def __setattr__(self, name, value):
                visibility.append(value)
        shape = SimpleNamespace(Name='', Line=SimpleNamespace(Visible=0), Visible=0,
                                Fill=SimpleNamespace(UserPicture=pictures.append))
        slide = SimpleNamespace(Shapes=SimpleNamespace(
            AddShape=lambda *args: shape,
            Range=lambda names: Range()))
        overlay = playback.CursorOverlay(slide, 400, 300, playback.COLORS)
        try:
            for index, pointer in enumerate(overlay.pointers):
                pointer.Left, pointer.Top, pointer.Visible = index * 20, 20, -1
                overlay.show(index + 1)
            overlay.publish()
            self.assertEqual(len(pictures), 1)
            self.assertEqual(visibility, [-1])
            overlay.publish()
            self.assertEqual(len(pictures), 1)
            from PIL import Image
            sample = (round(2 * overlay.scale), round(28 * overlay.scale))
            with Image.open(pictures[0]) as image:
                self.assertGreater(image.getpixel(sample)[3], 0)
            overlay.pointers[0].Visible = 0
            overlay.publish()
            with Image.open(pictures[-1]) as image:
                self.assertEqual(image.getpixel(sample)[3], 0)
        finally:
            overlay.close()

    def test_numbered_badge_fits_at_edge_and_trail_exits_with_pointer(self):
        shape = SimpleNamespace(Name='', Line=SimpleNamespace(Visible=0), Visible=0,
                                Fill=SimpleNamespace(UserPicture=lambda path: None))
        slide = SimpleNamespace(Shapes=SimpleNamespace(
            AddShape=lambda *args: shape,
            Range=lambda names: None))
        with patch('cursor_overlay.time.perf_counter', side_effect=(0.0, 0.02, 0.06, 0.09)):
            overlay = playback.CursorOverlay(slide, 400, 300, playback.COLORS[:1])
            try:
                pointer = overlay.pointers[0]
                pointer.Left, pointer.Top, pointer.Visible = 383, 279, -1
                overlay.publish()
                # At the bottom right the full numbered badge must sit above and left.
                x, y = overlay.last_snapshot[0][0]
                left, top, _, _ = overlay.image.getbbox()
                self.assertLess(left, x - overlay.badges[0].width)
                self.assertLess(top, y - overlay.badges[0].height)
                pointer.Left = 315
                overlay.publish()
                self.assertTrue(overlay.last_snapshot[0][1])
                pointer.Visible = 0
                overlay.publish()
                self.assertIsNone(overlay.image.getbbox())
                self.assertFalse(overlay.histories[0])
            finally:
                overlay.close()

    def test_text_box_and_text_bearing_frame_are_distinguished(self):
        deck = Presentation()
        slide = deck.slides.add_slide(deck.slide_layouts[6])
        label = slide.shapes.add_textbox(0, 0, Inches(2), Inches(1))
        label.text = 'Plain text'
        frame = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                                       0, 0, Inches(2), Inches(1))
        frame.text = 'Text on a frame'
        ring = slide.shapes.add_shape(MSO_SHAPE.DONUT,
                                      0, 0, Inches(1), Inches(1))
        self.assertFalse(playback.is_frame_shape(label))
        self.assertTrue(playback.is_frame_shape(frame))
        self.assertFalse(playback.is_frame_shape(ring))
        label.fill.solid()
        self.assertTrue(playback.is_frame_shape(label))

    def test_rectangle_freeform_is_recognized(self):
        deck = Presentation()
        slide = deck.slides.add_slide(deck.slide_layouts[6])
        drawing = slide.shapes.build_freeform(0, 0)
        drawing.add_line_segments([(100, 0), (100, 50), (0, 50)], close=True)
        frame = drawing.convert_to_shape()
        self.assertTrue(playback.is_frame_shape(frame))

    def test_group_is_hidden_as_one_editable_object(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            deck = Presentation()
            slide = deck.slides.add_slide(deck.slide_layouts[6])
            group = slide.shapes.add_group_shape()
            group.shapes.add_shape(MSO_SHAPE.OVAL, 0, 0, Inches(1), Inches(1))
            deck.save(root / 'source.pptx')
            self.assertEqual(prepare(root / 'source.pptx', root / 'hidden.pptx'), 1)
            hidden = Presentation(root / 'hidden.pptx').slides[0].shapes[0]
            self.assertEqual(hidden._element[0][0].get('hidden'), '1')
            self.assertEqual(len(hidden.shapes), 1)

    def test_graphic_visibly_grows_before_native_content_appears(self):
        class Box:
            def __init__(self):
                self.widths = []
            def __setattr__(self, name, value):
                if name == 'Width':
                    self.widths.append(value)
                object.__setattr__(self, name, value)

        source = SimpleNamespace(Id=10, Visible=0, Width=90, Height=60)
        pointers = [SimpleNamespace(Left=0, Top=0, Visible=0) for _ in playback.COLORS]
        bubbles = [SimpleNamespace(Visible=0, TextFrame=SimpleNamespace(
            TextRange=SimpleNamespace(Text=''))) for _ in playback.COLORS]
        boxes = [Box() for _ in playback.COLORS]
        prepared = playback.PreparedPage({}, {10: source}, {10: (10, 10, 90, 60, 1, '')},
                                         {}, set(), pointers, bubbles, boxes, {10})
        metrics = {}
        states = []
        for _ in playback.page_stream(prepared, 200, 150, [], metrics):
            states.append(source.Visible)
        self.assertEqual(metrics['graphic_drag_frames'], 8)
        self.assertEqual(metrics['dragged_graphics'], 1)
        owner = next(index for index, part in enumerate(playback.split_path_sequence([10])) if part)
        self.assertEqual(boxes[owner].widths[-1], 90)
        self.assertEqual(boxes[owner].widths, sorted(boxes[owner].widths))
        self.assertEqual(metrics['partition_count'], 12)
        self.assertEqual(sum(metrics['partition_sizes']), 1)
        self.assertEqual(metrics['partition_sizes'][owner], 1)
        self.assertTrue(all(value == 0 for value in states[:8]))
        self.assertEqual(source.Visible, -1)
        self.assertEqual((source.Width, source.Height), (90, 60))


if __name__ == '__main__':
    unittest.main()
