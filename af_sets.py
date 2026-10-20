# -*- coding: utf-8 -*-

# ╔══════════════════════════════════════════════════════════╗
# ║                 ARCHIFORGE — af_sets.py                  ║
# ║   Conjuntos combinados: baño completo y apartamento demo ║
# ║                 GPL v3 — ArchiForge Devs                 ║
# ╚══════════════════════════════════════════════════════════╝

# <pep8 compliant>

"""Combined sets built by composing the existing ArchiForge operators.

* ``archiforge.set_bathroom`` — a complete bathroom (reference layout
  for a Colombian apartment): walls, ceramic floor, door, high window,
  pedestal sink, toilet, shower with electric shower head, mirror, towel
  rail, GFCI outlet, switch and ceiling light.
* ``archiforge.set_apartment`` — a 6 × 7 m demo apartment with the
  bathroom above, open kitchen, living/dining, two bedrooms, doors,
  windows, floors, furniture, electrical items, dimensions and north.

Every piece is a regular parametric ArchiForge object (editable later,
counted by the quantity takeoff). The layouts are starting points, not
normative designs. Each step is isolated: when a module is missing or a
piece fails, the rest of the set is still created and the report lists
what was skipped.
"""

import math

import bpy
from mathutils import Vector
from bpy.types import Operator, Panel
from bpy.props import BoolProperty, EnumProperty, FloatProperty

from .af_construction_presets import (
    CUSTOM_PRESET,
    tile_preset_dimensions,
    wall_preset_items,
    wall_preset_thickness,
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

try:
    from . import af_autoboolean
except ImportError:  # pragma: no cover
    af_autoboolean = None

AF_WALL_PRESETS = wall_preset_items()

_DEG = math.radians


# ════════════════════════════════════════════════════════════
#  Compositor
# ════════════════════════════════════════════════════════════
class SetBuilder:
    """Creates pieces through the public operators and keeps a log."""

    def __init__(self, context, collection_name=None):
        self.context = context
        self.created = []
        self.skipped = []
        self.collection = None
        if collection_name:
            self.collection = bpy.data.collections.get(collection_name)
            if self.collection is None:
                self.collection = bpy.data.collections.new(collection_name)
            try:
                if self.collection.name not in context.scene.collection.children:
                    context.scene.collection.children.link(self.collection)
            except RuntimeError:
                pass

    # ── infraestructura ────────────────────────────────────
    def _active(self):
        return self.context.view_layer.objects.active

    def _track(self, obj, label):
        if obj is None:
            self.skipped.append(label)
            return None
        self.created.append(obj)
        if self.collection is not None:
            try:
                for coll in list(obj.users_collection):
                    if coll is not self.collection:
                        coll.objects.unlink(obj)
                if obj.name not in self.collection.objects:
                    self.collection.objects.link(obj)
            except RuntimeError:
                pass
        return obj

    def _run(self, label, func):
        try:
            return func()
        except Exception as err:  # noqa: BLE001 - keep building the set
            print("[ArchiForge] set step '{}' skipped: {}".format(label, err))
            self.skipped.append(label)
            return None

    @staticmethod
    def _op(name):
        op = getattr(bpy.ops.archiforge, name, None)
        if op is None:
            raise RuntimeError("operator archiforge.{} unavailable".format(name))
        return op

    def _place(self, obj, x, y, z=0.0, rot=0.0):
        obj.location = Vector((float(x), float(y), float(z)))
        obj.rotation_euler = (0.0, 0.0, float(rot))
        self.context.view_layer.update()
        return obj

    @staticmethod
    def _set_props(obj, group, **values):
        props = getattr(obj, group, None)
        if props is None:
            return
        for key, value in values.items():
            try:
                setattr(props, key, value)
            except Exception as err:  # noqa: BLE001
                print("[ArchiForge] set: {}.{} = {!r} ignored ({})".format(
                    group, key, value, err))

    # ── piezas ─────────────────────────────────────────────
    def wall(self, label, points, height, preset=CUSTOM_PRESET, width=0.15,
             closed=False, name=None):
        def make():
            from . import af_wall
            obj = af_wall.create_wall_from_points(
                self.context, points, height=height, width=width,
                wall_preset=preset, closed=closed, name=name)
            return self._track(obj, label)
        return self._run(label, make)

    def floor(self, label, points, tile_preset='T60x60', pattern='REGULAR',
              z=0.0, name="AF_Floor"):
        def make():
            from . import af_floor
            size = tile_preset_dimensions(tile_preset) or (0.60, 0.60)
            obj = af_floor.create_floor_from_outline(
                self.context, points, z=z, pattern=pattern,
                tile_width=size[0], tile_depth=size[1],
                tile_preset=tile_preset, name=name)
            return self._track(obj, label)
        return self._run(label, make)

    def _opening(self, label, kind, wall, x, y, rot, width, height,
                 sill=0.0, **kwargs):
        def make():
            if kind == 'DOOR':
                self._op("door")(width=width, height=height,
                                 auto_boolean=False, **kwargs)
            else:
                self._op("window")(width=width, height=height,
                                   sill_height=sill, auto_boolean=False,
                                   **kwargs)
            obj = self._active()
            if obj is None:
                return None
            self._place(obj, x, y, 0.0, rot)
            if wall is not None and af_autoboolean is not None:
                af_autoboolean.do_auto_boolean(
                    context=self.context, source_obj=obj, cutter_type=kind,
                    width=width, height=height, sill_height=sill,
                    wall_obj=wall)
            return self._track(obj, label)
        return self._run(label, make)

    def door(self, label, wall, x, y, rot=0.0, width=0.80, height=2.10,
             door_type='SINGLE'):
        """Door whose hinge jamb is at ``(x, y)``; ``rot`` follows the wall."""
        return self._opening(label, 'DOOR', wall, x, y, rot, width, height,
                             door_type=door_type)

    def window(self, label, wall, x, y, rot=0.0, width=1.20, height=1.20,
               sill=0.90, window_type='SLIDING'):
        return self._opening(label, 'WINDOW', wall, x, y, rot, width, height,
                             sill=sill, window_type=window_type)

    def item(self, label, op_name, item_type, x, y, z=0.0, rot=0.0,
             group=None, **props):
        """Fixture/furniture/electrical piece centred at ``(x, y, z)``."""
        def make():
            self._op(op_name)(item_type=item_type, auto_dimensions=True)
            obj = self._active()
            if obj is None:
                return None
            self._place(obj, x, y, z, rot)
            if group and props:
                self._set_props(obj, group, **props)
            return self._track(obj, label)
        return self._run(label, make)

    def bathroom_item(self, label, item_type, x, y, rot=0.0, **props):
        return self.item(label, "bathroom", item_type, x, y, 0.0, rot,
                         group="archiforge_bathroom", **props)

    def electrical(self, label, item_type, x, y, z, rot=0.0, **props):
        return self.item(label, "electrical", item_type, x, y, z, rot,
                         group="archiforge_electrical", **props)

    def furniture(self, label, item_type, x, y, rot=0.0, **props):
        return self.item(label, "furniture", item_type, x, y, 0.0, rot,
                         group="archiforge_furniture", **props)

    def kitchen(self, label, item_type, x, y, rot=0.0, **props):
        return self.item(label, "kitchen", item_type, x, y, 0.0, rot,
                         group="archiforge_kitchen", **props)

    def dimensions(self, label, wall_obj, offset=1.0):
        def make():
            from . import af_annotation, af_annotation_geometry as geo
            self.context.view_layer.update()   # fresh bound_box
            lo, hi = af_annotation._world_bounds(wall_obj)
            created = []
            for index, result in enumerate(geo.footprint_dimensions(
                    lo, hi, offset=offset,
                    unit_system=af_annotation._unit_system(self.context))):
                created.append(af_annotation._create_dimension(
                    self.context, result, "AF_Dim_Set_{}".format(index),
                    0.22, 0.01))
            for obj in created:
                self._track(obj, label)
            return created[0] if created else None
        return self._run(label, make)

    def north(self, label, x, y, size=1.0):
        def make():
            cursor = self.context.scene.cursor
            previous = cursor.location.copy()
            cursor.location = Vector((x, y, 0.0))
            try:
                self._op("north_arrow")(size=size)
            finally:
                cursor.location = previous
            return self._track(self._active(), label)
        return self._run(label, make)

    def finish(self):
        try:
            for obj in self.context.selected_objects:
                obj.select_set(False)
            for obj in self.created:
                obj.select_set(True)
            if self.created:
                self.context.view_layer.objects.active = self.created[0]
        except Exception:  # noqa: BLE001
            pass
        return len(self.created), list(self.skipped)


# ════════════════════════════════════════════════════════════
#  Baño completo (referencia CO)
# ════════════════════════════════════════════════════════════
def build_bathroom(builder, origin=(0.0, 0.0), width=1.50, depth=2.20,
                   height=2.40, preset='BRICK', wall_width=0.12,
                   walls=True, floor=True, door_wall='FRONT',
                   front_wall=None, right_wall=None, back_wall=None,
                   front_wall_thickness=None, fixtures=True,
                   electrical=True, openings=True):
    """Lay out a bathroom whose interior is ``[0, width] × [0, depth]``.

    ``door_wall`` is ``'FRONT'`` (y = 0, standalone set) or ``'RIGHT'``
    (x = width, used inside the apartment). When ``walls`` is False the
    caller passes the host wall objects for the boolean cuts and, if the
    front wall is thicker than the partitions, its thickness.
    """
    ox, oy = float(origin[0]), float(origin[1])
    W, D = float(width), float(depth)
    t = wall_preset_thickness(preset)
    if t is None:
        t = float(wall_width)
    tf = t if front_wall_thickness is None else float(front_wall_thickness)
    h = float(height)

    def P(x, y):
        return (ox + x, oy + y, 0.0)

    if walls:
        room = builder.wall(
            "bathroom walls",
            [P(-t / 2, -t / 2), P(W + t / 2, -t / 2),
             P(W + t / 2, D + t / 2), P(-t / 2, D + t / 2)],
            height=h, preset=preset, width=wall_width, closed=True,
            name="AF_Bath_Walls")
        front_wall = right_wall = back_wall = room

    if floor:
        builder.floor("bathroom floor",
                      [P(0, 0), P(W, 0), P(W, D), P(0, D)],
                      tile_preset='T30x30', name="AF_Bath_Floor")

    if openings:
        if door_wall == 'RIGHT':
            builder.door("bathroom door", right_wall, ox + W + t / 2,
                         oy + min(0.95, D - 0.80), rot=_DEG(90),
                         width=0.70, height=2.10)
            builder.window("bathroom window", front_wall,
                           ox + min(0.70, W - 0.70), oy - tf / 2,
                           width=0.60, height=0.40, sill=1.80)
        else:
            builder.door("bathroom door", front_wall,
                         ox + max(W - 0.80, 0.0), oy - tf / 2,
                         width=0.70, height=2.10)
            builder.window("bathroom window", back_wall, ox + 0.15,
                           oy + D + t / 2, width=0.60, height=0.40,
                           sill=1.80)

    if fixtures:
        # Fixtures keep their back (+Y local) against the left wall
        # (rotation +90°) or the back wall (rotation 0).
        builder.bathroom_item("pedestal sink", 'PEDESTAL_SINK', ox + 0.25,
                              oy + 0.35, rot=_DEG(90))
        builder.bathroom_item("mirror", 'MIRROR', ox + 0.03, oy + 0.35,
                              rot=_DEG(90))
        builder.bathroom_item("toilet", 'TOILET', ox + 0.36, oy + 1.05,
                              rot=_DEG(90))
        builder.bathroom_item("shower", 'SHOWER', ox + 0.45, oy + D - 0.45)
        builder.bathroom_item("electric shower", 'ELECTRIC_SHOWER',
                              ox + 0.45, oy + D - 0.03)
        builder.bathroom_item("towel rail", 'TOWEL_RAIL', ox + W - 0.03,
                              oy + min(1.50, D - 0.70), rot=_DEG(-90))

    if electrical:
        # Wall plates face +Y locally; rotate so they face into the room.
        builder.electrical("bathroom outlet", 'OUTLET', ox, oy + 0.75,
                           1.10, rot=_DEG(-90), socket_standard='CO',
                           outlet_gfci=True)
        if door_wall == 'RIGHT':
            builder.electrical("bathroom switch", 'SWITCH', ox + W,
                               oy + 0.80, 1.15, rot=_DEG(90))
        else:
            builder.electrical("bathroom switch", 'SWITCH', ox + 0.55, oy,
                               1.15)
        builder.electrical("bathroom light", 'CEILING_LIGHT', ox + W / 2,
                           oy + D / 2, h)


class ARCHIFORGE_OT_set_bathroom(Operator):
    bl_idname = "archiforge.set_bathroom"
    bl_label = "Complete Bathroom (CO)"
    bl_description = ("Build a complete bathroom at the 3D cursor: walls, "
                      "ceramic floor, door, high window, sink, toilet, "
                      "shower with electric shower head, accessories and "
                      "electrical items. Reference layout, edit freely")
    bl_options = {'REGISTER', 'UNDO'}

    width : FloatProperty(name="Interior Width", default=1.50, min=1.20,
                          max=4.0, unit='LENGTH')
    depth : FloatProperty(name="Interior Depth", default=2.20, min=1.80,
                          max=5.0, unit='LENGTH')
    wall_height : FloatProperty(name="Wall Height", default=2.40, min=2.10,
                                max=4.0, unit='LENGTH')
    wall_preset : EnumProperty(name="Wall Reference", items=AF_WALL_PRESETS,
                               default='BRICK')
    wall_width : FloatProperty(
        name="Wall Thickness", default=0.12, min=0.05, max=0.40,
        unit='LENGTH', description="Used when the wall reference is Custom")
    include_walls : BoolProperty(name="Walls", default=True)
    include_floor : BoolProperty(name="Floor", default=True)
    include_openings : BoolProperty(name="Door and Window", default=True)
    include_fixtures : BoolProperty(name="Fixtures", default=True)
    include_electrical : BoolProperty(name="Electrical", default=True)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        col = layout.column(align=True)
        col.prop(self, "width")
        col.prop(self, "depth")
        col.prop(self, "wall_height")
        col.separator()
        col.prop(self, "wall_preset")
        sub = col.column()
        sub.enabled = self.wall_preset == CUSTOM_PRESET
        sub.prop(self, "wall_width")
        col.separator()
        col.prop(self, "include_walls")
        col.prop(self, "include_floor")
        col.prop(self, "include_openings")
        col.prop(self, "include_fixtures")
        col.prop(self, "include_electrical")

    def execute(self, context):
        origin = context.scene.cursor.location.copy()
        builder = SetBuilder(context, "AF_Set_Bathroom")
        build_bathroom(
            builder, origin=(origin.x, origin.y), width=self.width,
            depth=self.depth, height=self.wall_height,
            preset=self.wall_preset, wall_width=self.wall_width,
            walls=self.include_walls, floor=self.include_floor,
            openings=self.include_openings and self.include_walls,
            fixtures=self.include_fixtures,
            electrical=self.include_electrical)
        context.scene.cursor.location = origin
        count, skipped = builder.finish()
        if not count:
            self.report({'ERROR'}, _tr("The set could not be created"))
            return {'CANCELLED'}
        if skipped:
            self.report({'WARNING'},
                        _tr("Bathroom set: {} objects, skipped: {}").format(
                            count, ", ".join(skipped)))
        else:
            self.report({'INFO'},
                        _tr("Bathroom set created: {} objects").format(count))
        return {'FINISHED'}


# ════════════════════════════════════════════════════════════
#  Apartamento demo 6 × 7 m
# ════════════════════════════════════════════════════════════
APARTMENT_WIDTH = 6.00
APARTMENT_DEPTH = 7.00


def build_apartment(builder, origin=(0.0, 0.0), height=2.40,
                    exterior_preset='STRUCTURAL_BLOCK',
                    interior_preset='BRICK', bathroom=True, kitchen=True,
                    furniture=True, electrical=True, annotations=True):
    """Demo apartment with interior ``[0, 6] × [0, 7]`` metres."""
    ox, oy = float(origin[0]), float(origin[1])
    W, D = APARTMENT_WIDTH, APARTMENT_DEPTH
    te = wall_preset_thickness(exterior_preset) or 0.20
    ti = wall_preset_thickness(interior_preset) or 0.12
    h = float(height)
    bw, bd = 1.50, 2.20            # bathroom interior
    y_bed = 4.20                   # bedrooms start (interior face)
    x_bed = 3.00                   # bedroom split (interior face)

    def P(x, y):
        return (ox + x, oy + y, 0.0)

    # ── muros ──────────────────────────────────────────────
    perimeter = builder.wall(
        "perimeter walls",
        [P(-te / 2, -te / 2), P(W + te / 2, -te / 2),
         P(W + te / 2, D + te / 2), P(-te / 2, D + te / 2)],
        height=h, preset=exterior_preset, width=te, closed=True,
        name="AF_Apt_Perimeter")
    bath_wall = builder.wall(
        "bathroom partition",
        [P(bw + ti / 2, 0.0), P(bw + ti / 2, bd + ti / 2), P(0.0, bd + ti / 2)],
        height=h, preset=interior_preset, width=ti, name="AF_Apt_BathWall")
    bed_wall = builder.wall(
        "bedroom partition",
        [P(0.0, y_bed + ti / 2), P(W, y_bed + ti / 2)],
        height=h, preset=interior_preset, width=ti, name="AF_Apt_BedWall")
    split_wall = builder.wall(
        "bedroom split",
        [P(x_bed + ti / 2, y_bed + ti), P(x_bed + ti / 2, D)],
        height=h, preset=interior_preset, width=ti, name="AF_Apt_SplitWall")

    # ── pisos ──────────────────────────────────────────────
    builder.floor(
        "apartment floor",
        [P(bw + ti, 0), P(W, 0), P(W, D), P(0, D), P(0, bd + ti),
         P(bw + ti, bd + ti)],
        tile_preset='T60x60', name="AF_Apt_Floor")

    # ── baño (puerta hacia el pasillo, ventana a fachada) ──
    if bathroom:
        build_bathroom(builder, origin=(ox, oy), width=bw, depth=bd,
                       height=h, preset=interior_preset, walls=False,
                       floor=True, door_wall='RIGHT', front_wall=perimeter,
                       right_wall=bath_wall, back_wall=bath_wall,
                       front_wall_thickness=te, fixtures=True,
                       electrical=electrical)

    # ── puertas y ventanas ─────────────────────────────────
    builder.door("entrance door", perimeter, ox - te / 2, oy + 2.70,
                 rot=_DEG(90), width=0.90, height=2.10)
    builder.door("bedroom 1 door", bed_wall, ox + 2.00, oy + y_bed + ti / 2,
                 width=0.80)
    builder.door("bedroom 2 door", bed_wall, ox + 3.50, oy + y_bed + ti / 2,
                 width=0.80)
    builder.window("bedroom 1 window", perimeter, ox + 0.90, oy + D + te / 2,
                   width=1.20, height=1.20, sill=0.90)
    builder.window("bedroom 2 window", perimeter, ox + 3.95, oy + D + te / 2,
                   width=1.20, height=1.20, sill=0.90)
    builder.window("living window", perimeter, ox + W + te / 2, oy + 2.80,
                   rot=_DEG(90), width=1.20, height=1.20, sill=0.90)
    builder.window("kitchen window", perimeter, ox + 4.20, oy - te / 2,
                   width=0.60, height=0.60, sill=1.20)

    # ── cocina abierta sobre la fachada inferior ───────────
    if kitchen:
        builder.kitchen("kitchen sink", 'SINK_CABINET', ox + 2.50, oy + 0.30,
                        rot=_DEG(180))
        builder.kitchen("stove", 'STOVE', ox + 3.50, oy + 0.30, rot=_DEG(180))
        builder.kitchen("fridge", 'FRIDGE', ox + 5.50, oy + 0.38,
                        rot=_DEG(180))

    # ── mobiliario ─────────────────────────────────────────
    if furniture:
        builder.furniture("sofa", 'SOFA', ox + 4.60, oy + 3.70)
        builder.furniture("coffee table", 'COFFEE_TABLE', ox + 4.60, oy + 2.90)
        builder.furniture("dining table", 'DINING_TABLE', ox + 1.80, oy + 3.30)
        for index, (x, y, rot) in enumerate((
                (1.45, 2.72, _DEG(180)), (2.15, 2.72, _DEG(180)),
                (1.45, 3.88, 0.0), (2.15, 3.88, 0.0))):
            builder.furniture("dining chair {}".format(index + 1),
                              'DINING_CHAIR', ox + x, oy + y, rot=rot)
        builder.furniture("bed 1", 'BED', ox + 1.50, oy + 5.95,
                          bed_size='DOUBLE')
        builder.furniture("nightstand 1", 'NIGHTSTAND', ox + 0.50, oy + 6.70)
        builder.furniture("nightstand 2", 'NIGHTSTAND', ox + 2.50, oy + 6.70)
        builder.furniture("bed 2", 'BED', ox + 5.40, oy + 5.95,
                          bed_size='SINGLE')
        builder.furniture("nightstand 3", 'NIGHTSTAND', ox + 4.55, oy + 6.70)
        builder.furniture("dresser", 'DRESSER', ox + x_bed + ti + 0.25,
                          oy + 5.60, rot=_DEG(90))

    # ── eléctrico ──────────────────────────────────────────
    if electrical:
        for label, x, y in (("kitchen light", 3.90, 1.10),
                            ("living light", 3.00, 3.30),
                            ("bedroom 1 light", 1.50, 5.70),
                            ("bedroom 2 light", 4.60, 5.70)):
            builder.electrical(label, 'CEILING_LIGHT', ox + x, oy + y, h)
        builder.electrical("entrance switch", 'SWITCH', ox, oy + 3.75, 1.15,
                           rot=_DEG(-90))
        builder.electrical("bedroom 1 switch", 'SWITCH', ox + 1.85,
                           oy + y_bed + ti, 1.15)
        builder.electrical("bedroom 2 switch", 'SWITCH', ox + 4.45,
                           oy + y_bed + ti, 1.15)
        builder.electrical("kitchen outlet", 'OUTLET', ox + 3.00, oy, 1.10,
                           socket_standard='CO')
        builder.electrical("living outlet", 'OUTLET', ox + W, oy + 3.00,
                           0.40, rot=_DEG(90), socket_standard='CO')
        builder.electrical("bedroom 1 outlet", 'OUTLET', ox + 0.40, oy + D,
                           0.40, rot=_DEG(180), socket_standard='CO')
        builder.electrical("bedroom 2 outlet", 'OUTLET', ox + 4.50, oy + D,
                           0.40, rot=_DEG(180), socket_standard='CO')

    # ── anotaciones ────────────────────────────────────────
    if annotations and perimeter is not None:
        builder.dimensions("overall dimensions", perimeter, offset=1.0)
        builder.north("north arrow", ox + W + 1.60, oy + D + 1.60, size=1.0)


class ARCHIFORGE_OT_set_apartment(Operator):
    bl_idname = "archiforge.set_apartment"
    bl_label = "Demo Apartment"
    bl_description = ("Build a 6 × 7 m demo apartment at the 3D cursor: "
                      "walls, floors, complete bathroom, open kitchen, "
                      "living/dining, two bedrooms, openings, furniture, "
                      "electrical items, dimensions and north arrow")
    bl_options = {'REGISTER', 'UNDO'}

    wall_height : FloatProperty(name="Wall Height", default=2.40, min=2.10,
                                max=4.0, unit='LENGTH')
    exterior_preset : EnumProperty(name="Exterior Walls",
                                   items=AF_WALL_PRESETS,
                                   default='STRUCTURAL_BLOCK')
    interior_preset : EnumProperty(name="Interior Walls",
                                   items=AF_WALL_PRESETS, default='BRICK')
    include_bathroom : BoolProperty(name="Bathroom", default=True)
    include_kitchen : BoolProperty(name="Kitchen", default=True)
    include_furniture : BoolProperty(name="Furniture", default=True)
    include_electrical : BoolProperty(name="Electrical", default=True)
    include_annotations : BoolProperty(name="Annotations", default=True)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        col = layout.column(align=True)
        col.prop(self, "wall_height")
        col.prop(self, "exterior_preset")
        col.prop(self, "interior_preset")
        col.separator()
        col.prop(self, "include_bathroom")
        col.prop(self, "include_kitchen")
        col.prop(self, "include_furniture")
        col.prop(self, "include_electrical")
        col.prop(self, "include_annotations")

    def execute(self, context):
        origin = context.scene.cursor.location.copy()
        builder = SetBuilder(context, "AF_Set_Apartment")
        exterior = self.exterior_preset
        interior = self.interior_preset
        if exterior == CUSTOM_PRESET:
            exterior = 'STRUCTURAL_BLOCK'
        if interior == CUSTOM_PRESET:
            interior = 'BRICK'
        build_apartment(
            builder, origin=(origin.x, origin.y), height=self.wall_height,
            exterior_preset=exterior, interior_preset=interior,
            bathroom=self.include_bathroom, kitchen=self.include_kitchen,
            furniture=self.include_furniture,
            electrical=self.include_electrical,
            annotations=self.include_annotations)
        context.scene.cursor.location = origin
        count, skipped = builder.finish()
        if not count:
            self.report({'ERROR'}, _tr("The set could not be created"))
            return {'CANCELLED'}
        if skipped:
            self.report({'WARNING'},
                        _tr("Apartment: {} objects, skipped: {}").format(
                            count, ", ".join(skipped)))
        else:
            self.report({'INFO'},
                        _tr("Demo apartment created: {} objects").format(count))
        return {'FINISHED'}


# ════════════════════════════════════════════════════════════
#  PANEL
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_PT_sets(Panel):
    bl_label = "Sets"
    bl_idname = "ARCHIFORGE_PT_sets"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ArchiForge"
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        self.layout.label(text="", **_icon("sets", 'HOME'))

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.label(text="Built at the 3D cursor", icon='PIVOT_CURSOR')
        col.operator("archiforge.set_bathroom", text="Complete Bathroom (CO)",
                     **_icon("set_bathroom", 'SPHERE'))
        col.operator("archiforge.set_apartment", text="Demo Apartment",
                     **_icon("set_apartment", 'HOME'))
        col.separator()
        col.label(text="Reference layouts, edit freely", icon='INFO')


classes = (
    ARCHIFORGE_OT_set_bathroom,
    ARCHIFORGE_OT_set_apartment,
    ARCHIFORGE_PT_sets,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    print("[ArchiForge] af_sets - registered")


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    print("[ArchiForge] af_sets - unregistered")
