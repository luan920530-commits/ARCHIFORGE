# -*- coding: utf-8 -*-

# ╔══════════════════════════════════════════════════════════╗
# ║         ARCHIFORGE — af_truss.py                        ║
# ║         Cerchas Paramétricas — Blender 3.3 LTS          ║
# ║         GPL v3 — ArchiForge Devs                        ║
# ╚══════════════════════════════════════════════════════════╝

# <pep8 compliant>

import bpy
import bmesh
import math

from mathutils import Vector, Matrix
from bpy.types  import PropertyGroup, Operator, Panel
from bpy.props  import (
    StringProperty, BoolProperty, IntProperty,
    FloatProperty, EnumProperty, PointerProperty,
)

from . import af_material

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


AF_TRUSS_PROP  = "archiforge_truss"
AF_TRUSS_TYPES = [
    ('PRATT',     "Pratt",      "Pratt truss — diagonals in tension",  'MESH_CUBE',  0),
    ('WARREN',    "Warren",     "Warren truss — triangulated",         'MESH_CUBE',  1),
    ('HOWE',      "Howe",       "Howe truss — diagonals in compression",'MESH_CUBE', 2),
    ('VIERENDEEL',"Vierendeel", "Vierendeel frame — no diagonals",    'MESH_CUBE',  3),
    ('ARCH',      "Arch",       "Arch / curved truss",                'MESH_CUBE',  4),
    ('SPACE',     "Space",      "Space frame (3D)",                   'MESH_CUBE',  5),
]

AF_CHORD_PROFILES = [
    ('SQUARE', "Square", "Square hollow section"),
    ('ROUND',  "Round",  "Round hollow section (circular)"),
    ('I_BEAM', "I-Beam", "I-beam / H-beam section"),
    ('FLAT',   "Flat",   "Flat bar"),
]


# ════════════════════════════════════════════════════════════
#  PROPERTYGROUP
# ════════════════════════════════════════════════════════════
class AF_TrussProperties(PropertyGroup):

    is_af_truss : BoolProperty(
        name="Is AF Truss", default=True, options={'HIDDEN'},
    )
    object_name : StringProperty(
        name="Object Name", default="", options={'HIDDEN'},
    )

    truss_type : EnumProperty(
        name    = "Truss Type",
        items   = AF_TRUSS_TYPES,
        default = 'WARREN',
        update  = lambda s, c: af_truss_update(s, c),
    )

    # ── Dimensiones principales ───────────────────────────────
    span : FloatProperty(
        name="Span", description="Total horizontal span",
        default=6.0, min=0.5, max=50.0, unit='LENGTH',
        update=lambda s, c: af_truss_update(s, c),
    )
    depth : FloatProperty(
        name="Depth", description="Truss depth (height)",
        default=0.80, min=0.10, max=5.0, unit='LENGTH',
        update=lambda s, c: af_truss_update(s, c),
    )
    width : FloatProperty(
        name="Width", description="Out-of-plane width",
        default=0.10, min=0.02, max=1.0, unit='LENGTH',
        update=lambda s, c: af_truss_update(s, c),
    )

    # ── Paneles ───────────────────────────────────────────────
    n_panels : IntProperty(
        name="Panels", description="Number of truss panels",
        default=6, min=2, max=32,
        update=lambda s, c: af_truss_update(s, c),
    )

    # ── Perfil de las barras ──────────────────────────────────
    chord_profile : EnumProperty(
        name    = "Chord Profile",
        items   = AF_CHORD_PROFILES,
        default = 'SQUARE',
        update  = lambda s, c: af_truss_update(s, c),
    )
    chord_size : FloatProperty(
        name="Chord Size", description="Cross-section size of chords",
        default=0.06, min=0.01, max=0.30, unit='LENGTH',
        update=lambda s, c: af_truss_update(s, c),
    )
    web_size : FloatProperty(
        name="Web Size", description="Cross-section size of web members",
        default=0.04, min=0.01, max=0.20, unit='LENGTH',
        update=lambda s, c: af_truss_update(s, c),
    )

    # ── Arco (para tipo ARCH) ─────────────────────────────────
    arch_rise : FloatProperty(
        name="Arch Rise", description="Height of arch camber",
        default=1.0, min=0.1, max=10.0, unit='LENGTH',
        update=lambda s, c: af_truss_update(s, c),
    )

    # ── Space Frame ───────────────────────────────────────────
    space_bays : IntProperty(
        name="Bays (Y)", description="Number of bays in Y for space frame",
        default=4, min=1, max=20,
        update=lambda s, c: af_truss_update(s, c),
    )
    space_bay_width : FloatProperty(
        name="Bay Width (Y)", description="Width of each Y bay",
        default=1.5, min=0.1, max=10.0, unit='LENGTH',
        update=lambda s, c: af_truss_update(s, c),
    )

    # ── Duplicar ──────────────────────────────────────────────
    repeat : IntProperty(
        name="Repeat", description="Number of trusses side by side",
        default=1, min=1, max=20,
        update=lambda s, c: af_truss_update(s, c),
    )
    repeat_spacing : FloatProperty(
        name="Repeat Spacing", description="Distance between repeated trusses",
        default=3.0, min=0.1, max=20.0, unit='LENGTH',
        update=lambda s, c: af_truss_update(s, c),
    )

    # ── Materiales ────────────────────────────────────────────
    mat_chord : IntProperty(name="Chord Material", default=0, min=0)
    mat_web   : IntProperty(name="Web Material",   default=1, min=0)


# ════════════════════════════════════════════════════════════
#  GENERADOR
# ════════════════════════════════════════════════════════════
class AF_TrussGenerator:

    def __init__(self, props):
        self.props = props
        self.bm    = bmesh.new()
        self._mat  = self.bm.faces.layers.int.new("material_index")

    # ────────────────────────────────────────────────────────
    #  PRIMITIVAS
    # ────────────────────────────────────────────────────────
    def _bar(self, p0: Vector, p1: Vector, size: float,
             profile: str, mi: int, y_offset: float = 0.0):
        """
        Genera una barra entre p0 y p1 con el perfil dado.
        y_offset desplaza lateralmente (para repeat).
        """
        bm  = self.bm
        mat = self._mat

        if (p1 - p0).length < 1e-5:
            return

        # Desplazar en Y para repeat
        p0 = p0 + Vector((0, y_offset, 0))
        p1 = p1 + Vector((0, y_offset, 0))

        # Eje de la barra
        axis  = (p1 - p0).normalized()
        length = (p1 - p0).length

        # Construir matriz de orientación
        z_world = Vector((0, 0, 1))
        x_axis  = z_world.cross(axis)
        if x_axis.length < 1e-5:
            x_axis = Vector((1, 0, 0))
        x_axis.normalize()
        y_axis = axis.cross(x_axis).normalized()

        rot = Matrix((
            (x_axis.x, y_axis.x, axis.x, p0.x),
            (x_axis.y, y_axis.y, axis.y, p0.y),
            (x_axis.z, y_axis.z, axis.z, p0.z),
            (0, 0, 0, 1),
        )).transposed()

        # — Perfil de sección transversal —
        if profile in ('SQUARE', 'FLAT', 'I_BEAM'):
            s    = size * 0.5
            pts  = [
                Vector((-s, -s, 0)),
                Vector(( s, -s, 0)),
                Vector(( s,  s, 0)),
                Vector((-s,  s, 0)),
                Vector((-s, -s, length)),
                Vector(( s, -s, length)),
                Vector(( s,  s, length)),
                Vector((-s,  s, length)),
            ]
            verts = [bm.verts.new(rot @ p) for p in pts]
            bm.verts.ensure_lookup_table()
            for fi in [
                (0,1,5,4),(2,3,7,6),(0,3,2,1),
                (4,5,6,7),(0,4,7,3),(1,2,6,5),
            ]:
                try:
                    f = bm.faces.new([verts[i] for i in fi])
                    f[mat] = mi
                except Exception:
                    pass

        elif profile == 'ROUND':
            segs  = 6
            r     = size * 0.5
            astep = (2 * math.pi) / segs
            vb, vt = [], []
            for i in range(segs):
                a = i * astep
                vb.append(bm.verts.new(rot @ Vector((
                    r * math.cos(a), r * math.sin(a), 0
                ))))
                vt.append(bm.verts.new(rot @ Vector((
                    r * math.cos(a), r * math.sin(a), length
                ))))
            bm.verts.ensure_lookup_table()
            for i in range(segs):
                ni = (i+1) % segs
                try:
                    f = bm.faces.new([vb[i], vb[ni], vt[ni], vt[i]])
                    f[mat] = mi
                except Exception:
                    pass
            try:
                bm.faces.new(list(reversed(vb)))[mat] = mi
                bm.faces.new(vt)[mat] = mi
            except Exception:
                pass

    # ────────────────────────────────────────────────────────
    #  PATRONES DE CERCHA
    # ────────────────────────────────────────────────────────
    def _top_chord_points(self):
        """Puntos de la cuerda superior (flat o arco)."""
        p   = self.props
        n   = p.n_panels
        pts = []
        for i in range(n + 1):
            x = p.span * i / n
            if p.truss_type == 'ARCH':
                # Parábola
                t  = 2 * i / n - 1
                z  = p.depth + p.arch_rise * (1 - t*t)
            else:
                z = p.depth
            pts.append(Vector((x, 0, z)))
        return pts

    def _bottom_chord_points(self):
        """Puntos de la cuerda inferior (siempre plana)."""
        p   = self.props
        n   = p.n_panels
        return [
            Vector((p.span * i / n, 0, 0))
            for i in range(n + 1)
        ]

    def _build_2d_truss(self, y_offset=0.0):
        """Construye un único plano de cercha 2D."""
        p   = self.props
        top = self._top_chord_points()
        bot = self._bottom_chord_points()
        n   = p.n_panels
        cp  = p.chord_profile
        cs  = p.chord_size
        ws  = p.web_size
        mi_c = p.mat_chord
        mi_w = p.mat_web

        # — Cuerdas —
        for i in range(n):
            self._bar(top[i], top[i+1], cs, cp, mi_c, y_offset)
            self._bar(bot[i], bot[i+1], cs, cp, mi_c, y_offset)

        # — Montantes y diagonales según tipo —
        if p.truss_type == 'PRATT':
            # Montantes verticales, diagonales hacia el centro
            for i in range(n + 1):
                self._bar(bot[i], top[i], ws, 'SQUARE', mi_w, y_offset)
            for i in range(n):
                # Diagonal: desde top → bot del panel siguiente
                if i < n // 2:
                    self._bar(top[i+1], bot[i],   ws, 'SQUARE', mi_w, y_offset)
                else:
                    self._bar(top[i],   bot[i+1], ws, 'SQUARE', mi_w, y_offset)

        elif p.truss_type == 'WARREN':
            # Solo triángulos (sin montantes)
            for i in range(n):
                if i % 2 == 0:
                    self._bar(bot[i], top[i+1], ws, 'SQUARE', mi_w, y_offset)
                else:
                    self._bar(top[i], bot[i+1], ws, 'SQUARE', mi_w, y_offset)

        elif p.truss_type == 'HOWE':
            # Montantes verticales, diagonales hacia afuera
            for i in range(n + 1):
                self._bar(bot[i], top[i], ws, 'SQUARE', mi_w, y_offset)
            for i in range(n):
                if i < n // 2:
                    self._bar(top[i], bot[i+1], ws, 'SQUARE', mi_w, y_offset)
                else:
                    self._bar(top[i+1], bot[i], ws, 'SQUARE', mi_w, y_offset)

        elif p.truss_type == 'VIERENDEEL':
            # Sin diagonales — solo montantes
            for i in range(n + 1):
                self._bar(bot[i], top[i], ws, 'SQUARE', mi_w, y_offset)

        elif p.truss_type == 'ARCH':
            # Warren + arco
            for i in range(n):
                if i % 2 == 0:
                    self._bar(bot[i], top[i+1], ws, 'ROUND', mi_w, y_offset)
                else:
                    self._bar(top[i], bot[i+1], ws, 'ROUND', mi_w, y_offset)

    def _build_space_frame(self):
        """Genera una malla espacial (space frame) 3D."""
        p     = self.props
        n     = p.n_panels
        m     = p.space_bays
        bw    = p.space_bay_width
        cs    = p.chord_size
        ws    = p.web_size
        cp    = p.chord_profile
        mi_c  = p.mat_chord
        mi_w  = p.mat_web
        depth = p.depth

        step_x = p.span / n

        # Grid superior e inferior
        top_pts = {}
        bot_pts = {}
        for ix in range(n + 1):
            for iy in range(m + 1):
                x = ix * step_x
                y = iy * bw
                top_pts[(ix, iy)] = Vector((x, y, depth))
                bot_pts[(ix, iy)] = Vector((x + step_x*0.5, y + bw*0.5, 0))

        # — Cuerdas superiores —
        for ix in range(n):
            for iy in range(m + 1):
                self._bar(
                    top_pts[(ix, iy)], top_pts[(ix+1, iy)],
                    cs, cp, mi_c
                )
        for ix in range(n + 1):
            for iy in range(m):
                self._bar(
                    top_pts[(ix, iy)], top_pts[(ix, iy+1)],
                    cs, cp, mi_c
                )

        # — Barras de celosía (top → bot) —
        for ix in range(n):
            for iy in range(m):
                bp = bot_pts[(ix, iy)]
                for corner in [
                    top_pts[(ix,   iy  )],
                    top_pts[(ix+1, iy  )],
                    top_pts[(ix,   iy+1)],
                    top_pts[(ix+1, iy+1)],
                ]:
                    self._bar(bp, corner, ws, 'ROUND', mi_w)

    # ────────────────────────────────────────────────────────
    #  GENERATE
    # ────────────────────────────────────────────────────────
    def generate(self):
        p = self.props

        if p.truss_type == 'SPACE':
            self._build_space_frame()
        else:
            # Cercha 2D repetida
            for r in range(p.repeat):
                y_off = r * p.repeat_spacing
                self._build_2d_truss(y_offset=y_off)

        try:
            bmesh.ops.recalc_face_normals(
                bm=self.bm, faces=self.bm.faces
            )
        except Exception:
            pass

        return self.bm


# ════════════════════════════════════════════════════════════
#  UPDATE / REBUILD
# ════════════════════════════════════════════════════════════
def _find_truss_object(props):
    name = props.object_name
    if name and name in bpy.data.objects:
        return bpy.data.objects[name]
    for obj in bpy.data.objects:
        if (obj.type == 'MESH'
                and hasattr(obj, AF_TRUSS_PROP)
                and getattr(obj, AF_TRUSS_PROP) is props):
            return obj
    return None


def af_truss_update(self, context):
    obj = _find_truss_object(self)
    if obj is None:
        obj = context.active_object
    if obj is None or obj.type != 'MESH':
        return
    props = getattr(obj, AF_TRUSS_PROP, None)
    if props is None or not props.is_af_truss:
        return
    _rebuild_truss_mesh(obj, props)


def _rebuild_truss_mesh(obj, props):
    gen = AF_TrussGenerator(props)
    bm  = gen.generate()
    if bm is None:
        return
    me = obj.data
    bm.to_mesh(me)
    bm.free()
    me.update()

    for poly in me.polygons:
        poly.use_smooth = True

    if "material_index" in me.polygon_layers_int:
        layer = me.polygon_layers_int["material_index"]
        for poly in me.polygons:
            poly.material_index = layer.data[poly.index].value


def _setup_truss_materials(obj):
    mat_names = [
        "AF.Truss.Steel",     # 0 chord
        "AF.Truss.Steel",     # 1 web
    ]
    af_material.ensure_af_materials_for_object(obj, mat_names)


def _create_truss_object(context, name="AF_Truss"):
    me  = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, me)
    context.collection.objects.link(obj)
    context.view_layer.objects.active = obj
    obj.select_set(True)

    props             = obj.archiforge_truss
    props.is_af_truss = True
    props.object_name = obj.name
    _setup_truss_materials(obj)
    return obj, props


# ════════════════════════════════════════════════════════════
#  OPERADORES
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_OT_truss(Operator):
    bl_idname      = "archiforge.truss"
    bl_label       = "Add AF Truss"
    bl_description = "Add a parametric ArchiForge truss"
    bl_options     = {'REGISTER', 'UNDO'}

    truss_type : EnumProperty(
        name="Type", items=AF_TRUSS_TYPES, default='WARREN',
    )
    span : FloatProperty(
        name="Span", default=6.0, min=0.5, unit='LENGTH',
    )
    depth : FloatProperty(
        name="Depth", default=0.80, min=0.10, unit='LENGTH',
    )
    n_panels : IntProperty(
        name="Panels", default=6, min=2, max=32,
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        col = layout.column(align=True)
        col.label(text="New Truss", **_icon("truss", 'MESH_CUBE'))
        col.prop(self, "truss_type")
        col.separator()
        col.prop(self, "span")
        col.prop(self, "depth")
        col.prop(self, "n_panels")

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        obj, props = _create_truss_object(context, "AF_Truss")
        props.truss_type = self.truss_type
        props.span       = self.span
        props.depth      = self.depth
        props.n_panels   = self.n_panels
        _rebuild_truss_mesh(obj, props)
        self.report({'INFO'}, _tr("Truss created: {}").format(obj.name))
        return {'FINISHED'}


class ARCHIFORGE_OT_truss_update(Operator):
    bl_idname  = "archiforge.truss_update"
    bl_label   = "Update Truss"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj is not None and obj.type == 'MESH'
            and hasattr(obj, AF_TRUSS_PROP)
            and obj.archiforge_truss.is_af_truss
        )

    def execute(self, context):
        obj = context.active_object
        _rebuild_truss_mesh(obj, obj.archiforge_truss)
        self.report({'INFO'}, _tr("Truss updated"))
        return {'FINISHED'}


# ════════════════════════════════════════════════════════════
#  PANEL
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_PT_truss(Panel):
    bl_label       = "Truss Properties"
    bl_idname      = "ARCHIFORGE_PT_truss"
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
            and hasattr(obj, AF_TRUSS_PROP)
            and obj.archiforge_truss.is_af_truss
        )

    def draw_header(self, context):
        self.layout.label(text="", **_icon("truss", 'MESH_CUBE'))

    def draw(self, context):
        props  = context.active_object.archiforge_truss
        layout = self.layout
        layout.use_property_split   = True
        layout.use_property_decorate = False

        # ── Tipo ─────────────────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Type", icon='MODIFIER')
        col.prop(props, "truss_type", text="")

        # ── Geometría ─────────────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Geometry", icon='ARROW_LEFTRIGHT')
        col.prop(props, "span")
        col.prop(props, "depth")
        col.prop(props, "width")
        col.prop(props, "n_panels")

        # ── Arch ─────────────────────────────────────────────
        if props.truss_type == 'ARCH':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Arch", icon='MOD_CURVE')
            col.prop(props, "arch_rise")

        # ── Space Frame ───────────────────────────────────────
        if props.truss_type == 'SPACE':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Space Frame", icon='MESH_GRID')
            col.prop(props, "space_bays")
            col.prop(props, "space_bay_width")

        # ── Secciones ─────────────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Sections", icon='MESH_CUBE')
        col.prop(props, "chord_profile")
        col.prop(props, "chord_size")
        col.prop(props, "web_size")

        # ── Repeat ────────────────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Array", icon='MOD_ARRAY')
        col.prop(props, "repeat")
        if props.repeat > 1:
            col.prop(props, "repeat_spacing")

        # ── Materiales ────────────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Materials", icon='MATERIAL')
        col.prop(props, "mat_chord", text="Chord")
        col.prop(props, "mat_web",   text="Web")

        # ── Acciones ──────────────────────────────────────────
        layout.separator()
        layout.operator(
            "archiforge.truss_update",
            text="Force Update",
            icon='FILE_REFRESH',
        )


# ════════════════════════════════════════════════════════════
#  REGISTRO
# ════════════════════════════════════════════════════════════
classes = [
    AF_TrussProperties,
    ARCHIFORGE_OT_truss,
    ARCHIFORGE_OT_truss_update,
    ARCHIFORGE_PT_truss,
]


def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except Exception as e:
            print(f"[ArchiForge] ⚠️  af_truss '{cls.__name__}': {e}")

    bpy.types.Object.archiforge_truss = PointerProperty(
        type        = AF_TrussProperties,
        name        = "ArchiForge Truss",
        description = "ArchiForge parametric truss properties",
    )
    print("[ArchiForge] ✅ af_truss — registered")


def unregister():
    if hasattr(bpy.types.Object, "archiforge_truss"):
        del bpy.types.Object.archiforge_truss

    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"[ArchiForge] ⚠️  af_truss '{cls.__name__}': {e}")

    print("[ArchiForge] 🔴 af_truss — unregistered")