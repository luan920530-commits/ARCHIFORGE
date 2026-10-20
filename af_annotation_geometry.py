# -*- coding: utf-8 -*-

# ╔══════════════════════════════════════════════════════════╗
# ║        ARCHIFORGE — af_annotation_geometry.py           ║
# ║        Geometría pura de cotas, ejes y norte            ║
# ║        GPL v3 — ArchiForge Devs                         ║
# ╚══════════════════════════════════════════════════════════╝

# <pep8 compliant>

"""Pure geometry for ArchiForge plan annotations (no ``bpy``).

Everything works on plain ``(x, y, z)`` tuples in the horizontal plane
and returns *polylines* (lists of points) plus *labels* (text, position,
rotation), which ``af_annotation.py`` turns into curve and text objects:

* :func:`dimension_line` — architectural dimension between two points
  with extension lines, 45° ticks and the length label.
* :func:`grid_axes` — structural axes (numbers along X, letters along Y)
  with end bubbles.
* :func:`north_arrow` — north symbol polygon with its "N" label.

Covered by ``tests/test_annotation_geometry.py``.
"""

import math
import string

try:
    from . import af_units
except ImportError:  # pragma: no cover - imported outside the package
    import af_units

TICK_ANGLE = math.radians(45.0)


# ════════════════════════════════════════════════════════════
#  Small vector helpers (tuples only)
# ════════════════════════════════════════════════════════════
def _p3(point):
    x, y = float(point[0]), float(point[1])
    z = float(point[2]) if len(point) > 2 else 0.0
    return (x, y, z)


def _add(a, b, scale=1.0):
    return (a[0] + b[0] * scale, a[1] + b[1] * scale, a[2] + b[2] * scale)


def _direction(p0, p1):
    """Unit XY direction from ``p0`` to ``p1`` and the planar length."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    length = math.hypot(dx, dy)
    if length < 1e-9:
        return (1.0, 0.0, 0.0), 0.0
    return (dx / length, dy / length, 0.0), length


def _left_normal(direction):
    return (-direction[1], direction[0], 0.0)


def circle_points(center, radius, segments=32):
    """Closed circle polyline (first point not repeated) in the XY plane."""
    center = _p3(center)
    segments = max(8, int(segments))
    return [
        (center[0] + radius * math.cos(2.0 * math.pi * i / segments),
         center[1] + radius * math.sin(2.0 * math.pi * i / segments),
         center[2])
        for i in range(segments)
    ]


# ════════════════════════════════════════════════════════════
#  Labels
# ════════════════════════════════════════════════════════════
def format_dimension(meters, unit_system=af_units.METRIC, decimals=2):
    """Length label: ``3.25 m`` or feet-inches (``10' 8"``)."""
    system = af_units.normalize(unit_system)
    if system == af_units.IMPERIAL:
        return af_units.feet_and_inches(meters)
    return "{:.{d}f} m".format(float(meters), d=max(0, int(decimals)))


def axis_letters(count):
    """``A, B, ..., Z, AA, AB, ...`` — structural axis names along Y."""
    letters = []
    alphabet = string.ascii_uppercase
    for index in range(max(0, int(count))):
        name = ""
        n = index
        while True:
            name = alphabet[n % 26] + name
            n = n // 26 - 1
            if n < 0:
                break
        letters.append(name)
    return letters


def readable_angle(angle):
    """Rotate text by ``angle`` (radians) but keep it readable from below/right.

    Plan text should never be upside down: angles pointing into the left
    half-plane are flipped by 180°.
    """
    angle = math.atan2(math.sin(angle), math.cos(angle))
    if angle > math.pi / 2.0 + 1e-9 or angle <= -math.pi / 2.0 + 1e-9:
        angle += math.pi
    return math.atan2(math.sin(angle), math.cos(angle))


# ════════════════════════════════════════════════════════════
#  Dimension line
# ════════════════════════════════════════════════════════════
def dimension_line(p0, p1, offset=0.5, tick=0.08, extension=0.05,
                   text_gap=0.06, unit_system=af_units.METRIC, decimals=2):
    """Architectural dimension between ``p0`` and ``p1``.

    ``offset`` moves the dimension line to the left of the p0→p1
    direction (negative values: to the right). Returns::

        {"polylines": [[(x, y, z), ...], ...],   # dimension line,
                                                  # extension lines, ticks
         "label": {"text": "3.00 m", "position": (x, y, z),
                   "rotation": radians},
         "length": metres, "start": p0, "end": p1}
    """
    p0, p1 = _p3(p0), _p3(p1)
    direction, length = _direction(p0, p1)
    if length < 1e-9:
        raise ValueError("Dimension points coincide")
    normal = _left_normal(direction)
    sign = 1.0 if offset >= 0.0 else -1.0
    distance = abs(float(offset))

    a = _add(p0, normal, sign * distance)
    b = _add(p1, normal, sign * distance)
    overshoot = max(0.0, float(extension))
    polylines = [
        [a, b],                                               # dimension line
        [p0, _add(a, normal, sign * overshoot)],              # extension p0
        [p1, _add(b, normal, sign * overshoot)],              # extension p1
    ]
    half = max(0.0, float(tick)) / 2.0
    if half > 0.0:
        # 45° ticks crossing the dimension line at both ends
        tick_dir = (
            (direction[0] + normal[0]) / math.sqrt(2.0),
            (direction[1] + normal[1]) / math.sqrt(2.0),
            0.0,
        )
        for end in (a, b):
            polylines.append([_add(end, tick_dir, -half),
                              _add(end, tick_dir, half)])

    mid = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0, a[2])
    angle = math.atan2(direction[1], direction[0])
    text_angle = readable_angle(angle)
    # Label sits on the side away from the measured object.
    text_normal = (-math.sin(text_angle), math.cos(text_angle), 0.0)
    text_side = 1.0 if (text_normal[0] * normal[0] + text_normal[1] * normal[1]) * sign >= 0 else -1.0
    position = _add(mid, text_normal, text_side * max(0.0, float(text_gap)))
    return {
        "polylines": polylines,
        "label": {"text": format_dimension(length, unit_system, decimals),
                  "position": position, "rotation": text_angle},
        "length": length,
        "start": p0,
        "end": p1,
    }


def footprint_dimensions(bounds_min, bounds_max, offset=0.5, z=None,
                         unit_system=af_units.METRIC, **kwargs):
    """Width (along X, below) and depth (along Y, right) of a footprint.

    ``bounds_min``/``bounds_max`` are world-space bounding-box corners.
    Returns a list of :func:`dimension_line` results (one or two; a
    degenerate axis is skipped).
    """
    x0, y0 = float(bounds_min[0]), float(bounds_min[1])
    x1, y1 = float(bounds_max[0]), float(bounds_max[1])
    level = float(bounds_min[2]) if z is None else float(z)
    results = []
    if x1 - x0 > 1e-6:
        # Along +X at the bottom edge; the left normal of +X is +Y, so a
        # negative offset places the line below (−Y).
        results.append(dimension_line((x0, y0, level), (x1, y0, level),
                                      offset=-abs(offset),
                                      unit_system=unit_system, **kwargs))
    if y1 - y0 > 1e-6:
        # Along +Y at the right edge; left normal of +Y is −X, so negative
        # offset places the line to the right (+X).
        results.append(dimension_line((x1, y0, level), (x1, y1, level),
                                      offset=-abs(offset),
                                      unit_system=unit_system, **kwargs))
    return results


# ════════════════════════════════════════════════════════════
#  Structural grid axes
# ════════════════════════════════════════════════════════════
def grid_axes(x_positions, y_positions, origin=(0.0, 0.0, 0.0),
              extension=1.0, bubble_radius=0.25, both_ends=False):
    """Axis lines with bubbles for a structural grid.

    ``x_positions`` are offsets along X (axes drawn parallel to Y and
    numbered 1, 2, 3…); ``y_positions`` are offsets along Y (axes parallel
    to X, lettered A, B, C…). Lines overshoot the grid by ``extension`` and
    end in a bubble whose centre is one radius beyond the line end.

    Returns ``{"axes": [{"name", "line": [p, q], "bubbles": [centre, ...]}],
    "bubble_radius": r}``.
    """
    xs = sorted(float(v) for v in x_positions)
    ys = sorted(float(v) for v in y_positions)
    if not xs or not ys:
        raise ValueError("Grid axes need at least one position per direction")
    ox, oy, oz = _p3(origin)
    ext = max(0.0, float(extension))
    radius = max(0.01, float(bubble_radius))
    axes = []
    y_lo, y_hi = oy + ys[0] - ext, oy + ys[-1] + ext
    for index, x in enumerate(xs, start=1):
        wx = ox + x
        line = [(wx, y_lo, oz), (wx, y_hi, oz)]
        bubbles = [(wx, y_hi + radius, oz)]
        if both_ends:
            bubbles.append((wx, y_lo - radius, oz))
        axes.append({"name": str(index), "line": line, "bubbles": bubbles})
    x_lo, x_hi = ox + xs[0] - ext, ox + xs[-1] + ext
    for letter, y in zip(axis_letters(len(ys)), ys):
        wy = oy + y
        line = [(x_lo, wy, oz), (x_hi, wy, oz)]
        bubbles = [(x_lo - radius, wy, oz)]
        if both_ends:
            bubbles.append((x_hi + radius, wy, oz))
        axes.append({"name": letter, "line": line, "bubbles": bubbles})
    return {"axes": axes, "bubble_radius": radius}


def regular_positions(count, spacing):
    """``[0, s, 2s, ...]`` for ``count`` axes."""
    count = max(1, int(count))
    spacing = max(0.0, float(spacing))
    return [i * spacing for i in range(count)]


# ════════════════════════════════════════════════════════════
#  North arrow
# ════════════════════════════════════════════════════════════
def north_arrow(center=(0.0, 0.0, 0.0), size=1.0, angle=0.0):
    """North symbol: an arrow head pointing to north plus a ring.

    ``angle`` (radians) rotates north counter-clockwise from +Y. Returns
    ``{"polylines": [...], "label": {"text": "N", "position", "rotation"}}``.
    """
    cx, cy, cz = _p3(center)
    size = max(0.05, float(size))
    cos_a, sin_a = math.cos(angle), math.sin(angle)

    def rot(x, y):
        return (cx + x * cos_a - y * sin_a, cy + x * sin_a + y * cos_a, cz)

    half = size * 0.18
    tip = size * 0.5
    tail = -size * 0.35
    arrow = [rot(0.0, tip), rot(-half, tail), rot(0.0, tail * 0.55),
             rot(half, tail), rot(0.0, tip)]
    ring = circle_points((cx, cy, cz), size * 0.5, 48)
    ring.append(ring[0])
    label_pos = rot(0.0, tip + size * 0.18)
    return {
        "polylines": [arrow, ring],
        "label": {"text": "N", "position": label_pos,
                  "rotation": readable_angle(angle)},
    }
