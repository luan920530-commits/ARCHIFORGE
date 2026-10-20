# -*- coding: utf-8 -*-

# ╔══════════════════════════════════════════════════════════╗
# ║         ARCHIFORGE — af_menu.py                         ║
# ║         Menús Contextuales — Blender 3.3 LTS            ║
# ║         GPL v3 — ArchiForge Devs                        ║
# ╚══════════════════════════════════════════════════════════╝

# <pep8 compliant>

import bpy
from bpy.types import Menu, Operator
from bpy.props import StringProperty


# ════════════════════════════════════════════════════════════
#  MENÚ PRINCIPAL — Shift+A (referenciado desde __init__.py
#  como ARCHIFORGE_MT_create)
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_MT_menu_main(Menu):
    """Menú raíz de ArchiForge en Shift+A."""
    bl_label  = "ArchiForge"
    bl_idname = "ARCHIFORGE_MT_menu_main"

    def draw(self, context):
        layout = self.layout
        layout.operator_context = 'INVOKE_DEFAULT'

        # ── Estructura ────────────────────────────────────────
        layout.label(text="Structure", icon='MESH_CUBE')
        layout.operator("archiforge.wall",  text="Wall",  icon='SNAP_EDGE')
        layout.operator("archiforge.slab",  text="Slab",  icon='MESH_PLANE')
        layout.operator("archiforge.roof",  text="Roof",  icon='MOD_BUILD')
        layout.operator("archiforge.truss", text="Truss", icon='MESH_CUBE')

        layout.separator()

        # ── Pavimento ─────────────────────────────────────────
        layout.label(text="Floor", icon='MESH_GRID')
        layout.operator("archiforge.floor", text="Floor Pattern", icon='MESH_GRID')

        layout.separator()

        # ── Aberturas ─────────────────────────────────────────
        layout.label(text="Openings", icon='MOD_MIRROR')
        layout.operator("archiforge.door",   text="Door",   icon='MESH_CUBE')
        layout.operator("archiforge.window", text="Window", icon='MOD_LATTICE')

        layout.separator()

        # ── Circulación ───────────────────────────────────────
        layout.label(text="Circulation", icon='EXPORT')
        layout.operator("archiforge.stair", text="Stair", icon='OBJECT_DATA')

        layout.separator()

        # ── Extras ────────────────────────────────────────────
        layout.label(text="Extras", icon='PLUS')
        layout.operator("archiforge.fence", text="Fence", icon='MESH_PLANE')

        # ── Conjuntos y anotaciones (v1.12) ───────────────────
        if hasattr(bpy.types, "ARCHIFORGE_OT_set_bathroom"):
            layout.separator()
            layout.label(text="Sets", icon='HOME')
            layout.operator("archiforge.set_bathroom",
                            text="Complete Bathroom (CO)", icon='SPHERE')
            layout.operator("archiforge.set_apartment",
                            text="Demo Apartment", icon='HOME')
        if hasattr(bpy.types, "ARCHIFORGE_OT_dimension_selected"):
            layout.separator()
            layout.label(text="Annotations", icon='DRIVER_DISTANCE')
            layout.operator("archiforge.dimension_selected",
                            text="Dimension Selected", icon='ARROW_LEFTRIGHT')
            layout.operator("archiforge.grid_axes", text="Grid Axes",
                            icon='GRID')
            layout.operator("archiforge.north_arrow", text="North Arrow",
                            icon='ORIENTATION_VIEW')


# ════════════════════════════════════════════════════════════
#  MENÚ CONTEXTUAL — clic derecho en objeto AF seleccionado
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_MT_context_object(Menu):
    """Menú contextual de clic derecho para objetos AF."""
    bl_label  = "ArchiForge Object"
    bl_idname = "ARCHIFORGE_MT_context_object"

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            return False
        af_attrs = [
            "archiforge_wall", "archiforge_floor",
            "archiforge_door", "archiforge_window",
            "archiforge_stair", "archiforge_roof",
            "archiforge_fence", "archiforge_slab",
            "archiforge_truss",
        ]
        return any(hasattr(obj, a) for a in af_attrs)

    def draw(self, context):
        layout = self.layout
        obj    = context.active_object

        layout.label(text="ArchiForge", icon='HOME')
        layout.separator()

        # — Detectar tipo y ofrecer el update correcto —
        update_map = {
            "archiforge_wall"   : ("archiforge.wall_update",   "Update Wall"),
            "archiforge_floor"  : ("archiforge.floor_update",  "Update Floor"),
            "archiforge_door"   : ("archiforge.door_update",   "Update Door"),
            "archiforge_window" : ("archiforge.window_update", "Update Window"),
            "archiforge_stair"  : ("archiforge.stair_update",  "Update Stair"),
            "archiforge_roof"   : ("archiforge.roof_update",   "Update Roof"),
            "archiforge_fence"  : ("archiforge.fence_update",  "Update Fence"),
            "archiforge_slab"   : ("archiforge.slab_update",   "Update Slab"),
            "archiforge_truss"  : ("archiforge.truss_update",  "Update Truss"),
        }

        for attr, (op_id, label) in update_map.items():
            if hasattr(obj, attr):
                layout.operator(op_id, text=label, icon='FILE_REFRESH')
                break

        layout.separator()

        # — Acciones generales —
        layout.operator(
            "archiforge.select_all",
            text="Select All AF Objects",
            icon='RESTRICT_SELECT_OFF'
        )
        layout.operator(
            "archiforge.rebuild_all",
            text="Rebuild All",
            icon='FILE_REFRESH'
        )
        layout.separator()
        layout.operator(
            "archiforge.preset_save",
            text="Save as Preset",
            icon='EXPORT'
        )


# ════════════════════════════════════════════════════════════
#  MENÚ PIE — acceso rápido con tecla
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_MT_pie(Menu):
    """Pie menu de acceso rápido a los objetos AF."""
    bl_label  = "ArchiForge Quick"
    bl_idname = "ARCHIFORGE_MT_pie"

    def draw(self, context):
        pie = self.layout.menu_pie()

        # West  ←
        pie.operator("archiforge.wall",  text="Wall",   icon='SNAP_EDGE')
        # East  →
        pie.operator("archiforge.floor", text="Floor",  icon='MESH_GRID')
        # South ↓
        pie.operator("archiforge.door",  text="Door",   icon='MESH_CUBE')
        # North ↑
        pie.operator("archiforge.roof",  text="Roof",   icon='MOD_BUILD')
        # NW
        pie.operator("archiforge.stair", text="Stair",  icon='OBJECT_DATA')
        # NE
        pie.operator("archiforge.truss", text="Truss",  icon='MESH_CUBE')
        # SW
        pie.operator("archiforge.fence", text="Fence",  icon='MESH_PLANE')
        # SE
        pie.operator("archiforge.window","Window",      icon='MOD_LATTICE')


# ════════════════════════════════════════════════════════════
#  OPERADOR — Invocar Pie Menu desde atajo de teclado
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_OT_pie_call(Operator):
    """Muestra el pie menu de ArchiForge."""
    bl_idname      = "archiforge.pie_call"
    bl_label       = "ArchiForge Pie Menu"
    bl_description = "Show ArchiForge quick access pie menu"
    bl_options     = {'REGISTER'}

    def invoke(self, context, event):
        bpy.ops.wm.call_menu_pie(name="ARCHIFORGE_MT_pie")
        return {'FINISHED'}

    def execute(self, context):
        return {'FINISHED'}


# ════════════════════════════════════════════════════════════
#  HOOKS de menús nativos de Blender
# ════════════════════════════════════════════════════════════
def _menu_func_add(self, context):
    """Entrada en VIEW3D_MT_mesh_add (Shift+A)."""
    layout = self.layout
    layout.separator()
    layout.menu(
        "ARCHIFORGE_MT_menu_main",
        text="ArchiForge",
        icon='HOME',
    )


def _menu_func_context(self, context):
    """Entrada en VIEW3D_MT_object_context_menu."""
    obj = context.active_object
    if obj is None:
        return
    af_attrs = [
        "archiforge_wall", "archiforge_floor",
        "archiforge_door", "archiforge_window",
        "archiforge_stair", "archiforge_roof",
        "archiforge_fence", "archiforge_slab",
        "archiforge_truss",
    ]
    if any(hasattr(obj, a) for a in af_attrs):
        self.layout.separator()
        self.layout.menu(
            "ARCHIFORGE_MT_context_object",
            text="ArchiForge",
            icon='HOME',
        )


# ════════════════════════════════════════════════════════════
#  KEYMAP
# ════════════════════════════════════════════════════════════
_keymaps = []


def _register_keymaps():
    """Registra el atajo de teclado para el pie menu."""
    wm  = bpy.context.window_manager
    kc  = wm.keyconfigs.addon
    if kc is None:
        return

    # Ctrl+Shift+A en Object Mode
    km = kc.keymaps.new(name='Object Mode', space_type='EMPTY')
    kmi = km.keymap_items.new(
        "archiforge.pie_call",
        type       = 'A',
        value      = 'PRESS',
        ctrl       = True,
        shift      = True,
        alt        = False,
    )
    _keymaps.append((km, kmi))


def _unregister_keymaps():
    """Elimina los atajos de teclado registrados."""
    for km, kmi in _keymaps:
        try:
            km.keymap_items.remove(kmi)
        except Exception:
            pass
    _keymaps.clear()


# ════════════════════════════════════════════════════════════
#  REGISTRO
# ════════════════════════════════════════════════════════════
classes = [
    ARCHIFORGE_MT_menu_main,
    ARCHIFORGE_MT_context_object,
    ARCHIFORGE_MT_pie,
    ARCHIFORGE_OT_pie_call,
]


def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except Exception as e:
            print(f"[ArchiForge] ⚠️  af_menu '{cls.__name__}': {e}")

    # Hooks en menús nativos
    bpy.types.VIEW3D_MT_mesh_add.append(_menu_func_add)
    bpy.types.VIEW3D_MT_object_context_menu.append(_menu_func_context)

    # Atajos de teclado
    _register_keymaps()

    print("[ArchiForge] ✅ af_menu — registered")


def unregister():
    _unregister_keymaps()
    bpy.types.VIEW3D_MT_mesh_add.remove(_menu_func_add)
    bpy.types.VIEW3D_MT_object_context_menu.remove(_menu_func_context)

    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"[ArchiForge] ⚠️  af_menu '{cls.__name__}': {e}")

    print("[ArchiForge] 🔴 af_menu — unregistered")