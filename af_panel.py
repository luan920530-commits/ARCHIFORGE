# -*- coding: utf-8 -*-

# ╔══════════════════════════════════════════════════════════╗
# ║         ARCHIFORGE — af_panel.py                        ║
# ║         Paneles UI Centralizados — Blender 3.3 LTS      ║
# ║         GPL v3 — ArchiForge Devs                        ║
# ╚══════════════════════════════════════════════════════════╝

# <pep8 compliant>

# ════════════════════════════════════════════════════════════
#  ¿QUÉ HACE ESTE MÓDULO?
#
#  Sistema de paneles UI centralizado de ArchiForge:
#
#  Paneles incluidos:
#  - ARCHIFORGE_PT_tools        : Herramientas globales
#  - ARCHIFORGE_PT_object_info  : Info contextual del objeto
#  - ARCHIFORGE_PT_scene        : Vista global de la escena
#  - ARCHIFORGE_PT_quick_edit   : Edición rápida multi-objeto
#  - ARCHIFORGE_PT_snap_tools   : Herramientas de snap AF
#
#  Operadores incluidos:
#  - Preset menus (door/window/stair/fence/floor/roof)
#  - Select AF objects by type
#  - Scene statistics
#  - Batch operations
# ════════════════════════════════════════════════════════════

import bpy
import math

from bpy.types import (
    Panel,
    Operator,
    Menu,
    UIList,
)
from bpy.props import (
    StringProperty,
    BoolProperty,
    EnumProperty,
    IntProperty,
    FloatProperty,
)

try:
    from .af_i18n import tr_report as _tr
except ImportError:  # pragma: no cover - fuera del paquete
    def _tr(text):
        return text


# ════════════════════════════════════════════════════════════
#  CONSTANTES — propiedades de cada tipo de objeto AF
# ════════════════════════════════════════════════════════════

# Mapa: prop_attr → (label, icon, panel_idname)
AF_OBJECT_TYPES = {
    "archiforge_wall"      : ("Wall",         'SNAP_EDGE',      "ARCHIFORGE_PT_wall"),
    "archiforge_floor"     : ("Floor",         'MESH_GRID',      "ARCHIFORGE_PT_floor"),
    "archiforge_slab"      : ("Slab",          'MESH_PLANE',     "ARCHIFORGE_PT_slab"),
    "archiforge_stair"     : ("Stair",         'OBJECT_DATA',    "ARCHIFORGE_PT_stair"),
    "archiforge_roof"      : ("Roof",          'MOD_BUILD',      "ARCHIFORGE_PT_roof"),
    "archiforge_door"      : ("Door",          'MESH_CUBE',      "ARCHIFORGE_PT_door"),
    "archiforge_window"    : ("Window",        'MOD_LATTICE',    "ARCHIFORGE_PT_window"),
    "archiforge_fence"     : ("Fence",         'MESH_PLANE',     "ARCHIFORGE_PT_fence"),
}

# Atributo is_af_* de cada PropertyGroup
AF_IS_ATTR = {
    "archiforge_wall"   : "is_af_wall",
    "archiforge_floor"  : "is_af_floor",
    "archiforge_slab"   : "is_af_slab",
    "archiforge_stair"  : "is_af_stair",
    "archiforge_roof"   : "is_af_roof",
    "archiforge_door"   : "is_af_door",
    "archiforge_window" : "is_af_window",
    "archiforge_fence"  : "is_af_fence",
}


def _detect_af_type(obj):
    """
    Detecta el tipo ArchiForge del objeto activo.
    Retorna (prop_attr, label, icon, panel_id) o None.
    """
    if obj is None or obj.type != 'MESH':
        return None
    for attr, (label, icon, panel_id) in AF_OBJECT_TYPES.items():
        if not hasattr(obj, attr):
            continue
        is_attr = AF_IS_ATTR.get(attr, "")
        prop    = getattr(obj, attr, None)
        if prop is None:
            continue
        if getattr(prop, is_attr, False):
            return attr, label, icon, panel_id
    return None


def _get_af_objects(scene):
    """
    Devuelve lista de (obj, attr, label, icon) de todos los
    objetos ArchiForge en la escena.
    """
    result = []
    for obj in scene.objects:
        info = _detect_af_type(obj)
        if info:
            attr, label, icon, _ = info
            result.append((obj, attr, label, icon))
    return result


def _count_af_by_type(scene):
    """Devuelve dict con conteo por tipo."""
    counts = {attr: 0 for attr in AF_OBJECT_TYPES}
    for obj in scene.objects:
        for attr, (label, icon, _) in AF_OBJECT_TYPES.items():
            if not hasattr(obj, attr):
                continue
            is_attr = AF_IS_ATTR.get(attr, "")
            prop    = getattr(obj, attr, None)
            if prop and getattr(prop, is_attr, False):
                counts[attr] += 1
    return counts


# ════════════════════════════════════════════════════════════
#  PRESET MENU — Operador base genérico
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_OT_preset_menu_invoke(Operator):
    """
    Operador genérico para invocar un operador
    desde un preset menu.
    """
    bl_idname  = "archiforge.preset_menu_invoke"
    bl_label   = "Invoke Preset"
    bl_options = {'INTERNAL'}

    operator_id : StringProperty(
        name    = "Operator ID",
        default = "",
    )

    def execute(self, context):
        if not self.operator_id:
            return {'CANCELLED'}
        try:
            parts = self.operator_id.split(".")
            if len(parts) == 2:
                category, name = parts
                op = getattr(getattr(bpy.ops, category), name)
                op('INVOKE_DEFAULT')
        except Exception as e:
            self.report({'ERROR'}, _tr("Could not invoke '{}': {}")
                                   .format(self.operator_id, e))
            return {'CANCELLED'}
        return {'FINISHED'}


# ════════════════════════════════════════════════════════════
#  PRESET MENUS — uno por tipo de objeto
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_MT_preset_door(Menu):
    bl_label  = "Door Presets"
    bl_idname = "ARCHIFORGE_MT_preset_door"

    def draw(self, context):
        layout = self.layout
        layout.operator_context = 'INVOKE_DEFAULT'
        layout.operator("archiforge.door", text="Default Door",   icon='MESH_CUBE')
        layout.separator()
        layout.operator("archiforge.door", text="Single — Flush", icon='MESH_CUBE')
        layout.operator("archiforge.door", text="Single — Panel", icon='MESH_CUBE')
        layout.operator("archiforge.door", text="Double — Panel", icon='MESH_CUBE')
        layout.operator("archiforge.door", text="Sliding",        icon='MESH_CUBE')
        layout.operator("archiforge.door", text="Garage",         icon='MESH_CUBE')


class ARCHIFORGE_MT_preset_window(Menu):
    bl_label  = "Window Presets"
    bl_idname = "ARCHIFORGE_MT_preset_window"

    def draw(self, context):
        layout = self.layout
        layout.operator_context = 'INVOKE_DEFAULT'
        layout.operator("archiforge.window", text="Default Window",      icon='MOD_LATTICE')
        layout.separator()
        layout.operator("archiforge.window", text="Fixed",               icon='MOD_LATTICE')
        layout.operator("archiforge.window", text="Single Hung",         icon='MOD_LATTICE')
        layout.operator("archiforge.window", text="Double Hung",         icon='MOD_LATTICE')
        layout.operator("archiforge.window", text="Casement",            icon='MOD_LATTICE')
        layout.operator("archiforge.window", text="Arched",              icon='MOD_LATTICE')
        layout.operator("archiforge.window", text="Bay Window (3-panel)",icon='MOD_LATTICE')


class ARCHIFORGE_MT_preset_stair(Menu):
    bl_label  = "Stair Presets"
    bl_idname = "ARCHIFORGE_MT_preset_stair"

    def draw(self, context):
        layout = self.layout
        layout.operator_context = 'INVOKE_DEFAULT'
        layout.operator("archiforge.stair", text="Default Stair",      icon='OBJECT_DATA')
        layout.separator()
        layout.operator("archiforge.stair", text="Straight — Open",    icon='OBJECT_DATA')
        layout.operator("archiforge.stair", text="Straight — Closed",  icon='OBJECT_DATA')
        layout.operator("archiforge.stair", text="L-Shape",            icon='OBJECT_DATA')
        layout.operator("archiforge.stair", text="U-Shape",            icon='OBJECT_DATA')
        layout.operator("archiforge.stair", text="Spiral",             icon='OBJECT_DATA')


class ARCHIFORGE_MT_preset_fence(Menu):
    bl_label  = "Fence Presets"
    bl_idname = "ARCHIFORGE_MT_preset_fence"

    def draw(self, context):
        layout = self.layout
        layout.operator_context = 'INVOKE_DEFAULT'
        layout.operator("archiforge.fence", text="Default Fence",       icon='MESH_PLANE')
        layout.separator()
        layout.operator("archiforge.fence", text="Wood Picket",         icon='MESH_PLANE')
        layout.operator("archiforge.fence", text="Wood Privacy",        icon='MESH_PLANE')
        layout.operator("archiforge.fence", text="Metal Rail",          icon='MESH_PLANE')
        layout.operator("archiforge.fence", text="Glass Rail",          icon='MESH_PLANE')
        layout.operator("archiforge.fence", text="Brick Wall",          icon='MESH_PLANE')
        layout.separator()
        layout.operator("archiforge.fence_from_curve",
                         text="From Curve", icon='CURVE_DATA')


class ARCHIFORGE_MT_preset_floor(Menu):
    bl_label  = "Floor Presets"
    bl_idname = "ARCHIFORGE_MT_preset_floor"

    def draw(self, context):
        layout = self.layout
        layout.operator_context = 'INVOKE_DEFAULT'
        layout.operator("archiforge.floor", text="Default Floor",      icon='MESH_GRID')
        layout.separator()
        layout.operator("archiforge.floor", text="Regular Tile",       icon='MESH_GRID')
        layout.operator("archiforge.floor", text="Offset / Brick",     icon='MESH_GRID')
        layout.operator("archiforge.floor", text="Herringbone",        icon='MESH_GRID')
        layout.operator("archiforge.floor", text="Parquet",            icon='MESH_GRID')
        layout.operator("archiforge.floor", text="Hexagonal",          icon='MESH_GRID')
        layout.operator("archiforge.floor", text="Wood Planks",        icon='MESH_GRID')
        layout.operator("archiforge.floor", text="Cobblestone",        icon='MESH_GRID')
        layout.separator()
        layout.operator("archiforge.floor_from_curve",
                         text="From Curve", icon='CURVE_DATA')
        layout.operator("archiforge.floor_from_wall",
                         text="From Wall",  icon='SNAP_FACE')


class ARCHIFORGE_MT_preset_roof(Menu):
    bl_label  = "Roof Presets"
    bl_idname = "ARCHIFORGE_MT_preset_roof"

    def draw(self, context):
        layout = self.layout
        layout.operator_context = 'INVOKE_DEFAULT'
        layout.operator("archiforge.roof", text="Default Roof",        icon='MOD_BUILD')
        layout.separator()
        layout.operator("archiforge.roof", text="Gable",               icon='MOD_BUILD')
        layout.operator("archiforge.roof", text="Hip",                 icon='MOD_BUILD')
        layout.operator("archiforge.roof", text="Flat",                icon='MOD_BUILD')
        layout.operator("archiforge.roof", text="Shed",                icon='MOD_BUILD')
        layout.operator("archiforge.roof", text="Gambrel",             icon='MOD_BUILD')
        layout.operator("archiforge.roof", text="Mansard",             icon='MOD_BUILD')


# ════════════════════════════════════════════════════════════
#  OPERADORES — Preset Menu Launchers
#  (referenciados desde __init__.py como
#   "archiforge.door_preset_menu" etc.)
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_OT_door_preset_menu(Operator):
    bl_idname      = "archiforge.door_preset_menu"
    bl_label       = "Door Presets"
    bl_description = "Choose a door preset"
    bl_options     = {'REGISTER'}

    preset_operator : StringProperty(
        name    = "Preset Operator",
        default = "archiforge.door",
    )

    def execute(self, context):
        bpy.ops.wm.call_menu(name="ARCHIFORGE_MT_preset_door")
        return {'FINISHED'}

    def invoke(self, context, event):
        bpy.ops.wm.call_menu(name="ARCHIFORGE_MT_preset_door")
        return {'FINISHED'}


class ARCHIFORGE_OT_window_preset_menu(Operator):
    bl_idname      = "archiforge.window_preset_menu"
    bl_label       = "Window Presets"
    bl_description = "Choose a window preset"
    bl_options     = {'REGISTER'}

    preset_operator : StringProperty(
        name    = "Preset Operator",
        default = "archiforge.window",
    )

    def execute(self, context):
        bpy.ops.wm.call_menu(name="ARCHIFORGE_MT_preset_window")
        return {'FINISHED'}

    def invoke(self, context, event):
        bpy.ops.wm.call_menu(name="ARCHIFORGE_MT_preset_window")
        return {'FINISHED'}


class ARCHIFORGE_OT_stair_preset_menu(Operator):
    bl_idname      = "archiforge.stair_preset_menu"
    bl_label       = "Stair Presets"
    bl_description = "Choose a stair preset"
    bl_options     = {'REGISTER'}

    preset_operator : StringProperty(
        name    = "Preset Operator",
        default = "archiforge.stair",
    )

    def execute(self, context):
        bpy.ops.wm.call_menu(name="ARCHIFORGE_MT_preset_stair")
        return {'FINISHED'}

    def invoke(self, context, event):
        bpy.ops.wm.call_menu(name="ARCHIFORGE_MT_preset_stair")
        return {'FINISHED'}


class ARCHIFORGE_OT_fence_preset_menu(Operator):
    bl_idname      = "archiforge.fence_preset_menu"
    bl_label       = "Fence Presets"
    bl_description = "Choose a fence preset"
    bl_options     = {'REGISTER'}

    preset_operator : StringProperty(
        name    = "Preset Operator",
        default = "archiforge.fence",
    )

    def execute(self, context):
        bpy.ops.wm.call_menu(name="ARCHIFORGE_MT_preset_fence")
        return {'FINISHED'}

    def invoke(self, context, event):
        bpy.ops.wm.call_menu(name="ARCHIFORGE_MT_preset_fence")
        return {'FINISHED'}


class ARCHIFORGE_OT_floor_preset_menu(Operator):
    bl_idname      = "archiforge.floor_preset_menu"
    bl_label       = "Floor Presets"
    bl_description = "Choose a floor pattern preset"
    bl_options     = {'REGISTER'}

    preset_operator : StringProperty(
        name    = "Preset Operator",
        default = "archiforge.floor",
    )

    def execute(self, context):
        bpy.ops.wm.call_menu(name="ARCHIFORGE_MT_preset_floor")
        return {'FINISHED'}

    def invoke(self, context, event):
        bpy.ops.wm.call_menu(name="ARCHIFORGE_MT_preset_floor")
        return {'FINISHED'}


class ARCHIFORGE_OT_roof_preset_menu(Operator):
    bl_idname      = "archiforge.roof_preset_menu"
    bl_label       = "Roof Presets"
    bl_description = "Choose a roof preset"
    bl_options     = {'REGISTER'}

    preset_operator : StringProperty(
        name    = "Preset Operator",
        default = "archiforge.roof",
    )

    def execute(self, context):
        bpy.ops.wm.call_menu(name="ARCHIFORGE_MT_preset_roof")
        return {'FINISHED'}

    def invoke(self, context, event):
        bpy.ops.wm.call_menu(name="ARCHIFORGE_MT_preset_roof")
        return {'FINISHED'}


# ════════════════════════════════════════════════════════════
#  OPERADORES — Selección y Utilidades de Escena
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_OT_select_by_type(Operator):
    """Selecciona todos los objetos AF de un tipo dado."""
    bl_idname      = "archiforge.select_by_type"
    bl_label       = "Select AF Objects by Type"
    bl_description = "Select all ArchiForge objects of the given type"
    bl_options     = {'REGISTER', 'UNDO'}

    af_type : StringProperty(
        name    = "AF Type",
        default = "archiforge_wall",
    )

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        attr     = self.af_type
        is_attr  = AF_IS_ATTR.get(attr, "")
        count    = 0

        for obj in context.scene.objects:
            if not hasattr(obj, attr):
                continue
            prop = getattr(obj, attr, None)
            if prop and getattr(prop, is_attr, False):
                obj.select_set(True)
                count += 1

        if count:
            label = AF_OBJECT_TYPES.get(attr, ("Unknown",))[0]
            self.report({'INFO'}, _tr("Selected {} {} object(s)").format(count, label))
        else:
            self.report({'WARNING'}, _tr("No objects of this type found"))
        return {'FINISHED'}


class ARCHIFORGE_OT_select_all_af(Operator):
    """Selecciona todos los objetos ArchiForge en la escena."""
    bl_idname      = "archiforge.select_all"
    bl_label       = "Select All AF Objects"
    bl_description = "Select all ArchiForge parametric objects in the scene"
    bl_options     = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        count = 0
        for obj, attr, label, icon in _get_af_objects(context.scene):
            obj.select_set(True)
            count += 1
        self.report({'INFO'}, _tr("Selected {} ArchiForge object(s)").format(count))
        return {'FINISHED'}


class ARCHIFORGE_OT_rebuild_all(Operator):
    """
    Fuerza el rebuild de todos los objetos AF en la escena.
    Útil tras cargar un archivo o cambiar de versión.
    """
    bl_idname      = "archiforge.rebuild_all"
    bl_label       = "Rebuild All AF Objects"
    bl_description = "Force rebuild mesh on all ArchiForge objects in scene"
    bl_options     = {'REGISTER', 'UNDO'}

    def execute(self, context):
        rebuilt = 0
        errors  = 0

        for obj, attr, label, icon in _get_af_objects(context.scene):
            try:
                # Cada módulo expone un _rebuild_*_mesh(obj, props)
                prop = getattr(obj, attr)
                # Trick: disparar un update tocando una propiedad no crítica
                # Alternativa: llamar al operador de update de cada tipo
                rebuild_op_map = {
                    "archiforge_wall"   : "archiforge.wall_update",
                    "archiforge_floor"  : "archiforge.floor_update",
                    "archiforge_slab"   : "archiforge.slab_update",
                    "archiforge_stair"  : "archiforge.stair_update",
                    "archiforge_roof"   : "archiforge.roof_update",
                    "archiforge_door"   : "archiforge.door_update",
                    "archiforge_window" : "archiforge.window_update",
                    "archiforge_fence"  : "archiforge.fence_update",
                }
                op_id = rebuild_op_map.get(attr)
                if op_id:
                    context.view_layer.objects.active = obj
                    parts = op_id.split(".")
                    op    = getattr(getattr(bpy.ops, parts[0]), parts[1])
                    op()
                rebuilt += 1
            except Exception as e:
                errors += 1

        msg = _tr("Rebuilt {} object(s)").format(rebuilt)
        if errors:
            msg += _tr(" | {} error(s)").format(errors)
            self.report({'WARNING'}, msg)
        else:
            self.report({'INFO'}, msg)
        return {'FINISHED'}


class ARCHIFORGE_OT_isolate_af_type(Operator):
    """
    Oculta todos los objetos NO pertenecientes al tipo AF dado.
    Toggle: segunda ejecución restaura visibilidad.
    """
    bl_idname      = "archiforge.isolate_type"
    bl_label       = "Isolate AF Type"
    bl_description = "Show only objects of this AF type"
    bl_options     = {'REGISTER', 'UNDO'}

    af_type : StringProperty(
        name    = "AF Type",
        default = "",
    )

    def execute(self, context):
        attr    = self.af_type
        is_attr = AF_IS_ATTR.get(attr, "")

        for obj in context.scene.objects:
            prop = getattr(obj, attr, None) if hasattr(obj, attr) else None
            is_af_obj = prop and getattr(prop, is_attr, False)
            obj.hide_viewport = not is_af_obj

        label = AF_OBJECT_TYPES.get(attr, ("Unknown",))[0]
        self.report({'INFO'}, _tr("Isolating: {} objects").format(label))
        return {'FINISHED'}


class ARCHIFORGE_OT_show_all(Operator):
    """Restaura la visibilidad de todos los objetos AF."""
    bl_idname      = "archiforge.show_all"
    bl_label       = "Show All AF Objects"
    bl_description = "Restore visibility of all ArchiForge objects"
    bl_options     = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for obj, attr, label, icon in _get_af_objects(context.scene):
            obj.hide_viewport = False
        self.report({'INFO'}, _tr("All AF objects visible"))
        return {'FINISHED'}


# ════════════════════════════════════════════════════════════
#  PANEL: OBJECT INFO — contextual, detecta tipo AF
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_PT_object_info(Panel):
    bl_label       = "Object Info"
    bl_idname      = "ARCHIFORGE_PT_object_info"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "ArchiForge"
    bl_context     = "objectmode"
    bl_order       = 1

    @classmethod
    def poll(cls, context):
        return _detect_af_type(context.active_object) is not None

    def draw_header(self, context):
        info = _detect_af_type(context.active_object)
        if info:
            self.layout.label(text="", icon=info[2])

    def draw(self, context):
        obj    = context.active_object
        layout = self.layout
        layout.use_property_split   = True
        layout.use_property_decorate = False

        info = _detect_af_type(obj)
        if info is None:
            return

        attr, label, icon, panel_id = info
        prop = getattr(obj, attr)

        # ── Cabecera del objeto ───────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        row = col.row(align=True)
        row.label(text=f"{label}", icon=icon)
        row.label(text=obj.name, icon='OBJECT_DATA')

        # ── Dimensiones del bounding box ─────────────────────
        bb  = obj.bound_box
        xs  = [v[0] for v in bb]
        ys  = [v[1] for v in bb]
        zs  = [v[2] for v in bb]
        dim = (
            max(xs) - min(xs),
            max(ys) - min(ys),
            max(zs) - min(zs),
        )

        col = box.column(align=True)
        col.label(text="Dimensions (World)", icon='ARROW_LEFTRIGHT')
        row = col.row(align=True)
        row.label(text=f"W: {dim[0]:.3f}m")
        row.label(text=f"D: {dim[1]:.3f}m")
        row.label(text=f"H: {dim[2]:.3f}m")

        # ── Número de polígonos ───────────────────────────────
        me = obj.data
        col.separator(factor=0.3)
        col.label(
            text=f"Polygons: {len(me.polygons):,} | "
                 f"Verts: {len(me.vertices):,}",
            icon='MESH_DATA'
        )

        # ── Materiales asignados ──────────────────────────────
        if obj.material_slots:
            col.separator(factor=0.3)
            col.label(text="Materials:", icon='MATERIAL')
            for i, slot in enumerate(obj.material_slots):
                mat_name = slot.material.name if slot.material else "(empty)"
                col.label(text=f"  [{i}] {mat_name}")

        # ── Botón de edición rápida ───────────────────────────
        layout.separator(factor=0.3)
        # Busca el operador de update del tipo activo
        update_op_map = {
            "archiforge_wall"   : "archiforge.wall_update",
            "archiforge_floor"  : "archiforge.floor_update",
            "archiforge_slab"   : "archiforge.slab_update",
            "archiforge_stair"  : "archiforge.stair_update",
            "archiforge_roof"   : "archiforge.roof_update",
            "archiforge_door"   : "archiforge.door_update",
            "archiforge_window" : "archiforge.window_update",
            "archiforge_fence"  : "archiforge.fence_update",
        }
        op_id = update_op_map.get(attr, "")
        if op_id:
            parts = op_id.split(".")
            row   = layout.row(align=True)
            row.operator(op_id, text="Force Rebuild", icon='FILE_REFRESH')
            row.operator(
                "archiforge.isolate_type",
                text="", icon='HIDE_OFF'
            ).af_type = attr


# ════════════════════════════════════════════════════════════
#  PANEL: SCENE OVERVIEW
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_PT_scene(Panel):
    bl_label       = "Scene"
    bl_idname      = "ARCHIFORGE_PT_scene"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "ArchiForge"
    bl_context     = "objectmode"
    bl_order       = 10
    bl_options     = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def draw_header(self, context):
        self.layout.label(text="", icon='SCENE_DATA')

    def draw(self, context):
        layout = self.layout
        layout.use_property_split   = False
        layout.use_property_decorate = False
        scene  = context.scene

        # ── Estadísticas por tipo ─────────────────────────────
        counts = _count_af_by_type(scene)
        total  = sum(counts.values())

        box = layout.box()
        col = box.column(align=True)
        row = col.row()
        row.label(
            text=f"Total AF Objects: {total}",
            icon='INFO'
        )
        col.separator(factor=0.3)

        for attr, (label, icon, _) in AF_OBJECT_TYPES.items():
            n = counts.get(attr, 0)
            if n == 0:
                continue
            row = col.row(align=True)
            row.label(text=f"  {label}:", icon=icon)
            row.label(text=str(n))
            sub = row.row(align=True)
            sub.scale_x = 0.7
            op = sub.operator(
                "archiforge.select_by_type",
                text="", icon='RESTRICT_SELECT_OFF'
            )
            op.af_type = attr

        if total == 0:
            col.label(
                text="No ArchiForge objects in scene",
                icon='ERROR'
            )

        # ── Acciones globales ─────────────────────────────────
        layout.separator(factor=0.3)
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Actions", icon='TOOL_SETTINGS')

        row = col.row(align=True)
        row.operator(
            "archiforge.select_all",
            text="Select All AF",
            icon='RESTRICT_SELECT_OFF'
        )
        row.operator(
            "archiforge.show_all",
            text="", icon='HIDE_OFF'
        )

        col.separator(factor=0.3)
        col.operator(
            "archiforge.rebuild_all",
            text="Rebuild All Objects",
            icon='FILE_REFRESH'
        )

        # ── Lista detallada (colapsable) ──────────────────────
        box = layout.box()
        row = box.row()
        row.label(text="Object List", icon='OUTLINER_OB_MESH')

        if total > 0:
            af_objs = _get_af_objects(scene)
            col = box.column(align=True)
            for obj, attr, label, icon in af_objs[:20]:  # máx 20
                row = col.row(align=True)
                icon_sel = 'RESTRICT_SELECT_OFF' \
                    if obj.select_get() else 'RESTRICT_SELECT_ON'
                row.label(text=obj.name, icon=icon)
                row.label(text=label)
                sub = row.row(align=True)
                sub.scale_x = 0.6
                sub.prop(obj, "hide_viewport", text="", emboss=False)

            if total > 20:
                box.label(
                    text=f"  ... and {total - 20} more",
                    icon='INFO'
                )
        else:
            box.label(text="  (empty)", icon='DOT')


# ════════════════════════════════════════════════════════════
#  PANEL: TOOLS — Herramientas globales ArchiForge
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_PT_tools(Panel):
    bl_label       = "Tools"
    bl_idname      = "ARCHIFORGE_PT_tools"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "ArchiForge"
    bl_context     = "objectmode"
    bl_order       = 20
    bl_options     = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def draw_header(self, context):
        self.layout.label(text="", icon='TOOL_SETTINGS')

    def draw(self, context):
        layout = self.layout
        layout.use_property_split   = False
        layout.use_property_decorate = False

        # ── Boolean ───────────────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Boolean", icon='MOD_BOOLEAN')
        row = col.row(align=True)
        op = row.operator(
            "archiforge.auto_boolean",
            text="Auto Boolean",
            icon='MOD_BOOLEAN'
        )
        op.mode = 'HYBRID'
        row2 = col.row(align=True)
        op2 = row2.operator(
            "archiforge.auto_boolean",
            text="Apply All",
            icon='CHECKMARK'
        )
        op2.mode = 'APPLY'

        # ── Wall Tools ────────────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Wall Tools", icon='SNAP_EDGE')
        row = col.row(align=True)
        row.operator(
            "archiforge.wall_draw",
            text="Draw Wall",
            icon='GREASEPENCIL'
        )
        row.operator(
            "archiforge.wall_from_curve",
            text="From Curve",
            icon='CURVE_DATA'
        )
        col.operator(
            "archiforge.wall_from_slab",
            text="Wall from Slab",
            icon='MESH_PLANE'
        )

        # ── Slab Tools ────────────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Slab Tools", icon='MESH_PLANE')
        row = col.row(align=True)
        row.operator(
            "archiforge.slab_from_wall",
            text="Floor",
            icon='MESH_PLANE'
        ).ceiling = False
        row.operator(
            "archiforge.slab_from_wall",
            text="Ceiling",
            icon='MESH_PLANE'
        ).ceiling = True
        col.operator(
            "archiforge.slab_from_curve",
            text="Slab from Curve",
            icon='CURVE_DATA'
        )

        # ── Fence Tools ───────────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Fence Tools", icon='MESH_PLANE')
        col.operator(
            "archiforge.fence_from_curve",
            text="Fence from Curve",
            icon='CURVE_DATA'
        )

        # ── Floor Tools ───────────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Floor Tools", icon='MESH_GRID')
        row = col.row(align=True)
        row.operator(
            "archiforge.floor_from_curve",
            text="From Curve",
            icon='CURVE_DATA'
        )
        row.operator(
            "archiforge.floor_from_wall",
            text="From Wall",
            icon='SNAP_FACE'
        )


# ════════════════════════════════════════════════════════════
#  PANEL: QUICK EDIT — propiedades rápidas del objeto activo
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_PT_quick_edit(Panel):
    bl_label       = "Quick Edit"
    bl_idname      = "ARCHIFORGE_PT_quick_edit"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "ArchiForge"
    bl_context     = "objectmode"
    bl_order       = 2
    bl_options     = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return _detect_af_type(context.active_object) is not None

    def draw_header(self, context):
        self.layout.label(text="", icon='PREFERENCES')

    def draw(self, context):
        obj    = context.active_object
        layout = self.layout
        layout.use_property_split   = True
        layout.use_property_decorate = False

        info = _detect_af_type(obj)
        if not info:
            return

        attr, label, icon, panel_id = info
        prop = getattr(obj, attr)

        # ── Dimensiones comunes ───────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Common Dimensions", icon='ARROW_LEFTRIGHT')

        # Muestra las props más relevantes según tipo
        # sin duplicar todo el panel específico
        shown = self._draw_quick_props(col, prop, attr)

        if not shown:
            col.label(
                text="Open specific panel for details",
                icon='INFO'
            )

        # ── Transform ────────────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Transform", icon='OBJECT_DATA')
        col.prop(obj, "location")
        col.prop(obj, "rotation_euler", text="Rotation")

    def _draw_quick_props(self, col, prop, attr):
        """
        Muestra las 2-3 props más importantes según tipo.
        Retorna True si mostró algo.
        """
        shown = False

        quick_map = {
            "archiforge_wall"  : ["width", "height", "thickness"],
            "archiforge_floor" : ["width", "depth", "tile_width"],
            "archiforge_slab"  : ["width", "depth", "thickness"],
            "archiforge_stair" : ["step_count", "step_width", "step_height"],
            "archiforge_roof"  : ["width", "depth", "ridge_height"],
            "archiforge_door"  : ["width", "height", "depth"],
            "archiforge_window": ["width", "height", "depth"],
            "archiforge_fence" : ["height", "post_spacing", "fence_type"],
        }

        props_to_show = quick_map.get(attr, [])
        for prop_name in props_to_show:
            if hasattr(prop, prop_name):
                try:
                    col.prop(prop, prop_name)
                    shown = True
                except Exception:
                    pass

        return shown


# ════════════════════════════════════════════════════════════
#  PANEL: SNAP TOOLS (UI only — lógica en af_snap.py)
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_PT_snap_tools(Panel):
    bl_label       = "Snap & Grid"
    bl_idname      = "ARCHIFORGE_PT_snap_tools"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "ArchiForge"
    bl_context     = "objectmode"
    bl_order       = 30
    bl_options     = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def draw_header(self, context):
        self.layout.label(text="", icon='SNAP_ON')

    def draw(self, context):
        layout = self.layout
        layout.use_property_split   = True
        layout.use_property_decorate = False
        scene  = context.scene
        ts     = context.scene.tool_settings

        # ── Snap nativo de Blender ────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Blender Snap", icon='SNAP_ON')

        row = col.row(align=True)
        row.prop(ts, "use_snap", text="Enable Snap", toggle=True)
        if ts.use_snap:
            col.prop(ts, "snap_elements", text="")
            col.prop(ts, "snap_target")
            col.prop(ts, "use_snap_align_rotation")

        # ── Grid de ArchiForge ────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="AF Grid Helpers", icon='GRID')

        # Accesos rápidos a resolución de grilla
        row = col.row(align=True)
        row.label(text="Common:")
        for val, lbl in [
            (0.05, "5cm"),
            (0.10, "10cm"),
            (0.25, "25cm"),
            (0.50, "50cm"),
        ]:
            op = row.operator(
                "archiforge.set_grid",
                text=lbl,
            )
            op.grid_size = val

        # ── Overlay del viewport ──────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Viewport Overlays", icon='OVERLAY')
        overlay = context.space_data.overlay
        col.prop(overlay, "show_floor",      text="Floor Grid")
        col.prop(overlay, "show_axis_x",     text="X Axis")
        col.prop(overlay, "show_axis_y",     text="Y Axis")
        col.prop(overlay, "show_axis_z",     text="Z Axis")
        col.prop(overlay, "grid_scale",      text="Grid Scale")
        col.prop(overlay, "grid_subdivisions", text="Subdivisions")


# ════════════════════════════════════════════════════════════
#  OPERADOR: Set Grid — helper para ARCHIFORGE_PT_snap_tools
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_OT_set_grid(Operator):
    bl_idname      = "archiforge.set_grid"
    bl_label       = "Set Grid Size"
    bl_description = "Set viewport grid scale"
    bl_options     = {'REGISTER'}

    grid_size : FloatProperty(
        name    = "Grid Size",
        default = 0.10,
        min     = 0.001,
    )

    def execute(self, context):
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.overlay.grid_scale = self.grid_size
        self.report({'INFO'}, _tr("Grid set to {:.3f}m").format(self.grid_size))
        return {'FINISHED'}


# ════════════════════════════════════════════════════════════
#  REGISTRO
# ════════════════════════════════════════════════════════════
classes = [
    # — Operadores de preset menus —
    ARCHIFORGE_OT_preset_menu_invoke,
    ARCHIFORGE_OT_door_preset_menu,
    ARCHIFORGE_OT_window_preset_menu,
    ARCHIFORGE_OT_stair_preset_menu,
    ARCHIFORGE_OT_fence_preset_menu,
    ARCHIFORGE_OT_floor_preset_menu,
    ARCHIFORGE_OT_roof_preset_menu,

    # — Preset menus —
    ARCHIFORGE_MT_preset_door,
    ARCHIFORGE_MT_preset_window,
    ARCHIFORGE_MT_preset_stair,
    ARCHIFORGE_MT_preset_fence,
    ARCHIFORGE_MT_preset_floor,
    ARCHIFORGE_MT_preset_roof,

    # — Operadores de escena —
    ARCHIFORGE_OT_select_by_type,
    ARCHIFORGE_OT_select_all_af,
    ARCHIFORGE_OT_rebuild_all,
    ARCHIFORGE_OT_isolate_af_type,
    ARCHIFORGE_OT_show_all,
    ARCHIFORGE_OT_set_grid,

    # — Paneles —
    ARCHIFORGE_PT_object_info,
    ARCHIFORGE_PT_quick_edit,
    ARCHIFORGE_PT_scene,
    ARCHIFORGE_PT_tools,
    ARCHIFORGE_PT_snap_tools,
]


def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except Exception as e:
            print(f"[ArchiForge] ⚠️  af_panel: could not register "
                  f"'{cls.__name__}': {e}")
    print("[ArchiForge] ✅ af_panel — registered")


def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"[ArchiForge] ⚠️  af_panel: could not unregister "
                  f"'{cls.__name__}': {e}")
    print("[ArchiForge] 🔴 af_panel — unregistered")