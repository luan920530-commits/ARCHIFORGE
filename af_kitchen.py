# -*- coding: utf-8 -*-

# ╔══════════════════════════════════════════════════════════╗
# ║         ARCHIFORGE — af_kitchen.py  (v1.0)              ║
# ║         Cocina moderna: electrodomésticos y más         ║
# ║         GPL v3 — ArchiForge Devs                        ║
# ╚══════════════════════════════════════════════════════════╝
#
# v1.0 — 7 tipos: nevera, estufa+horno, campana, lavaplatos,
#   lavavajillas (puerta abatible + canastillas), microondas,
#   set de utensilios. Origen en piso, frente -Y.

# <pep8 compliant>

import bpy
import math

from mathutils import Vector, Matrix, Euler
from bpy.types import PropertyGroup, Operator, Panel
from bpy.props import (
    StringProperty, BoolProperty, IntProperty,
    FloatProperty, EnumProperty, PointerProperty,
)

from . import af_material
from .af_objects_base import AF_ObjectBuilder

try:
    from .af_i18n import tr_report as _tr
except ImportError:  # pragma: no cover - fuera del paquete
    def _tr(text):
        return text


AF_KIT_PROP = "archiforge_kitchen"
AF_KIT_VERSION = 1

AF_KIT_TYPES = [
    ('FRIDGE', "Fridge", "Nevera french-door + dispenser", 'MESH_CUBE', 0),
    ('STOVE', "Stove + Oven", "Estufa y horno",            'MESH_CUBE', 1),
    ('RANGE_HOOD', "Range Hood", "Campana tipo T",          'MESH_CUBE', 2),
    ('SINK_CABINET', "Kitchen Sink", "Lavaplatos + mueble", 'MESH_CUBE', 3),
    ('DISHWASHER', "Dishwasher", "Lavavajillas",            'MESH_CUBE', 4),
    ('MICROWAVE', "Microwave", "Microondas",               'MESH_CUBE', 5),
    ('UTENSILS', "Utensil Set", "Utensilios + tabla",       'MESH_CUBE', 6),
]

AF_QUALITY = [
    ('LOW', "Low", "Fast preview"), ('MEDIUM', "Medium", "Balanced"),
    ('HIGH', "High", "Dense presentation"),
]

AF_KIT_DEFAULTS = {
    'FRIDGE': (0.90, 0.75, 1.90),
    'STOVE': (0.76, 0.65, 0.95),
    'RANGE_HOOD': (0.90, 0.50, 1.00),
    'SINK_CABINET': (1.20, 0.60, 0.90),
    'DISHWASHER': (0.60, 0.60, 0.85),
    'MICROWAVE': (0.55, 0.40, 0.30),
    ('UTENSILS'): (0.50, 0.35, 0.35),
}

_SUSPEND = False


def af_kitchen_update(self, context):
    if _SUSPEND:
        return
    obj = _find_kitchen_object(self)
    if obj is None and context is not None:
        obj = getattr(context, "active_object", None)
    if obj is None or obj.type != 'MESH':
        return
    props = getattr(obj, AF_KIT_PROP, None)
    if props is None or not props.is_af_kitchen:
        return
    _rebuild_kitchen_mesh(obj, props)


class AF_KitchenProperties(PropertyGroup):

    is_af_kitchen : BoolProperty(default=True, options={'HIDDEN'})
    object_name : StringProperty(default="", options={'HIDDEN'})
    af_version : IntProperty(default=AF_KIT_VERSION, options={'HIDDEN'})

    item_type : EnumProperty(name="Item Type", items=AF_KIT_TYPES,
                             default='FRIDGE',
                             update=af_kitchen_update)
    mesh_quality : EnumProperty(name="Mesh Quality", items=AF_QUALITY,
                                default='MEDIUM',
                                update=af_kitchen_update)

    width : FloatProperty(name="Width", default=0.90, min=0.10, max=3.0,
                          unit='LENGTH', update=af_kitchen_update)
    depth : FloatProperty(name="Depth", default=0.75, min=0.10, max=3.0,
                          unit='LENGTH', update=af_kitchen_update)
    height : FloatProperty(name="Height", default=1.90, min=0.10, max=3.0,
                           unit='LENGTH', update=af_kitchen_update)

    dispenser : BoolProperty(name="Water/Ice Dispenser", default=True,
                             update=af_kitchen_update)
    burners : IntProperty(name="Burners", default=4, min=4, max=6,
                          update=af_kitchen_update)
    oven_window : BoolProperty(name="Oven Window", default=True,
                               update=af_kitchen_update)
    hood_lights : BoolProperty(name="Hood Lights", default=True,
                               update=af_kitchen_update)
    sink_bowls : IntProperty(name="Bowls", default=2, min=1, max=2,
                             update=af_kitchen_update)
    faucet_pro : BoolProperty(name="Pro Faucet", default=True,
                              update=af_kitchen_update)
    door_open : BoolProperty(name="Open Door", default=False,
                             update=af_kitchen_update)
    display_on : BoolProperty(name="Display On", default=True,
                              update=af_kitchen_update)
    kettle : BoolProperty(name="Kettle", default=True,
                          update=af_kitchen_update)
    board : BoolProperty(name="Cutting Board", default=True,
                         update=af_kitchen_update)
    tools : IntProperty(name="Tools", default=4, min=2, max=5,
                        update=af_kitchen_update)

    mat_steel : IntProperty(name="Steel", default=0, min=0)
    mat_cabinet : IntProperty(name="Cabinet", default=1, min=0)
    mat_glass : IntProperty(name="Glass", default=2, min=0)
    mat_emissive : IntProperty(name="Emissive", default=3, min=0)


class AF_KitchenGenerator:
    def __init__(self, props):
        self.props = props
        self.b = AF_ObjectBuilder()
        q = getattr(props, "mesh_quality", "MEDIUM")
        self._qf = {"LOW": 0.6, "MEDIUM": 1.15, "HIGH": 1.8}.get(q, 1.15)

    def seg(self, base):
        return max(8, int(base * self._qf))

    def rings(self, base):
        return max(6, int(base * self._qf))

    def box_c(self, cx, cy, cz, sx, sy, sz, mi):
        self.b.box(cx - max(sx, 0.001) / 2, cx + max(sx, 0.001) / 2,
                   cy - max(sy, 0.001) / 2, cy + max(sy, 0.001) / 2,
                   cz - max(sz, 0.001) / 2, cz + max(sz, 0.001) / 2,
                   mi)

    def cyl(self, cx, cy, z0, z1, r, base_seg=24, mi=0):
        self.b.cylinder(cx, cy, z0, max(z1, z0 + 0.001),
                        max(r, 0.0012), segments=self.seg(base_seg),
                        mi=mi)

    def cone(self, cx, cy, z0, z1, r0, r1, base_seg=24, mi=0,
             cap=True):
        try:
            self.b.cone(cx, cy, z0, max(z1, z0 + 0.001),
                        max(r0, 0.0012), max(r1, 0.0012),
                        segments=self.seg(base_seg), mi=mi, cap=cap)
        except TypeError:
            self.b.cone(cx, cy, z0, max(z1, z0 + 0.001),
                        max(r0, 0.0012), max(r1, 0.0012),
                        segments=self.seg(base_seg), mi=mi)

    def sph(self, cx, cy, cz, r, base_seg=20, base_rings=14, mi=0):
        self.b.sphere(cx, cy, cz, max(r, 0.0012),
                      segments=self.seg(base_seg),
                      rings=self.rings(base_rings), mi=mi)

    def tube(self, p0, p1, r, base_seg=16, mi=0, cap=True):
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
                        segments=self.seg(base_seg), mi=mi, cap=cap,
                        transform=m)

    def disc(self, center, direction, r, thickness, base_seg=18,
             mi=0):
        dn = Vector(direction)
        dn = dn.normalized() if dn.length > 1e-9 else Vector(
            (0, 0, 1))
        if dn.dot(Vector((0, 0, 1))) < -0.9999:
            rot = Matrix.Rotation(math.pi, 3, 'X')
        else:
            rot = Vector((0, 0, 1)).rotation_difference(dn).to_matrix()
        m = rot.to_4x4()
        m.translation = Vector(center) - dn * max(thickness,
                                                  0.001) / 2
        self.b.cylinder(0, 0, 0, max(thickness, 0.001),
                        max(r, 0.0008),
                        segments=self.seg(base_seg), mi=mi, cap=True,
                        transform=m)

    def rbox(self, cx, cy, cz, sx, sy, sz, euler=(0, 0, 0), mi=0):
        m = Euler(euler, 'XYZ').to_matrix().to_4x4()
        m.translation = Vector((cx, cy, cz))
        self.b.box(-max(sx, 0.001) / 2, max(sx, 0.001) / 2,
                   -max(sy, 0.001) / 2, max(sy, 0.001) / 2,
                   -max(sz, 0.001) / 2, max(sz, 0.001) / 2,
                   mi, transform=m)

    # NEVERA
    def _build_fridge(self):
        p = self.props
        st, cab = p.mat_steel, p.mat_cabinet
        gla, emi = p.mat_glass, p.mat_emissive
        w = max(p.width, 0.50)
        d = max(p.depth, 0.50)
        h = max(p.height, 1.20)
        yf = -d / 2

        self.box_c(0, 0, h / 2, w, d, h, st)
        self.box_c(0, yf + 0.10, 0.05, w - 0.06, 0.06, 0.10,
                   cab)
        for sx in (-1, 1):
            self.box_c(sx * (w / 2 - 0.05), 0, h - 0.015, 0.10,
                       d - 0.10, 0.03, cab)
        fz0, fz1 = h * 0.32, h - 0.02  # puertas french
        for sx in (-1, 1):
            xc = sx * w / 4
            self.box_c(xc, yf - 0.015, (fz0 + fz1) / 2, w / 2 -
                       0.015, 0.045, fz1 - fz0 - 0.01, st)
            self.box_c(xc, yf - 0.036, (fz0 + fz1) / 2, w / 2 -
                       0.06, 0.006, fz1 - fz0 - 0.06, st)
            hx = sx * 0.035
            self.tube((hx, yf - 0.085, fz0 + 0.12),
                      (hx, yf - 0.085, fz1 - 0.30), 0.014, 14,
                      st)
            for ez in (fz0 + 0.16, fz1 - 0.34):
                self.box_c(hx, yf - 0.060, ez, 0.025, 0.05,
                           0.025, st)
        # cajón congelador
        self.box_c(0, yf - 0.015, (0.10 + fz0) / 2, w - 0.02,
                   0.045, fz0 - 0.12, st)
        self.tube((-w / 2 + 0.10, yf - 0.075, fz0 - 0.06),
                  (w / 2 - 0.10, yf - 0.075, fz0 - 0.06), 0.013,
                  12, st)
        if p.dispenser:
            dx = -w / 4
            self.box_c(dx, yf - 0.030, h * 0.62, 0.20, 0.030,
                       0.30, cab)
            self.box_c(dx, yf - 0.042, h * 0.60, 0.14, 0.012,
                       0.20, st)
            self.box_c(dx, yf - 0.048, h * 0.60, 0.05, 0.014,
                       0.09, cab)
            self.box_c(dx, yf - 0.040, h * 0.62 + 0.185, 0.16,
                       0.008, 0.05,
                       emi if p.display_on else gla)
            self.box_c(dx, yf - 0.048, h * 0.62 - 0.13, 0.15,
                       0.016, 0.02, st)

    # ESTUFA + HORNO
    def _build_stove(self):
        p = self.props
        st, cab = p.mat_steel, p.mat_cabinet
        gla, emi = p.mat_glass, p.mat_emissive
        w = max(p.width, 0.50)
        d = max(p.depth, 0.45)
        h = max(p.height, 0.70)
        yf = -d / 2
        top = h - 0.10

        self.box_c(0, 0, top / 2, w, d, top, st)
        self.box_c(0, yf + 0.08, 0.05, w - 0.06, 0.05, 0.10,
                   cab)
        # cubierta + quemadores
        self.box_c(0, 0, top + 0.008, w + 0.01, d + 0.01, 0.016,
                   st)
        nb = 6 if p.burners >= 6 and w >= 0.85 else 4
        if nb == 4:
            pts = [(-0.22, 0.14), (0.22, 0.14), (-0.22, -0.14),
                   (0.22, -0.14)]
            rr = [0.075, 0.060, 0.060, 0.075]
        else:
            pts = [(-0.30, 0.14), (0, 0.14), (0.30, 0.14),
                   (-0.30, -0.14), (0, -0.14), (0.30, -0.14)]
            rr = [0.075, 0.055, 0.075, 0.060, 0.075, 0.060]
        for (fx, fz), br in zip(pts, rr):
            bx, bz = fx * w / 0.76, fz * d / 0.65
            self.disc((bx, bz, top + 0.020), (0, 0, 1), br +
                      0.035, 0.010, 26, st)
            for a in range(4):
                ang = a * math.pi / 2 + math.pi / 4
                self.box_c(bx + (br + 0.012) * math.cos(ang),
                           bz + (br + 0.012) * math.sin(ang),
                           top + 0.032, 0.028, 0.028, 0.018,
                           st)
            self.disc((bx, bz, top + 0.026), (0, 0, 1), br,
                      0.012, 24, cab)
            self.disc((bx, bz, top + 0.033), (0, 0, 1), br *
                      0.45, 0.010, 18, st)
        # perillas + respaldo + display
        for i in range(nb):
            kx = -w / 2 + 0.09 + i * (w - 0.18) / max(1, nb - 1)
            self.disc((kx, yf - 0.028, top - 0.055), (0, -1, 0),
                      0.020, 0.025, 16, cab)
            self.box_c(kx, yf - 0.042, top - 0.055, 0.005,
                       0.004, 0.022, emi if p.display_on else
                       st)
        self.box_c(0, d / 2 - 0.03, top + 0.06, w, 0.06, 0.14,
                   st)
        self.box_c(0, d / 2 - 0.062, top + 0.065, 0.22, 0.008,
                   0.06, emi if p.display_on else gla)
        # puerta horno + ventana + manija + cajón
        oz1 = top - 0.12
        self.box_c(0, yf - 0.012, (0.16 + oz1) / 2, w - 0.06,
                   0.035, oz1 - 0.16, st)
        if p.oven_window:
            self.box_c(0, yf - 0.030, (0.24 + oz1) / 2 - 0.03,
                       w * 0.62, 0.010, (oz1 - 0.24) * 0.62,
                       gla)
            self.box_c(0, yf - 0.036, (0.24 + oz1) / 2 - 0.03,
                       w * 0.50, 0.006, (oz1 - 0.24) * 0.42,
                       emi if p.display_on else cab)
        self.tube((-w / 2 + 0.08, yf - 0.060, oz1 - 0.045),
                  (w / 2 - 0.08, yf - 0.060, oz1 - 0.045),
                  0.013, 12, st)
        self.box_c(0, yf - 0.010, 0.13, w - 0.08, 0.025, 0.10,
                   st)

    # CAMPANA
    def _build_range_hood(self):
        p = self.props
        st, gla, emi = p.mat_steel, p.mat_glass, p.mat_emissive
        w = max(p.width, 0.50)
        d = max(p.depth, 0.35)
        h = max(p.height, 0.60)
        can_z = 0.55

        self.box_c(0, 0.05, (can_z + h) / 2, 0.30, 0.26,
                   h - can_z, st)
        self.box_c(0, 0.05, h - 0.02, 0.34, 0.30, 0.04, st)
        # visor vidrio + cenefa acero
        self.box_c(0, -0.02, can_z, w, d + 0.06, 0.025, st)
        self.box_c(0, -0.02, can_z + 0.032, w - 0.04, d, 0.014,
                   gla)
        for sx in (-1, 1):
            self.box_c(sx * (w / 2 - 0.10), -0.02, can_z - 0.012,
                       0.16, d - 0.12, 0.022, st)
            for i in range(4):
                self.box_c(sx * (w / 2 - 0.10) - 0.06 + i *
                           0.04, -0.02, can_z - 0.024, 0.018,
                           d - 0.16, 0.006, st)
        if p.hood_lights:
            for sx in (-1, 1):
                self.disc((sx * (w / 2 - 0.24), -0.02,
                           can_z - 0.014), (0, 0, -1), 0.032,
                          0.010, 18, emi)
                self.disc((sx * (w / 2 - 0.24), -0.02,
                           can_z - 0.008), (0, 0, -1), 0.040,
                          0.006, 18, st)
        self.box_c(w / 2 - 0.10, -0.02, can_z + 0.045, 0.14,
                   d - 0.10, 0.012, st)
        for i in range(3):
            self.disc((w / 2 - 0.145 + i * 0.045, -0.02,
                       can_z + 0.052), (0, 0, 1), 0.011, 0.008,
                      12, emi if p.display_on else st)

    # LAVAPLATOS
    def _build_sink_cabinet(self):
        p = self.props
        st, cab = p.mat_steel, p.mat_cabinet
        w = max(p.width, 0.60)
        d = max(p.depth, 0.45)
        top = max(p.height, 0.80)
        yf = -d / 2

        self.box_c(0, -0.02, 0.05, w - 0.10, d - 0.12, 0.10,
                   cab)
        self.box_c(0, 0, (0.10 + top - 0.03) / 2, w, d,
                   top - 0.13, cab)
        for sx in (-1, 1):
            xc = sx * w / 4
            self.box_c(xc, yf - 0.009, (0.10 + top - 0.03) / 2,
                       w / 2 - 0.03, 0.018, top - 0.19, cab)
            self.box_c(xc, yf - 0.028, top - 0.16, 0.16, 0.014,
                       0.014, st)
            for ex in (-0.06, 0.06):
                self.box_c(xc + ex, yf - 0.018, top - 0.16,
                           0.012, 0.022, 0.012, st)
        self.box_c(0, 0, top - 0.015, w + 0.02, d + 0.02, 0.030,
                   st)
        self.box_c(0, d / 2 - 0.01, top + 0.05, w + 0.02, 0.03,
                   0.10, st)
        # pocetas
        nb = max(1, min(p.sink_bowls, 2))
        bw = (w - 0.20) / nb
        for i in range(nb):
            xc = -w / 2 + 0.10 + bw * (i + 0.5)
            self.box_c(xc, 0, top + 0.002, bw - 0.02, d - 0.22,
                       0.012, st)
            self.cone(xc, 0, top - 0.16, top - 0.002,
                      min(bw, d) * 0.30, min(bw, d) * 0.38, 26,
                      st)
            self.cyl(xc, 0, top - 0.165, top - 0.155, 0.045, 18,
                     st)
            self.cyl(xc, 0, top - 0.160, top - 0.152, 0.020, 12,
                     cab)
        # grifería pro + dosificador
        fx = 0 if nb == 1 else 0
        self.cyl(fx, d / 2 - 0.10, top, top + 0.03, 0.026, 16,
                 st)
        sp_h = 0.30 if p.faucet_pro else 0.20
        self.cyl(fx, d / 2 - 0.10, top, top + sp_h, 0.017, 14,
                 st)
        self.tube((fx, d / 2 - 0.10, top + sp_h),
                  (fx, d / 2 - 0.30, top + sp_h - 0.02), 0.014,
                  12, st)
        self.cyl(fx, d / 2 - 0.30, top + sp_h - 0.055,
                 top + sp_h - 0.015, 0.016, 12, st)
        self.box_c(fx + 0.06, d / 2 - 0.06, top + 0.10, 0.014,
                   0.07, 0.014, st)
        self.cyl(w / 2 - 0.12, d / 2 - 0.10, top, top + 0.10,
                 0.022, 14, st)
        self.cyl(w / 2 - 0.12, d / 2 - 0.10, top + 0.10,
                 top + 0.13, 0.010, 10, st)

    # LAVAVAJILLAS
    def _build_dishwasher(self):
        p = self.props
        st, cab = p.mat_steel, p.mat_cabinet
        gla, emi = p.mat_glass, p.mat_emissive
        w = max(p.width, 0.45)
        d = max(p.depth, 0.45)
        h = max(p.height, 0.60)
        yf = -d / 2
        kick = 0.08

        self.box_c(0, 0, h / 2, w, d, h, st)
        self.box_c(0, yf + 0.06, kick / 2, w - 0.04, 0.05,
                   kick, cab)
        if not p.door_open:
            self.box_c(0, yf - 0.012, (kick + h) / 2, w - 0.02,
                       0.035, h - kick - 0.01, st)
            self.box_c(0, yf - 0.030, (kick + h) / 2, w - 0.08,
                       0.006, h - kick - 0.08, st)
        else:
            # puerta abatida + interior + canastillas
            self.rbox(0, yf - 0.30, kick + 0.02, w - 0.02, 0.035,
                      h - kick - 0.01, euler=(math.pi / 2 - 0.06,
                                             0, 0), mi=st)
            self.box_c(0, -0.02, (kick + h) / 2 - 0.02, w - 0.06,
                       d - 0.08, h - kick - 0.06, cab)
            for rz, rw in ((0.32, 0.20), (0.58, 0.16)):
                ry = kick + (h - kick) * rz
                self.box_c(0, -0.02, ry, w - 0.12, d - 0.16,
                           0.015, st)
                for i in range(7):
                    tx = -w / 2 + 0.08 + i * (w - 0.16) / 6
                    self.tube((tx, -0.02 - (d - 0.16) / 2, ry),
                              (tx, -0.02 + (d - 0.16) / 2, ry),
                              0.0035, 6, st)
                    self.tube((tx, -0.02, ry),
                              (tx + 0.02, -0.02, ry + rw),
                              0.003, 6, st)
                self.tube((0, -0.02 - (d - 0.16) / 2, ry +
                           0.01),
                          (0, -0.02 + (d - 0.16) / 2, ry +
                           0.01), 0.008, 8, st)
        # controles + display + manija
        self.box_c(0, yf - 0.030, h - 0.09, w - 0.10, 0.008,
                   0.07, cab)
        self.box_c(-w / 4, yf - 0.034, h - 0.09, 0.12, 0.006,
                   0.035, emi if p.display_on else gla)
        for i in range(3):
            self.disc((w / 4 - 0.05 + i * 0.05, yf - 0.034,
                       h - 0.09), (0, -1, 0), 0.011, 0.008, 12,
                      st)
        if not p.door_open:
            self.tube((-w / 2 + 0.08, yf - 0.055, h - 0.20),
                      (w / 2 - 0.08, yf - 0.055, h - 0.20),
                      0.012, 12, st)

    # MICROONDAS
    def _build_microwave(self):
        p = self.props
        st, cab = p.mat_steel, p.mat_cabinet
        gla, emi = p.mat_glass, p.mat_emissive
        w = max(p.width, 0.35)
        d = max(p.depth, 0.25)
        h = max(p.height, 0.20)
        yf = -d / 2

        for sx in (-1, 1):
            for sy in (-1, 1):
                self.cyl(sx * (w / 2 - 0.06),
                         sy * (d / 2 - 0.06), 0.0, 0.025, 0.020,
                         12, cab)
        self.box_c(0, 0, 0.025 + h / 2, w, d, h, st)
        for i in range(6):
            self.box_c(-w / 2 + 0.08 + i * 0.035, 0.02,
                       0.025 + h - 0.005, 0.018, d - 0.16,
                       0.006, cab)
        dw = w * 0.68
        self.box_c(-w / 2 + dw / 2, yf - 0.008,
                   0.025 + h / 2, dw, 0.030, h - 0.04, st)
        self.box_c(-w / 2 + dw / 2, yf - 0.024,
                   0.025 + h / 2, dw - 0.10, 0.008, h - 0.12,
                   gla)
        self.box_c(w / 2 - 0.035, yf - 0.030, 0.025 + h / 2,
                   0.020, 0.025, h - 0.10, st)
        px = w / 2 - (w - dw) / 2
        self.box_c(px, yf - 0.012, 0.025 + h - 0.09,
                   w - dw - 0.03, 0.010, 0.07,
                   emi if p.display_on else gla)
        for ri in range(3):
            for ci in range(3):
                self.box_c(px - 0.035 + ci * 0.035, yf - 0.014,
                           0.025 + h / 2 - 0.02 - ri * 0.035,
                           0.026, 0.008, 0.026, cab)
        self.disc((px, yf - 0.016, 0.025 + 0.07), (0, -1, 0),
                  0.024, 0.014, 18, st)

    # UTENSILIOS
    def _build_utensils(self):
        p = self.props
        st, cab = p.mat_steel, p.mat_cabinet
        w = max(p.width, 0.30)
        d = max(p.depth, 0.25)

        # portautensilios + herramientas
        hx, hy = -w / 2 + 0.10, 0.02
        self.cyl(hx, hy, 0.0, 0.16, 0.075, 26, st)
        self.cyl(hx, hy, 0.155, 0.165, 0.078, 26, st)
        tools = max(2, min(p.tools, 5))
        for i in range(tools):
            ang = -0.5 + i * (1.0 / max(1, tools - 1))
            tx = hx + math.sin(ang) * 0.16
            ty = hy + math.cos(ang * 0.5) * 0.02
            kind = i % 3
            self.tube((hx, hy, 0.10), (tx, ty, 0.36), 0.009, 10,
                      cab if kind != 1 else st)
            if kind == 0:  # cucharón
                self.sph(tx, ty, 0.375, 0.032, 16, 10, st)
                self.cyl(tx, ty, 0.375, 0.385, 0.030, 16, st)
            elif kind == 1:  # espátula
                self.box_c(tx, ty, 0.40, 0.055, 0.012, 0.10,
                           st)
            else:  # batidor
                self.cone(tx, ty, 0.36, 0.46, 0.012, 0.032, 12,
                          st)
                self.sph(tx, ty, 0.465, 0.012, 10, 8, st)
        if p.board:
            bx = hx + 0.24
            self.box_c(bx, hy, 0.012, 0.20, 0.30, 0.024, cab)
            self.cyl(bx, hy + 0.19, 0.012, 0.036, 0.045, 18,
                     cab)
            self.tube((bx - 0.05, hy - 0.02, 0.030),
                      (bx + 0.07, hy + 0.06, 0.030), 0.006, 8,
                      st)
            self.box_c(bx + 0.085, hy + 0.075, 0.028, 0.07,
                       0.025, 0.012, cab)
        if p.kettle:
            kx, ky = w / 2 - 0.11, 0.0
            self.cyl(kx, ky, 0.0, 0.02, 0.085, 26, st)
            self.cone(kx, ky, 0.02, 0.20, 0.085, 0.055, 28,
                      st)
            self.cyl(kx, ky, 0.20, 0.225, 0.055, 24, st)
            self.cyl(kx, ky, 0.225, 0.245, 0.025, 16, cab)
            self.sph(kx, ky, 0.250, 0.014, 12, 8, cab)
            self.tube((kx - 0.075, ky, 0.06),
                      (kx - 0.135, ky, 0.17), 0.014, 12, st)
            self.tube((kx - 0.06, ky, 0.225),
                      (kx - 0.06, ky, 0.30), 0.010, 10, cab)
            self.tube((kx + 0.06, ky, 0.225),
                      (kx + 0.06, ky, 0.30), 0.010, 10, cab)
            self.tube((kx - 0.06, ky, 0.30),
                      (kx + 0.06, ky, 0.30), 0.010, 10, cab)
            self.disc((kx, ky - 0.078, 0.10), (0, -1, 0),
                      0.018, 0.010, 14, cab)

    def generate(self):
        t = self.props.item_type
        if t == 'FRIDGE':
            self._build_fridge()
        elif t == 'STOVE':
            self._build_stove()
        elif t == 'RANGE_HOOD':
            self._build_range_hood()
        elif t == 'SINK_CABINET':
            self._build_sink_cabinet()
        elif t == 'DISHWASHER':
            self._build_dishwasher()
        elif t == 'MICROWAVE':
            self._build_microwave()
        elif t == 'UTENSILS':
            self._build_utensils()
        return self.b


def _find_kitchen_object(props):
    name = props.object_name
    if name and name in bpy.data.objects:
        return bpy.data.objects[name]
    for obj in bpy.data.objects:
        if (obj.type == 'MESH' and hasattr(obj, AF_KIT_PROP)
                and getattr(obj, AF_KIT_PROP) is props):
            try:
                props.object_name = obj.name
            except Exception:
                pass
            return obj
    return None


def _rebuild_kitchen_mesh(obj, props):
    gen = AF_KitchenGenerator(props)
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


def _setup_kitchen_materials(obj):
    af_material.ensure_af_materials_for_object(obj, [
        "AF.Kit.Steel", "AF.Kit.Cabinet", "AF.Kit.Glass",
        "AF.Kit.Emissive",
    ])
    _tune_kit_materials()


def _tune_kit_materials():
    def _tune(name, base=None, metallic=None, rough=None,
              emission=None, emission_strength=None,
              transmission=None):
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
            if transmission is not None and "Transmission" in inp:
                inp["Transmission"].default_value = transmission
            if emission is not None and "Emission" in inp:
                inp["Emission"].default_value = emission
            if (emission_strength is not None
                    and "Emission Strength" in inp):
                inp["Emission Strength"].default_value = \
                    emission_strength
        except Exception:
            pass

    _tune("AF.Kit.Steel", base=(0.75, 0.76, 0.78, 1.0),
          metallic=1.0, rough=0.28)
    _tune("AF.Kit.Cabinet", base=(0.16, 0.16, 0.17, 1.0),
          metallic=0.2, rough=0.5)
    _tune("AF.Kit.Glass", base=(0.05, 0.05, 0.06, 1.0),
          metallic=0.0, rough=0.08, transmission=0.6)
    _tune("AF.Kit.Emissive", base=(0.0, 0.0, 0.0, 1.0),
          emission=(0.55, 0.85, 1.0, 1.0), emission_strength=3.0)


def _create_kitchen_object(context, name="AF_Kitchen"):
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
        props = obj.archiforge_kitchen
        props.is_af_kitchen = True
        props.object_name = obj.name
        props.af_version = AF_KIT_VERSION
    finally:
        _SUSPEND = False
    _setup_kitchen_materials(obj)
    return obj, props


def _apply_type_defaults(props, item_type):
    global _SUSPEND
    w, d, h = AF_KIT_DEFAULTS.get(item_type, (0.6, 0.6, 0.9))
    _SUSPEND = True
    try:
        props.width = w
        props.depth = d
        props.height = h
    finally:
        _SUSPEND = False


class ARCHIFORGE_OT_kitchen(Operator):
    bl_idname = "archiforge.kitchen"
    bl_label = "Add AF Kitchen"
    bl_description = "Add a parametric ArchiForge kitchen item"
    bl_options = {'REGISTER', 'UNDO'}

    item_type : EnumProperty(name="Type", items=AF_KIT_TYPES,
                             default='FRIDGE')
    auto_dimensions : BoolProperty(name="Real-World Dimensions",
                                   default=True)
    width : FloatProperty(name="Width", default=0.90, min=0.05,
                          unit='LENGTH')
    depth : FloatProperty(name="Depth", default=0.75, min=0.05,
                          unit='LENGTH')
    height : FloatProperty(name="Height", default=1.90, min=0.05,
                           unit='LENGTH')

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        col = layout.column(align=True)
        col.label(text="New Kitchen Item", icon='MESH_CUBE')
        col.prop(self, "item_type")
        col.separator()
        col.prop(self, "auto_dimensions")
        sub = col.column(align=True)
        sub.enabled = not self.auto_dimensions
        sub.prop(self, "width")
        sub.prop(self, "depth")
        sub.prop(self, "height")

    def execute(self, context):
        global _SUSPEND
        obj, props = _create_kitchen_object(context, "AF_Kitchen")
        _SUSPEND = True
        try:
            props.item_type = self.item_type
            if self.auto_dimensions:
                _apply_type_defaults(props, self.item_type)
            else:
                props.width = self.width
                props.depth = self.depth
                props.height = self.height
        finally:
            _SUSPEND = False
        _rebuild_kitchen_mesh(obj, props)
        self.report({'INFO'}, _tr("Kitchen item created: {}").format(obj.name))
        return {'FINISHED'}


class ARCHIFORGE_OT_kitchen_update(Operator):
    bl_idname = "archiforge.kitchen_update"
    bl_label = "Update"
    bl_description = "Force regeneration of the kitchen item"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH'
                and hasattr(obj, AF_KIT_PROP)
                and obj.archiforge_kitchen.is_af_kitchen)

    def execute(self, context):
        obj = context.active_object
        _rebuild_kitchen_mesh(obj, obj.archiforge_kitchen)
        self.report({'INFO'}, _tr("Kitchen item updated"))
        return {'FINISHED'}


class ARCHIFORGE_OT_kitchen_reset(Operator):
    bl_idname = "archiforge.kitchen_reset"
    bl_label = "Reset Dimensions"
    bl_description = "Reset to real-world default dimensions"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH'
                and hasattr(obj, AF_KIT_PROP)
                and obj.archiforge_kitchen.is_af_kitchen)

    def execute(self, context):
        obj = context.active_object
        props = obj.archiforge_kitchen
        _apply_type_defaults(props, props.item_type)
        _rebuild_kitchen_mesh(obj, props)
        self.report({'INFO'}, _tr("Dimensions reset"))
        return {'FINISHED'}


class ARCHIFORGE_PT_kitchen(Panel):
    bl_label = "Kitchen Properties"
    bl_idname = "ARCHIFORGE_PT_kitchen"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "ArchiForge"
    bl_context = "objectmode"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH'
                and hasattr(obj, AF_KIT_PROP)
                and obj.archiforge_kitchen.is_af_kitchen)

    def draw_header(self, context):
        self.layout.label(text="", icon='MESH_CUBE')

    def draw(self, context):
        props = context.active_object.archiforge_kitchen
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
        col.prop(props, "width")
        col.prop(props, "depth")
        col.prop(props, "height")
        col.operator("archiforge.kitchen_reset",
                     text="Reset Real Dimensions", icon='LOOP_BACK')

        if t == 'FRIDGE':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Fridge", icon='MESH_CUBE')
            col.prop(props, "dispenser")
            col.prop(props, "display_on")

        if t == 'STOVE':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Stove", icon='MESH_CUBE')
            col.prop(props, "burners")
            col.prop(props, "oven_window")
            col.prop(props, "display_on")

        if t == 'RANGE_HOOD':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Hood", icon='LIGHT_HEM')
            col.prop(props, "hood_lights")
            col.prop(props, "display_on")

        if t == 'SINK_CABINET':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Sink", icon='SPHERE')
            col.prop(props, "sink_bowls")
            col.prop(props, "faucet_pro")

        if t == 'DISHWASHER':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Dishwasher", icon='MESH_CUBE')
            col.prop(props, "door_open")
            col.prop(props, "display_on")

        if t == 'MICROWAVE':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Microwave", icon='MESH_CUBE')
            col.prop(props, "display_on")

        if t == 'UTENSILS':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Utensils", icon='MESH_CUBE')
            col.prop(props, "tools")
            col.prop(props, "board")
            col.prop(props, "kettle")

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Material Slots", icon='MATERIAL')
        col.prop(props, "mat_steel", text="Steel")
        col.prop(props, "mat_cabinet", text="Cabinet")
        col.prop(props, "mat_glass", text="Glass")
        col.prop(props, "mat_emissive", text="Emissive")

        layout.separator()
        layout.operator("archiforge.kitchen_update",
                        text="Force Update", icon='FILE_REFRESH')


classes = [
    AF_KitchenProperties,
    ARCHIFORGE_OT_kitchen,
    ARCHIFORGE_OT_kitchen_update,
    ARCHIFORGE_OT_kitchen_reset,
    ARCHIFORGE_PT_kitchen,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Object.archiforge_kitchen = PointerProperty(
        type=AF_KitchenProperties,
        name="ArchiForge Kitchen",
        description="ArchiForge kitchen properties",
    )
    print("[ArchiForge] af_kitchen v1 - registered")


def unregister():
    if hasattr(bpy.types.Object, "archiforge_kitchen"):
        del bpy.types.Object.archiforge_kitchen
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    print("[ArchiForge] af_kitchen - unregistered")
