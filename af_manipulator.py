# -*- coding: utf-8 -*-

# ╔══════════════════════════════════════════════════════════╗
# ║         ARCHIFORGE — af_manipulator.py                  ║
# ║         Gizmos / Manipuladores — Blender 3.3 LTS        ║
# ║         GPL v3 — ArchiForge Devs                        ║
# ╚══════════════════════════════════════════════════════════╝

# <pep8 compliant>

# ════════════════════════════════════════════════════════════
#  ¿QUÉ HACE ESTE MÓDULO?
#
#  Sistema de manipuladores on-screen para objetos AF:
#  - Handles de arrastre para width/height/depth
#  - Etiquetas de dimensión en viewport
#  - Compatible con Blender 3.3 (sin bgl deprecated)
#  - Usa gpu + blf para dibujo 2D
#  - Callbacks de modal para interactividad
# ════════════════════════════════════════════════════════════

import bpy
import math
import blf
import gpu

from gpu_extras.batch  import batch_for_shader
from mathutils         import Vector, Matrix
from bpy.types         import (
    PropertyGroup, Operator, Panel, GizmoGroup, Gizmo
)
from bpy.props         import (
    BoolProperty, FloatProperty,
    StringProperty, PointerProperty,
    EnumProperty,
)

try:
    from .af_i18n import tr_report as _tr
except ImportError:  # pragma: no cover - fuera del paquete
    def _tr(text):
        return text

# Importar snap para integración
try:
    from . import af_snap
    HAS_SNAP = True
except ImportError:
    HAS_SNAP = False


# ════════════════════════════════════════════════════════════
#  CONSTANTES DE ESTILO
# ════════════════════════════════════════════════════════════
AF_HANDLE_SIZE    = 0.08    # metros — tamaño base del handle
AF_LABEL_OFFSET   = 0.15   # metros — offset del label respecto al handle
AF_DIM_COLOR      = (0.9, 0.9, 0.2, 0.9)   # amarillo
AF_HANDLE_COLOR   = (1.0, 1.0, 1.0, 0.85)  # blanco
AF_HANDLE_HOVER   = (1.0, 0.8, 0.0, 1.0)   # naranja
AF_HANDLE_ACTIVE  = (1.0, 0.2, 0.2, 1.0)   # rojo
AF_LINE_COLOR     = (0.4, 0.8, 1.0, 0.6)   # azul claro


# ════════════════════════════════════════════════════════════
#  PROPERTYGROUP — configuración de manipuladores
# ════════════════════════════════════════════════════════════
class AF_ManipulatorSettings(PropertyGroup):

    show_manipulators : BoolProperty(
        name        = "Mostrar Manipuladores",
        description = "Mostrar handles interactivos de ArchiForge en el viewport",
        default     = True,
    )
    show_dimensions : BoolProperty(
        name        = "Mostrar Dimensiones",
        description = "Mostrar etiquetas de dimensión en objetos AF",
        default     = True,
    )
    handle_size : FloatProperty(
        name        = "Tamaño del Handle",
        description = "Tamaño de los handles interactivos",
        default     = AF_HANDLE_SIZE,
        min         = 0.01,
        max         = 0.50,
        unit        = 'LENGTH',
    )
    font_size : bpy.props.IntProperty(
        name        = "Tamaño de Fuente",
        description = "Tamaño de fuente para las etiquetas de dimensión",
        default     = 12,
        min         = 8,
        max         = 32,
    )
    label_color : bpy.props.FloatVectorProperty(
        name    = "Color de Etiqueta",
        subtype = 'COLOR_GAMMA',
        default = (1.0, 1.0, 0.2, 1.0),
        size=4, min=0, max=1,
    )
    handle_color_normal : bpy.props.FloatVectorProperty(
        name    = "Handle Normal",
        subtype = 'COLOR_GAMMA',
        default = (1.0, 1.0, 1.0, 0.85),
        size=4, min=0, max=1,
    )


# ════════════════════════════════════════════════════════════
#  UTILIDADES DE DIBUJO
# ════════════════════════════════════════════════════════════
def _world_to_screen(context, world_co: Vector):
    """
    Convierte coordenadas 3D world a coordenadas 2D de pantalla.
    Retorna (x, y) en píxeles o None si está fuera del frustum.
    """
    from bpy_extras.view3d_utils import location_3d_to_region_2d
    region = context.region
    rv3d   = context.region_data
    if region is None or rv3d is None:
        return None
    return location_3d_to_region_2d(region, rv3d, world_co)


def _draw_line_2d(p1, p2, color):
    """Dibuja una línea 2D en el viewport (coordenadas de pantalla)."""
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    batch  = batch_for_shader(
        shader, 'LINES',
        {"pos": [p1, p2]}
    )
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)


def _draw_quad_2d(cx, cy, size, color):
    """Dibuja un cuadrado 2D centrado en (cx, cy)."""
    s = size * 0.5
    verts = [
        (cx - s, cy - s),
        (cx + s, cy - s),
        (cx + s, cy + s),
        (cx - s, cy + s),
    ]
    indices = [(0, 1, 2), (0, 2, 3)]
    shader  = gpu.shader.from_builtin('UNIFORM_COLOR')
    batch   = batch_for_shader(
        shader, 'TRIS',
        {"pos": verts},
        indices=indices,
    )
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)


def _draw_label(context, world_co: Vector, text: str,
                font_size: int, color):
    """
    Dibuja un texto en coordenadas 3D world.
    Usa blf (compatible con Blender 3.3, sin bgl).
    """
    screen = _world_to_screen(context, world_co)
    if screen is None:
        return
    x, y = int(screen.x), int(screen.y)

    font_id = 0
    blf.enable(font_id, blf.SHADOW)
    blf.shadow(font_id, 3, 0.0, 0.0, 0.0, 0.8)
    blf.shadow_offset(font_id, 1, -1)
    blf.color(font_id, *color)
    blf.size(font_id, font_size)
    blf.position(font_id, x + 4, y + 4, 0)
    blf.draw(font_id, text)
    blf.disable(font_id, blf.SHADOW)


# ════════════════════════════════════════════════════════════
#  GIZMO — Handle genérico
# ════════════════════════════════════════════════════════════
class AF_ArrowGizmo(Gizmo):
    """
    Handle de flecha para manipular una sola propiedad float
    (width, height, depth…).
    """
    bl_idname = "VIEW3D_GT_af_arrow"
    bl_target_properties = (
        {"id": "offset", "type": 'FLOAT', "array_length": 1},
    )

    __slots__ = (
        "prop_name",
        "prop_min",
        "prop_max",
        "axis",
        "_init_value",
    )

    def setup(self):
        self.prop_name  = ""
        self.prop_min   = 0.0
        self.prop_max   = 100.0
        self.axis       = 'X'
        self._init_value = 0.0

    def draw(self, context):
        # Dibujo normal — sin select_id (Blender usa el default interno)
        self.draw_preset_arrow(self.matrix_world)

    def draw_select(self, context, select_id):
        # Pasada de selección — aquí SÍ se pasa el select_id entero
        self.draw_preset_arrow(self.matrix_world, select_id=select_id)

    def invoke(self, context, event):
        self._init_value = self.target_get_value("offset")
        return {'RUNNING_MODAL'}

    def modal(self, context, event, tweak):
        delta = event.mouse_x - event.mouse_prev_x
        if 'PRECISE' in tweak:
            delta *= 0.01
        else:
            delta *= 0.05

        val = self._init_value + delta * 0.01

        # Aplicar snap si está disponible
        if HAS_SNAP:
            snap = af_snap.get_snap_settings(context)
            if snap and snap.enabled and snap.grid_snap:
                val = af_snap.snap_to_grid(val, snap.grid_size)

        val = max(self.prop_min, min(self.prop_max, val))
        self.target_set_value("offset", val)
        return {'RUNNING_MODAL'}

    def exit(self, context, cancel):
        if cancel:
            self.target_set_value("offset", self._init_value)


# ════════════════════════════════════════════════════════════
#  GIZMO GROUP — Wall
# ════════════════════════════════════════════════════════════
class AF_WallGizmoGroup(GizmoGroup):
    bl_label      = "AF Wall Manipulators"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options    = {'3D', 'PERSISTENT'}
    bl_idname     = "VIEW3D_GGT_af_wall"

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            return False
        if not hasattr(obj, "archiforge_wall"):
            return False
        props = obj.archiforge_wall
        if not getattr(props, "is_af_wall", False):
            return False
        manip = getattr(context.scene, "af_manipulator", None)
        return manip is None or manip.show_manipulators

    def setup(self, context):
        obj   = context.active_object
        props = obj.archiforge_wall

        # ── Gizmo de Width (eje X) ────────────────────────────
        gz_w = self.gizmos.new(AF_ArrowGizmo.bl_idname)
        gz_w.prop_name  = "width"
        gz_w.prop_min   = 0.10
        gz_w.prop_max   = 100.0
        gz_w.color      = AF_HANDLE_COLOR[:3]
        gz_w.alpha      = AF_HANDLE_COLOR[3]
        gz_w.color_highlight = AF_HANDLE_HOVER[:3]
        gz_w.scale_basis = 0.1
        self.gz_width    = gz_w

        # ── Gizmo de Height (eje Z) ───────────────────────────
        gz_h = self.gizmos.new(AF_ArrowGizmo.bl_idname)
        gz_h.prop_name  = "height"
        gz_h.prop_min   = 0.10
        gz_h.prop_max   = 20.0
        gz_h.color      = (0.2, 1.0, 0.2)
        gz_h.alpha      = 0.85
        gz_h.color_highlight = (0.5, 1.0, 0.5)
        gz_h.scale_basis = 0.1
        self.gz_height   = gz_h

    def refresh(self, context):
        obj   = context.active_object
        if obj is None or not hasattr(obj, "archiforge_wall"):
            return
        props = obj.archiforge_wall
        mw    = obj.matrix_world

        # — Posición del handle de Width —
        w_pos = mw @ Vector((
            getattr(props, "width", 1.0), 0.0, 0.5
        ))
        self.gz_width.matrix_basis = Matrix.Translation(w_pos)
        self.gz_width.target_set_prop(
            "offset", props, "width"
        )

        # — Posición del handle de Height —
        h_pos = mw @ Vector((
            getattr(props, "width", 1.0) * 0.5,
            0.0,
            getattr(props, "height", 2.8)
        ))
        self.gz_height.matrix_basis = Matrix.Translation(h_pos)
        self.gz_height.target_set_prop(
            "offset", props, "height"
        )


# ════════════════════════════════════════════════════════════
#  DRAW HANDLER — Etiquetas de dimensión en viewport
# ════════════════════════════════════════════════════════════
_draw_handle = None


def _draw_dimensions_callback():
    """
    Callback de dibujo POST_PIXEL para etiquetas de dimensión.
    Compatible con Blender 3.3 (gpu + blf, sin bgl).
    """
    context = bpy.context
    if context.area is None or context.area.type != 'VIEW_3D':
        return

    manip = getattr(context.scene, "af_manipulator", None)
    if manip is None:
        return
    if not manip.show_manipulators or not manip.show_dimensions:
        return

    obj = context.active_object
    if obj is None or obj.type != 'MESH':
        return

    # ── Detectar tipo AF y obtener dimensiones ────────────────
    dim_info = _get_dimensions_for_object(obj)
    if dim_info is None:
        return

    mw       = obj.matrix_world
    fs       = manip.font_size
    lc       = manip.label_color

    # ── Dibujar cada etiqueta ─────────────────────────────────
    for label, world_point in dim_info:
        _draw_label(context, world_point, label, fs, lc)


def _get_dimensions_for_object(obj):
    """
    Retorna lista de (label_str, world_Vector) para las
    dimensiones del objeto AF activo.
    """
    result = []

    # — Wall —
    if hasattr(obj, "archiforge_wall"):
        props = obj.archiforge_wall
        if getattr(props, "is_af_wall", False):
            w = getattr(props, "width",     1.0)
            h = getattr(props, "height",    2.8)
            t = getattr(props, "thickness", 0.2)
            mw = obj.matrix_world
            result.append((
                f"W: {w:.2f}m",
                mw @ Vector((w * 0.5, 0.0, h + 0.1))
            ))
            result.append((
                f"H: {h:.2f}m",
                mw @ Vector((w + 0.1, 0.0, h * 0.5))
            ))
            result.append((
                f"T: {t:.2f}m",
                mw @ Vector((0.0, t * 0.5, h + 0.15))
            ))
            return result

    # — Floor —
    if hasattr(obj, "archiforge_floor"):
        props = obj.archiforge_floor
        if getattr(props, "is_af_floor", False):
            w = getattr(props, "width", 4.0)
            d = getattr(props, "depth", 3.0)
            mw = obj.matrix_world
            result.append((
                f"W: {w:.2f}m",
                mw @ Vector((w * 0.5, -0.15, 0.0))
            ))
            result.append((
                f"D: {d:.2f}m",
                mw @ Vector((-0.15, d * 0.5, 0.0))
            ))
            return result

    # — Fence —
    if hasattr(obj, "archiforge_fence"):
        props = obj.archiforge_fence
        if getattr(props, "is_af_fence", False):
            h = getattr(props, "height", 1.2)
            mw = obj.matrix_world
            # Usar el largo del primer segmento
            total_len = 0.0
            for seg in props.parts:
                if seg.enabled:
                    total_len += seg.length
            result.append((
                f"L: {total_len:.2f}m",
                mw @ Vector((total_len * 0.5, 0.0, h + 0.1))
            ))
            result.append((
                f"H: {h:.2f}m",
                mw @ Vector((total_len + 0.1, 0.0, h * 0.5))
            ))
            return result

    # — Genérico: bounding box —
    bb  = obj.bound_box
    xs  = [v[0] for v in bb]
    ys  = [v[1] for v in bb]
    zs  = [v[2] for v in bb]
    dim = (max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs))
    mw  = obj.matrix_world
    result.append((
        f"{dim[0]:.2f} × {dim[1]:.2f} × {dim[2]:.2f}m",
        mw @ Vector((dim[0]*0.5, dim[1]*0.5, dim[2]+0.1))
    ))
    return result if result else None


# ════════════════════════════════════════════════════════════
#  OPERADORES
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_OT_manipulator_toggle(Operator):
    """Activa/desactiva los manipuladores AF."""
    bl_idname      = "archiforge.manipulator_toggle"
    bl_label       = "Alternar Manipuladores AF"
    bl_description = "Alternar los manipuladores on-screen de ArchiForge"
    bl_options     = {'REGISTER'}

    def execute(self, context):
        manip = getattr(context.scene, "af_manipulator", None)
        if manip:
            manip.show_manipulators = not manip.show_manipulators
            state = "ON" if manip.show_manipulators else "OFF"
            self.report({'INFO'}, _tr("Manipuladores AF: {}").format(state))
        return {'FINISHED'}


class ARCHIFORGE_OT_dimensions_toggle(Operator):
    """Activa/desactiva las etiquetas de dimensión."""
    bl_idname      = "archiforge.dimensions_toggle"
    bl_label       = "Alternar Etiquetas de Dimensión"
    bl_description = "Alternar etiquetas de dimensión en el viewport"
    bl_options     = {'REGISTER'}

    def execute(self, context):
        manip = getattr(context.scene, "af_manipulator", None)
        if manip:
            manip.show_dimensions = not manip.show_dimensions
            state = "ON" if manip.show_dimensions else "OFF"
            self.report({'INFO'}, _tr("Etiquetas de Dimensión: {}").format(state))
        return {'FINISHED'}


# ════════════════════════════════════════════════════════════
#  PANEL — sub-panel de Tools
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_PT_manipulator(Panel):
    bl_label       = "Manipuladores"
    bl_idname      = "ARCHIFORGE_PT_manipulator"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "ArchiForge"
    bl_parent_id   = "ARCHIFORGE_PT_tools"
    bl_options     = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def draw(self, context):
        manip  = getattr(context.scene, "af_manipulator", None)
        layout = self.layout
        layout.use_property_split   = True
        layout.use_property_decorate = False

        if manip is None:
            layout.label(text="No disponible", icon='ERROR')
            return

        # ── Toggle rápido ─────────────────────────────────────
        row = layout.row(align=True)
        row.prop(
            manip, "show_manipulators",
            text="Handles", toggle=True, icon='PIVOT_CURSOR'
        )
        row.prop(
            manip, "show_dimensions",
            text="Etiquetas",  toggle=True, icon='FONT_DATA'
        )

        layout.separator(factor=0.3)

        # ── Opciones ──────────────────────────────────────────
        col = layout.column(align=True)
        col.active = manip.show_manipulators or manip.show_dimensions
        col.prop(manip, "handle_size")
        col.prop(manip, "font_size")
        col.prop(manip, "label_color")
        col.prop(manip, "handle_color_normal")


# ════════════════════════════════════════════════════════════
#  REGISTRO
# ════════════════════════════════════════════════════════════
classes = [
    AF_ManipulatorSettings,
    AF_ArrowGizmo,
    AF_WallGizmoGroup,
    ARCHIFORGE_OT_manipulator_toggle,
    ARCHIFORGE_OT_dimensions_toggle,
    ARCHIFORGE_PT_manipulator,
]


def register():
    global _draw_handle

    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except Exception as e:
            print(f"[ArchiForge] ⚠️  af_manipulator '{cls.__name__}': {e}")

    bpy.types.Scene.af_manipulator = PointerProperty(
        type        = AF_ManipulatorSettings,
        name        = "AF Manipulator",
        description = "Configuración de manipuladores de ArchiForge",
    )

    # Registrar el draw callback
    try:
        _draw_handle = bpy.types.SpaceView3D.draw_handler_add(
            _draw_dimensions_callback,
            (), 'WINDOW', 'POST_PIXEL'
        )
    except Exception as e:
        print(f"[ArchiForge] ⚠️  No se pudo añadir el draw handler: {e}")

    print("[ArchiForge] ✅ af_manipulator — registrado")


def unregister():
    global _draw_handle

    # Remover el draw callback
    if _draw_handle is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(
                _draw_handle, 'WINDOW'
            )
        except Exception as e:
            print(f"[ArchiForge] ⚠️  No se pudo remover el draw handler: {e}")
        _draw_handle = None

    if hasattr(bpy.types.Scene, "af_manipulator"):
        del bpy.types.Scene.af_manipulator

    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"[ArchiForge] ⚠️  af_manipulator '{cls.__name__}': {e}")

    print("[ArchiForge] 🔴 af_manipulator — desregistrado")