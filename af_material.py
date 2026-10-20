# -*- coding: utf-8 -*-

# ╔══════════════════════════════════════════════════════════╗
# ║         ARCHIFORGE — af_material.py                     ║
# ║         Sistema de Materiales para Blender 3.3 LTS      ║
# ║         GPL v3 — ArchiForge Devs                        ║
# ╚══════════════════════════════════════════════════════════╝

# <pep8 compliant>

import bpy
import os

from bpy.types import (
    PropertyGroup,
    Operator,
    Panel,
    Menu,
    UIList,
)
from bpy.props import (
    StringProperty,
    BoolProperty,
    IntProperty,
    FloatProperty,
    FloatVectorProperty,
    EnumProperty,
    CollectionProperty,
    PointerProperty,
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

try:
    from . import af_material_procedural as _procedural
except ImportError:  # pragma: no cover - fuera del paquete
    _procedural = None


# ════════════════════════════════════════════════════════════
#  CONSTANTES — Catálogo de materiales base de ArchiForge
#  Cada material tiene: nombre, color RGBA, roughness,
#  metallic, y categoría
# ════════════════════════════════════════════════════════════
AF_MATERIALS_CATALOG = {

    # ── Muros / Concreto ─────────────────────────────────────
    "AF.Wall.Default"    : {"color": (0.90, 0.90, 0.90, 1.0), "rough": 0.9,  "metal": 0.0, "cat": "Wall"},
    "AF.Wall.Concrete"   : {"color": (0.65, 0.65, 0.65, 1.0), "rough": 0.95, "metal": 0.0, "cat": "Wall",
                            "proc": "CONCRETE"},
    "AF.Wall.Brick"      : {"color": (0.70, 0.35, 0.25, 1.0), "rough": 0.9,  "metal": 0.0, "cat": "Wall",
                            "proc": "BRICK"},
    "AF.Wall.Block"      : {"color": (0.62, 0.60, 0.58, 1.0), "rough": 0.95, "metal": 0.0, "cat": "Wall",
                            "proc": "BRICK", "proc_params": {"brick_width": 0.39, "row_height": 0.19,
                                                             "mortar_size": 0.012, "color_variation": 0.9}},
    "AF.Wall.Plaster"    : {"color": (0.95, 0.92, 0.88, 1.0), "rough": 0.85, "metal": 0.0, "cat": "Wall",
                            "proc": "PLASTER"},
    "AF.Wall.Base"       : {"color": (0.80, 0.75, 0.70, 1.0), "rough": 0.8,  "metal": 0.0, "cat": "Wall"},
    "AF.Wall.Top"        : {"color": (0.92, 0.88, 0.84, 1.0), "rough": 0.75, "metal": 0.0, "cat": "Wall"},

    # ── Pisos ────────────────────────────────────────────────
    "AF.Floor.Wood"      : {"color": (0.55, 0.35, 0.18, 1.0), "rough": 0.7,  "metal": 0.0, "cat": "Floor",
                            "proc": "WOOD", "proc_params": {"bands_direction": 'Y'}},
    "AF.Floor.Tile"      : {"color": (0.85, 0.82, 0.80, 1.0), "rough": 0.2,  "metal": 0.0, "cat": "Floor",
                            "proc": "CERAMIC"},
    "AF.Floor.Marble"    : {"color": (0.95, 0.93, 0.91, 1.0), "rough": 0.05, "metal": 0.0, "cat": "Floor",
                            "proc": "MARBLE"},
    "AF.Floor.Concrete"  : {"color": (0.60, 0.60, 0.60, 1.0), "rough": 0.95, "metal": 0.0, "cat": "Floor",
                            "proc": "CONCRETE"},
    "AF.Floor.Carpet"    : {"color": (0.45, 0.40, 0.55, 1.0), "rough": 1.0,  "metal": 0.0, "cat": "Floor",
                            "proc": "FABRIC"},

    # ── Techos / Losas ───────────────────────────────────────
    "AF.Roof.Tile"       : {"color": (0.55, 0.28, 0.18, 1.0), "rough": 0.9,  "metal": 0.0, "cat": "Roof",
                            "proc": "CLAY"},
    "AF.Roof.Metal"      : {"color": (0.60, 0.62, 0.65, 1.0), "rough": 0.3,  "metal": 0.9, "cat": "Roof"},
    "AF.Roof.Concrete"   : {"color": (0.62, 0.62, 0.62, 1.0), "rough": 0.95, "metal": 0.0, "cat": "Roof",
                            "proc": "CONCRETE"},
    "AF.Slab.Default"    : {"color": (0.75, 0.75, 0.75, 1.0), "rough": 0.9,  "metal": 0.0, "cat": "Roof",
                            "proc": "CONCRETE"},

    # ── Puertas ──────────────────────────────────────────────
    "AF.Door.Wood"       : {"color": (0.42, 0.26, 0.12, 1.0), "rough": 0.65, "metal": 0.0, "cat": "Door",
                            "proc": "WOOD", "proc_params": {"bands_direction": 'X'}},
    "AF.Door.Glass"      : {"color": (0.70, 0.85, 0.90, 0.3), "rough": 0.02, "metal": 0.0, "cat": "Door"},
    "AF.Door.Metal"      : {"color": (0.55, 0.55, 0.60, 1.0), "rough": 0.25, "metal": 0.85,"cat": "Door"},
    "AF.Door.Frame"      : {"color": (0.85, 0.82, 0.78, 1.0), "rough": 0.7,  "metal": 0.0, "cat": "Door"},
    "AF.Door.Handle"     : {"color": (0.80, 0.72, 0.50, 1.0), "rough": 0.1,  "metal": 1.0, "cat": "Door"},

    # ── Ventanas ─────────────────────────────────────────────
    "AF.Window.Glass"    : {"color": (0.72, 0.88, 0.95, 0.2), "rough": 0.0,  "metal": 0.0, "cat": "Window"},
    "AF.Window.Frame"    : {"color": (0.90, 0.90, 0.90, 1.0), "rough": 0.5,  "metal": 0.0, "cat": "Window"},
    "AF.Window.Frame.Al" : {"color": (0.75, 0.78, 0.80, 1.0), "rough": 0.2,  "metal": 0.8, "cat": "Window"},

    # ── Escaleras ────────────────────────────────────────────
    "AF.Stair.Wood"      : {"color": (0.45, 0.28, 0.14, 1.0), "rough": 0.65, "metal": 0.0, "cat": "Stair",
                            "proc": "WOOD", "proc_params": {"bands_direction": 'Y'}},
    "AF.Stair.Concrete"  : {"color": (0.65, 0.65, 0.65, 1.0), "rough": 0.9,  "metal": 0.0, "cat": "Stair",
                            "proc": "CONCRETE"},
    "AF.Stair.Metal"     : {"color": (0.60, 0.62, 0.65, 1.0), "rough": 0.3,  "metal": 0.9, "cat": "Stair"},
    "AF.Stair.Rail"      : {"color": (0.55, 0.55, 0.58, 1.0), "rough": 0.2,  "metal": 0.9, "cat": "Stair"},

    # ── Cercas ───────────────────────────────────────────────
    "AF.Fence.Wood"      : {"color": (0.38, 0.22, 0.10, 1.0), "rough": 0.9,  "metal": 0.0, "cat": "Fence",
                            "proc": "WOOD", "proc_params": {"bands_direction": 'X'}},
    "AF.Fence.Metal"     : {"color": (0.25, 0.25, 0.28, 1.0), "rough": 0.4,  "metal": 0.8, "cat": "Fence"},

    # ── Truss / Estructura ───────────────────────────────────
    "AF.Truss.Metal"     : {"color": (0.50, 0.52, 0.55, 1.0), "rough": 0.35, "metal": 0.9, "cat": "Truss"},
    "AF.Truss.Wood"      : {"color": (0.42, 0.26, 0.12, 1.0), "rough": 0.7,  "metal": 0.0, "cat": "Truss",
                            "proc": "WOOD", "proc_params": {"bands_direction": 'X'}},

    # ── Room Asset Library ───────────────────────────────────
    "AF.Room.Wood"       : {"color": (0.38, 0.23, 0.13, 1.0), "rough": 0.58, "metal": 0.0,  "cat": "Room",
                            "proc": "WOOD", "proc_params": {"bands_direction": 'X'}},
    "AF.Room.Fabric"     : {"color": (0.68, 0.61, 0.53, 1.0), "rough": 0.82, "metal": 0.0,  "cat": "Room",
                            "proc": "FABRIC"},
    "AF.Room.Metal"      : {"color": (0.20, 0.23, 0.25, 1.0), "rough": 0.30, "metal": 0.72, "cat": "Room"},
    "AF.Room.Accent"     : {"color": (0.20, 0.43, 0.35, 1.0), "rough": 0.55, "metal": 0.0,  "cat": "Room"},
}

# Categorías disponibles para el filtro de la UI
AF_MATERIAL_CATEGORIES = [
    ('ALL',    "All",     "Show all materials"),
    ('WALL',   "Wall",    "Wall materials"),
    ('FLOOR',  "Floor",   "Floor materials"),
    ('ROOF',   "Roof",    "Roof and slab materials"),
    ('DOOR',   "Door",    "Door materials"),
    ('WINDOW', "Window",  "Window materials"),
    ('STAIR',  "Stair",   "Stair materials"),
    ('FENCE',  "Fence",   "Fence materials"),
    ('TRUSS',  "Truss",   "Truss materials"),
    ('ROOM',   "Room Assets", "Furniture and decor materials"),
]


# ════════════════════════════════════════════════════════════
#  UTILIDADES DE CREACIÓN DE NODOS
#  Creamos materiales Principled BSDF con nodos
# ════════════════════════════════════════════════════════════
def _create_principled_material(name, color, roughness, metallic):
    """
    Crea o actualiza un material con nodos Principled BSDF.
    Si el material ya existe, actualiza sus valores.
    Retorna el material.
    """
    # — Crear o recuperar —
    if name in bpy.data.materials:
        mat = bpy.data.materials[name]
    else:
        mat = bpy.data.materials.new(name)

    mat.use_nodes = True

    # — Limpiar nodos existentes —
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # — Nodo OUTPUT ——————————————————————————————————————————
    node_out = nodes.new("ShaderNodeOutputMaterial")
    node_out.location = (400, 0)

    # — Nodo PRINCIPLED BSDF ——————————————————————————————————
    node_bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    node_bsdf.location = (0, 0)

    # — Asignar valores ————————————————————————————————————————
    node_bsdf.inputs["Base Color"].default_value    = color
    node_bsdf.inputs["Roughness"].default_value     = roughness
    node_bsdf.inputs["Metallic"].default_value      = metallic

    # — Transparencia si alpha < 1 ————————————————————————————
    alpha = color[3] if len(color) == 4 else 1.0
    if alpha < 1.0:
        node_bsdf.inputs["Alpha"].default_value = alpha
        mat.blend_method   = 'BLEND'
        mat.shadow_method  = 'CLIP'
    else:
        mat.blend_method   = 'OPAQUE'
        mat.shadow_method  = 'OPAQUE'

    # — Conectar BSDF → Output ————————————————————————————————
    links.new(
        node_bsdf.outputs["BSDF"],
        node_out.inputs["Surface"]
    )

    # — Metadatos en el material ——————————————————————————————
    mat["af_material"]    = True
    mat["af_category"]    = AF_MATERIALS_CATALOG.get(name, {}).get("cat", "")
    mat.diffuse_color     = color

    return mat


def procedural_materials_enabled():
    """Preferencia *Procedural Materials* (True si no hay preferencias)."""
    try:
        prefs = bpy.context.preferences.addons[__package__].preferences
        return bool(getattr(prefs, "procedural_materials", True))
    except Exception:  # noqa: BLE001 - sin preferencias (background)
        return True


def _set_socket(node, key, value):
    try:
        node.inputs[key].default_value = value
        return True
    except (KeyError, IndexError, TypeError, AttributeError, ValueError):
        return False


def _build_recipe_nodes(node_tree, recipe):
    """Materializa una receta de ``af_material_procedural`` en ``node_tree``."""
    nodes = node_tree.nodes
    links = node_tree.links
    nodes.clear()
    created = {}
    for spec in recipe["nodes"]:
        node = nodes.new(spec["type"])
        node.location = spec.get("loc", (0, 0))
        if spec.get("name"):
            node.name = spec["name"]
            node.label = spec["name"]
        for attr, value in spec.get("props", {}).items():
            try:
                setattr(node, attr, value)
            except (AttributeError, TypeError, ValueError):
                pass
        for key, value in spec.get("inputs", {}).items():
            _set_socket(node, key, value)
        stops = spec.get("ramp")
        if stops and hasattr(node, "color_ramp"):
            elements = node.color_ramp.elements
            while len(elements) > 1:
                elements.remove(elements[-1])
            elements[0].position = stops[0][0]
            elements[0].color = stops[0][1]
            for position, color in stops[1:]:
                element = elements.new(position)
                element.color = color
        created[spec["id"]] = node
    for src, out, dst, inp in recipe["links"]:
        try:
            links.new(created[src].outputs[out], created[dst].inputs[inp])
        except (KeyError, IndexError, RuntimeError, AttributeError):
            pass
    return created


def _create_recipe_material(name, spec, recipe):
    """Crea/actualiza un material procedural; cae al plano si algo falla."""
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    try:
        _build_recipe_nodes(mat.node_tree, recipe)
    except Exception as err:  # noqa: BLE001 - versión de Blender sin el nodo
        print("[ArchiForge] procedural material '{}' failed ({}); "
              "using flat colour".format(name, err))
        return _create_principled_material(
            name, spec["color"], spec["rough"], spec["metal"])
    color = tuple(spec["color"])
    alpha = color[3] if len(color) == 4 else 1.0
    bsdf = mat.node_tree.nodes.get(_procedural.BSDF_NODE_NAME)
    if alpha < 1.0 and bsdf is not None:
        _set_socket(bsdf, "Alpha", alpha)
        mat.blend_method = 'BLEND'
        mat.shadow_method = 'CLIP'
    else:
        mat.blend_method = 'OPAQUE'
        mat.shadow_method = 'OPAQUE'
    mat["af_material"] = True
    mat["af_category"] = spec.get("cat", "")
    mat["af_procedural"] = spec.get("proc", "")
    mat.diffuse_color = color
    mat.roughness = float(spec["rough"])
    mat.metallic = float(spec["metal"])
    return mat


def create_catalog_material(name, spec=None):
    """Crea o actualiza el material ``name`` según el catálogo.

    Usa la receta procedural del catálogo cuando la preferencia está
    activa; de lo contrario (o si la receta no existe) un Principled plano.
    """
    spec = spec or AF_MATERIALS_CATALOG[name]
    kind = spec.get("proc")
    if kind and _procedural is not None and procedural_materials_enabled():
        recipe = _procedural.build_recipe(
            kind, spec["color"], spec["rough"], spec["metal"],
            spec.get("proc_params"))
        if recipe is not None:
            return _create_recipe_material(name, spec, recipe)
    return _create_principled_material(
        name      = name,
        color     = spec["color"],
        roughness = spec["rough"],
        metallic  = spec["metal"],
    )


def ensure_af_material(name):
    """
    Asegura que un material de ArchiForge existe en la escena.
    Si no existe, lo crea desde el catálogo.
    Retorna el material o None si el nombre no está en el catálogo.
    """
    if name in bpy.data.materials:
        return bpy.data.materials[name]

    if name not in AF_MATERIALS_CATALOG:
        print(f"[ArchiForge] ⚠️  Material '{name}' no está en el catálogo")
        return None

    return create_catalog_material(name)


def ensure_af_materials_for_object(obj, material_names):
    """
    Asegura que un objeto tiene los materiales indicados
    asignados en sus slots. Crea los que faltan.
    Retorna lista de índices de los materiales en el objeto.
    """
    me      = obj.data
    indices = []

    for mname in material_names:
        mat = ensure_af_material(mname)
        if mat is None:
            indices.append(0)
            continue

        # — Buscar si ya está en el objeto —
        found = False
        for i, slot in enumerate(me.materials):
            if slot and slot.name == mname:
                indices.append(i)
                found = True
                break

        # — Añadir si no estaba —
        if not found:
            me.materials.append(mat)
            indices.append(len(me.materials) - 1)

    return indices


def rebuild_all_af_materials():
    """
    Reconstruye todos los materiales del catálogo
    en la escena actual. Útil para resetear.
    """
    count = 0
    for name, spec in AF_MATERIALS_CATALOG.items():
        create_catalog_material(name, spec)
        count += 1
    print(f"[ArchiForge] ✅ {count} materiales reconstruidos")
    return count


def refresh_existing_af_materials():
    """Regenera solo los materiales del catálogo ya presentes en el archivo.

    Se usa al cambiar la preferencia *Procedural Materials* para que el
    archivo abierto refleje el modo elegido sin crear materiales nuevos.
    """
    count = 0
    for name, spec in AF_MATERIALS_CATALOG.items():
        if name in bpy.data.materials:
            create_catalog_material(name, spec)
            count += 1
    return count


def get_af_materials_by_category(category="ALL"):
    """
    Retorna lista de nombres de materiales del catálogo
    filtrados por categoría.
    """
    if category == "ALL":
        return list(AF_MATERIALS_CATALOG.keys())

    cat_lower = category.capitalize()
    return [
        name for name, spec in AF_MATERIALS_CATALOG.items()
        if spec.get("cat", "").lower() == category.lower()
    ]


# ════════════════════════════════════════════════════════════
#  PROPERTYGROUP — Slot de material en un objeto ArchiForge
# ════════════════════════════════════════════════════════════
class AF_MaterialSlot(PropertyGroup):
    """
    Representa un slot de material de ArchiForge.
    Cada objeto puede tener múltiples slots nombrados.
    """

    slot_name : StringProperty(
        name        = "Slot Name",
        description = "Descriptive name for this material slot",
        default     = "Material",
    )

    material_name : StringProperty(
        name        = "Material",
        description = "Name of the material assigned to this slot",
        default     = "",
    )

    slot_index : IntProperty(
        name        = "Slot Index",
        description = "Index of this slot in the object's material list",
        default     = 0,
        min         = 0,
    )

    enabled : BoolProperty(
        name        = "Enabled",
        description = "Enable or disable this material slot",
        default     = True,
    )


# ════════════════════════════════════════════════════════════
#  PROPERTYGROUP — Manager de materiales del objeto
# ════════════════════════════════════════════════════════════
class AF_MaterialManager(PropertyGroup):
    """
    Gestor de materiales para objetos ArchiForge.
    Se registra en bpy.types.Object como .archiforge_materials
    """

    slots : CollectionProperty(
        name = "Material Slots",
        type = AF_MaterialSlot,
    )

    active_slot : IntProperty(
        name    = "Active Slot",
        default = 0,
        min     = 0,
    )

    category_filter : EnumProperty(
        name    = "Category",
        items   = AF_MATERIAL_CATEGORIES,
        default = 'ALL',
    )

    show_catalog : BoolProperty(
        name    = "Show Catalog",
        default = False,
    )

    library_path : StringProperty(
        name        = "Library Path",
        description = "Path to external material library (.blend)",
        default     = "",
        subtype     = "FILE_PATH",
    )


# ════════════════════════════════════════════════════════════
#  UIList — Lista visual de slots de material
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_UL_material_slots(UIList):
    bl_idname = "ARCHIFORGE_UL_material_slots"

    def draw_item(
        self, context, layout, data,
        item, icon, active_data, active_propname,
        index=0, flt_flag=0
    ):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)

            # — Ícono de material —
            mat = bpy.data.materials.get(item.material_name)
            if mat:
                row.prop(
                    item, "enabled",
                    text="",
                    icon='MATERIAL',
                    emboss=False,
                )
                row.label(text=item.slot_name)
                # — Preview color del material —
                sub = row.row(align=True)
                sub.scale_x = 0.4
                sub.label(text="", icon='MATERIAL')
            else:
                row.prop(
                    item, "enabled",
                    text="",
                    icon='MATERIAL',
                    emboss=False,
                )
                row.label(
                    text=f"{item.slot_name}",
                    icon='ERROR' if not item.material_name else 'MATERIAL',
                )

        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon='MATERIAL')

    def filter_items(self, context, data, propname):
        items    = getattr(data, propname)
        filtered = [self.bitflag_filter_item] * len(items)
        ordered  = []
        return filtered, ordered


# ════════════════════════════════════════════════════════════
#  OPERADORES
# ════════════════════════════════════════════════════════════

# ────────────────────────────────────────────────────────────
#  OP: Crear todos los materiales del catálogo
# ────────────────────────────────────────────────────────────
class ARCHIFORGE_OT_create_all_materials(Operator):
    bl_idname      = "archiforge.create_all_materials"
    bl_label       = "Create All AF Materials"
    bl_description = "Generate all ArchiForge materials in the current scene"
    bl_options     = {'REGISTER', 'UNDO'}

    def execute(self, context):
        count = rebuild_all_af_materials()
        self.report({'INFO'}, _tr("✅ {} ArchiForge materials created/updated")
                              .format(count))
        return {'FINISHED'}


# ────────────────────────────────────────────────────────────
#  OP: Asignar material del catálogo al objeto activo
# ────────────────────────────────────────────────────────────
class ARCHIFORGE_OT_assign_material(Operator):
    bl_idname      = "archiforge.assign_material"
    bl_label       = "Assign Material"
    bl_description = "Assign selected ArchiForge material to active object slot"
    bl_options     = {'REGISTER', 'UNDO'}

    material_name : StringProperty(
        name    = "Material Name",
        default = "",
    )

    slot_index : IntProperty(
        name    = "Slot Index",
        default = 0,
        min     = 0,
    )

    @classmethod
    def poll(cls, context):
        return (
            context.active_object is not None
            and context.active_object.type == 'MESH'
        )

    def execute(self, context):
        obj = context.active_object
        mat = ensure_af_material(self.material_name)

        if mat is None:
            self.report({'ERROR'}, _tr("Material '{}' not found")
                                   .format(self.material_name))
            return {'CANCELLED'}

        me = obj.data

        # — Expandir slots si es necesario —
        while len(me.materials) <= self.slot_index:
            me.materials.append(None)

        me.materials[self.slot_index] = mat

        self.report(
            {'INFO'},
            _tr("Assigned '{}' to slot {}").format(self.material_name, self.slot_index)
        )
        return {'FINISHED'}


# ────────────────────────────────────────────────────────────
#  OP: Asignar material a slot activo desde catálogo
# ────────────────────────────────────────────────────────────
class ARCHIFORGE_OT_assign_from_catalog(Operator):
    bl_idname      = "archiforge.assign_from_catalog"
    bl_label       = "Assign from Catalog"
    bl_description = "Assign this catalog material to the active slot"
    bl_options     = {'REGISTER', 'UNDO'}

    material_name : StringProperty(default="")

    @classmethod
    def poll(cls, context):
        return (
            context.active_object is not None
            and context.active_object.type == 'MESH'
        )

    def execute(self, context):
        obj = context.active_object
        mat = ensure_af_material(self.material_name)

        if mat is None:
            self.report({'ERROR'}, _tr("Could not create material '{}'")
                                   .format(self.material_name))
            return {'CANCELLED'}

        # — Usar slot activo de Blender —
        slot_idx = obj.active_material_index
        me       = obj.data

        while len(me.materials) <= slot_idx:
            me.materials.append(None)

        me.materials[slot_idx] = mat

        self.report({'INFO'}, _tr("✅ '{}' assigned").format(self.material_name))
        return {'FINISHED'}


# ────────────────────────────────────────────────────────────
#  OP: Resetear materiales del objeto a defaults de AF
# ────────────────────────────────────────────────────────────
class ARCHIFORGE_OT_reset_materials(Operator):
    bl_idname      = "archiforge.reset_materials"
    bl_label       = "Reset AF Materials"
    bl_description = "Reset all ArchiForge materials on this object to defaults"
    bl_options     = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj is not None
            and obj.type == 'MESH'
            and any(
                (m and m.get("af_material", False))
                for m in obj.data.materials
            )
        )

    def execute(self, context):
        obj   = context.active_object
        count = 0

        for slot in obj.data.materials:
            if slot and slot.get("af_material", False):
                name = slot.name
                if name in AF_MATERIALS_CATALOG:
                    create_catalog_material(name)
                    count += 1

        self.report({'INFO'}, _tr("Reset {} materials").format(count))
        return {'FINISHED'}


# ────────────────────────────────────────────────────────────
#  OP: Limpiar materiales AF no usados
# ────────────────────────────────────────────────────────────
class ARCHIFORGE_OT_clean_unused_materials(Operator):
    bl_idname      = "archiforge.clean_unused_materials"
    bl_label       = "Clean Unused AF Materials"
    bl_description = "Remove ArchiForge materials not used by any object"
    bl_options     = {'REGISTER', 'UNDO'}

    def execute(self, context):
        removed = 0
        for mat in list(bpy.data.materials):
            if mat.get("af_material", False) and mat.users == 0:
                bpy.data.materials.remove(mat)
                removed += 1

        self.report({'INFO'}, _tr("Removed {} unused AF materials").format(removed))
        return {'FINISHED'}


# ────────────────────────────────────────────────────────────
#  OP: Cargar librería externa de materiales (.blend)
# ────────────────────────────────────────────────────────────
class ARCHIFORGE_OT_load_material_library(Operator):
    bl_idname      = "archiforge.load_material_library"
    bl_label       = "Load Material Library"
    bl_description = "Load materials from an external .blend file"
    bl_options     = {'REGISTER', 'UNDO'}

    filepath : StringProperty(subtype="FILE_PATH")
    filter_glob : StringProperty(default="*.blend", options={'HIDDEN'})

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        if not os.path.isfile(self.filepath):
            self.report({'ERROR'}, _tr("File not found: {}").format(self.filepath))
            return {'CANCELLED'}

        if not self.filepath.endswith(".blend"):
            self.report({'ERROR'}, _tr("File must be a .blend file"))
            return {'CANCELLED'}

        # — Cargar materiales del .blend externo —
        try:
            with bpy.data.libraries.load(self.filepath, link=False) as (src, dst):
                dst.materials = [
                    m for m in src.materials
                    if m.startswith("AF.")
                ]

            count = len([m for m in bpy.data.materials if m.name.startswith("AF.")])
            self.report({'INFO'}, _tr("✅ Loaded {} AF materials from library")
                                  .format(count))

        except Exception as e:
            self.report({'ERROR'}, _tr("Error loading library: {}").format(e))
            return {'CANCELLED'}

        return {'FINISHED'}


# ════════════════════════════════════════════════════════════
#  PANEL — N-Panel de materiales ArchiForge
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_PT_materials(Panel):
    bl_label       = "AF Materials"
    bl_idname      = "ARCHIFORGE_PT_materials"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "ArchiForge"
    bl_context     = "objectmode"
    bl_options     = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return (
            context.active_object is not None
            and context.active_object.type == 'MESH'
        )

    def draw_header(self, context):
        self.layout.label(text="", **_icon("material", 'MATERIAL'))

    def draw(self, context):
        obj    = context.active_object
        me     = obj.data
        layout = self.layout
        layout.use_property_split = False

        # ── Slots actuales del objeto ─────────────────────────
        box = layout.box()
        col = box.column(align=True)
        row = col.row(align=True)
        row.label(text="Material Slots", icon='MATERIAL')
        row.label(text=f"({len(me.materials)})")

        # — Lista de slots —
        for i, mat in enumerate(me.materials):
            row = col.row(align=True)
            row.label(
                text=f"[{i}]",
                icon='RADIOBUT_ON'
                    if i == obj.active_material_index
                    else 'RADIOBUT_OFF'
            )
            if mat:
                is_af = mat.get("af_material", False)
                row.label(
                    text=mat.name,
                    icon='MATERIAL' if is_af else 'MATERIAL'
                )
                # — Botón color preview —
                sub = row.row(align=True)
                sub.scale_x = 0.3
                sub.enabled = False
                sub.prop(mat, "diffuse_color", text="")
            else:
                row.label(text="(empty)", icon='ERROR')

        layout.separator(factor=0.4)

        # ── Catálogo de materiales AF ─────────────────────────
        box = layout.box()
        af_mat = obj.archiforge_materials
        row = box.row(align=True)
        row.prop(
            af_mat, "show_catalog",
            text="Material Catalog",
            icon='TRIA_DOWN' if af_mat.show_catalog else 'TRIA_RIGHT',
            toggle=True,
            emboss=False,
        )

        if af_mat.show_catalog:
            # — Filtro por categoría —
            row = box.row(align=True)
            row.label(text="Filter:", icon='FILTER')
            row.prop(af_mat, "category_filter", text="")

            box.separator(factor=0.3)

            # — Grid de materiales filtrados —
            cat    = af_mat.category_filter
            mats   = get_af_materials_by_category(cat)
            grid   = box.grid_flow(
                row_major   = True,
                columns     = 2,
                even_columns= True,
                even_rows   = False,
                align       = True,
            )

            for mname in mats:
                spec    = AF_MATERIALS_CATALOG[mname]
                mat_row = grid.row(align=True)

                # — Preview de color —
                existing = bpy.data.materials.get(mname)
                if existing:
                    sub = mat_row.row(align=True)
                    sub.scale_x = 0.15
                    sub.enabled = False
                    sub.prop(existing, "diffuse_color", text="")

                # — Botón de asignar —
                op = mat_row.operator(
                    "archiforge.assign_from_catalog",
                    text=mname.split(".")[-1],
                    emboss=True,
                )
                op.material_name = mname

        layout.separator(factor=0.4)

        # ── Acciones globales ─────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Actions", icon='TOOL_SETTINGS')

        row = col.row(align=True)
        row.operator(
            "archiforge.create_all_materials",
            text="Build All",
            **_icon("material_library", 'MATERIAL'),
        )
        row.operator(
            "archiforge.reset_materials",
            text="Reset",
            icon='FILE_REFRESH',
        )

        col.separator(factor=0.3)
        col.operator(
            "archiforge.clean_unused_materials",
            text="Clean Unused",
            icon='TRASH',
        )

        col.separator(factor=0.3)
        col.operator(
            "archiforge.load_material_library",
            text="Load Library (.blend)",
            icon='FILEBROWSER',
        )


# ════════════════════════════════════════════════════════════
#  PANEL SUB — Propiedades del material activo
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_PT_material_active(Panel):
    bl_label       = "Active Material"
    bl_idname      = "ARCHIFORGE_PT_material_active"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "ArchiForge"
    bl_context     = "objectmode"
    bl_parent_id   = "ARCHIFORGE_PT_materials"
    bl_options     = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj is not None
            and obj.type == 'MESH'
            and obj.active_material is not None
        )

    def draw(self, context):
        obj    = context.active_object
        mat    = obj.active_material
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        if mat is None:
            layout.label(text="No material selected", icon='ERROR')
            return

        # — Info del material activo —
        box = layout.box()
        row = box.row(align=True)
        row.label(
            text=mat.name,
            icon='MATERIAL'
        )
        if mat.get("af_material", False):
            row.label(text="AF", icon='CHECKMARK')

        box.separator(factor=0.3)

        # — Editar propiedades si tiene nodos —
        if mat.use_nodes:
            bsdf = mat.node_tree.nodes.get("Principled BSDF")
            if bsdf:
                col = box.column(align=True)
                col.prop(
                    bsdf.inputs["Base Color"],
                    "default_value",
                    text="Color"
                )
                col.prop(
                    bsdf.inputs["Roughness"],
                    "default_value",
                    text="Roughness"
                )
                col.prop(
                    bsdf.inputs["Metallic"],
                    "default_value",
                    text="Metallic"
                )
                col.prop(
                    bsdf.inputs["Alpha"],
                    "default_value",
                    text="Alpha"
                )
            else:
                box.label(text="No Principled BSDF found", icon='INFO')
        else:
            box.label(text="Material has no nodes", icon='INFO')


# ════════════════════════════════════════════════════════════
#  REGISTRO
# ════════════════════════════════════════════════════════════
classes = [
    # — PropertyGroups primero —
    AF_MaterialSlot,
    AF_MaterialManager,

    # — UIList —
    ARCHIFORGE_UL_material_slots,

    # — Operadores —
    ARCHIFORGE_OT_create_all_materials,
    ARCHIFORGE_OT_assign_material,
    ARCHIFORGE_OT_assign_from_catalog,
    ARCHIFORGE_OT_reset_materials,
    ARCHIFORGE_OT_clean_unused_materials,
    ARCHIFORGE_OT_load_material_library,

    # — Paneles —
    ARCHIFORGE_PT_materials,
    ARCHIFORGE_PT_material_active,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    # — Registrar PropertyGroup en Object —
    bpy.types.Object.archiforge_materials = PointerProperty(
        type        = AF_MaterialManager,
        name        = "ArchiForge Materials",
        description = "ArchiForge material manager for this object",
    )

    print("[ArchiForge] ✅ af_material — registered")


def unregister():
    if hasattr(bpy.types.Object, "archiforge_materials"):
        del bpy.types.Object.archiforge_materials

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    print("[ArchiForge] 🔴 af_material — unregistered")