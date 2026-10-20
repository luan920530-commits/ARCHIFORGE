# -*- coding: utf-8 -*-

# ╔══════════════════════════════════════════════════════════╗
# ║         ARCHIFORGE — af_icons.py                        ║
# ║         Acceso compartido a los íconos propios          ║
# ║         GPL v3 — ArchiForge Devs                        ║
# ╚══════════════════════════════════════════════════════════╝

# <pep8 compliant>

"""Shared access to ArchiForge's custom preview icons.

``__init__.py`` loads every PNG found in ``icons/`` into a
``bpy.utils.previews`` collection. This module lets any panel, menu or
operator button reference those icons without importing the package root:

    from .af_icons import icon_kw as _icon
    row.operator("archiforge.wall", text="Wall", **_icon("wall", 'SNAP_FACE'))

When the PNG is missing, failed to load or the addon runs outside Blender,
the helpers fall back to the built-in Blender icon so a ``draw()`` never
breaks. The module has no ``bpy`` dependency.
"""

import sys

__all__ = ("ITEM_ICONS", "OBJECT_ICONS", "get_icons", "icon_id", "icon_kw",
           "item_icon")


# Custom icon for each ``item_type`` of the catalogue operators (bathroom,
# electrical, furniture, kitchen, decor, openings, stairs, structure, roofs).
# Buttons fall back to the module icon when an item is not listed here.
ITEM_ICONS = {
    # archiforge.bathroom
    "TOILET": "toilet",
    "BIDET": "bidet",
    "PEDESTAL_SINK": "pedestal_sink",
    "VANITY": "vanity",
    "WALLHUNG_BASIN": "basin",
    "SHOWER": "shower",
    "BATHTUB": "bathtub",
    "MIRROR": "mirror",
    "TOWEL_RAIL": "towel_rail",
    "ELECTRIC_SHOWER": "electric_shower",
    # archiforge.electrical
    "OUTLET": "outlet",
    "SWITCH": "switch",
    "DATA": "data",
    "BULB": "bulb",
    "PENDANT": "pendant",
    "CEILING_LIGHT": "ceiling_light",
    "DOWNLIGHT": "downlight",
    "SCONCE": "sconce",
    "PANEL_BOARD": "panel_board",
    # archiforge.furniture
    "DINING_CHAIR": "dining_chair",
    "OFFICE_CHAIR": "office_chair",
    "ARMCHAIR": "armchair",
    "SOFA": "sofa",
    "COFFEE_TABLE": "coffee_table",
    "DINING_TABLE": "dining_table",
    "BED": "bed",
    "NIGHTSTAND": "nightstand",
    "DRESSER": "dresser",
    "SHELF": "shelf",
    # archiforge.kitchen
    "FRIDGE": "fridge",
    "STOVE": "stove",
    "RANGE_HOOD": "range_hood",
    "SINK_CABINET": "sink_cabinet",
    "DISHWASHER": "dishwasher",
    "MICROWAVE": "microwave",
    "UTENSILS": "utensils",
    # archiforge.decor
    "PLANTER": "planter",
    "FLOOR_LAMP": "floor_lamp",
    "TABLE_LAMP": "table_lamp",
    "VASE_SET": "vase_set",
    "WALL_ART": "wall_art",
    "CLOCK": "clock",
    "BOOKS": "books",
    "TV": "tv",
    "RUG": "rug",
    # archiforge.opening
    "DOOR_SINGLE": "door_single",
    "DOOR_DOUBLE": "door_double",
    "DOOR_SLIDING": "door_sliding",
    "WIN_SLIDING": "win_sliding",
    "WIN_CASEMENT": "win_casement",
    "WIN_FIXED": "win_fixed",
    # archiforge.stair
    "STRAIGHT": "stair",
    "L_SHAPED": "stair_l",
    "SPIRAL": "stair_spiral",
    "RAMP": "ramp",
    # archiforge.structure
    "FOOTING": "footing",
    "COLUMN": "column",
    "BEAM": "beam",
    "RIBBED_SLAB": "ribbed_slab",
    "GRID": "grid",
    "LEVELS": "levels",
    # archiforge.roof_add
    "GABLE": "roof_gable",
    "HIP": "roof_hip",
    "SHED": "roof_shed",
}


# Custom icon for each ArchiForge property group (object info, scene lists).
OBJECT_ICONS = {
    "archiforge_wall": "wall",
    "archiforge_floor": "floor",
    "archiforge_slab": "slab",
    "archiforge_stair": "stair",
    "archiforge_roof": "roof",
    "archiforge_door": "door",
    "archiforge_window": "window",
    "archiforge_fence": "fence",
    "archiforge_truss": "truss",
    "archiforge_bathroom": "bathroom",
    "archiforge_electrical": "electrical",
    "archiforge_furniture": "furniture",
    "archiforge_kitchen": "kitchen",
    "archiforge_decor": "decor",
    "archiforge_opening": "opening",
    "archiforge_structure": "structure",
    "archiforge_room_asset": "room_assets",
}


def _package_module():
    """The add-on package (``ArchiForge`` as legacy add-on,
    ``bl_ext.<repo>.archiforge`` as Blender 4.2+ extension)."""
    name = __package__ or ""
    return sys.modules.get(name) if name else None


def get_icons():
    """Preview collection loaded by the package, or an empty mapping."""
    getter = getattr(_package_module(), "get_icons", None)
    if getter is None:
        return {}
    try:
        return getter() or {}
    except Exception:  # noqa: BLE001 - never break a draw() over icons
        return {}


def icon_id(name, icons=None):
    """``icon_value`` of the custom icon ``name`` or 0 when unavailable."""
    if not name:
        return 0
    if icons is None:
        icons = get_icons()
    if name not in icons:
        return 0
    try:
        return int(icons[name].icon_id)
    except Exception:  # noqa: BLE001 - broken preview
        return 0


def icon_kw(name, fallback='MESH_CUBE', icons=None):
    """Keyword arguments for ``layout.operator/label/prop/menu``.

    Returns ``{'icon_value': id}`` when the custom icon is loaded and
    ``{'icon': fallback}`` otherwise (never ``icon_value=0``, which Blender
    rejects).
    """
    value = icon_id(name, icons)
    if value:
        return {'icon_value': value}
    return {'icon': fallback}


def item_icon(item_type, default=None):
    """Custom icon name for a catalogue ``item_type`` (or ``default``)."""
    return ITEM_ICONS.get(item_type, default)
