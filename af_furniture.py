# -*- coding: utf-8 -*-

# ╔══════════════════════════════════════════════════════════╗
# ║         ARCHIFORGE — af_furniture.py  (v1.0)            ║
# ║         Muebles modernos estilo Colombia                ║
# ║         GPL v3 — ArchiForge Devs                        ║
# ╚══════════════════════════════════════════════════════════╝
#
# v1.0 — 10 tipos: sillas comedor/oficina, poltrona, sofá,
#   mesas centro/comedor, cama, nochero, chifonier, biblioteca.
#   Medidas colombianas (sencilla/semidoble/doble/queen/king).
#   Origen en piso, frente -Y, respaldo/fondo +Y.

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


AF_FURN_PROP = "archiforge_furniture"
AF_FURN_VERSION = 1

AF_FURN_TYPES = [
    ('DINING_CHAIR', "Dining Chair", "Modern dining chair",     'MESH_CUBE', 0),
    ('OFFICE_CHAIR', "Office Chair", "5-star office chair",     'MESH_CUBE', 1),
    ('ARMCHAIR',     "Armchair",     "Sillon / armchair",       'MESH_CUBE', 2),
    ('SOFA',         "Sofa",         "2-4 seat sofa + chaise",  'MESH_CUBE', 3),
    ('COFFEE_TABLE', "Coffee Table", "Mesa de centro",          'MESH_CUBE', 4),
    ('DINING_TABLE', "Dining Table", "Mesa de comedor",         'MESH_CUBE', 5),
    ('BED',          "Bed",          "Cama + tendido completo", 'MESH_CUBE', 6),
    ('NIGHTSTAND',   "Nightstand",   "Nochero",                 'MESH_CUBE', 7),
    ('DRESSER',      "Dresser",      "Chifonier / comoda",      'MESH_CUBE', 8),
    ('SHELF',        "Bookshelf",    "Biblioteca modular",      'MESH_CUBE', 9),
]

AF_SEAT = [
    ('WOOD', "Wood Seat", "Molded wood seat"),
    ('UPHOLSTERED', "Upholstered", "Fabric cushion seat"),
]

AF_BED_SIZES = [
    ('SINGLE', "Sencilla 100x190", "100 x 190 cm"),
    ('SEMIDOUBLE', "Semidoble 120x190", "120 x 190 cm"),
    ('DOUBLE', "Doble 140x190", "140 x 190 cm"),
    ('QUEEN', "Queen 160x200", "160 x 200 cm"),
    ('KING', "King 200x200", "200 x 200 cm"),
]

AF_BED_INNER = {
    'SINGLE': (1.00, 1.90), 'SEMIDOUBLE': (1.20, 1.90),
    'DOUBLE': (1.40, 1.90), 'QUEEN': (1.60, 2.00), 'KING': (2.00, 2.00),
}

AF_HEADBOARD = [
    ('PANEL', "Panel", "Full panel + insets"),
    ('UPHOLSTERED', "Upholstered", "Tufted with buttons"),
    ('SLATS', "Slats", "Horizontal slats"),
]

AF_TOP_SHAPE = [
    ('RECT', "Rectangular", "Rectangular top"),
    ('ROUND', "Round", "Round top"),
]

AF_QUALITY = [
    ('LOW', "Low", "Fast preview"), ('MEDIUM', "Medium", "Balanced"),
    ('HIGH', "High", "Dense presentation"),
]

AF_FURN_DEFAULTS = {
    'DINING_CHAIR': (0.46, 0.52, 0.86),
    'OFFICE_CHAIR': (0.62, 0.62, 1.12),
    'ARMCHAIR': (0.74, 0.80, 0.90),
    'SOFA': (2.10, 0.92, 0.86),
    'COFFEE_TABLE': (1.10, 0.60, 0.40),
    'DINING_TABLE': (1.60, 0.90, 0.75),
    'BED': (1.70, 2.15, 1.15),
    'NIGHTSTAND': (0.45, 0.40, 0.55),
    'DRESSER': (1.20, 0.45, 0.82),
    'SHELF': (1.20, 0.32, 1.90),
}

_SUSPEND = False


def af_furniture_update(self, context):
    if _SUSPEND:
        return
    obj = _find_furniture_object(self)
    if obj is None and context is not None:
        obj = getattr(context, "active_object", None)
    if obj is None or obj.type != 'MESH':
        return
    props = getattr(obj, AF_FURN_PROP, None)
    if props is None or not props.is_af_furniture:
        return
    _rebuild_furniture_mesh(obj, props)


class AF_FurnitureProperties(PropertyGroup):

    is_af_furniture : BoolProperty(default=True, options={'HIDDEN'})
    object_name : StringProperty(default="", options={'HIDDEN'})
    af_version : IntProperty(default=AF_FURN_VERSION, options={'HIDDEN'})

    item_type : EnumProperty(name="Item Type", items=AF_FURN_TYPES,
                             default='DINING_CHAIR',
                             update=af_furniture_update)
    mesh_quality : EnumProperty(name="Mesh Quality", items=AF_QUALITY,
                                default='MEDIUM',
                                update=af_furniture_update)

    width : FloatProperty(name="Width", default=0.46, min=0.05, max=4.0,
                          unit='LENGTH', update=af_furniture_update)
    depth : FloatProperty(name="Depth", default=0.52, min=0.05, max=4.0,
                          unit='LENGTH', update=af_furniture_update)
    height : FloatProperty(name="Height", default=0.86, min=0.05, max=3.0,
                           unit='LENGTH', update=af_furniture_update)

    # sillas comedor
    seat_height : FloatProperty(name="Seat Height", default=0.45,
                                min=0.25, max=0.80, unit='LENGTH',
                                update=af_furniture_update)
    seat_style : EnumProperty(name="Seat", items=AF_SEAT,
                              default='UPHOLSTERED',
                              update=af_furniture_update)
    chair_cushion : BoolProperty(name="Back Cushion", default=True,
                                 update=af_furniture_update)
    chair_arms : BoolProperty(name="Armrests", default=False,
                              update=af_furniture_update)
    # oficina
    office_arms : BoolProperty(name="Armrests", default=True,
                               update=af_furniture_update)
    office_headrest : BoolProperty(name="Headrest", default=True,
                                   update=af_furniture_update)
    # poltrona / sofá
    swivel : BoolProperty(name="Swivel Base", default=False,
                          update=af_furniture_update)
    recline : FloatProperty(name="Back Angle", default=105.0,
                            min=95.0, max=120.0,
                            update=af_furniture_update)
    accent_pillow : BoolProperty(name="Accent Pillows", default=True,
                                 update=af_furniture_update)
    sofa_seats : IntProperty(name="Seats", default=3, min=2, max=4,
                             update=af_furniture_update)
    sofa_legs : BoolProperty(name="Legs", default=True,
                             update=af_furniture_update)
    sofa_chaise : BoolProperty(name="Chaise (left)", default=False,
                               update=af_furniture_update)
    # mesas
    top_shape : EnumProperty(name="Top Shape", items=AF_TOP_SHAPE,
                             default='RECT', update=af_furniture_update)
    glass_top : BoolProperty(name="Glass Top", default=False,
                             update=af_furniture_update)
    lower_shelf : BoolProperty(name="Lower Shelf", default=True,
                               update=af_furniture_update)
    pedestal : BoolProperty(name="Pedestal Base", default=False,
                            update=af_furniture_update)
    # cama
    bed_size : EnumProperty(name="Size (CO)", items=AF_BED_SIZES,
                            default='QUEEN', update=af_furniture_update)
    headboard : EnumProperty(name="Headboard", items=AF_HEADBOARD,
                             default='UPHOLSTERED',
                             update=af_furniture_update)
    pillows : IntProperty(name="Pillows", default=2, min=1, max=4,
                          update=af_furniture_update)
    throw : BoolProperty(name="Throw Blanket", default=True,
                         update=af_furniture_update)
    storage : BoolProperty(name="Under Drawers", default=False,
                           update=af_furniture_update)
    # almacenaje
    drawers : IntProperty(name="Drawers", default=2, min=1, max=3,
                          update=af_furniture_update)
    legs : BoolProperty(name="Legs", default=True,
                        update=af_furniture_update)
    shelf_bays : IntProperty(name="Bays", default=2, min=1, max=3,
                             update=af_furniture_update)
    shelf_back : BoolProperty(name="Back Panel", default=True,
                              update=af_furniture_update)
    lower_cabinet : BoolProperty(name="Lower Cabinet", default=True,
                                 update=af_furniture_update)

    mat_fabric : IntProperty(name="Fabric", default=0, min=0)
    mat_wood : IntProperty(name="Wood", default=1, min=0)
    mat_metal : IntProperty(name="Metal", default=2, min=0)
    mat_glass : IntProperty(name="Glass", default=3, min=0)


class AF_FurnitureGenerator:
    def __init__(self, props):
        self.props = props
        self.b = AF_ObjectBuilder()
        q = getattr(props, "mesh_quality", "MEDIUM")
        # bases altas: más polígonos por defecto
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

    def cyl(self, cx, cy, z0, z1, r, base_seg=20, mi=0):
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

    def sph(self, cx, cy, cz, r, base_seg=20, base_rings=14, mi=0):
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

    def _matrix_at(self, loc, euler=(0, 0, 0), scale=None):
        m = Euler(euler, 'XYZ').to_matrix().to_4x4()
        if scale is not None:
            m = m @ Matrix.Diagonal(Vector(
                (scale[0], scale[1], scale[2], 1.0)))
        m.translation = Vector(loc)
        return m

    def rbox(self, cx, cy, cz, sx, sy, sz, euler=(0, 0, 0), mi=0):
        m = self._matrix_at((cx, cy, cz), euler)
        self.b.box(-max(sx, 0.001) / 2, max(sx, 0.001) / 2,
                   -max(sy, 0.001) / 2, max(sy, 0.001) / 2,
                   -max(sz, 0.001) / 2, max(sz, 0.001) / 2,
                   mi, transform=m)

    def ellip(self, cx, cy, cz, rx, ry, rz, euler=(0, 0, 0),
              base_seg=22, base_rings=16, mi=0):
        m = self._matrix_at((cx, cy, cz), euler,
                            (max(rx, 0.002), max(ry, 0.002),
                             max(rz, 0.002)))
        self.b.sphere(0, 0, 0, 1.0, segments=self.seg(base_seg),
                      rings=self.rings(base_rings), mi=mi,
                      transform=m)

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

    # SILLA COMEDOR
    def _build_dining_chair(self):
        p = self.props
        fab, wood, met = p.mat_fabric, p.mat_wood, p.mat_metal
        w = max(p.width, 0.30)
        sh = max(p.seat_height, 0.25)
        h = max(p.height, sh + 0.30)
        uph = p.seat_style == 'UPHOLSTERED'

        for sx in (-1, 1):
            for sy in (-1, 1):
                tx, ty = sx * (w / 2 - 0.035), sy * 0.175
                bx, by = sx * (w / 2 - 0.005), sy * 0.205
                self.tube((bx, by, 0.0), (tx, ty, sh - 0.01),
                          0.016, 16, met)
                self.disc((bx, by, 0.004), (0, 0, 1), 0.020,
                          0.008, 12, met)
        # asiento: concha madera + cojín
        self.box_c(0, 0, sh - 0.015, w - 0.02, 0.40, 0.035, wood)
        if uph:
            self.box_c(0, -0.005, sh + 0.020, w - 0.06, 0.38,
                       0.055, fab)
            self.ellip(0, -0.005, sh + 0.045, (w - 0.06) / 2,
                       0.19, 0.030, base_seg=22, base_rings=10,
                       mi=fab)
        # respaldo: postes + panel curvo (2 tramos)
        for sx in (-1, 1):
            self.tube((sx * (w / 2 - 0.035), 0.175, sh),
                      (sx * (w / 2 - 0.045), 0.225, h), 0.014, 14,
                      met)
        tilt = math.atan2(0.05, h - sh)
        self.rbox(0, 0.205, (sh + h) / 2 + 0.02, w - 0.10, 0.025,
                  (h - sh) * 0.72, euler=(tilt, 0, 0), mi=fab)
        self.rbox(0, 0.212, h - 0.06, w - 0.10, 0.030, 0.09,
                  euler=(tilt + 0.12, 0, 0), mi=fab)
        if p.chair_cushion:
            self.ellip(0, 0.175, sh + 0.22, (w - 0.14) / 2, 0.045,
                       0.10, euler=(tilt, 0, 0), mi=fab)
        if p.chair_arms:
            for sx in (-1, 1):
                ax = sx * (w / 2 - 0.02)
                self.tube((ax, -0.16, sh), (ax, -0.17, sh + 0.20),
                          0.012, 12, met)
                self.rbox(ax, 0.0, sh + 0.21, 0.055, 0.42, 0.030,
                          mi=wood)

    # SILLA OFICINA
    def _build_office_chair(self):
        p = self.props
        fab, met = p.mat_fabric, p.mat_metal
        w = max(p.width, 0.40)
        sh = max(p.seat_height, 0.30)
        h = max(p.height, sh + 0.40)
        r = w / 2

        self.cyl(0, 0, 0.055, 0.13, 0.045, 18, met)
        for a in range(5):
            ang = a * 2 * math.pi / 5
            ex, ey = r * 0.92 * math.cos(ang), r * 0.92 * math.sin(
                ang)
            self.tube((0, 0, 0.10), (ex, ey, 0.045), 0.020, 14,
                      met)
            self.box_c(ex, ey, 0.045, 0.03, 0.03, 0.05, met)
            self.sph(ex, ey, 0.028, 0.030, 14, 10, met)
        self.cone(0, 0, 0.10, 0.20, 0.040, 0.028, 16, met)
        self.cyl(0, 0, 0.18, sh - 0.10, 0.024, 16, met)
        self.cyl(0, 0, sh - 0.16, sh - 0.06, 0.016, 12, met)
        # mecanismo + asiento + palanca
        self.box_c(0, 0, sh - 0.075, 0.26, 0.24, 0.06, met)
        self.box_c(0, -0.01, sh - 0.015, 0.48, 0.46, 0.075, fab)
        self.ellip(0, -0.01, sh + 0.020, 0.235, 0.225, 0.035,
                   mi=fab)
        self.tube((0.13, 0.05, sh - 0.08), (0.20, 0.10, sh - 0.05),
                  0.008, 10, met)
        self.sph(0.20, 0.10, sh - 0.05, 0.014, 10, 8, met)
        # respaldo reclinado + espina + lumbar
        tilt = math.radians(8)
        self.tube((0, 0.20, sh - 0.06), (0, 0.30, sh + 0.28),
                  0.022, 14, met)
        self.rbox(0, 0.265, (sh + h) / 2 + 0.05, 0.46, 0.085,
                  (h - sh) * 0.78, euler=(tilt, 0, 0), mi=fab)
        self.rbox(0, 0.235, sh + 0.16, 0.34, 0.05, 0.14,
                  euler=(tilt, 0, 0), mi=fab)
        self.cyl(0.19, 0.30, sh + 0.10, sh + 0.16, 0.020, 12,
                 met)
        if p.office_headrest:
            for sx in (-1, 1):
                self.tube((sx * 0.07, 0.30 + tilt * 0.4, h - 0.16),
                          (sx * 0.07, 0.32 + tilt * 0.4, h + 0.02),
                          0.010, 10, met)
            self.rbox(0, 0.325 + tilt * 0.4, h + 0.06, 0.26, 0.07,
                      0.13, euler=(tilt, 0, 0), mi=fab)
        if p.office_arms:
            for sx in (-1, 1):
                ax = sx * 0.26
                self.tube((ax, 0.02, sh - 0.06),
                          (ax, 0.02, sh + 0.16), 0.013, 10, met)
                self.box_c(ax, -0.02, sh + 0.175, 0.07, 0.26,
                           0.03, fab)

    # POLTRONA
    def _build_armchair(self):
        p = self.props
        fab, wood, met = p.mat_fabric, p.mat_wood, p.mat_metal
        w = max(p.width, 0.50)
        d = max(p.depth, 0.50)
        h = max(p.height, 0.70)
        tilt = math.radians(max(p.recline - 90.0, 5.0))

        if p.swivel:
            self.cyl(0, 0, 0.0, 0.030, 0.26, 28, met)
            self.cyl(0, 0, 0.030, 0.10, 0.045, 18, met)
            self.cyl(0, 0, 0.10, 0.24, 0.060, 18, met)
            base_z = 0.24
        else:
            for sx in (-1, 1):
                for sy in (-1, 1):
                    self.tube((sx * (w / 2 - 0.02),
                               sy * (d / 2 - 0.02), 0.0),
                              (sx * (w / 2 - 0.07),
                               sy * (d / 2 - 0.07), 0.16),
                              0.022, 14, wood)
            base_z = 0.16
        seat_z = base_z + 0.16
        # base + brazos + almohadón asiento
        self.box_c(0, 0, base_z + 0.08, w - 0.16, d - 0.06, 0.16,
                   fab)
        for sx in (-1, 1):
            ax = sx * (w / 2 - 0.07)
            self.box_c(ax, 0, base_z + 0.17, 0.14, d - 0.04,
                       0.34, fab)
            self.box_c(ax, -0.01, base_z + 0.35, 0.15, d - 0.12,
                       0.05, fab)
        self.box_c(0, -0.03, seat_z + 0.045, w - 0.32, d - 0.22,
                   0.13, fab)
        self.ellip(0, -0.03, seat_z + 0.10, (w - 0.32) / 2,
                   (d - 0.22) / 2, 0.055, mi=fab)
        # respaldo reclinado + cojín espalda
        bz = seat_z + 0.30
        self.rbox(0, d / 2 - 0.13, bz, w - 0.16, 0.16, 0.52,
                  euler=(tilt, 0, 0), mi=fab)
        self.ellip(0, d / 2 - 0.24, bz + 0.02, (w - 0.30) / 2,
                   0.10, 0.22, euler=(tilt, 0, 0), mi=fab)
        if p.accent_pillow:
            self.ellip(-(w / 2 - 0.28), 0.02, seat_z + 0.28, 0.16,
                       0.055, 0.16, euler=(tilt + 0.15, 0, 0.25),
                       mi=fab)

    # SOFÁ
    def _build_sofa(self):
        p = self.props
        fab, wood, met = p.mat_fabric, p.mat_wood, p.mat_metal
        n = max(2, min(p.sofa_seats, 4))
        unit = 0.62
        w = n * unit + 0.30
        d = max(p.depth, 0.70)
        h = max(p.height, 0.65)
        tilt = math.radians(max(p.recline - 90.0, 5.0))

        if p.sofa_legs:
            for sx in (-1, 1):
                for sy in (-1, 1):
                    self.tube((sx * (w / 2 - 0.03),
                               sy * (d / 2 - 0.03), 0.0),
                              (sx * (w / 2 - 0.07),
                               sy * (d / 2 - 0.07), 0.13),
                              0.020, 12, wood)
            base_z = 0.13
        else:
            self.box_c(0, 0, 0.05, w - 0.16, d - 0.16, 0.10,
                       wood)
            base_z = 0.10
        seat_z = base_z + 0.17
        # base + brazos
        self.box_c(0, 0, base_z + 0.085, w, d - 0.04, 0.17, fab)
        for sx in (-1, 1):
            ax = sx * (w / 2 - 0.075)
            self.box_c(ax, 0, base_z + 0.20, 0.15, d - 0.02,
                       0.40, fab)
            self.box_c(ax, -0.01, base_z + 0.415, 0.16, d - 0.10,
                       0.05, fab)
        # cojines por plaza
        x0 = -n * unit / 2
        for i in range(n):
            xc = x0 + unit * (i + 0.5)
            self.box_c(xc, -0.04, seat_z + 0.05, unit - 0.025,
                       d - 0.26, 0.14, fab)
            self.ellip(xc, -0.04, seat_z + 0.115, (unit - 0.03)
                       / 2, (d - 0.26) / 2, 0.055, mi=fab)
            self.ellip(xc, d / 2 - 0.26, seat_z + 0.36,
                       (unit - 0.06) / 2, 0.105, 0.24,
                       euler=(tilt, 0, 0), mi=fab)
        # respaldo posterior
        self.rbox(0, d / 2 - 0.10, seat_z + 0.33, w, 0.16, 0.56,
                  euler=(tilt, 0, 0), mi=fab)
        if p.accent_pillow:
            for i, sx in enumerate((-1, 1)):
                self.ellip(sx * (w / 2 - 0.42), -0.02,
                           seat_z + 0.30, 0.17, 0.06, 0.17,
                           euler=(tilt + 0.1, 0, sx * 0.22),
                           mi=fab)
        if p.sofa_chaise:
            cx = x0 + unit * 0.5
            self.box_c(cx, -d / 2 - 0.28, base_z + 0.085, unit,
                       0.62, 0.17, fab)
            self.box_c(cx, -d / 2 - 0.28, seat_z + 0.05, unit -
                       0.025, 0.58, 0.14, fab)
            for sx in (-1, 1):
                self.tube((cx + sx * (unit / 2 - 0.05),
                           -d / 2 - 0.55, 0.0),
                          (cx + sx * (unit / 2 - 0.08),
                           -d / 2 - 0.52, base_z), 0.020, 12,
                          wood)

    # MESA CENTRO
    def _build_coffee_table(self):
        p = self.props
        wood, met, gla = p.mat_wood, p.mat_metal, p.mat_glass
        w = max(p.width, 0.40)
        d = max(p.depth, 0.30)
        h = max(p.height, 0.25)
        top_mi = gla if p.glass_top else wood
        top_t = 0.012 if p.glass_top else 0.040

        if p.top_shape == 'ROUND':
            r = min(w, d) / 2
            self.cyl(0, 0, h - top_t, h, r, 36, top_mi)
            if not p.glass_top:
                self.tor(0, 0, h - top_t, r - 0.005, 0.008, 36,
                         10, wood)
            leg_r = r - 0.10
            for a in range(4):
                ang = a * math.pi / 2 + math.pi / 4
                lx, ly = leg_r * math.cos(ang), leg_r * math.sin(
                    ang)
                self.tube((lx * 1.15, ly * 1.15, 0.0),
                          (lx, ly, h - top_t), 0.024, 14, wood)
            if p.lower_shelf:
                self.cyl(0, 0, 0.10, 0.125, leg_r + 0.02, 32,
                         wood)
        else:
            self.box_c(0, 0, h - top_t / 2, w, d, top_t, top_mi)
            if not p.glass_top:
                self.box_c(0, 0, h - top_t - 0.015, w - 0.06,
                           d - 0.06, 0.030, wood)
            for sx in (-1, 1):
                for sy in (-1, 1):
                    self.tube((sx * (w / 2 - 0.02),
                               sy * (d / 2 - 0.02), 0.0),
                              (sx * (w / 2 - 0.08),
                               sy * (d / 2 - 0.08),
                               h - top_t), 0.024, 14, wood)
            if p.lower_shelf:
                self.box_c(0, 0, 0.112, w - 0.16, d - 0.16,
                           0.025, wood)
                for sx in (-1, 1):
                    self.tube((sx * (w / 2 - 0.06), -d / 2 + 0.08,
                               0.02),
                              (sx * (w / 2 - 0.06), d / 2 - 0.08,
                               0.02), 0.010, 10, met)

    # MESA COMEDOR
    def _build_dining_table(self):
        p = self.props
        wood = p.mat_wood
        w = max(p.width, 0.80)
        d = max(p.depth, 0.60)
        h = max(p.height, 0.60)

        self.box_c(0, 0, h - 0.020, w, d, 0.040, wood)
        self.box_c(0, 0, h - 0.055, w - 0.10, d - 0.10, 0.030,
                   wood)
        # faldón
        self.box_c(0, d / 2 - 0.10, h - 0.115, w - 0.16, 0.03,
                   0.09, wood)
        self.box_c(0, -d / 2 + 0.10, h - 0.115, w - 0.16, 0.03,
                   0.09, wood)
        if p.pedestal:
            for sx in (-1, 1):
                px = sx * w * 0.28
                self.box_c(px, 0, (h - 0.16) / 2, 0.05, d - 0.30,
                           h - 0.16, wood)
                self.box_c(px, 0, 0.025, 0.34, d - 0.24, 0.05,
                           wood)
            self.box_c(0, 0, 0.30, w * 0.56, 0.06, 0.08, wood)
        else:
            for sx in (-1, 1):
                for sy in (-1, 1):
                    self.box_c(sx * (w / 2 - 0.09),
                               sy * (d / 2 - 0.09),
                               (h - 0.07) / 2, 0.085, 0.085,
                               h - 0.07, wood)
                    self.box_c(sx * (w / 2 - 0.09),
                               sy * (d / 2 - 0.09), 0.03, 0.10,
                               0.10, 0.06, wood)

    # NOCHERO
    def _build_nightstand(self):
        p = self.props
        wood, met = p.mat_wood, p.mat_metal
        w = max(p.width, 0.30)
        d = max(p.depth, 0.28)
        h = max(p.height, 0.35)
        nd = max(1, min(p.drawers, 3))

        if p.legs:
            for sx in (-1, 1):
                for sy in (-1, 1):
                    self.tube((sx * (w / 2 - 0.02),
                               sy * (d / 2 - 0.02), 0.0),
                              (sx * (w / 2 - 0.045),
                               sy * (d / 2 - 0.045), 0.14),
                              0.018, 12, wood)
            z0 = 0.14
        else:
            self.box_c(0, -0.02, 0.05, w - 0.10, d - 0.12, 0.10,
                       wood)
            z0 = 0.10
        z1 = h - 0.025
        self.box_c(0, 0, (z0 + z1) / 2, w, d, z1 - z0, wood)
        self.box_c(0, 0, h - 0.012, w + 0.02, d + 0.02, 0.025,
                   wood)
        # pasacables en tapa
        self.disc((w / 2 - 0.08, d / 2 - 0.08, h + 0.001),
                  (0, 0, 1), 0.025, 0.004, 16, met)
        dh = (z1 - z0 - 0.02) / nd
        for i in range(nd):
            fz = z1 - 0.01 - dh * (i + 0.5)
            self.box_c(0, -d / 2 - 0.009, fz, w - 0.04, 0.018,
                       dh - 0.012, wood)
            self.sph(0, -d / 2 - 0.025, fz, 0.014, 14, 10, met)
            self.cyl(0, -d / 2 - 0.020, fz - 0.008, fz + 0.008,
                     0.006, 10, met)

    # CHIFONIER
    def _build_dresser(self):
        p = self.props
        wood, met = p.mat_wood, p.mat_metal
        w = max(p.width, 0.60)
        d = max(p.depth, 0.30)
        h = max(p.height, 0.50)

        if p.legs:
            for sx in (-1, 1):
                for sy in (-1, 1):
                    self.tube((sx * (w / 2 - 0.03),
                               sy * (d / 2 - 0.03), 0.0),
                              (sx * (w / 2 - 0.06),
                               sy * (d / 2 - 0.06), 0.15),
                              0.020, 12, wood)
            z0 = 0.15
        else:
            self.box_c(0, -0.02, 0.05, w - 0.12, d - 0.12, 0.10,
                       wood)
            z0 = 0.10
        z1 = h - 0.03
        self.box_c(0, 0, (z0 + z1) / 2, w, d, z1 - z0, wood)
        self.box_c(0, 0, h - 0.015, w + 0.02, d + 0.02, 0.030,
                   wood)
        cols, rows = (3, 2) if w >= 0.95 else (2, 2)
        dw, dh = (w - 0.04) / cols, (z1 - z0 - 0.03) / rows
        for ci in range(cols):
            for ri in range(rows):
                fx = -w / 2 + 0.02 + dw * (ci + 0.5)
                fz = z1 - 0.015 - dh * (ri + 0.5)
                self.box_c(fx, -d / 2 - 0.009, fz, dw - 0.012,
                           0.018, dh - 0.012, wood)
                self.box_c(fx, -d / 2 - 0.020, fz, dw - 0.06,
                           0.006, 0.008, met)
                for sx in (-1, 1):
                    self.box_c(fx + sx * (dw / 2 - 0.05),
                               -d / 2 - 0.014, fz, 0.012, 0.014,
                               0.012, met)

    # BIBLIOTECA
    def _build_shelf(self):
        p = self.props
        wood = p.mat_wood
        w = max(p.width, 0.50)
        d = max(p.depth, 0.24)
        h = max(p.height, 1.00)
        nb = max(1, min(p.shelf_bays, 3))
        cab_h = 0.55 if p.lower_cabinet else 0.0

        self.box_c(0, 0, 0.05, w - 0.10, d - 0.08, 0.10, wood)
        z0 = 0.10
        self.box_c(-w / 2 + 0.015, 0, (z0 + h) / 2, 0.03, d,
                   h - z0, wood)
        self.box_c(w / 2 - 0.015, 0, (z0 + h) / 2, 0.03, d,
                   h - z0, wood)
        self.box_c(0, 0, h - 0.015, w, d, 0.03, wood)
        if p.shelf_back:
            self.box_c(0, d / 2 - 0.008, (z0 + h) / 2, w - 0.06,
                       0.016, h - z0, wood)
        bw = (w - 0.06) / nb
        for bi in range(nb):
            xc = -w / 2 + 0.03 + bw * (bi + 0.5)
            if bi > 0:
                self.box_c(-w / 2 + 0.03 + bw * bi, 0,
                           (z0 + h) / 2, 0.024, d - 0.04,
                           h - z0, wood)
            top0 = z0 + cab_h + (0.03 if p.lower_cabinet else 0)
            if p.lower_cabinet:
                self.box_c(xc, -d / 2 - 0.009, z0 + cab_h / 2,
                           bw - 0.02, 0.018, cab_h - 0.04, wood)
                self.sph(xc + bw / 2 - 0.06, -d / 2 - 0.024,
                         z0 + cab_h / 2, 0.013, 12, 8,
                         p.mat_metal)
            nsh = 3
            for si in range(nsh):
                fz = top0 + (h - 0.03 - top0) * (si + 1) / (
                    nsh + 1)
                self.box_c(xc, 0, fz, bw - 0.03, d - 0.05,
                           0.024, wood)

    # CAMA
    def _build_bed(self):
        p = self.props
        fab, wood, met = p.mat_fabric, p.mat_wood, p.mat_metal
        iw, il = AF_BED_INNER.get(p.bed_size, (1.60, 2.00))
        w, L = iw + 0.12, il + 0.18
        hb_h = max(p.height, 0.90)
        rail_h, rail_y0 = 0.28, 0.10
        y_head, y_foot = L / 2, -L / 2

        for sx in (-1, 1):
            for sy in (-1, 1):
                self.box_c(sx * (w / 2 - 0.05),
                           sy * (L / 2 - 0.05), 0.05, 0.09,
                           0.09, 0.10, wood)
        # largueros + piecero
        for sx in (-1, 1):
            self.box_c(sx * (w / 2 - 0.03), -0.03,
                       rail_y0 + rail_h / 2, 0.06, L - 0.10,
                       rail_h, wood)
        self.box_c(0, y_foot + 0.03, rail_y0 + 0.10, w, 0.06,
                   0.34, wood)
        # cabecero
        if p.headboard == 'SLATS':
            for sx in (-1, 1):
                self.box_c(sx * (w / 2 - 0.04), y_head - 0.03,
                           hb_h / 2, 0.08, 0.06, hb_h, wood)
            for i in range(5):
                fz = 0.35 + (hb_h - 0.45) * i / 4
                self.box_c(0, y_head - 0.03, fz, w - 0.10,
                           0.035, 0.09, wood)
        elif p.headboard == 'UPHOLSTERED':
            self.box_c(0, y_head - 0.05, hb_h / 2 + 0.05, w,
                       0.14, hb_h, fab)
            self.box_c(0, y_head - 0.13, hb_h / 2 + 0.05,
                       w - 0.10, 0.03, hb_h - 0.12, fab)
            for ci in range(max(2, int(w / 0.30))):
                for ri in range(3):
                    bx = -w / 2 + 0.2 + ci * 0.30
                    bz = 0.35 + ri * (hb_h - 0.5) / 2
                    if abs(bx) < w / 2 - 0.12:
                        self.disc((bx, y_head - 0.148, bz),
                                  (0, -1, 0), 0.016, 0.012, 12,
                                  fab)
        else:  # PANEL
            self.box_c(0, y_head - 0.03, hb_h / 2, w, 0.06,
                       hb_h, wood)
            self.box_c(0, y_head - 0.03, hb_h - 0.03, w + 0.04,
                       0.10, 0.06, wood)
            for sx in (-1, 1):
                self.box_c(sx * w / 4, y_head - 0.065,
                           hb_h * 0.52, w / 2 - 0.14, 0.015,
                           hb_h * 0.55, wood)
        # colchón + protector
        mz0 = rail_y0 + rail_h
        self.box_c(0, -0.03, mz0 + 0.125, iw, il, 0.25, fab)
        self.box_c(0, -0.03, mz0 + 0.255, iw - 0.02, il - 0.02,
                   0.03, fab)
        self.box_c(0, -0.03, mz0 + 0.13, iw + 0.005, il + 0.005,
                   0.02, fab)
        # plumón + doblez + throw
        top = mz0 + 0.27
        self.box_c(0, -0.28, top + 0.035, iw + 0.10, il * 0.62,
                   0.09, fab)
        self.ellip(0, -0.28, top + 0.075, (iw + 0.10) / 2,
                   il * 0.31, 0.045, mi=fab)
        self.box_c(0, il * 0.5 - 0.62, top + 0.075, iw + 0.10,
                   0.16, 0.05, fab)
        if p.throw:
            self.box_c(0, -il * 0.5 + 0.45, top + 0.085,
                       iw + 0.16, 0.42, 0.035, fab)
            self.box_c(0, -il * 0.5 + 0.45, top + 0.055,
                       iw + 0.20, 0.46, 0.012, fab)
        # almohadas
        npy = max(1, min(p.pillows, 4))
        pw = min(0.62, (iw - 0.10) / max(1, (npy + 1) // 2))
        for i in range(npy):
            row, col = divmod(i, (npy + 1) // 2 or 1)
            cols = max(1, (npy + 1) // 2)
            px = (col - (cols - 1) / 2) * (pw + 0.04)
            pz = top + 0.16 + row * 0.10
            py = y_head - 0.42 - row * 0.16
            self.ellip(px, py, pz, pw / 2, 0.11, 0.20,
                       euler=(-0.35 - row * 0.15, 0, 0), mi=fab)
        # cajones bajo cama
        if p.storage:
            for sx in (-1, 1):
                for i in range(2):
                    fx = sx * (w / 2 + 0.009)
                    fz = rail_y0 + rail_h / 2
                    fy = -0.03 + (i - 0.5) * (L / 2 - 0.15)
                    self.box_c(fx, fy, fz, 0.018, L / 4 - 0.06,
                               rail_h - 0.08, wood)
                    self.sph(fx + sx * 0.016, fy, fz, 0.013, 12,
                             8, met)

    def generate(self):
        t = self.props.item_type
        if t == 'DINING_CHAIR':
            self._build_dining_chair()
        elif t == 'OFFICE_CHAIR':
            self._build_office_chair()
        elif t == 'ARMCHAIR':
            self._build_armchair()
        elif t == 'SOFA':
            self._build_sofa()
        elif t == 'COFFEE_TABLE':
            self._build_coffee_table()
        elif t == 'DINING_TABLE':
            self._build_dining_table()
        elif t == 'BED':
            self._build_bed()
        elif t == 'NIGHTSTAND':
            self._build_nightstand()
        elif t == 'DRESSER':
            self._build_dresser()
        elif t == 'SHELF':
            self._build_shelf()
        return self.b


def _find_furniture_object(props):
    name = props.object_name
    if name and name in bpy.data.objects:
        return bpy.data.objects[name]
    for obj in bpy.data.objects:
        if (obj.type == 'MESH' and hasattr(obj, AF_FURN_PROP)
                and getattr(obj, AF_FURN_PROP) is props):
            try:
                props.object_name = obj.name
            except Exception:
                pass
            return obj
    return None


def _rebuild_furniture_mesh(obj, props):
    gen = AF_FurnitureGenerator(props)
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


def _setup_furniture_materials(obj):
    af_material.ensure_af_materials_for_object(obj, [
        "AF.Furn.Fabric", "AF.Furn.Wood", "AF.Furn.Metal",
        "AF.Furn.Glass",
    ])
    _tune_furn_materials()


def _tune_furn_materials():
    def _tune(name, base=None, metallic=None, rough=None,
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
        except Exception:
            pass

    _tune("AF.Furn.Fabric", base=(0.72, 0.68, 0.62, 1.0),
          metallic=0.0, rough=0.9)
    _tune("AF.Furn.Wood", base=(0.42, 0.27, 0.15, 1.0),
          metallic=0.0, rough=0.55)
    _tune("AF.Furn.Metal", base=(0.08, 0.08, 0.09, 1.0),
          metallic=0.9, rough=0.35)
    _tune("AF.Furn.Glass", base=(0.92, 0.95, 0.95, 1.0),
          metallic=0.0, rough=0.05, transmission=1.0)


def _create_furniture_object(context, name="AF_Furniture"):
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
        props = obj.archiforge_furniture
        props.is_af_furniture = True
        props.object_name = obj.name
        props.af_version = AF_FURN_VERSION
    finally:
        _SUSPEND = False
    _setup_furniture_materials(obj)
    return obj, props


def _apply_type_defaults(props, item_type):
    global _SUSPEND
    w, d, h = AF_FURN_DEFAULTS.get(item_type, (0.5, 0.5, 0.9))
    _SUSPEND = True
    try:
        props.width = w
        props.depth = d
        props.height = h
    finally:
        _SUSPEND = False


class ARCHIFORGE_OT_furniture(Operator):
    bl_idname = "archiforge.furniture"
    bl_label = "Add AF Furniture"
    bl_description = "Add a parametric ArchiForge furniture item"
    bl_options = {'REGISTER', 'UNDO'}

    item_type : EnumProperty(name="Type", items=AF_FURN_TYPES,
                             default='DINING_CHAIR')
    auto_dimensions : BoolProperty(name="Real-World Dimensions",
                                   default=True)
    width : FloatProperty(name="Width", default=0.46, min=0.05,
                          unit='LENGTH')
    depth : FloatProperty(name="Depth", default=0.52, min=0.05,
                          unit='LENGTH')
    height : FloatProperty(name="Height", default=0.86, min=0.05,
                           unit='LENGTH')

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        col = layout.column(align=True)
        col.label(text="New Furniture Item", icon='MESH_CUBE')
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
        obj, props = _create_furniture_object(context,
                                              "AF_Furniture")
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
        _rebuild_furniture_mesh(obj, props)
        self.report({'INFO'}, _tr("Furniture created: {}").format(obj.name))
        return {'FINISHED'}


class ARCHIFORGE_OT_furniture_update(Operator):
    bl_idname = "archiforge.furniture_update"
    bl_label = "Update"
    bl_description = "Force regeneration of the furniture item"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH'
                and hasattr(obj, AF_FURN_PROP)
                and obj.archiforge_furniture.is_af_furniture)

    def execute(self, context):
        obj = context.active_object
        _rebuild_furniture_mesh(obj, obj.archiforge_furniture)
        self.report({'INFO'}, _tr("Furniture updated"))
        return {'FINISHED'}


class ARCHIFORGE_OT_furniture_reset(Operator):
    bl_idname = "archiforge.furniture_reset"
    bl_label = "Reset Dimensions"
    bl_description = "Reset to real-world default dimensions"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH'
                and hasattr(obj, AF_FURN_PROP)
                and obj.archiforge_furniture.is_af_furniture)

    def execute(self, context):
        obj = context.active_object
        props = obj.archiforge_furniture
        _apply_type_defaults(props, props.item_type)
        _rebuild_furniture_mesh(obj, props)
        self.report({'INFO'}, _tr("Dimensions reset"))
        return {'FINISHED'}


class ARCHIFORGE_PT_furniture(Panel):
    bl_label = "Furniture Properties"
    bl_idname = "ARCHIFORGE_PT_furniture"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "ArchiForge"
    bl_context = "objectmode"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH'
                and hasattr(obj, AF_FURN_PROP)
                and obj.archiforge_furniture.is_af_furniture)

    def draw_header(self, context):
        self.layout.label(text="", icon='MESH_CUBE')

    def draw(self, context):
        props = context.active_object.archiforge_furniture
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
        if t == 'SOFA':
            col.label(text="Width auto from seats")
            col.prop(props, "depth")
            col.prop(props, "height")
        elif t == 'BED':
            col.label(text="Size auto from (CO) size")
            col.prop(props, "height", text="Headboard H")
        else:
            col.prop(props, "width")
            col.prop(props, "depth")
            col.prop(props, "height")
        col.operator("archiforge.furniture_reset",
                     text="Reset Real Dimensions", icon='LOOP_BACK')

        if t in ('DINING_CHAIR', 'OFFICE_CHAIR'):
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Chair", icon='MESH_CUBE')
            col.prop(props, "seat_height")
            if t == 'DINING_CHAIR':
                col.prop(props, "seat_style", text="")
                col.prop(props, "chair_cushion")
                col.prop(props, "chair_arms")
            else:
                col.prop(props, "office_arms")
                col.prop(props, "office_headrest")

        if t in ('ARMCHAIR', 'SOFA'):
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Seating", icon='MESH_CUBE')
            col.prop(props, "recline")
            col.prop(props, "accent_pillow")
            if t == 'ARMCHAIR':
                col.prop(props, "swivel")
            else:
                col.prop(props, "sofa_seats")
                col.prop(props, "sofa_legs")
                col.prop(props, "sofa_chaise")

        if t == 'COFFEE_TABLE':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Table", icon='MESH_CUBE')
            col.prop(props, "top_shape", text="")
            col.prop(props, "glass_top")
            col.prop(props, "lower_shelf")

        if t == 'DINING_TABLE':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Table", icon='MESH_CUBE')
            col.prop(props, "pedestal")

        if t == 'BED':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Bed (CO sizes)", icon='MESH_CUBE')
            col.prop(props, "bed_size", text="")
            col.prop(props, "headboard", text="")
            col.prop(props, "pillows")
            col.prop(props, "throw")
            col.prop(props, "storage")

        if t in ('NIGHTSTAND', 'DRESSER'):
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Storage", icon='MESH_CUBE')
            if t == 'NIGHTSTAND':
                col.prop(props, "drawers")
            col.prop(props, "legs")

        if t == 'SHELF':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Shelf", icon='MESH_CUBE')
            col.prop(props, "shelf_bays")
            col.prop(props, "shelf_back")
            col.prop(props, "lower_cabinet")

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Material Slots", icon='MATERIAL')
        col.prop(props, "mat_fabric", text="Fabric")
        col.prop(props, "mat_wood", text="Wood")
        col.prop(props, "mat_metal", text="Metal")
        if t in ('COFFEE_TABLE',):
            col.prop(props, "mat_glass", text="Glass")

        layout.separator()
        layout.operator("archiforge.furniture_update",
                        text="Force Update", icon='FILE_REFRESH')


classes = [
    AF_FurnitureProperties,
    ARCHIFORGE_OT_furniture,
    ARCHIFORGE_OT_furniture_update,
    ARCHIFORGE_OT_furniture_reset,
    ARCHIFORGE_PT_furniture,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Object.archiforge_furniture = PointerProperty(
        type=AF_FurnitureProperties,
        name="ArchiForge Furniture",
        description="ArchiForge furniture properties",
    )
    print("[ArchiForge] af_furniture v1 - registered")


def unregister():
    if hasattr(bpy.types.Object, "archiforge_furniture"):
        del bpy.types.Object.archiforge_furniture
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    print("[ArchiForge] af_furniture - unregistered")
