# -*- coding: utf-8 -*-

# ╔══════════════════════════════════════════════════════════╗
# ║         ARCHIFORGE — af_autoboolean.py                  ║
# ║         Sistema de Boolean Automático Blender 3.3 LTS   ║
# ║         GPL v3 — ArchiForge Devs                        ║
# ╚══════════════════════════════════════════════════════════╝

# <pep8 compliant>

import bpy
import bmesh
import math

from mathutils import Vector, Matrix
from bpy.types import (
    PropertyGroup,
    Operator,
    Panel,
)
from bpy.props import (
    StringProperty,
    BoolProperty,
    IntProperty,
    FloatProperty,
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


# ════════════════════════════════════════════════════════════
#  CONSTANTES
# ════════════════════════════════════════════════════════════
AF_CUTTER_PREFIX   = "AF.Cutter."
AF_BOOL_MOD_PREFIX = "AF_Bool_"
AF_WALL_DETECT_DIST = 2.0

AF_BOOL_MODES = [
    ('HYBRID', "Hybrid",
     "Non-destructive: uses Boolean modifier (recommended)", 'MOD_BOOLEAN', 0),
    ('APPLY',  "Apply",
     "Apply the boolean and remove modifier",               'CHECKMARK',   1),
    ('DIRECT', "Direct",
     "Apply boolean and remove cutter object",             'TRASH',       2),
]

AF_BOOL_SOLVERS = [
    ('FAST',  "Fast",  "Faster, may have artifacts on complex meshes"),
    ('EXACT', "Exact", "More precise, slower (recommended for architecture)"),
]


# ════════════════════════════════════════════════════════════
#  PROPERTYGROUPS
# ════════════════════════════════════════════════════════════
class AF_BooleanCutter(PropertyGroup):
    cutter_name   : StringProperty(name="Cutter Object Name",   default="")
    wall_name     : StringProperty(name="Target Wall Name",     default="")
    modifier_name : StringProperty(name="Modifier Name",        default="")
    active        : BoolProperty(  name="Active",               default=True)


class AF_BooleanManager(PropertyGroup):
    cutters : CollectionProperty(name="Cutters", type=AF_BooleanCutter)

    mode : EnumProperty(
        name="Boolean Mode", items=AF_BOOL_MODES, default='HYBRID',
    )
    solver : EnumProperty(
        name="Solver", items=AF_BOOL_SOLVERS, default='EXACT',
    )
    is_af_cutter : BoolProperty(
        name="Is ArchiForge Cutter", default=False, options={'HIDDEN'},
    )
    source_object : StringProperty(
        name="Source Object", default="", options={'HIDDEN'},
    )
    cutter_type : EnumProperty(
        name="Cutter Type",
        items=[
            ('DOOR',   "Door",   "Cutter for a door opening"),
            ('WINDOW', "Window", "Cutter for a window opening"),
            ('CUSTOM', "Custom", "Custom shaped cutter"),
        ],
        default='DOOR',
    )


# ════════════════════════════════════════════════════════════
#  HELPERS DE EVALUACIÓN
# ════════════════════════════════════════════════════════════
def _eval_poly_count(obj):
    """
    Devuelve el número de polígonos EVALUADOS del objeto
    (incluyendo el efecto de los modificadores).

    Se usa para verificar que un Boolean realmente produjo
    geometría nueva en el muro.
    """
    if obj is None:
        return 0
    try:
        deps = bpy.context.evaluated_depsgraph_get()
        ev   = obj.evaluated_get(deps)
        if ev is None or ev.data is None:
            return 0
        return len(ev.data.polygons)
    except Exception:
        return 0


# ════════════════════════════════════════════════════════════
#  GENERADORES DE CUTTERS — alineados con origen
# ════════════════════════════════════════════════════════════
def _generate_door_cutter_mesh(
    width=0.90,
    height=2.10,
    depth=0.50,
    frame_w=0.05
):
    """
    Cutter para puerta.

    SISTEMA DE COORDENADAS (igual que af_door.py):
      X: 0 = borde izquierdo de la apertura
         width = borde derecho
      Y: centrado en 0 (atraviesa el muro)
      Z: 0 = suelo, height = techo de la apertura
    """
    bm = bmesh.new()

    x0 = -frame_w
    x1 =  width  + frame_w
    z0 = -0.005
    z1 =  height + frame_w
    d  =  depth  * 0.5

    verts = [
        bm.verts.new(Vector((x0, -d, z0))),
        bm.verts.new(Vector((x1, -d, z0))),
        bm.verts.new(Vector((x1, -d, z1))),
        bm.verts.new(Vector((x0, -d, z1))),
        bm.verts.new(Vector((x0,  d, z0))),
        bm.verts.new(Vector((x1,  d, z0))),
        bm.verts.new(Vector((x1,  d, z1))),
        bm.verts.new(Vector((x0,  d, z1))),
    ]

    bm.verts.ensure_lookup_table()

    for fi in [
        (0, 1, 2, 3),
        (5, 4, 7, 6),
        (0, 4, 5, 1),
        (3, 2, 6, 7),
        (0, 3, 7, 4),
        (1, 5, 6, 2),
    ]:
        bm.faces.new([verts[i] for i in fi])

    bm.normal_update()
    return bm


def _generate_window_cutter_mesh(
    width=1.20,
    height=1.20,
    sill_height=0.90,
    depth=0.50,
    frame_w=0.05
):
    """
    Cutter para ventana.

    SISTEMA DE COORDENADAS (igual que af_window.py):
      X: 0 = borde izquierdo, width = borde derecho
      Y: centrado en 0 (atraviesa el muro)
      Z: sill_height = alféizar base
    """
    bm = bmesh.new()

    x0 = -frame_w
    x1 =  width       + frame_w
    z0 =  sill_height - frame_w
    z1 =  sill_height + height + frame_w
    d  =  depth * 0.5

    verts = [
        bm.verts.new(Vector((x0, -d, z0))),
        bm.verts.new(Vector((x1, -d, z0))),
        bm.verts.new(Vector((x1, -d, z1))),
        bm.verts.new(Vector((x0, -d, z1))),
        bm.verts.new(Vector((x0,  d, z0))),
        bm.verts.new(Vector((x1,  d, z0))),
        bm.verts.new(Vector((x1,  d, z1))),
        bm.verts.new(Vector((x0,  d, z1))),
    ]

    bm.verts.ensure_lookup_table()

    for fi in [
        (0, 1, 2, 3),
        (5, 4, 7, 6),
        (0, 4, 5, 1),
        (3, 2, 6, 7),
        (0, 3, 7, 4),
        (1, 5, 6, 2),
    ]:
        bm.faces.new([verts[i] for i in fi])

    bm.normal_update()
    return bm


def _generate_custom_cutter_mesh(width, height, depth):
    """Cutter rectangular genérico."""
    return _generate_door_cutter_mesh(
        width   = width,
        height  = height,
        depth   = depth,
        frame_w = 0.0,
    )


# ════════════════════════════════════════════════════════════
#  DETECCIÓN DE MURO — por AABB (no por centro)
# ════════════════════════════════════════════════════════════
def _world_bbox(obj):
    corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    xs = [c.x for c in corners]
    ys = [c.y for c in corners]
    zs = [c.z for c in corners]
    return min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)


def _bbox_distance(obj_a, obj_b):
    """
    Distancia mínima entre las AABB de dos objetos.
    Retorna 0 si se solapan o tocan.
    """
    ax0, ay0, az0, ax1, ay1, az1 = _world_bbox(obj_a)
    bx0, by0, bz0, bx1, by1, bz1 = _world_bbox(obj_b)

    dx = max(0.0, max(ax0 - bx1, bx0 - ax1))
    dy = max(0.0, max(ay0 - by1, by0 - ay1))
    dz = max(0.0, max(az0 - bz1, bz0 - az1))

    return math.sqrt(dx * dx + dy * dy + dz * dz)


def find_nearest_wall(source_obj, max_dist=AF_WALL_DETECT_DIST):
    """
    Encuentra el muro AF más cercano usando distancia AABB.
    Mucho más preciso que comparar centros.
    """
    nearest      = None
    nearest_dist = max_dist

    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        if obj is source_obj:
            continue
        if not hasattr(obj, 'archiforge_wall'):
            continue
        if not obj.archiforge_wall.is_af_wall:
            continue

        dist = _bbox_distance(source_obj, obj)
        if dist < nearest_dist:
            nearest_dist = dist
            nearest      = obj

    return nearest


def find_all_walls():
    return [
        obj for obj in bpy.data.objects
        if (obj.type == 'MESH'
            and hasattr(obj, 'archiforge_wall')
            and obj.archiforge_wall.is_af_wall)
    ]


def get_walls_in_radius(center, radius):
    results = []
    for obj in bpy.data.objects:
        if (obj.type == 'MESH'
                and hasattr(obj, 'archiforge_wall')
                and obj.archiforge_wall.is_af_wall):
            dist = (obj.matrix_world.translation - center).length
            if dist <= radius:
                results.append((obj, dist))
    results.sort(key=lambda x: x[1])
    return results


# ════════════════════════════════════════════════════════════
#  SISTEMA PRINCIPAL DE BOOLEAN
# ════════════════════════════════════════════════════════════
def create_cutter_object(
    context,
    name,
    cutter_type='DOOR',
    width=0.90,
    height=2.10,
    sill_height=0.90,
    depth=0.50,
    source_obj=None
):
    """
    Crea el objeto cutter y lo configura.
    """
    cutter_name = f"{AF_CUTTER_PREFIX}{name}"

    if cutter_type == 'DOOR':
        bm = _generate_door_cutter_mesh(
            width=width, height=height, depth=depth,
        )
    elif cutter_type == 'WINDOW':
        bm = _generate_window_cutter_mesh(
            width=width, height=height,
            sill_height=sill_height, depth=depth,
        )
    else:
        bm = _generate_custom_cutter_mesh(
            width=width, height=height, depth=depth,
        )

    me  = bpy.data.meshes.new(cutter_name)
    bm.to_mesh(me)
    bm.free()
    me.update()

    cutter_obj = bpy.data.objects.new(cutter_name, me)
    context.collection.objects.link(cutter_obj)

    cutter_obj.display_type  = 'WIRE'
    cutter_obj.hide_render   = True
    cutter_obj.hide_viewport = False
    cutter_obj.show_in_front = True
    cutter_obj.color         = (1, 0.3, 0.1, 0.5)

    bm_props               = cutter_obj.archiforge_bool
    bm_props.is_af_cutter  = True
    bm_props.cutter_type   = cutter_type
    bm_props.source_object = source_obj.name if source_obj else ""

    # ── Parenting ────────────────────────────────────────────
    if source_obj:
        cutter_obj.matrix_world         = source_obj.matrix_world.copy()
        cutter_obj.parent               = source_obj
        cutter_obj.matrix_parent_inverse = source_obj.matrix_world.inverted()

    print(f"[ArchiForge] ✅ Cutter creado: {cutter_name}")
    return cutter_obj


def apply_boolean_to_wall(
    wall_obj,
    cutter_obj,
    mode='HYBRID',
    solver='EXACT'
):
    if wall_obj is None or cutter_obj is None:
        print("[ArchiForge] ❌ apply_boolean: wall o cutter es None")
        return None

    mod_name = f"{AF_BOOL_MOD_PREFIX}{cutter_obj.name}"

    existing = wall_obj.modifiers.get(mod_name)
    if existing:
        print(f"[ArchiForge] ℹ️  Modifier '{mod_name}' ya existe")
        return mod_name

    try:
        mod           = wall_obj.modifiers.new(name=mod_name, type='BOOLEAN')
        mod.operation = 'DIFFERENCE'
        mod.object    = cutter_obj
        mod.solver    = solver

        # ── FIX: activar self-intersection para muros multi-segmento ──
        # use_self=True evita que el solver EXACT falle cuando el muro
        # tiene geometría interna (segmentos que se tocan, solapes, etc.).
        if hasattr(mod, 'use_self'):
            mod.use_self = True
        if hasattr(mod, 'use_hole_tolerant'):
            mod.use_hole_tolerant = True

    except Exception as e:
        print(f"[ArchiForge] ❌ Error creando modifier Boolean: {e}")
        return None

    if mode in ('APPLY', 'DIRECT'):
        try:
            bpy.context.view_layer.objects.active = wall_obj
            bpy.ops.object.modifier_apply(modifier=mod_name)

            if mode == 'DIRECT':
                bpy.data.objects.remove(cutter_obj, do_unlink=True)
                return None

        except Exception as e:
            print(f"[ArchiForge] ❌ Error aplicando modifier: {e}")

    print(
        f"[ArchiForge] ✅ Boolean aplicado: "
        f"'{wall_obj.name}' ← '{cutter_obj.name}' ({mode})"
    )
    return mod_name


def register_cutter_on_source(source_obj, cutter_obj, wall_obj, mod_name):
    if source_obj is None:
        return
    bool_mgr            = source_obj.archiforge_bool
    entry               = bool_mgr.cutters.add()
    entry.cutter_name   = cutter_obj.name if cutter_obj else ""
    entry.wall_name     = wall_obj.name   if wall_obj   else ""
    entry.modifier_name = mod_name        if mod_name   else ""
    entry.active        = True


def remove_boolean_from_wall(wall_obj, mod_name, remove_cutter=False):
    if wall_obj is None:
        return
    mod = wall_obj.modifiers.get(mod_name)
    if mod:
        cutter = mod.object
        wall_obj.modifiers.remove(mod)
        if remove_cutter and cutter:
            bpy.data.objects.remove(cutter, do_unlink=True)


def clean_all_booleans_from_object(source_obj, remove_cutters=True):
    if source_obj is None:
        return
    bool_mgr = source_obj.archiforge_bool
    removed  = 0
    for entry in bool_mgr.cutters:
        if not entry.active:
            continue
        wall = bpy.data.objects.get(entry.wall_name)
        if wall and entry.modifier_name:
            remove_boolean_from_wall(
                wall_obj      = wall,
                mod_name      = entry.modifier_name,
                remove_cutter = remove_cutters,
            )
            removed += 1
    bool_mgr.cutters.clear()
    print(f"[ArchiForge] 🧹 {removed} booleans limpiados de '{source_obj.name}'")


def update_cutter_transform(source_obj):
    if source_obj is None:
        return
    for entry in source_obj.archiforge_bool.cutters:
        wall = bpy.data.objects.get(entry.wall_name)
        if wall:
            wall.data.update_tag()


# ════════════════════════════════════════════════════════════
#  FUNCIÓN PRINCIPAL — do_auto_boolean
# ════════════════════════════════════════════════════════════
def do_auto_boolean(
    context,
    source_obj,
    cutter_type='DOOR',
    width=0.90,
    height=2.10,
    sill_height=0.90,
    wall_obj=None,
    mode=None,
    solver=None
):
    """
    Función principal de Auto Boolean.
    Retorna dict con 'success', 'cutter', 'wall', 'modifier'.
    """
    result = {
        'success'  : False,
        'cutter'   : None,
        'wall'     : None,
        'modifier' : None,
    }

    # ── 1. Configuración ─────────────────────────────────────
    bool_mgr = source_obj.archiforge_bool
    if mode   is None: mode   = bool_mgr.mode
    if solver is None: solver = bool_mgr.solver

    # ── 2. Encontrar muro ────────────────────────────────────
    if wall_obj is None:
        wall_obj = find_nearest_wall(source_obj)

    if wall_obj is None:
        print(
            f"[ArchiForge] ⚠️  No se encontró muro cerca de "
            f"'{source_obj.name}' (radio: {AF_WALL_DETECT_DIST}m)"
        )
        result['success'] = True
        return result

    # ── 3. Profundidad del cutter ────────────────────────────
    if hasattr(wall_obj, 'archiforge_wall'):
        depth = wall_obj.archiforge_wall.width * 3.0
    else:
        depth = 0.60

    # ── 3.5 Baseline de polígonos (para verificar el corte) ──
    context.view_layer.update()
    poly_before = _eval_poly_count(wall_obj)

    # ── 4. Crear cutter ──────────────────────────────────────
    cutter_obj = create_cutter_object(
        context     = context,
        name        = source_obj.name,
        cutter_type = cutter_type,
        width       = width,
        height      = height,
        sill_height = sill_height,
        depth       = depth,
        source_obj  = source_obj,
    )

    if cutter_obj is None:
        print("[ArchiForge] ❌ do_auto_boolean: No se pudo crear el cutter")
        return result

    # ── 5. Actualizar depsgraph antes del boolean ─────────────
    context.view_layer.update()

    # ── 6. Aplicar boolean al muro ───────────────────────────
    mod_name = apply_boolean_to_wall(
        wall_obj   = wall_obj,
        cutter_obj = cutter_obj,
        mode       = mode,
        solver     = solver,
    )

    # ── 7. Verificar que el Boolean produjo geometría nueva ──
    context.view_layer.update()
    poly_after = _eval_poly_count(wall_obj)
    boolean_effective = poly_after > poly_before

    if not boolean_effective:
        print(
            f"[ArchiForge] ⚠️  Boolean sin efecto en '{wall_obj.name}' "
            f"(polys: {poly_before} → {poly_after}). "
            f"Posible causa: cutter fuera del muro, o geometría del muro "
            f"no manifold."
        )
    else:
        print(
            f"[ArchiForge] ✅ Boolean efectivo en '{wall_obj.name}' "
            f"(polys: {poly_before} → {poly_after})"
        )

    # ── 8. Registrar relación ────────────────────────────────
    if mode != 'DIRECT':
        register_cutter_on_source(
            source_obj = source_obj,
            cutter_obj = cutter_obj,
            wall_obj   = wall_obj,
            mod_name   = mod_name,
        )

    # ── 9. FIX: NO ocultar con hide_set(True) ────────────────
    # hide_set(True) rompía la evaluación del modificador Boolean
    # en algunas configuraciones de Blender 3.3, causando que uno de
    # los dos cortes no se aplicara. En su lugar, dejamos el cutter
    # visible pero con display_type='WIRE' y show_in_front=False
    # para que sea poco intrusivo.
    if cutter_obj and mode == 'HYBRID':
        cutter_obj.show_in_front = False

    # ── 10. Resultado ─────────────────────────────────────────
    result['success']  = boolean_effective
    result['cutter']   = cutter_obj
    result['wall']     = wall_obj
    result['modifier'] = mod_name

    if boolean_effective:
        print(
            f"[ArchiForge] ✅ Auto Boolean completado: "
            f"'{source_obj.name}' → '{wall_obj.name}' ({mode}/{solver})"
        )
    return result


# ════════════════════════════════════════════════════════════
#  OPERADORES
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_OT_auto_boolean(Operator):
    bl_idname      = "archiforge.auto_boolean"
    bl_label       = "Auto Boolean"
    bl_description = "Automatically cut openings in nearby walls"
    bl_options     = {'REGISTER', 'UNDO'}

    mode   : EnumProperty(name="Mode",   items=AF_BOOL_MODES,   default='HYBRID')
    solver : EnumProperty(name="Solver", items=AF_BOOL_SOLVERS, default='EXACT')

    @classmethod
    def poll(cls, context):
        return (
            context.mode == 'OBJECT'
            and len(context.selected_objects) > 0
        )

    def execute(self, context):
        processed = 0
        errors    = 0

        for obj in context.selected_objects:
            is_door   = (hasattr(obj, 'archiforge_door')
                         and obj.archiforge_door.is_af_door)
            is_window = (hasattr(obj, 'archiforge_window')
                         and obj.archiforge_window.is_af_window)

            if not (is_door or is_window):
                continue

            if is_door:
                props  = obj.archiforge_door
                result = do_auto_boolean(
                    context=context, source_obj=obj,
                    cutter_type='DOOR',
                    width=getattr(props, 'width',  0.90),
                    height=getattr(props, 'height', 2.10),
                    mode=self.mode, solver=self.solver,
                )
            else:
                props  = obj.archiforge_window
                result = do_auto_boolean(
                    context=context, source_obj=obj,
                    cutter_type='WINDOW',
                    width=getattr(props, 'width',       1.20),
                    height=getattr(props, 'height',      1.20),
                    sill_height=getattr(props, 'sill_height', 0.90),
                    mode=self.mode, solver=self.solver,
                )

            if result['success']:
                processed += 1
            else:
                errors += 1

        if processed > 0:
            self.report({'INFO'},
                        _tr("✅ Auto Boolean: {} objeto(s) procesado(s)")
                        .format(processed))
        elif errors > 0:
            self.report({'WARNING'},
                        _tr("⚠️  Auto Boolean: {} error(es). ¿Hay muros AF cerca?")
                        .format(errors))
        else:
            self.report({'WARNING'},
                        _tr("Selecciona puertas o ventanas ArchiForge primero"))

        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        col = layout.column(align=True)
        col.label(text="Boolean Settings", **_icon("boolean", 'MOD_BOOLEAN'))
        col.prop(self, "mode")
        col.prop(self, "solver")


class ARCHIFORGE_OT_boolean_clean(Operator):
    bl_idname      = "archiforge.boolean_clean"
    bl_label       = "Clean Booleans"
    bl_description = "Remove all boolean cuts from selected object"
    bl_options     = {'REGISTER', 'UNDO'}

    remove_cutters : BoolProperty(
        name="Remove Cutter Objects", default=True,
    )

    @classmethod
    def poll(cls, context):
        return (
            context.active_object is not None
            and context.active_object.type == 'MESH'
        )

    def execute(self, context):
        for obj in context.selected_objects:
            clean_all_booleans_from_object(
                source_obj=obj,
                remove_cutters=self.remove_cutters,
            )
        self.report({'INFO'}, _tr("✅ Booleans limpiados"))
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        self.layout.prop(self, "remove_cutters")


class ARCHIFORGE_OT_boolean_toggle_cutters(Operator):
    bl_idname      = "archiforge.boolean_toggle_cutters"
    bl_label       = "Toggle Cutter Visibility"
    bl_description = "Show or hide all ArchiForge cutter objects"
    bl_options     = {'REGISTER', 'UNDO'}

    show : BoolProperty(name="Show", default=True)

    def execute(self, context):
        count = 0
        for obj in bpy.data.objects:
            if (hasattr(obj, 'archiforge_bool')
                    and obj.archiforge_bool.is_af_cutter):
                obj.hide_set(not self.show)
                count += 1
        self.report({'INFO'}, (_tr("{} cutters shown") if self.show
                               else _tr("{} cutters hidden")).format(count))
        return {'FINISHED'}


class ARCHIFORGE_OT_boolean_add_cutter(Operator):
    bl_idname      = "archiforge.boolean_add_cutter"
    bl_label       = "Add Custom Cutter"
    bl_description = "Add a custom boolean cutter to the active wall"
    bl_options     = {'REGISTER', 'UNDO'}

    cutter_type : EnumProperty(
        name="Type",
        items=[('DOOR', "Door", ""), ('WINDOW', "Window", ""), ('CUSTOM', "Custom", "")],
        default='DOOR',
    )
    width  : FloatProperty(name="Width",       default=0.90, min=0.01, unit='LENGTH')
    height : FloatProperty(name="Height",      default=2.10, min=0.01, unit='LENGTH')
    sill   : FloatProperty(name="Sill Height", default=0.90, min=0.0,  unit='LENGTH')
    mode   : EnumProperty(name="Mode",   items=AF_BOOL_MODES,   default='HYBRID')
    solver : EnumProperty(name="Solver", items=AF_BOOL_SOLVERS, default='EXACT')

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj is not None and obj.type == 'MESH'
            and hasattr(obj, 'archiforge_wall')
            and obj.archiforge_wall.is_af_wall
        )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        col = layout.column(align=True)
        col.prop(self, "cutter_type")
        col.separator()
        col.prop(self, "width")
        col.prop(self, "height")
        if self.cutter_type == 'WINDOW':
            col.prop(self, "sill")
        col.separator()
        col.prop(self, "mode")
        col.prop(self, "solver")

    def execute(self, context):
        wall_obj = context.active_object

        if hasattr(wall_obj, 'archiforge_wall'):
            depth = wall_obj.archiforge_wall.width * 3.0
        else:
            depth = 0.60

        cutter = create_cutter_object(
            context     = context,
            name        = f"Custom.{self.cutter_type}",
            cutter_type = self.cutter_type,
            width       = self.width,
            height      = self.height,
            sill_height = self.sill,
            depth       = depth,
            source_obj  = None,
        )

        cutter.location = context.scene.cursor.location.copy()

        apply_boolean_to_wall(
            wall_obj=wall_obj, cutter_obj=cutter,
            mode=self.mode, solver=self.solver,
        )

        if self.mode == 'HYBRID':
            cutter.hide_set(False)
            bpy.ops.object.select_all(action='DESELECT')
            cutter.select_set(True)
            context.view_layer.objects.active = cutter

        self.report(
            {'INFO'},
            _tr("✅ Cutter '{}' añadido. Muévelo para posicionar el hueco.")
            .format(self.cutter_type)
        )
        return {'FINISHED'}


class ARCHIFORGE_OT_boolean_reassign(Operator):
    bl_idname      = "archiforge.boolean_reassign"
    bl_label       = "Reassign to Nearest Wall"
    bl_description = "Move boolean cuts to the nearest wall"
    bl_options     = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj is not None and obj.type == 'MESH'
            and hasattr(obj, 'archiforge_bool')
            and len(obj.archiforge_bool.cutters) > 0
        )

    def execute(self, context):
        source_obj = context.active_object
        bool_mgr   = source_obj.archiforge_bool
        new_wall   = find_nearest_wall(source_obj)

        if new_wall is None:
            self.report({'WARNING'}, _tr("No se encontró muro cercano"))
            return {'CANCELLED'}

        reassigned = 0
        for entry in bool_mgr.cutters:
            if not entry.active:
                continue
            old_wall = bpy.data.objects.get(entry.wall_name)
            cutter   = bpy.data.objects.get(entry.cutter_name)

            if old_wall and entry.modifier_name:
                mod = old_wall.modifiers.get(entry.modifier_name)
                if mod:
                    old_wall.modifiers.remove(mod)

            if cutter:
                new_mod = apply_boolean_to_wall(
                    wall_obj=new_wall, cutter_obj=cutter,
                    mode='HYBRID', solver=bool_mgr.solver,
                )
                entry.wall_name     = new_wall.name
                entry.modifier_name = new_mod or ""
                reassigned += 1

        self.report({'INFO'},
                    _tr("✅ {} boolean(s) reasignados a '{}'")
                    .format(reassigned, new_wall.name))
        return {'FINISHED'}


# ════════════════════════════════════════════════════════════
#  PANEL
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_PT_boolean(Panel):
    bl_label       = "Auto Boolean"
    bl_idname      = "ARCHIFORGE_PT_boolean"
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
        self.layout.label(text="", **_icon("boolean", 'MOD_BOOLEAN'))

    def draw(self, context):
        obj      = context.active_object
        layout   = self.layout
        layout.use_property_split = False
        bool_mgr = obj.archiforge_bool

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Settings", icon='PREFERENCES')
        col.prop(bool_mgr, "mode")
        col.prop(bool_mgr, "solver")

        layout.separator(factor=0.3)

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Actions", icon='TOOL_SETTINGS')

        row = col.row(align=True)
        row.operator(
            "archiforge.auto_boolean",
            text="Auto Boolean", **_icon("boolean", 'MOD_BOOLEAN'),
        ).mode = bool_mgr.mode

        col.separator(factor=0.3)
        col.operator("archiforge.boolean_add_cutter",
                     text="Add Custom Cutter", icon='ADD')
        col.operator("archiforge.boolean_reassign",
                     text="Reassign to Nearest Wall", icon='LINKED')

        if len(bool_mgr.cutters) > 0:
            layout.separator(factor=0.3)
            box = layout.box()
            col = box.column(align=True)
            col.label(
                text=f"Active Cuts ({len(bool_mgr.cutters)})",
                icon='MOD_BOOLEAN'
            )
            for entry in bool_mgr.cutters:
                row = col.row(align=True)
                row.label(text="", icon='CHECKMARK' if entry.active else 'X')
                wall = bpy.data.objects.get(entry.wall_name)
                row.label(
                    text=entry.wall_name,
                    icon='SNAP_FACE' if wall else 'ERROR'
                )

        layout.separator(factor=0.3)
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Cutter Visibility", icon='HIDE_OFF')
        row = col.row(align=True)
        row.operator("archiforge.boolean_toggle_cutters",
                     text="Show All", icon='HIDE_OFF').show = True
        row.operator("archiforge.boolean_toggle_cutters",
                     text="Hide All", icon='HIDE_ON').show  = False

        layout.separator(factor=0.3)
        layout.operator("archiforge.boolean_clean",
                        text="Clean All Booleans", icon='TRASH')


# ════════════════════════════════════════════════════════════
#  REGISTRO
# ════════════════════════════════════════════════════════════
classes = [
    AF_BooleanCutter,
    AF_BooleanManager,
    ARCHIFORGE_OT_auto_boolean,
    ARCHIFORGE_OT_boolean_clean,
    ARCHIFORGE_OT_boolean_toggle_cutters,
    ARCHIFORGE_OT_boolean_add_cutter,
    ARCHIFORGE_OT_boolean_reassign,
    ARCHIFORGE_PT_boolean,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Object.archiforge_bool = PointerProperty(
        type        = AF_BooleanManager,
        name        = "ArchiForge Boolean",
        description = "ArchiForge boolean system properties",
    )
    print("[ArchiForge] ✅ af_autoboolean — registered")


def unregister():
    if hasattr(bpy.types.Object, "archiforge_bool"):
        del bpy.types.Object.archiforge_bool

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    print("[ArchiForge] 🔴 af_autoboolean — unregistered")