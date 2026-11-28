"""Read drawable PowerPoint contours for the temporary path-tracing preview."""

from bisect import bisect_right
import math

from pptx import Presentation
from pptx.oxml.ns import qn
from pptx.util import Pt


def contour_prefix(points, offsets, distance):
    """Sample one continuous contour, keeping its partial stroke separate."""
    distance = max(0.0, min(distance, offsets[-1]))
    end = bisect_right(offsets, distance)
    prefix = points[:end]
    tip = prefix[-1]
    if end < len(points) and distance > offsets[end - 1]:
        ratio = (distance - offsets[end - 1]) / (offsets[end] - offsets[end - 1])
        tip = tuple(a + (b - a) * ratio for a, b in zip(tip, points[end]))
        prefix += (tip,)
    return tip, prefix


class PathTrace:
    def __init__(self, contours):
        outlines, distances, ends = [], [], []
        total = 0.0
        for contour in contours:
            if not contour:
                continue
            points, cumulative = [contour[0]], [0.0]
            for point in contour[1:]:
                length = math.dist(points[-1], point)
                if length > 1e-6:
                    points.append(point)
                    cumulative.append(cumulative[-1] + length)
            if len(points) > 1:
                outlines.append(tuple(points))
                distances.append(tuple(cumulative))
                total += cumulative[-1]
                ends.append(total)
        if not outlines:
            raise ValueError("Path has no drawable contour")
        self.outlines = tuple(outlines)
        self.distances = tuple(distances)
        self.ends = tuple(ends)
        self.length = total
        xs = [x for contour in outlines for x, _ in contour]
        ys = [y for contour in outlines for _, y in contour]
        self.bounds = (min(xs), min(ys), max(xs), max(ys))

    def at(self, fraction):
        """Return the tip and a separate polyline for each traversed contour."""
        distance = min(1.0, max(0.0, fraction)) * self.length
        index = min(bisect_right(self.ends, distance), len(self.ends) - 1)
        local = distance - (self.ends[index - 1] if index else 0.0)
        tip, prefix = contour_prefix(self.outlines[index], self.distances[index], local)
        return tip, self.outlines[:index] + (prefix,)


def _shape_coordinates(shape, transform, grid_width, grid_height):
    left, top, width, height = (float(value) / Pt(1) for value in
                                (shape.left, shape.top, shape.width, shape.height))
    radians = math.radians(float(transform.get("rot", "0")) / 60000)
    cosine, sine = math.cos(radians), math.sin(radians)
    horizontal = -1 if transform.get("flipH") in ("1", "true") else 1
    vertical = -1 if transform.get("flipV") in ("1", "true") else 1
    center_x, center_y = left + width / 2, top + height / 2

    def map_point(x, y):
        dx = (x / grid_width - 0.5) * width * horizontal
        dy = (y / grid_height - 0.5) * height * vertical
        return center_x + dx * cosine - dy * sine, center_y + dx * sine + dy * cosine

    return map_point


def _cubic_samples(start, a, b, end):
    length = math.dist(start, a) + math.dist(a, b) + math.dist(b, end)
    count = max(2, min(48, math.ceil(length / 6)))
    for step in range(1, count):
        t = step / count
        u = 1 - t
        yield tuple(u**3 * p0 + 3 * u**2 * t * p1 + 3 * u * t**2 * p2 + t**3 * p3
                    for p0, p1, p2, p3 in zip(start, a, b, end))
    yield end


def _read_contours(path, map_point):
    points = []
    for command in path:
        kind = command.tag.rsplit("}", 1)[-1]
        coordinates = [map_point(float(p.get("x")), float(p.get("y")))
                       for p in command.findall(qn("a:pt"))]
        if kind == "moveTo" and len(coordinates) == 1:
            if points:
                yield points
            points = coordinates
        elif kind == "lnTo" and points and len(coordinates) == 1:
            points.extend(coordinates)
        elif kind == "cubicBezTo" and points and len(coordinates) == 3:
            points.extend(_cubic_samples(points[-1], *coordinates))
        elif kind == "quadBezTo" and points and len(coordinates) == 2:
            start = points[-1]
            control, end = coordinates
            first = tuple(a + (b - a) * 2 / 3 for a, b in zip(start, control))
            second = tuple(a + (b - a) * 2 / 3 for a, b in zip(end, control))
            points.extend(_cubic_samples(start, first, second, end))
        elif kind == "close" and points:
            points.append(points[0])
        else:
            raise ValueError(f"Unsupported DrawingML path command {kind}")
    if points:
        yield points


def _preset_contour(preset):
    if preset == "rect":
        return ((0, 0), (1, 0), (1, 1), (0, 1), (0, 0))
    if preset in ("line", "straightConnector1"):
        return ((0, 0), (1, 1))
    if preset == "ellipse":
        return tuple((0.5 + 0.5 * math.cos(math.tau * step / 96),
                      0.5 + 0.5 * math.sin(math.tau * step / 96))
                     for step in range(97))
    return ()


def drawable_trace(shape):
    properties = shape._element.find(qn("p:spPr"))
    if properties is None:
        return None
    transform = properties.find(qn("a:xfrm"))
    if transform is None:
        return None
    try:
        geometry = properties.find(qn("a:custGeom"))
        if geometry is None:
            preset = properties.find(qn("a:prstGeom"))
            contour = _preset_contour(preset.get("prst")) if preset is not None else ()
            mapping = _shape_coordinates(shape, transform, 1.0, 1.0)
            return PathTrace([tuple(mapping(x, y) for x, y in contour)]) if contour else None
        paths = geometry.find(qn("a:pathLst"))
        if paths is None:
            return None
        contours = []
        for path in paths.findall(qn("a:path")):
            if path.get("fill") == "none" and path.get("stroke") in ("0", "false"):
                continue
            grid_width = float(path.get("w", 0)) or float(shape.width) or 1.0
            grid_height = float(path.get("h", 0)) or float(shape.height) or 1.0
            mapping = _shape_coordinates(shape, transform, grid_width, grid_height)
            contours.extend(_read_contours(path, mapping))
        return PathTrace(contours)
    except (TypeError, ValueError, OverflowError):
        return None


def load_traces(deck):
    """Load source geometry before the COM-driven preview starts."""
    return {str(slide.slide_id): {shape.shape_id: trace for shape in slide.shapes
                                 if (trace := drawable_trace(shape)) is not None}
            for slide in Presentation(deck).slides}
