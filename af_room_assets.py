# -*- coding: utf-8 -*-
"""Parametric furniture, storage and decor catalog for five room types."""

import bpy
import math

from mathutils import Euler, Matrix, Vector
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)

from . import af_material
from .af_objects_base import AF_ObjectBuilder
from .af_room_assets_catalog import (
    ASSET_ENUM_ITEMS,
    ROOM_ENUM_ITEMS,
    assets_for_room,
    find_asset,
)

try:
    from .af_i18n import tr_report as _tr
except ImportError:  # pragma: no cover - fuera del paquete
    def _tr(text):
        return text

try:
    from .af_icons import icon_kw as _icon
except ImportError:  # pragma: no cover - fuera del paquete
    def _icon(name, fallback='MESH_CUBE', icons=None):
        return {'icon': fallback}


AF_ROOM_ASSET_PROP = "archiforge_room_asset"
AF_ROOM_ASSET_VERSION = 1
_QUALITY_FACTORS = {"LOW": 0.65, "MEDIUM": 1.0, "HIGH": 1.5}
_DRAWER_DEFAULTS = {
    "BED_NIGHTSTAND_DRAWERS": 2,
    "BED_DRESSER_LOW": 6,
    "BED_DRESSER_TALL": 5,
    "KIT_BASE_CABINET_DRAWERS": 3,
}
_SUSPEND = False


def _asset_items(self, context):
    return ASSET_ENUM_ITEMS.get(getattr(self, "room", "BEDROOM"), ())


def _set_dimensions(props, record):
    global _SUSPEND
    previous_suspend = _SUSPEND
    _SUSPEND = True
    try:
        props.width = record[5]
        props.depth = record[6]
        props.height = record[7]
    finally:
        _SUSPEND = previous_suspend


def _rebuild_room_asset_for_props(props, context):
    if _SUSPEND:
        return
    obj = _find_room_asset_object(props)
    if obj is None and context is not None:
        obj = getattr(context, "active_object", None)
    if (obj is None or obj.type != 'MESH'
            or not hasattr(obj, AF_ROOM_ASSET_PROP)):
        return
    stored = getattr(obj, AF_ROOM_ASSET_PROP, None)
    if stored is None or not stored.is_af_room_asset:
        return
    try:
        _rebuild_room_asset_mesh(obj, stored)
    except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError) as exc:
        print(f"[ArchiForge] Room asset update skipped: {exc}")


def _room_property_update(self, context):
    global _SUSPEND
    if _SUSPEND:
        return
    records = assets_for_room(self.room)
    valid_ids = {record[0] for record in records}
    if not records:
        return
    if self.asset_type not in valid_ids:
        _set_dimensions(self, records[0])
        previous_suspend = _SUSPEND
        _SUSPEND = True
        try:
            self.asset_type = records[0][0]
            self.drawer_count = _DRAWER_DEFAULTS.get(records[0][0], 3)
        finally:
            _SUSPEND = previous_suspend
    _rebuild_room_asset_for_props(self, context)


def _asset_property_update(self, context):
    global _SUSPEND
    if _SUSPEND:
        return
    record = find_asset(self.room, self.asset_type)
    if record is not None:
        _set_dimensions(self, record)
        previous_suspend = _SUSPEND
        _SUSPEND = True
        try:
            self.drawer_count = _DRAWER_DEFAULTS.get(self.asset_type, 3)
        finally:
            _SUSPEND = previous_suspend
    _rebuild_room_asset_for_props(self, context)


def _dimension_update(self, context):
    _rebuild_room_asset_for_props(self, context)


def _count_update(self, context):
    _rebuild_room_asset_for_props(self, context)


def _operator_room_update(self, context):
    records = assets_for_room(self.room)
    if not records:
        return
    valid_ids = {record[0] for record in records}
    if self.asset_type not in valid_ids:
        self.asset_type = records[0][0]
    if self.auto_dimensions:
        record = find_asset(self.room, self.asset_type)
        if record is not None:
            self.width, self.depth, self.height = record[5:8]


def _operator_asset_update(self, context):
    if not self.auto_dimensions:
        return
    record = find_asset(self.room, self.asset_type)
    if record is not None:
        self.width, self.depth, self.height = record[5:8]


def _operator_auto_update(self, context):
    if self.auto_dimensions:
        _operator_asset_update(self, context)


class AF_RoomAssetProperties(PropertyGroup):
    is_af_room_asset: BoolProperty(default=True, options={'HIDDEN'})
    object_name: StringProperty(default="", options={'HIDDEN'})
    af_version: IntProperty(default=AF_ROOM_ASSET_VERSION, options={'HIDDEN'})

    # Blender (3.3 and 4.2 alike) rejects a string ``default`` when ``items``
    # is a callback: the room list is static, so pass the tuple directly and
    # let the dynamic asset list fall back to its first entry.
    room: EnumProperty(
        name="Room",
        items=ROOM_ENUM_ITEMS,
        default="BEDROOM",
        update=_room_property_update,
    )
    asset_type: EnumProperty(
        name="Asset",
        items=_asset_items,
        update=_asset_property_update,
    )
    width: FloatProperty(
        name="Width", default=0.50, min=0.05, max=8.0,
        unit='LENGTH', update=_dimension_update,
    )
    depth: FloatProperty(
        name="Depth", default=0.42, min=0.05, max=8.0,
        unit='LENGTH', update=_dimension_update,
    )
    height: FloatProperty(
        name="Height", default=0.58, min=0.01, max=5.0,
        unit='LENGTH', update=_dimension_update,
    )
    mesh_quality: EnumProperty(
        name="Mesh Quality",
        items=(('LOW', "Low", "Fast preview"),
               ('MEDIUM', "Medium", "Balanced"),
               ('HIGH', "High", "More curved detail")),
        default="MEDIUM",
        update=_dimension_update,
    )
    drawer_count: IntProperty(
        name="Drawers", default=2, min=1, max=8, update=_count_update,
    )
    shelf_count: IntProperty(
        name="Shelves", default=4, min=1, max=8, update=_count_update,
    )
    decor_detail: BoolProperty(
        name="Include small decor", default=True, update=_dimension_update,
    )

    mat_wood: IntProperty(name="Wood / frame", default=0, min=0, max=3,
                          update=_dimension_update)
    mat_fabric: IntProperty(name="Fabric / ceramic", default=1, min=0, max=3,
                            update=_dimension_update)
    mat_metal: IntProperty(name="Metal / glass", default=2, min=0, max=3,
                           update=_dimension_update)
    mat_accent: IntProperty(name="Accent / foliage", default=3, min=0, max=3,
                            update=_dimension_update)


class AF_RoomAssetGenerator:
    """Build a single editable mesh for an individual item or coordinated set."""

    def __init__(self, props):
        self.props = props
        self.builder = AF_ObjectBuilder()
        self.b = self.builder.bm
        self.w = max(float(props.width), 0.05)
        self.d = max(float(props.depth), 0.05)
        self.h = max(float(props.height), 0.05)
        self.wood = props.mat_wood
        self.fabric = props.mat_fabric
        self.metal = props.mat_metal
        self.accent = props.mat_accent
        self.qf = _QUALITY_FACTORS.get(props.mesh_quality, 1.0)
        self.record = find_asset(props.room, props.asset_type)

    def _box(self, cx, cy, cz, sx, sy, sz, mi=None):
        sx, sy, sz = max(float(sx), 0.002), max(float(sy), 0.002), max(float(sz), 0.002)
        material = self.wood if mi is None else mi
        self.builder.box(
            cx - sx / 2, cx + sx / 2,
            cy - sy / 2, cy + sy / 2,
            cz - sz / 2, cz + sz / 2,
            material,
        )

    def _cylinder(self, cx, cy, z0, z1, radius, mi=None, segments=20):
        material = self.wood if mi is None else mi
        self.builder.cylinder(
            cx, cy, z0, max(z1, z0 + 0.002), max(radius, 0.002),
            segments=max(8, int(segments * self.qf)), mi=material,
        )

    def _disk(self, cx, cy, z0, z1, rx, ry, mi=None, segments=32):
        material = self.wood if mi is None else mi
        transform = Matrix.Translation(Vector((cx, cy, 0.0))) @ Matrix.Diagonal(
            Vector((max(rx, 0.002), max(ry, 0.002), 1.0, 1.0)))
        self.builder.cylinder(
            0.0, 0.0, z0, max(z1, z0 + 0.002), 1.0,
            segments=max(12, int(segments * self.qf)), mi=material,
            transform=transform,
        )

    def _sphere(self, cx, cy, cz, radius, mi=None):
        material = self.accent if mi is None else mi
        self.builder.sphere(
            cx, cy, cz, max(radius, 0.003),
            segments=max(8, int(18 * self.qf)),
            rings=max(6, int(12 * self.qf)), mi=material,
        )

    def _tube(self, start, end, radius, mi=None, segments=12):
        a, b = Vector(start), Vector(end)
        direction = b - a
        if direction.length < 1e-5:
            return
        axis = direction.normalized()
        if axis.dot(Vector((0.0, 0.0, 1.0))) < -0.9999:
            rotation = Matrix.Rotation(math.pi, 3, 'X')
        else:
            rotation = Vector((0.0, 0.0, 1.0)).rotation_difference(axis).to_matrix()
        transform = rotation.to_4x4()
        transform.translation = a
        material = self.metal if mi is None else mi
        self.builder.cylinder(
            0.0, 0.0, 0.0, direction.length, max(radius, 0.001),
            segments=max(6, int(segments * self.qf)), mi=material,
            transform=transform,
        )

    def _rotated_box(self, center, size, angles, mi=None):
        transform = Euler(angles, 'XYZ').to_matrix().to_4x4()
        transform.translation = Vector(center)
        sx, sy, sz = size
        self.builder.box(
            -sx / 2, sx / 2, -sy / 2, sy / 2, -sz / 2, sz / 2,
            self.wood if mi is None else mi, transform=transform,
        )

    def _table_top(self, cx, cy, z, width, depth, thickness, style,
                   mi=None):
        material = self.wood if mi is None else mi
        if style in {"round", "nightstand_round", "coffee_round", "breakfast_round"}:
            self._disk(cx, cy, z - thickness / 2, z + thickness / 2,
                       min(width, depth) * 0.5, min(width, depth) * 0.5,
                       material)
        elif style == "oval":
            self._disk(cx, cy, z - thickness / 2, z + thickness / 2,
                       width * 0.5, depth * 0.5, material)
        else:
            self._box(cx, cy, z, width, depth, thickness, material)

    def _draw_table(self, cx, cy, width, depth, height, style,
                    include_shelf=False):
        width, depth, height = max(width, 0.18), max(depth, 0.18), max(height, 0.20)
        top_t = max(0.025, min(0.07, height * 0.065))
        top_z = height - top_t / 2
        if style in {"nightstand_round", "coffee_round", "breakfast_round"}:
            self._table_top(cx, cy, top_z, width, depth, top_t, style)
            if style == "nightstand_round":
                self._cylinder(cx, cy, 0.08, height - top_t, min(width, depth) * 0.20)
                self._cylinder(cx, cy, 0.0, 0.09, min(width, depth) * 0.30, self.metal)
            else:
                self._cylinder(cx, cy, 0.08, height - top_t, min(width, depth) * 0.09)
                self._disk(cx, cy, 0.035, 0.075, width * 0.23, depth * 0.23, self.wood)
            return

        if style == "kitchen_island":
            body_h = height * 0.82
            self._box(cx, cy, body_h / 2, width * 0.86, depth * 0.80, body_h)
            self._box(cx, cy - depth * 0.42, body_h * 0.52,
                      width * 0.82, 0.018, body_h * 0.74, self.fabric)
            for index in range(3):
                x = cx - width * 0.28 + index * width * 0.28
                self._box(x, cy - depth * 0.42 - 0.014,
                          body_h * 0.20, width * 0.18, 0.012, 0.012,
                          self.metal)
            self._box(cx, cy, height - top_t / 2, width, depth, top_t, self.accent)
            if self.props.decor_detail:
                for x in (-width * 0.24, width * 0.24):
                    self._cylinder(cx + x, cy + depth * 0.10,
                                   height - top_t, height - top_t + 0.014,
                                   0.055, self.metal, 20)
            return

        if style == "rolling_cart":
            for z in (height * 0.34, height * 0.78):
                self._box(cx, cy, z, width * 0.88, depth * 0.82, 0.035)
            for sx in (-1, 1):
                for sy in (-1, 1):
                    x = cx + sx * width * 0.42
                    y = cy + sy * depth * 0.38
                    self._tube((x, y, 0.10), (x, y, height * 0.94), 0.018)
                    self._cylinder(x, y, 0.015, 0.065, 0.035, self.metal, 14)
            self._table_top(cx, cy, top_z, width, depth, top_t, "rect")
            self._tube((cx - width * 0.35, cy + depth * 0.36, height * 0.87),
                       (cx + width * 0.35, cy + depth * 0.36, height * 0.87),
                       0.014)
            return

        if style == "breakfast_bar":
            self._table_top(cx, cy, top_z, width, depth, top_t, "rect", self.accent)
            for sx in (-1, 1):
                self._box(cx + sx * width * 0.38, cy, (height - top_t) / 2,
                          0.065, depth * 0.80, height - top_t)
            self._tube((cx - width * 0.32, cy - depth * 0.32, 0.30),
                       (cx + width * 0.32, cy - depth * 0.32, 0.30), 0.016)
            return

        # Rectangular, console, coffee, nesting, dining and patio tables.
        top_width, top_depth = width, depth
        self._table_top(cx, cy, top_z, top_width, top_depth, top_t,
                        "oval" if style == "oval" else "rect")
        leg_h = height - top_t
        if style == "sofa_console":
            leg_x = width * 0.42
            leg_y = depth * 0.36
            for sx in (-1, 1):
                self._box(cx + sx * leg_x, cy, leg_h / 2,
                          0.045, 0.055, leg_h)
            self._box(cx, cy, height * 0.28, width * 0.86,
                      depth * 0.72, 0.028)
        elif style == "console_table":
            for sx in (-1, 1):
                self._box(cx + sx * width * 0.42, cy, leg_h / 2,
                          0.055, depth * 0.75, leg_h)
            self._box(cx, cy, height * 0.35, width * 0.78, 0.035, 0.035)
        else:
            for sx in (-1, 1):
                for sy in (-1, 1):
                    self._box(cx + sx * width * 0.42,
                              cy + sy * depth * 0.39, leg_h / 2,
                              max(0.045, width * 0.055),
                              max(0.045, depth * 0.055), leg_h)
        if include_shelf or style == "coffee_rect":
            self._box(cx, cy, max(0.11, height * 0.32),
                      width * 0.80, depth * 0.72, 0.025, self.accent)
        if style in {"nesting", "nesting_set"}:
            self._draw_table(cx + width * 0.19, cy + depth * 0.12,
                             width * 0.64, depth * 0.62, height * 0.76,
                             "end_table")
            self._draw_table(cx - width * 0.19, cy - depth * 0.12,
                             width * 0.48, depth * 0.46, height * 0.58,
                             "end_table")
        if style == "vanity_desk":
            self._box(cx, cy - depth * 0.36, height * 0.67,
                      width * 0.42, 0.025, height * 0.18, self.wood)
            self._box(cx, cy + depth * 0.42, height * 0.73,
                      width * 0.52, 0.035, height * 0.36, self.metal)
            self._box(cx, cy + depth * 0.39, height * 0.75,
                      width * 0.45, 0.012, height * 0.27, self.accent)
            if self.props.decor_detail:
                self._sphere(cx, cy + depth * 0.33, height * 0.90, 0.018, self.metal)

    def _build_table(self, style):
        self._draw_table(0.0, 0.0, self.w, self.d, self.h, style,
                         include_shelf=style in {"coffee_rect", "end_table"})

    def _build_bed(self, style):
        width, length, height = self.w, self.d, self.h
        frame_h = min(0.32, height * 0.28)
        mattress_h = min(0.28, height * 0.24)
        headboard_h = max(height * 0.72, 0.78)
        y_head, y_foot = length * 0.45, -length * 0.48
        self._box(0, 0, frame_h / 2, width, length, frame_h)
        self._box(0, 0, frame_h + mattress_h / 2,
                  width * 0.94, length * 0.94, mattress_h, self.fabric)
        self._box(0, -length * 0.08, frame_h + mattress_h + 0.025,
                  width * 0.92, length * 0.54, 0.045, self.accent)
        self._box(0, y_head, headboard_h / 2, width * 1.03, 0.10,
                  headboard_h, self.fabric if style != "canopy" else self.wood)
        for side in (-1, 1):
            pillow_x = side * width * 0.23
            self._box(pillow_x, length * 0.30, frame_h + mattress_h + 0.075,
                      width * 0.40, length * 0.16, 0.10, self.fabric)
        if style == "canopy":
            post_h = max(0.25, height - 0.10)
            for sx in (-1, 1):
                for sy in (-1, 1):
                    x, y = sx * width * 0.47, sy * length * 0.46
                    self._box(x, y, post_h / 2, 0.055, 0.055, post_h, self.wood)
            for sy in (-1, 1):
                self._box(0, sy * length * 0.46, post_h,
                          width * 0.96, 0.055, 0.055, self.wood)
            for sx in (-1, 1):
                self._box(sx * width * 0.47, 0, post_h,
                          0.055, length * 0.92, 0.055, self.wood)
        if self.props.decor_detail:
            self._box(0, y_foot + 0.16, frame_h + mattress_h + 0.08,
                      width * 0.94, length * 0.13, 0.035, self.fabric)

    def _build_headboard(self, style):
        self._box(0, 0, self.h * 0.52, self.w, self.d, self.h, self.fabric)
        if style == "slatted":
            for index in range(6):
                z = self.h * (0.16 + index * 0.14)
                self._box(0, -self.d * 0.53, z,
                          self.w * 0.92, self.d * 0.12, self.h * 0.055,
                          self.wood)
        else:
            self._box(0, -self.d * 0.54, self.h * 0.54,
                      self.w * 0.88, self.d * 0.04, self.h * 0.78,
                      self.fabric)
            for row in range(3):
                columns = max(2, int(self.w / 0.32))
                for col in range(columns):
                    x = -self.w * 0.38 + col * (
                        self.w * 0.76 / max(1, columns - 1))
                    z = self.h * (0.25 + row * 0.23)
                    self._sphere(x, -self.d * 0.57, z,
                                 0.016, self.accent)

    def _build_sofa(self, style):
        width, depth, height = self.w, self.d, self.h
        seat_h = min(0.46, height * 0.50)
        arm_w = min(0.18, width * 0.12)
        back_h = max(0.30, height - seat_h)
        seats = {"loveseat": 2, "three_seat": 3, "four_seat": 4,
                 "sectional": 3, "outdoor_sofa": 2}.get(style, 3)
        self._box(0, 0, 0.14, width * 0.92, depth * 0.92, 0.28, self.wood)
        self._box(0, -depth * 0.025, seat_h, width - arm_w * 1.3,
                  depth * 0.77, 0.20, self.fabric)
        for index in range(seats):
            x = -width * 0.34 + index * (width * 0.68 / max(1, seats - 1))
            self._box(x, -depth * 0.025, seat_h + 0.105,
                      width * 0.68 / seats, depth * 0.68, 0.13, self.fabric)
            self._box(x, depth * 0.34, seat_h + back_h * 0.48,
                      width * 0.68 / seats, depth * 0.18,
                      back_h * 0.92, self.fabric)
        for sx in (-1, 1):
            x = sx * (width / 2 - arm_w / 2)
            self._box(x, 0, seat_h + back_h * 0.20,
                      arm_w, depth * 0.90, back_h * 0.62, self.fabric)
            self._box(x, 0, seat_h + back_h * 0.52,
                      arm_w * 1.04, depth * 0.82, 0.07, self.fabric)
        if style == "sectional":
            chaise_w, chaise_d = width * 0.40, depth * 0.48
            self._box(-width * 0.27, -depth * 0.62, 0.14,
                      chaise_w, chaise_d, 0.28, self.wood)
            self._box(-width * 0.27, -depth * 0.62, seat_h,
                      chaise_w, chaise_d, 0.20, self.fabric)
            self._box(-width * 0.27, -depth * 0.46, seat_h + back_h * 0.45,
                      chaise_w, 0.16, back_h * 0.86, self.fabric)
        for sx in (-1, 1):
            for sy in (-1, 1):
                self._box(sx * width * 0.40, sy * depth * 0.39,
                          0.07, 0.06, 0.06, 0.14, self.metal)

    def _build_seat(self, style):
        width, depth, height = self.w, self.d, self.h
        if style in {"ottoman", "round_pouf"}:
            if style == "round_pouf":
                self._cylinder(0, 0, 0.04, height * 0.78,
                               min(width, depth) * 0.48, self.fabric, 32)
                self._disk(0, 0, height * 0.74, height * 0.80,
                           width * 0.46, depth * 0.46, self.fabric)
            else:
                self._box(0, 0, height * 0.46, width * 0.92,
                          depth * 0.90, height * 0.78, self.fabric)
                for sx in (-1, 1):
                    for sy in (-1, 1):
                        self._box(sx * width * 0.39, sy * depth * 0.38,
                                  height * 0.10, 0.045, 0.045,
                                  height * 0.20, self.wood)
            return

        if style in {"bed_bench", "bath_bench", "banquette", "garden_bench"}:
            seat_z = height * 0.50
            if style == "banquette":
                self._box(0, depth * 0.12, height * 0.32,
                          width * 0.94, depth * 0.88, height * 0.58, self.wood)
                self._box(0, depth * 0.48, height * 0.68,
                          width * 0.94, depth * 0.12, height * 0.48,
                          self.fabric)
            else:
                self._box(0, 0, seat_z, width * 0.94, depth * 0.86,
                          max(0.06, height * 0.18),
                          self.fabric if style == "bed_bench" else self.wood)
                for sx in (-1, 1):
                    for sy in (-1, 1):
                        self._box(sx * width * 0.40, sy * depth * 0.35,
                                  seat_z / 2, 0.055, 0.055, seat_z,
                                  self.metal if style == "bath_bench" else self.wood)
                if style == "garden_bench":
                    self._box(0, depth * 0.37, height * 0.78,
                              width * 0.94, 0.055, height * 0.40, self.wood)
                    for index in range(4):
                        self._box(-width * 0.36 + index * width * 0.24,
                                  depth * 0.33, height * 0.78,
                                  0.035, 0.075, height * 0.36, self.wood)
            return

        if style == "sun_lounger":
            self._rotated_box((0, -depth * 0.08, height * 0.66),
                              (width * 0.88, depth * 0.60, 0.10),
                              (math.radians(-12), 0, 0), self.fabric)
            self._rotated_box((0, depth * 0.25, height * 0.68),
                              (width * 0.88, depth * 0.48, 0.10),
                              (math.radians(18), 0, 0), self.fabric)
            for sx in (-1, 1):
                self._tube((sx * width * 0.38, -depth * 0.36, 0.18),
                           (sx * width * 0.38, depth * 0.34, 0.18), 0.025)
            return

        if style in {"vanity_stool", "bath_stool"}:
            seat_z = height * 0.78
            seat_material = self.fabric if style == "vanity_stool" else self.wood
            self._box(0, 0, seat_z, width * 0.90, depth * 0.86,
                      height * 0.16, seat_material)
            for sx in (-1, 1):
                for sy in (-1, 1):
                    self._tube((sx * width * 0.34, sy * depth * 0.30, 0.02),
                               (sx * width * 0.27, sy * depth * 0.23, seat_z - 0.05),
                               0.018, self.metal if style == "bath_stool" else self.wood)
            self._tube((-width * 0.27, -depth * 0.20, seat_z * 0.42),
                       (width * 0.27, -depth * 0.20, seat_z * 0.42),
                       0.012, self.metal)
            self._tube((-width * 0.27, depth * 0.20, seat_z * 0.42),
                       (width * 0.27, depth * 0.20, seat_z * 0.42),
                       0.012, self.metal)
            return

        seat_z = max(0.38, height * 0.52)
        is_bar = style == "bar_stool"
        self._box(0, 0, seat_z, width * 0.86, depth * 0.78, 0.09,
                  self.fabric if style != "patio_chair" else self.wood)
        if is_bar:
            for sx in (-1, 1):
                for sy in (-1, 1):
                    self._tube((sx * width * 0.34, sy * depth * 0.30, 0.04),
                               (sx * width * 0.27, sy * depth * 0.24, seat_z),
                               0.022, self.metal)
            self._tube((-width * 0.25, 0, seat_z * 0.48),
                       (width * 0.25, 0, seat_z * 0.48), 0.014)
            return

        for sx in (-1, 1):
            for sy in (-1, 1):
                leg_mi = self.wood if style == "patio_chair" else self.metal
                self._tube((sx * width * 0.34, sy * depth * 0.31, 0.02),
                           (sx * width * 0.30, sy * depth * 0.27, seat_z - 0.03),
                           0.020, leg_mi)
        back_y = depth * 0.35
        self._box(0, back_y, seat_z + (height - seat_z) * 0.48,
                  width * 0.82, 0.075, height - seat_z, self.fabric)
        if style in {"club_chair", "accent_chair", "patio_chair"}:
            for sx in (-1, 1):
                self._box(sx * width * 0.43, -depth * 0.01,
                          seat_z + 0.17, width * 0.12, depth * 0.85,
                          0.30, self.fabric if style != "patio_chair" else self.wood)
        if style == "patio_chair":
            for index in range(4):
                self._box(0, back_y - 0.045,
                          seat_z + 0.12 + index * 0.11,
                          width * 0.78, 0.025, 0.035, self.accent)

    def _draw_chair(self, cx, cy, width, depth, height, style="patio_chair"):
        seat_z = height * 0.52
        seat_material = self.wood if style == "patio_chair" else self.fabric
        self._box(cx, cy, seat_z, width * 0.86, depth * 0.78,
                  0.075, seat_material)
        for sx in (-1, 1):
            for sy in (-1, 1):
                self._tube((cx + sx * width * 0.34,
                            cy + sy * depth * 0.30, 0.02),
                           (cx + sx * width * 0.30,
                            cy + sy * depth * 0.27, seat_z - 0.03),
                           0.018, self.wood if style == "patio_chair" else self.metal)
        back_y = cy + depth * 0.34
        self._box(cx, back_y, seat_z + (height - seat_z) * 0.48,
                  width * 0.80, 0.06, height - seat_z,
                  self.wood if style == "patio_chair" else self.fabric)
        if style == "patio_chair":
            for index in range(4):
                z = seat_z + 0.10 + index * (height - seat_z - 0.14) / 3
                self._box(cx, back_y - 0.04, z, width * 0.76,
                          0.022, 0.035, self.accent)

    def _build_shelf(self, style):
        width, depth, height = self.w, self.d, self.h
        shelves = max(2, min(self.props.shelf_count, 8))
        if style == "floating_shelves":
            for index in range(3):
                z = height * (0.18 + index * 0.30)
                shelf_w = width * (1.0 - index * 0.12)
                self._box(0, 0, z, shelf_w, depth, 0.045, self.wood)
                for sx in (-1, 1):
                    self._box(sx * shelf_w * 0.35, depth * 0.36,
                              z - 0.055, 0.035, depth * 0.30, 0.11,
                              self.metal)
            return
        if style in {"ladder_shelf", "blanket_ladder", "towel_ladder"}:
            lean = depth * (0.18 if style == "ladder_shelf" else 0.04)
            for sx in (-1, 1):
                self._tube((sx * width * 0.42, -lean, 0.04),
                           (sx * width * 0.30, lean, height),
                           0.035, self.wood)
            levels = 5 if style != "blanket_ladder" else 4
            for index in range(levels):
                z = height * (0.18 + index * 0.18)
                y = -lean + (2 * lean) * z / max(height, 0.01)
                self._box(0, y, z, width * (0.82 - index * 0.045),
                          depth * (0.52 if style == "ladder_shelf" else 0.30),
                          0.035, self.wood)
            if style == "blanket_ladder":
                for index in range(3):
                    z = height * (0.36 + index * 0.20)
                    self._box(0, lean * 0.65, z, width * 0.76,
                              0.025, 0.035, self.fabric)
            return
        if style == "pot_rail":
            self._tube((-width * 0.45, 0, height * 0.60),
                       (width * 0.45, 0, height * 0.60), 0.018)
            for index in range(5):
                x = -width * 0.34 + index * width * 0.17
                self._tube((x, 0, height * 0.59), (x, 0, height * 0.44), 0.008)
                self._cylinder(x, 0, height * 0.25, height * 0.42,
                               width * 0.055, self.metal, 18)
                self._disk(x, 0, height * 0.25, height * 0.27,
                           width * 0.065, depth * 0.15, self.wood, 20)
            return
        if style == "trellis":
            for sx in (-1, 1):
                self._box(sx * width * 0.46, 0, height / 2,
                          0.045, depth * 0.40, height, self.wood)
            for index in range(7):
                z = height * (0.10 + index * 0.13)
                self._box(0, 0, z, width * 0.95, depth * 0.34,
                          0.035, self.wood)
            for index in range(5):
                x = -width * 0.38 + index * width * 0.19
                self._box(x, -depth * 0.05, height / 2,
                          0.025, depth * 0.30, height * 0.92,
                          self.accent)
            return
        if style == "shower_niche":
            self._box(0, 0, height / 2, width, depth, height, self.wood)
            self._box(0, -depth * 0.52, height / 2,
                      width * 0.88, depth * 0.10, height * 0.82,
                      self.fabric)
            for index in range(2):
                self._box(0, -depth * 0.44, height * (0.34 + index * 0.30),
                          width * 0.82, depth * 0.22, 0.025, self.wood)
            if self.props.decor_detail:
                for sx in (-1, 1):
                    self._cylinder(sx * width * 0.27, -depth * 0.25,
                                   height * 0.38, height * 0.66,
                                   width * 0.065, self.accent, 16)
            return
        if style == "shower_caddy":
            self._tube((0, 0, 0.02), (0, 0, height), 0.020)
            for index in range(3):
                z = height * (0.28 + index * 0.25)
                self._box(0, -depth * 0.08, z, width, depth * 0.82,
                          0.028, self.metal)
                for sx in (-1, 1):
                    self._box(sx * width * 0.47, 0, z + 0.045,
                              0.025, depth * 0.82, 0.12, self.metal)
            return
        if style in {"spice_rack", "plate_rack", "wine_rack", "pantry_shelf"}:
            self._box(0, depth * 0.40, height / 2,
                      width, 0.025, height, self.wood)
            count = 3 if style == "plate_rack" else shelves
            for index in range(count):
                z = height * (0.16 + index * 0.72 / max(count - 1, 1))
                self._box(0, 0, z, width * 0.92, depth * 0.82,
                          0.035, self.wood)
            if style == "wine_rack":
                for row in range(3):
                    z = height * (0.28 + row * 0.25)
                    for col in range(3):
                        x = -width * 0.30 + col * width * 0.30
                        self._cylinder(x, -depth * 0.06, z, z + height * 0.18,
                                       width * 0.045, self.accent, 12)
            elif style == "spice_rack":
                for index in range(6):
                    x = -width * 0.38 + index * width * 0.15
                    self._cylinder(x, -depth * 0.12, height * 0.58,
                                   height * 0.81, width * 0.045,
                                   self.accent, 12)
            elif style == "plate_rack":
                for index in range(6):
                    x = -width * 0.36 + index * width * 0.14
                    self._box(x, -depth * 0.18, height * 0.55,
                              0.018, depth * 0.48, height * 0.60,
                              self.metal)
            return
        if style == "cube_divider":
            cols, rows = 3, 3
            self._box(0, depth * 0.44, height / 2, width, 0.025, height,
                      self.wood)
            for index in range(cols + 1):
                x = -width / 2 + index * width / cols
                self._box(x, 0, height / 2, 0.04, depth, height,
                          self.wood)
            for index in range(rows + 1):
                z = index * height / rows
                self._box(0, 0, z, width, depth, 0.04, self.wood)
            return
        if style == "bath_shelves":
            for index in range(2):
                z = height * (0.28 + index * 0.52)
                self._box(0, 0, z, width, depth, 0.045, self.wood)
                for sx in (-1, 1):
                    self._box(sx * width * 0.38, depth * 0.30,
                              z - 0.05, 0.035, depth * 0.30, 0.10,
                              self.metal)
            return
        if style == "bookcase":
            self._box(-width * 0.47, 0, height / 2, width * 0.06,
                      depth, height, self.wood)
            self._box(width * 0.47, 0, height / 2, width * 0.06,
                      depth, height, self.wood)
            self._box(0, depth * 0.46, height / 2, width * 0.90,
                      depth * 0.08, height, self.accent)
            self._box(0, 0, height * 0.04, width, depth, 0.08, self.wood)
            self._box(0, 0, height * 0.96, width, depth, 0.08, self.wood)
            for index in range(1, shelves):
                z = height * index / shelves
                self._box(0, 0, z, width * 0.90, depth * 0.88,
                          0.035, self.wood)
            if self.props.decor_detail:
                for index in range(min(6, shelves + 1)):
                    x = -width * 0.34 + (index % 3) * width * 0.30
                    z = height * (0.16 + (index // 3) * 0.44)
                    self._box(x, -depth * 0.12, z, width * 0.14,
                              depth * 0.30, height * 0.12,
                              self.fabric if index % 2 else self.accent)
            return
        # Default open shelving / pantry rack.
        for sx in (-1, 1):
            self._box(sx * width * 0.46, 0, height / 2,
                      width * 0.06, depth, height, self.wood)
        for index in range(shelves):
            z = height * (index + 0.5) / shelves
            self._box(0, 0, z, width * 0.92, depth * 0.88,
                      max(0.025, height * 0.025), self.wood)

    def _build_cabinet(self, style):
        width, depth, height = self.w, self.d, self.h
        face_y = -depth / 2 - 0.012
        if style in {"wardrobe_hinged", "wardrobe_sliding", "wardrobe_open"}:
            self._box(0, 0, height / 2, width, depth, height, self.wood)
            self._box(0, depth * 0.48, height / 2, width * 0.92,
                      0.035, height * 0.92, self.accent)
            if style == "wardrobe_open":
                self._box(0, 0, height * 0.72, width * 0.90,
                          depth * 0.86, 0.045, self.wood)
                self._tube((-width * 0.37, 0, height * 0.72),
                           (width * 0.37, 0, height * 0.72), 0.018)
                for index in range(5):
                    x = -width * 0.30 + index * width * 0.15
                    self._box(x, face_y, height * 0.52,
                              width * 0.10, 0.035, height * 0.28,
                              self.fabric if index % 2 else self.accent)
                return
            if style == "wardrobe_sliding":
                self._box(-width * 0.24, face_y, height / 2,
                          width * 0.52, 0.035, height * 0.96, self.fabric)
                self._box(width * 0.24, face_y - 0.04, height / 2,
                          width * 0.52, 0.035, height * 0.96, self.wood)
                self._box(0, face_y - 0.055, height * 0.96,
                          width * 1.02, 0.035, 0.035, self.metal)
            else:
                for sx in (-1, 1):
                    self._box(sx * width * 0.25, face_y, height / 2,
                              width * 0.49, 0.035, height * 0.96,
                              self.fabric)
                    self._cylinder(sx * width * 0.04, face_y - 0.03,
                                   height * 0.45, height * 0.55,
                                   0.012, self.metal, 12)
            self._box(0, 0, height * 0.80, width * 0.88,
                      depth * 0.88, 0.04, self.wood)
            self._tube((-width * 0.36, 0, height * 0.79),
                       (width * 0.36, 0, height * 0.79), 0.018)
            return

        if style == "tv_console":
            body_h = height * 0.76
            self._box(0, 0, body_h / 2, width, depth, body_h, self.wood)
            self._box(0, 0, height * 0.94, width * 1.04,
                      depth * 1.04, height * 0.10, self.accent)
            for index in range(1, 3):
                x = -width / 2 + index * width / 3
                self._box(x, 0, body_h * 0.52, 0.035,
                          depth * 0.84, body_h * 0.76, self.wood)
            for index in range(3):
                x = -width / 3 + index * width / 3
                self._box(x, face_y, body_h * 0.54,
                          width * 0.27, 0.025, body_h * 0.72,
                          self.fabric if index != 1 else self.accent)
            for sx in (-1, 1):
                self._box(sx * width * 0.39, depth * 0.35,
                          0.06, 0.055, 0.055, 0.12, self.metal)
            return

        if style == "medicine_cabinet":
            self._box(0, 0, height / 2, width, depth, height, self.wood)
            self._box(0, face_y, height / 2, width * 0.94,
                      0.025, height * 0.94, self.metal)
            for z in (height * 0.35, height * 0.67):
                self._box(0, depth * 0.05, z, width * 0.88,
                          depth * 0.80, 0.025, self.wood)
            return

        if style in {"dresser_low", "dresser_tall", "kitchen_drawers",
                     "nightstand_drawers"}:
            self._box(0, 0, height / 2, width, depth, height * 0.94, self.wood)
            count = max(1, min(self.props.drawer_count, 8))
            if style == "dresser_low":
                cols = 3 if width > 1.0 else 2
            else:
                cols = 1
            rows = max(1, math.ceil(count / cols))
            drawer_h = height * 0.88 / rows
            for row in range(rows):
                for col in range(cols):
                    if row * cols + col >= count:
                        continue
                    x = -width / 2 + width * (col + 0.5) / cols
                    z = height * 0.08 + drawer_h * (row + 0.5)
                    self._box(x, face_y, z, width / cols - 0.035,
                              0.035, drawer_h - 0.025, self.fabric)
                    self._box(x, face_y - 0.025, z, min(width * 0.12, 0.12),
                              0.018, 0.018, self.metal)
            self._box(0, 0, height * 0.98, width * 1.04,
                      depth * 1.04, 0.04, self.accent)
            return

        if style in {"floating_nightstand", "nightstand_cubby"}:
            body_h = height * (0.82 if style != "floating_nightstand" else 0.88)
            body_z = height * (0.08 if style != "floating_nightstand" else 0.08)
            self._box(0, 0, body_z + body_h / 2, width, depth, body_h, self.wood)
            self._box(0, 0, height * 0.96, width * 1.06,
                      depth * 1.06, 0.05, self.accent)
            if style == "nightstand_cubby":
                self._box(0, face_y, height * 0.70, width * 0.91,
                          0.03, height * 0.30, self.fabric)
                self._box(0, 0, height * 0.43, width * 0.88,
                          depth * 0.86, 0.035, self.accent)
            else:
                rows = 1 if style == "floating_nightstand" else 2
                for row in range(rows):
                    z = height * (0.31 + row * 0.30)
                    self._box(0, face_y, z, width * 0.90, 0.035,
                              height * 0.24, self.fabric)
                    self._box(0, face_y - 0.025, z,
                              width * 0.12, 0.018, 0.018, self.metal)
            if style == "floating_nightstand":
                for sx in (-1, 1):
                    self._box(sx * width * 0.35, depth * 0.44,
                              body_z + body_h * 0.48, 0.035,
                              depth * 0.20, body_h * 0.74, self.metal)
            return

        if style in {"kitchen_wall", "kitchen_glass_wall"}:
            self._box(0, 0, height / 2, width, depth, height, self.wood)
            self._box(0, face_y, height / 2, width * 0.95,
                      0.035, height * 0.92,
                      self.metal if style == "kitchen_glass_wall" else self.fabric)
            for sx in (-1, 1):
                self._box(sx * width * 0.25, face_y - 0.025,
                          height * 0.50, width * 0.48, 0.025,
                          height * 0.88,
                          self.accent if style == "kitchen_glass_wall" else self.fabric)
            self._box(0, 0, height * 0.52, width * 0.90,
                      depth * 0.82, 0.035, self.wood)
            return

        if style == "corner_cabinet":
            self._box(0, 0, height / 2, width * 0.96,
                      depth * 0.96, height, self.wood)
            self._box(0, -depth * 0.51, height / 2,
                      width * 0.92, 0.035, height * 0.92, self.fabric)
            for z in (height * 0.32, height * 0.63):
                self._disk(0, 0, z - 0.018, z + 0.018,
                           width * 0.42, depth * 0.42, self.accent, 24)
            return

        if style in {"bath_vanity_single", "bath_vanity_double"}:
            self._box(0, 0, height * 0.28, width, depth * 0.55,
                      height * 0.48, self.wood)
            self._box(0, 0, height * 0.53, width * 1.04,
                      depth * 1.04, 0.055, self.accent)
            columns = 2 if style == "bath_vanity_double" else 2
            for index in range(columns):
                x = -width * 0.25 + index * width * 0.50
                if style == "bath_vanity_single":
                    x = 0.0
                self._disk(x, 0, height * 0.54, height * 0.58,
                           min(width * 0.18, 0.19), min(depth * 0.20, 0.18),
                           self.fabric, 28)
                self._cylinder(x, 0, height * 0.54, height * 0.57,
                               0.025, self.metal, 14)
            for row in range(2):
                z = height * (0.17 + row * 0.20)
                self._box(0, face_y, z, width * 0.92, 0.03,
                          height * 0.16, self.fabric)
                self._box(0, face_y - 0.025, z, width * 0.13,
                          0.018, 0.018, self.metal)
            if self.props.decor_detail:
                mirror_h = height * 0.36
                self._box(0, depth * 0.46, height * 0.81,
                          width * 0.72, 0.035, mirror_h, self.metal)
                self._box(0, depth * 0.435, height * 0.81,
                          width * 0.66, 0.012, mirror_h * 0.90, self.accent)
            return

        if style == "deck_box":
            self._box(0, 0, height * 0.43, width, depth, height * 0.82,
                      self.wood)
            self._box(0, 0, height * 0.88, width * 1.03,
                      depth * 1.03, height * 0.12, self.accent)
            for sx in (-1, 1):
                self._box(sx * width * 0.40, 0, height * 0.91,
                          0.025, depth * 0.55, 0.025, self.metal)
            return

        # General cupboards: kitchen base, pantry, display cabinet and linen tower.
        self._box(0, 0, height / 2, width, depth, height, self.wood)
        self._box(0, face_y, height / 2, width * 0.94,
                  0.035, height * 0.94,
                  self.metal if style == "display_cabinet" else self.fabric)
        if style in {"kitchen_base_doors", "kitchen_pantry", "linen_tower",
                     "display_cabinet"}:
            door_cols = 1 if style in {"kitchen_pantry", "linen_tower"} else 2
            for col in range(door_cols):
                x = -width * 0.24 + col * width * 0.48
                if door_cols == 1:
                    x = 0.0
                self._box(x, face_y - 0.022, height * 0.50,
                          width / door_cols * 0.92, 0.025,
                          height * 0.92, self.accent if style == "display_cabinet" else self.fabric)
                self._cylinder(x + width * 0.13, face_y - 0.045,
                               height * 0.46, height * 0.56,
                               0.012, self.metal, 12)
        if style == "display_cabinet":
            for index in range(1, 4):
                self._box(0, 0, height * index / 4,
                          width * 0.88, depth * 0.84, 0.025, self.wood)
        else:
            shelves = max(2, min(self.props.shelf_count, 8))
            for index in range(1, shelves):
                self._box(0, depth * 0.08,
                          height * index / shelves,
                          width * 0.88, depth * 0.82, 0.03, self.accent)
        if style == "kitchen_base_doors":
            self._box(0, 0, height * 0.98, width * 1.06,
                      depth * 1.06, 0.045, self.accent)

    def _build_accessory(self, style):
        width, depth, height = self.w, self.d, self.h
        if style in {"hamper", "bath_hamper"}:
            self._box(0, 0, height * 0.46, width * 0.86,
                      depth * 0.86, height * 0.84, self.fabric)
            self._box(0, 0, height * 0.90, width * 0.94,
                      depth * 0.94, 0.05, self.wood)
            for sx in (-1, 1):
                self._box(sx * width * 0.38, 0, height * 0.48,
                          0.035, depth * 0.045, height * 0.58, self.accent)
            return
        if style == "full_mirror":
            self._box(0, 0, height / 2, width, depth * 0.36,
                      height * 0.94, self.wood)
            self._box(0, -depth * 0.20, height / 2,
                      width * 0.84, depth * 0.08, height * 0.88,
                      self.metal)
            for sx in (-1, 1):
                self._box(sx * width * 0.35, depth * 0.18,
                          height * 0.27, 0.035, depth * 0.38,
                          height * 0.40, self.wood)
            return
        if style == "paper_holder":
            self._box(0, 0, height * 0.70, width, depth * 0.55,
                      height * 0.16, self.accent)
            self._tube((-width * 0.34, 0, height * 0.34),
                       (width * 0.34, 0, height * 0.34), 0.012)
            self._cylinder(0, 0, height * 0.22, height * 0.45,
                           depth * 0.20, self.fabric, 18)
            return
        self._box(0, 0, height / 2, width, depth, height, self.accent)

    def _build_set(self, style):
        width, depth, height = self.w, self.d, self.h
        if style == "bedside_lamps":
            for sx in (-1, 1):
                x = sx * width * 0.31
                self._cylinder(x, 0, 0.02, height * 0.12,
                               width * 0.13, self.wood)
                self._cylinder(x, 0, height * 0.12, height * 0.72,
                               width * 0.035, self.metal)
                self._cylinder(x, 0, height * 0.64, height * 0.96,
                               width * 0.15, self.fabric, 20)
                self._sphere(x, 0, height * 0.70, width * 0.045, self.accent)
            return
        if style == "living_decor":
            self._box(0, 0, 0.015, width, depth, 0.025, self.fabric)
            for sx in (-1, 1):
                x = sx * width * 0.37
                self._cylinder(x, 0, 0.03, 0.34, width * 0.085, self.accent)
                self._cylinder(x, 0, 0.30, 0.34, width * 0.09, self.wood)
                for index in range(5):
                    angle = index * math.tau / 5
                    self._sphere(x + math.cos(angle) * width * 0.07,
                                 math.sin(angle) * width * 0.07,
                                 0.55 + 0.08 * (index % 2),
                                 width * 0.075, self.accent)
            return
        if style == "recycle_bins":
            for index, sx in enumerate((-1, 1)):
                x = sx * width * 0.23
                self._box(x, 0, height * 0.45, width * 0.40,
                          depth * 0.82, height * 0.86,
                          self.fabric if index == 0 else self.accent)
                self._box(x, 0, height * 0.90, width * 0.43,
                          depth * 0.86, height * 0.10, self.wood)
                self._box(x, -depth * 0.42, height * 0.52,
                          width * 0.25, 0.012, height * 0.18, self.metal)
            return
        if style == "coffee_station":
            self._box(0, 0, 0.035, width, depth, 0.07, self.wood)
            self._box(-width * 0.22, 0, height * 0.50,
                      width * 0.44, depth * 0.58, height * 0.62, self.metal)
            self._box(-width * 0.22, -depth * 0.31, height * 0.52,
                      width * 0.36, 0.018, height * 0.32, self.accent)
            self._cylinder(-width * 0.22, -depth * 0.33,
                           height * 0.12, height * 0.38,
                           width * 0.07, self.wood)
            for index in range(3):
                x = width * (0.07 + index * 0.18)
                self._cylinder(x, 0, height * 0.14, height * 0.48,
                               width * 0.055, self.fabric, 14)
                self._cylinder(x, 0, height * 0.47, height * 0.51,
                               width * 0.058, self.metal, 14)
            return
        if style == "kitchen_prep":
            self._box(-width * 0.28, 0, 0.025, width * 0.42,
                      depth * 0.70, 0.05, self.wood)
            self._box(-width * 0.28, 0, 0.055, width * 0.14,
                      depth * 0.24, 0.012, self.metal)
            for index in range(3):
                x = width * (0.05 + index * 0.22)
                self._cylinder(x, 0, 0.02, height * 0.54,
                               width * 0.07, self.accent, 14)
                self._cylinder(x, 0, height * 0.53, height * 0.62,
                               width * 0.075, self.wood, 14)
            for index, x in enumerate((-width * 0.32, -width * 0.20, -width * 0.08)):
                self._sphere(x, depth * 0.26, 0.10,
                             width * 0.065, self.accent if index != 1 else self.fabric)
            return
        if style in {"towel_bars", "robe_hooks"}:
            levels = (0.40, 0.82) if style == "towel_bars" else (0.50,)
            for index, fraction in enumerate(levels):
                z = height * fraction
                self._tube((-width * 0.43, 0, z), (width * 0.43, 0, z), 0.018)
                if style == "towel_bars":
                    self._box(0, -depth * 0.07, z - height * 0.15,
                              width * 0.38, depth * 0.04, height * 0.28,
                              self.fabric)
                else:
                    for hook in range(4):
                        x = -width * 0.34 + hook * width * 0.22
                        self._tube((x, 0, z), (x, -depth * 0.18, z - 0.10), 0.012)
            return
        if style == "bath_mats":
            self._box(-width * 0.19, 0, 0.018, width * 0.60,
                      depth * 0.44, 0.035, self.fabric)
            self._box(width * 0.25, 0, 0.018, width * 0.36,
                      depth * 0.32, 0.035, self.accent)
            return
        if style in {"spa_set", "bath_organizer", "bath_tray"}:
            self._box(0, 0, 0.035, width, depth, 0.07, self.wood)
            bottle_count = 3 if style != "bath_tray" else 2
            for index in range(bottle_count):
                x = -width * 0.32 + index * width * 0.28
                z1 = height * (0.72 if style == "bath_organizer" else 0.60)
                self._cylinder(x, 0, 0.07, z1, width * 0.065,
                               self.fabric if index % 2 else self.accent, 16)
                self._cylinder(x, 0, z1, z1 + height * 0.12,
                               width * 0.035, self.metal, 12)
            if style == "bath_tray":
                self._box(width * 0.31, 0, height * 0.40,
                          width * 0.18, depth * 0.62, height * 0.35,
                          self.fabric)
                self._box(width * 0.25, 0, height * 0.60,
                          width * 0.25, depth * 0.40, 0.035, self.accent)
            elif style == "spa_set":
                self._cylinder(width * 0.35, 0, 0.07, height * 0.56,
                               width * 0.075, self.wood, 16)
            return
        if style == "toilet_brush":
            self._cylinder(0, 0, 0.02, height * 0.38,
                           width * 0.40, self.accent, 18)
            self._tube((0, 0, height * 0.35),
                       (0, 0, height * 0.90), 0.012, self.metal)
            self._sphere(0, 0, height * 0.92, width * 0.09, self.fabric)
            return
        if style == "grab_bars":
            self._tube((-width * 0.42, 0, height * 0.30),
                       (width * 0.42, 0, height * 0.30), 0.025)
            self._tube((width * 0.32, 0, height * 0.40),
                       (width * 0.32, 0, height * 0.94), 0.025)
            for x, z in ((-width * 0.42, height * 0.30),
                         (width * 0.42, height * 0.30),
                         (width * 0.32, height * 0.40),
                         (width * 0.32, height * 0.94)):
                self._disk(x, -0.018, z - 0.035, z + 0.035,
                           0.05, 0.035, self.metal, 16)
            return
        if style == "bistro_set":
            self._draw_table(0, 0, width * 0.48, depth * 0.48,
                             height, "breakfast_round")
            for sx in (-1, 1):
                self._draw_chair(sx * width * 0.32, -depth * 0.30,
                                 width * 0.31, depth * 0.30,
                                 height * 0.91, "patio_chair")
            return
        if style == "picnic_set":
            tabletop_z = height * 0.62
            self._box(0, 0, tabletop_z, width * 0.94,
                      depth * 0.36, 0.08, self.wood)
            for sy in (-1, 1):
                y = sy * depth * 0.38
                self._box(0, y, height * 0.36, width * 0.92,
                          depth * 0.15, 0.06, self.wood)
                self._box(-width * 0.34, y, height * 0.30,
                          0.06, 0.06, height * 0.60, self.wood)
                self._box(width * 0.34, y, height * 0.30,
                          0.06, 0.06, height * 0.60, self.wood)
            for sx in (-1, 1):
                self._box(sx * width * 0.34, 0, tabletop_z * 0.50,
                          0.07, depth * 0.62, tabletop_z, self.wood)
            return
        if style == "path_lights":
            for index in range(4):
                x = -width * 0.38 + index * width * 0.25
                self._cylinder(x, 0, 0.02, height * 0.72,
                               width * 0.035, self.metal, 12)
                self._disk(x, 0, height * 0.70, height * 0.75,
                           width * 0.085, depth * 0.085, self.accent, 16)
                self._cylinder(x, 0, height * 0.74, height * 0.84,
                               width * 0.055, self.fabric, 12)
            return
        if style == "lantern_planters":
            for sx in (-1, 1):
                x = sx * width * 0.32
                self._box(x, 0, height * 0.18, width * 0.24,
                          depth * 0.72, height * 0.34, self.accent)
                self._cylinder(x, 0, height * 0.42, height * 0.76,
                               width * 0.045, self.metal, 16)
                self._box(x, 0, height * 0.74, width * 0.18,
                          depth * 0.26, height * 0.18, self.fabric)
                self._sphere(x, 0, height * 0.78, width * 0.055, self.accent)
            return
        self._box(0, 0, height / 2, width, depth, height, self.accent)

    def _build_canopy(self, style):
        width, depth, height = self.w, self.d, self.h
        if style == "pergola":
            post = max(0.07, min(width, depth) * 0.055)
            for sx in (-1, 1):
                for sy in (-1, 1):
                    self._box(sx * width * 0.45, sy * depth * 0.45,
                              height / 2, post, post, height, self.wood)
            for sy in (-1, 1):
                self._box(0, sy * depth * 0.45, height * 0.94,
                          width, post, post, self.wood)
            for index in range(7):
                x = -width * 0.42 + index * width * 0.14
                self._box(x, 0, height * 0.98, post * 0.60,
                          depth * 0.94, post * 0.60, self.wood)
            return
        if style == "garden_arch":
            for sx in (-1, 1):
                self._box(sx * width * 0.40, 0, height * 0.42,
                          0.07, depth * 0.28, height * 0.84, self.wood)
            self._box(0, 0, height * 0.90, width * 0.84,
                      depth * 0.28, 0.08, self.wood)
            for index in range(5):
                x = -width * 0.32 + index * width * 0.16
                self._box(x, 0, height * 0.94, 0.035,
                          depth * 0.32, height * 0.18, self.accent)
            return
        # Cantilever-like umbrella canopy, mast, ribs and weighted base.
        self._cylinder(0, 0, 0.02, height * 0.18, width * 0.16, self.metal, 20)
        self._tube((0, 0, height * 0.16), (0, 0, height * 0.92), 0.025)
        canopy_z = height * 0.90
        self._disk(0, 0, canopy_z - 0.06, canopy_z,
                   width * 0.49, depth * 0.49, self.fabric, 32)
        self._sphere(0, 0, canopy_z + 0.035, width * 0.055, self.metal)
        for index in range(8):
            angle = index * math.tau / 8
            self._tube((0, 0, canopy_z - 0.02),
                       (math.cos(angle) * width * 0.48,
                        math.sin(angle) * depth * 0.48, canopy_z - 0.08),
                       0.009)

    def _build_planter(self, style):
        width, depth, height = self.w, self.d, self.h
        bed_h = height * 0.42
        self._box(0, 0, bed_h / 2, width, depth, bed_h, self.wood)
        self._box(0, 0, bed_h * 0.88, width * 0.92,
                  depth * 0.92, 0.045, self.accent)
        rows = 2 if style == "raised_bed" else 1
        count = 3 if rows == 1 else 6
        for index in range(count):
            x = -width * 0.36 + (index % 3) * width * 0.36
            y = 0 if rows == 1 else (-depth * 0.22 if index < 3 else depth * 0.22)
            stem_h = height * (0.50 + 0.08 * (index % 2))
            self._tube((x, y, bed_h), (x, y, stem_h), 0.012, self.accent)
            self._sphere(x, y, stem_h, min(width, depth) * 0.12, self.accent)
        if style == "raised_bed":
            for index in range(2):
                x = -width / 6 + index * width / 3
                self._box(x, 0, bed_h * 0.96, 0.025,
                          depth * 0.92, 0.045, self.wood)

    def _build_outdoor(self, style):
        width, depth, height = self.w, self.d, self.h
        if style == "grill":
            body_h = height * 0.60
            self._box(0, 0, body_h / 2, width * 0.70,
                      depth * 0.70, body_h, self.metal)
            self._box(0, -depth * 0.38, body_h * 0.94,
                      width * 0.76, depth * 0.78, 0.055, self.accent)
            self._box(0, -depth * 0.38, body_h * 1.43,
                      width * 0.70, depth * 0.70, body_h * 0.90,
                      self.metal)
            self._box(0, -depth * 0.38, body_h * 1.82,
                      width * 0.67, depth * 0.65, 0.04, self.wood)
            for index in range(4):
                x = -width * 0.26 + index * width * 0.17
                self._cylinder(x, -depth * 0.80, body_h * 0.82,
                               body_h * 0.92, 0.025, self.accent, 12)
            self._box(width * 0.44, 0, body_h * 0.88,
                      width * 0.25, depth * 0.72, 0.05, self.wood)
            for sx in (-1, 1):
                for sy in (-1, 1):
                    self._cylinder(sx * width * 0.28, sy * depth * 0.26,
                                   0.02, 0.12, 0.025, self.metal, 10)
            return
        if style == "fire_pit":
            self._cylinder(0, 0, 0.05, height * 0.45,
                           min(width, depth) * 0.46, self.wood, 28)
            self._cylinder(0, 0, height * 0.43, height * 0.52,
                           min(width, depth) * 0.49, self.metal, 28)
            for index in range(5):
                angle = index * math.pi / 5
                self._rotated_box((math.cos(angle) * width * 0.12,
                                   math.sin(angle) * depth * 0.12,
                                   height * 0.58),
                                  (width * 0.32, 0.055, 0.06),
                                  (0, 0, angle), self.accent)
            return
        if style == "fountain":
            self._cylinder(0, 0, 0.02, height * 0.18,
                           min(width, depth) * 0.38, self.wood, 24)
            self._cylinder(0, 0, height * 0.18, height * 0.48,
                           min(width, depth) * 0.13, self.accent, 20)
            self._disk(0, 0, height * 0.46, height * 0.54,
                       width * 0.47, depth * 0.47, self.wood, 32)
            self._cylinder(0, 0, height * 0.54, height * 0.78,
                           min(width, depth) * 0.09, self.accent, 18)
            self._disk(0, 0, height * 0.76, height * 0.81,
                       width * 0.30, depth * 0.30, self.wood, 24)
            self._cylinder(0, 0, height * 0.81, height * 0.90,
                           min(width, depth) * 0.045, self.accent, 16)
            self._sphere(0, 0, height * 0.93, min(width, depth) * 0.07,
                         self.metal)
            return
        if style == "bird_bath":
            self._cylinder(0, 0, 0.02, height * 0.65,
                           min(width, depth) * 0.13, self.wood, 20)
            self._disk(0, 0, height * 0.64, height * 0.74,
                       width * 0.48, depth * 0.48, self.accent, 28)
            self._disk(0, 0, height * 0.73, height * 0.78,
                       width * 0.40, depth * 0.40, self.metal, 28)
            return

    def _build(self):
        if self.record is None:
            raise ValueError("Selecciona un objeto válido para esta habitación")
        family, style = self.record[3], self.record[4]
        dispatch = {
            "table": self._build_table,
            "bed": self._build_bed,
            "headboard": self._build_headboard,
            "sofa": self._build_sofa,
            "seat": self._build_seat,
            "shelf": self._build_shelf,
            "cabinet": self._build_cabinet,
            "accessory": self._build_accessory,
            "set": self._build_set,
            "canopy": self._build_canopy,
            "planter": self._build_planter,
            "outdoor": self._build_outdoor,
        }
        generator = dispatch.get(family)
        if generator is None:
            raise ValueError(f"Familia geométrica no implementada: {family}")
        generator(style)
        return self.builder

    def generate(self):
        return self._build()


def _find_room_asset_object(props):
    name = getattr(props, "object_name", "")
    if name and name in bpy.data.objects:
        return bpy.data.objects[name]
    for obj in bpy.data.objects:
        if (obj.type == 'MESH' and hasattr(obj, AF_ROOM_ASSET_PROP)
                and getattr(obj, AF_ROOM_ASSET_PROP) is props):
            return obj
    return None


def _rebuild_room_asset_mesh(obj, props):
    generator = AF_RoomAssetGenerator(props)
    builder = generator.generate()
    builder.finalize(obj.data)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    obj.data.update()


def _setup_room_asset_materials(obj):
    af_material.ensure_af_materials_for_object(obj, [
        "AF.Room.Wood", "AF.Room.Fabric", "AF.Room.Metal", "AF.Room.Accent",
    ])


def _create_room_asset_object(context, name="AF_RoomAsset"):
    mesh = bpy.data.meshes.new(name)
    obj = None
    try:
        obj = bpy.data.objects.new(name, mesh)
        context.collection.objects.link(obj)
        obj.location = context.scene.cursor.location.copy()
        context.view_layer.objects.active = obj
        obj.select_set(True)
        props = getattr(obj, AF_ROOM_ASSET_PROP)
        props.is_af_room_asset = True
        props.object_name = obj.name
        props.af_version = AF_ROOM_ASSET_VERSION
        _setup_room_asset_materials(obj)
        return obj, props
    except Exception:
        if obj is not None and obj.name in bpy.data.objects:
            bpy.data.objects.remove(obj, do_unlink=True)
        if mesh.users == 0 and mesh.name in bpy.data.meshes:
            bpy.data.meshes.remove(mesh)
        raise


class ARCHIFORGE_OT_room_asset(Operator):
    """Browse and create a parametric room-specific furniture or decor asset."""
    bl_idname = "archiforge.room_asset"
    bl_label = "Room Asset Library"
    bl_description = "Choose from 100 furniture and decor assets by room"
    bl_options = {'REGISTER', 'UNDO'}

    # Same rule as AF_RoomAssetProperties: no string default on callback enums.
    room: EnumProperty(
        name="Room", items=ROOM_ENUM_ITEMS, default="BEDROOM",
        update=_operator_room_update,
    )
    asset_type: EnumProperty(
        name="Object / Set", items=_asset_items,
        update=_operator_asset_update,
    )
    auto_dimensions: BoolProperty(
        name="Use Suggested Dimensions", default=True,
        update=_operator_auto_update,
    )
    width: FloatProperty(name="Width", default=0.50, min=0.05, unit='LENGTH')
    depth: FloatProperty(name="Depth", default=0.42, min=0.05, unit='LENGTH')
    height: FloatProperty(name="Height", default=0.58, min=0.01, unit='LENGTH')

    def invoke(self, context, event):
        record = find_asset(self.room, self.asset_type)
        if record is not None and self.auto_dimensions:
            self.width, self.depth, self.height = record[5:8]
        return context.window_manager.invoke_props_dialog(self, width=480)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.prop(self, "room")
        layout.prop(self, "asset_type")
        layout.prop(self, "auto_dimensions")
        dimensions = layout.column(align=True)
        dimensions.enabled = not self.auto_dimensions
        dimensions.prop(self, "width")
        dimensions.prop(self, "depth")
        dimensions.prop(self, "height")
        layout.label(text="The created mesh remains parametric and editable.",
                     icon='INFO')

    def execute(self, context):
        global _SUSPEND
        record = find_asset(self.room, self.asset_type)
        if record is None:
            self.report({'ERROR'}, _tr("El objeto no pertenece a la habitación elegida"))
            return {'CANCELLED'}
        if self.auto_dimensions:
            width, depth, height = record[5:8]
        else:
            width, depth, height = self.width, self.depth, self.height

        obj = None
        previous_suspend = _SUSPEND
        _SUSPEND = True
        try:
            obj, props = _create_room_asset_object(context)
            props.room = self.room
            props.asset_type = self.asset_type
            props.drawer_count = _DRAWER_DEFAULTS.get(self.asset_type, 3)
            props.width = width
            props.depth = depth
            props.height = height
            _rebuild_room_asset_mesh(obj, props)
            obj.name = "AF_" + self.room.title().replace(" ", "") + "_" + self.asset_type
            props.object_name = obj.name
        except Exception as exc:
            if obj is not None and obj.name in bpy.data.objects:
                mesh = obj.data if obj.type == 'MESH' else None
                bpy.data.objects.remove(obj, do_unlink=True)
                if mesh is not None and mesh.users == 0:
                    bpy.data.meshes.remove(mesh)
            self.report({'ERROR'}, _tr("No se pudo crear el objeto: {}").format(exc))
            return {'CANCELLED'}
        finally:
            _SUSPEND = previous_suspend

        self.report({'INFO'}, _tr("{} creado: {}").format(record[1], obj.name))
        return {'FINISHED'}


class ARCHIFORGE_OT_room_asset_reset(Operator):
    bl_idname = "archiforge.room_asset_reset"
    bl_label = "Reset Suggested Dimensions"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj is not None and obj.type == 'MESH'
                and hasattr(obj, AF_ROOM_ASSET_PROP)
                and obj.archiforge_room_asset.is_af_room_asset)

    def execute(self, context):
        props = context.active_object.archiforge_room_asset
        record = find_asset(props.room, props.asset_type)
        if record is None:
            return {'CANCELLED'}
        _set_dimensions(props, record)
        _rebuild_room_asset_mesh(context.active_object, props)
        return {'FINISHED'}


class ARCHIFORGE_OT_room_asset_update(Operator):
    bl_idname = "archiforge.room_asset_update"
    bl_label = "Rebuild Room Asset"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj is not None and obj.type == 'MESH'
                and hasattr(obj, AF_ROOM_ASSET_PROP)
                and obj.archiforge_room_asset.is_af_room_asset)

    def execute(self, context):
        obj = context.active_object
        _rebuild_room_asset_mesh(obj, obj.archiforge_room_asset)
        self.report({'INFO'}, _tr("Room asset rebuilt"))
        return {'FINISHED'}


class ARCHIFORGE_PT_room_asset(Panel):
    bl_label = "Room Asset Properties"
    bl_idname = "ARCHIFORGE_PT_room_asset"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "ArchiForge"
    bl_context = "objectmode"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj is not None and obj.type == 'MESH'
                and hasattr(obj, AF_ROOM_ASSET_PROP)
                and obj.archiforge_room_asset.is_af_room_asset)

    def draw_header(self, context):
        self.layout.label(text="", **_icon("room_assets", 'ASSET_MANAGER'))

    def draw(self, context):
        props = context.active_object.archiforge_room_asset
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.prop(props, "room")
        layout.prop(props, "asset_type")
        layout.label(text="Suggested dimensions (metres)", icon='ARROW_LEFTRIGHT')
        layout.prop(props, "width")
        layout.prop(props, "depth")
        layout.prop(props, "height")
        layout.operator("archiforge.room_asset_reset",
                        text="Reset Suggested Dimensions", icon='LOOP_BACK')
        layout.prop(props, "mesh_quality")
        if "shelf" in props.asset_type.lower() or "bookcase" in props.asset_type.lower():
            layout.prop(props, "shelf_count")
        if "dresser" in props.asset_type.lower() or "drawer" in props.asset_type.lower():
            layout.prop(props, "drawer_count")
        layout.prop(props, "decor_detail")
        box = layout.box()
        box.label(text="Material Slots", icon='MATERIAL')
        box.prop(props, "mat_wood")
        box.prop(props, "mat_fabric")
        box.prop(props, "mat_metal")
        box.prop(props, "mat_accent")
        layout.separator()
        layout.operator("archiforge.room_asset_update",
                        text="Rebuild Geometry", icon='FILE_REFRESH')


classes = [
    AF_RoomAssetProperties,
    ARCHIFORGE_OT_room_asset,
    ARCHIFORGE_OT_room_asset_reset,
    ARCHIFORGE_OT_room_asset_update,
    ARCHIFORGE_PT_room_asset,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Object.archiforge_room_asset = PointerProperty(
        type=AF_RoomAssetProperties,
        name="ArchiForge Room Asset",
        description="Parametric room furniture and decor",
    )
    print("[ArchiForge] Room asset library registered (100 catalog entries)")


def unregister():
    if hasattr(bpy.types.Object, "archiforge_room_asset"):
        del bpy.types.Object.archiforge_room_asset
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    print("[ArchiForge] Room asset library unregistered")
