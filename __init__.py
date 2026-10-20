# -*- coding: utf-8 -*-

# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   ░█████╗░██████╗░░█████╗░██╗░░██╗██╗███████╗░█████╗░██████╗░██╗║
# ║   ██╔══██╗██╔══██╗██╔══██╗██║░░██║██║██╔════╝██╔══██╗██╔══██╗██║║
# ║   ███████║██████╔╝██║░░╚═╝███████║██║█████╗░░██║░░██║██████╔╝██║║
# ║   ██╔══██║██╔══██╗██║░░██╗██╔══██║██║██╔══╝░░██║░░██║██╔══██╗██║║
# ║   ██║░░██║██║░░██║╚█████╔╝██║░░██║██║██║░░░░░╚█████╔╝██║░░██║╚█╝║
# ║   ╚═╝░░╚═╝╚═╝░░╚═╝░╚════╝░╚═╝░░╚═╝╚═╝╚═╝░░░░░░╚════╝░╚═╝░░╚═╝░░║
# ║                                                                  ║
# ║              ARCHIFORGE — for Blender 3.3 LTS                    ║
# ║         Modern Parametric Architectural Objects                  ║
# ║                     GPL v3 License                               ║
# ╚══════════════════════════════════════════════════════════════════╝

# <pep8 compliant>
#
# v1.1.0 — Revisado:
#   * Panel y menú Shift+A ahora exponen Bathroom y Electrical
#     (antes se registraban pero no aparecían en la UI).
#   * Hot-reload tolerante a fallos por módulo (try/except).
#   * af_objects_base incluido en el orden de registro (se omite
#     limpiamente si no define register/unregister).
#   * Manejo de íconos sin icon_value=0 inválidos.
#   * log_level de preferencias sincronizado en vivo.
#   * register/unregister blindados (sin duplicados ni traceback).

bl_info = {
    "name"        : "ArchiForge",
    "description" : "Modern parametric architectural objects for Blender 3.3+ "
                     "(walls, doors, windows, stairs, slabs, roofs, bathroom, electrical...)",
    "author"      : "ArchiForge Devs",
    "license"     : "GPL",
    "version"     : (1, 10, 0),
    "blender"     : (3, 3, 0),
    "location"    : "View3D > Sidebar > ArchiForge | Shift+A > Mesh > ArchiForge",
    "warning"     : "",
    "doc_url"     : "https://github.com/luan920530-commits/ARCHIFORGE#readme",
    "tracker_url" : "https://github.com/luan920530-commits/ARCHIFORGE/issues",
    "support"     : "COMMUNITY",
    "category"    : "Add Mesh",
}

__all__ = [
    "bl_info",
    "register",
    "unregister",
    "get_icons",
    "af_log",
]


# ════════════════════════════════════════════════════════════
#  SISTEMA DE LOGGING INTERNO
# ════════════════════════════════════════════════════════════
import os
import sys

# Nivel de log: 0=silent, 1=errors, 2=warnings, 3=info, 4=debug
AF_LOG_LEVEL = 3


def af_log(msg, level=3):
    """Logger central de ArchiForge."""
    if level <= AF_LOG_LEVEL:
        prefix = {1: "❌ ERROR", 2: "⚠️  WARN", 3: "ℹ️  INFO", 4: "🔍 DEBUG"}
        print(f"[ArchiForge] {prefix.get(level, 'LOG')} » {msg}")


def _on_log_level_update(self, context):
    """Sincroniza AF_LOG_LEVEL en vivo al cambiar la preferencia."""
    global AF_LOG_LEVEL
    try:
        AF_LOG_LEVEL = int(self.log_level)
    except (TypeError, ValueError):
        pass


# ════════════════════════════════════════════════════════════
#  HOT-RELOAD — tolerante a fallos, orden de dependencias
#  Orden CRÍTICO: core primero, luego objetos, luego UI
# ════════════════════════════════════════════════════════════
if "bpy" in locals():
    import importlib as _imp

    # Unregister the old classes and callbacks before importlib.reload replaces
    # their Python class objects. Otherwise Blender retains the old RNA classes
    # while the new classes fail to register with the same bl_idname.
    _previous_unregister = locals().get("unregister")
    if callable(_previous_unregister):
        try:
            _previous_unregister()
            af_log("Addon anterior desregistrado antes del hot-reload", level=3)
        except Exception as _err:  # noqa: BLE001 — best-effort cleanup
            af_log(f"No se pudo limpiar todo antes del hot-reload: {_err}",
                   level=2)

    _RELOAD_ORDER = (
        # 1. Core (base del sistema)
        "af_material",
        "af_snap",
        "af_manipulator",
        "af_reference_point",
        "af_preset",
        # 2. Lógica compartida
        "af_autoboolean",
        "af_objects_base",
        "af_room_assets_catalog",
        "af_room_assets",
        "af_wall_path",
        "af_floor_geometry",
        "af_window_geometry",
        "af_construction_presets",
        "af_outline_draw",
        # 3. Objetos paramétricos
        "af_wall",
        "af_door",
        "af_window",
        "af_stair",
        "af_slab",
        "af_roof",
        "af_fence",
        "af_floor",
        "af_truss",
        "af_electrical",
        "af_bathroom",
        "af_furniture",
        "af_kitchen",
        "af_decor",
        "af_openings",
        "af_stairs",
        # Pure helper, reloaded before the Blender-facing exporter.
        "af_quantities_io",
        "af_quantities",
        "af_structure",
        "af_control_center",
        # 4. UI (último, depende de todo lo anterior)
        "af_rendering",
        "af_panel",
        "af_menu",
    )

    for _mod_name in _RELOAD_ORDER:
        _mod = locals().get(_mod_name)
        if _mod is None:
            # Nuevo en esta versión o falló antes: intentar importar.
            try:
                _mod = _imp.import_module(
                    ".{}".format(_mod_name), __name__)
                globals()[_mod_name] = _mod
            except Exception as _err:  # noqa: BLE001
                print("[ArchiForge] import '{}' falló: {}".format(
                    _mod_name, _err))
                globals()[_mod_name] = None
                _mod = None
                continue
        try:
            _imp.reload(_mod)
        except Exception as _err:  # noqa: BLE001 — reload nunca debe abortar
            print(f"[ArchiForge] ⚠️  reload '{_mod_name}' falló: {_err}")

    af_log("🔄 Hot-reload completado", level=3)

    del _imp, _RELOAD_ORDER, _mod_name, _mod, _previous_unregister

else:
    # Imports TOLERANTES (v1.5.1): un módulo ausente o con error
    # se reporta y se omite — ya no tumba todo el addon.
    import importlib as _imp_first
    _FIRST_ORDER = (
        # 1. Core (base del sistema)
        "af_material",
        "af_snap",
        "af_manipulator",
        "af_reference_point",
        "af_preset",
        # 2. Lógica compartida
        "af_autoboolean",
        "af_objects_base",
        "af_room_assets_catalog",
        "af_room_assets",
        "af_wall_path",
        "af_floor_geometry",
        "af_window_geometry",
        "af_construction_presets",
        "af_outline_draw",
        # 3. Objetos paramétricos
        "af_wall",
        "af_door",
        "af_window",
        "af_stair",
        "af_slab",
        "af_roof",
        "af_fence",
        "af_floor",
        "af_truss",
        "af_electrical",
        "af_bathroom",
        "af_furniture",
        "af_kitchen",
        "af_decor",
        "af_openings",
        "af_stairs",
        # Pure helper, reloaded before the Blender-facing exporter.
        "af_quantities_io",
        "af_quantities",
        "af_structure",
        "af_control_center",
        # 4. UI (último, depende de todo lo anterior)
        "af_rendering",
        "af_panel",
        "af_menu",
    )
    for _mod_name in _FIRST_ORDER:
        try:
            globals()[_mod_name] = _imp_first.import_module(
                ".{}".format(_mod_name), __name__)
        except Exception as _err:  # noqa: BLE001
            print("[ArchiForge] import '{}' falló: {}".format(
                _mod_name, _err))
            globals()[_mod_name] = None

    del _imp_first, _FIRST_ORDER, _mod_name

    af_log("📦 Módulos cargados OK", level=3)


# ════════════════════════════════════════════════════════════
#  IMPORTS DE BLENDER
# ════════════════════════════════════════════════════════════
import bpy
from bpy.utils import previews
from bpy.types import (
    Panel, Menu,
    AddonPreferences,
)
from bpy.props import (
    EnumProperty,
    StringProperty,
    BoolProperty,
    IntProperty,
    FloatProperty,
    FloatVectorProperty,
)


# ════════════════════════════════════════════════════════════
#  GESTOR DE ÍCONOS — con manejo de errores
# ════════════════════════════════════════════════════════════
_icons_collection = {}   # Privado, acceso via get_icons()


def get_icons():
    """Acceso seguro a la colección de íconos."""
    return _icons_collection.get("main", {})


def _load_icons():
    """
    Carga todos los íconos desde /icons con manejo
    de errores por ícono individual.
    """
    global _icons_collection

    # Evita fugas si register() se llama dos veces seguidas.
    if "main" in _icons_collection:
        _unload_icons()

    icons_dir = os.path.join(os.path.dirname(__file__), "icons")

    if not os.path.isdir(icons_dir):
        af_log("No hay íconos personalizados; se usarán los iconos de Blender",
               level=3)
        _icons_collection["main"] = previews.new()
        return

    icon_preview = previews.new()
    loaded = 0
    failed = 0

    for icon_file in sorted(os.listdir(icons_dir)):
        name, ext = os.path.splitext(icon_file)
        if ext.lower() not in {".png", ".jpg", ".jpeg"}:
            continue
        try:
            icon_preview.load(
                name,
                os.path.join(icons_dir, icon_file),
                'IMAGE'
            )
            loaded += 1
        except Exception as e:
            af_log(f"No se pudo cargar ícono '{icon_file}': {e}", level=2)
            failed += 1

    _icons_collection["main"] = icon_preview
    af_log(f"Íconos: {loaded} cargados, {failed} fallidos", level=3)


def _unload_icons():
    """Libera memoria de íconos correctamente."""
    global _icons_collection
    for icon_set in tuple(_icons_collection.values()):
        try:
            previews.remove(icon_set)
        except Exception as e:
            af_log(f"Error liberando íconos: {e}", level=2)
    _icons_collection.clear()
    af_log("Íconos liberados de memoria", level=4)


def _icon_kw(icons, name, fallback='MESH_CUBE'):
    """kwargs para operator/menu: icon_value si existe, sino icon builtin.

    Evita pasar icon_value=0 (inválido) cuando falta el png.
    """
    if name in icons:
        try:
            return {'icon_value': icons[name].icon_id}
        except Exception:
            pass
    return {'icon': fallback}


def _op_exists(idname):
    """True si el operador está registrado (evita romper el draw)."""
    try:
        mod_name, op_name = idname.split(".", 1)
        sub = getattr(bpy.ops, mod_name, None)
        return sub is not None and hasattr(sub, op_name)
    except Exception:
        return False


def _available_ids(modname, attr, fallback):
    """IDs de enum disponibles en otro módulo (tolerante a versiones viejas)."""
    mod = globals().get(modname)
    items = getattr(mod, attr, None) if mod is not None else None
    if not items:
        return set(fallback)
    try:
        return {it[0] for it in items}
    except Exception:
        return set(fallback)


# ════════════════════════════════════════════════════════════
#  PREFERENCIAS DEL ADDON — Ampliadas y organizadas
# ════════════════════════════════════════════════════════════
class ArchiForge_Pref(AddonPreferences):
    bl_idname = __name__

    language : EnumProperty(
        name="Addon language",
        description="Language used by ArchiForge only",
        items=[('EN', "English", "Show ArchiForge in English"),
               ('ES', "Español", "Mostrar ArchiForge en español")],
        default='EN',
    )

    # ── Pestaña activa en preferencias ──────────────────────
    pref_tab : EnumProperty(
        name  = "Tab",
        items = [
            ('GENERAL',       "General",       "General settings",        'PREFERENCES',   0),
            ('MANIPULATORS',  "Manipulators",  "Handles and gizmos",      'PIVOT_CURSOR',  1),
            ('COLORS',        "Colors",        "UI color scheme",         'COLOR',         2),
            ('ADVANCED',      "Advanced",      "Debug and advanced opts", 'MODIFIER',      3),
        ],
        default = 'GENERAL',
    )

    # ────────────────────────────────────────────────────────
    #  TAB: GENERAL
    # ────────────────────────────────────────────────────────
    create_submenu : BoolProperty(
        name        = "Use Sub-menu in Shift+A",
        description = "Put ArchiForge objects inside a sub-menu (Shift+A)",
        default     = True,
    )
    auto_boolean : BoolProperty(
        name        = "Auto Boolean",
        description = "Automatically cut openings in walls for doors/windows",
        default     = True,
    )
    auto_material : BoolProperty(
        name        = "Auto Material",
        description = "Assign base materials automatically on object creation",
        default     = True,
    )
    unit_system : EnumProperty(
        name  = "Unit System",
        items = [
            ('METRIC',   "Metric (m/cm)",  "Use meters and centimeters"),
            ('IMPERIAL', "Imperial (ft/in)", "Use feet and inches"),
        ],
        default = 'METRIC',
    )
    matlib_path : StringProperty(
        name        = "Material Library Folder",
        description = "Absolute path to your material library folder",
        default     = "",
        subtype     = "DIR_PATH",
    )

    # ────────────────────────────────────────────────────────
    #  TAB: MANIPULATORS
    # ────────────────────────────────────────────────────────
    max_style_draw_tool : BoolProperty(
        name        = "3ds Max Style Wall Drawing",
        description = "Reverse click/release cycle when drawing walls",
        default     = True,
    )
    show_gizmos : BoolProperty(
        name        = "Show On-Screen Gizmos",
        description = "Show interactive gizmos on selected objects",
        default     = True,
    )
    arrow_size : FloatProperty(
        name        = "Arrow Size",
        description = "Manipulator arrow size (Blender units)",
        default     = 0.05,
        min         = 0.001,
        max         = 1.0,
        step        = 1,
    )
    handle_size : IntProperty(
        name        = "Handle Sensitive Area",
        description = "Manipulator handle hit area (pixels)",
        default     = 10,
        min         = 2,
        max         = 50,
    )
    constant_handle_size : BoolProperty(
        name        = "Constant Handle Size on Screen",
        description = "Keep handle size constant regardless of zoom",
        default     = False,
    )
    text_size : IntProperty(
        name        = "Manipulator Font Size",
        description = "Font size for on-screen dimension labels (pixels)",
        default     = 14,
        min         = 6,
        max         = 48,
    )

    # ────────────────────────────────────────────────────────
    #  TAB: COLORS
    # ────────────────────────────────────────────────────────
    handle_colour_normal : FloatVectorProperty(
        name    = "Handle — Normal",
        subtype = 'COLOR_GAMMA',
        default = (1.0, 1.0, 1.0, 1.0),
        size=4, min=0, max=1,
    )
    handle_colour_hover : FloatVectorProperty(
        name    = "Handle — Hover",
        subtype = 'COLOR_GAMMA',
        default = (1.0, 1.0, 0.0, 1.0),
        size=4, min=0, max=1,
    )
    handle_colour_active : FloatVectorProperty(
        name    = "Handle — Active",
        subtype = 'COLOR_GAMMA',
        default = (1.0, 0.0, 0.0, 1.0),
        size=4, min=0, max=1,
    )
    handle_colour_selected : FloatVectorProperty(
        name    = "Handle — Selected",
        subtype = 'COLOR_GAMMA',
        default = (0.0, 0.0, 0.7, 1.0),
        size=4, min=0, max=1,
    )
    handle_colour_inactive : FloatVectorProperty(
        name    = "Handle — Inactive",
        subtype = 'COLOR_GAMMA',
        default = (0.3, 0.3, 0.3, 1.0),
        size=4, min=0, max=1,
    )
    feedback_title_area : FloatVectorProperty(
        name    = "Background — Title",
        subtype = 'COLOR_GAMMA',
        default = (0.0, 0.4, 0.6, 0.5),
        size=4, min=0, max=1,
    )
    feedback_shortcut_area : FloatVectorProperty(
        name    = "Background — Shortcuts",
        subtype = 'COLOR_GAMMA',
        default = (0.0, 0.4, 0.6, 0.2),
        size=4, min=0, max=1,
    )
    feedback_colour_main : FloatVectorProperty(
        name    = "Font — Main Title",
        subtype = 'COLOR_GAMMA',
        default = (0.95, 0.95, 0.95, 1.0),
        size=4, min=0, max=1,
    )
    feedback_colour_key : FloatVectorProperty(
        name    = "Font — Shortcut Key",
        subtype = 'COLOR_GAMMA',
        default = (0.67, 0.67, 0.67, 1.0),
        size=4, min=0, max=1,
    )
    feedback_colour_shortcut : FloatVectorProperty(
        name    = "Font — Shortcut Hint",
        subtype = 'COLOR_GAMMA',
        default = (0.51, 0.51, 0.51, 1.0),
        size=4, min=0, max=1,
    )

    # ── Tamaños de fuente de feedback ───────────────────────
    feedback_size_main : IntProperty(
        name="Font Size — Main",  default=16, min=6, max=48)
    feedback_size_title : IntProperty(
        name="Font Size — Title", default=14, min=6, max=48)
    feedback_size_shortcut : IntProperty(
        name="Font Size — Shortcuts", default=11, min=6, max=48)

    # ────────────────────────────────────────────────────────
    #  TAB: ADVANCED / DEBUG
    # ────────────────────────────────────────────────────────
    log_level : EnumProperty(
        name  = "Log Level",
        items = [
            ('0', "Silent",   "No output"),
            ('1', "Errors",   "Only errors"),
            ('2', "Warnings", "Errors + warnings"),
            ('3', "Info",     "Normal output (recommended)"),
            ('4', "Debug",    "Full verbose output"),
        ],
        default = '3',
        update  = _on_log_level_update,
    )
    enable_experimental : BoolProperty(
        name        = "Enable Experimental Features",
        description = "Enable features still in development (may be unstable)",
        default     = False,
    )

    # ────────────────────────────────────────────────────────
    #  DRAW — Panel de preferencias con tabs
    # ────────────────────────────────────────────────────────
    def draw(self, context):
        layout = self.layout
        ver = ".".join(str(v) for v in bl_info.get("version", (1, 0, 0)))

        # ── Header con logo ─────────────────────────────────
        box = layout.box()
        row = box.row(align=True)
        row.label(
            text=f"ArchiForge v{ver}",
            **_icon_kw(get_icons(), "archiforge", 'HOME'),
        )
        row.label(text="for Blender 3.3 LTS")

        # ── Tabs de navegación ───────────────────────────────
        row = layout.row(align=True)
        row.prop_tabs_enum(self, "pref_tab")
        layout.separator(factor=0.5)

        # ── Contenido según tab activo ───────────────────────
        if self.pref_tab == 'GENERAL':
            self._draw_general(layout)
        elif self.pref_tab == 'MANIPULATORS':
            self._draw_manipulators(layout)
        elif self.pref_tab == 'COLORS':
            self._draw_colors(layout)
        elif self.pref_tab == 'ADVANCED':
            self._draw_advanced(layout)

    def _draw_general(self, layout):
        col = layout.column(align=True)
        icons = get_icons()

        box = col.box()
        box.label(text="Interface", **_icon_kw(icons, "control_center", 'WINDOW'))
        box.prop(self, "language")
        box.prop(self, "create_submenu")
        box.prop(self, "unit_system")

        col.separator()
        box = col.box()
        box.label(text="Behavior", **_icon_kw(icons, "snap", 'MODIFIER'))
        box.prop(self, "auto_boolean")
        box.prop(self, "auto_material")

        col.separator()
        box = col.box()
        box.label(text="Material Library", **_icon_kw(icons, "material", 'MATERIAL'))
        box.prop(self, "matlib_path", text="")

    def _draw_manipulators(self, layout):
        col = layout.column(align=True)
        icons = get_icons()

        box = col.box()
        box.label(text="Style", **_icon_kw(icons, "wall_draw", 'GREASEPENCIL'))
        box.prop(self, "max_style_draw_tool")
        box.prop(self, "show_gizmos")

        col.separator()
        box = col.box()
        box.label(text="Sizes", **_icon_kw(icons, "structure", 'FULLSCREEN_ENTER'))
        split = box.split(factor=0.5)
        c = split.column(align=True)
        c.prop(self, "arrow_size")
        c.prop(self, "handle_size")
        c.prop(self, "text_size")
        c = split.column(align=True)
        c.prop(self, "constant_handle_size")
        c.separator()
        c.prop(self, "feedback_size_main")
        c.prop(self, "feedback_size_title")
        c.prop(self, "feedback_size_shortcut")

    def _draw_colors(self, layout):
        col = layout.column(align=True)
        split = col.split(factor=0.5)

        # ── Columna izquierda: Handles ───────────────────────
        c_left = split.column(align=True)
        c_left.label(text="Handle Colors", icon='PIVOT_CURSOR')
        for prop in [
            "handle_colour_normal",
            "handle_colour_hover",
            "handle_colour_active",
            "handle_colour_selected",
            "handle_colour_inactive",
        ]:
            row = c_left.row(align=True)
            row.prop(self, prop)

        # ── Columna derecha: Feedback ────────────────────────
        c_right = split.column(align=True)
        c_right.label(text="Feedback Colors", icon='FONT_DATA')
        for prop in [
            "feedback_title_area",
            "feedback_shortcut_area",
            "feedback_colour_main",
            "feedback_colour_key",
            "feedback_colour_shortcut",
        ]:
            row = c_right.row(align=True)
            row.prop(self, prop)

    def _draw_advanced(self, layout):
        col = layout.column(align=True)

        box = col.box()
        box.label(text="Debug", icon='CONSOLE')
        box.prop(self, "log_level")

        col.separator()
        box = col.box()
        row = box.row()
        row.label(text="⚠️  Experimental Features", icon='ERROR')
        box.prop(self, "enable_experimental")

        col.separator()
        box = col.box()
        box.label(text="System Info", icon='INFO')
        box.label(text=f"Blender: {bpy.app.version_string}")
        box.label(text=f"Python: {sys.version.split()[0]}")
        box.label(text=f"Platform: {sys.platform}")


# ════════════════════════════════════════════════════════════
#  PANEL PRINCIPAL — "ArchiForge" en Sidebar
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_PT_create(Panel):
    bl_label       = "ArchiForge"
    bl_idname      = "ARCHIFORGE_PT_create"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "ArchiForge"      # ← Tab propio, más limpio
    bl_context     = "objectmode"
    bl_options     = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def draw_header(self, context):
        icons = get_icons()
        if "archiforge" in icons:
            self.layout.label(
                text="",
                icon_value=icons["archiforge"].icon_id
            )
        elif "archipack" in icons:
            self.layout.label(
                text="",
                icon_value=icons["archipack"].icon_id
            )
        else:
            self.layout.label(text="", icon='HOME')

    def draw(self, context):
        icons  = get_icons()
        layout = self.layout
        layout.use_property_split = False

        bath_avail = _available_ids(
            "af_bathroom", "AF_BATH_TYPES",
            {'TOILET', 'PEDESTAL_SINK', 'VANITY', 'SHOWER', 'BATHTUB'})
        elec_avail = _available_ids(
            "af_electrical", "AF_ELECTRICAL_TYPES",
            {'OUTLET', 'SWITCH', 'BULB', 'CEILING_LIGHT', 'PENDANT', 'SCONCE'})

        has_bath = _op_exists("archiforge.bathroom")
        has_elec = _op_exists("archiforge.electrical")
        furn_avail = _available_ids(
            "af_furniture", "AF_FURN_TYPES",
            {'DINING_CHAIR', 'SOFA', 'BED', 'DINING_TABLE'})
        kit_avail = _available_ids(
            "af_kitchen", "AF_KIT_TYPES",
            {'FRIDGE', 'STOVE', 'SINK_CABINET'})
        decor_avail = _available_ids(
            "af_decor", "AF_DECOR_TYPES",
            {'PLANTER', 'TV', 'RUG'})
        has_furn = _op_exists("archiforge.furniture")
        has_kit = _op_exists("archiforge.kitchen")
        has_decor = _op_exists("archiforge.decor")
        open_avail = _available_ids(
            "af_openings", "AF_OPEN_TYPES",
            {'DOOR_SINGLE', 'WIN_SLIDING'})
        stair_avail = _available_ids(
            "af_stairs", "AF_STAIR_TYPES",
            {'STRAIGHT', 'RAMP'})
        has_open = _op_exists("archiforge.opening")
        has_stair = _op_exists("archiforge.stairs")
        has_quant = _op_exists("archiforge.quantities_export")
        struct_avail = _available_ids(
            "af_structure", "AF_STRUCT_TYPES",
            {'COLUMN', 'GRID'})
        has_struct = _op_exists("archiforge.structure")

        def bath_btn(row, text, tid, icon='SPHERE'):
            if has_bath and tid in bath_avail:
                icon_kwargs = (
                    _icon_kw(icons, "bathroom", icon)
                    if icon == 'SPHERE' else {'icon': icon}
                )
                row.operator(
                    "archiforge.bathroom", text=text, **icon_kwargs
                ).item_type = tid

        def elec_btn(row, text, tid, icon='PLUGIN'):
            if has_elec and tid in elec_avail:
                icon_kwargs = (
                    _icon_kw(icons, "electrical", icon)
                    if icon == 'PLUGIN' else {'icon': icon}
                )
                row.operator(
                    "archiforge.electrical", text=text, **icon_kwargs
                ).item_type = tid

        def furn_btn(row, text, tid, icon='MESH_CUBE'):
            if has_furn and tid in furn_avail:
                row.operator(
                    "archiforge.furniture", text=text,
                    **_icon_kw(icons, "furniture", icon)
                ).item_type = tid

        def kit_btn(row, text, tid, icon='MESH_CUBE'):
            if has_kit and tid in kit_avail:
                row.operator(
                    "archiforge.kitchen", text=text,
                    **_icon_kw(icons, "kitchen", icon)
                ).item_type = tid

        def dec_btn(row, text, tid, icon='MESH_CUBE'):
            if has_decor and tid in decor_avail:
                icon_kwargs = (
                    _icon_kw(icons, "decor", icon)
                    if icon == 'MESH_CUBE' else {'icon': icon}
                )
                row.operator(
                    "archiforge.decor", text=text, **icon_kwargs
                ).item_type = tid

        def open_btn(row, text, tid, icon='MESH_CUBE'):
            if has_open and tid in open_avail:
                row.operator(
                    "archiforge.opening", text=text,
                    **_icon_kw(icons, "opening", icon)
                ).item_type = tid

        def stair_btn(row, text, tid, icon='MESH_CUBE'):
            if has_stair and tid in stair_avail:
                row.operator(
                    "archiforge.stairs", text=text,
                    **_icon_kw(icons, "stair", icon)
                ).item_type = tid

        def struct_btn(row, text, tid, icon='MESH_CUBE'):
            if has_struct and tid in struct_avail:
                row.operator(
                    "archiforge.structure", text=text,
                    **_icon_kw(icons, "structure", icon)
                ).item_type = tid

        # ── SECCIÓN: Herramientas globales ───────────────────
        box = layout.box()
        row = box.row(align=True)
        row.label(text="Tools", **_icon_kw(icons, "control_center", 'TOOL_SETTINGS'))
        row = box.row(align=True)
        if _op_exists("archiforge.auto_boolean"):
            row.operator(
                "archiforge.auto_boolean",
                text="Auto Boolean",
                **_icon_kw(icons, "boolean", 'MOD_BOOLEAN')
            ).mode = 'HYBRID'
        row = box.row(align=True)
        if _op_exists("archiforge.control_center"):
            row.operator(
                "archiforge.control_center",
                text="Control Center",
                **_icon_kw(icons, "control_center", 'HOME')
            )

        layout.separator(factor=0.3)

        # ── SECCIÓN: Estructura ──────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Structure", **_icon_kw(icons, "structure", 'MESH_CUBE'))

        # — Muros —
        row = col.row(align=True)
        row.operator(
            "archiforge.wall", text="Wall",
            **_icon_kw(icons, "wall", 'SNAP_FACE'))
        if _op_exists("archiforge.wall_draw"):
            row.operator("archiforge.wall_draw", text="Draw",
                         **_icon_kw(icons, "wall_draw", 'GREASEPENCIL'))
        if _op_exists("archiforge.wall_from_curve"):
            row.operator("archiforge.wall_from_curve", text="",
                         icon='CURVE_DATA')

        # — Losa / Techo —
        row = col.row(align=True)
        if _op_exists("archiforge.slab_from_curve"):
            row.operator(
                "archiforge.slab_from_curve", text="Slab",
                **_icon_kw(icons, "slab", 'MESH_CUBE'))
        if _op_exists("archiforge.slab_draw"):
            row.operator(
                "archiforge.slab_draw", text="Draw",
                **_icon_kw(icons, "slab", 'GREASEPENCIL'))
        if _op_exists("archiforge.slab_from_wall"):
            row.operator(
                "archiforge.slab_from_wall", text="Floor",
                **_icon_kw(icons, "slab", 'MESH_CUBE')).ceiling = False
            row.operator(
                "archiforge.slab_from_wall", text="Ceiling",
                **_icon_kw(icons, "slab", 'MESH_CUBE')).ceiling = True

        # — Techo —
        row = col.row(align=True)
        if _op_exists("archiforge.roof_preset_menu"):
            row.operator(
                "archiforge.roof_preset_menu", text="Roof",
                **_icon_kw(icons, "roof", 'MESH_CUBE')
            ).preset_operator = "archiforge.roof"

        layout.separator(factor=0.3)

        # ── SECCIÓN: Aberturas ───────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Openings", **_icon_kw(icons, "opening", 'MESH_PLANE'))

        # — Puertas —
        row = col.row(align=True)
        if _op_exists("archiforge.door_preset_menu"):
            row.operator(
                "archiforge.door_preset_menu", text="Door",
                **_icon_kw(icons, "door", 'MESH_PLANE')
            ).preset_operator = "archiforge.door"
            row.operator(
                "archiforge.door_preset_menu", text="Draw",
                icon='GREASEPENCIL'
            ).preset_operator = "archiforge.door_draw"

        # — Ventanas —
        row = col.row(align=True)
        if _op_exists("archiforge.window_preset_menu"):
            row.operator(
                "archiforge.window_preset_menu", text="Window",
                **_icon_kw(icons, "window", 'MESH_PLANE')
            ).preset_operator = "archiforge.window"
            row.operator(
                "archiforge.window_preset_menu", text="Draw",
                icon='GREASEPENCIL'
            ).preset_operator = "archiforge.window_draw"

        layout.separator(factor=0.3)

        # ── SECCIÓN: Circulación ─────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Circulation", **_icon_kw(icons, "stair", 'EXPORT'))

        row = col.row(align=True)
        if _op_exists("archiforge.stair_preset_menu"):
            row.operator(
                "archiforge.stair_preset_menu", text="Stairs",
                **_icon_kw(icons, "stair", 'EXPORT')
            ).preset_operator = "archiforge.stair"

        layout.separator(factor=0.3)

        # ── SECCIÓN: Baño (NUEVO — v1.1) ─────────────────────
        if has_bath:
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Bathroom", **_icon_kw(icons, "bathroom", 'SPHERE'))

            row = col.row(align=True)
            bath_btn(row, "Toilet",  'TOILET')
            bath_btn(row, "Bidet",   'BIDET')

            row = col.row(align=True)
            bath_btn(row, "Pedestal", 'PEDESTAL_SINK')
            bath_btn(row, "Vanity",   'VANITY')

            row = col.row(align=True)
            bath_btn(row, "W. Basin", 'WALLHUNG_BASIN')
            bath_btn(row, "Shower",   'SHOWER', icon='MOD_FLUID')

            row = col.row(align=True)
            bath_btn(row, "Bathtub", 'BATHTUB', icon='MESH_UVSPHERE')
            bath_btn(row, "Mirror",  'MIRROR',  icon='MOD_MIRROR')

            row = col.row(align=True)
            bath_btn(row, "Towel Rail", 'TOWEL_RAIL', icon='DRIVER')
            row.operator("archiforge.bathroom", text="Custom…", icon='ADD')

            layout.separator(factor=0.3)

        # ── SECCIÓN: Eléctrico (NUEVO — v1.1) ────────────────
        if has_elec:
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Electrical", **_icon_kw(icons, "electrical", 'PLUGIN'))

            row = col.row(align=True)
            elec_btn(row, "Outlet", 'OUTLET')
            elec_btn(row, "Switch", 'SWITCH')

            row = col.row(align=True)
            elec_btn(row, "Data", 'DATA', icon='NETWORK_DRIVE')
            elec_btn(row, "Bulb", 'BULB', icon='LIGHT')

            row = col.row(align=True)
            elec_btn(row, "Pendant", 'PENDANT', icon='LIGHT_HEMI')
            elec_btn(row, "Ceiling", 'CEILING_LIGHT', icon='LIGHT')

            row = col.row(align=True)
            elec_btn(row, "Downlight", 'DOWNLIGHT', icon='LIGHT_SPOT')
            elec_btn(row, "Sconce",    'SCONCE',    icon='LIGHT')

            row = col.row(align=True)
            elec_btn(row, "Panel Board", 'PANEL_BOARD', icon='PACKAGE')
            row.operator("archiforge.electrical", text="Custom…", icon='ADD')

            layout.separator(factor=0.3)

        # ── SECCIÓN: Muebles (NUEVO — v1.2) ────────────────
        if has_furn:
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Furniture", **_icon_kw(icons, "furniture", 'MESH_CUBE'))

            row = col.row(align=True)
            furn_btn(row, "D.Chair", 'DINING_CHAIR')
            furn_btn(row, "O.Chair", 'OFFICE_CHAIR')

            row = col.row(align=True)
            furn_btn(row, "Armchair", 'ARMCHAIR')
            furn_btn(row, "Sofa", 'SOFA')

            row = col.row(align=True)
            furn_btn(row, "C.Table", 'COFFEE_TABLE')
            furn_btn(row, "D.Table", 'DINING_TABLE')

            row = col.row(align=True)
            furn_btn(row, "Bed (CO)", 'BED')
            furn_btn(row, "Nochero", 'NIGHTSTAND')

            row = col.row(align=True)
            furn_btn(row, "Chifonier", 'DRESSER')
            furn_btn(row, "Shelf", 'SHELF')

            layout.separator(factor=0.3)

        # ── SECCIÓN: Cocina (NUEVO — v1.2) ───────────────────
        if has_kit:
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Kitchen", **_icon_kw(icons, "kitchen", 'MESH_CUBE'))

            row = col.row(align=True)
            kit_btn(row, "Fridge", 'FRIDGE')
            kit_btn(row, "Stove", 'STOVE')

            row = col.row(align=True)
            kit_btn(row, "Hood", 'RANGE_HOOD')
            kit_btn(row, "Sink", 'SINK_CABINET')

            row = col.row(align=True)
            kit_btn(row, "Dishwash.", 'DISHWASHER')
            kit_btn(row, "Microwave", 'MICROWAVE')

            row = col.row(align=True)
            kit_btn(row, "Utensils", 'UTENSILS')
            row.operator("archiforge.kitchen", text="Custom…",
                         icon='ADD')

            layout.separator(factor=0.3)

        # ── SECCIÓN: Decoración (NUEVO — v1.2) ───────────────
        if has_decor:
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Decor", **_icon_kw(icons, "decor", 'LIGHT'))

            row = col.row(align=True)
            dec_btn(row, "Planter", 'PLANTER')
            dec_btn(row, "F.Lamp", 'FLOOR_LAMP', icon='LIGHT')

            row = col.row(align=True)
            dec_btn(row, "T.Lamp", 'TABLE_LAMP', icon='LIGHT')
            dec_btn(row, "Vases", 'VASE_SET')

            row = col.row(align=True)
            dec_btn(row, "Wall Art", 'WALL_ART')
            dec_btn(row, "Clock", 'CLOCK')

            row = col.row(align=True)
            dec_btn(row, "Books", 'BOOKS')
            dec_btn(row, "TV", 'TV')

            row = col.row(align=True)
            dec_btn(row, "Rug", 'RUG')
            row.operator("archiforge.decor", text="Custom…",
                         icon='ADD')

            layout.separator(factor=0.3)

        if _op_exists("archiforge.room_asset"):
            box = layout.box()
            box.label(text="Room Assets · 100 objects / sets",
                      icon='ASSET_MANAGER')
            box.operator("archiforge.room_asset", text="Browse by room",
                         icon='MESH_CUBE')
            layout.separator(factor=0.3)

        # ── SECCIÓN: Aberturas (NUEVO — v1.3) ──────────────
        if has_open:
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Doors & Windows", **_icon_kw(icons, "opening", 'MESH_CUBE'))

            row = col.row(align=True)
            open_btn(row, "Door 1H", 'DOOR_SINGLE')
            open_btn(row, "Door 2H", 'DOOR_DOUBLE')

            row = col.row(align=True)
            open_btn(row, "Door Slid.", 'DOOR_SLIDING')
            open_btn(row, "Win Slid.", 'WIN_SLIDING')

            row = col.row(align=True)
            open_btn(row, "Win Cas.", 'WIN_CASEMENT')
            open_btn(row, "Win Fixed", 'WIN_FIXED')

            layout.separator(factor=0.3)

        # ── SECCIÓN: Escaleras (NUEVO — v1.3) ────────────────
        if has_stair:
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Stairs & Ramp", **_icon_kw(icons, "stair", 'MESH_CUBE'))

            row = col.row(align=True)
            stair_btn(row, "Straight", 'STRAIGHT')
            stair_btn(row, "L-Shaped", 'L_SHAPED')

            row = col.row(align=True)
            stair_btn(row, "Spiral", 'SPIRAL')
            stair_btn(row, "Ramp 8%", 'RAMP')

            layout.separator(factor=0.3)

        # ── SECCIÓN: Cantidades (NUEVO — v1.3) ──────────────
        if has_quant:
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Quantities", **_icon_kw(icons, "quantities", 'SPREADSHEET'))
            col.operator(
                "archiforge.quantities_export",
                text="Export CSV (Excel)",
                **_icon_kw(icons, "quantities", 'EXPORT'),
            )

            layout.separator(factor=0.3)

        # ── SECCIÓN: Estructura (NUEVO — v1.4) ───────────────
        if has_struct:
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Structure+", **_icon_kw(icons, "structure", 'MESH_CUBE'))

            row = col.row(align=True)
            struct_btn(row, "Footing", 'FOOTING')
            struct_btn(row, "Column", 'COLUMN')

            row = col.row(align=True)
            struct_btn(row, "Beam", 'BEAM')
            struct_btn(row, "Ribbed", 'RIBBED_SLAB')

            row = col.row(align=True)
            struct_btn(row, "Grid", 'GRID')
            struct_btn(row, "Levels", 'LEVELS')

            layout.separator(factor=0.3)

        # ── SECCIÓN: Extras ──────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Extras", **_icon_kw(icons, "truss", 'PLUS'))

        row = col.row(align=True)
        if _op_exists("archiforge.fence_preset_menu"):
            row.operator(
                "archiforge.fence_preset_menu", text="Fence",
                **_icon_kw(icons, "fence", 'PLUS')
            ).preset_operator = "archiforge.fence"
        if _op_exists("archiforge.fence_from_curve"):
            row.operator("archiforge.fence_from_curve", text="",
                         icon='CURVE_DATA')

        row = col.row(align=True)
        if _op_exists("archiforge.floor_preset_menu"):
            row.operator(
                "archiforge.floor_preset_menu", text="Floor Pattern",
                **_icon_kw(icons, "floor", 'PLUS')
            ).preset_operator = "archiforge.floor"
            row.operator(
                "archiforge.floor_preset_menu", text="",
                icon='CURVE_DATA'
            ).preset_operator = "archiforge.floor_from_curve"
        if _op_exists("archiforge.floor_draw"):
            row.operator(
                "archiforge.floor_draw", text="Draw",
                **_icon_kw(icons, "floor", 'GREASEPENCIL'))

        row = col.row(align=True)
        if _op_exists("archiforge.truss"):
            row.operator(
                "archiforge.truss", text="Truss",
                **_icon_kw(icons, "truss", 'PLUS'))

        layout.separator(factor=0.3)

        # ── SECCIÓN: Wall → otros ────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="From Wall", **_icon_kw(icons, "wall", 'LINKED'))
        row = col.row(align=True)
        if _op_exists("archiforge.wall_from_slab"):
            row.operator(
                "archiforge.wall_from_slab", text="Wall → Slab",
                **_icon_kw(icons, "wall", 'LINKED'))
        row = col.row(align=True)
        if _op_exists("archiforge.floor_preset_menu"):
            row.operator(
                "archiforge.floor_preset_menu", text="Wall → Floor",
                **_icon_kw(icons, "floor", 'LINKED')
            ).preset_operator = "archiforge.floor_from_wall"


# ════════════════════════════════════════════════════════════
#  MENÚ SHIFT+A — con fallback de íconos y nuevos módulos
# ════════════════════════════════════════════════════════════
def _draw_shift_a_menu(self, context):
    """Contenido compartido entre sub-menu y menú directo."""
    icons  = get_icons()
    layout = self.layout
    layout.operator_context = 'INVOKE_REGION_WIN'

    if _op_exists("archiforge.control_center"):
        layout.operator(
            "archiforge.control_center",
            text="Control Center",
            **_icon_kw(icons, "control_center", 'HOME'))
        layout.separator()

    if _op_exists("archiforge.wall"):
        layout.operator(
            "archiforge.wall", text="Wall",
            **_icon_kw(icons, "wall", 'MESH_CUBE'))
    if _op_exists("archiforge.wall_draw"):
        layout.operator(
            "archiforge.wall_draw", text="Draw Wall / Room",
            **_icon_kw(icons, "wall_draw", 'GREASEPENCIL'))
    if _op_exists("archiforge.slab_draw"):
        layout.operator(
            "archiforge.slab_draw", text="Draw Slab",
            **_icon_kw(icons, "slab", 'MESH_CUBE'))
    if _op_exists("archiforge.floor_draw"):
        layout.operator(
            "archiforge.floor_draw", text="Draw Floor",
            **_icon_kw(icons, "floor", 'MESH_GRID'))
    if _op_exists("archiforge.window_preset_menu"):
        layout.operator(
            "archiforge.window_preset_menu", text="Window",
            **_icon_kw(icons, "window", 'MESH_PLANE')
        ).preset_operator = "archiforge.window"
    if _op_exists("archiforge.door_preset_menu"):
        layout.operator(
            "archiforge.door_preset_menu", text="Door",
            **_icon_kw(icons, "door", 'MESH_PLANE')
        ).preset_operator = "archiforge.door"
    if _op_exists("archiforge.stair_preset_menu"):
        layout.operator(
            "archiforge.stair_preset_menu", text="Stairs",
            **_icon_kw(icons, "stair", 'EXPORT')
        ).preset_operator = "archiforge.stair"
    if _op_exists("archiforge.fence_preset_menu"):
        layout.operator(
            "archiforge.fence_preset_menu", text="Fence",
            **_icon_kw(icons, "fence", 'PLUS')
        ).preset_operator = "archiforge.fence"
    if _op_exists("archiforge.floor_preset_menu"):
        layout.operator(
            "archiforge.floor_preset_menu", text="Floor Pattern",
            **_icon_kw(icons, "floor", 'PLUS')
        ).preset_operator = "archiforge.floor"
    if _op_exists("archiforge.roof_preset_menu"):
        layout.operator(
            "archiforge.roof_preset_menu", text="Roof",
            **_icon_kw(icons, "roof", 'MESH_CUBE')
        ).preset_operator = "archiforge.roof"
    if _op_exists("archiforge.truss"):
        layout.operator(
            "archiforge.truss", text="Truss",
            **_icon_kw(icons, "truss", 'PLUS'))

    # ── Nuevos en v1.1 ──────────────────────────────────────
    if _op_exists("archiforge.bathroom") or _op_exists("archiforge.electrical"):
        layout.separator()
    if _op_exists("archiforge.bathroom"):
        layout.operator("archiforge.bathroom", text="Bathroom Fixture",
                        **_icon_kw(icons, "bathroom", 'SPHERE'))
    if _op_exists("archiforge.electrical"):
        layout.operator("archiforge.electrical", text="Electrical Item",
                        **_icon_kw(icons, "electrical", 'PLUGIN'))
    if _op_exists("archiforge.furniture"):
        layout.operator("archiforge.furniture", text="Furniture",
                        **_icon_kw(icons, "furniture", 'MESH_CUBE'))
    if _op_exists("archiforge.kitchen"):
        layout.operator("archiforge.kitchen", text="Kitchen Item",
                        **_icon_kw(icons, "kitchen", 'MESH_CUBE'))
    if _op_exists("archiforge.decor"):
        layout.operator("archiforge.decor", text="Decor Item",
                        **_icon_kw(icons, "decor", 'LIGHT'))
    if _op_exists("archiforge.room_asset"):
        layout.operator("archiforge.room_asset", text="Room Asset Library",
                        icon='ASSET_MANAGER')
    if _op_exists("archiforge.opening"):
        layout.operator("archiforge.opening", text="Door/Window",
                        **_icon_kw(icons, "opening", 'MESH_CUBE'))
    if _op_exists("archiforge.stairs"):
        layout.operator("archiforge.stairs", text="Stair/Ramp",
                        **_icon_kw(icons, "stair", 'MESH_CUBE'))
    if _op_exists("archiforge.structure"):
        layout.operator("archiforge.structure", text="Structure",
                        **_icon_kw(icons, "structure", 'MESH_CUBE'))


class ARCHIFORGE_MT_create(Menu):
    """Sub-menú de ArchiForge en Shift+A."""
    bl_label = "ArchiForge"

    def draw(self, context):
        _draw_shift_a_menu(self, context)


def menu_func(self, context):
    """Punto de entrada en VIEW3D_MT_mesh_add (Shift+A)."""
    layout = self.layout
    layout.separator()
    icons = get_icons()

    prefs = None
    try:
        prefs = context.preferences.addons.get(__name__)
    except Exception:
        prefs = None

    use_submenu = True
    if prefs is not None:
        try:
            use_submenu = bool(prefs.preferences.create_submenu)
        except Exception:
            use_submenu = True

    if use_submenu:
        layout.operator_context = 'INVOKE_REGION_WIN'
        if "archiforge" in icons:
            layout.menu(
                "ARCHIFORGE_MT_create",
                icon_value=icons["archiforge"].icon_id
            )
        elif "archipack" in icons:
            layout.menu(
                "ARCHIFORGE_MT_create",
                icon_value=icons["archipack"].icon_id
            )
        else:
            layout.menu("ARCHIFORGE_MT_create", icon='HOME')
    else:
        _draw_shift_a_menu(self, context)


# ════════════════════════════════════════════════════════════
#  LISTA DE MÓDULOS — orden correcto de registro
#  (af_objects_base se omite solo si no define register())
# ════════════════════════════════════════════════════════════
_modules = [
    af_material,
    af_snap,
    af_manipulator,
    af_reference_point,
    af_preset,
    af_autoboolean,
    af_objects_base,
    af_room_assets,
    af_wall,
    af_door,
    af_window,
    af_stair,
    af_slab,
    af_roof,
    af_fence,
    af_floor,
    af_truss,
    af_electrical,
    af_bathroom,
    af_furniture,
    af_kitchen,
    af_decor,
    af_openings,
    af_stairs,
    af_quantities,
    af_structure,
    af_control_center,
    af_rendering,
    af_panel,
    af_menu,
]

# v1.5.1: los módulos que fallaron al importar quedan como None → se omiten.
_modules = [m for m in _modules if m is not None]

# Clases propias de __init__.py
_own_classes = [
    ArchiForge_Pref,
    ARCHIFORGE_PT_create,
    ARCHIFORGE_MT_create,
]


# ════════════════════════════════════════════════════════════
#  REGISTER / UNREGISTER
# ════════════════════════════════════════════════════════════
def register():
    global AF_LOG_LEVEL
    ver = ".".join(str(v) for v in bl_info.get("version", (1, 0, 0)))

    # ── Cargar íconos primero ────────────────────────────────
    try:
        _load_icons()
    except Exception as e:
        af_log(f"Error cargando íconos: {e}", level=1)

    # ── Registrar clases propias ─────────────────────────────
    for cls in _own_classes:
        try:
            bpy.utils.register_class(cls)
        except Exception as e:
            af_log(f"Error registrando clase {cls.__name__}: {e}", level=1)

    # ── Registrar módulos en orden ───────────────────────────
    ok_count   = 0
    skip_count = 0
    fail_count = 0

    for mod in _modules:
        if not hasattr(mod, "register"):
            af_log(f"Módulo '{mod.__name__}' sin register() — omitido",
                   level=4)
            skip_count += 1
            continue
        try:
            mod.register()
            ok_count += 1
        except Exception as e:
            af_log(f"Error en módulo '{mod.__name__}': {e}", level=1)
            fail_count += 1

    # ── Registrar en menú Shift+A ────────────────────────────
    try:
        bpy.types.VIEW3D_MT_mesh_add.append(menu_func)
    except Exception as e:
        af_log(f"Error registrando menú Shift+A: {e}", level=1)

    # ── Sync nivel de log desde prefs ───────────────────────
    try:
        prefs = bpy.context.preferences.addons.get(__name__)
        if prefs is not None:
            AF_LOG_LEVEL = int(prefs.preferences.log_level)
    except Exception:
        pass

    # ── Reporte final ────────────────────────────────────────
    print("─" * 55)
    print(f"  ✅  ArchiForge v{ver} — {ok_count} módulos OK", end="")
    if skip_count:
        print(f" | ⏭️  {skip_count} omitidos", end="")
    if fail_count:
        print(f" | ⚠️  {fail_count} fallos")
    else:
        print(" — Todo OK 🎉")
    print("─" * 55)


def unregister():
    # ── Quitar del menú Shift+A ──────────────────────────────
    try:
        bpy.types.VIEW3D_MT_mesh_add.remove(menu_func)
    except Exception as e:
        af_log(f"Error quitando menú Shift+A: {e}", level=2)

    # ── Desregistrar módulos en orden INVERSO ────────────────
    for mod in reversed(_modules):
        if not hasattr(mod, "unregister"):
            continue
        try:
            mod.unregister()
        except Exception as e:
            af_log(f"Error desregistrando '{mod.__name__}': {e}", level=1)

    # ── Desregistrar clases propias en orden INVERSO ─────────
    for cls in reversed(_own_classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            af_log(f"Error desregistrando clase {cls.__name__}: {e}", level=1)

    # ── Liberar íconos de memoria ────────────────────────────
    try:
        _unload_icons()
    except Exception as e:
        af_log(f"Error liberando íconos: {e}", level=2)

    print("─" * 55)
    print("  🔴  ArchiForge — Desregistrado correctamente")
    print("─" * 55)


if __name__ == "__main__":
    register()
