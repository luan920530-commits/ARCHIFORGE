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

    def _offset_polyline(self, pts, offset):
        result = []

        for i, pt in enumerate(pts):
            if i == 0:
                if len(pts) > 1:
                    d = (pts[1] - pts[0]).normalized()
                else:
                    d = Vector((1.0, 0.0))
                n = Vector((-d.y, d.x))
            elif i == len(pts) - 1:
                d = (pts[-1] - pts[-2]).normalized()
                n = Vector((-d.y, d.x))
            else:
                d1 = (pt - pts[i - 1]).normalized()
                d2 = (pts[i + 1] - pt).normalized()
                n1 = Vector((-d1.y, d1.x))
                n2 = Vector((-d2.y, d2.x))
                n  = (n1 + n2).normalized()

                cos_a = n.dot(n1)
                if abs(cos_a) > 0.001:
                    n = n / cos_a

            result.append(pt + n * offset)

        return result

    def generate(self):
        props  = self.props
        w      = props.width
        h      = props.height
        half_w = w * 0.5

        flip = -1.0 if props.flip else 1.0

        baseline = self._build_baseline()
        if len(baseline) < 2:
            return None

        pts_ext = self._offset_polyline(baseline,  half_w * flip)
        pts_int = self._offset_polyline(baseline, -half_w * flip)

        n  = len(baseline)
        bm = bmesh.new()

        v_ext_bot = [bm.verts.new(Vector((p.x, p.y, 0.0))) for p in pts_ext]
        v_ext_top = [bm.verts.new(Vector((p.x, p.y, h)))   for p in pts_ext]
        v_int_bot = [bm.verts.new(Vector((p.x, p.y, 0.0))) for p in pts_int]
        v_int_top = [bm.verts.new(Vector((p.x, p.y, h)))   for p in pts_int]

        bm.verts.ensure_lookup_table()
        mat_layer = bm.faces.layers.int.new("material_index")

        # — Cara exterior —
        for i in range(n - 1):
            f = bm.faces.new([
                v_ext_bot[i], v_ext_bot[i+1],
                v_ext_top[i+1], v_ext_top[i],
            ])
            f[mat_layer] = props.mat_wall

        # — Cara interior —
        for i in range(n - 1):
            f = bm.faces.new([
                v_int_bot[i+1], v_int_bot[i],
                v_int_top[i], v_int_top[i+1],
            ])
            f[mat_layer] = props.mat_wall

        # — Tapa superior —
        for i in range(n - 1):
            f = bm.faces.new([
                v_ext_top[i], v_ext_top[i+1],
                v_int_top[i+1], v_int_top[i],
            ])
            f[mat_layer] = props.mat_wall

        # — Tapa inferior —
        for i in range(n - 1):
            f = bm.faces.new([
                v_int_bot[i], v_int_bot[i+1],
                v_ext_bot[i+1], v_ext_bot[i],
            ])
            f[mat_layer] = props.mat_wall

        # — Capiteles —
        bm.faces.new([
            v_ext_bot[0], v_ext_top[0],
            v_int_top[0], v_int_bot[0],
        ])[mat_layer] = props.mat_wall

        last = n - 1
        bm.faces.new([
            v_int_bot[last], v_int_top[last],
            v_ext_top[last], v_ext_bot[last],
        ])[mat_layer] = props.mat_wall

        if props.closed and n > 2:
            bm.faces.new([
                v_ext_bot[last], v_ext_top[last],
                v_int_top[0], v_int_bot[0],
            ])[mat_layer] = props.mat_wall

        # ── Zócalo ───────────────────────────────────────────
        if props.base_enable:
            bw = props.base_width
            bh = props.base_height

            pts_be = self._offset_polyline(baseline,  (half_w + bw) * flip)
            pts_bi = self._offset_polyline(baseline, -(half_w + bw) * flip)

            vb_ext_bot = [bm.verts.new(Vector((p.x, p.y, 0.0))) for p in pts_be]
            vb_ext_top = [bm.verts.new(Vector((p.x, p.y, bh)))  for p in pts_be]
            vb_int_bot = [bm.verts.new(Vector((p.x, p.y, 0.0))) for p in pts_bi]
            vb_int_top = [bm.verts.new(Vector((p.x, p.y, bh)))  for p in pts_bi]

            bm.verts.ensure_lookup_table()

            for i in range(n - 1):
                bm.faces.new([
                    vb_ext_bot[i], vb_ext_bot[i+1],
                    vb_ext_top[i+1], vb_ext_top[i],
                ])[mat_layer] = props.mat_base

                bm.faces.new([
                    vb_int_bot[i+1], vb_int_bot[i],
                    vb_int_top[i], vb_int_top[i+1],
                ])[mat_layer] = props.mat_base

                bm.faces.new([
                    vb_ext_top[i], vb_ext_top[i+1],
                    v_ext_bot[i+1], v_ext_bot[i],
                ])[mat_layer] = props.mat_base

                bm.faces.new([
                    v_int_bot[i], v_int_bot[i+1],
                    vb_int_top[i+1], vb_int_top[i],
                ])[mat_layer] = props.mat_base

        # ── Cornisa ───────────────────────────────────────────
        if props.top_enable:
            tw = props.top_width
            th = props.top_height
            z0 = h - th
            z1 = h

            pts_te = self._offset_polyline(baseline,  (half_w + tw) * flip)
            pts_ti = self._offset_polyline(baseline, -(half_w + tw) * flip)

            vt_ext_bot = [bm.verts.new(Vector((p.x, p.y, z0))) for p in pts_te]
            vt_ext_top = [bm.verts.new(Vector((p.x, p.y, z1))) for p in pts_te]
            vt_int_bot = [bm.verts.new(Vector((p.x, p.y, z0))) for p in pts_ti]
            vt_int_top = [bm.verts.new(Vector((p.x, p.y, z1))) for p in pts_ti]

            bm.verts.ensure_lookup_table()

            for i in range(n - 1):
                bm.faces.new([
                    vt_ext_bot[i], vt_ext_bot[i+1],
                    vt_ext_top[i+1], vt_ext_top[i],
                ])[mat_layer] = props.mat_top

                bm.faces.new([
                    vt_int_bot[i+1], vt_int_bot[i],
                    vt_int_top[i], vt_int_top[i+1],
                ])[mat_layer] = props.mat_top

                bm.faces.new([
                    v_ext_top[i], v_ext_top[i+1],
                    vt_ext_bot[i+1], vt_ext_bot[i],
                ])[mat_layer] = props.mat_top

                bm.faces.new([
                    vt_int_bot[i], vt_int_bot[i+1],
                    v_int_top[i+1], v_int_top[i],
                ])[mat_layer] = props.mat_top

                bm.faces.new([
                    vt_ext_top[i], vt_ext_top[i+1],
                    vt_int_top[i+1], vt_int_top[i],
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