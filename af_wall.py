# -*- coding: utf-8 -*-

# ╔══════════════════════════════════════════════════════════╗
# ║         ARCHIFORGE — af_wall.py                         ║
# ║         Muros Paramétricos para Blender 3.3 LTS         ║
# ║         GPL v3 — ArchiForge Devs                        ║
# ╚══════════════════════════════════════════════════════════╝

# <pep8 compliant>

import bpy
import bmesh
import math

from mathutils import Vector, Matrix

from .af_wall_path import build_wall_segments, offset_polyline

from bpy.types import (
    PropertyGroup,
    Operator,
    Panel,
    Object,
)
from bpy.props import (
    FloatProperty,
    IntProperty,
    BoolProperty,
    EnumProperty,
    CollectionProperty,
    PointerProperty,
    StringProperty,
)


# ════════════════════════════════════════════════════════════
#  CONSTANTES
# ════════════════════════════════════════════════════════════
AF_WALL_MIN_LEN    = 0.01
AF_WALL_MAX_LEN    = 1000.0
AF_WALL_MIN_HEIGHT = 0.01
AF_WALL_MAX_HEIGHT = 100.0
AF_WALL_MIN_WIDTH  = 0.001
AF_WALL_MAX_WIDTH  = 10.0

AF_WALL_PROP = "archiforge_wall"
_WALL_UPDATE_SUSPENDED = False
AF_WALL_DRAW_MAX_POINTS = 64
AF_WALL_DRAW_CLOSE_PIXELS = 14


# ════════════════════════════════════════════════════════════
#  PROPERTYGROUP — Segmento de muro
# ════════════════════════════════════════════════════════════
class AF_WallSegment(PropertyGroup):

    length : FloatProperty(
        name        = "Length",
        description = "Length of this wall segment",
        default     = 2.0,
        min         = AF_WALL_MIN_LEN,
        max         = AF_WALL_MAX_LEN,
        unit        = 'LENGTH',
        update      = lambda self, ctx: af_wall_update(self, ctx),
    )

    angle : FloatProperty(
        name        = "Angle",
        description = "Rotation angle relative to previous segment",
        default     = 0.0,
        min         = -math.pi,
        max         = math.pi,
        subtype     = 'ANGLE',
        update      = lambda self, ctx: af_wall_update(self, ctx),
    )

    enabled : BoolProperty(
        name        = "Enabled",
        description = "Toggle this segment on/off",
        default     = True,
        update      = lambda self, ctx: af_wall_update(self, ctx),
    )


# ════════════════════════════════════════════════════════════
#  PROPERTYGROUP — Muro completo
# ════════════════════════════════════════════════════════════
class AF_WallProperties(PropertyGroup):

    height : FloatProperty(
        name        = "Height",
        description = "Wall total height",
        default     = 2.7,
        min         = AF_WALL_MIN_HEIGHT,
        max         = AF_WALL_MAX_HEIGHT,
        unit        = 'LENGTH',
        update      = lambda self, ctx: af_wall_update(self, ctx),
    )

    width : FloatProperty(
        name        = "Width (Thickness)",
        description = "Wall thickness",
        default     = 0.20,
        min         = AF_WALL_MIN_WIDTH,
        max         = AF_WALL_MAX_WIDTH,
        unit        = 'LENGTH',
        update      = lambda self, ctx: af_wall_update(self, ctx),
    )

    n_parts : IntProperty(
        name        = "Segments",
        description = "Number of wall segments",
        default     = 1,
        min         = 1,
        max         = 64,
        update      = lambda self, ctx: af_wall_parts_update(self, ctx),
    )

    parts : CollectionProperty(
        name = "Parts",
        type = AF_WallSegment,
    )

    flip : BoolProperty(
        name        = "Flip",
        description = "Flip wall direction (inside/outside)",
        default     = False,
        update      = lambda self, ctx: af_wall_update(self, ctx),
    )

    closed : BoolProperty(
        name        = "Closed",
        description = "Close the wall loop",
        default     = False,
        update      = lambda self, ctx: af_wall_update(self, ctx),
    )

    # ── Zócalo ───────────────────────────────────────────────
    base_enable : BoolProperty(
        name        = "Base Molding",
        default     = False,
        update      = lambda self, ctx: af_wall_update(self, ctx),
    )
    base_height : FloatProperty(
        name        = "Base Height",
        default     = 0.10,
        min         = 0.001, max = 1.0,
        unit        = 'LENGTH',
        update      = lambda self, ctx: af_wall_update(self, ctx),
    )
    base_width : FloatProperty(
        name        = "Base Width",
        default     = 0.02,
        min         = 0.001, max = 0.5,
        unit        = 'LENGTH',
        update      = lambda self, ctx: af_wall_update(self, ctx),
    )

    # ── Cornisa ───────────────────────────────────────────────
    top_enable : BoolProperty(
        name        = "Top Molding",
        default     = False,
        update      = lambda self, ctx: af_wall_update(self, ctx),
    )
    top_height : FloatProperty(
        name        = "Top Height",
        default     = 0.10,
        min         = 0.001, max = 1.0,
        unit        = 'LENGTH',
        update      = lambda self, ctx: af_wall_update(self, ctx),
    )
    top_width : FloatProperty(
        name        = "Top Width",
        default     = 0.02,
        min         = 0.001, max = 0.5,
        unit        = 'LENGTH',
        update      = lambda self, ctx: af_wall_update(self, ctx),
    )

    # ── Material slots ───────────────────────────────────────
    mat_wall : IntProperty(name="Wall Material Index",  default=0, min=0)
    mat_base : IntProperty(name="Base Molding Material", default=1, min=0)
    mat_top  : IntProperty(name="Top Molding Material",  default=2, min=0)

    is_af_wall : BoolProperty(
        name="Is ArchiForge Wall", default=True, options={'HIDDEN'},
    )
    object_name : StringProperty(
        name="Object Name", default="", options={'HIDDEN'},
    )


# ════════════════════════════════════════════════════════════
#  GENERADOR DE GEOMETRÍA
# ════════════════════════════════════════════════════════════
class AF_WallGenerator:

    def __init__(self, props):
        self.props   = props
        self.verts   = []
        self.faces   = []
        self.mat_ids = []

    def _build_baseline(self):
        pts   = [Vector((0.0, 0.0))]
        angle = 0.0

        for seg in self.props.parts:
            if not seg.enabled:
                continue
            angle += seg.angle
            dx     = math.cos(angle) * seg.length
            dy     = math.sin(angle) * seg.length
            last   = pts[-1]
            pts.append(Vector((last.x + dx, last.y + dy)))

        return pts

    def _offset_polyline(self, pts, offset, closed=False):
        """Offset the wall baseline, using cyclic miters for room loops."""
        return [
            Vector(point) for point in offset_polyline(pts, offset, closed=closed)
        ]

    def generate(self):
        props  = self.props
        w      = props.width
        h      = props.height
        half_w = w * 0.5

        flip = -1.0 if props.flip else 1.0

        baseline = self._build_baseline()
        closed = bool(props.closed and len(baseline) >= 3)
        if closed and (baseline[-1] - baseline[0]).length < 1e-5:
            # A draw-tool loop stores its last edge explicitly. Keep one copy
            # of the first vertex so the cyclic mesh has a single seam vertex.
            baseline = baseline[:-1]
        if len(baseline) < (3 if closed else 2):
            return None

        pts_ext = self._offset_polyline(
            baseline, half_w * flip, closed=closed)
        pts_int = self._offset_polyline(
            baseline, -half_w * flip, closed=closed)

        n = len(baseline)
        edge_count = n if closed else n - 1
        bm = bmesh.new()

        v_ext_bot = [bm.verts.new(Vector((p.x, p.y, 0.0))) for p in pts_ext]
        v_ext_top = [bm.verts.new(Vector((p.x, p.y, h)))   for p in pts_ext]
        v_int_bot = [bm.verts.new(Vector((p.x, p.y, 0.0))) for p in pts_int]
        v_int_top = [bm.verts.new(Vector((p.x, p.y, h)))   for p in pts_int]

        bm.verts.ensure_lookup_table()
        mat_layer = bm.faces.layers.int.new("material_index")

        # Cada lado del polilínea genera una cara; en un recinto los índices
        # conectan de forma cíclica para que no queden tapas ni una junta abierta.
        for i in range(edge_count):
            j = (i + 1) % n
            bm.faces.new([
                v_ext_bot[i], v_ext_bot[j],
                v_ext_top[j], v_ext_top[i],
            ])[mat_layer] = props.mat_wall
            bm.faces.new([
                v_int_bot[j], v_int_bot[i],
                v_int_top[i], v_int_top[j],
            ])[mat_layer] = props.mat_wall
            bm.faces.new([
                v_ext_top[i], v_ext_top[j],
                v_int_top[j], v_int_top[i],
            ])[mat_layer] = props.mat_wall
            bm.faces.new([
                v_int_bot[i], v_int_bot[j],
                v_ext_bot[j], v_ext_bot[i],
            ])[mat_layer] = props.mat_wall

        if not closed:
            last = n - 1
            bm.faces.new([
                v_ext_bot[0], v_ext_top[0],
                v_int_top[0], v_int_bot[0],
            ])[mat_layer] = props.mat_wall
            bm.faces.new([
                v_int_bot[last], v_int_top[last],
                v_ext_top[last], v_ext_bot[last],
            ])[mat_layer] = props.mat_wall

        # ── Zócalo ───────────────────────────────────────────
        if props.base_enable:
            bw = props.base_width
            bh = props.base_height

            pts_be = self._offset_polyline(
                baseline, (half_w + bw) * flip, closed=closed)
            pts_bi = self._offset_polyline(
                baseline, -(half_w + bw) * flip, closed=closed)

            vb_ext_bot = [bm.verts.new(Vector((p.x, p.y, 0.0))) for p in pts_be]
            vb_ext_top = [bm.verts.new(Vector((p.x, p.y, bh)))  for p in pts_be]
            vb_int_bot = [bm.verts.new(Vector((p.x, p.y, 0.0))) for p in pts_bi]
            vb_int_top = [bm.verts.new(Vector((p.x, p.y, bh)))  for p in pts_bi]

            bm.verts.ensure_lookup_table()

            for i in range(edge_count):
                j = (i + 1) % n
                bm.faces.new([
                    vb_ext_bot[i], vb_ext_bot[j],
                    vb_ext_top[j], vb_ext_top[i],
                ])[mat_layer] = props.mat_base
                bm.faces.new([
                    vb_int_bot[j], vb_int_bot[i],
                    vb_int_top[i], vb_int_top[j],
                ])[mat_layer] = props.mat_base
                bm.faces.new([
                    vb_ext_top[i], vb_ext_top[j],
                    v_ext_bot[j], v_ext_bot[i],
                ])[mat_layer] = props.mat_base
                bm.faces.new([
                    v_int_bot[i], v_int_bot[j],
                    vb_int_top[j], vb_int_top[i],
                ])[mat_layer] = props.mat_base

        # ── Cornisa ───────────────────────────────────────────
        if props.top_enable:
            tw = props.top_width
            th = props.top_height
            z0 = h - th
            z1 = h

            pts_te = self._offset_polyline(
                baseline, (half_w + tw) * flip, closed=closed)
            pts_ti = self._offset_polyline(
                baseline, -(half_w + tw) * flip, closed=closed)

            vt_ext_bot = [bm.verts.new(Vector((p.x, p.y, z0))) for p in pts_te]
            vt_ext_top = [bm.verts.new(Vector((p.x, p.y, z1))) for p in pts_te]
            vt_int_bot = [bm.verts.new(Vector((p.x, p.y, z0))) for p in pts_ti]
            vt_int_top = [bm.verts.new(Vector((p.x, p.y, z1))) for p in pts_ti]

            bm.verts.ensure_lookup_table()

            for i in range(edge_count):
                j = (i + 1) % n
                bm.faces.new([
                    vt_ext_bot[i], vt_ext_bot[j],
                    vt_ext_top[j], vt_ext_top[i],
                ])[mat_layer] = props.mat_top
                bm.faces.new([
                    vt_int_bot[j], vt_int_bot[i],
                    vt_int_top[i], vt_int_top[j],
                ])[mat_layer] = props.mat_top
                bm.faces.new([
                    v_ext_top[i], v_ext_top[j],
                    vt_ext_bot[j], vt_ext_bot[i],
                ])[mat_layer] = props.mat_top
                bm.faces.new([
                    vt_int_bot[i], vt_int_bot[j],
                    v_int_top[j], v_int_top[i],
                ])[mat_layer] = props.mat_top
                bm.faces.new([
                    vt_ext_top[i], vt_ext_top[j],
                    vt_int_top[j], vt_int_top[i],
                ])[mat_layer] = props.mat_top

        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        return bm


# ════════════════════════════════════════════════════════════
#  UPDATE CALLBACKS
# ════════════════════════════════════════════════════════════
def _find_wall_object(props):
    name = props.object_name
    if name and name in bpy.data.objects:
        return bpy.data.objects[name]
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and hasattr(obj, AF_WALL_PROP):
            if getattr(obj, AF_WALL_PROP) is props:
                return obj
    return None


def af_wall_update(self, context):
    if _WALL_UPDATE_SUSPENDED:
        return
    obj = _find_wall_object(self)
    if obj is None:
        obj = context.active_object
    if obj is None or obj.type != 'MESH':
        return
    props = getattr(obj, AF_WALL_PROP, None)
    if props is None or not props.is_af_wall:
        return
    _rebuild_wall_mesh(obj, props)


def af_wall_parts_update(self, context):
    if _WALL_UPDATE_SUSPENDED:
        return
    obj = _find_wall_object(self)
    if obj is None:
        obj = context.active_object
    if obj is None:
        return

    props  = getattr(obj, AF_WALL_PROP, None)
    if props is None:
        return

    target = props.n_parts

    while len(props.parts) < target:
        seg         = props.parts.add()
        seg.length  = 2.0
        seg.angle   = 0.0
        seg.enabled = True

    while len(props.parts) > target:
        props.parts.remove(len(props.parts) - 1)

    _rebuild_wall_mesh(obj, props)


def _rebuild_wall_mesh(obj, props):
    gen = AF_WallGenerator(props)
    bm  = gen.generate()

    if bm is None:
        return

    me = obj.data
    bm.to_mesh(me)
    bm.free()
    me.update()

    # ── FIX: Flat shading — muros tienen aristas vivas ────────
    for poly in me.polygons:
        poly.use_smooth = False

    # ── Marcar todas las aristas como sharp ───────────────────
    for edge in me.edges:
        edge.use_edge_sharp = True

    # ── Desactivar auto smooth ────────────────────────────────
    if hasattr(me, "use_auto_smooth"):
        me.use_auto_smooth = False

    # ── Aplicar material index ────────────────────────────────
    if "material_index" in me.polygon_layers_int:
        layer = me.polygon_layers_int["material_index"]
        for poly in me.polygons:
            poly.material_index = layer.data[poly.index].value


# ════════════════════════════════════════════════════════════
#  OPERADORES
# ════════════════════════════════════════════════════════════
def _create_wall_object(context, name="AF_Wall"):
    me  = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, me)

    context.collection.objects.link(obj)
    context.view_layer.objects.active = obj
    obj.select_set(True)

    props             = obj.archiforge_wall
    props.is_af_wall  = True
    props.object_name = obj.name

    seg         = props.parts.add()
    seg.length  = 2.0
    seg.angle   = 0.0
    seg.enabled = True

    _setup_wall_materials(obj)
    return obj, props


def _setup_wall_materials(obj):
    me        = obj.data
    mat_names = ["AF.Wall", "AF.Wall.Base", "AF.Wall.Top"]

    for mname in mat_names:
        if mname not in bpy.data.materials:
            mat = bpy.data.materials.new(mname)
            mat.use_nodes = True
            if "Base" in mname:
                mat.diffuse_color = (0.8, 0.7, 0.6, 1.0)
            elif "Top" in mname:
                mat.diffuse_color = (0.9, 0.85, 0.8, 1.0)
            else:
                mat.diffuse_color = (0.9, 0.9, 0.9, 1.0)

        if mname not in [m.name for m in me.materials]:
            me.materials.append(bpy.data.materials[mname])


class ARCHIFORGE_OT_wall(Operator):
    bl_idname      = "archiforge.wall"
    bl_label       = "Add AF Wall"
    bl_description = "Add a parametric ArchiForge wall"
    bl_options     = {'REGISTER', 'UNDO'}

    height : FloatProperty(name="Height", default=2.7,
                           min=AF_WALL_MIN_HEIGHT, unit='LENGTH')
    width  : FloatProperty(name="Width",  default=0.20,
                           min=AF_WALL_MIN_WIDTH,  unit='LENGTH')
    length : FloatProperty(name="Length", default=2.0,
                           min=AF_WALL_MIN_LEN,    unit='LENGTH')

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        obj, props = _create_wall_object(context, "AF_Wall")
        props.height          = self.height
        props.width           = self.width
        props.parts[0].length = self.length
        _rebuild_wall_mesh(obj, props)
        self.report({'INFO'}, f"ArchiForge Wall created: {obj.name}")
        return {'FINISHED'}

    def invoke(self, context, event):
        return self.execute(context)


def _wall_draw_world_point(context, event, plane_z):
    """Intersect the viewport mouse ray with the horizontal draw plane."""
    try:
        from bpy_extras.view3d_utils import (
            region_2d_to_origin_3d,
            region_2d_to_vector_3d,
        )
        region = context.region
        rv3d = context.region_data
        if region is None or rv3d is None:
            return None
        coord = (event.mouse_region_x, event.mouse_region_y)
        origin = region_2d_to_origin_3d(region, rv3d, coord)
        direction = region_2d_to_vector_3d(region, rv3d, coord)
        if abs(direction.z) < 1e-7:
            return None
        distance = (plane_z - origin.z) / direction.z
        if distance < 0.0:
            return None
        point = origin + direction * distance
        return Vector((point.x, point.y, plane_z))
    except (AttributeError, ReferenceError, TypeError, ValueError):
        return None


def _wall_draw_screen_point(context, point):
    try:
        from bpy_extras.view3d_utils import location_3d_to_region_2d
        if context.region is None or context.region_data is None:
            return None
        return location_3d_to_region_2d(
            context.region, context.region_data, point)
    except (AttributeError, ReferenceError, TypeError, ValueError):
        return None


class ARCHIFORGE_OT_wall_draw(Operator):
    """Dibuja un muro continuo haciendo clic en sus vértices."""
    bl_idname = "archiforge.wall_draw"
    bl_label = "Draw Connected Wall / Room"
    bl_description = (
        "Draw a connected wall polyline; close a room by clicking its first "
        "point or pressing C"
    )
    bl_options = {'REGISTER', 'UNDO'}

    height: FloatProperty(
        name="Height", default=2.70, min=AF_WALL_MIN_HEIGHT,
        max=AF_WALL_MAX_HEIGHT, unit='LENGTH',
    )
    width: FloatProperty(
        name="Thickness", default=0.20, min=AF_WALL_MIN_WIDTH,
        max=AF_WALL_MAX_WIDTH, unit='LENGTH',
    )

    @classmethod
    def poll(cls, context):
        return (
            context.area is not None
            and context.area.type == 'VIEW_3D'
            and context.mode == 'OBJECT'
        )

    def _start_modal(self, context):
        self._points = []
        self._hover = None
        self._closing_hint = False
        self._draw_z = float(context.scene.cursor.location.z)
        self._draw_area = context.area
        self._draw_handle = None
        try:
            self._draw_handle = bpy.types.SpaceView3D.draw_handler_add(
                self._draw_preview, (), 'WINDOW', 'POST_PIXEL')
            context.window_manager.modal_handler_add(self)
        except Exception as exc:
            self._remove_draw_handler()
            self.report({'ERROR'}, f"No se pudo iniciar el dibujo: {exc}")
            return {'CANCELLED'}
        self._set_header(context)
        context.area.tag_redraw()
        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        return self._start_modal(context)

    def execute(self, context):
        return self._start_modal(context)

    def _set_header(self, context):
        if context.area is None:
            return
        context.area.header_text_set(
            "ArchiForge: clic para vértice · clic en inicio / C para cerrar "
            "· Enter: abierto · Backspace: quitar punto · Esc: cancelar")

    def _remove_draw_handler(self):
        handle = getattr(self, "_draw_handle", None)
        if handle is not None:
            try:
                bpy.types.SpaceView3D.draw_handler_remove(handle, 'WINDOW')
            except (ReferenceError, RuntimeError, TypeError):
                pass
            self._draw_handle = None
        area = getattr(self, "_draw_area", None)
        if area is not None:
            try:
                area.header_text_set(None)
                area.tag_redraw()
            except (ReferenceError, RuntimeError, TypeError):
                pass
            self._draw_area = None

    def _draw_preview(self):
        if not self._points:
            return
        try:
            import blf
            import gpu
            from gpu_extras.batch import batch_for_shader

            context = bpy.context
            if (context.area is None or context.area.type != 'VIEW_3D'
                    or context.region is None or context.region_data is None):
                return

            points = list(self._points)
            if self._hover is not None:
                points.append(self._hover)
            screen_points = []
            for point in points:
                screen = _wall_draw_screen_point(context, point)
                if screen is not None:
                    screen_points.append((screen.x, screen.y))
            if self._closing_hint and len(screen_points) > 1:
                first = _wall_draw_screen_point(context, self._points[0])
                if first is not None:
                    screen_points.append((first.x, first.y))
            if len(screen_points) < 2:
                return

            try:
                shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
            except Exception:
                # Compatibility with newer Blender GPU shader identifiers.
                shader = gpu.shader.from_builtin('UNIFORM_COLOR')
            gpu.state.blend_set('ALPHA')
            gpu.state.line_width_set(2.0)
            shader.bind()
            shader.uniform_float(
                "color", (0.20, 0.85, 1.0, 0.95) if not self._closing_hint
                else (0.25, 1.0, 0.35, 1.0))
            batch_for_shader(
                shader, 'LINE_STRIP', {"pos": screen_points}).draw(shader)

            gpu.state.point_size_set(7.0)
            point_batch = batch_for_shader(
                shader, 'POINTS', {"pos": screen_points[:-1]})
            point_batch.draw(shader)
            gpu.state.point_size_set(1.0)
            gpu.state.line_width_set(1.0)
            gpu.state.blend_set('NONE')

            font_id = 0
            blf.size(font_id, 14, 72)
            blf.position(font_id, 18, context.region.height - 28, 0)
            blf.color(font_id, 1.0, 1.0, 1.0, 1.0)
            blf.draw(
                font_id,
                "Clic: vértice | Clic en inicio o C: cerrar | "
                "Enter: terminar | Backspace: quitar punto | Esc: cancelar",
            )
        except Exception:
            # A drawing overlay must never interrupt viewport interaction.
            try:
                import gpu
                gpu.state.point_size_set(1.0)
                gpu.state.line_width_set(1.0)
                gpu.state.blend_set('NONE')
            except Exception:
                pass

    def _snap_point(self, context, point):
        point = Vector((point.x, point.y, self._draw_z))
        snap = getattr(context.scene, "af_snap", None)
        if snap is None or not getattr(snap, "enabled", False):
            return point

        if getattr(snap, "grid_snap", False):
            grid = max(0.001, float(snap.grid_size))
            point.x = round(point.x / grid) * grid
            point.y = round(point.y / grid) * grid

        if self._points and getattr(snap, "angle_snap", False):
            delta = point - self._points[-1]
            distance = math.hypot(delta.x, delta.y)
            if distance > 1e-6:
                step = math.radians(max(1, int(snap.angle_step)))
                angle = math.atan2(delta.y, delta.x)
                angle = round(angle / step) * step
                point.x = self._points[-1].x + math.cos(angle) * distance
                point.y = self._points[-1].y + math.sin(angle) * distance
        return point

    def _near_first_point(self, context, event):
        if len(self._points) < 3:
            return False
        screen = _wall_draw_screen_point(context, self._points[0])
        if screen is None:
            return False
        return math.hypot(
            screen.x - event.mouse_region_x,
            screen.y - event.mouse_region_y,
        ) <= AF_WALL_DRAW_CLOSE_PIXELS

    def _create_wall(self, context, closed, edges):
        global _WALL_UPDATE_SUSPENDED

        points = list(self._points)
        segment_count = len(edges)
        if not 1 <= segment_count <= AF_WALL_DRAW_MAX_POINTS:
            raise ValueError(
                f"El muro admite entre 1 y {AF_WALL_DRAW_MAX_POINTS} segmentos"
            )

        bpy.ops.object.select_all(action='DESELECT')
        name = "AF_RoomWall" if closed else "AF_Wall"
        obj, props = _create_wall_object(context, name)
        mesh = obj.data
        obj.location = points[0]

        try:
            _WALL_UPDATE_SUSPENDED = True
            try:
                props.n_parts = segment_count
                while len(props.parts) < segment_count:
                    props.parts.add()
                while len(props.parts) > segment_count:
                    props.parts.remove(len(props.parts) - 1)
                props.height = self.height
                props.width = self.width
                props.closed = closed
                props.is_af_wall = True
                props.object_name = obj.name

                for index, (length, relative_angle) in enumerate(edges):
                    segment = props.parts[index]
                    segment.enabled = True
                    segment.length = length
                    segment.angle = relative_angle
            finally:
                _WALL_UPDATE_SUSPENDED = False

            _rebuild_wall_mesh(obj, props)
            return obj
        except Exception:
            # Do not leave an empty or partially generated parametric object
            # behind if Blender fails while rebuilding the mesh.
            if obj.name in bpy.data.objects:
                bpy.data.objects.remove(obj, do_unlink=True)
            if mesh.users == 0 and mesh.name in bpy.data.meshes:
                bpy.data.meshes.remove(mesh)
            raise
        finally:
            _WALL_UPDATE_SUSPENDED = False

    def _finish(self, context, closed):
        try:
            edges = build_wall_segments(
                self._points,
                closed=closed,
                min_segment_length=AF_WALL_MIN_LEN,
                max_segments=AF_WALL_DRAW_MAX_POINTS,
            )
        except ValueError as exc:
            self.report({'WARNING'}, str(exc))
            return {'RUNNING_MODAL'}

        try:
            obj = self._create_wall(context, closed, edges)
        except Exception as exc:
            self.report({'ERROR'}, f"No se pudo crear el muro: {exc}")
            self._remove_draw_handler()
            return {'CANCELLED'}
        self._remove_draw_handler()
        self.report({'INFO'},
                    f"Recinto cerrado creado: {obj.name}" if closed
                    else f"Muro creado: {obj.name}")
        return {'FINISHED'}

    def modal(self, context, event):
        if context.area is None or context.area.type != 'VIEW_3D':
            self._remove_draw_handler()
            return {'CANCELLED'}

        if event.type in {'ESC', 'RIGHTMOUSE'} and event.value == 'PRESS':
            self._remove_draw_handler()
            return {'CANCELLED'}

        if event.type == 'MOUSEMOVE':
            self._closing_hint = self._near_first_point(context, event)
            if self._closing_hint:
                self._hover = self._points[0].copy()
            else:
                point = _wall_draw_world_point(context, event, self._draw_z)
                self._hover = (
                    self._snap_point(context, point)
                    if point is not None else None
                )
            context.area.tag_redraw()
            return {'RUNNING_MODAL'}

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            if self._near_first_point(context, event):
                return self._finish(context, closed=True)
            point = _wall_draw_world_point(context, event, self._draw_z)
            if point is None:
                self.report({'WARNING'},
                            "No se pudo intersectar el cursor con el plano de dibujo")
                return {'RUNNING_MODAL'}
            point = self._snap_point(context, point)
            if self._points and (point - self._points[-1]).length < AF_WALL_MIN_LEN:
                return {'RUNNING_MODAL'}
            if len(self._points) >= AF_WALL_DRAW_MAX_POINTS:
                self.report({'WARNING'}, "Máximo de 64 vértices alcanzado")
                return {'RUNNING_MODAL'}
            self._points.append(point)
            self._hover = point.copy()
            context.area.tag_redraw()
            return {'RUNNING_MODAL'}

        if event.type in {'BACK_SPACE', 'DEL'} and event.value == 'PRESS':
            if self._points:
                self._points.pop()
                self._hover = self._points[-1].copy() if self._points else None
                self._closing_hint = False
                context.area.tag_redraw()
            return {'RUNNING_MODAL'}

        if event.type == 'C' and event.value == 'PRESS':
            return self._finish(context, closed=True)
        if event.type in {'RET', 'NUMPAD_ENTER'} and event.value == 'PRESS':
            return self._finish(context, closed=False)
        if event.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            return {'PASS_THROUGH'}
        return {'RUNNING_MODAL'}


class ARCHIFORGE_OT_wall_update(Operator):
    bl_idname      = "archiforge.wall_update"
    bl_label       = "Update Wall"
    bl_description = "Force regeneration of the selected wall"
    bl_options     = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj is not None and obj.type == 'MESH'
            and hasattr(obj, AF_WALL_PROP)
            and obj.archiforge_wall.is_af_wall
        )

    def execute(self, context):
        obj = context.active_object
        _rebuild_wall_mesh(obj, obj.archiforge_wall)
        self.report({'INFO'}, "Wall updated")
        return {'FINISHED'}


class ARCHIFORGE_OT_wall_add_segment(Operator):
    bl_idname      = "archiforge.wall_add_segment"
    bl_label       = "Add Segment"
    bl_description = "Add a new segment to the wall"
    bl_options     = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj is not None and obj.type == 'MESH'
            and hasattr(obj, AF_WALL_PROP)
            and obj.archiforge_wall.is_af_wall
        )

    def execute(self, context):
        context.active_object.archiforge_wall.n_parts += 1
        return {'FINISHED'}


class ARCHIFORGE_OT_wall_remove_segment(Operator):
    bl_idname      = "archiforge.wall_remove_segment"
    bl_label       = "Remove Segment"
    bl_description = "Remove the last segment from the wall"
    bl_options     = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj is not None and obj.type == 'MESH'
            and hasattr(obj, AF_WALL_PROP)
            and obj.archiforge_wall.is_af_wall
            and obj.archiforge_wall.n_parts > 1
        )

    def execute(self, context):
        context.active_object.archiforge_wall.n_parts -= 1
        return {'FINISHED'}


class ARCHIFORGE_OT_wall_flip(Operator):
    bl_idname      = "archiforge.wall_flip"
    bl_label       = "Flip Wall"
    bl_description = "Flip wall interior/exterior sides"
    bl_options     = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj is not None and obj.type == 'MESH'
            and hasattr(obj, AF_WALL_PROP)
            and obj.archiforge_wall.is_af_wall
        )

    def execute(self, context):
        props      = context.active_object.archiforge_wall
        props.flip = not props.flip
        return {'FINISHED'}


# ════════════════════════════════════════════════════════════
#  PANEL
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_PT_wall(Panel):
    bl_label       = "Wall Properties"
    bl_idname      = "ARCHIFORGE_PT_wall"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "ArchiForge"
    bl_context     = "objectmode"
    bl_options     = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj is not None and obj.type == 'MESH'
            and hasattr(obj, AF_WALL_PROP)
            and obj.archiforge_wall.is_af_wall
        )

    def draw_header(self, context):
        self.layout.label(text="", icon='SNAP_FACE')

    def draw(self, context):
        obj    = context.active_object
        props  = obj.archiforge_wall
        layout = self.layout
        layout.use_property_split     = True
        layout.use_property_decorate  = False

        # ── Dimensiones ───────────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Dimensions", icon='ARROW_LEFTRIGHT')
        col.prop(props, "height")
        col.prop(props, "width")

        # ── Opciones ──────────────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Options", icon='MODIFIER')
        row = col.row(align=True)
        row.prop(props, "flip",   toggle=True, icon='UV_SYNC_SELECT')
        row.prop(props, "closed", toggle=True, icon='LINKED')

        # ── Segmentos ─────────────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        row = col.row(align=True)
        row.label(text="Segments", icon='MESH_DATA')
        row.prop(props, "n_parts", text="")

        row = col.row(align=True)
        row.operator("archiforge.wall_add_segment",    text="Add",    icon='ADD')
        row.operator("archiforge.wall_remove_segment", text="Remove", icon='REMOVE')

        col.separator(factor=0.5)

        for i, seg in enumerate(props.parts):
            seg_box = col.box()
            row     = seg_box.row(align=True)
            row.prop(
                seg, "enabled",
                text=f"Seg {i+1}",
                icon='CHECKMARK' if seg.enabled else 'PANEL_CLOSE',
                toggle=True,
            )
            if seg.enabled:
                inner = seg_box.column(align=True)
                inner.prop(seg, "length")
                if i > 0:
                    inner.prop(seg, "angle")

        # ── Zócalo ────────────────────────────────────────────
        box = layout.box()
        row = box.row(align=True)
        row.prop(
            props, "base_enable", text="Base Molding",
            icon='TRIA_DOWN' if props.base_enable else 'TRIA_RIGHT',
            toggle=True,
        )
        if props.base_enable:
            col = box.column(align=True)
            col.prop(props, "base_height")
            col.prop(props, "base_width")

        # ── Cornisa ───────────────────────────────────────────
        box = layout.box()
        row = box.row(align=True)
        row.prop(
            props, "top_enable", text="Top Molding",
            icon='TRIA_DOWN' if props.top_enable else 'TRIA_RIGHT',
            toggle=True,
        )
        if props.top_enable:
            col = box.column(align=True)
            col.prop(props, "top_height")
            col.prop(props, "top_width")

        # ── Materiales ────────────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Material Slots", icon='MATERIAL')
        col.prop(props, "mat_wall", text="Wall")
        if props.base_enable:
            col.prop(props, "mat_base", text="Base")
        if props.top_enable:
            col.prop(props, "mat_top", text="Top")

        # ── Acciones ──────────────────────────────────────────
        layout.separator()
        layout.operator("archiforge.wall_update",
                        text="Force Update", icon='FILE_REFRESH')
        layout.operator("archiforge.wall_flip",
                        text="Flip Wall", icon='UV_SYNC_SELECT')


# ════════════════════════════════════════════════════════════
#  REGISTRO
# ════════════════════════════════════════════════════════════
classes = [
    AF_WallSegment,
    AF_WallProperties,
    ARCHIFORGE_OT_wall,
    ARCHIFORGE_OT_wall_draw,
    ARCHIFORGE_OT_wall_update,
    ARCHIFORGE_OT_wall_add_segment,
    ARCHIFORGE_OT_wall_remove_segment,
    ARCHIFORGE_OT_wall_flip,
    ARCHIFORGE_PT_wall,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Object.archiforge_wall = PointerProperty(
        type        = AF_WallProperties,
        name        = "ArchiForge Wall",
        description = "ArchiForge parametric wall properties",
    )
    print("[ArchiForge] ✅ af_wall — registered")


def unregister():
    if hasattr(bpy.types.Object, "archiforge_wall"):
        del bpy.types.Object.archiforge_wall

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    print("[ArchiForge] 🔴 af_wall — unregistered")