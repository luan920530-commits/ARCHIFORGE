# -*- coding: utf-8 -*-

# ╔══════════════════════════════════════════════════════════╗
# ║         ARCHIFORGE — af_reference_point.py              ║
# ║         Punto de Referencia Global — Blender 3.3 LTS    ║
# ║         GPL v3 — ArchiForge Devs                        ║
# ╚══════════════════════════════════════════════════════════╝

# <pep8 compliant>

# ════════════════════════════════════════════════════════════
#  ¿QUÉ HACE ESTE MÓDULO?
#
#  Gestiona el Punto de Referencia Global (PRG) de ArchiForge:
#  - Objeto vacío especial que actúa como origen de proyecto
#  - Todos los objetos AF pueden anclarse a él
#  - Permite mover todo el proyecto cambiando solo el PRG
#  - Muestra las coordenadas relativas al PRG en el panel
#  - Compatible con múltiples PRGs (multi-edificio)
# ════════════════════════════════════════════════════════════

import bpy
import math

from mathutils  import Vector
from bpy.types  import PropertyGroup, Operator, Panel
from bpy.props  import (
    StringProperty,
    BoolProperty,
    FloatProperty,
    FloatVectorProperty,
    PointerProperty,
    EnumProperty,
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


# ════════════════════════════════════════════════════════════
#  CONSTANTES
# ════════════════════════════════════════════════════════════
AF_RP_PROP    = "af_reference_point"
AF_RP_NAME    = "AF_ReferencePoint"
AF_RP_ICON    = 'EMPTY_AXIS'
AF_RP_TAG     = "is_af_reference_point"


# ════════════════════════════════════════════════════════════
#  PROPERTYGROUP
# ════════════════════════════════════════════════════════════
class AF_ReferencePointSettings(PropertyGroup):
    """Configuración global de puntos de referencia."""

    active_rp_name : StringProperty(
        name        = "Active Reference Point",
        description = "Name of the active ArchiForge reference point object",
        default     = "",
    )

    show_coordinates : BoolProperty(
        name        = "Show Coordinates",
        description = "Show coordinates relative to reference point in panel",
        default     = True,
    )

    coordinate_mode : EnumProperty(
        name  = "Coordinate Mode",
        items = [
            ('WORLD',    "World",    "World coordinates"),
            ('RELATIVE', "Relative", "Coordinates relative to reference point"),
            ('PROJECT',  "Project",  "Project-level coordinates"),
        ],
        default = 'RELATIVE',
    )


class AF_ReferencePointProps(PropertyGroup):
    """Propiedades de un punto de referencia individual."""

    is_af_rp : BoolProperty(
        name="Is AF Reference Point", default=True, options={'HIDDEN'},
    )
    rp_label : StringProperty(
        name        = "Label",
        description = "Human-readable label for this reference point",
        default     = "Building Origin",
    )
    elevation : FloatProperty(
        name        = "Base Elevation",
        description = "Z elevation of this reference point (sea level / datum)",
        default     = 0.0,
        unit        = 'LENGTH',
    )
    north_offset : FloatProperty(
        name        = "North Offset",
        description = "Rotation offset to true north (degrees)",
        default     = 0.0,
        min         = -180.0,
        max         = 180.0,
        subtype     = 'ANGLE',
    )
    scale_factor : FloatProperty(
        name        = "Scale Factor",
        description = "Project scale factor (1.0 = 1:1)",
        default     = 1.0,
        min         = 0.001,
        max         = 1000.0,
    )


# ════════════════════════════════════════════════════════════
#  UTILIDADES
# ════════════════════════════════════════════════════════════
def get_active_rp(context):
    """
    Retorna el objeto de referencia activo o None.
    Busca primero por nombre en la configuración, luego
    por la propiedad is_af_rp en todos los objetos.
    """
    settings = getattr(context.scene, AF_RP_PROP, None)
    if settings is None:
        return None

    name = settings.active_rp_name
    if name and name in bpy.data.objects:
        obj = bpy.data.objects[name]
        rp  = getattr(obj, "af_rp_props", None)
        if rp and rp.is_af_rp:
            return obj

    # Fallback: buscar el primero que tenga is_af_rp
    for obj in context.scene.objects:
        rp = getattr(obj, "af_rp_props", None)
        if rp and rp.is_af_rp:
            if settings:
                settings.active_rp_name = obj.name
            return obj

    return None


def get_relative_location(context, world_location: Vector) -> Vector:
    """
    Retorna la posición relativa al punto de referencia activo.
    Si no hay PRG, retorna world_location sin cambios.
    """
    rp = get_active_rp(context)
    if rp is None:
        return world_location
    return world_location - rp.location


def get_all_rps(context):
    """Retorna lista de todos los objetos PRG en la escena."""
    result = []
    for obj in context.scene.objects:
        rp = getattr(obj, "af_rp_props", None)
        if rp and rp.is_af_rp:
            result.append(obj)
    return result


# ════════════════════════════════════════════════════════════
#  OPERADORES
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_OT_rp_create(Operator):
    """Crea un nuevo punto de referencia de ArchiForge."""
    bl_idname      = "archiforge.rp_create"
    bl_label       = "Create Reference Point"
    bl_description = "Create an ArchiForge project reference point"
    bl_options     = {'REGISTER', 'UNDO'}

    label : StringProperty(
        name="Label", default="Building Origin",
    )
    elevation : FloatProperty(
        name="Elevation", default=0.0, unit='LENGTH',
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        col = self.layout.column(align=True)
        col.label(text="Reference Point", icon=AF_RP_ICON)
        col.prop(self, "label")
        col.prop(self, "elevation")

    def execute(self, context):
        # Crear empty en la posición del cursor
        cursor_loc = context.scene.cursor.location.copy()

        bpy.ops.object.empty_add(
            type     = 'ARROWS',
            location = cursor_loc,
        )
        obj = context.active_object
        obj.name            = AF_RP_NAME
        obj.empty_display_size = 0.5
        obj.show_name       = True

        # Asignar propiedades
        rp             = obj.af_rp_props
        rp.is_af_rp    = True
        rp.rp_label    = self.label
        rp.elevation   = self.elevation

        # Registrar como activo
        settings = context.scene.af_reference_point
        settings.active_rp_name = obj.name

        self.report({'INFO'}, _tr("Reference point '{}' created").format(self.label))
        return {'FINISHED'}


class ARCHIFORGE_OT_rp_set_active(Operator):
    """Establece el punto de referencia activo."""
    bl_idname      = "archiforge.rp_set_active"
    bl_label       = "Set Active Reference Point"
    bl_description = "Set selected empty as active ArchiForge reference point"
    bl_options     = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj is not None
            and obj.type == 'EMPTY'
            and hasattr(obj, "af_rp_props")
            and obj.af_rp_props.is_af_rp
        )

    def execute(self, context):
        obj = context.active_object
        context.scene.af_reference_point.active_rp_name = obj.name
        self.report({'INFO'}, _tr("Active RP: '{}'").format(obj.af_rp_props.rp_label))
        return {'FINISHED'}


class ARCHIFORGE_OT_rp_go_to(Operator):
    """Mueve el cursor 3D al punto de referencia activo."""
    bl_idname      = "archiforge.rp_go_to"
    bl_label       = "Go to Reference Point"
    bl_description = "Move 3D cursor to active reference point"
    bl_options     = {'REGISTER', 'UNDO'}

    def execute(self, context):
        rp = get_active_rp(context)
        if rp is None:
            self.report({'WARNING'}, _tr("No active reference point"))
            return {'CANCELLED'}
        context.scene.cursor.location = rp.location.copy()
        self.report({'INFO'}, _tr("Cursor → {}").format(rp.name))
        return {'FINISHED'}


class ARCHIFORGE_OT_rp_center_view(Operator):
    """Centra la vista en el punto de referencia activo."""
    bl_idname      = "archiforge.rp_center_view"
    bl_label       = "Center View on Reference Point"
    bl_description = "Center viewport on the active reference point"
    bl_options     = {'REGISTER'}

    def execute(self, context):
        rp = get_active_rp(context)
        if rp is None:
            self.report({'WARNING'}, _tr("No active reference point"))
            return {'CANCELLED'}

        bpy.ops.object.select_all(action='DESELECT')
        rp.select_set(True)
        context.view_layer.objects.active = rp
        bpy.ops.view3d.view_selected()
        self.report({'INFO'}, _tr("View centered on: {}").format(rp.name))
        return {'FINISHED'}


class ARCHIFORGE_OT_rp_move_project(Operator):
    """
    Mueve todos los objetos AF manteniendo
    sus posiciones relativas al PRG.
    """
    bl_idname      = "archiforge.rp_move_project"
    bl_label       = "Move Project"
    bl_description = "Move all AF objects together with the reference point"
    bl_options     = {'REGISTER', 'UNDO'}

    delta : FloatVectorProperty(
        name    = "Delta",
        default = (0.0, 0.0, 0.0),
        unit    = 'LENGTH',
        size    = 3,
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        col = self.layout.column(align=True)
        col.label(text="Offset (X, Y, Z)", icon='MOVE_TEXTURES')
        col.prop(self, "delta", text="")

    def execute(self, context):
        rp = get_active_rp(context)
        if rp is None:
            self.report({'WARNING'}, _tr("No active reference point"))
            return {'CANCELLED'}

        delta_v = Vector(self.delta)

        # Mover el PRG
        rp.location += delta_v

        # Mover todos los objetos "hijos" del PRG (si los tiene)
        for obj in context.scene.objects:
            if obj.parent == rp:
                obj.location += delta_v

        self.report(
            {'INFO'},
            _tr("Project moved by {}").format(tuple(round(v,3) for v in self.delta))
        )
        return {'FINISHED'}


# ════════════════════════════════════════════════════════════
#  PANEL
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_PT_reference_point(Panel):
    bl_label       = "Reference Point"
    bl_idname      = "ARCHIFORGE_PT_reference_point"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "ArchiForge"
    bl_context     = "objectmode"
    bl_order       = 25
    bl_options     = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def draw_header(self, context):
        self.layout.label(text="", **_icon("reference_point", AF_RP_ICON))

    def draw(self, context):
        layout   = self.layout
        layout.use_property_split   = True
        layout.use_property_decorate = False
        settings = getattr(context.scene, AF_RP_PROP, None)

        # ── Sin PRG ───────────────────────────────────────────
        rp = get_active_rp(context)
        if rp is None:
            box = layout.box()
            col = box.column(align=True)
            col.label(
                text="No reference point in scene",
                icon='INFO'
            )
            col.operator(
                "archiforge.rp_create",
                text="Create Reference Point",
                icon='ADD'
            )
            return

        # ── PRG activo ────────────────────────────────────────
        rp_props = rp.af_rp_props
        box = layout.box()
        col = box.column(align=True)
        col.label(text=rp_props.rp_label, icon=AF_RP_ICON)
        col.prop(rp, "location", text="Position")
        col.prop(rp_props, "elevation")
        col.prop(rp_props, "north_offset")
        col.prop(rp_props, "scale_factor")

        # ── Lista de PRGs ─────────────────────────────────────
        all_rps = get_all_rps(context)
        if len(all_rps) > 1:
            box = layout.box()
            col = box.column(align=True)
            col.label(text="All Reference Points", icon='LINKED')
            for rp_obj in all_rps:
                row = col.row(align=True)
                is_active = (rp_obj.name == settings.active_rp_name)
                row.label(
                    text=rp_obj.af_rp_props.rp_label,
                    icon='FAKE_USER_ON' if is_active else 'FAKE_USER_OFF'
                )
                if not is_active:
                    op = row.operator(
                        "archiforge.rp_set_active",
                        text="Set Active", icon='CHECKMARK'
                    )

        # ── Coordenadas relativas del objeto activo ───────────
        if settings and settings.show_coordinates:
            active = context.active_object
            if active and active != rp:
                rel = get_relative_location(
                    context, active.location
                )
                box = layout.box()
                col = box.column(align=True)
                col.label(
                    text=f"Relative Coords: {active.name}",
                    icon='OBJECT_DATA'
                )
                col.label(
                    text=f"  X: {rel.x:.3f}m  "
                         f"Y: {rel.y:.3f}m  "
                         f"Z: {rel.z:.3f}m"
                )

        # ── Acciones ──────────────────────────────────────────
        layout.separator(factor=0.3)
        row = layout.row(align=True)
        row.operator(
            "archiforge.rp_create",
            text="New", icon='ADD'
        )
        row.operator(
            "archiforge.rp_go_to",
            text="Go To", icon='CURSOR'
        )
        row.operator(
            "archiforge.rp_center_view",
            text="", icon='ZOOM_IN'
        )
        layout.operator(
            "archiforge.rp_move_project",
            text="Move Project",
            icon='MOVE_TEXTURES'
        )

        # ── Settings ─────────────────────────────────────────
        if settings:
            layout.separator(factor=0.3)
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Display", icon='PREFERENCES')
            col.prop(settings, "show_coordinates")
            col.prop(settings, "coordinate_mode")


# ════════════════════════════════════════════════════════════
#  REGISTRO
# ════════════════════════════════════════════════════════════
classes = [
    AF_ReferencePointSettings,
    AF_ReferencePointProps,
    ARCHIFORGE_OT_rp_create,
    ARCHIFORGE_OT_rp_set_active,
    ARCHIFORGE_OT_rp_go_to,
    ARCHIFORGE_OT_rp_center_view,
    ARCHIFORGE_OT_rp_move_project,
    ARCHIFORGE_PT_reference_point,
]


def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except Exception as e:
            print(f"[ArchiForge] ⚠️  af_reference_point '{cls.__name__}': {e}")

    bpy.types.Scene.af_reference_point = PointerProperty(
        type        = AF_ReferencePointSettings,
        name        = "AF Reference Point",
        description = "ArchiForge reference point settings",
    )
    bpy.types.Object.af_rp_props = PointerProperty(
        type        = AF_ReferencePointProps,
        name        = "AF RP Props",
        description = "ArchiForge reference point properties",
    )
    print("[ArchiForge] ✅ af_reference_point — registered")


def unregister():
    if hasattr(bpy.types.Scene, "af_reference_point"):
        del bpy.types.Scene.af_reference_point
    if hasattr(bpy.types.Object, "af_rp_props"):
        del bpy.types.Object.af_rp_props

    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"[ArchiForge] ⚠️  af_reference_point '{cls.__name__}': {e}")

    print("[ArchiForge] 🔴 af_reference_point — unregistered")