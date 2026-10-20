#!/usr/bin/env python3
"""Regenerate ArchiForge's original Blender preview icons.

Developer utility only; Blender loads the generated PNGs and does not need
Pillow. Run with Pillow installed: ``python icons/generate_icons.py``.
"""

import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent
SIZE = 128
SCALE = 4
CANVAS = SIZE * SCALE

NAVY = "#142436"
BORDER = "#30485e"
ICE = "#e9f2f3"
TEAL = "#62d7c7"
GOLD = "#f4bb58"
CORAL = "#f1806b"
BLUE = "#6a9fdb"
MUTED = "#91a8b8"


def xy(x, y):
    return round(x * SCALE), round(y * SCALE)


def box(x1, y1, x2, y2):
    return (*xy(x1, y1), *xy(x2, y2))


def line(draw, points, color=ICE, width=6):
    pts = [xy(x, y) for x, y in points]
    stroke = max(1, round(width * SCALE))
    draw.line(pts, fill=color, width=stroke, joint="curve")
    radius = stroke // 2
    for x, y in (pts[0], pts[-1]):
        draw.ellipse((x - radius, y - radius, x + radius, y + radius),
                     fill=color)


def polygon(draw, points, fill=None, outline=None, width=4):
    pts = [xy(x, y) for x, y in points]
    if fill is not None:
        draw.polygon(pts, fill=fill)
    if outline is not None:
        line(draw, points + [points[0]], outline, width)


def circle(draw, cx, cy, radius, fill=None, outline=None, width=4):
    bounds = box(cx - radius, cy - radius, cx + radius, cy + radius)
    draw.ellipse(bounds, fill=fill, outline=outline,
                 width=max(1, round(width * SCALE)))


def rectangle(draw, x1, y1, x2, y2, fill=None, outline=ICE, width=5,
              radius=0):
    bounds = box(x1, y1, x2, y2)
    stroke = max(1, round(width * SCALE))
    if radius:
        draw.rounded_rectangle(bounds, radius=round(radius * SCALE),
                               fill=fill, outline=outline, width=stroke)
    else:
        draw.rectangle(bounds, fill=fill, outline=outline, width=stroke)


def draw_background(draw):
    draw.rounded_rectangle(
        box(5, 5, 123, 123),
        radius=round(25 * SCALE),
        fill=NAVY,
        outline=BORDER,
        width=2 * SCALE,
    )


def icon_archiforge(draw):
    # Architectural roofline and a crisp AF monogram.
    line(draw, [(25, 47), (64, 20), (103, 47)], GOLD, 7)
    line(draw, [(32, 47), (32, 52)], GOLD, 7)
    line(draw, [(96, 47), (96, 52)], GOLD, 7)
    # Stroke-built monogram keeps regeneration deterministic on every OS.
    line(draw, [(30, 96), (46, 54), (62, 96)], TEAL, 8)
    line(draw, [(37, 78), (55, 78)], TEAL, 6)
    line(draw, [(72, 96), (72, 54), (100, 54)], ICE, 8)
    line(draw, [(72, 73), (94, 73)], ICE, 6)
    line(draw, [(25, 105), (103, 105)], GOLD, 4)
    line(draw, [(38, 113), (90, 113)], TEAL, 3)


def icon_wall(draw):
    # Two wall runs meeting in plan, with visible wall thickness.
    polygon(draw, [(28, 94), (28, 34), (42, 34), (42, 80), (98, 80),
                  (98, 94)], fill=TEAL)
    polygon(draw, [(49, 67), (49, 48), (96, 48), (96, 62), (63, 62),
                  (63, 67)], fill=ICE)
    circle(draw, 35, 34, 5, fill=GOLD)


def icon_wall_draw(draw):
    line(draw, [(27, 94), (49, 54), (76, 75), (101, 34)], TEAL, 7)
    for x, y in [(27, 94), (49, 54), (76, 75), (101, 34)]:
        circle(draw, x, y, 6, fill=GOLD, outline=NAVY, width=2)


def icon_slab(draw):
    polygon(draw, [(24, 43), (64, 25), (104, 43), (64, 62)],
            fill="#285c6b", outline=TEAL, width=4)
    polygon(draw, [(24, 43), (64, 62), (64, 77), (24, 58)],
            fill="#1d4156", outline=TEAL, width=4)
    polygon(draw, [(64, 62), (104, 43), (104, 58), (64, 77)],
            fill="#234a60", outline=TEAL, width=4)
    line(draw, [(24, 69), (64, 88), (104, 69)], GOLD, 5)
    line(draw, [(24, 80), (64, 99), (104, 80)], ICE, 4)


def icon_roof(draw):
    line(draw, [(22, 62), (64, 28), (106, 62)], GOLD, 9)
    line(draw, [(33, 57), (33, 98), (95, 98), (95, 57)], TEAL, 6)
    line(draw, [(51, 98), (51, 72), (77, 72), (77, 98)], ICE, 5)
    line(draw, [(31, 67), (64, 40), (97, 67)], CORAL, 3)


def icon_truss(draw):
    line(draw, [(22, 91), (64, 34), (106, 91), (22, 91)], GOLD, 6)
    line(draw, [(36, 72), (92, 72)], TEAL, 5)
    line(draw, [(49, 91), (49, 72), (64, 53), (79, 72), (79, 91)], ICE, 4)
    line(draw, [(36, 72), (49, 91)], TEAL, 4)
    line(draw, [(92, 72), (79, 91)], TEAL, 4)


def icon_fence(draw):
    for x in (29, 64, 99):
        line(draw, [(x, 35), (x, 101)], TEAL, 7)
        line(draw, [(x - 6, 35), (x + 6, 35)], GOLD, 4)
    line(draw, [(24, 55), (104, 55)], ICE, 7)
    line(draw, [(24, 82), (104, 82)], ICE, 7)


def icon_floor(draw):
    polygon(draw, [(27, 38), (101, 38), (111, 98), (17, 98)],
            fill="#1c4355", outline=TEAL, width=4)
    for y in (53, 69, 84):
        line(draw, [(24, y), (104, y)], MUTED, 3)
    for top_x, bottom_x in ((39, 31), (53, 48), (75, 80), (89, 97)):
        line(draw, [(top_x, 38), (bottom_x, 98)], MUTED, 3)
    line(draw, [(27, 38), (101, 38)], GOLD, 5)


def icon_door(draw):
    rectangle(draw, 28, 27, 100, 102, outline=GOLD, width=6)
    rectangle(draw, 40, 39, 89, 102, fill="#1c3b50", outline=TEAL,
              width=5, radius=3)
    line(draw, [(49, 49), (80, 49), (80, 90), (49, 90)], MUTED, 3)
    circle(draw, 80, 72, 3, fill=GOLD)
    line(draw, [(34, 109), (94, 109)], ICE, 4)


def icon_window(draw):
    rectangle(draw, 23, 29, 105, 101, outline=GOLD, width=6)
    rectangle(draw, 32, 38, 96, 92, fill="#1c4355", outline=TEAL, width=4)
    line(draw, [(64, 38), (64, 92)], ICE, 5)
    line(draw, [(32, 65), (96, 65)], ICE, 5)
    line(draw, [(23, 106), (105, 106)], GOLD, 4)


def icon_stair(draw):
    line(draw, [(23, 100), (23, 84), (40, 84), (40, 68), (57, 68),
                (57, 52), (74, 52), (74, 36), (103, 36)], TEAL, 8)
    line(draw, [(23, 100), (103, 100)], GOLD, 5)
    line(draw, [(74, 29), (103, 29), (103, 58)], ICE, 4)


def icon_bathroom(draw):
    rectangle(draw, 31, 29, 61, 57, fill="#24475c", outline=TEAL,
              width=5, radius=4)
    line(draw, [(38, 58), (50, 58)], ICE, 5)
    draw.arc(box(44, 51, 99, 84), 0, 180, fill=GOLD, width=6 * SCALE)
    line(draw, [(47, 68), (54, 82), (80, 82), (91, 70)], ICE, 6)
    line(draw, [(61, 83), (61, 98), (82, 98), (82, 83)], TEAL, 5)
    line(draw, [(58, 104), (88, 104)], GOLD, 4)
    circle(draw, 43, 43, 3, fill=GOLD)


def icon_electrical(draw):
    circle(draw, 64, 64, 38, outline=TEAL, width=5)
    polygon(draw, [(69, 27), (46, 67), (62, 67), (54, 101),
                   (83, 57), (67, 57)], fill=GOLD)
    circle(draw, 64, 64, 47, outline=MUTED, width=2)


def icon_furniture(draw):
    rectangle(draw, 29, 43, 99, 79, fill="#24475c", outline=TEAL,
              width=5, radius=8)
    rectangle(draw, 24, 61, 104, 88, fill="#1c3d52", outline=ICE,
              width=5, radius=7)
    line(draw, [(33, 88), (31, 101)], GOLD, 5)
    line(draw, [(95, 88), (97, 101)], GOLD, 5)
    line(draw, [(43, 67), (43, 80)], MUTED, 3)
    line(draw, [(84, 67), (84, 80)], MUTED, 3)


def icon_kitchen(draw):
    line(draw, [(24, 42), (104, 42)], GOLD, 7)
    rectangle(draw, 28, 48, 100, 100, fill="#1c3d52", outline=TEAL,
              width=5, radius=3)
    line(draw, [(28, 73), (100, 73)], ICE, 4)
    line(draw, [(63, 48), (63, 100)], MUTED, 3)
    circle(draw, 43, 60, 4, fill=GOLD)
    circle(draw, 82, 60, 4, fill=GOLD)
    line(draw, [(76, 84), (91, 84)], TEAL, 4)
    line(draw, [(76, 91), (91, 91)], TEAL, 4)


def icon_decor(draw):
    polygon(draw, [(39, 70), (89, 70), (82, 102), (46, 102)],
            fill="#664b3e", outline=GOLD, width=5)
    line(draw, [(64, 72), (64, 38)], TEAL, 5)
    line(draw, [(64, 58), (42, 41)], TEAL, 5)
    line(draw, [(64, 53), (84, 34)], TEAL, 5)
    line(draw, [(63, 47), (56, 28)], TEAL, 5)
    polygon(draw, [(41, 41), (28, 34), (34, 51)], fill=TEAL)
    polygon(draw, [(84, 34), (99, 29), (92, 47)], fill=GOLD)
    polygon(draw, [(56, 28), (51, 15), (69, 25)], fill=ICE)
    line(draw, [(34, 107), (94, 107)], MUTED, 4)


def icon_openings(draw):
    rectangle(draw, 19, 35, 58, 98, outline=GOLD, width=5)
    rectangle(draw, 69, 35, 109, 98, outline=TEAL, width=5)
    line(draw, [(28, 45), (49, 45), (49, 89), (28, 89)], ICE, 4)
    line(draw, [(89, 40), (89, 93)], ICE, 4)
    line(draw, [(74, 66), (104, 66)], ICE, 4)


def icon_structure(draw):
    line(draw, [(27, 96), (27, 37), (101, 37), (101, 96)], TEAL, 7)
    line(draw, [(27, 57), (101, 57)], GOLD, 7)
    line(draw, [(51, 39), (51, 96)], ICE, 5)
    line(draw, [(77, 39), (77, 96)], ICE, 5)
    line(draw, [(20, 102), (108, 102)], MUTED, 4)


def icon_quantities(draw):
    rectangle(draw, 29, 23, 99, 105, fill="#1c3d52", outline=TEAL,
              width=5, radius=5)
    line(draw, [(43, 42), (82, 42)], ICE, 4)
    line(draw, [(43, 54), (75, 54)], MUTED, 3)
    rectangle(draw, 43, 72, 52, 91, fill=BLUE, outline=None)
    rectangle(draw, 59, 64, 68, 91, fill=TEAL, outline=None)
    rectangle(draw, 75, 50, 84, 91, fill=GOLD, outline=None)
    line(draw, [(39, 96), (89, 96)], ICE, 3)


def icon_control_center(draw):
    circle(draw, 64, 64, 15, fill=GOLD, outline=ICE, width=3)
    for cx, cy, color in ((32, 35, TEAL), (96, 35, BLUE),
                          (32, 93, CORAL), (96, 93, ICE)):
        line(draw, [(64, 64), (cx, cy)], MUTED, 4)
        rectangle(draw, cx - 10, cy - 10, cx + 10, cy + 10,
                  fill=NAVY, outline=color, width=4, radius=4)


def icon_boolean(draw):
    circle(draw, 48, 64, 27, fill="#1d4b5b", outline=TEAL, width=5)
    circle(draw, 80, 64, 27, fill="#5a4433", outline=GOLD, width=5)
    polygon(draw, [(64, 39), (75, 43), (83, 52), (86, 64), (83, 76),
                   (75, 85), (64, 89), (56, 82), (52, 70), (52, 58),
                   (56, 46)], fill=ICE)


def icon_snap(draw):
    circle(draw, 57, 65, 31, outline=TEAL, width=5)
    circle(draw, 57, 65, 16, outline=GOLD, width=4)
    circle(draw, 57, 65, 5, fill=ICE)
    line(draw, [(67, 75), (101, 103)], GOLD, 7)
    polygon(draw, [(88, 86), (107, 108), (83, 99)], fill=ICE)


def icon_material(draw):
    polygon(draw, [(64, 25), (95, 41), (95, 82), (64, 101),
                   (33, 82), (33, 41)], fill="#24475c", outline=TEAL, width=5)
    line(draw, [(33, 41), (64, 59), (95, 41)], ICE, 4)
    line(draw, [(64, 59), (64, 101)], GOLD, 4)
    line(draw, [(64, 59), (95, 41)], TEAL, 4)


# ════════════════════════════════════════════════════════════
#  Extra primitives shared by the v1.13 icon set
# ════════════════════════════════════════════════════════════
def arc(draw, cx, cy, radius, start, end, color=ICE, width=4):
    """Arc of a circle; PIL angles grow clockwise, 0° at 3 o'clock."""
    draw.arc(box(cx - radius, cy - radius, cx + radius, cy + radius),
             start, end, fill=color, width=max(1, round(width * SCALE)))


def pie(draw, cx, cy, radius, start, end, fill=None, outline=None, width=4):
    draw.pieslice(box(cx - radius, cy - radius, cx + radius, cy + radius),
                  start, end, fill=fill, outline=outline,
                  width=max(1, round(width * SCALE)))


def ellipse(draw, x1, y1, x2, y2, fill=None, outline=None, width=4):
    draw.ellipse(box(x1, y1, x2, y2), fill=fill, outline=outline,
                 width=max(1, round(width * SCALE)))


def arrow(draw, start, end, color=ICE, width=5, head=12):
    """Straight arrow with a filled triangular head at ``end``."""
    line(draw, [start, end], color, width)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    spread = 0.5
    left = (end[0] - head * math.cos(angle - spread),
            end[1] - head * math.sin(angle - spread))
    right = (end[0] - head * math.cos(angle + spread),
             end[1] - head * math.sin(angle + spread))
    polygon(draw, [end, left, right], fill=color)


def star(cx, cy, outer, inner, points=5):
    result = []
    for index in range(points * 2):
        radius = outer if index % 2 == 0 else inner
        angle = -math.pi / 2 + index * math.pi / points
        result.append((cx + radius * math.cos(angle),
                       cy + radius * math.sin(angle)))
    return result


def bezier(p0, p1, p2, p3, steps=24):
    result = []
    for index in range(steps + 1):
        t = index / steps
        u = 1.0 - t
        result.append((
            u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0]
            + t ** 3 * p3[0],
            u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1]
            + t ** 3 * p3[1],
        ))
    return result


def radial(cx, cy, radius, degrees):
    angle = math.radians(degrees)
    return cx + radius * math.cos(angle), cy + radius * math.sin(angle)


DARK = "#1c4355"
PANEL = "#1c3d52"
CABINET = "#1c3b50"
CUSHION = "#24475c"
WOOD = "#664b3e"
LEATHER = "#5a4433"
GLASS = "#1d4b5b"
LEAF = "#2f6b4f"


# ════════════════════════════════════════════════════════════
#  Annotations
# ════════════════════════════════════════════════════════════
def icon_annotation(draw):
    # Plan outline with its overall dimension underneath.
    rectangle(draw, 34, 26, 94, 64, fill=DARK, outline=TEAL, width=4)
    line(draw, [(34, 70), (34, 98)], MUTED, 3)
    line(draw, [(94, 70), (94, 98)], MUTED, 3)
    line(draw, [(26, 90), (102, 90)], GOLD, 4)
    line(draw, [(29, 95), (39, 85)], ICE, 4)
    line(draw, [(89, 95), (99, 85)], ICE, 4)
    line(draw, [(54, 79), (74, 79)], ICE, 4)


def icon_dimension(draw):
    line(draw, [(28, 36), (28, 92)], MUTED, 3)
    line(draw, [(100, 36), (100, 92)], MUTED, 3)
    line(draw, [(20, 76), (108, 76)], GOLD, 5)
    line(draw, [(22, 82), (34, 70)], ICE, 4)
    line(draw, [(94, 82), (106, 70)], ICE, 4)
    line(draw, [(50, 60), (78, 60)], ICE, 5)
    line(draw, [(56, 50), (72, 50)], TEAL, 3)


def icon_dimension_draw(draw):
    line(draw, [(26, 50), (26, 96)], MUTED, 3)
    line(draw, [(20, 82), (78, 82)], TEAL, 5)
    line(draw, [(22, 88), (32, 76)], ICE, 4)
    circle(draw, 26, 82, 6, fill=GOLD, outline=NAVY, width=2)
    line(draw, [(86, 74), (108, 52)], GOLD, 10)
    polygon(draw, [(76, 84), (82, 70), (90, 78)], fill=ICE)


def icon_grid_axes(draw):
    for x in (56, 90):
        line(draw, [(x, 42), (x, 106)], TEAL, 4)
        circle(draw, x, 32, 9, fill=NAVY, outline=ICE, width=4)
    for y in (62, 92):
        line(draw, [(38, y), (106, y)], GOLD, 4)
        circle(draw, 28, y, 9, fill=NAVY, outline=ICE, width=4)
    for x in (56, 90):
        for y in (62, 92):
            circle(draw, x, y, 4, fill=ICE)


def icon_north_arrow(draw):
    polygon(draw, [(58, 20), (36, 98), (58, 82)], fill=TEAL)
    polygon(draw, [(58, 20), (80, 98), (58, 82)], fill=NAVY, outline=ICE,
            width=4)
    line(draw, [(88, 108), (88, 86), (104, 108), (104, 86)], GOLD, 5)


# ════════════════════════════════════════════════════════════
#  Sets
# ════════════════════════════════════════════════════════════
def icon_sets(draw):
    rectangle(draw, 44, 26, 104, 86, fill="#1a3344", outline=MUTED, width=3)
    rectangle(draw, 26, 42, 86, 102, fill=DARK, outline=TEAL, width=4)
    line(draw, [(56, 42), (56, 72)], GOLD, 4)
    line(draw, [(26, 72), (86, 72)], GOLD, 4)
    line(draw, [(56, 86), (56, 98)], ICE, 3)
    arc(draw, 56, 86, 12, 90, 180, ICE, 3)


def icon_set_bathroom(draw):
    rectangle(draw, 26, 24, 102, 104, fill=DARK, outline=TEAL, width=5)
    rectangle(draw, 33, 31, 51, 40, fill=ICE, outline=None)
    ellipse(draw, 34, 43, 50, 63, outline=ICE, width=3)
    rectangle(draw, 70, 32, 94, 48, outline=GOLD, width=3, radius=4)
    circle(draw, 82, 36, 2, fill=GOLD)
    rectangle(draw, 68, 70, 94, 96, outline=ICE, width=3)
    line(draw, [(68, 70), (94, 96)], MUTED, 2)
    line(draw, [(94, 70), (68, 96)], MUTED, 2)
    circle(draw, 81, 83, 3, fill=TEAL)
    line(draw, [(34, 104), (34, 86)], GOLD, 3)
    arc(draw, 34, 104, 18, 270, 360, GOLD, 3)


def icon_set_apartment(draw):
    rectangle(draw, 22, 24, 106, 104, fill=DARK, outline=TEAL, width=5)
    line(draw, [(58, 24), (58, 66)], GOLD, 4)
    line(draw, [(22, 66), (106, 66)], GOLD, 4)
    line(draw, [(76, 66), (76, 104)], GOLD, 4)
    rectangle(draw, 78, 32, 98, 54, outline=ICE, width=3)
    line(draw, [(78, 40), (98, 40)], ICE, 2)
    circle(draw, 40, 86, 8, outline=ICE, width=3)
    line(draw, [(58, 54), (58, 66)], NAVY, 6)
    arc(draw, 58, 54, 12, 0, 90, ICE, 3)
    line(draw, [(58, 54), (70, 54)], ICE, 3)


# ════════════════════════════════════════════════════════════
#  Preferences & general tools
# ════════════════════════════════════════════════════════════
def icon_units(draw):
    rectangle(draw, 20, 46, 108, 82, fill=DARK, outline=GOLD, width=4,
              radius=3)
    for x in range(27, 104, 7):
        tall = (x - 27) % 28 == 0
        line(draw, [(x, 46), (x, 62 if tall else 55)],
             TEAL if tall else ICE, 3)
    line(draw, [(30, 96), (98, 96)], MUTED, 3)
    line(draw, [(30, 91), (30, 101)], MUTED, 3)
    line(draw, [(98, 91), (98, 101)], MUTED, 3)


def icon_language(draw):
    circle(draw, 64, 64, 37, fill=DARK, outline=TEAL, width=5)
    ellipse(draw, 49, 27, 79, 101, outline=ICE, width=3)
    line(draw, [(27, 64), (101, 64)], ICE, 3)
    line(draw, [(34, 46), (94, 46)], MUTED, 2)
    line(draw, [(34, 82), (94, 82)], MUTED, 2)
    line(draw, [(64, 27), (64, 101)], GOLD, 2)


def icon_procedural(draw):
    for y, color in ((30, TEAL), (58, GOLD), (86, CORAL)):
        rectangle(draw, 22, y, 44, y + 14, fill=DARK, outline=color,
                  width=3, radius=3)
        circle(draw, 44, y + 7, 3, fill=color)
    rectangle(draw, 74, 40, 106, 92, fill=DARK, outline=ICE, width=4,
              radius=4)
    for y, target, color in ((37, 52, TEAL), (65, 66, GOLD),
                             (93, 80, CORAL)):
        line(draw, [(47, y), (60, y), (62, target), (74, target)], color, 3)
        circle(draw, 74, target, 3, fill=color)
    for y in (52, 66, 80):
        line(draw, [(80, y), (100, y)], MUTED, 2)


def icon_preferences(draw):
    for step in range(8):
        line(draw, [radial(64, 64, 27, step * 45),
                    radial(64, 64, 38, step * 45)], ICE, 9)
    circle(draw, 64, 64, 28, fill=DARK, outline=ICE, width=6)
    circle(draw, 64, 64, 11, fill=NAVY, outline=GOLD, width=4)


def icon_material_library(draw):
    rectangle(draw, 50, 22, 98, 70, fill=LEATHER, outline=GOLD, width=4,
              radius=5)
    rectangle(draw, 40, 36, 88, 84, fill=GLASS, outline=TEAL, width=4,
              radius=5)
    rectangle(draw, 30, 50, 78, 98, fill=CUSHION, outline=ICE, width=4,
              radius=5)
    line(draw, [(40, 62), (68, 62)], MUTED, 3)
    line(draw, [(40, 72), (60, 72)], MUTED, 3)
    circle(draw, 44, 86, 4, fill=GOLD)


def icon_scene(draw):
    polygon(draw, [(40, 60), (88, 60), (106, 100), (22, 100)], fill=DARK,
            outline=TEAL, width=4)
    line(draw, [(52, 60), (46, 100)], MUTED, 2)
    line(draw, [(64, 60), (64, 100)], MUTED, 2)
    line(draw, [(76, 60), (82, 100)], MUTED, 2)
    line(draw, [(34, 80), (94, 80)], MUTED, 2)
    polygon(draw, [(50, 48), (64, 40), (78, 48), (64, 56)], fill="#285c6b",
            outline=ICE, width=3)
    polygon(draw, [(50, 48), (64, 56), (64, 76), (50, 68)], fill="#1d4156",
            outline=ICE, width=3)
    polygon(draw, [(64, 56), (78, 48), (78, 68), (64, 76)], fill="#234a60",
            outline=ICE, width=3)
    circle(draw, 96, 32, 8, fill=GOLD)


def icon_tools(draw):
    line(draw, [(32, 96), (76, 52)], GOLD, 13)
    circle(draw, 86, 42, 18, fill=GOLD)
    polygon(draw, [(86, 42), (98, 18), (112, 30)], fill=NAVY)
    line(draw, [(40, 92), (70, 62)], ICE, 3)


def icon_quick_edit(draw):
    for y, knob, color in ((40, 50, TEAL), (64, 86, GOLD), (88, 62, ICE)):
        line(draw, [(26, y), (102, y)], MUTED, 4)
        line(draw, [(26, y), (knob, y)], color, 4)
        circle(draw, knob, y, 8, fill=color, outline=NAVY, width=2)


def icon_manipulator(draw):
    arrow(draw, (56, 72), (56, 24), TEAL, 6, 14)
    arrow(draw, (56, 72), (106, 72), CORAL, 6, 14)
    arrow(draw, (56, 72), (24, 102), BLUE, 6, 14)
    circle(draw, 56, 72, 8, fill=ICE, outline=NAVY, width=2)


def icon_reference_point(draw):
    ellipse(draw, 34, 88, 94, 106, fill=DARK, outline=TEAL, width=3)
    line(draw, [(44, 97), (84, 97)], MUTED, 2)
    polygon(draw, [(47, 52), (81, 52), (64, 92)], fill=GOLD)
    circle(draw, 64, 46, 21, fill=GOLD)
    circle(draw, 64, 46, 9, fill=NAVY, outline=ICE, width=3)


def icon_render(draw):
    rectangle(draw, 44, 32, 72, 48, fill=ICE, outline=None, radius=3)
    rectangle(draw, 24, 44, 104, 98, fill=DARK, outline=ICE, width=5,
              radius=7)
    circle(draw, 64, 71, 17, fill=NAVY, outline=TEAL, width=5)
    circle(draw, 64, 71, 6, fill=GOLD)
    circle(draw, 92, 57, 4, fill=GOLD)


def icon_preset(draw):
    rectangle(draw, 28, 24, 100, 104, fill=DARK, outline=TEAL, width=4,
              radius=6)
    polygon(draw, star(64, 56, 21, 9), fill=GOLD)
    line(draw, [(42, 86), (86, 86)], ICE, 4)
    line(draw, [(48, 95), (80, 95)], MUTED, 3)


def icon_room_assets(draw):
    for x1, y1 in ((26, 26), (68, 26), (26, 68), (68, 68)):
        rectangle(draw, x1, y1, x1 + 34, y1 + 34, fill=DARK, outline=MUTED,
                  width=3, radius=5)
    circle(draw, 43, 43, 10, fill=TEAL)
    polygon(draw, [(85, 33), (96, 53), (74, 53)], fill=GOLD)
    rectangle(draw, 34, 76, 52, 94, fill=ICE, outline=None, radius=2)
    line(draw, [(85, 76), (85, 94)], CORAL, 5)
    line(draw, [(76, 85), (94, 85)], CORAL, 5)


def icon_place(draw):
    line(draw, [(24, 104), (104, 104)], TEAL, 4)
    circle(draw, 64, 60, 24, fill=DARK, outline=ICE, width=4)
    line(draw, [(64, 28), (64, 46)], MUTED, 3)
    line(draw, [(32, 60), (50, 60)], MUTED, 3)
    line(draw, [(78, 60), (96, 60)], MUTED, 3)
    circle(draw, 64, 60, 6, fill=GOLD)
    arrow(draw, (64, 74), (64, 100), GOLD, 4, 10)


def icon_draw(draw):
    line(draw, [(22, 94), (36, 72), (54, 86), (70, 62)], TEAL, 6)
    line(draw, [(82, 52), (106, 28)], GOLD, 12)
    polygon(draw, [(69, 65), (76, 51), (83, 58)], fill=ICE)
    line(draw, [(98, 36), (106, 28)], CORAL, 12)


def icon_curve(draw):
    p0, p1, p2, p3 = (26, 96), (38, 30), (90, 98), (102, 32)
    line(draw, [p0, p1], MUTED, 2)
    line(draw, [p3, p2], MUTED, 2)
    line(draw, bezier(p0, p1, p2, p3), TEAL, 6)
    for point in (p1, p2):
        circle(draw, point[0], point[1], 5, fill=GOLD, outline=NAVY, width=2)
    for point in (p0, p3):
        circle(draw, point[0], point[1], 6, fill=ICE, outline=NAVY, width=2)


def icon_ceiling(draw):
    polygon(draw, [(24, 38), (64, 20), (104, 38), (64, 56)], fill="#285c6b",
            outline=TEAL, width=4)
    polygon(draw, [(24, 38), (64, 56), (64, 66), (24, 48)], fill="#1d4156",
            outline=TEAL, width=4)
    polygon(draw, [(64, 56), (104, 38), (104, 48), (64, 66)], fill="#234a60",
            outline=TEAL, width=4)
    line(draw, [(64, 66), (64, 84)], MUTED, 3)
    polygon(draw, [(54, 84), (74, 84), (82, 98), (46, 98)], fill=GOLD)
    line(draw, [(56, 104), (58, 110)], ICE, 3)
    line(draw, [(64, 104), (64, 111)], ICE, 3)
    line(draw, [(72, 104), (70, 110)], ICE, 3)


# ════════════════════════════════════════════════════════════
#  Circulation
# ════════════════════════════════════════════════════════════
def icon_ramp(draw):
    polygon(draw, [(22, 100), (106, 100), (106, 40)], fill=DARK, outline=TEAL,
            width=5)
    arrow(draw, (34, 80), (88, 41), GOLD, 5, 13)
    line(draw, [(22, 108), (106, 108)], MUTED, 3)


def icon_stair_l(draw):
    rectangle(draw, 22, 70, 70, 100, fill=DARK, outline=TEAL, width=4)
    rectangle(draw, 70, 22, 100, 100, fill=DARK, outline=TEAL, width=4)
    for x in (34, 46, 58):
        line(draw, [(x, 70), (x, 100)], ICE, 3)
    for y in (34, 46, 58):
        line(draw, [(70, y), (100, y)], ICE, 3)
    line(draw, [(28, 85), (85, 85)], GOLD, 4)
    arrow(draw, (85, 85), (85, 32), GOLD, 4, 11)


def icon_stair_spiral(draw):
    circle(draw, 64, 64, 38, fill=DARK, outline=TEAL, width=4)
    for step in range(12):
        line(draw, [radial(64, 64, 8, step * 30), radial(64, 64, 37, step * 30)],
             GOLD if step == 0 else ICE, 3)
    circle(draw, 64, 64, 7, fill=GOLD)
    arc(draw, 64, 64, 24, 200, 340, GOLD, 4)


# ════════════════════════════════════════════════════════════
#  Bathroom fixtures
# ════════════════════════════════════════════════════════════
def icon_toilet(draw):
    rectangle(draw, 28, 26, 52, 66, fill=DARK, outline=ICE, width=4, radius=4)
    circle(draw, 40, 34, 3, fill=GOLD)
    polygon(draw, [(52, 60), (98, 60), (94, 74), (70, 80), (58, 80), (52, 72)],
            fill=CUSHION, outline=TEAL, width=4)
    line(draw, [(52, 58), (100, 58)], ICE, 5)
    polygon(draw, [(58, 80), (70, 80), (74, 102), (54, 102)], fill=DARK,
            outline=TEAL, width=4)
    line(draw, [(44, 104), (84, 104)], MUTED, 3)


def icon_bidet(draw):
    polygon(draw, [(28, 56), (100, 56), (94, 72), (70, 78), (58, 78), (34, 72)],
            fill=CUSHION, outline=TEAL, width=4)
    ellipse(draw, 38, 50, 90, 62, fill=DARK, outline=ICE, width=3)
    line(draw, [(84, 50), (84, 36), (94, 36)], GOLD, 4)
    polygon(draw, [(56, 78), (72, 78), (76, 102), (52, 102)], fill=DARK,
            outline=TEAL, width=4)
    line(draw, [(40, 104), (88, 104)], MUTED, 3)


def icon_pedestal_sink(draw):
    line(draw, [(64, 30), (64, 44)], GOLD, 4)
    line(draw, [(56, 30), (72, 30)], GOLD, 4)
    polygon(draw, [(24, 46), (104, 46), (96, 64), (76, 72), (52, 72), (32, 64)],
            fill=CUSHION, outline=TEAL, width=4)
    line(draw, [(30, 46), (98, 46)], ICE, 4)
    polygon(draw, [(54, 72), (74, 72), (76, 104), (52, 104)], fill=DARK,
            outline=ICE, width=4)
    line(draw, [(44, 106), (84, 106)], MUTED, 3)


def icon_vanity(draw):
    line(draw, [(64, 28), (64, 40)], GOLD, 4)
    line(draw, [(56, 28), (72, 28)], GOLD, 4)
    rectangle(draw, 22, 42, 106, 52, fill=ICE, outline=None, radius=2)
    rectangle(draw, 26, 52, 102, 100, fill=CABINET, outline=TEAL, width=4,
              radius=3)
    ellipse(draw, 46, 44, 82, 54, fill=DARK, outline=TEAL, width=3)
    line(draw, [(64, 58), (64, 98)], MUTED, 3)
    circle(draw, 56, 76, 3, fill=GOLD)
    circle(draw, 72, 76, 3, fill=GOLD)
    line(draw, [(30, 100), (30, 106)], ICE, 4)
    line(draw, [(98, 100), (98, 106)], ICE, 4)


def icon_basin(draw):
    line(draw, [(20, 24), (20, 106)], MUTED, 5)
    line(draw, [(58, 36), (58, 48)], GOLD, 4)
    line(draw, [(50, 36), (66, 36)], GOLD, 4)
    polygon(draw, [(20, 50), (98, 50), (90, 66), (70, 74), (46, 74), (26, 66)],
            fill=CUSHION, outline=TEAL, width=4)
    line(draw, [(24, 50), (94, 50)], ICE, 4)
    line(draw, [(58, 74), (58, 86), (46, 86), (46, 98), (20, 98)], ICE, 4)


def icon_shower(draw):
    line(draw, [(32, 30), (32, 42), (68, 42), (68, 50)], TEAL, 5)
    polygon(draw, [(50, 50), (86, 50), (80, 60), (56, 60)], fill=ICE)
    for x in (56, 64, 72, 80):
        line(draw, [(x, 66), (x - 2, 84)], GOLD, 3)
    rectangle(draw, 36, 90, 100, 100, fill=DARK, outline=TEAL, width=4,
              radius=3)
    circle(draw, 68, 95, 2, fill=ICE)


def icon_bathtub(draw):
    line(draw, [(88, 30), (88, 46)], GOLD, 4)
    line(draw, [(80, 30), (96, 30)], GOLD, 4)
    rectangle(draw, 22, 46, 106, 56, fill=ICE, outline=None, radius=3)
    polygon(draw, [(26, 56), (102, 56), (94, 90), (34, 90)], fill=CUSHION,
            outline=TEAL, width=4)
    line(draw, [(38, 90), (38, 102)], ICE, 5)
    line(draw, [(90, 90), (90, 102)], ICE, 5)
    line(draw, [(44, 66), (84, 66)], MUTED, 2)


def icon_mirror(draw):
    ellipse(draw, 34, 22, 94, 94, fill=CUSHION, outline=GOLD, width=5)
    line(draw, [(52, 70), (74, 40)], ICE, 4)
    line(draw, [(62, 76), (80, 52)], ICE, 3)
    line(draw, [(40, 104), (88, 104)], TEAL, 4)


def icon_towel_rail(draw):
    line(draw, [(24, 40), (104, 40)], ICE, 6)
    for x in (34, 94):
        line(draw, [(x, 40), (x, 28)], MUTED, 5)
        circle(draw, x, 26, 5, fill=MUTED)
    polygon(draw, [(42, 40), (86, 40), (86, 100), (42, 100)], fill=CUSHION,
            outline=TEAL, width=4)
    line(draw, [(42, 86), (86, 86)], GOLD, 3)
    line(draw, [(42, 92), (86, 92)], GOLD, 3)


def icon_electric_shower(draw):
    line(draw, [(28, 28), (28, 44), (64, 44), (64, 52)], TEAL, 5)
    ellipse(draw, 40, 52, 88, 78, fill=CUSHION, outline=ICE, width=4)
    polygon(draw, [(68, 54), (58, 66), (65, 66), (60, 78), (72, 63), (65, 63)],
            fill=GOLD)
    for x in (48, 58, 70, 80):
        line(draw, [(x, 84), (x - 2, 100)], BLUE, 3)


# ════════════════════════════════════════════════════════════
#  Electrical
# ════════════════════════════════════════════════════════════
def icon_outlet(draw):
    rectangle(draw, 30, 24, 98, 104, fill=DARK, outline=ICE, width=4, radius=6)
    circle(draw, 64, 64, 26, fill=NAVY, outline=TEAL, width=4)
    rectangle(draw, 50, 52, 56, 68, fill=ICE, outline=None, radius=1)
    rectangle(draw, 72, 52, 78, 68, fill=ICE, outline=None, radius=1)
    circle(draw, 64, 78, 4, fill=GOLD)


def icon_switch(draw):
    rectangle(draw, 30, 24, 98, 104, fill=DARK, outline=ICE, width=4, radius=6)
    rectangle(draw, 46, 40, 82, 88, fill=NAVY, outline=TEAL, width=4, radius=4)
    rectangle(draw, 50, 44, 78, 62, fill=GOLD, outline=None, radius=3)
    circle(draw, 64, 76, 3, fill=MUTED)


def icon_data(draw):
    rectangle(draw, 30, 24, 98, 104, fill=DARK, outline=ICE, width=4, radius=6)
    polygon(draw, [(46, 48), (82, 48), (82, 84), (72, 84), (72, 90), (56, 90),
                   (56, 84), (46, 84)], fill=NAVY, outline=TEAL, width=4)
    for x in (54, 60, 66, 72):
        line(draw, [(x, 52), (x, 62)], GOLD, 2)


def icon_bulb(draw):
    circle(draw, 64, 52, 26, fill=LEATHER, outline=GOLD, width=4)
    rectangle(draw, 54, 74, 74, 86, fill=MUTED, outline=None)
    rectangle(draw, 56, 86, 72, 96, fill=NAVY, outline=ICE, width=3, radius=2)
    line(draw, [(56, 60), (60, 50), (64, 60), (68, 50), (72, 60)], ICE, 2)
    line(draw, [(30, 26), (36, 32)], GOLD, 3)
    line(draw, [(98, 26), (92, 32)], GOLD, 3)
    line(draw, [(22, 52), (30, 52)], GOLD, 3)
    line(draw, [(106, 52), (98, 52)], GOLD, 3)


def icon_pendant(draw):
    line(draw, [(64, 18), (64, 44)], MUTED, 3)
    polygon(draw, [(46, 44), (82, 44), (98, 76), (30, 76)], fill=CUSHION,
            outline=GOLD, width=4)
    circle(draw, 64, 84, 9, fill=GOLD)
    line(draw, [(48, 94), (44, 104)], ICE, 3)
    line(draw, [(64, 98), (64, 108)], ICE, 3)
    line(draw, [(80, 94), (84, 104)], ICE, 3)


def icon_ceiling_light(draw):
    line(draw, [(20, 36), (108, 36)], MUTED, 5)
    pie(draw, 64, 36, 30, 0, 180, fill=CUSHION, outline=GOLD, width=5)
    for x, dx in ((40, -6), (64, 0), (88, 6)):
        line(draw, [(x, 76), (x + dx, 96)], ICE, 3)


def icon_downlight(draw):
    polygon(draw, [(48, 24), (80, 24), (84, 52), (44, 52)], fill=DARK,
            outline=TEAL, width=4)
    line(draw, [(20, 52), (108, 52)], MUTED, 5)
    rectangle(draw, 40, 50, 88, 58, fill=ICE, outline=None, radius=2)
    polygon(draw, [(50, 60), (78, 60), (96, 104), (32, 104)], fill="#524a35")
    circle(draw, 64, 60, 5, fill=GOLD)


def icon_sconce(draw):
    line(draw, [(28, 20), (28, 108)], MUTED, 5)
    rectangle(draw, 28, 56, 40, 72, fill=ICE, outline=None, radius=2)
    line(draw, [(40, 64), (62, 64)], ICE, 4)
    pie(draw, 70, 56, 22, 0, 180, fill=CUSHION, outline=GOLD, width=4)
    line(draw, [(48, 56), (92, 56)], GOLD, 4)
    line(draw, [(56, 44), (52, 32)], ICE, 3)
    line(draw, [(70, 42), (70, 28)], ICE, 3)
    line(draw, [(84, 44), (88, 32)], ICE, 3)


def icon_panel_board(draw):
    rectangle(draw, 30, 22, 98, 106, fill=DARK, outline=ICE, width=4, radius=4)
    rectangle(draw, 40, 32, 88, 96, fill=NAVY, outline=MUTED, width=3)
    for index, y in enumerate((40, 52, 64, 76)):
        first, second = (TEAL, ICE) if index % 2 == 0 else (ICE, TEAL)
        rectangle(draw, 44, y, 60, y + 8, fill=first, outline=None, radius=1)
        rectangle(draw, 68, y, 84, y + 8, fill=second, outline=None, radius=1)
    polygon(draw, [(66, 82), (60, 92), (64, 92), (61, 100), (69, 89), (65, 89)],
            fill=GOLD)


# ════════════════════════════════════════════════════════════
#  Furniture
# ════════════════════════════════════════════════════════════
def icon_dining_chair(draw):
    rectangle(draw, 38, 24, 90, 62, fill=DARK, outline=TEAL, width=4, radius=5)
    line(draw, [(55, 30), (55, 56)], MUTED, 3)
    line(draw, [(73, 30), (73, 56)], MUTED, 3)
    rectangle(draw, 30, 62, 98, 76, fill=ICE, outline=None, radius=3)
    line(draw, [(36, 76), (34, 104)], GOLD, 5)
    line(draw, [(92, 76), (94, 104)], GOLD, 5)


def icon_office_chair(draw):
    rectangle(draw, 40, 22, 88, 58, fill=DARK, outline=TEAL, width=4, radius=8)
    rectangle(draw, 32, 58, 96, 72, fill=ICE, outline=None, radius=4)
    line(draw, [(26, 50), (26, 60), (36, 60)], MUTED, 4)
    line(draw, [(102, 50), (102, 60), (92, 60)], MUTED, 4)
    line(draw, [(64, 72), (64, 90)], GOLD, 5)
    line(draw, [(34, 104), (64, 90), (94, 104)], GOLD, 5)
    line(draw, [(64, 90), (64, 106)], GOLD, 5)
    for x, y in ((34, 104), (94, 104), (64, 106)):
        circle(draw, x, y, 3, fill=ICE)


def icon_armchair(draw):
    rectangle(draw, 36, 28, 92, 70, fill=CUSHION, outline=TEAL, width=4,
              radius=8)
    rectangle(draw, 24, 56, 104, 90, fill=PANEL, outline=ICE, width=4,
              radius=8)
    rectangle(draw, 40, 62, 88, 80, fill=CUSHION, outline=TEAL, width=3,
              radius=4)
    line(draw, [(32, 90), (30, 102)], GOLD, 5)
    line(draw, [(96, 90), (98, 102)], GOLD, 5)


def icon_sofa(draw):
    rectangle(draw, 26, 34, 102, 68, fill=CUSHION, outline=TEAL, width=4,
              radius=6)
    rectangle(draw, 18, 60, 110, 90, fill=PANEL, outline=ICE, width=4,
              radius=7)
    line(draw, [(48, 64), (48, 86)], MUTED, 3)
    line(draw, [(80, 64), (80, 86)], MUTED, 3)
    line(draw, [(26, 90), (24, 102)], GOLD, 5)
    line(draw, [(102, 90), (104, 102)], GOLD, 5)


def icon_coffee_table(draw):
    circle(draw, 56, 46, 6, fill=TEAL)
    ellipse(draw, 66, 48, 86, 54, fill=GOLD, outline=None)
    rectangle(draw, 20, 54, 108, 64, fill=ICE, outline=None, radius=3)
    line(draw, [(30, 64), (30, 100)], GOLD, 5)
    line(draw, [(98, 64), (98, 100)], GOLD, 5)
    line(draw, [(30, 86), (98, 86)], TEAL, 4)


def icon_dining_table(draw):
    polygon(draw, [(58, 44), (70, 44), (68, 30), (60, 30)], fill=TEAL)
    circle(draw, 64, 26, 5, fill=CORAL)
    rectangle(draw, 20, 44, 108, 54, fill=ICE, outline=None, radius=3)
    line(draw, [(32, 54), (32, 104)], GOLD, 6)
    line(draw, [(96, 54), (96, 104)], GOLD, 6)
    line(draw, [(32, 70), (96, 70)], MUTED, 3)


def icon_bed(draw):
    rectangle(draw, 22, 26, 44, 92, fill=CUSHION, outline=TEAL, width=4,
              radius=4)
    rectangle(draw, 40, 58, 108, 84, fill=PANEL, outline=ICE, width=4,
              radius=4)
    rectangle(draw, 46, 50, 70, 62, fill=ICE, outline=None, radius=4)
    line(draw, [(40, 72), (108, 72)], GOLD, 3)
    line(draw, [(48, 84), (48, 100)], GOLD, 5)
    line(draw, [(100, 84), (100, 100)], GOLD, 5)


def icon_nightstand(draw):
    line(draw, [(64, 54), (64, 42)], MUTED, 3)
    polygon(draw, [(52, 42), (76, 42), (80, 26), (48, 26)], fill=GOLD)
    rectangle(draw, 34, 54, 94, 100, fill=CABINET, outline=TEAL, width=4,
              radius=3)
    line(draw, [(34, 76), (94, 76)], MUTED, 3)
    circle(draw, 64, 65, 3, fill=GOLD)
    circle(draw, 64, 88, 3, fill=GOLD)
    line(draw, [(38, 100), (38, 106)], ICE, 4)
    line(draw, [(90, 100), (90, 106)], ICE, 4)


def icon_dresser(draw):
    rectangle(draw, 34, 22, 94, 104, fill=CABINET, outline=TEAL, width=4,
              radius=3)
    for y in (42, 62, 82):
        line(draw, [(34, y), (94, y)], MUTED, 3)
    for y in (32, 52, 72, 93):
        line(draw, [(58, y), (70, y)], GOLD, 4)


def icon_shelf(draw):
    rectangle(draw, 28, 22, 100, 104, fill=CABINET, outline=TEAL, width=4)
    for x, color in ((36, GOLD), (46, CORAL), (56, BLUE)):
        rectangle(draw, x, 30, x + 8, 50, fill=color, outline=None)
    polygon(draw, [(70, 50), (80, 50), (90, 30), (80, 30)], fill=ICE)
    rectangle(draw, 36, 60, 52, 78, fill=MUTED, outline=None)
    for x, color in ((60, TEAL), (72, GOLD), (84, ICE)):
        rectangle(draw, x, 58, x + 9, 78, fill=color, outline=None)
    ellipse(draw, 40, 86, 60, 100, fill=CORAL, outline=None)
    for y in (50, 78):
        line(draw, [(28, y), (100, y)], ICE, 4)


# ════════════════════════════════════════════════════════════
#  Kitchen
# ════════════════════════════════════════════════════════════
def icon_fridge(draw):
    rectangle(draw, 36, 20, 92, 106, fill=PANEL, outline=ICE, width=4,
              radius=6)
    line(draw, [(36, 50), (92, 50)], ICE, 4)
    line(draw, [(80, 30), (80, 44)], GOLD, 4)
    line(draw, [(80, 58), (80, 84)], GOLD, 4)
    circle(draw, 52, 40, 2, fill=MUTED)


def icon_stove(draw):
    rectangle(draw, 28, 40, 100, 104, fill=PANEL, outline=ICE, width=4,
              radius=3)
    line(draw, [(28, 40), (100, 40)], TEAL, 6)
    circle(draw, 46, 32, 8, fill=NAVY, outline=TEAL, width=3)
    circle(draw, 82, 32, 8, fill=NAVY, outline=TEAL, width=3)
    for x in (36, 52, 76, 92):
        circle(draw, x, 49, 2, fill=GOLD)
    rectangle(draw, 40, 58, 88, 94, fill=NAVY, outline=MUTED, width=3,
              radius=3)
    line(draw, [(48, 70), (80, 70)], GOLD, 3)


def icon_range_hood(draw):
    rectangle(draw, 52, 18, 76, 50, fill=PANEL, outline=ICE, width=4)
    polygon(draw, [(24, 76), (104, 76), (84, 50), (44, 50)], fill=CUSHION,
            outline=TEAL, width=4)
    line(draw, [(24, 76), (104, 76)], GOLD, 5)
    for x in (44, 64, 84):
        arrow(draw, (x, 104), (x, 88), MUTED, 3, 7)


def icon_sink_cabinet(draw):
    line(draw, [(64, 24), (64, 38)], GOLD, 4)
    line(draw, [(56, 24), (74, 24)], GOLD, 4)
    rectangle(draw, 22, 40, 106, 50, fill=ICE, outline=None, radius=2)
    rectangle(draw, 26, 50, 102, 100, fill=CABINET, outline=TEAL, width=4,
              radius=3)
    rectangle(draw, 44, 42, 84, 56, fill=DARK, outline=TEAL, width=3, radius=2)
    line(draw, [(64, 60), (64, 98)], MUTED, 3)
    line(draw, [(52, 76), (58, 76)], GOLD, 4)
    line(draw, [(70, 76), (76, 76)], GOLD, 4)


def icon_dishwasher(draw):
    rectangle(draw, 28, 24, 100, 104, fill=PANEL, outline=ICE, width=4,
              radius=4)
    line(draw, [(28, 42), (100, 42)], TEAL, 4)
    for x in (40, 50, 60):
        circle(draw, x, 33, 3, fill=GOLD)
    line(draw, [(76, 33), (90, 33)], MUTED, 3)
    line(draw, [(40, 56), (88, 56)], ICE, 5)
    rectangle(draw, 44, 68, 84, 92, fill=NAVY, outline=MUTED, width=3,
              radius=3)
    circle(draw, 64, 80, 6, outline=TEAL, width=3)


def icon_microwave(draw):
    rectangle(draw, 20, 36, 108, 92, fill=PANEL, outline=ICE, width=4,
              radius=5)
    rectangle(draw, 28, 44, 78, 84, fill=NAVY, outline=TEAL, width=3, radius=3)
    for y in (52, 60, 68, 76):
        line(draw, [(36, y), (70, y)], MUTED, 2)
    circle(draw, 93, 54, 5, fill=GOLD)
    circle(draw, 93, 70, 5, fill=GOLD)
    line(draw, [(86, 82), (100, 82)], MUTED, 3)
    line(draw, [(32, 92), (32, 98)], ICE, 4)
    line(draw, [(96, 92), (96, 98)], ICE, 4)


def icon_utensils(draw):
    line(draw, [(40, 44), (40, 104)], ICE, 5)
    for x in (32, 40, 48):
        line(draw, [(x, 24), (x, 44)], ICE, 4)
    line(draw, [(32, 44), (48, 44)], ICE, 4)
    line(draw, [(64, 54), (64, 104)], GOLD, 5)
    polygon(draw, [(58, 56), (70, 56), (70, 24), (58, 36)], fill=GOLD)
    line(draw, [(88, 50), (88, 104)], TEAL, 5)
    ellipse(draw, 78, 22, 98, 52, fill=TEAL, outline=None)


# ════════════════════════════════════════════════════════════
#  Decor
# ════════════════════════════════════════════════════════════
def icon_planter(draw):
    circle(draw, 64, 46, 24, fill=LEAF, outline=TEAL, width=4)
    circle(draw, 48, 56, 14, fill=LEAF, outline=TEAL, width=3)
    circle(draw, 80, 56, 14, fill=LEAF, outline=TEAL, width=3)
    line(draw, [(64, 66), (64, 76)], GOLD, 4)
    polygon(draw, [(38, 76), (90, 76), (84, 104), (44, 104)], fill=WOOD,
            outline=GOLD, width=5)
    line(draw, [(34, 76), (94, 76)], GOLD, 6)


def icon_floor_lamp(draw):
    polygon(draw, [(48, 24), (80, 24), (90, 50), (38, 50)], fill=CUSHION,
            outline=GOLD, width=4)
    line(draw, [(64, 50), (64, 100)], ICE, 5)
    ellipse(draw, 42, 96, 86, 108, fill=TEAL, outline=None)
    line(draw, [(52, 58), (50, 68)], GOLD, 3)
    line(draw, [(76, 58), (78, 68)], GOLD, 3)


def icon_table_lamp(draw):
    polygon(draw, [(42, 30), (86, 30), (98, 66), (30, 66)], fill=CUSHION,
            outline=GOLD, width=4)
    line(draw, [(64, 66), (64, 90)], ICE, 5)
    rectangle(draw, 44, 90, 84, 100, fill=TEAL, outline=None, radius=4)
    line(draw, [(22, 104), (106, 104)], MUTED, 3)


def icon_vase_set(draw):
    polygon(draw, [(30, 52), (46, 52), (50, 70), (46, 104), (30, 104), (26, 70)],
            fill=CUSHION, outline=TEAL, width=4)
    polygon(draw, [(56, 36), (72, 36), (68, 48), (78, 70), (74, 104), (54, 104),
                   (50, 70), (60, 48)], fill=LEATHER, outline=GOLD, width=4)
    polygon(draw, [(84, 62), (100, 62), (104, 104), (80, 104)], fill=PANEL,
            outline=ICE, width=4)
    line(draw, [(64, 36), (64, 22)], TEAL, 3)
    circle(draw, 64, 18, 5, fill=CORAL)


def icon_wall_art(draw):
    line(draw, [(64, 28), (64, 18)], MUTED, 3)
    rectangle(draw, 22, 28, 106, 100, fill=PANEL, outline=GOLD, width=5)
    rectangle(draw, 32, 38, 96, 90, fill=GLASS, outline=None)
    polygon(draw, [(32, 90), (54, 58), (68, 78), (78, 66), (96, 90)], fill=TEAL)
    circle(draw, 82, 50, 6, fill=GOLD)


def icon_clock(draw):
    circle(draw, 64, 64, 40, fill=PANEL, outline=GOLD, width=5)
    for step in range(12):
        major = step % 3 == 0
        line(draw, [radial(64, 64, 26 if major else 30, step * 30),
                    radial(64, 64, 35, step * 30)],
             TEAL if major else ICE, 3)
    line(draw, [(64, 64), (64, 40)], ICE, 5)
    line(draw, [(64, 64), (82, 72)], ICE, 5)
    circle(draw, 64, 64, 4, fill=GOLD)


def icon_books(draw):
    rectangle(draw, 24, 78, 92, 92, fill=LEATHER, outline=GOLD, width=3,
              radius=2)
    rectangle(draw, 30, 64, 98, 78, fill=GLASS, outline=TEAL, width=3,
              radius=2)
    rectangle(draw, 26, 50, 90, 64, fill=CUSHION, outline=ICE, width=3,
              radius=2)
    polygon(draw, [(90, 92), (102, 92), (108, 38), (96, 38)], fill="#3b2f3f",
            outline=CORAL, width=3)
    line(draw, [(40, 85), (76, 85)], MUTED, 2)
    line(draw, [(44, 71), (84, 71)], MUTED, 2)
    line(draw, [(40, 57), (76, 57)], MUTED, 2)
    line(draw, [(20, 96), (108, 96)], MUTED, 3)


def icon_tv(draw):
    rectangle(draw, 20, 26, 108, 84, fill=NAVY, outline=ICE, width=5, radius=4)
    rectangle(draw, 26, 32, 102, 78, fill=GLASS, outline=None)
    line(draw, [(34, 70), (56, 46), (72, 60), (94, 40)], TEAL, 4)
    line(draw, [(64, 84), (64, 96)], MUTED, 4)
    line(draw, [(40, 100), (88, 100)], MUTED, 5)


def icon_rug(draw):
    rectangle(draw, 30, 32, 98, 96, fill=LEATHER, outline=GOLD, width=4)
    rectangle(draw, 40, 42, 88, 86, outline=ICE, width=3)
    polygon(draw, [(64, 50), (78, 64), (64, 78), (50, 64)], fill=TEAL)
    for y in range(36, 96, 10):
        line(draw, [(22, y), (30, y)], GOLD, 3)
        line(draw, [(98, y), (106, y)], GOLD, 3)


# ════════════════════════════════════════════════════════════
#  Doors & windows (plan symbols / elevations)
# ════════════════════════════════════════════════════════════
def icon_door_single(draw):
    line(draw, [(16, 96), (40, 96)], TEAL, 8)
    line(draw, [(88, 96), (112, 96)], TEAL, 8)
    line(draw, [(40, 96), (40, 48)], ICE, 6)
    arc(draw, 40, 96, 48, 270, 360, GOLD, 4)


def icon_door_double(draw):
    line(draw, [(14, 96), (30, 96)], TEAL, 8)
    line(draw, [(98, 96), (114, 96)], TEAL, 8)
    line(draw, [(30, 96), (30, 62)], ICE, 6)
    line(draw, [(98, 96), (98, 62)], ICE, 6)
    arc(draw, 30, 96, 34, 270, 360, GOLD, 4)
    arc(draw, 98, 96, 34, 180, 270, GOLD, 4)


def icon_door_sliding(draw):
    line(draw, [(14, 80), (40, 80)], TEAL, 8)
    line(draw, [(88, 80), (114, 80)], TEAL, 8)
    line(draw, [(40, 84), (76, 84)], ICE, 6)
    line(draw, [(56, 74), (92, 74)], GOLD, 6)
    arrow(draw, (68, 54), (36, 54), ICE, 4, 10)
    line(draw, [(46, 100), (82, 100)], MUTED, 3)


def icon_win_sliding(draw):
    rectangle(draw, 20, 30, 108, 98, fill=DARK, outline=GOLD, width=5)
    rectangle(draw, 28, 38, 66, 90, outline=TEAL, width=4)
    rectangle(draw, 62, 42, 100, 94, fill=DARK, outline=ICE, width=4)
    arrow(draw, (54, 64), (38, 64), ICE, 3, 8)
    arrow(draw, (74, 72), (90, 72), ICE, 3, 8)


def icon_win_casement(draw):
    rectangle(draw, 20, 30, 108, 98, fill=DARK, outline=GOLD, width=5)
    rectangle(draw, 28, 38, 100, 90, outline=TEAL, width=4)
    line(draw, [(28, 38), (100, 64), (28, 90)], ICE, 3)
    circle(draw, 92, 64, 3, fill=GOLD)


def icon_win_fixed(draw):
    rectangle(draw, 20, 30, 108, 98, fill=DARK, outline=GOLD, width=5)
    rectangle(draw, 30, 40, 98, 88, fill=GLASS, outline=TEAL, width=4)
    line(draw, [(42, 80), (72, 48)], ICE, 3)
    line(draw, [(56, 84), (84, 54)], ICE, 2)


# ════════════════════════════════════════════════════════════
#  Structure+
# ════════════════════════════════════════════════════════════
def icon_footing(draw):
    rectangle(draw, 52, 22, 76, 70, fill=PANEL, outline=TEAL, width=4)
    rectangle(draw, 24, 70, 104, 92, fill=CUSHION, outline=GOLD, width=4)
    line(draw, [(20, 96), (108, 96)], MUTED, 3)
    for x in range(28, 104, 12):
        line(draw, [(x, 100), (x + 6, 108)], MUTED, 2)


def icon_column(draw):
    rectangle(draw, 36, 22, 92, 32, fill=ICE, outline=None)
    rectangle(draw, 46, 32, 82, 96, fill=PANEL, outline=TEAL, width=4)
    line(draw, [(58, 36), (58, 92)], MUTED, 2)
    line(draw, [(70, 36), (70, 92)], MUTED, 2)
    rectangle(draw, 36, 96, 92, 106, fill=GOLD, outline=None)


def icon_beam(draw):
    rectangle(draw, 18, 42, 110, 62, fill=CUSHION, outline=GOLD, width=4)
    rectangle(draw, 24, 62, 40, 100, fill=PANEL, outline=TEAL, width=4)
    rectangle(draw, 88, 62, 104, 100, fill=PANEL, outline=TEAL, width=4)
    line(draw, [(26, 52), (102, 52)], MUTED, 2)
    arrow(draw, (64, 22), (64, 40), ICE, 3, 8)


def icon_ribbed_slab(draw):
    rectangle(draw, 18, 36, 110, 52, fill=CUSHION, outline=TEAL, width=4)
    for x in (30, 58, 86):
        rectangle(draw, x, 52, x + 12, 86, fill=PANEL, outline=GOLD, width=3)
    line(draw, [(24, 92), (104, 92)], MUTED, 3)


def icon_grid(draw):
    for value in (34, 64, 94):
        line(draw, [(value, 24), (value, 104)], MUTED, 2)
        line(draw, [(24, value), (104, value)], MUTED, 2)
    for x in (34, 64, 94):
        for y in (34, 64, 94):
            rectangle(draw, x - 5, y - 5, x + 5, y + 5, fill=GOLD, outline=None)


def icon_levels(draw):
    line(draw, [(26, 28), (26, 100)], MUTED, 3)
    for y, color in ((36, GOLD), (64, TEAL), (92, ICE)):
        line(draw, [(26, y), (102, y)], color, 4)
        polygon(draw, [(36, y), (44, y - 10), (52, y)], fill=color)
        line(draw, [(60, y - 6), (96, y - 6)], MUTED, 3)


# ════════════════════════════════════════════════════════════
#  Roof types
# ════════════════════════════════════════════════════════════
def icon_roof_gable(draw):
    polygon(draw, [(20, 70), (64, 28), (108, 70)], fill=CUSHION, outline=GOLD,
            width=6)
    line(draw, [(32, 70), (32, 100), (96, 100), (96, 70)], TEAL, 5)


def icon_roof_hip(draw):
    polygon(draw, [(18, 72), (46, 34), (82, 34), (110, 72)], fill=CUSHION,
            outline=GOLD, width=5)
    line(draw, [(46, 34), (40, 72)], ICE, 3)
    line(draw, [(82, 34), (88, 72)], ICE, 3)
    line(draw, [(32, 72), (32, 100), (96, 100), (96, 72)], TEAL, 5)


def icon_roof_shed(draw):
    polygon(draw, [(20, 72), (108, 36), (108, 46), (20, 82)], fill=CUSHION,
            outline=GOLD, width=5)
    line(draw, [(32, 82), (32, 100), (96, 100), (96, 50)], TEAL, 5)


ICONS = {
    # ── Brand & original module set ───────────────────────────
    "archiforge": icon_archiforge,
    "archipack": icon_archiforge,  # Compatibility alias used by the menu.
    "wall": icon_wall,
    "wall_draw": icon_wall_draw,
    "slab": icon_slab,
    "roof": icon_roof,
    "truss": icon_truss,
    "fence": icon_fence,
    "floor": icon_floor,
    "door": icon_door,
    "window": icon_window,
    "stair": icon_stair,
    "bathroom": icon_bathroom,
    "electrical": icon_electrical,
    "furniture": icon_furniture,
    "kitchen": icon_kitchen,
    "decor": icon_decor,
    "opening": icon_openings,
    "structure": icon_structure,
    "quantities": icon_quantities,
    "control_center": icon_control_center,
    "boolean": icon_boolean,
    "snap": icon_snap,
    "material": icon_material,
    # ── Annotations ───────────────────────────────────────────
    "annotation": icon_annotation,
    "dimension": icon_dimension,
    "dimension_draw": icon_dimension_draw,
    "grid_axes": icon_grid_axes,
    "north_arrow": icon_north_arrow,
    # ── Sets ──────────────────────────────────────────────────
    "sets": icon_sets,
    "set_bathroom": icon_set_bathroom,
    "set_apartment": icon_set_apartment,
    # ── Preferences & tools ───────────────────────────────────
    "units": icon_units,
    "language": icon_language,
    "procedural": icon_procedural,
    "preferences": icon_preferences,
    "material_library": icon_material_library,
    "scene": icon_scene,
    "tools": icon_tools,
    "quick_edit": icon_quick_edit,
    "manipulator": icon_manipulator,
    "reference_point": icon_reference_point,
    "render": icon_render,
    "preset": icon_preset,
    "room_assets": icon_room_assets,
    "place": icon_place,
    "draw": icon_draw,
    "curve": icon_curve,
    "ceiling": icon_ceiling,
    # ── Circulation ───────────────────────────────────────────
    "ramp": icon_ramp,
    "stair_l": icon_stair_l,
    "stair_spiral": icon_stair_spiral,
    # ── Bathroom ──────────────────────────────────────────────
    "toilet": icon_toilet,
    "bidet": icon_bidet,
    "pedestal_sink": icon_pedestal_sink,
    "vanity": icon_vanity,
    "basin": icon_basin,
    "shower": icon_shower,
    "bathtub": icon_bathtub,
    "mirror": icon_mirror,
    "towel_rail": icon_towel_rail,
    "electric_shower": icon_electric_shower,
    # ── Electrical ────────────────────────────────────────────
    "outlet": icon_outlet,
    "switch": icon_switch,
    "data": icon_data,
    "bulb": icon_bulb,
    "pendant": icon_pendant,
    "ceiling_light": icon_ceiling_light,
    "downlight": icon_downlight,
    "sconce": icon_sconce,
    "panel_board": icon_panel_board,
    # ── Furniture ─────────────────────────────────────────────
    "dining_chair": icon_dining_chair,
    "office_chair": icon_office_chair,
    "armchair": icon_armchair,
    "sofa": icon_sofa,
    "coffee_table": icon_coffee_table,
    "dining_table": icon_dining_table,
    "bed": icon_bed,
    "nightstand": icon_nightstand,
    "dresser": icon_dresser,
    "shelf": icon_shelf,
    # ── Kitchen ───────────────────────────────────────────────
    "fridge": icon_fridge,
    "stove": icon_stove,
    "range_hood": icon_range_hood,
    "sink_cabinet": icon_sink_cabinet,
    "dishwasher": icon_dishwasher,
    "microwave": icon_microwave,
    "utensils": icon_utensils,
    # ── Decor ─────────────────────────────────────────────────
    "planter": icon_planter,
    "floor_lamp": icon_floor_lamp,
    "table_lamp": icon_table_lamp,
    "vase_set": icon_vase_set,
    "wall_art": icon_wall_art,
    "clock": icon_clock,
    "books": icon_books,
    "tv": icon_tv,
    "rug": icon_rug,
    # ── Doors & windows+ ──────────────────────────────────────
    "door_single": icon_door_single,
    "door_double": icon_door_double,
    "door_sliding": icon_door_sliding,
    "win_sliding": icon_win_sliding,
    "win_casement": icon_win_casement,
    "win_fixed": icon_win_fixed,
    # ── Structure+ ────────────────────────────────────────────
    "footing": icon_footing,
    "column": icon_column,
    "beam": icon_beam,
    "ribbed_slab": icon_ribbed_slab,
    "grid": icon_grid,
    "levels": icon_levels,
    # ── Roof types ────────────────────────────────────────────
    "roof_gable": icon_roof_gable,
    "roof_hip": icon_roof_hip,
    "roof_shed": icon_roof_shed,
}


def render(name, draw_symbol):
    image = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw_background(draw)
    draw_symbol(draw)
    image = image.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
    image.save(ROOT / f"{name}.png", optimize=True)


def main(argv=None):
    """Render every icon, or only the names passed on the command line."""
    names = list(argv if argv is not None else sys.argv[1:])
    unknown = [name for name in names if name not in ICONS]
    if unknown:
        raise SystemExit(f"Unknown icon(s): {', '.join(unknown)}")
    selected = names or list(ICONS)
    for name in selected:
        render(name, ICONS[name])
    print(f"Generated {len(selected)} ArchiForge icons in {ROOT}")


if __name__ == "__main__":
    main()
