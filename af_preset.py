# -*- coding: utf-8 -*-

# ╔══════════════════════════════════════════════════════════╗
# ║         ARCHIFORGE — af_preset.py                       ║
# ║         Sistema de Presets — Blender 3.3 LTS            ║
# ║         GPL v3 — ArchiForge Devs                        ║
# ╚══════════════════════════════════════════════════════════╝

# <pep8 compliant>

# ════════════════════════════════════════════════════════════
#  ¿QUÉ HACE ESTE MÓDULO?
#
#  Sistema de presets para objetos ArchiForge:
#  - Guardar propiedades de un objeto como preset
#  - Cargar preset en un objeto existente
#  - Exportar/Importar presets en JSON
#  - Presets integrados (built-in) por tipo
#  - Biblioteca de presets por proyecto
# ════════════════════════════════════════════════════════════

import bpy
import os
import json
import math

from bpy.types  import (
    PropertyGroup, Operator, Panel, UIList, Menu
)
from bpy.props  import (
    StringProperty, BoolProperty,
    EnumProperty, IntProperty,
    FloatProperty, CollectionProperty,
    PointerProperty,
)


# ════════════════════════════════════════════════════════════
#  CONSTANTES
# ════════════════════════════════════════════════════════════
AF_PRESET_VERSION  = "1.0"
AF_PRESET_EXT      = ".afpreset"
AF_PRESET_SUBDIR   = "archiforge_presets"

# Tipos de objetos que soportan presets
AF_PRESET_TYPES = [
    ('WALL',   "Wall",   "Wall presets",   'SNAP_EDGE',   0),
    ('FLOOR',  "Floor",  "Floor presets",  'MESH_GRID',   1),
    ('DOOR',   "Door",   "Door presets",   'MESH_CUBE',   2),
    ('WINDOW', "Window", "Window presets", 'MOD_LATTICE', 3),
    ('STAIR',  "Stair",  "Stair presets",  'OBJECT_DATA', 4),
    ('ROOF',   "Roof",   "Roof presets",   'MOD_BUILD',   5),
    ('FENCE',  "Fence",  "Fence presets",  'MESH_PLANE',  6),
    ('SLAB',   "Slab",   "Slab presets",   'MESH_PLANE',  7),
]

# Mapa tipo → atributo del objeto
AF_TYPE_TO_PROP = {
    'WALL'   : "archiforge_wall",
    'FLOOR'  : "archiforge_floor",
    'DOOR'   : "archiforge_door",
    'WINDOW' : "archiforge_window",
    'STAIR'  : "archiforge_stair",
    'ROOF'   : "archiforge_roof",
    'FENCE'  : "archiforge_fence",
    'SLAB'   : "archiforge_slab",
}

# Props a NO serializar (internas, no tienen sentido en preset)
AF_SKIP_PROPS = {
    "is_af_wall", "is_af_floor", "is_af_door",
    "is_af_window", "is_af_stair", "is_af_roof",
    "is_af_fence", "is_af_slab",
    "object_name", "name", "rna_type",
    "parts", "vertices", "holes",  # CollectionProperty — no serializable directo
    "n_parts", "n_vertices", "n_holes",  # dependen de las colecciones
}


# ════════════════════════════════════════════════════════════
#  BUILT-IN PRESETS
# ════════════════════════════════════════════════════════════
BUILTIN_PRESETS = {
    'WALL': [
        {
            "name"       : "Exterior 30cm",
            "description": "Standard 30cm exterior wall",
            "props"      : {"thickness": 0.30, "height": 2.80, "width": 0.30},
        },
        {
            "name"       : "Interior 15cm",
            "description": "Standard 15cm interior partition wall",
            "props"      : {"thickness": 0.15, "height": 2.60, "width": 0.15},
        },
        {
            "name"       : "Brick 25cm",
            "description": "Traditional brick wall 25cm",
            "props"      : {"thickness": 0.25, "height": 3.00, "width": 0.25},
        },
        {
            "name"       : "Curtain Wall",
            "description": "Glass curtain wall system",
            "props"      : {"thickness": 0.15, "height": 4.00, "width": 0.15},
        },
    ],
    'FLOOR': [
        {
            "name"       : "60x60 Porcelain",
            "description": "Standard 60x60cm porcelain tile",
            "props"      : {
                "pattern": "REGULAR",
                "tile_width": 0.60, "tile_depth": 0.60,
                "grout_width": 0.004,
            },
        },
        {
            "name"       : "Herringbone Parquet",
            "description": "Classic herringbone wood floor",
            "props"      : {
                "pattern": "HERRINGBONE",
                "tile_width": 0.12, "tile_depth": 0.60,
            },
        },
        {
            "name"       : "Hexagonal 20cm",
            "description": "Hexagonal tile 20cm",
            "props"      : {
                "pattern": "HEXAGONAL",
                "hex_size": 0.10,
            },
        },
        {
            "name"       : "Wood Plank 12cm",
            "description": "12cm wood plank flooring",
            "props"      : {
                "pattern": "WOOD_PLANK",
                "plank_width": 0.12,
            },
        },
    ],
    'DOOR': [
        {
            "name"       : "Standard 90x210",
            "description": "Standard door 90x210cm",
            "props"      : {"width": 0.90, "height": 2.10},
        },
        {
            "name"       : "Double 180x210",
            "description": "Double door 180x210cm",
            "props"      : {"width": 1.80, "height": 2.10},
        },
        {
            "name"       : "Entrance 100x230",
            "description": "Entrance door 100x230cm",
            "props"      : {"width": 1.00, "height": 2.30},
        },
    ],
    'WINDOW': [
        {
            "name"       : "Standard 120x120",
            "description": "Standard window 120x120cm",
            "props"      : {"width": 1.20, "height": 1.20},
        },
        {
            "name"       : "Wide 180x120",
            "description": "Wide window 180x120cm",
            "props"      : {"width": 1.80, "height": 1.20},
        },
        {
            "name"       : "Tall 60x180",
            "description": "Tall narrow window 60x180cm",
            "props"      : {"width": 0.60, "height": 1.80},
        },
        {
            "name"       : "Picture 240x150",
            "description": "Picture window 240x150cm",
            "props"      : {"width": 2.40, "height": 1.50},
        },
    ],
    'FENCE': [
        {
            "name"       : "Wood Picket 1.2m",
            "description": "Classic wood picket fence",
            "props"      : {
                "fence_type": "WOOD_PICKET",
                "height": 1.20,
            },
        },
        {
            "name"       : "Metal Rail 1.1m",
            "description": "Metal railing 110cm",
            "props"      : {
                "fence_type": "METAL_RAIL",
                "height": 1.10,
            },
        },
        {
            "name"       : "Privacy 1.8m",
            "description": "Privacy fence 180cm",
            "props"      : {
                "fence_type": "WOOD_PRIVACY",
                "height": 1.80,
            },
        },
    ],
    'STAIR': [
        {
            "name"       : "Standard 18/27",
            "description": "Standard stair 18cm rise / 27cm run",
            "props"      : {
                "step_rise"  : 0.18,
                "step_run"   : 0.27,
                "step_count" : 12,
            },
        },
        {
            "name"       : "Steep 20/25",
            "description": "Steep stair 20cm rise / 25cm run",
            "props"      : {
                "step_rise"  : 0.20,
                "step_run"   : 0.25,
                "step_count" : 14,
            },
        },
    ],
}


# ════════════════════════════════════════════════════════════
#  SERIALIZACIÓN
# ════════════════════════════════════════════════════════════
def _serialize_props(prop_group) -> dict:
    """
    Serializa un PropertyGroup a un diccionario JSON-compatible.
    Omite propiedades internas y colecciones.
    """
    result = {}
    for prop_name in prop_group.bl_rna.properties.keys():
        if prop_name in AF_SKIP_PROPS:
            continue
        if prop_name.startswith("_"):
            continue
        try:
            val = getattr(prop_group, prop_name)
            if isinstance(val, (bool, int, float, str)):
                result[prop_name] = val
            elif hasattr(val, '__iter__') and not isinstance(val, str):
                # Solo vectores numéricos, no colecciones
                try:
                    lst = list(val)
                    if all(isinstance(x, (int, float)) for x in lst):
                        result[prop_name] = lst
                except Exception:
                    pass
        except Exception:
            pass
    return result


def _apply_props(prop_group, data: dict):
    """
    Aplica un diccionario de propiedades a un PropertyGroup.
    Omite propiedades inexistentes o con tipos incompatibles.
    """
    for key, val in data.items():
        if key in AF_SKIP_PROPS:
            continue
        if not hasattr(prop_group, key):
            continue
        try:
            current = getattr(prop_group, key)
            if isinstance(current, bool):
                setattr(prop_group, key, bool(val))
            elif isinstance(current, int):
                setattr(prop_group, key, int(val))
            elif isinstance(current, float):
                setattr(prop_group, key, float(val))
            elif isinstance(current, str):
                setattr(prop_group, key, str(val))
            elif hasattr(current, '__len__') and isinstance(val, list):
                setattr(prop_group, key, val)
        except Exception:
            pass


def _get_presets_dir() -> str:
    """Directorio de presets del usuario."""
    user_scripts = bpy.utils.script_path_user()
    path = os.path.join(user_scripts, AF_PRESET_SUBDIR)
    os.makedirs(path, exist_ok=True)
    return path


def _save_preset_file(af_type: str, name: str, data: dict):
    """Guarda un preset en disco como JSON."""
    directory = os.path.join(_get_presets_dir(), af_type.lower())
    os.makedirs(directory, exist_ok=True)
    safe_name = "".join(
        c if c.isalnum() or c in "-_ " else "_"
        for c in name
    ).strip().replace(" ", "_")
    path = os.path.join(directory, f"{safe_name}{AF_PRESET_EXT}")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({
            "version"    : AF_PRESET_VERSION,
            "type"       : af_type,
            "name"       : name,
            "description": data.get("description", ""),
            "props"      : data.get("props", {}),
        }, f, indent=2, ensure_ascii=False)
    return path


def _load_preset_file(path: str) -> dict:
    """Carga un preset desde disco."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


# ════════════════════════════════════════════════════════════
#  REFRESH — NO llamar desde draw()
# ════════════════════════════════════════════════════════════
def _refresh_preset_list_from_settings(settings):
    """
    Puebla la lista de presets en el PropertyGroup.
    Versión sin context — segura para llamar desde timers,
    callbacks de update, o al registrar el addon.
    """
    if settings is None:
        return
    settings.items.clear()

    af_type = settings.active_type

    # Built-in presets
    for bp in BUILTIN_PRESETS.get(af_type, []):
        item             = settings.items.add()
        item.label       = bp["name"]
        item.description = bp["description"]
        item.is_builtin  = True
        item.af_type     = af_type

    # User presets desde disco
    directory = os.path.join(_get_presets_dir(), af_type.lower())
    if os.path.isdir(directory):
        for fname in sorted(os.listdir(directory)):
            if not fname.endswith(AF_PRESET_EXT):
                continue
            path = os.path.join(directory, fname)
            try:
                data             = _load_preset_file(path)
                item             = settings.items.add()
                item.label       = data.get("name", fname)
                item.description = data.get("description", "")
                item.is_builtin  = False
                item.file_path   = path
                item.af_type     = af_type
            except Exception:
                pass


def _refresh_preset_list(context, af_type: str):
    """
    Recarga la lista usando context.
    Uso: operadores, update callbacks. NUNCA desde draw().
    """
    settings = getattr(context.scene, "af_presets", None)
    _refresh_preset_list_from_settings(settings)


def _on_active_type_change(self, context):
    """Update callback al cambiar el tipo de preset."""
    _refresh_preset_list_from_settings(self)


# ════════════════════════════════════════════════════════════
#  PROPERTYGROUP — UI
# ════════════════════════════════════════════════════════════
class AF_PresetItem(PropertyGroup):
    """Un ítem de preset en la lista de la UI."""
    label       : StringProperty(name="Label",       default="")
    description : StringProperty(name="Description", default="")
    is_builtin  : BoolProperty(  name="Built-in",    default=False)
    file_path   : StringProperty(name="File Path",   default="")
    af_type     : StringProperty(name="AF Type",     default="")


class AF_PresetSettings(PropertyGroup):
    """Configuración del sistema de presets."""
    active_type : EnumProperty(
        name    = "Type",
        items   = AF_PRESET_TYPES,
        default = 'WALL',
        update  = _on_active_type_change,
    )
    active_index : IntProperty(
        name    = "Active Index",
        default = 0,
        min     = 0,
    )
    preset_name : StringProperty(
        name        = "Preset Name",
        description = "Name for the new preset",
        default     = "My Preset",
    )
    preset_description : StringProperty(
        name        = "Description",
        description = "Short description of this preset",
        default     = "",
    )
    items : CollectionProperty(
        name = "Preset Items",
        type = AF_PresetItem,
    )


# ════════════════════════════════════════════════════════════
#  UILIST
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_UL_presets(UIList):
    bl_idname = "ARCHIFORGE_UL_presets"

    def draw_item(self, context, layout, data, item, icon,
                  active_data, active_propname):
        row = layout.row(align=True)
        if item.is_builtin:
            row.label(text=item.label, icon='FAKE_USER_ON')
        else:
            row.label(text=item.label, icon='FILE_BLEND')
        if item.description:
            row.label(text=item.description)


# ════════════════════════════════════════════════════════════
#  OPERADORES
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_OT_preset_save(Operator):
    """Guarda las propiedades del objeto activo como preset."""
    bl_idname      = "archiforge.preset_save"
    bl_label       = "Save as Preset"
    bl_description = "Save active object properties as a preset"
    bl_options     = {'REGISTER'}

    def execute(self, context):
        settings = context.scene.af_presets
        af_type  = settings.active_type
        name     = settings.preset_name.strip()
        desc     = settings.preset_description.strip()

        if not name:
            self.report({'WARNING'}, "Enter a preset name")
            return {'CANCELLED'}

        obj      = context.active_object
        prop_key = AF_TYPE_TO_PROP.get(af_type)

        if obj is None or prop_key is None or not hasattr(obj, prop_key):
            self.report({'WARNING'}, f"Active object is not a {af_type}")
            return {'CANCELLED'}

        prop_group = getattr(obj, prop_key)
        props_data = _serialize_props(prop_group)

        path = _save_preset_file(af_type, name, {
            "description": desc,
            "props"      : props_data,
        })
        _refresh_preset_list(context, af_type)
        self.report({'INFO'}, f"Preset saved: {os.path.basename(path)}")
        return {'FINISHED'}


class ARCHIFORGE_OT_preset_load(Operator):
    """Carga el preset seleccionado en el objeto activo."""
    bl_idname      = "archiforge.preset_load"
    bl_label       = "Load Preset"
    bl_description = "Apply selected preset to the active object"
    bl_options     = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.af_presets
        af_type  = settings.active_type
        idx      = settings.active_index
        items    = settings.items

        if idx < 0 or idx >= len(items):
            self.report({'WARNING'}, "No preset selected")
            return {'CANCELLED'}

        item     = items[idx]
        obj      = context.active_object
        prop_key = AF_TYPE_TO_PROP.get(af_type)

        if obj is None or prop_key is None or not hasattr(obj, prop_key):
            self.report({'WARNING'}, f"Active object is not a {af_type}")
            return {'CANCELLED'}

        prop_group = getattr(obj, prop_key)

        if item.is_builtin:
            bp_list = BUILTIN_PRESETS.get(af_type, [])
            builtin_count = sum(
                1 for i in items[:idx] if i.is_builtin
            )
            if builtin_count < len(bp_list):
                bp = bp_list[builtin_count]
                _apply_props(prop_group, bp["props"])
            else:
                self.report({'ERROR'}, "Built-in preset not found")
                return {'CANCELLED'}
        else:
            if not os.path.isfile(item.file_path):
                self.report({'ERROR'}, f"File not found: {item.file_path}")
                return {'CANCELLED'}
            try:
                data = _load_preset_file(item.file_path)
                _apply_props(prop_group, data.get("props", {}))
            except Exception as e:
                self.report({'ERROR'}, f"Could not load preset: {e}")
                return {'CANCELLED'}

        self.report({'INFO'}, f"Preset applied: {item.label}")
        return {'FINISHED'}


class ARCHIFORGE_OT_preset_delete(Operator):
    """Elimina el preset de usuario seleccionado."""
    bl_idname      = "archiforge.preset_delete"
    bl_label       = "Delete Preset"
    bl_description = "Delete selected user preset from disk"
    bl_options     = {'REGISTER'}

    def execute(self, context):
        settings = context.scene.af_presets
        idx      = settings.active_index
        items    = settings.items

        if idx < 0 or idx >= len(items):
            self.report({'WARNING'}, "No preset selected")
            return {'CANCELLED'}

        item = items[idx]
        if item.is_builtin:
            self.report({'WARNING'}, "Cannot delete built-in presets")
            return {'CANCELLED'}

        if os.path.isfile(item.file_path):
            os.remove(item.file_path)
            self.report({'INFO'}, f"Deleted: {item.label}")
        else:
            self.report({'WARNING'}, "File not found")

        _refresh_preset_list(context, settings.active_type)
        return {'FINISHED'}


class ARCHIFORGE_OT_preset_refresh(Operator):
    """Recarga la lista de presets desde disco."""
    bl_idname      = "archiforge.preset_refresh"
    bl_label       = "Refresh Presets"
    bl_description = "Reload preset list from disk"
    bl_options     = {'REGISTER'}

    def execute(self, context):
        settings = context.scene.af_presets
        _refresh_preset_list(context, settings.active_type)
        self.report({'INFO'}, "Presets reloaded")
        return {'FINISHED'}


class ARCHIFORGE_OT_preset_export(Operator):
    """Exporta el preset seleccionado a una ruta externa."""
    bl_idname      = "archiforge.preset_export"
    bl_label       = "Export Preset"
    bl_description = "Export selected preset to a file"
    bl_options     = {'REGISTER'}

    filepath : StringProperty(subtype='FILE_PATH')

    def invoke(self, context, event):
        settings = context.scene.af_presets
        idx = settings.active_index
        if 0 <= idx < len(settings.items):
            item = settings.items[idx]
            self.filepath = item.label.replace(" ", "_") + AF_PRESET_EXT
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        settings = context.scene.af_presets
        idx = settings.active_index
        if idx < 0 or idx >= len(settings.items):
            return {'CANCELLED'}
        item = settings.items[idx]
        if not item.file_path or not os.path.isfile(item.file_path):
            self.report({'ERROR'}, "No file to export")
            return {'CANCELLED'}
        import shutil
        shutil.copy2(item.file_path, self.filepath)
        self.report({'INFO'}, f"Exported to: {self.filepath}")
        return {'FINISHED'}


class ARCHIFORGE_OT_preset_import(Operator):
    """Importa un preset desde una ruta externa."""
    bl_idname      = "archiforge.preset_import"
    bl_label       = "Import Preset"
    bl_description = "Import a preset from file"
    bl_options     = {'REGISTER'}

    filepath : StringProperty(subtype='FILE_PATH')

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        if not os.path.isfile(self.filepath):
            self.report({'ERROR'}, "File not found")
            return {'CANCELLED'}
        try:
            data    = _load_preset_file(self.filepath)
            af_type = data.get("type", "WALL")
            name    = data.get("name", "Imported")
            _save_preset_file(af_type, name, data)
            _refresh_preset_list(
                context, context.scene.af_presets.active_type
            )
            self.report({'INFO'}, f"Imported: {name}")
        except Exception as e:
            self.report({'ERROR'}, f"Import failed: {e}")
            return {'CANCELLED'}
        return {'FINISHED'}


# ════════════════════════════════════════════════════════════
#  PANEL
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_PT_presets(Panel):
    bl_label       = "Presets"
    bl_idname      = "ARCHIFORGE_PT_presets"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "ArchiForge"
    bl_context     = "objectmode"
    bl_order       = 15
    bl_options     = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def draw_header(self, context):
        self.layout.label(text="", icon='ASSET_MANAGER')

    def draw(self, context):
        layout   = self.layout
        layout.use_property_split   = False
        layout.use_property_decorate = False
        settings = getattr(context.scene, "af_presets", None)
        if settings is None:
            layout.label(text="Presets not available", icon='ERROR')
            return

        # ── Selector de tipo ──────────────────────────────────
        # (El update callback refresca la lista automáticamente)
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Object Type", icon='OBJECT_DATA')
        col.prop(settings, "active_type", text="")

        # ── Lista de presets ──────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        row = col.row()
        row.label(
            text=f"Presets ({len(settings.items)})",
            icon='ASSET_MANAGER'
        )
        row.operator(
            "archiforge.preset_refresh",
            text="", icon='FILE_REFRESH'
        )
        col.template_list(
            "ARCHIFORGE_UL_presets", "",
            settings, "items",
            settings, "active_index",
            rows=5,
        )

        # ── Cargar / Eliminar ─────────────────────────────────
        row = col.row(align=True)
        row.operator(
            "archiforge.preset_load",
            text="Apply",
            icon='CHECKMARK'
        )
        row.operator(
            "archiforge.preset_delete",
            text="",
            icon='TRASH'
        )

        # ── Guardar nuevo preset ──────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Save Current Object", icon='ADD')
        col.prop(settings, "preset_name",        text="Name")
        col.prop(settings, "preset_description", text="Desc")
        col.operator(
            "archiforge.preset_save",
            text="Save as Preset",
            icon='EXPORT'
        )

        # ── Import / Export ───────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="File Operations", icon='FILE')
        row = col.row(align=True)
        row.operator(
            "archiforge.preset_export",
            text="Export",
            icon='EXPORT'
        )
        row.operator(
            "archiforge.preset_import",
            text="Import",
            icon='IMPORT'
        )


# ════════════════════════════════════════════════════════════
#  REGISTRO
# ════════════════════════════════════════════════════════════
classes = [
    AF_PresetItem,
    AF_PresetSettings,
    ARCHIFORGE_UL_presets,
    ARCHIFORGE_OT_preset_save,
    ARCHIFORGE_OT_preset_load,
    ARCHIFORGE_OT_preset_delete,
    ARCHIFORGE_OT_preset_refresh,
    ARCHIFORGE_OT_preset_export,
    ARCHIFORGE_OT_preset_import,
    ARCHIFORGE_PT_presets,
]


def _initial_load_presets():
    """
    Carga inicial de presets en todas las escenas.
    Se ejecuta una vez tras registrar, vía timer.
    """
    for scene in bpy.data.scenes:
        settings = getattr(scene, "af_presets", None)
        if settings:
            try:
                _refresh_preset_list_from_settings(settings)
            except Exception as e:
                print(f"[ArchiForge] ⚠️  Preset initial load: {e}")
    return None   # No repetir


def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except Exception as e:
            print(f"[ArchiForge] ⚠️  af_preset '{cls.__name__}': {e}")

    bpy.types.Scene.af_presets = PointerProperty(
        type        = AF_PresetSettings,
        name        = "AF Presets",
        description = "ArchiForge preset system settings",
    )

    # Carga inicial diferida (evita problemas de contexto al registrar)
    try:
        bpy.app.timers.register(_initial_load_presets, first_interval=0.2)
    except Exception as e:
        print(f"[ArchiForge] ⚠️  Preset timer: {e}")

    print("[ArchiForge] ✅ af_preset — registered")


def unregister():
    # Cancelar timer si está pendiente
    try:
        if bpy.app.timers.is_registered(_initial_load_presets):
            bpy.app.timers.unregister(_initial_load_presets)
    except Exception:
        pass

    if hasattr(bpy.types.Scene, "af_presets"):
        del bpy.types.Scene.af_presets

    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"[ArchiForge] ⚠️  af_preset '{cls.__name__}': {e}")

    print("[ArchiForge] 🔴 af_preset — unregistered")