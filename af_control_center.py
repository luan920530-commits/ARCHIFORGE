# -*- coding: utf-8 -*-
"""
════════════════════════════════════════════════════════════
  ARCHIFORGE — Control Center (ventana flotante) v1.0.0
════════════════════════════════════════════════════════════
  Diálogo flotante lanzador de TODOS los módulos:
  muros, losas, techos, puertas, ventanas, escaleras,
  estructura, baño, cocina, muebles, decoración,
  eléctrico, cantidades y herramientas.

  Acceso: panel ArchiForge > Tools > Control Center,
  Shift+A > ArchiForge > Control Center, o F3 > Control Center.

  Compatible Blender 3.3 LTS. Todos los botones verifican que
  el operador exista antes de dibujarse (no rompe el diálogo
  si falta un módulo).
════════════════════════════════════════════════════════════
"""

import bpy
from bpy.types import Operator
from bpy.props import EnumProperty


# ════════════════════════════════════════════════════════════
#  HELPERS (autocontenidos — no dependen de __init__)
# ════════════════════════════════════════════════════════════
def _op_exists(idname):
    """True si el operador está registrado."""
    try:
        mod_name, op_name = idname.split(".", 1)
        sub = getattr(bpy.ops, mod_name, None)
        return sub is not None and hasattr(sub, op_name)
    except Exception:
        return False


def _mod_const(modname, attr):
    """Lee una constante AF_*_TYPES de otro módulo del addon."""
    try:
        import importlib
        pkg = __package__ or ""
        if pkg:
            mod = importlib.import_module(f".{modname}", pkg)
        else:
            mod = importlib.import_module(modname)
        return getattr(mod, attr, None)
    except Exception:
        return None


def _available_ids(modname, attr, fallback):
    """IDs de enum disponibles (tolerante a versiones viejas)."""
    items = _mod_const(modname, attr)
    if not items:
        return set(fallback)
    try:
        return {it[0] for it in items}
    except Exception:
        return set(fallback)


def _icons():
    """Íconos custom del addon (si __init__ los expone)."""
    try:
        import importlib
        pkg = __package__ or ""
        if not pkg:
            return {}
        init = importlib.import_module(pkg)
        fn = getattr(init, "get_icons", None)
        return fn() if fn else {}
    except Exception:
        return {}


def _icon_kw(icons, name, fallback='MESH_CUBE'):
    if name in icons:
        try:
            return {'icon_value': icons[name].icon_id}
        except Exception:
            pass
    return {'icon': fallback}


# ════════════════════════════════════════════════════════════
#  OPERADOR — Diálogo flotante
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_OT_control_center(Operator):
    """Floating launcher for all ArchiForge modules"""
    bl_idname = "archiforge.control_center"
    bl_label = "ArchiForge Control Center"
    bl_options = {'REGISTER'}

    tab: EnumProperty(
        name="Section",
        items=[
            ('STRUCT',  "Structure",  "Walls, slabs, roofs, structure",
             'MESH_CUBE', 0),
            ('OPEN',    "Openings",   "Doors, windows, stairs",
             'MESH_PLANE', 1),
            ('INTER',   "Interior",   "Bathroom, kitchen, furniture, decor",
             'LIGHT', 2),
            ('TOOLS',   "Electro & Tools", "Electrical, quantities, tools",
             'TOOL_SETTINGS', 3),
        ],
        default='STRUCT',
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(
            self, width=660)

    def execute(self, context):
        return {'FINISHED'}

    # ── Disponibilidad (se calcula 1 vez por draw) ──
    def _avail(self):
        a = {}
        a['bath'] = _available_ids(
            "af_bathroom", "AF_BATH_TYPES",
            {'TOILET', 'PEDESTAL_SINK', 'VANITY', 'SHOWER',
             'BATHTUB'})
        a['elec'] = _available_ids(
            "af_electrical", "AF_ELECTRICAL_TYPES",
            {'OUTLET', 'SWITCH', 'BULB', 'CEILING_LIGHT',
             'PENDANT', 'SCONCE'})
        a['furn'] = _available_ids(
            "af_furniture", "AF_FURN_TYPES",
            {'DINING_CHAIR', 'SOFA', 'BED', 'DINING_TABLE'})
        a['kit'] = _available_ids(
            "af_kitchen", "AF_KIT_TYPES",
            {'FRIDGE', 'STOVE', 'SINK_CABINET'})
        a['decor'] = _available_ids(
            "af_decor", "AF_DECOR_TYPES",
            {'PLANTER', 'TV', 'RUG'})
        a['open'] = _available_ids(
            "af_openings", "AF_OPEN_TYPES",
            {'DOOR_SINGLE', 'WIN_SLIDING'})
        a['stair'] = _available_ids(
            "af_stair", "AF_STAIR_TYPES",
            {'STRAIGHT', 'RAMP'})
        a['struct'] = _available_ids(
            "af_structure", "AF_STRUCT_TYPES",
            {'COLUMN', 'GRID'})
        a['roof'] = _available_ids(
            "af_roof", "AF_ROOF_TYPES",
            {'GABLE', 'HIP', 'SHED'})
        return a

    def draw(self, context):
        layout = self.layout
        icons = _icons()
        av = self._avail()

        # ── Encabezado + pestañas ──
        row = layout.row(align=True)
        row.label(text="ArchiForge Control Center",
                   **_icon_kw(icons, "archiforge", 'HOME'))
        layout.prop(self, "tab", expand=True)

        if self.tab == 'STRUCT':
            self._draw_struct(layout, icons, av)
        elif self.tab == 'OPEN':
            self._draw_open(layout, icons, av)
        elif self.tab == 'INTER':
            self._draw_inter(layout, icons, av)
        else:
            self._draw_tools(layout, icons, av)

    # ═══════════════════════════════════════════════════════
    #  TAB: ESTRUCTURA
    # ═══════════════════════════════════════════════════════
    def _draw_struct(self, layout, icons, av):
        # — Muros —
        box = layout.box()
        box.label(text="Walls", **_icon_kw(icons, "wall", 'SNAP_FACE'))
        row = box.row(align=True)
        if _op_exists("archiforge.wall"):
            row.operator(
                "archiforge.wall", text="Wall",
                **_icon_kw(icons, "wall", 'SNAP_FACE'))
        if _op_exists("archiforge.wall_draw"):
            row.operator("archiforge.wall_draw", text="Draw",
                         **_icon_kw(icons, "wall_draw", 'GREASEPENCIL'))
        if _op_exists("archiforge.wall_from_curve"):
            row.operator("archiforge.wall_from_curve", text="",
                         icon='CURVE_DATA')

        # — Losas —
        box = layout.box()
        box.label(text="Slabs", **_icon_kw(icons, "slab", 'MESH_CUBE'))
        row = box.row(align=True)
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
                **_icon_kw(icons, "slab", 'MESH_CUBE')
            ).ceiling = False
            row.operator(
                "archiforge.slab_from_wall", text="Ceiling",
                **_icon_kw(icons, "slab", 'MESH_CUBE')
            ).ceiling = True

        # — Techos —
        box = layout.box()
        box.label(text="Roofs", **_icon_kw(icons, "roof", 'HOME'))
        row = box.row(align=True)
        if _op_exists("archiforge.roof_preset_menu"):
            row.operator(
                "archiforge.roof_preset_menu", text="Roof…",
                **_icon_kw(icons, "roof", 'MESH_CUBE')
            ).preset_operator = "archiforge.roof"
        if _op_exists("archiforge.roof_add"):
            for tid, txt in (('GABLE', "Gable"),
                             ('HIP', "Hip"),
                             ('SHED', "Shed")):
                if tid in av['roof']:
                    row.operator(
                        "archiforge.roof_add", text=txt,
                        icon='ADD').roof_type = tid
        if _op_exists("archiforge.roof_place"):
            row.operator("archiforge.roof_place", text="Place",
                         icon='CURSOR')

        # — Estructura+ (columnas, vigas,…) —
        if _op_exists("archiforge.structure"):
            box = layout.box()
            box.label(text="Structure+", **_icon_kw(icons, "structure", 'MESH_CUBE'))
            grid = [('FOOTING', "Footing"), ('COLUMN', "Column"),
                    ('BEAM', "Beam"), ('RIBBED_SLAB', "Ribbed"),
                    ('GRID', "Grid"), ('LEVELS', "Levels")]
            for i in range(0, len(grid), 3):
                row = box.row(align=True)
                for tid, txt in grid[i:i + 3]:
                    if tid in av['struct']:
                        row.operator(
                            "archiforge.structure", text=txt,
                            **_icon_kw(icons, "structure", 'MESH_CUBE')).item_type = tid

        # — Extras estructura —
        box = layout.box()
        box.label(text="Extras", **_icon_kw(icons, "truss", 'PLUS'))
        row = box.row(align=True)
        if _op_exists("archiforge.truss"):
            row.operator(
                "archiforge.truss", text="Truss",
                **_icon_kw(icons, "truss", 'PLUS'))
        if _op_exists("archiforge.fence_preset_menu"):
            row.operator(
                "archiforge.fence_preset_menu", text="Fence",
                **_icon_kw(icons, "fence", 'PLUS')
            ).preset_operator = "archiforge.fence"
        if _op_exists("archiforge.fence_from_curve"):
            row.operator("archiforge.fence_from_curve", text="",
                         icon='CURVE_DATA')
        row = box.row(align=True)
        if _op_exists("archiforge.floor_preset_menu"):
            row.operator(
                "archiforge.floor_preset_menu",
                text="Floor Pattern",
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

    # ═══════════════════════════════════════════════════════
    #  TAB: ABERTURAS + CIRCULACIÓN
    # ═══════════════════════════════════════════════════════
    def _draw_open(self, layout, icons, av):
        # — Puertas —
        box = layout.box()
        box.label(text="Doors", **_icon_kw(icons, "door", 'MESH_PLANE'))
        row = box.row(align=True)
        if _op_exists("archiforge.door_preset_menu"):
            row.operator(
                "archiforge.door_preset_menu", text="Door…",
                **_icon_kw(icons, "door", 'MESH_PLANE')
            ).preset_operator = "archiforge.door"
            row.operator(
                "archiforge.door_preset_menu", text="Draw",
                icon='GREASEPENCIL'
            ).preset_operator = "archiforge.door_draw"
        if _op_exists("archiforge.door_place"):
            row.operator("archiforge.door_place", text="Place",
                         icon='CURSOR')

        # — Ventanas —
        box = layout.box()
        box.label(text="Windows", **_icon_kw(icons, "window", 'MESH_PLANE'))
        row = box.row(align=True)
        if _op_exists("archiforge.window_preset_menu"):
            row.operator(
                "archiforge.window_preset_menu", text="Window…",
                **_icon_kw(icons, "window", 'MESH_PLANE')
            ).preset_operator = "archiforge.window"
            row.operator(
                "archiforge.window_preset_menu", text="Draw",
                icon='GREASEPENCIL'
            ).preset_operator = "archiforge.window_draw"
        if _op_exists("archiforge.window_place"):
            row.operator("archiforge.window_place", text="Place",
                         icon='CURSOR')

        # — Puertas/ventanas paramétricas (nuevas) —
        if _op_exists("archiforge.opening"):
            box = layout.box()
            box.label(text="Doors & Windows+", **_icon_kw(icons, "opening", 'MESH_CUBE'))
            grid = [('DOOR_SINGLE', "Door 1H"),
                    ('DOOR_DOUBLE', "Door 2H"),
                    ('DOOR_SLIDING', "Door Slid."),
                    ('WIN_SLIDING', "Win Slid."),
                    ('WIN_CASEMENT', "Win Cas."),
                    ('WIN_FIXED', "Win Fixed")]
            for i in range(0, len(grid), 3):
                row = box.row(align=True)
                for tid, txt in grid[i:i + 3]:
                    if tid in av['open']:
                        row.operator(
                            "archiforge.opening", text=txt,
                            **_icon_kw(icons, "opening", 'MESH_CUBE')).item_type = tid

        # — Escaleras —
        box = layout.box()
        box.label(text="Stairs", **_icon_kw(icons, "stair", 'EXPORT'))
        row = box.row(align=True)
        if _op_exists("archiforge.stair_preset_menu"):
            row.operator(
                "archiforge.stair_preset_menu", text="Stairs…",
                **_icon_kw(icons, "stair", 'EXPORT')
            ).preset_operator = "archiforge.stair"
        if _op_exists("archiforge.stair"):
            for tid, txt in (('STRAIGHT', "Straight"),
                             ('L_SHAPED', "L-Shape"),
                             ('SPIRAL', "Spiral"),
                             ('RAMP', "Ramp 8%")):
                if tid in av['stair']:
                    row.operator(
                        "archiforge.stair", text=txt,
                        **_icon_kw(icons, "stair", 'ADD')).item_type = tid

    # ═══════════════════════════════════════════════════════
    #  TAB: INTERIORES
    # ═══════════════════════════════════════════════════════
    def _grid(self, box, op, avail, items, icon='MESH_CUBE',
              per_row=3, custom=False, icons=None, icon_name=None):
        """Rejilla genérica de botones item_type."""
        shown = [(t, x) for t, x in items if t in avail]
        if custom:
            shown.append((None, "Custom…"))
        icon_kwargs = (
            _icon_kw(icons or {}, icon_name, icon)
            if icon_name else {'icon': icon}
        )
        for i in range(0, len(shown), per_row):
            row = box.row(align=True)
            for tid, txt in shown[i:i + per_row]:
                kwargs = {'icon': 'ADD'} if tid is None else icon_kwargs
                op_call = row.operator(op, text=txt, **kwargs)
                if tid is not None:
                    op_call.item_type = tid

    def _draw_inter(self, layout, icons, av):
        if _op_exists("archiforge.bathroom"):
            box = layout.box()
            box.label(text="Bathroom", **_icon_kw(icons, "bathroom", 'SPHERE'))
            self._grid(box, "archiforge.bathroom", av['bath'], [
                ('TOILET', "Toilet"), ('BIDET', "Bidet"),
                ('PEDESTAL_SINK', "Pedestal"),
                ('VANITY', "Vanity"),
                ('WALLHUNG_BASIN', "W. Basin"),
                ('SHOWER', "Shower"), ('BATHTUB', "Bathtub"),
                ('MIRROR', "Mirror"),
                ('TOWEL_RAIL', "Towel Rail")],
                icon='SPHERE', custom=True, icons=icons,
                icon_name='bathroom')

        if _op_exists("archiforge.kitchen"):
            box = layout.box()
            box.label(text="Kitchen", **_icon_kw(icons, "kitchen", 'MESH_CUBE'))
            self._grid(box, "archiforge.kitchen", av['kit'], [
                ('FRIDGE', "Fridge"), ('STOVE', "Stove"),
                ('RANGE_HOOD', "Hood"),
                ('SINK_CABINET', "Sink"),
                ('DISHWASHER', "Dishwash."),
                ('MICROWAVE', "Microwave"),
                ('UTENSILS', "Utensils")], custom=True, icons=icons,
                icon_name='kitchen')

        if _op_exists("archiforge.furniture"):
            box = layout.box()
            box.label(text="Furniture", **_icon_kw(icons, "furniture", 'MESH_CUBE'))
            self._grid(box, "archiforge.furniture", av['furn'], [
                ('DINING_CHAIR', "D.Chair"),
                ('OFFICE_CHAIR', "O.Chair"),
                ('ARMCHAIR', "Armchair"), ('SOFA', "Sofa"),
                ('COFFEE_TABLE', "C.Table"),
                ('DINING_TABLE', "D.Table"),
                ('BED', "Bed (CO)"),
                ('NIGHTSTAND', "Nochero"),
                ('DRESSER', "Chifonier"), ('SHELF', "Shelf")],
                icons=icons, icon_name='furniture')

        if _op_exists("archiforge.decor"):
            box = layout.box()
            box.label(text="Decor", **_icon_kw(icons, "decor", 'LIGHT'))
            self._grid(box, "archiforge.decor", av['decor'], [
                ('PLANTER', "Planter"),
                ('FLOOR_LAMP', "F.Lamp"),
                ('TABLE_LAMP', "T.Lamp"),
                ('VASE_SET', "Vases"),
                ('WALL_ART', "Wall Art"), ('CLOCK', "Clock"),
                ('BOOKS', "Books"), ('TV', "TV"), ('RUG', "Rug")],
                icon='LIGHT', custom=True, icons=icons, icon_name='decor')

        if _op_exists("archiforge.room_asset"):
            box = layout.box()
            box.label(text="Room Asset Library", icon='ASSET_MANAGER')
            box.operator("archiforge.room_asset", text="Browse 100 objects / sets",
                         icon='MESH_CUBE')

    # ═══════════════════════════════════════════════════════
    #  TAB: ELÉCTRICO + HERRAMIENTAS
    # ═══════════════════════════════════════════════════════
    def _draw_tools(self, layout, icons, av):
        if _op_exists("archiforge.electrical"):
            box = layout.box()
            box.label(text="Electrical", **_icon_kw(icons, "electrical", 'PLUGIN'))
            self._grid(box, "archiforge.electrical", av['elec'], [
                ('OUTLET', "Outlet"), ('SWITCH', "Switch"),
                ('DATA', "Data"), ('BULB', "Bulb"),
                ('PENDANT', "Pendant"),
                ('CEILING_LIGHT', "Ceiling"),
                ('DOWNLIGHT', "Downlight"),
                ('SCONCE', "Sconce"),
                ('PANEL_BOARD', "Panel")],
                icon='PLUGIN', custom=True, icons=icons,
                icon_name='electrical')
            if _op_exists("archiforge.electrical_light"):
                row = box.row(align=True)
                row.operator("archiforge.electrical_light",
                             text="Real Blender Light",
                             icon='LIGHT')

        box = layout.box()
        box.label(text="Quantities", **_icon_kw(icons, "quantities", 'SPREADSHEET'))
        row = box.row(align=True)
        if _op_exists("archiforge.quantities_export"):
            row.operator("archiforge.quantities_export",
                         text="Export CSV (Excel)",
                         **_icon_kw(icons, "quantities", 'EXPORT'))

        box = layout.box()
        box.label(text="Tools", **_icon_kw(icons, "control_center", 'TOOL_SETTINGS'))
        row = box.row(align=True)
        if _op_exists("archiforge.auto_boolean"):
            row.operator(
                "archiforge.auto_boolean", text="Auto Boolean",
                **_icon_kw(icons, "boolean", 'MOD_BOOLEAN')).mode = 'HYBRID'
        row = box.row(align=True)
        if _op_exists("archiforge.wall_from_slab"):
            row.operator(
                "archiforge.wall_from_slab", text="Wall → Slab",
                **_icon_kw(icons, "wall", 'LINKED'))
        if _op_exists("archiforge.floor_preset_menu"):
            row.operator(
                "archiforge.floor_preset_menu",
                text="Wall → Floor",
                **_icon_kw(icons, "floor", 'LINKED')
            ).preset_operator = "archiforge.floor_from_wall"


# ════════════════════════════════════════════════════════════
#  REGISTRO
# ════════════════════════════════════════════════════════════
classes = (
    ARCHIFORGE_OT_control_center,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
