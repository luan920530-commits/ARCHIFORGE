# -*- coding: utf-8 -*-
"""ArchiForge — Escaleras paramétricas con norma + rampas.

v1.0 — Blender 3.3 LTS.
Regla confort: 2R + T = 64 cm (auto). Baranda h=90 cm.
Origen en piso al arranque, ascenso hacia +Y (recta/L), rampa igual.
"""

import bpy
import math

from mathutils import Euler, Matrix, Vector
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)

try:
    from . import af_material
    from .af_objects_base import AF_ObjectBuilder
except ImportError:
    af_material = None
    AF_ObjectBuilder = None

AF_STAIR_PROP = "archiforge_stairs"
AF_STAIR_VERSION = 1

AF_STAIR_TYPES = [
    ('STRAIGHT', "Straight", "Escalera recta 1 tramo"),
    ('L_SHAPED', "L-Shaped", "Escalera en L con descanso"),
    ('SPIRAL', "Spiral", "Escalera caracol"),
    ('RAMP', "Ramp 8%", "Rampa accesible + barandas"),
]

AF_RAILING_SIDES = [
    ('BOTH', "Both", "Baranda ambos lados"),
    ('LEFT', "Left", "Baranda izquierda"),
    ('RIGHT', "Right", "Baranda derecha"),
    ('NONE', "None", "Sin baranda"),
]

AF_TREAD_STYLES = [
    ('CONCRETE', "Concrete", "Pasos en concreto"),
    ('WOOD', "Wood", "Pasos en madera"),
]

_SUSPEND = False


def af_stair_update(self, context):
    if _SUSPEND:
        return
    try:
        from .af_stairs import _find_stair_object as _find
        from .af_stairs import _rebuild_stair_mesh as _rb
    except ImportError:
        return
    props = self if hasattr(self, "is_af_stair") else None
    if props is None:
        return
    obj = _find(props)
    if obj is None:
        obj = context.active_object if context else None
    if obj is None or obj.type != 'MESH':
        return
    if not getattr(obj, AF_STAIR_PROP, None):
        return
    _rb(obj, props)


def stair_code_calc(total_rise):
    """n/R/T automáticos: R~17.5cm, 2R+T=64cm."""
    n = max(2, min(int(round(total_rise / 0.175)), 30))
    r = total_rise / n
    t = 0.64 - 2 * r
    t = max(0.22, min(t, 0.34))
    return n, r, t


class AF_StairsProperties(PropertyGroup):
    is_af_stair : BoolProperty(default=True, options={'HIDDEN'})
    object_name : StringProperty(default="", options={'HIDDEN'})
    af_version : IntProperty(default=AF_STAIR_VERSION,
                             options={'HIDDEN'})

    item_type : EnumProperty(name="Type", items=AF_STAIR_TYPES,
                             default='STRAIGHT',
                             update=af_stair_update)
    mesh_quality : EnumProperty(
        name="Quality",
        items=[('LOW', "Low", ""), ('MEDIUM', "Medium", ""),
               ('HIGH', "High", "")],
        default='MEDIUM', update=af_stair_update)

    total_rise : FloatProperty(name="Total Rise", default=2.40,
                               min=0.30, max=6.0, unit='LENGTH',
                               update=af_stair_update)
    width : FloatProperty(name="Width", default=1.00, min=0.60,
                          max=3.0, unit='LENGTH',
                          update=af_stair_update)
    auto_code : BoolProperty(name="Auto 2R+T=64", default=True,
                             update=af_stair_update)
    n_risers : IntProperty(name="Risers", default=14, min=2,
                           max=30, update=af_stair_update)
    riser_h : FloatProperty(name="Riser H", default=0.171,
                            min=0.10, max=0.25, unit='LENGTH',
                            update=af_stair_update)
    tread_d : FloatProperty(name="Tread D", default=0.28,
                            min=0.20, max=0.40, unit='LENGTH',
                            update=af_stair_update)
    tread_t : FloatProperty(name="Tread Thick.", default=0.05,
                            min=0.02, max=0.15, unit='LENGTH',
                            update=af_stair_update)
    closed_risers : BoolProperty(name="Closed Risers", default=True,
                                 update=af_stair_update)
    tread_style : EnumProperty(name="Tread Style",
                               items=AF_TREAD_STYLES,
                               default='CONCRETE',
                               update=af_stair_update)

    railing : EnumProperty(name="Railing", items=AF_RAILING_SIDES,
                           default='BOTH', update=af_stair_update)
    railing_height : FloatProperty(name="Rail Height", default=0.90,
                                   min=0.60, max=1.10,
                                   unit='LENGTH',
                                   update=af_stair_update)
    balusters : BoolProperty(name="Balusters", default=True,
                             update=af_stair_update)

    ramp_slope : FloatProperty(name="Ramp Slope", default=0.08,
                               min=0.02, max=0.20,
                               update=af_stair_update)
    ramp_landings : BoolProperty(name="End Landings", default=True,
                                 update=af_stair_update)

    mat_step : IntProperty(name="Step Mat", default=0, min=0,
                           max=7, update=af_stair_update)
    mat_metal : IntProperty(name="Metal Mat", default=1, min=0,
                            max=7, update=af_stair_update)
    mat_wood : IntProperty(name="Wood Mat", default=2, min=0,
                           max=7, update=af_stair_update)


class AF_StairGenerator:
    def __init__(self, props):
        self.props = props
        self.b = AF_ObjectBuilder()
        q = getattr(props, "mesh_quality", "MEDIUM")
        self._qf = {"LOW": 0.6, "MEDIUM": 1.15, "HIGH": 1.8}.get(q, 1.15)

    def seg(self, base):
        return max(8, int(base * self._qf))

    def dims(self):
        p = self.props
        if p.auto_code:
            return stair_code_calc(max(p.total_rise, 0.3))
        return (max(2, p.n_risers), max(p.riser_h, 0.1),
                max(p.tread_d, 0.2))

    def box_c(self, cx, cy, cz, sx, sy, sz, mi):
        self.b.box(cx - max(sx, 0.001) / 2, cx + max(sx, 0.001) / 2,
                   cy - max(sy, 0.001) / 2, cy + max(sy, 0.001) / 2,
                   cz - max(sz, 0.001) / 2, cz + max(sz, 0.001) / 2,
                   mi)

    def cyl(self, cx, cy, z0, z1, r, base_seg=16, mi=0):
        self.b.cylinder(cx, cy, z0, max(z1, z0 + 0.001),
                        max(r, 0.0012), segments=self.seg(base_seg),
                        mi=mi)

    def rbox(self, cx, cy, cz, sx, sy, sz, euler=(0, 0, 0), mi=0):
        m = Euler(euler, 'XYZ').to_matrix().to_4x4()
        m.translation = Vector((cx, cy, cz))
        self.b.box(-max(sx, 0.001) / 2, max(sx, 0.001) / 2,
                   -max(sy, 0.001) / 2, max(sy, 0.001) / 2,
                   -max(sz, 0.001) / 2, max(sz, 0.001) / 2,
                   mi, transform=m)

    def tube(self, p0, p1, r, base_seg=10, mi=0):
        a, b = Vector(p0), Vector(p1)
        d = b - a
        if d.length < 1e-6:
            return
        dn = d.normalized()
        if dn.dot(Vector((0, 0, 1))) < -0.9999:
            rot = Matrix.Rotation(math.pi, 3, 'X')
        else:
            rot = Vector((0, 0, 1)).rotation_difference(dn).to_matrix()
        m = rot.to_4x4()
        m.translation = a
        self.b.cylinder(0, 0, 0, d.length, max(r, 0.0008),
                        segments=self.seg(base_seg), mi=mi,
                        transform=m)

    def sides(self):
        r = self.props.railing
        if r == 'BOTH':
            return (-1, 1)
        if r == 'LEFT':
            return (-1,)
        if r == 'RIGHT':
            return (1,)
        return ()

    def _rail_flight(self, x, y0, z0b, y1, z1b, n, r_, t_,
                     met, yaw0=0.0):
        """Baranda inclinada: postes + pasamanos + balustres."""
        p = self.props
        rh = max(p.railing_height, 0.6)
        run = max(y1 - y0, 0.1)
        rise = z1b - z0b
        s = rise / run
        rail = lambda y: z0b + rh + s * (y - y0)
        self.tube((x, y0 - 0.30, rail(y0 - 0.30)),
                  (x, y1 + 0.30, rail(y1 + 0.30)), 0.025, 12,
                  met)
        self.tube((x, y0 - 0.30, rail(y0 - 0.30) - rh * 0.45),
                  (x, y1 + 0.30, rail(y1 + 0.30) - rh * 0.45),
                  0.015, 8, met)
        for py, pb in ((y0 - 0.25, z0b), ((y0 + y1) / 2,
                                          (z0b + z1b) / 2),
                       (y1 + 0.25, z1b)):
            self.box_c(x, py, (pb + rail(py)) / 2, 0.05, 0.05,
                       rail(py) - pb, met)
        if p.balusters:
            for i in range(n):
                by = y0 + i * t_ + t_ / 2
                if by > y1:
                    break
                bz = z0b + (i + 1) * r_
                self.box_c(x, by, (bz + rail(by) - 0.02) / 2,
                           0.018, 0.018, rail(by) - 0.02 - bz,
                           met)

    def _steps_run(self, x0, y0, z0, dx, dy, n, r_, t_, w,
                   step_mat, closed):
        """Tramo de n pasos hacia dirección (dx,dy)."""
        p = self.props
        tt = max(p.tread_t, 0.02)
        for i in range(n):
            cx = x0 + dx * (i * t_ + t_ / 2)
            cy = y0 + dy * (i * t_ + t_ / 2)
            zt = z0 + (i + 1) * r_
            sx = t_ + (0.02 if i > 0 else 0) if dx else w
            sy = t_ + (0.02 if i > 0 else 0) if dy else w
            ox = -dx * (0.01 if i > 0 else 0)
            oy = -dy * (0.01 if i > 0 else 0)
            self.box_c(cx + ox, cy + oy, zt - tt / 2, sx, sy,
                       tt, step_mat)
            if closed:
                rx = x0 + dx * i * t_
                ry = y0 + dy * i * t_
                self.box_c(rx, ry, z0 + i * r_ + r_ / 2,
                           0.025 if dx else w, w if dx else
                           0.025, r_, step_mat)

    # RECTA
    def _build_straight(self):
        p = self.props
        n, r_, t_ = self.dims()
        w = max(p.width, 0.6)
        h = n * r_
        run = n * t_
        step_mat = (p.mat_wood if p.tread_style == 'WOOD'
                    else p.mat_step)
        self._steps_run(0, 0, 0, 0, 1, n, r_, t_, w, step_mat,
                        p.closed_risers)
        ang = math.atan2(h, run)
        ln = math.hypot(run, h) + 0.3
        for sx in (-1, 1):
            self.rbox(sx * (w / 2 - 0.02), run / 2,
                      h / 2 - 0.12, 0.05, ln, 0.28,
                      euler=(ang, 0, 0), mi=p.mat_step)
        for sx in self.sides():
            self._rail_flight(sx * (w / 2 - 0.03), 0, 0, run,
                              h, n, r_, t_, p.mat_metal)

    # EN L
    def _build_l_shaped(self):
        p = self.props
        n, r_, t_ = self.dims()
        w = max(p.width, 0.6)
        n1 = max(2, n // 2)
        n2 = max(2, n - n1)
        h1 = n1 * r_
        h2 = h1 + n2 * r_
        run1, run2 = n1 * t_, n2 * t_
        step_mat = (p.mat_wood if p.tread_style == 'WOOD'
                    else p.mat_step)
        met = p.mat_metal
        rh = max(p.railing_height, 0.6)

        self._steps_run(0, 0, 0, 0, 1, n1, r_, t_, w, step_mat,
                        p.closed_risers)
        self.box_c(0, run1 + w / 2, h1 - 0.075, w, w, 0.15,
                   step_mat)
        self.box_c(0, run1 + w / 2, h1 / 2 - 0.075, w, w,
                   max(h1 - 0.15, 0.05), p.mat_step)
        self._steps_run(w / 2, run1 + w / 2, h1, 1, 0, n2, r_,
                        t_, w, step_mat, p.closed_risers)

        if p.railing != 'NONE':
            self._rail_flight(-(w / 2 - 0.03), 0, 0, run1, h1,
                              n1, r_, t_, met)
            x0, x1 = w / 2, w / 2 + run2
            yo = run1 + w - 0.03
            s = (h2 - h1) / max(run2, 0.1)
            rail = lambda x: h1 + rh + s * (x - x0)
            self.tube((x0 - 0.30, yo, rail(x0 - 0.30)),
                      (x1 + 0.30, yo, rail(x1 + 0.30)), 0.025,
                      12, met)
            self.tube((x0 - 0.30, yo, rail(x0 - 0.30) - rh *
                       0.45), (x1 + 0.30, yo,
                               rail(x1 + 0.30) - rh * 0.45),
                      0.015, 8, met)
            for px, pb in ((x0 - 0.25, h1), ((x0 + x1) / 2,
                                             (h1 + h2) / 2),
                           (x1 + 0.25, h2)):
                self.box_c(px, yo, (pb + rail(px)) / 2, 0.05,
                           0.05, rail(px) - pb, met)
            if p.balusters:
                for i in range(n2):
                    bx = x0 + i * t_ + t_ / 2
                    bz = h1 + (i + 1) * r_
                    self.box_c(bx, yo, (bz + rail(bx) - 0.02) /
                               2, 0.018, 0.018,
                               rail(bx) - 0.02 - bz, met)
            for px in (-w / 2 + 0.03, w / 2 - 0.03):
                self.box_c(px, yo, h1 + rh / 2, 0.05, 0.05,
                           rh, met)
            self.tube((-w / 2 + 0.03, yo, h1 + rh),
                      (x0 - 0.28, yo, rail(x0 - 0.30)), 0.025,
                      10, met)

    # CARACOL
    def _build_spiral(self):
        p = self.props
        n, r_, _t = self.dims()
        w = max(p.width, 0.7)
        h = n * r_
        step_mat = (p.mat_wood if p.tread_style == 'WOOD'
                    else p.mat_step)
        met = p.mat_metal
        rh = max(p.railing_height, 0.6)
        tt = max(p.tread_t, 0.02)
        r_in, r_out = 0.12, w
        a = 2 * math.pi / n
        rc = (r_in + r_out) / 2

        self.cyl(0, 0, 0, h + 0.10, 0.09, 18, met)
        self.cyl(0, 0, 0, 0.03, 0.20, 18, met)
        for i in range(n):
            th = i * a
            cx, cy = rc * math.cos(th), rc * math.sin(th)
            self.rbox(cx, cy, (i + 1) * r_ - tt / 2,
                      r_out - r_in + 0.06,
                      2 * rc * math.pi / n * 1.15, tt,
                      euler=(0, 0, th), mi=step_mat)
        if p.railing != 'NONE':
            k = n * 2
            prev = None
            for j in range(k + 1):
                th = j * a / 2
                rr = r_out - 0.03
                pt = (rr * math.cos(th), rr * math.sin(th),
                      (j / k) * h + rh)
                if prev is not None:
                    self.tube(prev, pt, 0.025, 8, met)
                prev = pt
            if p.balusters:
                for i in range(n):
                    th = i * a
                    rr = r_out - 0.05
                    bz = (i + 1) * r_
                    rz = ((i + 0.5) / n) * h + rh - 0.02
                    self.box_c(rr * math.cos(th),
                               rr * math.sin(th),
                               (bz + rz) / 2, 0.018, 0.018,
                               rz - bz, met)

    def generate(self):
        t = self.props.item_type
        if t == 'STRAIGHT':
            self._build_straight()
        elif t == 'L_SHAPED':
            self._build_l_shaped()
        elif t == 'SPIRAL':
            self._build_spiral()
        elif t == 'RAMP':
            self._build_ramp()
        return self.b

    # RAMPA 8%
    def _build_ramp(self):
        p = self.props
        h = max(p.total_rise, 0.2)
        w = max(p.width, 0.9)
        s = max(p.ramp_slope, 0.02)
        run = h / s
        met = p.mat_metal
        rh = max(p.railing_height, 0.6)
        land = 1.20 if p.ramp_landings else 0.0
        y0 = land

        self.box_c(0, land / 2, -0.075, w, land, 0.15,
                   p.mat_step)
        self.box_c(0, y0 + run + land / 2, h - 0.075, w, land,
                   0.15, p.mat_step)
        ang = math.atan2(h, run)
        ln = math.hypot(run, h)
        self.rbox(0, y0 + run / 2, h / 2 - 0.075, w, ln, 0.15,
                  euler=(ang, 0, 0), mi=p.mat_step)
        for sx in (-1, 1):
            self.rbox(sx * (w / 2 - 0.05), y0 + run / 2,
                      h / 2 + 0.05, 0.10, ln, 0.10,
                      euler=(ang, 0, 0), mi=p.mat_step)
        for sx in self.sides():
            x = sx * (w / 2 - 0.03)
            rail = lambda y: rh + s * (y - y0)
            self.tube((x, y0 - 0.30, rail(y0 - 0.30)),
                      (x, y0 + run + 0.30,
                       rail(y0 + run + 0.30)), 0.025, 12, met)
            self.tube((x, y0, 0.35 * rh + s * 0),
                      (x, y0 + run, h + 0.35 * rh), 0.015, 8,
                      met)
            for py in (y0 - 0.25, y0 + run / 2, y0 + run +
                       0.25):
                bz = max(0.0, min(h, s * (py - y0)))
                self.box_c(x, py, (bz + rail(py)) / 2, 0.05,
                           0.05, rail(py) - bz, met)


def _find_stair_object(props):
    name = props.object_name
    if name and name in bpy.data.objects:
        return bpy.data.objects[name]
    for obj in bpy.data.objects:
        if (obj.type == 'MESH' and hasattr(obj, AF_STAIR_PROP)
                and getattr(obj, AF_STAIR_PROP) is props):
            try:
                props.object_name = obj.name
            except Exception:
                pass
            return obj
    return None


def _rebuild_stair_mesh(obj, props):
    gen = AF_StairGenerator(props)
    builder = gen.generate()
    if builder is None:
        return
    builder.finalize(obj.data)
    mesh = obj.data
    if hasattr(mesh, "use_auto_smooth"):
        try:
            mesh.use_auto_smooth = True
            mesh.auto_smooth_angle = math.radians(35)
        except Exception:
            pass
    for poly in mesh.polygons:
        poly.use_smooth = True
    try:
        mesh.update()
    except Exception:
        pass


def _setup_stair_materials(obj):
    af_material.ensure_af_materials_for_object(obj, [
        "AF.Stair.Step", "AF.Stair.Metal", "AF.Stair.Wood",
    ])
    _tune_stair_materials()


def _tune_stair_materials():
    def _tune(name, base=None, metallic=None, rough=None):
        try:
            mat = bpy.data.materials.get(name)
            if mat is None:
                return
            mat.use_nodes = True
            bsdf = mat.node_tree.nodes.get("Principled BSDF")
            if bsdf is None:
                return
            inp = bsdf.inputs
            if base is not None and "Base Color" in inp:
                inp["Base Color"].default_value = base
            if metallic is not None and "Metallic" in inp:
                inp["Metallic"].default_value = metallic
            if rough is not None and "Roughness" in inp:
                inp["Roughness"].default_value = rough
        except Exception:
            pass

    _tune("AF.Stair.Step", base=(0.62, 0.62, 0.63, 1.0),
          metallic=0.0, rough=0.8)
    _tune("AF.Stair.Metal", base=(0.12, 0.12, 0.13, 1.0),
          metallic=0.9, rough=0.4)
    _tune("AF.Stair.Wood", base=(0.50, 0.34, 0.20, 1.0),
          metallic=0.0, rough=0.55)


def _create_stair_object(context, name="AF_Stair"):
    global _SUSPEND
    me = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, me)
    context.collection.objects.link(obj)
    try:
        obj.location = context.scene.cursor.location.copy()
    except Exception:
        pass
    context.view_layer.objects.active = obj
    obj.select_set(True)
    _SUSPEND = True
    try:
        props = obj.archiforge_stairs
        props.is_af_stair = True
        props.object_name = obj.name
        props.af_version = AF_STAIR_VERSION
    finally:
        _SUSPEND = False
    _setup_stair_materials(obj)
    return obj, props


class ARCHIFORGE_OT_stairs(Operator):
    bl_idname = "archiforge.stairs"
    bl_label = "Add AF Stair"
    bl_description = "Add a parametric ArchiForge stair/ramp"
    bl_options = {'REGISTER', 'UNDO'}

    item_type : EnumProperty(name="Type", items=AF_STAIR_TYPES,
                             default='STRAIGHT')
    total_rise : FloatProperty(name="Total Rise", default=2.40,
                               min=0.30, unit='LENGTH')
    width : FloatProperty(name="Width", default=1.00, min=0.60,
                          unit='LENGTH')

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        col = layout.column(align=True)
        col.label(text="New Stair / Ramp", icon='MESH_CUBE')
        col.prop(self, "item_type")
        col.separator()
        col.prop(self, "total_rise")
        col.prop(self, "width")

    def execute(self, context):
        global _SUSPEND
        obj, props = _create_stair_object(context, "AF_Stair")
        _SUSPEND = True
        try:
            props.item_type = self.item_type
            props.total_rise = self.total_rise
            props.width = self.width
        finally:
            _SUSPEND = False
        _rebuild_stair_mesh(obj, props)
        self.report({'INFO'}, f"Stair created: {obj.name}")
        return {'FINISHED'}


class ARCHIFORGE_OT_stairs_update(Operator):
    bl_idname = "archiforge.stairs_update"
    bl_label = "Update"
    bl_description = "Force regeneration of the stair"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH'
                and hasattr(obj, AF_STAIR_PROP)
                and obj.archiforge_stairs.is_af_stair)

    def execute(self, context):
        obj = context.active_object
        _rebuild_stair_mesh(obj, obj.archiforge_stairs)
        self.report({'INFO'}, "Stair updated")
        return {'FINISHED'}


class ARCHIFORGE_PT_stairs(Panel):
    bl_label = "Stair Properties"
    bl_idname = "ARCHIFORGE_PT_stairs"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "ArchiForge"
    bl_context = "objectmode"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH'
                and hasattr(obj, AF_STAIR_PROP)
                and obj.archiforge_stairs.is_af_stair)

    def draw_header(self, context):
        self.layout.label(text="", icon='MESH_CUBE')

    def draw(self, context):
        props = context.active_object.archiforge_stairs
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        t = props.item_type

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Type", icon='MODIFIER')
        col.prop(props, "item_type", text="")
        col.prop(props, "mesh_quality", text="Quality")

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Dimensions", icon='ARROW_LEFTRIGHT')
        col.prop(props, "total_rise")
        col.prop(props, "width")
        if t == 'RAMP':
            col.prop(props, "ramp_slope")
            col.prop(props, "ramp_landings")
            run = max(props.total_rise, 0.2) / max(
                props.ramp_slope, 0.02)
            col.label(text=f"Run needed: {run:.2f} m",
                      icon='INFO')
        else:
            col.prop(props, "auto_code")
            if props.auto_code:
                n, r_, t_ = stair_code_calc(
                    max(props.total_rise, 0.3))
                col.label(
                    text=f"{n} risers — R={r_*100:.1f} "
                         f"T={t_*100:.1f} cm", icon='INFO')
                col.label(text=f"2R+T = {(2*r_+t_)*100:.0f} cm",
                          icon='CHECKMARK')
                col.label(text=f"Run: {n*t_:.2f} m", icon='INFO')
            else:
                col.prop(props, "n_risers")
                col.prop(props, "riser_h")
                col.prop(props, "tread_d")
                v = (2 * props.riser_h + props.tread_d) * 100
                ok = 62 <= v <= 66
                col.label(text=f"2R+T = {v:.0f} cm "
                               f"({'OK' if ok else 'revisar'})",
                          icon='CHECKMARK' if ok else 'ERROR')
            col.prop(props, "tread_t")
            col.prop(props, "closed_risers")
            col.prop(props, "tread_style", text="")

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Railing", icon='MESH_CUBE')
        col.prop(props, "railing", text="")
        if props.railing != 'NONE':
            col.prop(props, "railing_height")
            if t != 'RAMP':
                col.prop(props, "balusters")

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Material Slots", icon='MATERIAL')
        col.prop(props, "mat_step", text="Step")
        col.prop(props, "mat_metal", text="Metal")
        col.prop(props, "mat_wood", text="Wood")

        layout.separator()
        layout.operator("archiforge.stairs_update",
                        text="Force Update", icon='FILE_REFRESH')


classes = [
    AF_StairsProperties,
    ARCHIFORGE_OT_stairs,
    ARCHIFORGE_OT_stairs_update,
    ARCHIFORGE_PT_stairs,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Object.archiforge_stairs = PointerProperty(
        type=AF_StairsProperties,
        name="ArchiForge Stair",
        description="ArchiForge stair properties",
    )
    print("[ArchiForge] af_stairs v1 - registered")


def unregister():
    if hasattr(bpy.types.Object, "archiforge_stairs"):
        del bpy.types.Object.archiforge_stairs
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    print("[ArchiForge] af_stairs - unregistered")
