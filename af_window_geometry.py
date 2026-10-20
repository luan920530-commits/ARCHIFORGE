# -*- coding: utf-8 -*-

# ╔══════════════════════════════════════════════════════════╗
# ║         ARCHIFORGE — af_window_geometry.py              ║
# ║         Cinemática pura de hojas de ventana             ║
# ║         GPL v3 — ArchiForge Devs                        ║
# ╚══════════════════════════════════════════════════════════╝

# <pep8 compliant>

"""Hinge axes and rigid rotations for parametric window sashes.

This module has no ``bpy`` dependency, so the opening kinematics used by
``af_window.py`` can be verified outside Blender. Coordinates follow the
window generator: X runs along the wall, Y crosses it (-Y is the exterior,
+Y the interior) and Z points up.

A sash is described by its closed rectangle ``x0..x1`` / ``z0..z1`` and the
two faces of its frame depth ``y_outer`` (exterior) and ``y_inner``
(interior). ``sash_hinge`` picks the hinge axis for the window type and
``rotate_point`` applies the same rigid rotation to every vertex of the
leaf (stiles, rails, glass and grille), so nothing is left behind when the
sash opens. ``hinge_positions`` returns knuckle centres that lie exactly on
that axis.
"""

import math
from collections import namedtuple

# Types whose sashes rotate around a hinge. SLIDING and DOUBLE_HUNG
# translate, FIXED and ARCH never open: none of them may expose the
# open/close toggle.
OPENABLE_WINDOW_TYPES = ('CASEMENT', 'AWNING')

HINGE_SIDES = ('LEFT', 'RIGHT')
SWING_DIRECTIONS = ('OUT', 'IN')

# Knuckle centres along the hinge axis, as fractions of the leaf extent.
HINGE_FRACTIONS = (0.15, 0.85)

# Angles below this threshold are treated as "closed".
MIN_OPEN_ANGLE = 1e-6

SashHinge = namedtuple("SashHinge", "axis pivot angle side")
"""Rotation of one sash.

``axis``  'Z' for a vertical (casement) hinge, 'X' for a horizontal top
          (awning) hinge.
``pivot`` a point ``(x, y, z)`` on the hinge axis.
``angle`` signed rotation in radians following the right-hand rule around
          ``axis``; ``0.0`` keeps the leaf closed.
``side``  'LEFT' / 'RIGHT' for casements, 'TOP' for awnings.
"""


def window_type_can_open(window_type):
    """True when ``window_type`` has sashes that rotate around a hinge."""
    return window_type in OPENABLE_WINDOW_TYPES


def leaf_hinge_side(hinge_side, column):
    """Side of the hinge for the casement leaf in ``column`` (0-based).

    Adjacent leaves alternate sides so that paired leaves meet in the
    middle like a French window, starting with the user-selected side.
    """
    side = 'RIGHT' if hinge_side == 'RIGHT' else 'LEFT'
    if int(column) % 2:
        side = 'LEFT' if side == 'RIGHT' else 'RIGHT'
    return side


def sash_hinge(window_type, x0, x1, z0, z1, y_outer, y_inner, open_angle,
               hinge_side='LEFT', column=0, swing='OUT'):
    """Describe the hinge of one sash, or ``None`` if the type cannot open.

    Casements rotate around a vertical axis on the hinge stile. The axis
    sits on the sash face it swings towards (exterior face for ``OUT``,
    interior face for ``IN``) so the stile sweeps into the daylight
    opening instead of cutting through the jamb. Awnings are top-hinged
    on the exterior face and project their bottom rail outwards.
    """
    if not window_type_can_open(window_type):
        return None

    angle = float(open_angle)
    if abs(angle) < MIN_OPEN_ANGLE:
        angle = 0.0

    if window_type == 'AWNING':
        # Rotation around +X with a negative angle moves the bottom rail
        # (dz < 0) towards -Y, i.e. to the exterior, and keeps every point
        # of the sash at or below the hinge line.
        return SashHinge('X', (float(x0), float(y_outer), float(z1)),
                         -angle, 'TOP')

    side = leaf_hinge_side(hinge_side, column)
    outward = swing != 'IN'
    pivot_x = float(x0) if side == 'LEFT' else float(x1)
    pivot_y = float(y_outer) if outward else float(y_inner)
    # Sign table (free edge must move to -Y when opening outwards):
    #   LEFT/OUT -> -a   RIGHT/OUT -> +a   LEFT/IN -> +a   RIGHT/IN -> -a
    sign = (-1.0 if side == 'LEFT' else 1.0) * (1.0 if outward else -1.0)
    return SashHinge('Z', (pivot_x, pivot_y, float(z0)), sign * angle, side)


def rotate_point(point, hinge):
    """Rotate ``point`` rigidly around ``hinge`` (right-hand rule)."""
    x, y, z = (float(point[0]), float(point[1]), float(point[2]))
    if hinge is None or abs(hinge.angle) < MIN_OPEN_ANGLE:
        return (x, y, z)
    px, py, pz = hinge.pivot
    cos_a = math.cos(hinge.angle)
    sin_a = math.sin(hinge.angle)
    if hinge.axis == 'Z':
        dx, dy = x - px, y - py
        return (px + dx * cos_a - dy * sin_a,
                py + dx * sin_a + dy * cos_a,
                z)
    if hinge.axis == 'X':
        dy, dz = y - py, z - pz
        return (x,
                py + dy * cos_a - dz * sin_a,
                pz + dy * sin_a + dz * cos_a)
    raise ValueError("Unsupported hinge axis: {!r}".format(hinge.axis))


def distance_to_axis(point, hinge):
    """Perpendicular distance from ``point`` to the hinge axis."""
    x, y, z = (float(point[0]), float(point[1]), float(point[2]))
    px, py, pz = hinge.pivot
    if hinge.axis == 'Z':
        return math.hypot(x - px, y - py)
    if hinge.axis == 'X':
        return math.hypot(y - py, z - pz)
    raise ValueError("Unsupported hinge axis: {!r}".format(hinge.axis))


def hinge_positions(hinge, x0, x1, z0, z1, fractions=HINGE_FRACTIONS):
    """Centres of the hinge knuckles, all lying on the rotation axis."""
    if hinge is None:
        return []
    px, py, pz = hinge.pivot
    if hinge.axis == 'Z':
        return [(px, py, float(z0) + f * (float(z1) - float(z0)))
                for f in fractions]
    return [(float(x0) + f * (float(x1) - float(x0)), py, pz)
            for f in fractions]


def hinge_knuckle_length(hinge, x0, x1, z0, z1, requested, max_fraction=0.4):
    """Knuckle length clamped so the two hinges never overlap each other."""
    extent = (float(z1) - float(z0)) if hinge.axis == 'Z' \
        else (float(x1) - float(x0))
    return max(min(float(requested), abs(extent) * max_fraction), 0.0)
