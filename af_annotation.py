# -*- coding: utf-8 -*-

# ╔══════════════════════════════════════════════════════════╗
# ║              ARCHIFORGE — af_annotation.py              ║
# ║              Cotas, ejes estructurales y norte          ║
# ║              GPL v3 — ArchiForge Devs                   ║
# ╚══════════════════════════════════════════════════════════╝

# <pep8 compliant>

"""Plan annotations: dimension lines, structural grid axes and a north
arrow, generated as curve objects (lines with a small bevel so they also
render) plus text objects, all inside the ``AF_Annotations`` collection.

The geometry comes from ``af_annotation_geometry`` (pure, tested); this
module only turns polylines and labels into Blender data. Annotation
objects carry the custom property ``af_annotation`` and are never
counted by the quantity takeoff.
"""

import math

import bpy
from mathutils import Vector
from bpy.types import Operator, Panel
from bpy.props import (
    BoolProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
)

from . import af_annotation_geometry as geo
from . import af_units

try:
    from .af_i18n import tr_report as _tr
except ImportError:  # pragma: no cover - fuera del paquete
    def _tr(text):
        return text

try:
    from .af_outline_draw import _mouse_world_point, _screen_point
except ImportError:  # pragma: no cover
    _mouse_world_point = None
    _screen_point = None

ANNOTATION_COLLECTION = "AF_Annotations"
ANNOTATION_PROP = "af_annotation"
ANNOTATION_MATERIAL = "AF.Annotation"


# ════════════════════════════════════════════════════════════
#  Helpers
# ════════════════════════════════════════════════════════════
def _unit_system(context):
    try:
        prefs = context.preferences.addons[__package__].preferences
        return af_units.normalize(getattr(prefs, "unit_system", af_units.METRIC))
    except Exception:  # noqa: BLE001
        return af_units.METRIC


def _annotation_collection(context):
    scene = context.scene
    coll = bpy.data.collections.get(ANNOTATION_COLLECTION)
    if coll is None:
        coll = bpy.data.collections.new(ANNOTATION_COLLECTION)
    if coll.name not in scene.collection.children:
        try:
            scene.collection.children.link(coll)
        except RuntimeError:
            pass
    return coll


def _annotation_material():
    mat = bpy.data.materials.get(ANNOTATION_MATERIAL)
    if mat is None:
        mat = bpy.data.materials.new(ANNOTATION_MATERIAL)
        mat.diffuse_color = (0.05, 0.05, 0.05, 1.0)
        mat.use_nodes = True
        try:
            bsdf = mat.node_tree.nodes.get("Principled BSDF")
            if bsdf is not None:
                bsdf.inputs["Base Color"].default_value = (0.02, 0.02, 0.02, 1.0)
                bsdf.inputs["Roughness"].default_value = 0.9
        except Exception:  # noqa: BLE001
            pass
        mat["af_material"] = True
        mat["af_category"] = "Annotation"
    return mat


def _link(obj, context, kind):
    _annotation_collection(context).objects.link(obj)
    obj[ANNOTATION_PROP] = kind
    try:
        obj.data.materials.append(_annotation_material())
    except Exception:  # noqa: BLE001
        pass
    return obj


def _new_curve_object(name, polylines, thickness, context, kind):
    """Curve object with one POLY spline per polyline."""
    curve = bpy.data.curves.new(name, type='CURVE')
    curve.dimensions = '3D'
    curve.bevel_depth = max(0.0, float(thickness)) / 2.0
    curve.bevel_resolution = 2
    curve.fill_mode = 'FULL'
    curve.use_fill_caps = True
    for points in polylines:
        if len(points) < 2:
            continue
        closed = len(points) > 2 and _same_point(points[0], points[-1])
        coords = points[:-1] if closed else points
        spline = curve.splines.new('POLY')
        spline.points.add(len(coords) - 1)
        for point, (x, y, z) in zip(spline.points, coords):
            point.co = (x, y, z, 1.0)
        spline.use_cyclic_u = closed
    obj = bpy.data.objects.new(name, curve)
    return _link(obj, context, kind)


def _same_point(a, b, eps=1e-6):
    return all(abs(a[i] - b[i]) < eps for i in range(3))


def _new_text_object(name, text, position, rotation, size, context, kind,
                     parent=None):
    font = bpy.data.curves.new(name, type='FONT')
    font.body = text
    font.size = max(0.01, float(size))
    font.align_x = 'CENTER'
    font.align_y = 'CENTER'
    obj = bpy.data.objects.new(name, font)
    obj.location = Vector(position)
    obj.rotation_euler = (0.0, 0.0, float(rotation))
    _link(obj, context, kind)
    if parent is not None:
        obj.parent = parent
        obj.matrix_parent_inverse = parent.matrix_world.inverted()
    return obj


def _select(context, objects):
    try:
        for obj in context.selected_objects:
            obj.select_set(False)
        for obj in objects:
            obj.select_set(True)
        if objects:
            context.view_layer.objects.active = objects[0]
    except Exception:  # noqa: BLE001
        pass


def _world_bounds(obj):
    corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    xs = [c.x for c in corners]
    ys = [c.y for c in corners]
    zs = [c.z for c in corners]
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def _create_dimension(context, result, prefix, text_size, thickness):
    curve = _new_curve_object(prefix, result["polylines"], thickness,
                              context, 'DIMENSION')
    label = result["label"]
    _new_text_object(prefix + "_txt", label["text"], label["position"],
                     label["rotation"], text_size, context, 'DIMENSION',
                     parent=curve)
    return curve


def annotation_objects(scene):
    return [obj for obj in scene.objects if obj.get(ANNOTATION_PROP)]


# ════════════════════════════════════════════════════════════
#  OP: cotas del contorno de los objetos seleccionados
# ════════════════════════════════════════════════════════════
class _DimensionSettingsMixin:
    offset : FloatProperty(
        name="Offset", default=0.5, min=0.05, max=10.0, unit='LENGTH',
        description="Distance from the measured edge to the dimension line")
    text_size : FloatProperty(
        name="Text Size", default=0.18, min=0.02, max=2.0, unit='LENGTH',
        description="Height of the dimension text")
    line_thickness : FloatProperty(
        name="Line Thickness", default=0.008, min=0.0, max=0.1,
        unit='LENGTH',
        description="Bevel of the annotation lines so they render; 0 for "
                    "viewport-only wire lines")
    decimals : IntProperty(
        name="Decimals", default=2, min=0, max=3,
        description="Decimals of metric dimension labels")


class ARCHIFORGE_OT_dimension_selected(_DimensionSettingsMixin, Operator):
    bl_idname = "archiforge.dimension_selected"
    bl_label = "Dimension Selected"
    bl_description = ("Add width and depth dimension lines around the plan "
                      "footprint of each selected object")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return any(o.type in {'MESH', 'CURVE'} for o in context.selected_objects)

    def execute(self, context):
        created = []
        system = _unit_system(context)
        try:
            context.view_layer.update()   # bound_box of freshly built objects
        except Exception:  # noqa: BLE001
            pass
        for obj in list(context.selected_objects):
            if obj.type not in {'MESH', 'CURVE'} or obj.get(ANNOTATION_PROP):
                continue
            lo, hi = _world_bounds(obj)
            for index, result in enumerate(geo.footprint_dimensions(
                    lo, hi, offset=self.offset, unit_system=system,
                    decimals=self.decimals)):
                created.append(_create_dimension(
                    context, result, "AF_Dim_{}_{}".format(obj.name, index),
                    self.text_size, self.line_thickness))
        if not created:
            self.report({'WARNING'}, _tr("No measurable objects selected"))
            return {'CANCELLED'}
        _select(context, created)
        self.report({'INFO'}, _tr("{} dimension(s) created").format(len(created)))
        return {'FINISHED'}


# ════════════════════════════════════════════════════════════
#  OP: cota entre dos clics en el plano del cursor
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_OT_dimension_draw(_DimensionSettingsMixin, Operator):
    bl_idname = "archiforge.dimension_draw"
    bl_label = "Draw Dimension"
    bl_description = ("Click two points in the viewport to add a dimension "
                      "line between them (ESC to cancel)")
    bl_options = {'REGISTER', 'UNDO'}

    start : FloatVectorProperty(name="Start", size=3, subtype='XYZ',
                                unit='LENGTH', options={'HIDDEN'})
    end : FloatVectorProperty(name="End", size=3, subtype='XYZ',
                              unit='LENGTH', options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        return context.area is not None and context.area.type == 'VIEW_3D'

    def invoke(self, context, event):
        if _mouse_world_point is None:
            self.report({'ERROR'}, _tr("Viewport drawing is not available"))
            return {'CANCELLED'}
        self._points = []
        self._hover = None
        self._z = float(context.scene.cursor.location.z)
        self._area = context.area
        self._handle = None
        try:
            self._handle = bpy.types.SpaceView3D.draw_handler_add(
                self._draw_preview, (), 'WINDOW', 'POST_PIXEL')
            context.window_manager.modal_handler_add(self)
        except Exception as exc:  # noqa: BLE001
            self._cleanup()
            self.report({'ERROR'}, _tr("No se pudo iniciar el dibujo: {}").format(exc))
            return {'CANCELLED'}
        context.area.header_text_set(_tr(
            "ArchiForge Dimension: click start and end point · Esc: cancel"))
        return {'RUNNING_MODAL'}

    def _cleanup(self):
        handle = getattr(self, "_handle", None)
        if handle is not None:
            try:
                bpy.types.SpaceView3D.draw_handler_remove(handle, 'WINDOW')
            except Exception:  # noqa: BLE001
                pass
            self._handle = None
        area = getattr(self, "_area", None)
        if area is not None:
            try:
                area.header_text_set(None)
                area.tag_redraw()
            except Exception:  # noqa: BLE001
                pass

    def _snap(self, context, point):
        snap = getattr(context.scene, "af_snap", None)
        if snap is not None and getattr(snap, "enabled", False) \
                and getattr(snap, "grid_snap", False):
            grid = max(0.001, float(snap.grid_size))
            point = Vector((round(point.x / grid) * grid,
                            round(point.y / grid) * grid, self._z))
        return point

    def _draw_preview(self):
        try:
            import gpu
            from gpu_extras.batch import batch_for_shader
            context = bpy.context
            if not self._points or self._hover is None:
                return
            pts = []
            for p in (self._points[0], self._hover):
                s = _screen_point(context, p)
                if s is not None:
                    pts.append((s.x, s.y))
            if len(pts) < 2:
                return
            try:
                shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
            except Exception:  # noqa: BLE001
                shader = gpu.shader.from_builtin('UNIFORM_COLOR')
            gpu.state.blend_set('ALPHA')
            gpu.state.line_width_set(2.0)
            shader.bind()
            shader.uniform_float("color", (1.0, 0.75, 0.2, 0.95))
            batch_for_shader(shader, 'LINES', {"pos": pts}).draw(shader)
            gpu.state.line_width_set(1.0)
            gpu.state.blend_set('NONE')
        except Exception:  # noqa: BLE001 - never break the viewport
            pass

    def modal(self, context, event):
        if context.area is None or context.area.type != 'VIEW_3D':
            self._cleanup()
            return {'CANCELLED'}
        if event.type in {'ESC', 'RIGHTMOUSE'} and event.value == 'PRESS':
            self._cleanup()
            return {'CANCELLED'}
        if event.type == 'MOUSEMOVE':
            point = _mouse_world_point(context, event, self._z)
            self._hover = self._snap(context, point) if point is not None else None
            context.area.tag_redraw()
            return {'RUNNING_MODAL'}
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            point = _mouse_world_point(context, event, self._z)
            if point is None:
                self.report({'WARNING'},
                            _tr("No se pudo intersectar el cursor con el plano de dibujo"))
                return {'RUNNING_MODAL'}
            self._points.append(self._snap(context, point))
            if len(self._points) == 2:
                self._cleanup()
                self.start = tuple(self._points[0])
                self.end = tuple(self._points[1])
                return self.execute(context)
            return {'RUNNING_MODAL'}
        if event.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            return {'PASS_THROUGH'}
        return {'RUNNING_MODAL'}

    def execute(self, context):
        """Build from ``start``/``end`` (also used by the redo panel)."""
        p0, p1 = Vector(self.start), Vector(self.end)
        if (p1 - p0).length < 0.01:
            self.report({'WARNING'}, _tr("Dimension points are too close"))
            return {'CANCELLED'}
        result = geo.dimension_line(
            tuple(p0), tuple(p1), offset=self.offset,
            unit_system=_unit_system(context), decimals=self.decimals)
        curve = _create_dimension(context, result, "AF_Dim", self.text_size,
                                  self.line_thickness)
        _select(context, [curve])
        self.report({'INFO'}, _tr("Dimension created: {}").format(
            result["label"]["text"]))
        return {'FINISHED'}


# ════════════════════════════════════════════════════════════
#  OP: ejes estructurales con burbuja
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_OT_grid_axes(Operator):
    bl_idname = "archiforge.grid_axes"
    bl_label = "Add Grid Axes"
    bl_description = ("Add structural axes from the 3D cursor: numbered "
                      "axes along X and lettered axes along Y, each ending "
                      "in a bubble")
    bl_options = {'REGISTER', 'UNDO'}

    count_x : IntProperty(name="Axes along X", default=4, min=1, max=40,
                          description="Number of numbered axes (1, 2, 3…)")
    spacing_x : FloatProperty(name="Spacing X", default=5.0, min=0.1,
                              max=100.0, unit='LENGTH')
    count_y : IntProperty(name="Axes along Y", default=3, min=1, max=40,
                          description="Number of lettered axes (A, B, C…)")
    spacing_y : FloatProperty(name="Spacing Y", default=4.0, min=0.1,
                              max=100.0, unit='LENGTH')
    extension : FloatProperty(
        name="Extension", default=1.0, min=0.0, max=20.0, unit='LENGTH',
        description="How far the axis lines run past the grid")
    bubble_radius : FloatProperty(name="Bubble Radius", default=0.30,
                                  min=0.05, max=2.0, unit='LENGTH')
    both_ends : BoolProperty(name="Bubbles at Both Ends", default=False)
    text_size : FloatProperty(name="Text Size", default=0.28, min=0.02,
                              max=2.0, unit='LENGTH')
    line_thickness : FloatProperty(name="Line Thickness", default=0.006,
                                   min=0.0, max=0.1, unit='LENGTH')

    def execute(self, context):
        origin = tuple(context.scene.cursor.location)
        grid = geo.grid_axes(
            geo.regular_positions(self.count_x, self.spacing_x),
            geo.regular_positions(self.count_y, self.spacing_y),
            origin=origin, extension=self.extension,
            bubble_radius=self.bubble_radius, both_ends=self.both_ends)
        polylines = []
        labels = []
        for axis in grid["axes"]:
            polylines.append(axis["line"])
            for centre in axis["bubbles"]:
                ring = geo.circle_points(centre, grid["bubble_radius"], 32)
                ring.append(ring[0])
                polylines.append(ring)
                labels.append((axis["name"], centre))
        curve = _new_curve_object("AF_Axes", polylines, self.line_thickness,
                                  context, 'AXES')
        for name, centre in labels:
            _new_text_object("AF_Axis_" + name, name, centre, 0.0,
                             self.text_size, context, 'AXES', parent=curve)
        _select(context, [curve])
        self.report({'INFO'}, _tr("Grid axes created: {}").format(
            len(grid["axes"])))
        return {'FINISHED'}


# ════════════════════════════════════════════════════════════
#  OP: símbolo de norte
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_OT_north_arrow(Operator):
    bl_idname = "archiforge.north_arrow"
    bl_label = "Add North Arrow"
    bl_description = "Add a north symbol at the 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}

    size : FloatProperty(name="Size", default=1.0, min=0.1, max=20.0,
                         unit='LENGTH')
    angle : FloatProperty(
        name="North Angle", default=0.0, min=-math.pi, max=math.pi,
        subtype='ANGLE',
        description="Rotation of north counter-clockwise from +Y")
    line_thickness : FloatProperty(name="Line Thickness", default=0.01,
                                   min=0.0, max=0.1, unit='LENGTH')

    def execute(self, context):
        result = geo.north_arrow(tuple(context.scene.cursor.location),
                                 size=self.size, angle=self.angle)
        curve = _new_curve_object("AF_North", result["polylines"],
                                  self.line_thickness, context, 'NORTH')
        label = result["label"]
        _new_text_object("AF_North_txt", label["text"], label["position"],
                         label["rotation"], self.size * 0.3, context,
                         'NORTH', parent=curve)
        _select(context, [curve])
        self.report({'INFO'}, _tr("North arrow created"))
        return {'FINISHED'}


# ════════════════════════════════════════════════════════════
#  OP: mostrar / ocultar anotaciones
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_OT_annotations_visibility(Operator):
    bl_idname = "archiforge.annotations_visibility"
    bl_label = "Show/Hide Annotations"
    bl_description = "Toggle the visibility of every ArchiForge annotation"
    bl_options = {'REGISTER', 'UNDO'}

    show : BoolProperty(name="Show", default=True)

    def execute(self, context):
        objects = annotation_objects(context.scene)
        for obj in objects:
            try:
                obj.hide_set(not self.show)
                obj.hide_render = not self.show
            except Exception:  # noqa: BLE001
                pass
        self.report({'INFO'}, (_tr("{} annotation(s) shown") if self.show
                               else _tr("{} annotation(s) hidden")).format(
                                   len(objects)))
        return {'FINISHED'}


# ════════════════════════════════════════════════════════════
#  PANEL
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_PT_annotations(Panel):
    bl_label = "Annotations"
    bl_idname = "ARCHIFORGE_PT_annotations"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ArchiForge"
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        self.layout.label(text="", icon='DRIVER_DISTANCE')

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.label(text="Dimensions", icon='DRIVER_DISTANCE')
        col.operator("archiforge.dimension_selected", text="Dimension Selected",
                     icon='ARROW_LEFTRIGHT')
        col.operator("archiforge.dimension_draw", text="Draw Dimension",
                     icon='GREASEPENCIL')
        col.separator()
        col.label(text="Plan Symbols", icon='GRID')
        col.operator("archiforge.grid_axes", text="Grid Axes", icon='GRID')
        col.operator("archiforge.north_arrow", text="North Arrow",
                     icon='ORIENTATION_VIEW')
        count = len(annotation_objects(context.scene))
        if count:
            col.separator()
            row = col.row(align=True)
            row.operator("archiforge.annotations_visibility", text="Show",
                         icon='HIDE_OFF').show = True
            row.operator("archiforge.annotations_visibility", text="Hide",
                         icon='HIDE_ON').show = False
            col.label(text=_tr("{} annotation object(s)").format(count),
                      icon='INFO')


classes = (
    ARCHIFORGE_OT_dimension_selected,
    ARCHIFORGE_OT_dimension_draw,
    ARCHIFORGE_OT_grid_axes,
    ARCHIFORGE_OT_north_arrow,
    ARCHIFORGE_OT_annotations_visibility,
    ARCHIFORGE_PT_annotations,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    print("[ArchiForge] af_annotation - registered")


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    print("[ArchiForge] af_annotation - unregistered")
