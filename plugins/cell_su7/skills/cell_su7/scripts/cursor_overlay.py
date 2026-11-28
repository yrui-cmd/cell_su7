"""Render temporary reconstruction controls through one PowerPoint picture fill."""
import math
import os
import tempfile
import time
from collections import deque
from pathlib import Path
from types import SimpleNamespace

from PIL import Image, ImageDraw, ImageFont


class CursorOverlay:
    TRAIL_SECONDS = 0.18
    ARROW = ((0, 0), (0, 17), (4, 13), (8, 21), (12, 19), (8, 11), (16, 11))
    HINT_SIZE = (88, 22)

    def __init__(self, slide, width, height, colors, *, trace_mode=False):
        self.width, self.height = width, height
        self.colors = [tuple(bytes.fromhex(color)) for color in colors]
        self.scale = min(2, 1280 / width)
        self.trace_mode = trace_mode
        self.image = Image.new('RGBA', (round(width * self.scale), round(height * self.scale)))
        self.directory = tempfile.TemporaryDirectory(prefix='cell-ppt-cursors-')
        self.frame = 0
        self.pending_visibility = {}
        self.last_snapshot = None
        self.last_time = time.perf_counter()
        self.positions = [None] * len(colors)
        self.histories = [deque(maxlen=5) for _ in colors]
        self.trace_paths = [()] * len(colors)
        self.pointers = [SimpleNamespace(Left=0, Top=0, Visible=0) for _ in colors]
        self.boxes = [SimpleNamespace(Left=0, Top=0, Width=1, Height=1, Visible=0) for _ in colors]
        self.bubbles = [SimpleNamespace(Left=0, Top=0, Visible=0,
            TextFrame=SimpleNamespace(TextRange=SimpleNamespace(Text=''))) for _ in colors]
        fonts = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts'
        font_path = fonts / 'msyh.ttc'
        self.font = (ImageFont.truetype(str(font_path), max(10, round(13 * self.scale)))
                     if font_path.exists() else ImageFont.load_default())
        label_path = fonts / 'arialbd.ttf'
        label_size = max(6, round(9.8 * self.scale * 3))
        label_font = (ImageFont.truetype(str(label_path), label_size)
                      if label_path.exists() else ImageFont.load_default(size=label_size))
        self.arrows = [self.arrow_sprite(color) for color in self.colors]
        if trace_mode:
            self.edge_arrows = [(arrow, arrow.transpose(Image.Transpose.FLIP_LEFT_RIGHT),
                                 arrow.transpose(Image.Transpose.FLIP_TOP_BOTTOM),
                                 arrow.transpose(Image.Transpose.ROTATE_180))
                                for arrow in self.arrows]
        self.badges = [self.badge_sprite(f'DRAW {i + 1:02d}', color, label_font)
                       for i, color in enumerate(self.colors)]
        self.shape = slide.Shapes.AddShape(1, 0, 0, width, height)
        self.shape.Name = 'SwarmCursorOverlay'
        self.shape.Line.Visible = 0
        self.shape.Visible = 0
        self.set_picture = self.shape.Fill.UserPicture
        self.shape_range = slide.Shapes.Range

    def show(self, name, visible=True):
        self.pending_visibility[name] = visible

    def arrow_sprite(self, color):
        scale = self.scale * 3
        size = (round(19 * scale), round(24 * scale))
        sprite = Image.new('RGBA', size)
        draw = ImageDraw.Draw(sprite)
        shadow = [((x + 1.1) * scale, (y + 1.4) * scale) for x, y in self.ARROW]
        draw.polygon(shadow, fill=(18, 29, 44, 78))
        points = [(x * scale, y * scale) for x, y in self.ARROW]
        draw.polygon(points, fill=color + (255,), outline='white', width=max(1, round(scale)))
        return sprite.resize((round(19 * self.scale), round(24 * self.scale)),
                             Image.Resampling.LANCZOS)

    def badge_sprite(self, text, color, font):
        width, height = round(51 * self.scale), round(15 * self.scale)
        sprite = Image.new('RGBA', (width * 3, height * 3))
        draw = ImageDraw.Draw(sprite)
        tint = tuple(round(channel * 0.76 + 255 * 0.24) for channel in color)
        draw.rounded_rectangle((0, 0, sprite.width - 1, sprite.height - 1),
                               radius=max(1, round(4 * self.scale)), fill=tint + (244,))
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        draw.text(((sprite.width - (right - left)) / 2 - left,
                   (sprite.height - (bottom - top)) / 2 - top),
                  text, font=font, fill=(18, 29, 44, 255))
        return sprite.resize((width, height), Image.Resampling.LANCZOS)

    def draw_selection(self, draw, bounds, color):
        left, top, right, bottom = (round(value * self.scale) for value in bounds)
        draw.rectangle((left, top, right, bottom), fill=color + (11,))
        dash = max(2, round(3.5 * self.scale))
        gap = max(2, round(2.5 * self.scale))
        stroke = max(1, round(self.scale * 0.8))
        edge = color + (180,)
        for start in range(left, right + 1, dash + gap):
            for y in (top, bottom):
                draw.line((start, y, min(right, start + dash), y), fill=edge, width=stroke)
        for start in range(top, bottom + 1, dash + gap):
            for x in (left, right):
                draw.line((x, start, x, min(bottom, start + dash)), fill=edge, width=stroke)
        handle = max(1, round(1.5 * self.scale))
        for x, y in ((left, top), (right, top), (left, bottom), (right, bottom)):
            draw.rectangle((x - handle, y - handle, x + handle, y + handle),
                           fill=color + (230,), outline=(255, 255, 255, 230))

    def pointer_visual(self, index, now, follow):
        pointer = self.pointers[index]
        history = self.histories[index]
        if not pointer.Visible:
            self.positions[index] = None
            history.clear()
            return None, ()
        target = (pointer.Left, pointer.Top)
        if self.trace_mode:
            x, y = (round(value * self.scale) for value in target)
            # A path may continue beyond the slide. Its tip returns when it re-enters.
            if not (0 <= x <= self.image.width and 0 <= y <= self.image.height):
                return None, ()
            return (min(x, self.image.width - 1), min(y, self.image.height - 1)), ()
        previous = self.positions[index]
        if previous is None or self.boxes[index].Visible:
            # The drag worker already eases the corner. Keep its arrow on the handle.
            position = target
        else:
            position = tuple(old + (new - old) * follow for old, new in zip(previous, target))
        self.positions[index] = position
        point = tuple(round(value * self.scale) for value in position)
        if previous is not None:
            old_point = tuple(round(value * self.scale) for value in previous)
            if point != old_point:
                history.append((self.last_time, old_point))
        while history and now - history[0][0] >= self.TRAIL_SECONDS:
            history.popleft()
        segments = []
        end = point
        length_left = 32 * self.scale
        for moment, start in reversed(history):
            distance = math.dist(start, end)
            if distance == 0:
                continue
            amount = min(1, length_left / distance)
            clipped = tuple(round(b + (a - b) * amount) for a, b in zip(start, end))
            opacity = round(104 * (1 - (now - moment) / self.TRAIL_SECONDS))
            segments.append((clipped, end, opacity))
            if distance >= length_left:
                break
            length_left -= distance
            end = start
        return point, tuple(reversed(segments))

    def draw_badge(self, index, x, y, hint):
        badge = self.badges[index]
        left, top = x + round(15 * self.scale), y + round(15 * self.scale)
        if left + badge.width > self.image.width:
            left = x - badge.width - round(4 * self.scale)
        if top + badge.height > self.image.height:
            top = y - badge.height - round(3 * self.scale)
        left = max(0, min(self.image.width - badge.width, left))
        top = max(0, min(self.image.height - badge.height, top))
        if hint is not None:
            hint_left, hint_top = (round(value * self.scale) for value in hint[:2])
            hint_right = hint_left + round(self.HINT_SIZE[0] * self.scale)
            hint_bottom = hint_top + round(self.HINT_SIZE[1] * self.scale)
            if (left < hint_right and left + badge.width > hint_left
                    and top < hint_bottom and top + badge.height > hint_top):
                gap = max(2, round(2 * self.scale))
                below = hint_bottom + gap
                above = hint_top - badge.height - gap
                top = below if below + badge.height <= self.image.height else max(0, above)
        self.image.alpha_composite(badge, (left, top))

    def draw_arrow(self, index, point):
        sprite = self.arrows[index]
        x, y = point
        if self.trace_mode:
            flip_x = x + sprite.width > self.image.width
            flip_y = y + sprite.height > self.image.height
            sprite = self.edge_arrows[index][int(flip_x) + 2 * int(flip_y)]
            x -= sprite.width - 1 if flip_x else 0
            y -= sprite.height - 1 if flip_y else 0
        self.image.alpha_composite(sprite, (x, y))

    def publish(self):
        for visible in (False, True):
            names = tuple(name for name, value in self.pending_visibility.items() if value == visible)
            if names:
                self.shape_range(names).Visible = -1 if visible else 0
        self.pending_visibility.clear()
        now = time.perf_counter()
        follow = 1 - math.exp(-min(0.2, now - self.last_time) / 0.025)
        snapshot = []
        for index in range(len(self.pointers)):
            point, trail = self.pointer_visual(index, now, follow)
            box, bubble = self.boxes[index], self.bubbles[index]
            selection = None
            hint = None
            if point is not None:
                if box.Visible:
                    selection = (box.Left, box.Top, box.Left + box.Width, box.Top + box.Height)
                if bubble.Visible:
                    hint = (bubble.Left, bubble.Top, bubble.TextFrame.TextRange.Text)
            outline = self.trace_paths[index] if self.pointers[index].Visible else ()
            snapshot.append((point, trail, selection, hint, outline))
        self.last_time = now
        if snapshot == self.last_snapshot:
            return
        self.image.paste((0, 0, 0, 0), (0, 0, *self.image.size))
        draw = ImageDraw.Draw(self.image)
        scale = self.scale
        for index, (_, trail, selection, hint, outline) in enumerate(snapshot):
            color = self.colors[index]
            if selection is not None:
                self.draw_selection(draw, selection, color)
            for start, end, opacity in trail:
                draw.line((start, end), fill=color + (opacity,), width=max(1, round(scale * 1.4)))
            for contour in outline:
                coordinates = [(x * scale, y * scale) for x, y in contour]
                if len(coordinates) > 1:
                    draw.line(coordinates, fill=color + (225,), width=max(1, round(scale * 1.4)),
                              joint='curve')
                else:
                    draw.point(coordinates[0], fill=color + (245,))
            if hint is not None:
                x, y, caption = hint
                x, y = x * scale, y * scale
                draw.rectangle((x, y, x + self.HINT_SIZE[0] * scale, y + self.HINT_SIZE[1] * scale),
                               fill='white', outline=color, width=max(1, round(scale)))
                draw.text((x + 3 * scale, y), caption, font=self.font, fill=color)
        for index, (point, _, _, hint, _) in enumerate(snapshot):
            if point is not None:
                self.draw_badge(index, *point, hint)
        for index, (point, _, _, _, _) in enumerate(snapshot):
            if point is not None:
                self.draw_arrow(index, point)
        path = Path(self.directory.name) / f'frame-{self.frame:06d}.png'
        self.image.save(path, compress_level=1)
        self.set_picture(str(path))
        if self.frame == 0:
            self.shape.Visible = -1
        self.last_snapshot = snapshot
        self.frame += 1

    def close(self):
        self.directory.cleanup()
