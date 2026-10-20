# -*- coding: utf-8 -*-

# ╔══════════════════════════════════════════════════════════╗
# ║         ARCHIFORGE — af_decor.py  (v1.0)                ║
# ║         Decoración: plantas, lámparas, arte y más       ║
# ║         GPL v3 — ArchiForge Devs                        ║
# ╚══════════════════════════════════════════════════════════╝
#
# v1.0 — 9 tipos: materas con plantas, lámparas pie/mesa,
#   floreros, cuadros, reloj, libros, TV, tapetes.
#   Piso: origen abajo. Pared (arte/reloj/TV-wall): origen
#   en superficie, +Y al ambiente, `mount_height` = centro.

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

try:
    from .af_icons import icon_kw as _icon, item_icon as _item_icon
except ImportError:  # pragma: no cover - fuera del paquete
    def _icon(name, fallback='MESH_CUBE', icons=None):
        return {'icon': fallback}

    def _item_icon(item_type, default=None):
        return default


AF_DECOR_PROP = "archiforge_decor"
AF_DECOR_VERSION = 1

AF_DECOR_TYPES = [
    ('PLANTER', "Planter + Plant", "Matera con planta",   'MESH_CUBE', 0),
    ('FLOOR_LAMP', "Floor Lamp", "Lámpara de pie",        'LIGHT',     1),
    ('TABLE_LAMP', "Table Lamp", "Lámpara de mesa",       'LIGHT',     2),
    ('VASE_SET', "Vase Set", "Floreros + flores",         'MESH_CUBE', 3),
    ('WALL_ART', "Wall Art", "Cuadro decorativo",         'MESH_CUBE', 4),
    ('CLOCK', "Wall Clock", "Reloj de pared (hora real)", 'MESH_CUBE', 5),
    ('BOOKS', "Books", "Libros apilados/fila",           'MESH_CUBE', 6),
    ('TV', "TV + Soundbar", "Televisor",                 'MESH_CUBE', 7),
    ('RUG', "Rug", "Tapete",                             'MESH_CUBE', 8),
]

AF_POTS = [
    ('TAPERED', "Tapered", "Tronco cónico"),
    ('CYLINDER', "Cylinder", "Cilíndrica"),
    ('BOWL', "Bowl", "Tipo bowl bajo"),
]

AF_PLANTS = [
    ('SNAKE', "Snake Plant", "Sansevieria vertical"),
    ('LEAFY', "Leafy Bush", "Follaje denso + tutor"),
    ('GRASS', "Grass", "Hierba plumosa"),
    ('PALM', "Palm", "Palma areca"),
]

AF_FULLNESS = [
    ('SPARSE', "Sparse", "Pocas hojas"),
    ('FULL', "Full", "Frondosa"),
    ('LUSH', "Lush", "Muy densa"),
]

AF_SHADES = [
    ('DRUM', "Drum", "Pantalla tambor"),
    ('CONE', "Cone", "Pantalla cónica"),
    ('GLOBE', "Globe", "Globo opalino"),
]

AF_ART = [
    ('ABSTRACT', "Abstract", "Bloques abstractos"),
    ('GEO', "Geometric", "Composición geométrica"),
    ('BOTANIC', "Botanic", "Motivo hoja"),
]

AF_FRAMES = [('BLACK', "Black", "Marco negro"),
             ('WHITE', "White", "Marco blanco")]

AF_ARRANGE = [('STACK', "Stack", "Pila horizontal"),
              ('ROW', "Row", "Fila vertical"),
              ('BOTH', "Both", "Pila + fila")]

AF_TV_SIZE = [('43', '43"', "109 cm"), ('50', '50"', "127 cm"),
              ('55', '55"', "140 cm"), ('65', '65"', "165 cm")]

AF_TV_MOUNT = [('WALL', "Wall Mount", "Soporte pared"),
               ('STAND', "Stand", "Base mueble")]

AF_RUG_SHAPE = [('RECT', "Rect", "Rectangular"),
                ('ROUND', "Round", "Redondo")]

AF_QUALITY = [
    ('LOW', "Low", "Fast preview"), ('MEDIUM', "Medium", "Balanced"),
    ('HIGH', "High", "Dense presentation"),
]

AF_DECOR_DEFAULTS = {
    'PLANTER': (0.35, 0.35, 0.95),
    'FLOOR_LAMP': (0.40, 0.40, 1.60),
    'TABLE_LAMP': (0.28, 0.28, 0.55),
    'VASE_SET': (0.45, 0.25, 0.60),
    'WALL_ART': (0.80, 0.06, 0.60),
    'CLOCK': (0.30, 0.05, 0.30),
    'BOOKS': (0.40, 0.25, 0.25),
    'TV': (1.25, 0.10, 0.75),
    'RUG': (1.60, 2.30, 0.02),
}

_SUSPEND = False


def af_decor_update(self, context):
    if _SUSPEND:
        return
    obj = _find_decor_object(self)
    if obj is None and context is not None:
        obj = getattr(context, "active_object", None)
    if obj is None or obj.type != 'MESH':
        return
    props = getattr(obj, AF_DECOR_PROP, None)
    if props is None or not props.is_af_decor:
        return
    _rebuild_decor_mesh(obj, props)


class AF_DecorProperties(PropertyGroup):

    is_af_decor : BoolProperty(default=True, options={'HIDDEN'})
    object_name : StringProperty(default="", options={'HIDDEN'})
    af_version : IntProperty(default=AF_DECOR_VERSION, options={'HIDDEN'})

    item_type : EnumProperty(name="Item Type", items=AF_DECOR_TYPES,
                             default='PLANTER',
                             update=af_decor_update)
    mesh_quality : EnumProperty(name="Mesh Quality", items=AF_QUALITY,
                                default='MEDIUM',
                                update=af_decor_update)

    width : FloatProperty(name="Width", default=0.35, min=0.03, max=4.0,
                          unit='LENGTH', update=af_decor_update)
    depth : FloatProperty(name="Depth", default=0.35, min=0.02, max=4.0,
                          unit='LENGTH', update=af_decor_update)
    height : FloatProperty(name="Height", default=0.95, min=0.02, max=4.0,
                           unit='LENGTH', update=af_decor_update)
    mount_height : FloatProperty(name="Mount Height", default=1.50,
                                 min=0.0, max=3.0, unit='LENGTH',
                                 update=af_decor_update)

    pot_style : EnumProperty(name="Pot", items=AF_POTS,
                             default='TAPERED', update=af_decor_update)
    plant : EnumProperty(name="Plant", items=AF_PLANTS,
                         default='LEAFY', update=af_decor_update)
    fullness : EnumProperty(name="Fullness", items=AF_FULLNESS,
                            default='FULL', update=af_decor_update)
    shade_style : EnumProperty(name="Shade", items=AF_SHADES,
                               default='DRUM', update=af_decor_update)
    flowers : BoolProperty(name="Flowers", default=True,
                           update=af_decor_update)
    art_style : EnumProperty(name="Art", items=AF_ART,
                             default='ABSTRACT', update=af_decor_update)
    frame_style : EnumProperty(name="Frame", items=AF_FRAMES,
                               default='BLACK', update=af_decor_update)
    hour : FloatProperty(name="Hour", default=10.0, min=1.0, max=12.0,
                         update=af_decor_update)
    minute : FloatProperty(name="Minute", default=10.0, min=0.0,
                           max=59.0, update=af_decor_update)
    seconds : BoolProperty(name="Second Hand", default=True,
                           update=af_decor_update)
    arrangement : EnumProperty(name="Arrangement", items=AF_ARRANGE,
                               default='BOTH', update=af_decor_update)
    book_count : IntProperty(name="Books", default=6, min=2, max=10,
                             update=af_decor_update)
    tv_size : EnumProperty(name="TV Size", items=AF_TV_SIZE,
                           default='55', update=af_decor_update)
    tv_mount : EnumProperty(name="Mount", items=AF_TV_MOUNT,
                            default='WALL', update=af_decor_update)
    tv_on : BoolProperty(name="Screen On", default=True,
                         update=af_decor_update)
    soundbar : BoolProperty(name="Soundbar", default=True,
                            update=af_decor_update)
    rug_shape : EnumProperty(name="Shape", items=AF_RUG_SHAPE,
                             default='RECT', update=af_decor_update)
    fringe : BoolProperty(name="Fringe", default=True,
                          update=af_decor_update)

    mat_ceramic : IntProperty(name="Ceramic", default=0, min=0)
    mat_metal : IntProperty(name="Metal", default=1, min=0)
    mat_glass : IntProperty(name="Glass", default=2, min=0)
    mat_emissive : IntProperty(name="Emissive", default=3, min=0)
    mat_leaf : IntProperty(name="Leaf", default=4, min=0)
    mat_fabric : IntProperty(name="Fabric", default=5, min=0)


class AF_DecorGenerator:
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

    def cone(self, cx, cy, z0, z1, r0, r1, base_seg=20, mi=0,
             cap=True):
        try:
            self.b.cone(cx, cy, z0, max(z1, z0 + 0.001),
                        max(r0, 0.0012), max(r1, 0.0012),
                        segments=self.seg(base_seg), mi=mi, cap=cap)
        except TypeError:
            self.b.cone(cx, cy, z0, max(z1, z0 + 0.001),
                        max(r0, 0.0012), max(r1, 0.0012),
                        segments=self.seg(base_seg), mi=mi)

    def sph(self, cx, cy, cz, r, base_seg=18, base_rings=12, mi=0):
        self.b.sphere(cx, cy, cz, max(r, 0.0012),
                      segments=self.seg(base_seg),
                      rings=self.rings(base_rings), mi=mi)

    def tor(self, cx, cy, cz, major, minor, base_seg=26,
            minor_seg=12, mi=0):
        self.b.torus(cx, cy, cz, max(major, 0.004),
                     max(minor, 0.0012),
                     major_segs=self.seg(base_seg),
                     minor_segs=max(6, int(minor_seg * self._qf)),
                     mi=mi)

    def rbox(self, cx, cy, cz, sx, sy, sz, euler=(0, 0, 0), mi=0):
        m = Euler(euler, 'XYZ').to_matrix().to_4x4()
        m.translation = Vector((cx, cy, cz))
        self.b.box(-max(sx, 0.001) / 2, max(sx, 0.001) / 2,
                   -max(sy, 0.001) / 2, max(sy, 0.001) / 2,
                   -max(sz, 0.001) / 2, max(sz, 0.001) / 2,
                   mi, transform=m)

    def tube(self, p0, p1, r, base_seg=10, mi=0, cap=True):
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

    def fleaf(self, pos, yaw, pitch, rx, ry, rz, mi):
        """Hoja elipsoide: yaw(Z) + pitch(X) + escala."""
        m = Matrix.Translation(Vector(pos))
        m = m @ Matrix.Rotation(yaw, 4, 'Z')
        m = m @ Matrix.Rotation(pitch, 4, 'X')
        m = m @ Matrix.Diagonal(Vector(
            (max(rx, 0.003), max(ry, 0.003), max(rz, 0.003),
             1.0)))
        self.b.sphere(0, 0, 0, 1.0, segments=self.seg(14),
                      rings=self.rings(10), mi=mi, transform=m)

    def blade(self, base, yaw, tilt, length, width, mi,
              flat=0.38):
        """Hoja cónica aplanada (sansevieria/hierba)."""
        m = Matrix.Translation(Vector(base))
        m = m @ Matrix.Rotation(yaw, 4, 'Z')
        m = m @ Matrix.Rotation(tilt, 4, 'X')
        m = m @ Matrix.Diagonal(Vector((1.0, flat, 1.0, 1.0)))
        self.b.cone(0, 0, 0, max(length, 0.02),
                    max(width / 2, 0.002), 0.003,
                    segments=self.seg(10), mi=mi, cap=True,
                    transform=m)

    # MATERA + PLANTA
    def _build_planter(self):
        p = self.props
        cer, met, leaf = (p.mat_ceramic, p.mat_metal,
                          p.mat_leaf)
        w = max(p.width, 0.15)
        h = max(p.height, 0.30)
        pot_h = h * 0.34
        r_top = w / 2

        self.cyl(0, 0, 0.0, 0.025, r_top + 0.03, 28, cer)
        if p.pot_style == 'TAPERED':
            self.cone(0, 0, 0.025, pot_h, r_top * 0.72, r_top,
                      30, cer)
        elif p.pot_style == 'CYLINDER':
            self.cyl(0, 0, 0.025, pot_h, r_top, 30, cer)
        else:  # BOWL
            self.cyl(0, 0, 0.025, pot_h * 0.8, r_top * 1.15, 30,
                     cer)
            self.cone(0, 0, pot_h * 0.8, pot_h, r_top * 1.15,
                      r_top, 30, cer)
        self.tor(0, 0, pot_h, r_top - 0.008, 0.018, 30, 12,
                 cer)
        self.cyl(0, 0, pot_h - 0.035, pot_h - 0.015,
                 r_top - 0.03, 24, met)
        soil_z = pot_h - 0.015
        plant_h = h - soil_z
        dens = {'SPARSE': 0.6, 'FULL': 1.0, 'LUSH': 1.45}.get(
            p.fullness, 1.0)

        if p.plant == 'SNAKE':
            n = max(5, int(10 * dens))
            for i in range(n):
                yaw = i * 2.39996
                rr = r_top * 0.28 * (0.4 + 0.6 * abs(math.sin(
                    i * 1.7)))
                tilt = 0.06 + 0.20 * abs(math.sin(i * 2.3))
                ln = plant_h * (0.55 + 0.45 * abs(math.cos(
                    i * 1.3)))
                self.blade((rr * math.cos(yaw), rr * math.sin(
                    yaw), soil_z), yaw + math.pi / 2, tilt, ln,
                           0.055 + 0.02 * abs(math.sin(i)), leaf)
        elif p.plant == 'GRASS':
            n = max(10, int(22 * dens))
            for i in range(n):
                yaw = i * 2.39996
                tilt = 0.12 + 0.42 * abs(math.sin(i * 1.9))
                ln = plant_h * (0.60 + 0.40 * abs(math.cos(
                    i * 2.7)))
                self.blade((0, 0, soil_z), yaw, tilt, ln,
                           0.016, leaf, flat=0.6)
                if i % 3 == 0:
                    tip_x = math.sin(tilt) * math.sin(yaw) * ln
                    tip_y = -math.sin(tilt) * math.cos(yaw) * ln
                    self.sph(tip_x, tip_y,
                             soil_z + math.cos(tilt) * ln,
                             0.014, 10, 8, leaf)
        elif p.plant == 'PALM':
            nf = max(4, int(7 * dens))
            for f in range(nf):
                yaw = f * 2 * math.pi / nf + 0.3
                dx, dy = math.cos(yaw), math.sin(yaw)
                rise = plant_h * (0.45 + 0.10 * math.sin(f * 3))
                reach = plant_h * 0.42
                p0 = (0, 0, soil_z)
                p1 = (dx * reach * 0.45, dy * reach * 0.45,
                      soil_z + rise)
                p2 = (dx * reach, dy * reach,
                      soil_z + rise - plant_h * 0.12)
                self.tube(p0, p1, 0.011, 8, leaf)
                self.tube(p1, p2, 0.007, 8, leaf)
                for k in range(5):
                    f_ = 0.15 + 0.7 * k / 4
                    lx = p1[0] + (p2[0] - p1[0]) * f_
                    ly = p1[1] + (p2[1] - p1[1]) * f_
                    lz = p1[2] + (p2[2] - p1[2]) * f_
                    for sgs in (-1, 1):
                        self.fleaf((lx, ly, lz),
                                   yaw + sgs * 1.05, -0.55,
                                   0.016, 0.085, 0.007, leaf)
                self.fleaf(p2, yaw, -0.9, 0.016, 0.10, 0.007,
                           leaf)
        else:  # LEAFY
            self.tube((0, 0, soil_z), (0, 0, soil_z + plant_h *
                                      0.80), 0.016, 10, met)
            for i in range(4):
                self.tor(0, 0, soil_z + plant_h * (0.2 + i *
                                                  0.15),
                         0.022, 0.007, 14, 8, met)
            n = max(8, int(16 * dens))
            for i in range(n):
                yaw = i * 2.39996
                f_ = 0.25 + 0.75 * (i % 4) / 3
                rr = r_top * (0.3 + f_ * 1.1)
                lz = soil_z + plant_h * (0.15 + 0.70 * f_ *
                                         abs(math.cos(i * 0.9)))
                sx = (rr * math.cos(yaw), rr * math.sin(yaw),
                      max(lz, soil_z + 0.03))
                self.tube((rr * 0.2 * math.cos(yaw),
                           rr * 0.2 * math.sin(yaw),
                           soil_z + plant_h * 0.1), sx, 0.006,
                          6, leaf)
                sc = 0.7 + 0.5 * abs(math.sin(i * 2.1))
                self.fleaf(sx, yaw + math.pi / 2,
                           -0.5 - 0.4 * abs(math.cos(i * 1.4)),
                           0.055 * sc, 0.10 * sc, 0.018, leaf)

    def _lamp_shade(self, cx, cy, z_bot, dia, style, fab, met,
                    gla, emi):
        r = dia / 2
        if style == 'DRUM':
            h = dia * 0.72
            self.cyl(cx, cy, z_bot, z_bot + h, r, 32, fab)
            self.tor(cx, cy, z_bot + 0.004, r - 0.002, 0.005,
                     32, 8, met)
            self.tor(cx, cy, z_bot + h - 0.004, r - 0.002,
                     0.005, 32, 8, met)
            self.cyl(cx, cy, z_bot + h - 0.02, z_bot + h -
                     0.012, r - 0.01, 28, gla)
            cz = z_bot + h * 0.45
        elif style == 'CONE':
            h = dia * 0.85
            self.cone(cx, cy, z_bot, z_bot + h, r, r * 0.55, 32,
                      fab)
            self.tor(cx, cy, z_bot + 0.004, r - 0.002, 0.005,
                     32, 8, met)
            cz = z_bot + h * 0.35
        else:  # GLOBE
            self.sph(cx, cy, z_bot + r, r, 30, 20, gla)
            self.cyl(cx, cy, z_bot - 0.01, z_bot + r * 0.3,
                     r * 0.30, 18, met)
            cz = z_bot + r
            h = r * 2
        self.cyl(cx, cy, cz - 0.035, cz + 0.005, 0.014, 12,
                 met)
        self.sph(cx, cy, cz + 0.030, 0.026, 16, 12, emi)
        self.tube((cx + r * 0.9, cy, z_bot + h * 0.5),
                  (cx + r * 0.9, cy, z_bot + h * 0.5 - 0.12),
                  0.003, 6, met)
        self.sph(cx + r * 0.9, cy, z_bot + h * 0.5 - 0.135,
                 0.009, 10, 8, met)
        return z_bot + h

    # LÁMPARA PIE
    def _build_floor_lamp(self):
        p = self.props
        met, fab = p.mat_metal, p.mat_fabric
        gla, emi = p.mat_glass, p.mat_emissive
        w = max(p.width, 0.20)
        h = max(p.height, 0.80)

        self.cyl(0, 0, 0.0, 0.025, 0.15, 30, met)
        self.cyl(0, 0, 0.025, 0.045, 0.05, 18, met)
        pole_top = h - w * 0.8
        self.cyl(0, 0, 0.04, pole_top, 0.014, 14, met)
        self.cyl(0, 0, pole_top - 0.06, pole_top + 0.02, 0.022,
                 14, met)
        self._lamp_shade(0, 0, pole_top - 0.02, w,
                         p.shade_style, fab, met, gla, emi)
        self.tube((0.10, 0, 0.01), (0.22, 0.10, 0.008), 0.006,
                  8, met)
        self.box_c(0.24, 0.12, 0.015, 0.07, 0.045, 0.025, met)

    # LÁMPARA MESA
    def _build_table_lamp(self):
        p = self.props
        met, fab = p.mat_metal, p.mat_fabric
        gla, emi = p.mat_glass, p.mat_emissive
        w = max(p.width, 0.15)
        h = max(p.height, 0.25)

        self.cyl(0, 0, 0.0, 0.020, w * 0.32, 26, met)
        self.cone(0, 0, 0.020, 0.075, w * 0.30, 0.035, 22,
                  met)
        stem_top = h - w * 0.85
        self.cyl(0, 0, 0.07, stem_top, 0.013, 12, met)
        self._lamp_shade(0, 0, stem_top - 0.02, w,
                         p.shade_style, fab, met, gla, emi)
        self.box_c(w * 0.30, 0, 0.045, 0.018, 0.024, 0.024,
                   met)

    # FLOREROS
    def _vase(self, cx, cy, r, h, cer):
        self.cyl(cx, cy, 0.0, 0.012, r * 0.62, 22, cer)
        self.cone(cx, cy, 0.012, h * 0.55, r * 0.60, r, 26,
                  cer)
        self.cone(cx, cy, h * 0.55, h * 0.88, r, r * 0.42, 26,
                  cer)
        self.cyl(cx, cy, h * 0.88, h, r * 0.42, 22, cer)
        self.tor(cx, cy, h, r * 0.42, 0.008, 24, 10, cer)
        return h

    def _flower(self, x, y, z_top, tilt, yaw, emi, leaf, met):
        self.tube((x, y, z_top - 0.30), (x, y, z_top), 0.005, 8,
                  leaf)
        self.fleaf((x, y, z_top - 0.12), yaw + 1.2, -0.7,
                   0.012, 0.05, 0.005, leaf)
        for k in range(6):
            ang = k * math.pi / 3
            self.fleaf((x + 0.028 * math.cos(ang),
                        y + 0.028 * math.sin(ang), z_top +
                        0.008), ang, -1.1, 0.016, 0.030, 0.006,
                       emi)
        self.sph(x, y, z_top + 0.012, 0.013, 12, 8, leaf)

    def _build_vase_set(self):
        p = self.props
        cer, met = p.mat_ceramic, p.mat_metal
        emi, leaf = p.mat_emissive, p.mat_leaf
        w = max(p.width, 0.25)
        h = max(p.height, 0.30)

        defs = [(-0.32, 0.30, 1.00), (0.0, 0.24, 0.78),
                (0.32, 0.27, 0.88)]
        for fx, fr, fh in defs:
            cx = fx * w / 0.45 * 0.45
            vh = self._vase(cx, 0, fr * w / 0.9 + 0.03, h * fh,
                            cer)
            if p.flowers:
                for s in range(2):
                    self._flower(cx + (s - 0.5) * 0.05,
                                 (s - 0.5) * 0.04, vh + 0.16 +
                                 s * 0.05, 0.12 * (s - 0.5),
                                 s * 2.1, emi, leaf, met)

    def disc(self, center, direction, r, thickness, base_seg=20,
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

    def ring(self, center, direction, major, minor, base_seg=28,
             minor_seg=10, mi=0):
        dn = Vector(direction)
        dn = dn.normalized() if dn.length > 1e-9 else Vector(
            (0, 0, 1))
        if dn.dot(Vector((0, 0, 1))) < -0.9999:
            rot = Matrix.Rotation(math.pi, 3, 'X')
        else:
            rot = Vector((0, 0, 1)).rotation_difference(dn).to_matrix()
        m = rot.to_4x4()
        m.translation = Vector(center)
        self.b.torus(0, 0, 0, max(major, 0.002),
                     max(minor, 0.0008),
                     major_segs=self.seg(base_seg),
                     minor_segs=max(6, int(minor_seg * self._qf)),
                     mi=mi, transform=m)

    # CUADRO (origen en pared, centro=mount)
    def _build_wall_art(self):
        p = self.props
        cer, met = p.mat_ceramic, p.mat_metal
        emi, leaf = p.mat_emissive, p.mat_leaf
        fab = p.mat_fabric
        w = max(p.width, 0.20)
        h = max(p.height, 0.20)
        cz = max(p.mount_height, 0.20)
        fr = met if p.frame_style == 'BLACK' else cer
        fw = 0.045

        self.box_c(0, 0.012, cz, w, 0.024, h, cer)
        self.box_c(0, 0.030, cz + h / 2 + fw / 2 - 0.005,
                   w + 2 * fw, 0.035, fw, fr)
        self.box_c(0, 0.030, cz - h / 2 - fw / 2 + 0.005,
                   w + 2 * fw, 0.035, fw, fr)
        for sx in (-1, 1):
            self.box_c(sx * (w / 2 + fw / 2), 0.030, cz, fw,
                       0.035, h, fr)
        self.box_c(0, 0.026, cz, w - 0.03, 0.008, h - 0.03,
                   cer)
        if p.art_style == 'ABSTRACT':
            self.box_c(-w * 0.16, 0.032, cz + h * 0.10,
                       w * 0.42, 0.008, h * 0.52, leaf)
            self.disc((w * 0.20, 0.036, cz - h * 0.08),
                      (0, 1, 0), min(w, h) * 0.20, 0.008, 26,
                      emi)
            self.rbox(-w * 0.05, 0.034, cz - h * 0.22, w * 0.30,
                      0.008, 0.05, euler=(0, 0, 0.35), mi=met)
        elif p.art_style == 'GEO':
            self.rbox(0, 0.032, cz + h * 0.05, w * 0.34,
                      0.008, w * 0.34, euler=(0, 0, math.pi / 4),
                      mi=fab)
            self.disc((-w * 0.22, 0.036, cz - h * 0.18),
                      (0, 1, 0), min(w, h) * 0.13, 0.008, 26,
                      met)
            self.box_c(w * 0.20, 0.034, cz - h * 0.16, 0.045,
                       0.008, h * 0.30, emi)
        else:  # BOTANIC
            self.box_c(0, 0.032, cz, w * 0.50, 0.006, h * 0.62,
                       fab)
            self.tube((0, 0.038, cz - h * 0.24),
                      (0, 0.038, cz + h * 0.24), 0.006, 8, leaf)
            for i in range(5):
                fz = cz - h * 0.16 + i * h * 0.08
                for sgs in (-1, 1):
                    self.fleaf((sgs * w * 0.09, 0.038, fz),
                               sgs * 1.1, -1.35, 0.020,
                               0.055 * (1 - i * 0.08), 0.006,
                               leaf)

    # RELOJ (hora paramétrica)
    def _build_clock(self):
        p = self.props
        cer, met, emi = (p.mat_ceramic, p.mat_metal,
                         p.mat_emissive)
        r = max(p.width, 0.12) / 2
        cz = max(p.mount_height, 0.20)
        fy = 0.030

        self.disc((0, 0.012, cz), (0, 1, 0), r, 0.024, 36, met)
        self.disc((0, fy, cz), (0, 1, 0), r - 0.012, 0.010, 36,
                  cer)
        self.ring((0, fy, cz), (0, 1, 0), r - 0.006, 0.008, 36,
                  10, met)
        for i in range(12):
            a = i * math.pi / 6
            big = i % 3 == 0
            tx = (r - 0.035) * math.sin(a)
            tz = cz + (r - 0.035) * math.cos(a)
            self.rbox(tx, fy + 0.006, tz, 0.010 if big else
                      0.006, 0.006, 0.034 if big else 0.020,
                      euler=(0, -a, 0), mi=met)
        hf = ((p.hour - 1) % 12 + p.minute / 60.0) / 12.0
        mf = (p.minute % 60) / 60.0
        self.rbox(0, fy + 0.010, cz + r * 0.14, 0.018, 0.006,
                  r * 0.52, euler=(0, -hf * 2 * math.pi, 0),
                  mi=met)
        self.rbox(0, fy + 0.014, cz + r * 0.20, 0.012, 0.006,
                  r * 0.72, euler=(0, -mf * 2 * math.pi, 0),
                  mi=met)
        if p.seconds:
            self.rbox(0, fy + 0.018, cz + r * 0.16, 0.005,
                      0.004, r * 0.80,
                      euler=(0, -mf * 2 * math.pi, 0), mi=emi)
        self.disc((0, fy + 0.016, cz), (0, 1, 0), 0.016, 0.012,
                  16, met)

    # LIBROS
    def _book(self, cx, cy, cz, sx, sy, sz, yaw, cover, pages):
        m = Matrix.Translation(Vector((cx, cy, cz)))
        m = m @ Matrix.Rotation(yaw, 4, 'Z')
        self.b.box(-sx / 2, sx / 2, -sy / 2, sy / 2, -sz / 2,
                   sz / 2, cover, transform=m)
        m2 = Matrix.Translation(Vector((cx + math.sin(yaw) *
                                        0.008, cy, cz)))
        m2 = m2 @ Matrix.Rotation(yaw, 4, 'Z')
        self.b.box(-sx / 2 + 0.006, sx / 2 - 0.002,
                   -sy / 2 + 0.006, sy / 2 - 0.006,
                   -sz / 2 + 0.004, sz / 2 - 0.004, pages,
                   transform=m2)

    def _build_books(self):
        p = self.props
        cer, met = p.mat_ceramic, p.mat_metal
        leaf, fab = p.mat_leaf, p.mat_fabric
        covers = [fab, leaf, met, cer]
        n = max(2, min(p.book_count, 10))

        if p.arrangement in ('STACK', 'BOTH'):
            z = 0.0
            ns = max(2, n // 2) if p.arrangement == 'BOTH' else n
            for i in range(ns):
                bw = 0.24 - 0.02 * abs(math.sin(i * 2.2))
                bd = 0.17 - 0.015 * abs(math.cos(i * 1.6))
                bh = 0.030 + 0.008 * abs(math.sin(i * 3.1))
                self._book(-0.14 if p.arrangement == 'BOTH'
                           else 0, 0, z + bh / 2, bw, bd, bh,
                           0.06 * math.sin(i * 4.0),
                           covers[i % 4], cer)
                z += bh
        if p.arrangement in ('ROW', 'BOTH'):
            x0 = 0.10 if p.arrangement == 'BOTH' else -n * 0.021
            for i in range(n if p.arrangement == 'ROW' else 5):
                bx = x0 + i * 0.042
                bh = 0.24 + 0.03 * math.sin(i * 1.8)
                lean = -0.20 if i == (
                    n - 1 if p.arrangement == 'ROW' else 4
                ) else 0.0
                if lean:
                    m = Matrix.Translation(Vector(
                        (bx + 0.03, 0, bh / 2)))
                    m = m @ Matrix.Rotation(lean, 4, 'Y')
                    self.b.box(-0.018, 0.018, -0.075, 0.075,
                               -bh / 2, bh / 2, covers[i % 4],
                               transform=m)
                else:
                    self._book(bx, 0, bh / 2, 0.036, 0.15, bh,
                               0.0, covers[i % 4], cer)
            ex = x0 + (n if p.arrangement == 'ROW' else 5
                       ) * 0.042 + 0.02
            self.box_c(ex, 0, 0.09, 0.015, 0.15, 0.18, met)
            self.box_c(ex + 0.045, 0, 0.008, 0.10, 0.15, 0.016,
                       met)

    # TV + SOUNDBAR
    def _build_tv(self):
        p = self.props
        met, gla, emi = (p.mat_metal, p.mat_glass,
                         p.mat_emissive)
        diag = {'43': 1.09, '50': 1.27, '55': 1.40, '65': 1.65
                }.get(p.tv_size, 1.40)
        w = diag * 0.8716
        h = diag * 0.4903
        screen = emi if p.tv_on else gla

        if p.tv_mount == 'WALL':
            cz = max(p.mount_height, 0.60)
            self.box_c(0, 0.02, cz, 0.40, 0.04, 0.30, met)
            for sx in (-1, 1):
                for sz in (-1, 1):
                    self.disc((sx * 0.15, 0.041, cz + sz *
                               0.10), (0, 1, 0), 0.012, 0.008,
                              12, met)
            self.box_c(0, 0.055, cz, w * 0.5, 0.03, 0.10, met)
            y0 = 0.075
        else:
            y0 = 0.06
            cz = y0 + 0.10 + h / 2
            for sx in (-1, 1):
                self.box_c(sx * w * 0.32, y0, 0.05, 0.05,
                           0.22, 0.10, met)
                self.box_c(sx * w * 0.32, y0, 0.10 + (cz - h /
                           2 - 0.10) / 2, 0.04, 0.04, cz - h /
                           2 - 0.10, met)
        self.box_c(0, y0 + 0.015, cz, w, 0.035, h, met)
        self.box_c(0, y0 + 0.034, cz, w - 0.03, 0.006, h -
                   0.03, screen)
        if p.tv_on:
            self.box_c(-w * 0.22, y0 + 0.038, cz + h * 0.12,
                       w * 0.30, 0.004, h * 0.22, gla)
            self.box_c(w * 0.25, y0 + 0.038, cz - h * 0.10,
                       w * 0.24, 0.004, 0.035, gla)
        self.box_c(0, y0 + 0.034, cz - h / 2 + 0.035, 0.10,
                   0.006, 0.018, met)
        self.disc((0, y0 + 0.036, cz - h / 2 + 0.035),
                  (0, 1, 0), 0.004, 0.004, 8, emi)
        if p.soundbar:
            by = y0 + 0.02
            bz = cz - h / 2 - 0.055
            if p.tv_mount == 'STAND':
                bz = max(bz, 0.075)
            self.box_c(0, by, bz, w * 0.72, 0.07, 0.065, met)
            for i in range(9):
                self.box_c(-w * 0.32 + i * w * 0.08, by +
                           0.036, bz, 0.030, 0.004, 0.030,
                           met)

    # TAPETE
    def _build_rug(self):
        p = self.props
        fab, cer = p.mat_fabric, p.mat_ceramic
        w = max(p.width, 0.40)
        d = max(p.depth, 0.40)

        if p.rug_shape == 'ROUND':
            r = min(w, d) / 2
            self.cyl(0, 0, 0.0, 0.012, r, 40, fab)
            self.cyl(0, 0, 0.012, 0.016, r - 0.07, 36, cer)
            self.cyl(0, 0, 0.016, 0.019, r - 0.14, 32, fab)
        else:
            self.box_c(0, 0, 0.006, w, d, 0.012, fab)
            self.box_c(0, 0, 0.011, w - 0.14, d - 0.14, 0.010,
                       cer)
            self.box_c(0, 0, 0.015, w - 0.28, d - 0.28, 0.008,
                       fab)
            if p.fringe:
                n = max(6, int(w / 0.05))
                for i in range(n):
                    fx = -w / 2 + w * (i + 0.5) / n
                    for sy in (-1, 1):
                        self.box_c(fx, sy * (d / 2 + 0.035),
                                   0.004, 0.018, 0.075, 0.006,
                                   cer)

    def generate(self):
        t = self.props.item_type
        if t == 'PLANTER':
            self._build_planter()
        elif t == 'FLOOR_LAMP':
            self._build_floor_lamp()
        elif t == 'TABLE_LAMP':
            self._build_table_lamp()
        elif t == 'VASE_SET':
            self._build_vase_set()
        elif t == 'WALL_ART':
            self._build_wall_art()
        elif t == 'CLOCK':
            self._build_clock()
        elif t == 'BOOKS':
            self._build_books()
        elif t == 'TV':
            self._build_tv()
        elif t == 'RUG':
            self._build_rug()
        return self.b


def _find_decor_object(props):
    name = props.object_name
    if name and name in bpy.data.objects:
        return bpy.data.objects[name]
    for obj in bpy.data.objects:
        if (obj.type == 'MESH' and hasattr(obj, AF_DECOR_PROP)
                and getattr(obj, AF_DECOR_PROP) is props):
            try:
                props.object_name = obj.name
            except Exception:
                pass
            return obj
    return None


def _rebuild_decor_mesh(obj, props):
    gen = AF_DecorGenerator(props)
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


def _setup_decor_materials(obj):
    af_material.ensure_af_materials_for_object(obj, [
        "AF.Decor.Ceramic", "AF.Decor.Metal", "AF.Decor.Glass",
        "AF.Decor.Emissive", "AF.Decor.Leaf", "AF.Decor.Fabric",
    ])
    _tune_decor_materials()


def _tune_decor_materials():
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
            # "Transmission"/"Emission" se llaman "Transmission Weight"/
            # "Emission Color" desde Blender 4.0: probar ambos nombres.
            for _name in ("Transmission", "Transmission Weight"):
                if transmission is not None and _name in inp:
                    inp[_name].default_value = transmission
                    break
            for _name in ("Emission", "Emission Color"):
                if emission is not None and _name in inp:
                    inp[_name].default_value = emission
                    break
            if (emission_strength is not None
                    and "Emission Strength" in inp):
                inp["Emission Strength"].default_value = \
                    emission_strength
        except Exception:
            pass

    _tune("AF.Decor.Ceramic", base=(0.92, 0.90, 0.86, 1.0),
          metallic=0.0, rough=0.35)
    _tune("AF.Decor.Metal", base=(0.10, 0.10, 0.11, 1.0),
          metallic=0.9, rough=0.4)
    _tune("AF.Decor.Glass", base=(0.95, 0.96, 0.94, 1.0),
          metallic=0.0, rough=0.05, transmission=0.9)
    _tune("AF.Decor.Emissive", base=(1.0, 0.95, 0.88, 1.0),
          emission=(1.0, 0.90, 0.75, 1.0), emission_strength=2.5)
    _tune("AF.Decor.Leaf", base=(0.16, 0.38, 0.14, 1.0),
          metallic=0.0, rough=0.7)
    _tune("AF.Decor.Fabric", base=(0.80, 0.76, 0.68, 1.0),
          metallic=0.0, rough=0.9)


def _create_decor_object(context, name="AF_Decor"):
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
        props = obj.archiforge_decor
        props.is_af_decor = True
        props.object_name = obj.name
        props.af_version = AF_DECOR_VERSION
    finally:
        _SUSPEND = False
    _setup_decor_materials(obj)
    return obj, props


def _apply_type_defaults(props, item_type):
    global _SUSPEND
    w, d, h = AF_DECOR_DEFAULTS.get(item_type, (0.4, 0.4, 0.6))
    _SUSPEND = True
    try:
        props.width = w
        props.depth = d
        props.height = h
    finally:
        _SUSPEND = False


class ARCHIFORGE_OT_decor(Operator):
    bl_idname = "archiforge.decor"
    bl_label = "Add AF Decor"
    bl_description = "Add a parametric ArchiForge decor item"
    bl_options = {'REGISTER', 'UNDO'}

    item_type : EnumProperty(name="Type", items=AF_DECOR_TYPES,
                             default='PLANTER')
    auto_dimensions : BoolProperty(name="Real-World Dimensions",
                                   default=True)
    width : FloatProperty(name="Width", default=0.35, min=0.02,
                          unit='LENGTH')
    depth : FloatProperty(name="Depth", default=0.35, min=0.02,
                          unit='LENGTH')
    height : FloatProperty(name="Height", default=0.95, min=0.02,
                           unit='LENGTH')

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        col = layout.column(align=True)
        col.label(text="New Decor Item",
                  **_icon(_item_icon(self.item_type, "decor"), 'MESH_CUBE'))
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
        obj, props = _create_decor_object(context, "AF_Decor")
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
        _rebuild_decor_mesh(obj, props)
        self.report({'INFO'}, _tr("Decor item created: {}").format(obj.name))
        return {'FINISHED'}


class ARCHIFORGE_OT_decor_update(Operator):
    bl_idname = "archiforge.decor_update"
    bl_label = "Update"
    bl_description = "Force regeneration of the decor item"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH'
                and hasattr(obj, AF_DECOR_PROP)
                and obj.archiforge_decor.is_af_decor)

    def execute(self, context):
        obj = context.active_object
        _rebuild_decor_mesh(obj, obj.archiforge_decor)
        self.report({'INFO'}, _tr("Decor item updated"))
        return {'FINISHED'}


class ARCHIFORGE_OT_decor_reset(Operator):
    bl_idname = "archiforge.decor_reset"
    bl_label = "Reset Dimensions"
    bl_description = "Reset to real-world default dimensions"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH'
                and hasattr(obj, AF_DECOR_PROP)
                and obj.archiforge_decor.is_af_decor)

    def execute(self, context):
        obj = context.active_object
        props = obj.archiforge_decor
        _apply_type_defaults(props, props.item_type)
        _rebuild_decor_mesh(obj, props)
        self.report({'INFO'}, _tr("Dimensions reset"))
        return {'FINISHED'}


class ARCHIFORGE_PT_decor(Panel):
    bl_label = "Decor Properties"
    bl_idname = "ARCHIFORGE_PT_decor"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "ArchiForge"
    bl_context = "objectmode"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH'
                and hasattr(obj, AF_DECOR_PROP)
                and obj.archiforge_decor.is_af_decor)

    def draw_header(self, context):
        self.layout.label(text="", **_icon("decor", 'MESH_CUBE'))

    def draw(self, context):
        props = context.active_object.archiforge_decor
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        t = props.item_type

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Type",
                  **_icon(_item_icon(props.item_type, "decor"), 'MODIFIER'))
        col.prop(props, "item_type", text="")
        col.prop(props, "mesh_quality", text="Quality")

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Dimensions", icon='ARROW_LEFTRIGHT')
        if t == 'TV':
            col.label(text="Size auto from inches")
        else:
            col.prop(props, "width")
            col.prop(props, "depth")
            col.prop(props, "height")
        if t in ('WALL_ART', 'CLOCK', 'TV'):
            col.prop(props, "mount_height")
        col.operator("archiforge.decor_reset",
                     text="Reset Real Dimensions", icon='LOOP_BACK')

        if t == 'PLANTER':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Planter",
                      **_icon(_item_icon(t, "decor"), 'MESH_CUBE'))
            col.prop(props, "pot_style", text="")
            col.prop(props, "plant", text="")
            col.prop(props, "fullness", text="")

        if t in ('FLOOR_LAMP', 'TABLE_LAMP'):
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Lamp",
                      **_icon(_item_icon(t, "decor"), 'LIGHT'))
            col.prop(props, "shade_style", text="")

        if t == 'VASE_SET':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Vases",
                      **_icon(_item_icon(t, "decor"), 'MESH_CUBE'))
            col.prop(props, "flowers")

        if t == 'WALL_ART':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Art",
                      **_icon(_item_icon(t, "decor"), 'MESH_CUBE'))
            col.prop(props, "art_style", text="")
            col.prop(props, "frame_style", text="")

        if t == 'CLOCK':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Time",
                      **_icon(_item_icon(t, "decor"), 'TIME'))
            col.prop(props, "hour")
            col.prop(props, "minute")
            col.prop(props, "seconds")

        if t == 'BOOKS':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Books",
                      **_icon(_item_icon(t, "decor"), 'MESH_CUBE'))
            col.prop(props, "arrangement", text="")
            col.prop(props, "book_count")

        if t == 'TV':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="TV",
                      **_icon(_item_icon(t, "decor"), 'MESH_CUBE'))
            col.prop(props, "tv_size", text="")
            col.prop(props, "tv_mount", text="")
            col.prop(props, "tv_on")
            col.prop(props, "soundbar")

        if t == 'RUG':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Rug",
                      **_icon(_item_icon(t, "decor"), 'MESH_CUBE'))
            col.prop(props, "rug_shape", text="")
            if props.rug_shape == 'RECT':
                col.prop(props, "fringe")

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Material Slots", icon='MATERIAL')
        col.prop(props, "mat_ceramic", text="Ceramic")
        col.prop(props, "mat_metal", text="Metal")
        col.prop(props, "mat_glass", text="Glass")
        col.prop(props, "mat_emissive", text="Emissive")
        if t in ('PLANTER', 'VASE_SET', 'WALL_ART'):
            col.prop(props, "mat_leaf", text="Leaf")
        if t in ('FLOOR_LAMP', 'TABLE_LAMP', 'BOOKS', 'RUG',
                 'WALL_ART'):
            col.prop(props, "mat_fabric", text="Fabric")

        layout.separator()
        layout.operator("archiforge.decor_update",
                        text="Force Update", icon='FILE_REFRESH')


classes = [
    AF_DecorProperties,
    ARCHIFORGE_OT_decor,
    ARCHIFORGE_OT_decor_update,
    ARCHIFORGE_OT_decor_reset,
    ARCHIFORGE_PT_decor,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Object.archiforge_decor = PointerProperty(
        type=AF_DecorProperties,
        name="ArchiForge Decor",
        description="ArchiForge decor properties",
    )
    print("[ArchiForge] af_decor v1 - registered")


def unregister():
    if hasattr(bpy.types.Object, "archiforge_decor"):
        del bpy.types.Object.archiforge_decor
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    print("[ArchiForge] af_decor - unregistered")
