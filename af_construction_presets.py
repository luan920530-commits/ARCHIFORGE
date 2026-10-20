# -*- coding: utf-8 -*-

# ╔══════════════════════════════════════════════════════════╗
# ║         ARCHIFORGE — af_construction_presets.py         ║
# ║         Presets de referencia para muros y pisos        ║
# ║         GPL v3 — ArchiForge Devs                        ║
# ╚══════════════════════════════════════════════════════════╝

# <pep8 compliant>

"""Commercial reference presets shared by ``af_wall.py`` and ``af_floor.py``.

Pure data without ``bpy`` so the catalogue can be validated by the test
suite. Every value is an editable starting point taken from common
commercial formats or drafting conventions; none of them is a statement of
code compliance.

Wall presets only set the initial thickness of the single solid that
ArchiForge generates. They do not add bond patterns, studs, cavities or
finish layers, and the labels must not suggest otherwise.
"""

CUSTOM_PRESET = 'CUSTOM'

# (identifier, label, thickness in metres, reference basis)
WALL_SYSTEM_PRESETS = (
    (CUSTOM_PRESET, "Custom", None,
     "Manual thickness"),
    ('WOOD_FRAME', "Wood frame", 0.115,
     "2x4 studs (89 mm) plus 12.7 mm boards on both faces"),
    ('BRICK', "Brick", 0.15,
     "12 cm clay brick laid as a single wythe plus ~15 mm plaster per face"),
    ('CONCRETE', "Concrete", 0.25,
     "Cast-in-place reinforced concrete wall"),
    ('STRUCTURAL_BLOCK', "Structural block", 0.20,
     "20 cm hollow structural masonry block"),
)

# (identifier, label, (width, depth) in metres, reference basis)
TILE_FORMAT_PRESETS = (
    (CUSTOM_PRESET, "Custom", None,
     "Manual tile size"),
    ('T30x30', "30 x 30 cm", (0.30, 0.30),
     "Ceramic floor tile"),
    ('T45x45', "45 x 45 cm", (0.45, 0.45),
     "Ceramic / porcelain floor tile"),
    ('T60x60', "60 x 60 cm", (0.60, 0.60),
     "Rectified porcelain tile"),
    ('T60x120', "60 x 120 cm", (0.60, 1.20),
     "Large-format rectified porcelain plank"),
)

WALL_PRESET_NOTE = (
    "Reference thickness only: the wall stays a single solid with no bond "
    "pattern or layers, and the value is not a code requirement."
)
TILE_PRESET_NOTE = (
    "Commercial reference format; edit the size freely afterwards."
)

# Tolerance when deciding whether an edited value still matches a preset.
PRESET_MATCH_TOLERANCE = 1e-4


def _format_metres(value):
    text = "{:.3f}".format(float(value)).rstrip("0").rstrip(".")
    return text if text else "0"


def wall_preset_thickness(preset_id):
    """Initial thickness for a wall preset, ``None`` for ``CUSTOM``/unknown."""
    for identifier, _label, thickness, _basis in WALL_SYSTEM_PRESETS:
        if identifier == preset_id:
            return thickness
    return None


def wall_preset_items():
    """Enum items ``(id, label, description)`` for Blender properties."""
    items = []
    for identifier, label, thickness, basis in WALL_SYSTEM_PRESETS:
        if thickness is None:
            description = basis
        else:
            description = "{} - {} m reference thickness ({}). {}".format(
                basis, _format_metres(thickness), "editable",
                WALL_PRESET_NOTE)
        items.append((identifier, label, description))
    return items


def tile_preset_dimensions(preset_id):
    """``(width, depth)`` for a tile preset, ``None`` for ``CUSTOM``/unknown."""
    for identifier, _label, dims, _basis in TILE_FORMAT_PRESETS:
        if identifier == preset_id:
            return dims
    return None


def tile_preset_items():
    """Enum items ``(id, label, description)`` for Blender properties."""
    items = []
    for identifier, label, dims, basis in TILE_FORMAT_PRESETS:
        if dims is None:
            description = basis
        else:
            description = "{} {} x {} m. {}".format(
                basis, _format_metres(dims[0]), _format_metres(dims[1]),
                TILE_PRESET_NOTE)
        items.append((identifier, label, description))
    return items


def values_match(expected, actual, tolerance=PRESET_MATCH_TOLERANCE):
    """True when every edited value still equals the preset value."""
    if expected is None:
        return False
    try:
        expected_values = tuple(expected)
    except TypeError:
        expected_values = (expected,)
    try:
        actual_values = tuple(actual)
    except TypeError:
        actual_values = (actual,)
    if len(expected_values) != len(actual_values):
        return False
    return all(abs(float(e) - float(a)) <= tolerance
               for e, a in zip(expected_values, actual_values))


def preset_for_wall_thickness(current_preset, thickness):
    """Preset to keep after the user edits the thickness by hand.

    Returns ``current_preset`` while the value still matches it and
    ``CUSTOM`` as soon as it diverges, so the label never claims a system
    whose reference thickness is no longer in use.
    """
    if values_match(wall_preset_thickness(current_preset), thickness):
        return current_preset
    return CUSTOM_PRESET


def preset_for_tile_size(current_preset, width, depth):
    """Tile preset to keep after the user edits the tile size by hand."""
    if values_match(tile_preset_dimensions(current_preset), (width, depth)):
        return current_preset
    return CUSTOM_PRESET
