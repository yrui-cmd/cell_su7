"""Render temporary reconstruction controls through one PowerPoint picture fill."""
import math
import os
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

from PIL import Image, ImageDraw, ImageFont


class CursorOverlay:
    def __init__(self, slide, width, height, colors):
        self.width, self.height = width, height
        self.colors = colors
        self.scale = min(2, 1280 / width)
        self.image = Image.new('RGBA', (round(width * self.scale), round(height * self.scale)))
        self.directory = tempfile.TemporaryDirectory(prefix='cell-ppt-cursors-')
        self.frame = 0
        self.pending_visibility = {}
        self.last_snapshot = None
        self.last_time = time.perf_counter()
        self.positions = [None] * len(colors)
        self.pointers = [SimpleNamespace(Left=0, Top=0, Visible=0) for _ in colors]
        self.boxes = [SimpleNamespace(Left=0, Top=0, Width=1, Height=1, Visible=0) for _ in colors]
        self.bubbles = [SimpleNamespace(Left=0, Top=0, Visible=0,
            TextFrame=SimpleNamespace(TextRange=SimpleNamespace(Text=''))) for _ in colors]
        font_path = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts/msyh.ttc'
        self.font = (ImageFont.truetype(str(font_path), max(10, round(13 * self.scale)))
                     if font_path.exists() else ImageFont.load_default())
        self.shape = slide.Shapes.AddShape(1, 0, 0, width, height)
        self.shape.Name = 'SwarmCursorOverlay'
        self.shape.Line.Visible = 0
        self.shape.Visible = 0
        self.set_picture = self.shape.Fill.UserPicture
        self.shape_range = slide.Shapes.Range

    def show(self, name, visible=True):
        self.pending_visibility[name] = visible

    def publish(self):
        for visible in (False, True):
            names = tuple(name for name, value in self.pending_visibility.items() if value == visible)
            if names:
                self.shape_range(names).Visible = -1 if visible else 0
        self.pending_visibility.clear()
        now = time.perf_counter()
        follow = 1 - math.exp(-min(0.2, now - self.last_time) / 0.025)
        self.last_time = now
        snapshot = []
        for index, pointer in enumerate(self.pointers):
            target = (pointer.Left, pointer.Top)
            previous = self.positions[index]
            if previous is None or not pointer.Visible:
                position = target
            else:
                position = tuple(old + (new - old) * follow for old, new in zip(previous, target))
            self.positions[index] = position
            box, bubble = self.boxes[index], self.bubbles[index]
            snapshot.append((round(position[0], 2), round(position[1], 2), pointer.Visible,
                             box.Left, box.Top, box.Width, box.Height, box.Visible,
                             bubble.Left, bubble.Top, bubble.Visible, bubble.TextFrame.TextRange.Text))
        if snapshot == self.last_snapshot:
            return
        self.last_snapshot = snapshot
        self.image.paste((0, 0, 0, 0), (0, 0, *self.image.size))
        draw = ImageDraw.Draw(self.image)
        scale = self.scale
        for index, (pointer, box, bubble) in enumerate(zip(self.pointers, self.boxes, self.bubbles)):
            color = '#' + self.colors[index]
            if box.Visible:
                bounds = tuple(value * scale for value in
                               (box.Left, box.Top, box.Left + box.Width, box.Top + box.Height))
                draw.rectangle(bounds, fill=tuple(bytes.fromhex(self.colors[index])) + (18,),
                               outline=color, width=max(1, round(scale)))
            if bubble.Visible:
                x, y = bubble.Left * scale, bubble.Top * scale
                draw.rectangle((x, y, x + 88 * scale, y + 22 * scale),
                               fill='white', outline=color, width=max(1, round(scale)))
                draw.text((x + 3 * scale, y), bubble.TextFrame.TextRange.Text,
                          font=self.font, fill=color)
            if pointer.Visible:
                x, y = self.positions[index]
                points = [((x + dx) * scale, (y + dy) * scale) for dx, dy in
                          [(0, 0), (0, 17), (4, 13), (8, 21), (12, 19), (8, 11), (16, 11)]]
                draw.polygon(points, fill=color, outline='white', width=max(1, round(scale)))
        path = Path(self.directory.name) / f'frame-{self.frame:06d}.png'
        self.image.save(path, compress_level=1)
        self.set_picture(str(path))
        if self.frame == 0:
            self.shape.Visible = -1
        self.frame += 1

    def close(self):
        self.directory.cleanup()
