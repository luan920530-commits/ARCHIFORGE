# -*- coding: utf-8 -*-

# ╔══════════════════════════════════════════════════════════╗
# ║         ARCHIFORGE — af_snap.py                         ║
# ║         Sistema de Snap Arquitectónico — Blender 3.3    ║
# ║         GPL v3 — ArchiForge Devs                        ║
# ╚══════════════════════════════════════════════════════════╝

# <pep8 compliant>

# ════════════════════════════════════════════════════════════
#  ¿QUÉ HACE ESTE MÓDULO?
#
#  Sistema de snap especializado para arquitectura:
#  - Snap a grilla métrica configurable
#  - Snap a vértices/aristas de objetos AF
#  - Snap a ángulos de 0°/45°/90°
#  - Snap a dimensiones estándar (modular)
#  - Configuración por contexto (modo muro, modo piso…)
# ════════════════════════════════════════════════════════════

import bpy
import math

from bpy.types  import PropertyGroup, Operator, AddonPreferences
from bpy.props  import (
    BoolProperty,
    FloatProperty,
    EnumProperty,
    IntProperty,
    PointerProperty,
)

try:
    from .af_i18n import tr_report as _tr
except ImportError:  # pragma: no cover - fuera del paquete
    def _tr(text):
        return text


# ════════════════════════════════════════════════════════════
#  CONSTANTES
# ════════════════════════════════════════════════════════════
AF_SNAP_GRIDS = [
    (0.010, "1 cm"),
    (0.025, "2.5 cm"),
    (0.050, "5 cm"),
    (0.100, "10 cm"),
    (0.125, "12.5 cm"),
    (0.200, "20 cm"),
    (0.250, "25 cm"),
    (0.300, "30 cm"),
    (0.500, "50 cm"),
    (1.000, "1 m"),
]

AF_SNAP_ANGLES = [0, 15, 30, 45, 60, 90, 180]


# ════════════════════════════════════════════════════════════
#  PROPERTYGROUP — configuración de snap por escena
# ════════════════════════════════════════════════════════════
class AF_SnapSettings(PropertyGroup):

    # ── Activación ───────────────────────────────────────────
    enabled : BoolProperty(
        name        = "AF Snap",
        description = "Enable ArchiForge smart snap system",
        default     = True,
    )

    # ── Grilla métrica ───────────────────────────────────────
    grid_snap : BoolProperty(
        name        = "Grid Snap",
        description = "Snap to metric grid",
        default     = True,
    )
    grid_size : FloatProperty(
        name        = "Grid Size",
        description = "Snap grid size in meters",
        default     = 0.05,
        min         = 0.001,
        max         = 10.0,
        step        = 1,
        precision   = 3,
        unit        = 'LENGTH',
    )

    # ── Snap angular ─────────────────────────────────────────
    angle_snap : BoolProperty(
        name        = "Angle Snap",
        description = "Snap rotation to architectural angles",
        default     = True,
    )
    angle_step : EnumProperty(
        name  = "Angle Step",
        items = [
            ('15',  "15°",  "Snap every 15 degrees"),
            ('30',  "30°",  "Snap every 30 degrees"),
            ('45',  "45°",  "Snap every 45 degrees"),
            ('90',  "90°",  "Snap every 90 degrees"),
        ],
        default = '45',
    )

    # ── Snap a objetos AF ─────────────────────────────────────
    af_object_snap : BoolProperty(
        name        = "Snap to AF Objects",
        description = "Snap to vertices and edges of other AF objects",
        default     = True,
    )

    # ── Snap modular ─────────────────────────────────────────
    modular_snap : BoolProperty(
        name        = "Modular Snap",
        description = "Snap to standard architectural dimensions (60, 90, 120...)",
        default     = False,
    )
    module_size : FloatProperty(
        name        = "Module",
        description = "Modular coordination unit",
        default     = 0.30,
        min         = 0.05,
        max         = 2.0,
        unit        = 'LENGTH',
    )

    # ── Display ───────────────────────────────────────────────
    show_snap_cursor : BoolProperty(
        name        = "Show Snap Cursor",
        description = "Show snap cursor indicator in viewport",
        default     = True,
    )


# ════════════════════════════════════════════════════════════
#  UTILIDADES DE SNAP
# ════════════════════════════════════════════════════════════
def snap_to_grid(value: float, grid: float) -> float:
    """Redondea value al múltiplo más cercano de grid."""
    if grid < 0.0001:
        return value
    return round(value / grid) * grid


def snap_to_angle(angle_rad: float, step_deg: int) -> float:
    """Redondea angle_rad al ángulo más cercano según step_deg."""
    step_rad = math.radians(step_deg)
    if step_rad < 0.0001:
        return angle_rad
    return round(angle_rad / step_rad) * step_rad


def snap_vector_to_grid(v, grid: float):
    """Aplica grid snap a un Vector mathutils."""
    from mathutils import Vector
    return Vector((
        snap_to_grid(v.x, grid),
        snap_to_grid(v.y, grid),
        snap_to_grid(v.z, grid),
    ))


def get_snap_settings(context):
    """Acceso seguro a AF_SnapSettings de la escena."""
    return getattr(context.scene, "af_snap", None)


def apply_grid_snap(context, location):
    """
    Aplica snap de grilla si está activado.
    Retorna el location modificado.
    """
    snap = get_snap_settings(context)
    if snap and snap.enabled and snap.grid_snap:
        return snap_vector_to_grid(location, snap.grid_size)
    return location


def apply_angle_snap(context, angle_rad: float) -> float:
    """
    Aplica snap de ángulo si está activado.
    Retorna el ángulo modificado.
    """
    snap = get_snap_settings(context)
    if snap and snap.enabled and snap.angle_snap:
        step = int(snap.angle_step)
        return snap_to_angle(angle_rad, step)
    return angle_rad


# ════════════════════════════════════════════════════════════
#  OPERADORES
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_OT_snap_toggle(Operator):
    """Activa/desactiva el snap de ArchiForge."""
    bl_idname      = "archiforge.snap_toggle"
    bl_label       = "Toggle AF Snap"
    bl_description = "Toggle ArchiForge snap system on/off"
    bl_options     = {'REGISTER'}

    def execute(self, context):
        snap = get_snap_settings(context)
        if snap:
            snap.enabled = not snap.enabled
            state = "ON" if snap.enabled else "OFF"
            self.report({'INFO'}, _tr("AF Snap: {}").format(state))
        return {'FINISHED'}


class ARCHIFORGE_OT_snap_set_grid(Operator):
    """Establece el tamaño de grilla desde un preset."""
    bl_idname      = "archiforge.snap_set_grid"
    bl_label       = "Set Snap Grid"
    bl_description = "Set AF snap grid to a preset size"
    bl_options     = {'REGISTER'}

    grid_size : FloatProperty(
        name="Grid Size", default=0.05, min=0.001,
    )

    def execute(self, context):
        snap = get_snap_settings(context)
        if snap:
            snap.grid_size = self.grid_size
            self.report(
                {'INFO'},
                _tr("AF Snap grid: {:.1f} cm").format(self.grid_size * 100)
            )
        return {'FINISHED'}


class ARCHIFORGE_OT_snap_sync_blender(Operator):
    """
    Sincroniza la configuración de snap de AF
    con el snap nativo de Blender.
    """
    bl_idname      = "archiforge.snap_sync"
    bl_label       = "Sync with Blender Snap"
    bl_description = "Sync AF snap grid with Blender native snap"
    bl_options     = {'REGISTER'}

    def execute(self, context):
        snap = get_snap_settings(context)
        if snap is None:
            return {'CANCELLED'}
        ts = context.scene.tool_settings

        # Activar snap nativo con vértices + grilla
        ts.use_snap         = snap.enabled
        ts.snap_elements    = {'VERTEX', 'EDGE', 'FACE'}
        ts.snap_target      = 'CLOSEST'

        # Sincronizar escala de grilla en el viewport
        grid = snap.grid_size
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.overlay.grid_scale = grid

        self.report({'INFO'}, _tr("Snap synchronized with Blender"))
        return {'FINISHED'}


# ════════════════════════════════════════════════════════════
#  PANEL — sub-panel dentro de ARCHIFORGE_PT_snap_tools
#  (si af_panel.py ya existe, este es un sub-panel)
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_PT_snap(bpy.types.Panel):
    bl_label       = "AF Snap Settings"
    bl_idname      = "ARCHIFORGE_PT_snap"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "ArchiForge"
    bl_parent_id   = "ARCHIFORGE_PT_snap_tools"
    bl_options     = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def draw_header(self, context):
        snap = get_snap_settings(context)
        icon = 'SNAP_ON' if (snap and snap.enabled) else 'SNAP_OFF'
        self.layout.label(text="", icon=icon)

    def draw(self, context):
        snap   = get_snap_settings(context)
        layout = self.layout
        layout.use_property_split   = True
        layout.use_property_decorate = False

        if snap is None:
            layout.label(text="Snap not available", icon='ERROR')
            return

        # ── Toggle master ─────────────────────────────────────
        row = layout.row(align=True)
        row.prop(snap, "enabled",   text="Enable AF Snap", toggle=True)
        row.operator(
            "archiforge.snap_sync",
            text="", icon='LINKED'
        )

        layout.separator(factor=0.3)

        # ── Grid ─────────────────────────────────────────────
        box = layout.box()
        box.active = snap.enabled
        col = box.column(align=True)
        col.prop(snap, "grid_snap")
        if snap.grid_snap:
            col.prop(snap, "grid_size")
            col.separator(factor=0.3)
            col.label(text="Presets:", icon='GRID')
            row = col.row(align=True)
            for size, label in AF_SNAP_GRIDS[:6]:
                op = row.operator(
                    "archiforge.snap_set_grid",
                    text=label.replace(" ", ""),
                )
                op.grid_size = size

        # ── Angle ─────────────────────────────────────────────
        box = layout.box()
        box.active = snap.enabled
        col = box.column(align=True)
        col.prop(snap, "angle_snap")
        if snap.angle_snap:
            col.prop(snap, "angle_step")

        # ── Modular ───────────────────────────────────────────
        box = layout.box()
        box.active = snap.enabled
        col = box.column(align=True)
        col.prop(snap, "modular_snap")
        if snap.modular_snap:
            col.prop(snap, "module_size")

        # ── AF Objects ────────────────────────────────────────
        box = layout.box()
        box.active = snap.enabled
        col = box.column(align=True)
        col.prop(snap, "af_object_snap")
        col.prop(snap, "show_snap_cursor")


# ════════════════════════════════════════════════════════════
#  REGISTRO
# ════════════════════════════════════════════════════════════
classes = [
    AF_SnapSettings,
    ARCHIFORGE_OT_snap_toggle,
    ARCHIFORGE_OT_snap_set_grid,
    ARCHIFORGE_OT_snap_sync_blender,
    ARCHIFORGE_PT_snap,
]


def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except Exception as e:
            print(f"[ArchiForge] ⚠️  af_snap '{cls.__name__}': {e}")

    bpy.types.Scene.af_snap = PointerProperty(
        type        = AF_SnapSettings,
        name        = "AF Snap",
        description = "ArchiForge snap settings",
    )
    print("[ArchiForge] ✅ af_snap — registered")


def unregister():
    if hasattr(bpy.types.Scene, "af_snap"):
        del bpy.types.Scene.af_snap

    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"[ArchiForge] ⚠️  af_snap '{cls.__name__}': {e}")

    print("[ArchiForge] 🔴 af_snap — unregistered")