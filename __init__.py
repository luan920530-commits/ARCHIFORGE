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
    "version"     : (1, 14, 0),
    "blender"     : (3, 3, 0),
    "location"    : "View3D > Sidebar > ArchiForge | Shift+A > Mesh > ArchiForge",
    "warning"     : "",
    "doc_url"     : "https://github.com/luan920530-commits/ARCHIFORGE#readme",
    "tracker_url" : "https://github.com/luan920530-commits/ARCHIFORGE/issues",
    "support"     : "COMMUNITY",
    "category"    : "Add Mesh",
}

# Versión capturada al importar: cuando el addon se instala como *extensión*
# (Blender 4.2+, blender_manifest.toml) Blender elimina ``bl_info`` del módulo
# antes de llamar a ``register()``, así que nunca debe leerse en tiempo de
# ejecución. Debe coincidir con ``version`` del manifiesto (lo exige un test).
ADDON_VERSION = tuple(bl_info["version"])
ADDON_VERSION_STR = ".".join(str(v) for v in ADDON_VERSION)

__all__ = [
    "bl_info",
    "ADDON_VERSION",
    "ADDON_VERSION_STR",
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

try:
    from .af_i18n import tr_report as _tr
except ImportError:  # pragma: no cover - fuera del paquete
    def _tr(text):
        return text

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


def _i18n_module():
    """Módulo af_i18n si cargó correctamente (import tolerante)."""
    mod = globals().get("af_i18n")
    return mod if mod is not None and hasattr(mod, "apply_language") else None


def _units_module():
    mod = globals().get("af_units")
    return mod if mod is not None and hasattr(mod, "apply_to_scenes") else None


def _apply_unit_system(system):
    """Escribe el sistema de unidades en todas las escenas abiertas."""
    mod = _units_module()
    if mod is None:
        return 0
    try:
        return mod.apply_to_scenes(bpy.data.scenes, system)
    except Exception as e:  # noqa: BLE001 - bpy.data restringido
        af_log(f"No se pudo aplicar el sistema de unidades: {e}", level=2)
        return 0


def _on_unit_system_update(self, context):
    """Sincroniza las unidades de la escena con la preferencia del addon."""
    _apply_unit_system(self.unit_system)


def _on_procedural_materials_update(self, context):
    """Regenera los materiales AF del archivo en el modo elegido."""
    mod = globals().get("af_material")
    if mod is None or not hasattr(mod, "refresh_existing_af_materials"):
        return
    try:
        count = mod.refresh_existing_af_materials()
        af_log(f"Materiales AF regenerados: {count}", level=3)
    except Exception as e:  # noqa: BLE001
        af_log(f"No se pudieron regenerar los materiales: {e}", level=2)


def _on_language_update(self, context):
    """Registra el catálogo del idioma elegido y redibuja la interfaz."""
    mod = _i18n_module()
    if mod is None:
        af_log("af_i18n no disponible; el idioma no se puede aplicar",
               level=2)
        return
    mod.apply_language(self.language, __name__)


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
        "af_i18n_es",
        "af_i18n",
        "af_icons",
        "af_units",
        "af_material_procedural",
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
        # Pure helper, reloaded before the Blender-facing exporter.
        "af_quantities_io",
        "af_quantities",
        "af_structure",
        "af_annotation_geometry",
        "af_annotation",
        "af_sets",
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
        "af_i18n_es",
        "af_i18n",
        "af_icons",
        "af_units",
        "af_material_procedural",
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
        # Pure helper, reloaded before the Blender-facing exporter.
        "af_quantities_io",
        "af_quantities",
        "af_structure",
        "af_annotation_geometry",
        "af_annotation",
        "af_sets",
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
    Panel, Menu, Operator,
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


def _item_icon(item_type, default):
    """Nombre del ícono propio de un ``item_type`` (ver af_icons.ITEM_ICONS)."""
    table = getattr(globals().get("af_icons"), "ITEM_ICONS", None)
    if table:
        return table.get(item_type, default)
    return default


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
        description=("Language used by ArchiForge only; Blender keeps its "
                     "own language"),
        items=[('EN', "English", "Show ArchiForge in English"),
               ('ES', "Español", "Mostrar ArchiForge en español")],
        default='EN',
        update=_on_language_update,
    )
    # Casillas de traducción de Blender que el addon activó (para
    # restaurarlas al desactivarlo).
    i18n_forced_use_translate_interface : BoolProperty(
        default=False, options={'HIDDEN'})
    i18n_forced_use_translate_tooltips : BoolProperty(
        default=False, options={'HIDDEN'})

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
    procedural_materials : BoolProperty(
        name        = "Procedural Materials",
        description = ("Build node-based textures (brick and block bond, "
                       "ceramic, wood grain, concrete, marble, clay, "
                       "plaster, fabric) for the ArchiForge materials "
                       "instead of flat colors; visible in Material "
                       "Preview and Rendered shading"),
        default     = True,
        update      = _on_procedural_materials_update,
    )
    auto_material : BoolProperty(
        name        = "Auto Material",
        description = "Assign base materials automatically on object creation",
        default     = True,
    )
    unit_system : EnumProperty(
        name  = "Unit System",
        description = ("Units shown by ArchiForge and used in the quantities "
                       "CSV; applied to the unit settings of the open scenes"),
        items = [
            ('METRIC',   "Metric (m/cm)",  "Use meters and centimeters"),
            ('IMPERIAL', "Imperial (ft/in)", "Use feet and inches"),
        ],
        default = 'METRIC',
        update = _on_unit_system_update,
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
        ver = ADDON_VERSION_STR

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
        box.label(text="Interface", **_icon_kw(icons, "preferences", 'WINDOW'))
        box.prop(self, "language", **_icon_kw(icons, "language", 'WORLD'))
        self._draw_language_hints(box)
        box.prop(self, "create_submenu")
        box.prop(self, "unit_system",
                 **_icon_kw(icons, "units", 'DRIVER_DISTANCE'))
        self._draw_unit_hints(box)

        col.separator()
        box = col.box()
        box.label(text="Behavior", **_icon_kw(icons, "snap", 'MODIFIER'))
        box.prop(self, "auto_boolean")
        box.prop(self, "auto_material")
        box.prop(self, "procedural_materials")

        col.separator()
        box = col.box()
        box.label(text="Material Library",
                  **_icon_kw(icons, "material_library", 'MATERIAL'))
        box.prop(self, "matlib_path", text="")

    def _draw_language_hints(self, box):
        """Avisa si Blender tiene apagadas las casillas que permiten
        traducir la interfaz del addon y las ofrece para activarlas."""
        mod = _i18n_module()
        if mod is None:
            box.label(text="Language module unavailable", icon='ERROR')
            return
        if mod.blender_flags_enabled():
            return
        col = box.column(align=True)
        col.label(text="Blender translation is off; enable it to apply the "
                       "addon language", icon='INFO')
        try:
            view = bpy.context.preferences.view
        except Exception:  # noqa: BLE001
            return
        row = col.row(align=True)
        row.prop(view, "use_translate_interface", text="Translate Interface")
        row.prop(view, "use_translate_tooltips", text="Translate Tooltips")

    def _draw_unit_hints(self, box):
        """Avisa cuando la escena activa no usa el sistema elegido (p. ej.
        tras abrir otro archivo) y ofrece aplicarlo."""
        mod = _units_module()
        if mod is None:
            return
        try:
            scene = bpy.context.scene
        except Exception:  # noqa: BLE001
            return
        if scene is None or mod.scene_system(scene) == self.unit_system:
            return
        row = box.row(align=True)
        row.label(text="The active scene uses another unit system",
                  icon='INFO')
        row.operator("archiforge.apply_unit_system", text="Apply to Scenes",
                     **_icon_kw(get_icons(), "units", 'SCENE_DATA'))

    def _draw_manipulators(self, layout):
        col = layout.column(align=True)
        icons = get_icons()

        box = col.box()
        box.label(text="Style", **_icon_kw(icons, "manipulator", 'GREASEPENCIL'))
        box.prop(self, "max_style_draw_tool")
        box.prop(self, "show_gizmos")

        col.separator()
        box = col.box()
        box.label(text="Sizes", **_icon_kw(icons, "quick_edit", 'FULLSCREEN_ENTER'))
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
class ARCHIFORGE_OT_apply_unit_system(Operator):
    """Escribe la preferencia Unit System en las escenas del archivo."""
    bl_idname = "archiforge.apply_unit_system"
    bl_label = "Apply Unit System to Scenes"
    bl_description = ("Set the unit settings of every open scene to the "
                      "ArchiForge unit system (metric or imperial)")
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            system = context.preferences.addons[__name__].preferences.unit_system
        except Exception:  # noqa: BLE001
            system = 'METRIC'
        count = _apply_unit_system(system)
        if count:
            self.report({'INFO'}, _tr("Unit system applied to {} scene(s)")
                                  .format(count))
            return {'FINISHED'}
        self.report({'WARNING'}, _tr("Unit system could not be applied"))
        return {'CANCELLED'}


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
            "af_stair", "AF_STAIR_TYPES",
            {'STRAIGHT', 'RAMP'})
        has_open = _op_exists("archiforge.opening")
        has_stair = _op_exists("archiforge.stair")
        has_quant = _op_exists("archiforge.quantities_export")
        struct_avail = _available_ids(
            "af_structure", "AF_STRUCT_TYPES",
            {'COLUMN', 'GRID'})
        has_struct = _op_exists("archiforge.structure")

        # Cada ítem usa su ícono propio (af_icons.ITEM_ICONS); si falta el
        # PNG cae al ícono del módulo y, en último término, al de Blender.
        def _item_btn(row, op, text, tid, group_icon, fallback):
            row.operator(
                op, text=text,
                **_icon_kw(icons, _item_icon(tid, group_icon), fallback)
            ).item_type = tid

        def bath_btn(row, text, tid, icon='SPHERE'):
            if has_bath and tid in bath_avail:
                _item_btn(row, "archiforge.bathroom", text, tid,
                          "bathroom", icon)

        def elec_btn(row, text, tid, icon='PLUGIN'):
            if has_elec and tid in elec_avail:
                _item_btn(row, "archiforge.electrical", text, tid,
                          "electrical", icon)

        def furn_btn(row, text, tid, icon='MESH_CUBE'):
            if has_furn and tid in furn_avail:
                _item_btn(row, "archiforge.furniture", text, tid,
                          "furniture", icon)

        def kit_btn(row, text, tid, icon='MESH_CUBE'):
            if has_kit and tid in kit_avail:
                _item_btn(row, "archiforge.kitchen", text, tid,
                          "kitchen", icon)

        def dec_btn(row, text, tid, icon='MESH_CUBE'):
            if has_decor and tid in decor_avail:
                _item_btn(row, "archiforge.decor", text, tid, "decor", icon)

        def open_btn(row, text, tid, icon='MESH_CUBE'):
            if has_open and tid in open_avail:
                _item_btn(row, "archiforge.opening", text, tid,
                          "opening", icon)

        def stair_btn(row, text, tid, icon='MESH_CUBE'):
            if has_stair and tid in stair_avail:
                _item_btn(row, "archiforge.stair", text, tid, "stair", icon)

        def struct_btn(row, text, tid, icon='MESH_CUBE'):
            if has_struct and tid in struct_avail:
                _item_btn(row, "archiforge.structure", text, tid,
                          "structure", icon)

        # ── SECCIÓN: Herramientas globales ───────────────────
        box = layout.box()
        row = box.row(align=True)
        row.label(text="Tools", **_icon_kw(icons, "tools", 'TOOL_SETTINGS'))
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
                         **_icon_kw(icons, "curve", 'CURVE_DATA'))

        # — Losa / Techo —
        row = col.row(align=True)
        if _op_exists("archiforge.slab_from_curve"):
            row.operator(
                "archiforge.slab_from_curve", text="Slab",
                **_icon_kw(icons, "slab", 'MESH_CUBE'))
        if _op_exists("archiforge.slab_draw"):
            row.operator(
                "archiforge.slab_draw", text="Draw",
                **_icon_kw(icons, "draw", 'GREASEPENCIL'))
        if _op_exists("archiforge.slab_from_wall"):
            row.operator(
                "archiforge.slab_from_wall", text="Floor",
                **_icon_kw(icons, "slab", 'MESH_CUBE')).ceiling = False
            row.operator(
                "archiforge.slab_from_wall", text="Ceiling",
                **_icon_kw(icons, "ceiling", 'MESH_CUBE')).ceiling = True

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
                **_icon_kw(icons, "draw", 'GREASEPENCIL')
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
                **_icon_kw(icons, "draw", 'GREASEPENCIL')
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
                      **_icon_kw(icons, "room_assets", 'ASSET_MANAGER'))
            box.operator("archiforge.room_asset", text="Browse by room",
                         **_icon_kw(icons, "room_assets", 'MESH_CUBE'))
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

        # ── SECCIÓN: Anotaciones (v1.12) ─────────────────────
        if _op_exists("archiforge.dimension_selected"):
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Annotations",
                      **_icon_kw(icons, "annotation", 'DRIVER_DISTANCE'))
            row = col.row(align=True)
            row.operator("archiforge.dimension_selected", text="Dimension",
                         **_icon_kw(icons, "dimension", 'ARROW_LEFTRIGHT'))
            row.operator("archiforge.dimension_draw", text="Draw",
                         **_icon_kw(icons, "dimension_draw", 'GREASEPENCIL'))
            row = col.row(align=True)
            row.operator("archiforge.grid_axes", text="Axes",
                         **_icon_kw(icons, "grid_axes", 'GRID'))
            row.operator("archiforge.north_arrow", text="North",
                         **_icon_kw(icons, "north_arrow", 'ORIENTATION_VIEW'))

            layout.separator(factor=0.3)

        # ── SECCIÓN: Conjuntos (v1.12) ───────────────────────
        if _op_exists("archiforge.set_bathroom"):
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Sets", **_icon_kw(icons, "sets", 'HOME'))
            col.operator("archiforge.set_bathroom",
                         text="Complete Bathroom (CO)",
                         **_icon_kw(icons, "set_bathroom", 'SPHERE'))
            col.operator("archiforge.set_apartment", text="Demo Apartment",
                         **_icon_kw(icons, "set_apartment", 'HOME'))

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
                         **_icon_kw(icons, "curve", 'CURVE_DATA'))

        row = col.row(align=True)
        if _op_exists("archiforge.floor_preset_menu"):
            row.operator(
                "archiforge.floor_preset_menu", text="Floor Pattern",
                **_icon_kw(icons, "floor", 'PLUS')
            ).preset_operator = "archiforge.floor"
            row.operator(
                "archiforge.floor_preset_menu", text="",
                **_icon_kw(icons, "curve", 'CURVE_DATA')
            ).preset_operator = "archiforge.floor_from_curve"
        if _op_exists("archiforge.floor_draw"):
            row.operator(
                "archiforge.floor_draw", text="Draw",
                **_icon_kw(icons, "draw", 'GREASEPENCIL'))

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
                        **_icon_kw(icons, "room_assets", 'ASSET_MANAGER'))
    if _op_exists("archiforge.opening"):
        layout.operator("archiforge.opening", text="Door/Window",
                        **_icon_kw(icons, "opening", 'MESH_CUBE'))
    if _op_exists("archiforge.stair"):
        layout.operator("archiforge.stair", text="Stair/Ramp",
                        **_icon_kw(icons, "stair", 'MESH_CUBE'))
    if _op_exists("archiforge.structure"):
        layout.operator("archiforge.structure", text="Structure",
                        **_icon_kw(icons, "structure", 'MESH_CUBE'))

    # ── Anotaciones y conjuntos (v1.12) ──────────────────────
    if _op_exists("archiforge.dimension_selected"):
        layout.separator()
        layout.operator("archiforge.dimension_selected",
                        text="Dimension Selected",
                        **_icon_kw(icons, "dimension", 'ARROW_LEFTRIGHT'))
        layout.operator("archiforge.grid_axes", text="Grid Axes",
                        **_icon_kw(icons, "grid_axes", 'GRID'))
        layout.operator("archiforge.north_arrow", text="North Arrow",
                        **_icon_kw(icons, "north_arrow", 'ORIENTATION_VIEW'))
    if _op_exists("archiforge.set_bathroom"):
        layout.separator()
        layout.operator("archiforge.set_bathroom",
                        text="Complete Bathroom (CO)",
                        **_icon_kw(icons, "set_bathroom", 'SPHERE'))
        layout.operator("archiforge.set_apartment", text="Demo Apartment",
                        **_icon_kw(icons, "set_apartment", 'HOME'))


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
    af_quantities,
    af_structure,
    af_annotation,
    af_sets,
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
    ARCHIFORGE_OT_apply_unit_system,
    ARCHIFORGE_PT_create,
    ARCHIFORGE_MT_create,
]


# ════════════════════════════════════════════════════════════
#  REGISTER / UNREGISTER
# ════════════════════════════════════════════════════════════
def register():
    global AF_LOG_LEVEL
    ver = ADDON_VERSION_STR

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

    # ── Idioma del addon (independiente del de Blender) ─────
    i18n = _i18n_module()
    if i18n is not None:
        try:
            i18n.apply_language(i18n.current_language(__name__), __name__)
        except Exception as e:  # noqa: BLE001
            af_log(f"No se pudo aplicar el idioma del addon: {e}", level=2)

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
    # ── Liberar el catálogo de idioma ────────────────────────
    i18n = _i18n_module()
    if i18n is not None:
        try:
            i18n.release(__name__)
        except Exception as e:  # noqa: BLE001
            af_log(f"Error liberando traducciones: {e}", level=2)

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
