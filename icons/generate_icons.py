#!/usr/bin/env python3
"""Regenerate ArchiForge's original Blender preview icons.

Developer utility only; Blender loads the generated PNGs and does not need
Pillow. Run with Pillow installed: ``python icons/generate_icons.py``.
"""

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


ICONS = {
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
}


def render(name, draw_symbol):
    image = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw_background(draw)
    draw_symbol(draw)
    image = image.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
    image.save(ROOT / f"{name}.png", optimize=True)


def main():
    for name, draw_symbol in ICONS.items():
        render(name, draw_symbol)
    print(f"Generated {len(ICONS)} ArchiForge icons in {ROOT}")


if __name__ == "__main__":
    main()
