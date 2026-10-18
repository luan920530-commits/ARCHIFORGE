# -*- coding: utf-8 -*-

# ╔══════════════════════════════════════════════════════════╗
# ║         ARCHIFORGE — af_electrical.py  (v2.0)           ║
# ║         Elementos eléctricos y luminarias               ║
# ║         GPL v3 — ArchiForge Devs                        ║
# ╚══════════════════════════════════════════════════════════╝
#
# v2.1 — Redondez real vía transform + gimbal inclinable + herrajes.
# v2.0 — Modelos reescritos:
#   * 9 tipos: Outlet, Switch, Data, Bulb, Pendant,
#     Ceiling Light, Downlight, Sconce, Panel Board.
#   * Tomas por norma real: EU Schuko, US NEMA dúplex,
#     UK BS1363 con interruptor; 1-4 gangs, H/V.
#   * Bulbos E27/E14/GU10 con filamento, roscas y campanas;
#     pantallas Cónica/Cúpula/Globo/Cilindro/Industrial.
#   * Plafones, downlights empotrados, apliques Up/Down/Globo,
#     tablero eléctrico con filas de breakers y puerta.
#   * Opción de crear luz REAL de Blender (Point/Spot)
#     hija del objeto, con potencia y color paramétricos.
#   * Auto-smooth correcto + calidad de malla + creación
#     en el cursor 3D sin borrar la selección.
#
# CONVENCIÓN DE EJES:
#   * Pared (OUTLET/SWITCH/DATA/SCONCE/PANEL_BOARD): origen en
#     la superficie, +Y hacia el ambiente, centrado en X/Z.
#   * Techo (BULB/PENDANT/CEILING_LIGHT/DOWNLIGHT): origen en
#     el cielorraso, la luminaria cuelga en -Z.

# <pep8 compliant>

import bpy
import math

from mathutils import Vector, Matrix

from bpy.types import PropertyGroup, Operator, Panel
from bpy.props import (
    StringProperty, BoolProperty, IntProperty,
    FloatProperty, EnumProperty, PointerProperty,
    FloatVectorProperty,
)

from . import af_material
from .af_objects_base import AF_ObjectBuilder


AF_ELECTRICAL_PROP = "archiforge_electrical"
AF_ELEC_VERSION = 3  # v2.1: detalles con transform

AF_ELECTRICAL_TYPES = [
    ('OUTLET',        "Outlet",        "Wall power outlet",          'PLUGIN',    0),
    ('SWITCH',        "Switch",        "Wall light switch",          'TOGGLE',    1),
    ('DATA',          "Data / RJ45",   "Data / keystone wall plate", 'NETWORK_DRIVE', 2),
    ('BULB',          "Bare Bulb",     "Hanging bare light bulb",    'LIGHT',     3),
    ('PENDANT',       "Pendant",       "Hanging pendant lamp",       'LIGHT_HEM', 4),
    ('CEILING_LIGHT', "Ceiling Light", "Surface ceiling lamp",       'LIGHT',     5),
    ('DOWNLIGHT',     "Downlight",     "Recessed ceiling downlight", 'LIGHT_SPOT', 6),
    ('SCONCE',        "Wall Sconce",   "Wall-mounted light",         'LIGHT',     7),
    ('PANEL_BOARD',   "Panel Board",   "Distribution / breaker box", 'PACKAGE',   8),
]

AF_SOCKET_STANDARDS = [
    ('EU',  "EU (Schuko)",  "European Schuko outlet"),
    ('US',  "US (NEMA)",    "US NEMA 5-15 duplex outlet"),
    ('UK',  "UK (BS 1363)", "UK switched outlet"),
    ('CO',  "CO (NEMA+GFCI)", "Colombia modern duplex + GFCI"),
]

AF_ORIENTATION = [
    ('HORIZONTAL', "Horizontal", "Gangs side by side"),
    ('VERTICAL',   "Vertical",   "Gangs stacked"),
]

AF_PLATE_STYLES = [
    ('FLAT',     "Flat",     "Flat plate"),
    ('BEVELED',  "Beveled",  "Stepped beveled plate"),
    ('SCREWLESS',"Screwless","Clean screwless plate"),
]

AF_SWITCH_TYPES = [
    ('ROCKER', "Rocker", "Wide rocker"),
    ('TOGGLE', "Toggle", "Classic toggle bat"),
    ('DIMMER', "Dimmer", "Rocker + slider"),
    ('PUSH',   "Push",   "Round push button"),
]

AF_SOCKET_TYPES = [
    ('E27', "E27", "Edison screw 27 mm"),
    ('E14', "E14", "Edison screw 14 mm"),
    ('GU10',"GU10","GU10 twist-lock"),
]

AF_BULB_SHAPES = [
    ('A19',   "A19 Globe",   "Standard A-shape bulb"),
    ('G95',   "G95 Globe",   "Large decorative globe"),
    ('CANDLE',"Candle",      "Candle with flame tip"),
    ('EDISON',"Edison Tube", "Vintage tubular bulb"),
]

AF_SHADES = [
    ('CONE',      "Cone",       "Conical shade"),
    ('DOME',      "Dome",       "Dome shade"),
    ('GLOBE',     "Globe",      "Opal glass globe"),
    ('CYLINDER',  "Cylinder",   "Drum / cylinder shade"),
    ('INDUSTRIAL',"Industrial", "Wide coolie shade"),
]

AF_CEILING_STYLES = [
    ('FLUSH_DOME', "Flush Dome", "Flush opal dome"),
    ('SEMI_FLUSH', "Semi-flush", "Stem + glass bowl"),
    ('PANEL',      "Panel",      "Slim round panel"),
]

AF_TRIM_STYLES = [
    ('ROUND',      "Round",      "Round trim"),
    ('SQUARE',     "Square",     "Square trim"),
    ('ADJUSTABLE', "Adjustable", "Gimbal / eyeball"),
]

AF_SCONCE_STYLES = [
    ('UP',     "Up-light",   "Shade opening upward"),
    ('DOWN',   "Down-light", "Shade opening downward"),
    ('UPDOWN', "Up/Down",    "Tube open both ends"),
    ('GLOBE',  "Globe",      "Opal globe on arm"),
]

AF_PANEL_DOORS = [
    ('NONE',  "Open",         "No door, breakers visible"),
    ('BLIND', "Blind Door",   "Solid door + handle"),
    ('GLASS', "Glazed Door",  "Framed glass door"),
]

AF_QUALITY = [
    ('LOW',    "Low",    "Fast preview mesh"),
    ('MEDIUM', "Medium", "Balanced (recommended)"),
    ('HIGH',   "High",   "Dense presentation mesh"),
]

# Luz real por defecto según tipo (None = sin luz).
AF_LIGHT_KIND = {
    'BULB': 'POINT', 'PENDANT': 'POINT', 'CEILING_LIGHT': 'POINT',
    'DOWNLIGHT': 'SPOT', 'SCONCE': 'POINT',
}

AF_ELEC_DEFAULTS = {
    'OUTLET':        (0.086, 0.086, 0.012),
    'SWITCH':        (0.086, 0.086, 0.012),
    'DATA':          (0.086, 0.146, 0.012),
    'BULB':          (0.060, 0.110, 0.030),
    'PENDANT':       (0.300, 0.260, 0.050),
    'CEILING_LIGHT': (0.320, 0.120, 0.060),
    'DOWNLIGHT':     (0.095, 0.095, 0.110),
    'SCONCE':        (0.120, 0.220, 0.170),
    'PANEL_BOARD':   (0.400, 0.550, 0.120),
}

LUMINOUS_TYPES = {'BULB', 'PENDANT', 'CEILING_LIGHT', 'DOWNLIGHT', 'SCONCE'}


# ════════════════════════════════════════════════════════════
#  UPDATE — bandera anti-recursión para asignación en lote
# ════════════════════════════════════════════════════════════
_SUSPEND = False


def af_electrical_update(self, context):
    if _SUSPEND:
        return
    obj = _find_electrical_object(self)
    if obj is None and context is not None:
        obj = getattr(context, "active_object", None)
    if obj is None or obj.type != 'MESH':
        return
    props = getattr(obj, AF_ELECTRICAL_PROP, None)
    if props is None or not props.is_af_electrical:
        return
    _rebuild_electrical_mesh(obj, props)


# ════════════════════════════════════════════════════════════
def af_electrical_light_only(self, context):
    """Solo actualiza la luz hija (sin rebuild de malla)."""
    if _SUSPEND:
        return
    obj = _find_electrical_object(self)
    if obj is None and context is not None:
        obj = getattr(context, "active_object", None)
    if obj is None or obj.type != 'MESH':
        return
    props = getattr(obj, AF_ELECTRICAL_PROP, None)
    if props is None or not props.is_af_electrical:
        return
    try:
        gen = AF_ElectricalGenerator(props)
        gen.generate()
        _update_light_transform(obj, props, gen.light_local,
                               gen.light_kind)
    except Exception:
        pass


#  PROPIEDADES
# ════════════════════════════════════════════════════════════
class AF_ElectricalProperties(PropertyGroup):

    is_af_electrical : BoolProperty(
        name="Is ArchiForge Electrical", default=True, options={'HIDDEN'},
    )
    object_name : StringProperty(
        name="Object Name", default="", options={'HIDDEN'},
    )
    af_version : IntProperty(
        name="AF Version", default=AF_ELEC_VERSION, options={'HIDDEN'},
    )
    light_name : StringProperty(
        name="Child Light", default="", options={'HIDDEN'},
        description="Name of the generated Blender light object",
    )

    item_type : EnumProperty(
        name="Item Type", items=AF_ELECTRICAL_TYPES, default='OUTLET',
        update=af_electrical_update,
    )
    mesh_quality : EnumProperty(
        name="Mesh Quality", items=AF_QUALITY, default='MEDIUM',
        update=af_electrical_update,
    )

    # ── Dimensiones generales ───────────────────────────────
    width : FloatProperty(
        name="Width", default=0.086, min=0.01, max=2.00,
        unit='LENGTH', update=af_electrical_update,
    )
    height : FloatProperty(
        name="Height", default=0.086, min=0.01, max=2.00,
        unit='LENGTH', update=af_electrical_update,
    )
    depth : FloatProperty(
        name="Depth", default=0.012, min=0.002, max=1.00,
        unit='LENGTH', update=af_electrical_update,
    )

    # ── Placas de pared ─────────────────────────────────────
    gangs : IntProperty(
        name="Gangs", default=1, min=1, max=4,
        update=af_electrical_update,
    )
    plate_orientation : EnumProperty(
        name="Orientation", items=AF_ORIENTATION, default='HORIZONTAL',
        update=af_electrical_update,
    )
    plate_style : EnumProperty(
        name="Plate Style", items=AF_PLATE_STYLES, default='BEVELED',
        update=af_electrical_update,
    )
    plate_screws : BoolProperty(
        name="Screws", default=True, update=af_electrical_update,
    )

    # ── Tomas ───────────────────────────────────────────────
    socket_standard : EnumProperty(
        name="Socket Standard", items=AF_SOCKET_STANDARDS, default='EU',
        update=af_electrical_update,
    )
    outlet_switched : BoolProperty(
        name="With Switch", default=True, update=af_electrical_update,
        description="Rocker above each outlet (UK style)",
    )
    outlet_gfci : BoolProperty(
        name="GFCI (CO)", default=True, update=af_electrical_update,
        description="Test/reset + LED center module (Colombia)",
    )

    # ── Interruptores ───────────────────────────────────────
    switch_type : EnumProperty(
        name="Switch Type", items=AF_SWITCH_TYPES, default='ROCKER',
        update=af_electrical_update,
    )
    switch_led : BoolProperty(
        name="Locator LED", default=False, update=af_electrical_update,
    )

    # ── Colgantes / bulbos ──────────────────────────────────
    pendant_drop : FloatProperty(
        name="Drop", default=0.60, min=0.05, max=3.00,
        unit='LENGTH', update=af_electrical_update,
        description="Ceiling to shade/bulb distance",
    )
    cable_enable : BoolProperty(
        name="Cable", default=True, update=af_electrical_update,
    )
    canopy_enable : BoolProperty(
        name="Ceiling Canopy", default=True, update=af_electrical_update,
    )
    socket_type : EnumProperty(
        name="Socket", items=AF_SOCKET_TYPES, default='E27',
        update=af_electrical_update,
    )
    bulb_shape : EnumProperty(
        name="Bulb Shape", items=AF_BULB_SHAPES, default='A19',
        update=af_electrical_update,
    )
    bulb_cage : BoolProperty(
        name="Wire Cage", default=False, update=af_electrical_update,
    )
    shade_style : EnumProperty(
        name="Shade", items=AF_SHADES, default='CONE',
        update=af_electrical_update,
    )

    # ── Plafón / downlight / aplique ────────────────────────
    ceiling_style : EnumProperty(
        name="Ceiling Style", items=AF_CEILING_STYLES, default='FLUSH_DOME',
        update=af_electrical_update,
    )
    trim_style : EnumProperty(
        name="Trim", items=AF_TRIM_STYLES, default='ROUND',
        update=af_electrical_update,
    )
    downlight_tilt : FloatProperty(
        name="Gimbal Tilt", default=12.0, min=0.0, max=35.0,
        update=af_electrical_update,
        description="Tilt angle for the adjustable gimbal (deg)",
    )
    housing_enable : BoolProperty(
        name="Housing Can", default=True, update=af_electrical_update,
    )
    lens_enable : BoolProperty(
        name="Lens / Diffuser", default=True, update=af_electrical_update,
    )
    sconce_style : EnumProperty(
        name="Sconce", items=AF_SCONCE_STYLES, default='UP',
        update=af_electrical_update,
    )

    # ── Tablero ─────────────────────────────────────────────
    panel_rows : IntProperty(
        name="Rows", default=2, min=1, max=4,
        update=af_electrical_update,
    )
    panel_modules : IntProperty(
        name="Modules / Row", default=12, min=2, max=24,
        update=af_electrical_update,
    )
    panel_door : EnumProperty(
        name="Door", items=AF_PANEL_DOORS, default='BLIND',
        update=af_electrical_update,
    )
    panel_recessed : BoolProperty(
        name="Recessed", default=True, update=af_electrical_update,
    )

    # ── Luz real de Blender ─────────────────────────────────
    create_light : BoolProperty(
        name="Create Real Light", default=False,
        description="Generate a Blender light child (Point/Spot). "
                    "Use 'Sync Light' to apply.",
    )
    light_power : FloatProperty(
        name="Power", default=20.0, min=0.0, max=100000.0,
        update=af_electrical_light_only,
    )
    light_color : FloatVectorProperty(
        name="Light Color", subtype='COLOR_GAMMA', size=3,
        default=(1.0, 0.93, 0.80), min=0.0, max=1.0,
        update=af_electrical_light_only,
    )
    light_size : FloatProperty(
        name="Soft Size", default=0.05, min=0.001, max=2.0,
        unit='LENGTH', update=af_electrical_light_only,
    )
    spot_angle : FloatProperty(
        name="Spot Angle", default=60.0, min=5.0, max=150.0,
        update=af_electrical_light_only,
    )

    # ── Material slots ──────────────────────────────────────
    mat_plastic  : IntProperty(name="Plastic Material",  default=0, min=0)
    mat_metal    : IntProperty(name="Metal Material",    default=1, min=0)
    mat_glass    : IntProperty(name="Glass Material",    default=2, min=0)
    mat_emissive : IntProperty(name="Emissive Material", default=3, min=0)


# ════════════════════════════════════════════════════════════
#  GENERADOR
# ════════════════════════════════════════════════════════════
class AF_ElectricalGenerator:

    def __init__(self, props):
        self.props = props
        self.b = AF_ObjectBuilder()
        q = getattr(props, "mesh_quality", "MEDIUM")
        self._qf = {"LOW": 0.5, "MEDIUM": 1.0, "HIGH": 1.7}.get(q, 1.0)
        self.light_local = None
        self.light_kind = None

    def seg(self, base):
        return max(6, int(base * self._qf))

    def rings(self, base):
        return max(4, int(base * self._qf))

    def box_c(self, cx, cy, cz, sx, sy, sz, mi):
        sx = max(sx, 0.0008)
        sy = max(sy, 0.0008)
        sz = max(sz, 0.0008)
        self.b.box(cx - sx / 2, cx + sx / 2,
                   cy - sy / 2, cy + sy / 2,
                   cz - sz / 2, cz + sz / 2, mi)

    def box_r(self, x0, x1, y0, y1, z0, z1, mi):
        if x1 <= x0:
            x1 = x0 + 0.0008
        if y1 <= y0:
            y1 = y0 + 0.0008
        if z1 <= z0:
            z1 = z0 + 0.0008
        self.b.box(x0, x1, y0, y1, z0, z1, mi)

    def cyl(self, cx, cy, z0, z1, r, base_seg=14, mi=0):
        r = max(r, 0.0008)
        if z1 <= z0:
            z1 = z0 + 0.0008
        self.b.cylinder(cx, cy, z0, z1, r,
                        segments=self.seg(base_seg), mi=mi)

    def cone(self, cx, cy, z0, z1, r0, r1, base_seg=16, mi=0, cap=True):
        r0 = max(r0, 0.0008)
        r1 = max(r1, 0.0008)
        if z1 <= z0:
            z1 = z0 + 0.0008
        try:
            self.b.cone(cx, cy, z0, z1, r0, r1,
                        segments=self.seg(base_seg), mi=mi, cap=cap)
        except TypeError:
            self.b.cone(cx, cy, z0, z1, r0, r1,
                        segments=self.seg(base_seg), mi=mi)

    def sph(self, cx, cy, cz, r, base_seg=16, base_rings=10, mi=0):
        r = max(r, 0.0008)
        self.b.sphere(cx, cy, cz, r, segments=self.seg(base_seg),
                      rings=self.rings(base_rings), mi=mi)

    def tor(self, cx, cy, cz, major, minor, base_seg=20, minor_seg=8, mi=0):
        major = max(major, 0.002)
        minor = max(minor, 0.0008)
        self.b.torus(cx, cy, cz, major, minor,
                     major_segs=self.seg(base_seg),
                     minor_segs=max(6, int(minor_seg * self._qf)), mi=mi)

    # -- primitivas orientadas (el builder acepta Matrix 4x4) --
    @staticmethod
    def _rot_to_dir(direction):
        """Matriz 3x3 que lleva +Z a `direction`."""
        d = Vector(direction)
        if d.length < 1e-9:
            d = Vector((0.0, 0.0, 1.0))
        d = d.normalized()
        if d.dot(Vector((0.0, 0.0, 1.0))) < -0.9999:
            return Matrix.Rotation(math.pi, 3, 'X')
        return Vector((0.0, 0.0, 1.0)).rotation_difference(d).to_matrix()

    @classmethod
    def _matrix_at(cls, loc, direction=None):
        if direction is None:
            m = Matrix.Identity(4)
        else:
            m = cls._rot_to_dir(direction).to_4x4()
        m.translation = Vector(loc)
        return m

    def tube(self, p0, p1, r, base_seg=12, mi=0, cap=True):
        """Tubo redondo entre dos puntos (cualquier orientación)."""
        a, b = Vector(p0), Vector(p1)
        d = b - a
        if d.length < 1e-6:
            return
        m = self._matrix_at(a, d.normalized())
        self.b.cylinder(0, 0, 0, d.length, max(r, 0.0008),
                        segments=self.seg(base_seg), mi=mi, cap=cap,
                        transform=m)

    def disc(self, center, direction, r, thickness, base_seg=16, mi=0):
        """Disco redondo con normal `direction`, centrado en `center`."""
        dn = Vector(direction)
        if dn.length < 1e-9:
            dn = Vector((0.0, 0.0, 1.0))
        dn = dn.normalized()
        c = Vector(center)
        m = self._matrix_at(c - dn * max(thickness, 0.001) / 2, dn)
        self.b.cylinder(0, 0, 0, max(thickness, 0.001),
                        max(r, 0.0008),
                        segments=self.seg(base_seg), mi=mi, cap=True,
                        transform=m)

    def ring(self, center, direction, major, minor, base_seg=22,
             minor_seg=8, mi=0):
        """Toro con eje `direction`, centrado en `center`."""
        m = self._matrix_at(center, Vector(direction))
        self.b.torus(0, 0, 0, max(major, 0.002), max(minor, 0.0008),
                     major_segs=self.seg(base_seg),
                     minor_segs=max(6, int(minor_seg * self._qf)),
                     mi=mi, transform=m)

    def cone_dir(self, center, direction, length, r0, r1,
                 base_seg=16, mi=0, cap=True):
        """Cono con base en `center` y eje `direction` (r0 en la base)."""
        dn = Vector(direction)
        if dn.length < 1e-9:
            dn = Vector((0.0, 0.0, 1.0))
        m = self._matrix_at(center, dn.normalized())
        self.b.cone(0, 0, 0, max(length, 0.001), max(r0, 0.0008),
                    max(r1, 0.0008), segments=self.seg(base_seg),
                    mi=mi, cap=cap, transform=m)

    def _flag_light(self, x, y, z):
        kind = AF_LIGHT_KIND.get(self.props.item_type)
        if kind:
            self.light_local = (x, y, z)
            self.light_kind = kind

    # ════════════════════════════════════════════════════════
    #  PLACAS DE PARED
    # ════════════════════════════════════════════════════════
    def _plate_layout(self):
        """(plate_w, plate_h, [(cx, cz), ...]) según gangs/orientación."""
        p = self.props
        n = max(1, min(p.gangs, 4))
        cell = 0.071 if p.socket_standard == 'US' else 0.086
        if p.item_type == 'DATA':
            cell = 0.086
        if p.plate_orientation == 'HORIZONTAL':
            pw, ph = cell * n + 0.010, cell + 0.010
            pos = [(-pw / 2 + 0.005 + cell / 2 + i * cell, 0.0)
                   for i in range(n)]
        else:
            pw, ph = cell + 0.010, cell * n + 0.010
            pos = [(0.0, ph / 2 - 0.005 - cell / 2 - i * cell)
                   for i in range(n)]
        return pw, ph, pos

    def _wall_plate(self, mi_plastic, mi_metal):
        p = self.props
        pw, ph, pos = self._plate_layout()
        d = max(p.depth, 0.004)

        # caja de embutir (detrás del plano de pared)
        self.box_c(0, -0.028, 0, pw - 0.02, 0.055, ph - 0.02, mi_plastic)

        if p.plate_style == 'FLAT':
            self.box_c(0, d / 2, 0, pw, d, ph, mi_plastic)
            front = d
        elif p.plate_style == 'BEVELED':
            self.box_c(0, d * 0.30, 0, pw, d * 0.6, ph, mi_plastic)
            self.box_c(0, d * 0.72, 0, pw - 0.006, d * 0.5, ph - 0.006,
                       mi_plastic)
            front = d * 0.97
        else:  # SCREWLESS
            self.box_c(0, d / 2, 0, pw + 0.004, d, ph + 0.004, mi_plastic)
            self.box_c(0, d + 0.0012, 0, pw - 0.010, 0.0025, ph - 0.010,
                       mi_plastic)
            front = d + 0.0025

        if p.plate_screws and p.plate_style != 'SCREWLESS':
            if p.plate_orientation == 'HORIZONTAL':
                pts = [(-pw / 2 + 0.009, 0), (pw / 2 - 0.009, 0)]
            else:
                pts = [(0, ph / 2 - 0.009), (0, -ph / 2 + 0.009)]
            for sx, sz in pts:
                self.disc((sx, front + 0.0005, sz), (0, 1, 0),
                          0.0035, 0.0016, 12, mi_metal)
                self.box_c(sx, front + 0.0012, sz, 0.005, 0.001,
                           0.0012, mi_plastic)
        return pw, ph, pos, front

    # ── Tomas por norma ─────────────────────────────────────
    def _build_outlet(self):
        p = self.props
        pla, met = p.mat_plastic, p.mat_metal
        pw, ph, pos, front = self._wall_plate(pla, met)

        for cx, cz in pos:
            if p.socket_standard == 'EU':
                self._schuko(cx, cz, front, pla, met)
            elif p.socket_standard == 'US':
                self._nema_duplex(cx, cz, front, pla, met)
            elif p.socket_standard == 'CO':
                self._co_outlet(cx, cz, front, pla, met,
                                p.mat_emissive)
            else:
                self._uk_outlet(cx, cz, front, pla, met, p.mat_emissive)

    def _co_outlet(self, cx, cz, front, pla, met, emi):
        p = self.props
        # dúplex NEMA elegante + módulo GFCI central
        self.box_c(cx, front + 0.001, cz, 0.068, 0.004, 0.108,
                   pla)
        gap = 0.026 if p.outlet_gfci else 0.0205
        for dz in (gap, -gap):
            zc = cz + dz
            self.box_c(cx, front + 0.0045, zc, 0.033, 0.004,
                       0.036, pla)
            self.box_c(cx - 0.0064, front + 0.005, zc + 0.003,
                       0.0025, 0.004, 0.0115, met)
            self.box_c(cx + 0.0064, front + 0.005, zc + 0.003,
                       0.0025, 0.004, 0.0095, met)
            self.disc((cx, front + 0.0055, zc - 0.010),
                      (0, 1, 0), 0.0026, 0.003, 10, met)
        if p.outlet_gfci:
            self.box_c(cx, front + 0.005, cz, 0.024, 0.005,
                       0.024, pla)
            self.disc((cx - 0.005, front + 0.007, cz + 0.004),
                      (0, 1, 0), 0.0045, 0.004, 12, met)
            self.disc((cx - 0.005, front + 0.007, cz - 0.006),
                      (0, 1, 0), 0.0045, 0.004, 12, met)
            self.disc((cx + 0.007, front + 0.007, cz),
                      (0, 1, 0), 0.0024, 0.004, 8, emi)

    def _schuko(self, cx, cz, front, pla, met):
        p = self.props
        # cavidad redonda escalonada + orificios + tierras
        self.disc((cx, front + 0.001, cz), (0, 1, 0), 0.0255,
                  0.004, 26, pla)
        self.disc((cx, front + 0.000, cz), (0, 1, 0), 0.0225,
                  0.004, 26, pla)
        self.disc((cx, front - 0.001, cz), (0, 1, 0), 0.0195,
                  0.004, 26, pla)
        self.ring((cx, front + 0.003, cz), (0, 1, 0), 0.0240,
                  0.0016, 26, 8, pla)
        for sx in (-1, 1):
            self.disc((cx + sx * 0.0095, front - 0.0005, cz),
                      (0, 1, 0), 0.0026, 0.004, 10, met)
        for sz in (-1, 1):
            self.box_c(cx, front + 0.001, cz + sz * 0.021,
                       0.009, 0.004, 0.005, met)
        if p.outlet_switched:
            self.box_c(cx, front + 0.002, cz + 0.033,
                       0.020, 0.005, 0.012, pla)

    def _nema_duplex(self, cx, cz, front, pla, met):
        for i, dz in enumerate((0.0205, -0.0205)):
            zc = cz + dz
            self.box_c(cx, front + 0.0015, zc, 0.033, 0.004, 0.036, pla)
            # ranuras: neutro (izq, más larga) + fase + tierra
            self.box_c(cx - 0.0064, front + 0.002, zc + 0.003,
                       0.0025, 0.004, 0.0115, met)
            self.box_c(cx + 0.0064, front + 0.002, zc + 0.003,
                       0.0025, 0.004, 0.0095, met)
            self.disc((cx, front + 0.0025, zc - 0.010), (0, 1, 0),
                      0.0026, 0.003, 10, met)

    def _uk_outlet(self, cx, cz, front, pla, met, emi):
        p = self.props
        self.box_c(cx - 0.008, front + 0.0015, cz, 0.052, 0.004, 0.052, pla)
        # 3 orificios rectangulares (tierra arriba)
        self.box_c(cx - 0.008, front + 0.002, cz + 0.0145,
                   0.005, 0.004, 0.010, met)
        for sx in (-1, 1):
            self.box_c(cx - 0.008 + sx * 0.0111, front + 0.002,
                       cz - 0.0078, 0.005, 0.004, 0.010, met)
        if p.outlet_switched:
            self.box_c(cx + 0.024, front + 0.0025, cz,
                       0.012, 0.006, 0.020, pla)
            self.box_c(cx + 0.024, front + 0.006, cz + 0.005,
                       0.006, 0.002, 0.006, emi)

    # ── Interruptores ───────────────────────────────────────
    def _build_switch(self):
        p = self.props
        pla, met, emi = p.mat_plastic, p.mat_metal, p.mat_emissive
        pw, ph, pos, front = self._wall_plate(pla, met)

        for cx, cz in pos:
            if p.switch_type == 'ROCKER':
                self.box_c(cx, front + 0.002, cz, 0.040, 0.004, 0.040, pla)
                self.box_c(cx, front + 0.006, cz + 0.0085, 0.032, 0.007,
                           0.015, pla)
                self.box_c(cx, front + 0.006, cz - 0.0085, 0.032, 0.007,
                           0.015, pla)
            elif p.switch_type == 'TOGGLE':
                self.box_c(cx, front + 0.002, cz, 0.030, 0.004, 0.030,
                           pla)
                self.ring((cx, front + 0.004, cz), (0, 1, 0),
                          0.008, 0.002, 16, 8, met)
                self.tube((cx, front + 0.004, cz + 0.001),
                          (cx, front + 0.024, cz + 0.006),
                          0.0055, 12, met)
                self.sph(cx, front + 0.026, cz + 0.007, 0.0075, 12,
                         8, pla)
            elif p.switch_type == 'DIMMER':
                self.box_c(cx, front + 0.002, cz, 0.036, 0.004, 0.036,
                           pla)
                self.box_c(cx - 0.008, front + 0.006, cz, 0.020, 0.007,
                           0.030, pla)
                self.box_c(cx + 0.011, front + 0.004, cz, 0.006, 0.005,
                           0.026, met)
                self.box_c(cx + 0.011, front + 0.007, cz + 0.004,
                           0.010, 0.004, 0.006, pla)
            else:  # PUSH
                self.box_c(cx, front + 0.002, cz, 0.036, 0.004, 0.036,
                           pla)
                self.disc((cx, front + 0.005, cz), (0, 1, 0),
                          0.013, 0.005, 22, met)
                self.disc((cx, front + 0.007, cz), (0, 1, 0),
                          0.0085, 0.006, 20, pla)
                self.ring((cx, front + 0.0075, cz), (0, 1, 0),
                          0.011, 0.0012, 22, 6, pla)
            if p.switch_led:
                self.disc((cx, front + 0.001, cz - 0.030), (0, 1, 0),
                          0.0032, 0.003, 12, emi)

    # -- Data / RJ45 --
    def _build_data(self):
        p = self.props
        pla, met, gla = p.mat_plastic, p.mat_metal, p.mat_glass
        pw, ph, pos, front = self._wall_plate(pla, met)

        for cx, cz in pos:
            self.box_c(cx, front + 0.002, cz, 0.046, 0.004, 0.046,
                       pla)
            for dz in (0.012, -0.012):
                zc = cz + dz
                self.box_c(cx, front + 0.004, zc, 0.020, 0.004,
                           0.018, pla)
                self.box_c(cx, front + 0.005, zc, 0.012, 0.004,
                           0.010, met)
            self.box_c(cx, front + 0.0035, cz + 0.030, 0.030, 0.002,
                       0.008, gla)

    # BOMBILLAS COLGANTES
    def _socket_shell(self, x, y, z_top, sock_d, met, pla,
                      pins=False):
        """Portalámparas colgando (rosca E27/E14 o pines GU10)."""
        r = sock_d / 2
        h = sock_d * 1.9
        z0 = z_top - h
        self.cyl(x, y, z0, z_top, r, 18, met)
        if not pins:
            for i in range(3):
                self.tor(x, y, z0 + h * (0.25 + 0.2 * i), r,
                         0.0016, 20, 6, met)
        self.cyl(x, y, z_top, z_top + 0.012, r * 0.75, 14, pla)
        if pins:
            for sx in (-1, 1):
                self.cyl(x + sx * 0.004, y, z0 - 0.009, z0,
                         0.0016, 8, met)
            return z0 - 0.009
        self.cyl(x, y, z0 - 0.006, z0, r * 0.55, 12, pla)
        return z0 - 0.006

    def _bulb_glass(self, x, y, z_base, dia, gla, emi, met):
        """Bulbo según forma; retorna z del centro luminoso."""
        p = self.props
        r = dia / 2
        if p.bulb_shape == 'A19':
            self.cyl(x, y, z_base - 0.018, z_base + 0.004,
                     r * 0.52, 16, gla)
            cz = z_base - 0.018 - r * 0.72
            self.sph(x, y, cz, r, 20, 14, gla)
        elif p.bulb_shape == 'G95':
            self.cyl(x, y, z_base - 0.012, z_base + 0.004,
                     r * 0.42, 16, gla)
            cz = z_base - 0.012 - r * 0.85
            self.sph(x, y, cz, r, 22, 14, gla)
        elif p.bulb_shape == 'CANDLE':
            self.cyl(x, y, z_base - r * 1.1, z_base + 0.004,
                     r * 0.55, 14, gla)
            self.cone(x, y, z_base - r * 1.9, z_base - r * 1.1,
                      r * 0.55, 0.004, 14, gla)
            cz = z_base - r * 1.1
        else:  # EDISON tubular
            self.cyl(x, y, z_base - r * 2.6, z_base + 0.004,
                     r * 0.62, 16, gla)
            self.sph(x, y, z_base - r * 2.6, r * 0.62, 16, 10,
                     gla)
            cz = z_base - r * 1.5
        self.cyl(x, y, cz - r * 0.5, cz + r * 0.3, r * 0.08, 8,
                 gla)
        self.sph(x, y, cz, r * 0.22, 10, 8, emi)
        self.tor(x, y, cz, r * 0.30, r * 0.045, 14, 6, emi)
        for sx in (-1, 1):
            self.cyl(x + sx * r * 0.28, y, cz - r * 0.45,
                     cz + r * 0.1, r * 0.03, 6, met)
        return cz

    def _bulb_cage(self, x, y, cz, r, met):
        rings = [(-0.95, 0.55), (-0.35, 1.12), (0.30, 1.02),
                 (0.80, 0.45)]
        for f, k in rings:
            self.tor(x, y, cz + r * f, r * k, 0.0022, 24, 6,
                     met)
        for a in range(4):
            ang = a * math.pi / 2 + math.pi / 4
            ca, sa = math.cos(ang), math.sin(ang)
            self.tube((x + r * 0.55 * ca, y + r * 0.55 * sa,
                       cz - r * 0.95),
                      (x + r * 0.45 * ca, y + r * 0.45 * sa,
                       cz + r * 0.80), 0.0022, 8, met)
        self.cyl(x, y, cz + r * 0.80, cz + r * 1.10, 0.012, 10,
                 met)

    def _build_bulb(self):
        p = self.props
        met, pla = p.mat_metal, p.mat_plastic
        gla, emi = p.mat_glass, p.mat_emissive
        dia = max(p.width, 0.02)
        drop = max(p.pendant_drop, 0.05)

        if p.canopy_enable:
            self.cone(0, 0, -0.035, 0.0, 0.030, 0.016, 16, met)
            self.cyl(0, 0, -0.038, -0.035, 0.030, 16, met)
        if p.cable_enable:
            self.cyl(0, 0, -drop, -0.030, 0.0035, 8, pla)
        else:
            self.cyl(0, 0, -drop, -0.030, 0.008, 10, met)

        sock_d = {'E27': 0.027, 'E14': 0.015, 'GU10': 0.018}.get(
            p.socket_type, 0.027)
        zsock = self._socket_shell(0, 0, -drop, sock_d, met, pla,
                                   pins=(p.socket_type == 'GU10'))
        cz = self._bulb_glass(0, 0, zsock, dia, gla, emi, met)
        if p.bulb_cage:
            self._bulb_cage(0, 0, cz, dia / 2, met)
        self._flag_light(0, 0, cz)

    # COLGANTES CON PANTALLA
    def _build_pendant(self):
        p = self.props
        met, pla = p.mat_metal, p.mat_plastic
        gla, emi = p.mat_glass, p.mat_emissive
        dia = max(p.width, 0.10)
        drop = max(p.pendant_drop, 0.10)

        if p.canopy_enable:
            self.cone(0, 0, -0.040, 0.0, 0.035, 0.018, 16, met)
        if p.cable_enable:
            self.cyl(0, 0, -drop, -0.035, 0.0035, 8, pla)
        else:
            self.cyl(0, 0, -drop, -0.035, 0.009, 10, met)

        r = dia / 2
        zt = -drop
        if p.shade_style == 'CONE':
            h = dia * 0.80
            zb = zt - h
            self.cone(0, 0, zb, zt, r, r * 0.28, 26, met)
            self.cone(0, 0, zb + 0.004, zt - 0.01, r - 0.006,
                      r * 0.28, 26, pla, cap=False)
            self.cyl(0, 0, zt, zt + 0.035, r * 0.28, 16, met)
        elif p.shade_style == 'DOME':
            h = dia * 0.55
            zb = zt - h
            zm = zb + h * 0.55
            self.cone(0, 0, zb, zm, r, r * 0.72, 26, met)
            self.cone(0, 0, zm, zt, r * 0.72, r * 0.30, 26, met)
            self.cone(0, 0, zb + 0.004, zm, r - 0.006,
                      r * 0.72 - 0.004, 26, pla, cap=False)
            self.cyl(0, 0, zt, zt + 0.03, r * 0.30, 16, met)
        elif p.shade_style == 'GLOBE':
            zb = zt - r - 0.02
            self.sph(0, 0, zb, r, 26, 18, gla)
            self.cyl(0, 0, zt - 0.025, zt + 0.01, r * 0.35, 16,
                     met)
            self.cyl(0, 0, zb - r - 0.015, zb - r + 0.005,
                     r * 0.18, 12, met)
            self._socket_shell(0, 0, zb + r * 0.85, 0.027, met,
                               pla)
            self.sph(0, 0, zb, r * 0.30, 12, 8, emi)
            self.cyl(0, 0, zb + r * 0.1, zb + r * 0.8, 0.008, 8,
                     pla)
            self._flag_light(0, 0, zb)
            return
        elif p.shade_style == 'CYLINDER':
            h = dia * 0.90
            zb = zt - h
            self.cyl(0, 0, zb, zt, r, 26, met)
            self.cyl(0, 0, zb + 0.004, zt - 0.004, r - 0.006, 26,
                     pla)
            self.cyl(0, 0, zt - 0.004, zt + 0.02, r, 26, met)
        else:  # INDUSTRIAL coolie
            h = dia * 0.42
            zb = zt - h
            self.cone(0, 0, zb, zt, r, r * 0.22, 28, met)
            self.tor(0, 0, zb, r, 0.006, 28, 8, met)
            self.cone(0, 0, zb + 0.004, zt - 0.01, r - 0.006,
                      r * 0.22, 28, pla, cap=False)
            self.cyl(0, 0, zt, zt + 0.05, r * 0.22, 16, met)
            self.cone(0, 0, zt + 0.05, zt + 0.085, r * 0.22,
                      r * 0.12, 14, met)

        sock_d = {'E27': 0.027, 'E14': 0.015, 'GU10': 0.018}.get(
            p.socket_type, 0.027)
        zsock = self._socket_shell(0, 0, zt - 0.02, sock_d, met, pla,
                                   pins=(p.socket_type == 'GU10'))
        cz = self._bulb_glass(0, 0, zsock, min(dia * 0.32, 0.075),
                              gla, emi, met)
        if p.lens_enable:
            self.cyl(0, 0, zb + 0.002, zb + 0.008, r * 0.92, 26,
                     gla)
        self._flag_light(0, 0, cz)

    # PLAFONES
    def _build_ceiling_light(self):
        p = self.props
        met, pla = p.mat_metal, p.mat_plastic
        gla, emi = p.mat_glass, p.mat_emissive
        dia = max(p.width, 0.10)
        r = dia / 2

        if p.ceiling_style == 'FLUSH_DOME':
            self.cyl(0, 0, -0.025, 0.0, r * 1.02, 26, met)
            self.sph(0, 0, -0.02, r * 0.88, 26, 14, gla)
            self.tor(0, 0, -0.025, r * 0.95, 0.008, 28, 8, met)
            fz = -0.02 - r * 0.88
            self.cyl(0, 0, fz - 0.020, fz + 0.010, 0.014, 10,
                     met)
            self.sph(0, 0, fz - 0.025, 0.016, 10, 8, met)
            cz = -0.02 - r * 0.45
            self.sph(0, 0, cz, r * 0.30, 12, 8, emi)
        elif p.ceiling_style == 'SEMI_FLUSH':
            self.cyl(0, 0, -0.02, 0.0, 0.075, 20, met)
            self.cyl(0, 0, -0.10, -0.02, 0.014, 10, met)
            self.cone(0, 0, -0.20, -0.10, r, r * 0.30, 26, gla)
            self.tor(0, 0, -0.20, r, 0.007, 28, 8, met)
            self.cyl(0, 0, -0.115, -0.10, r * 0.30, 16, met)
            cz = -0.15
            self.sph(0, 0, cz, 0.028, 12, 8, emi)
        else:  # PANEL
            self.cyl(0, 0, -0.028, -0.012, r, 28, met)
            self.cyl(0, 0, -0.012, 0.0, r * 0.55, 20, met)
            self.cyl(0, 0, -0.032, -0.028, r * 0.94, 28, emi)
            if p.lens_enable:
                self.cyl(0, 0, -0.036, -0.032, r * 0.94, 28,
                         gla)
            cz = -0.06
        self._flag_light(0, 0, cz)

    # DOWNLIGHTS EMPOTRADOS
    def _build_downlight(self):
        p = self.props
        met, pla = p.mat_metal, p.mat_plastic
        gla, emi = p.mat_glass, p.mat_emissive
        dia = max(p.width, 0.05)
        r = dia / 2

        if p.housing_enable:
            hd = max(p.depth, 0.06)
            self.cyl(0, 0, 0.0, hd, r * 1.35, 20, met)
            self.cyl(0, 0, hd, hd + 0.015, r * 1.35, 20, met)
            for sx in (-1, 1):
                self.box_c(sx * r * 1.45, 0, 0.03, 0.02, 0.03,
                           0.06, met)
            self.box_c(0, 0, hd + 0.03, r * 1.1, 0.05, 0.035,
                       pla)
        if p.trim_style == 'SQUARE':
            self.box_c(0, 0, -0.006, dia * 1.25, dia * 1.25,
                       0.012, pla)
            self.cone(0, 0, -0.006, 0.05, r * 0.95, r * 0.55, 20,
                      met)
        else:
            self.cyl(0, 0, -0.010, 0.0, r * 1.25, 26, pla)
            self.cone(0, 0, -0.006, 0.05, r * 0.95, r * 0.55, 22,
                      met)
            self.tor(0, 0, -0.008, r * 1.02, 0.005, 26, 8, pla)
            if p.trim_style == 'ADJUSTABLE':
                self.tor(0, 0, 0.005, r * 0.62, 0.008, 22, 8,
                         met)
        for i in range(3):
            fz = 0.008 + i * 0.012
            self.tor(0, 0, fz, r * (0.80 - i * 0.09), 0.004, 22,
                     6, met)
        tilted = (p.trim_style == 'ADJUSTABLE'
                  and p.downlight_tilt > 0.5)
        if not tilted:
            if p.lens_enable:
                self.cyl(0, 0, 0.038, 0.044, r * 0.55, 20, gla)
            self.cyl(0, 0, 0.044, 0.052, r * 0.50, 18, emi)
        else:
            tilt = math.radians(p.downlight_tilt)
            inward = (math.sin(tilt), 0.0, math.cos(tilt))
            self.ring((0, 0, 0.028), inward, r * 0.52, 0.007,
                      22, 8, met)
            if p.lens_enable:
                self.disc((math.sin(tilt) * 0.010, 0.0, 0.040),
                          inward, r * 0.50, 0.005, 20, gla)
            self.disc((math.sin(tilt) * 0.016, 0.0, 0.047),
                      inward, r * 0.48, 0.008, 20, emi)
        self._flag_light(0, 0, -0.02)

    # APLIQUES DE PARED
    def _build_sconce(self):
        p = self.props
        met, pla = p.mat_metal, p.mat_plastic
        gla, emi = p.mat_glass, p.mat_emissive
        w = max(p.width, 0.06)
        proj = max(p.depth, 0.08)

        self.box_c(0, 0.012, 0, w * 0.55, 0.024, w * 1.4, met)
        for sz in (-1, 1):
            self.disc((0, 0.026, sz * w * 0.55), (0, 1, 0),
                      0.006, 0.004, 10, pla)
        self.disc((0, 0.024, 0), (0, 1, 0), 0.030, 0.020, 18,
                  met)
        self.tube((0, 0.030, 0), (0, proj * 0.85, 0), 0.013, 14,
                  met)
        self.sph(0, proj * 0.85, 0, 0.016, 12, 8, met)
        ay = proj * 0.85

        if p.sconce_style == 'GLOBE':
            self.cyl(0, ay, -0.005, 0.035, 0.028, 14, met)
            cz = 0.035 + w * 0.28
            self.sph(0, ay, cz, w * 0.28, 22, 16, gla)
            self.sph(0, ay, cz, w * 0.09, 10, 8, emi)
            self._flag_light(0, ay, cz)
            return

        r = w * 0.42
        if p.sconce_style in ('UP', 'UPDOWN'):
            self.cone(0, ay, 0.0, r * 1.5, r * 0.35, r, 22, met)
            self.cone(0, ay, 0.01, r * 1.5 - 0.01, r * 0.35 - 0.005,
                      r - 0.006, 22, pla, cap=False)
            self.sph(0, ay, r * 0.8, r * 0.32, 12, 8, emi)
        if p.sconce_style in ('DOWN', 'UPDOWN'):
            self.cone(0, ay, -r * 1.5, 0.0, r, r * 0.35, 22, met)
            self.cone(0, ay, -r * 1.5 + 0.01, -0.01, r - 0.006,
                      r * 0.35 - 0.005, 22, pla, cap=False)
            self.sph(0, ay, -r * 0.8, r * 0.32, 12, 8, emi)
        self.box_c(0, ay, 0, 0.05, 0.05, 0.04, met)
        if p.sconce_style == 'DOWN':
            for i in range(5):
                self.sph(r * 0.55, ay + r * 0.30,
                         -r * 1.5 - 0.012 - i * 0.016, 0.006, 8,
                         6, met)
            self.cone(r * 0.55, ay + r * 0.30, -r * 1.5 - 0.115,
                      -r * 1.5 - 0.085, 0.011, 0.006, 10, met)
        if p.sconce_style == 'UP':
            lz = r * 0.9
        elif p.sconce_style == 'DOWN':
            lz = -r * 0.9
        else:
            lz = 0.0
        self._flag_light(0, ay, lz)

    # TABLERO ELÉCTRICO
    def _build_panel_board(self):
        p = self.props
        pla, met = p.mat_plastic, p.mat_metal
        gla, emi = p.mat_glass, p.mat_emissive
        w = max(p.width, 0.20)
        h = max(p.height, 0.25)
        d = max(p.depth, 0.06)
        y0 = -0.02 if p.panel_recessed else 0.0

        self.box_c(0, y0 - d / 2 + 0.01, 0, w, d, h, pla)
        self.box_c(0, y0 + 0.008, 0, w + 0.03, 0.025, h + 0.03,
                   pla)
        n_glands = max(2, int(w / 0.08))
        for i in range(n_glands):
            gx = -w / 2 + w * (i + 0.5) / n_glands
            self.cyl(gx, y0 - d / 2 + 0.01, h / 2, h / 2 + 0.03,
                     0.012, 10, met)

        show_interior = p.panel_door in ('NONE', 'GLASS')
        if show_interior:
            rows = max(1, min(p.panel_rows, 4))
            mods = max(2, min(p.panel_modules, 24))
            rh = (h - 0.10) / rows
            mw = (w - 0.08) / mods
            for ri in range(rows):
                rz = h / 2 - 0.05 - rh * (ri + 0.5)
                self.box_c(0, y0 - 0.01, rz, w - 0.08, 0.02,
                           rh - 0.015, met)
                for mi in range(mods):
                    mx = -w / 2 + 0.04 + mw * (mi + 0.5)
                    bw, bh = mw - 0.004, rh - 0.03
                    self.box_c(mx, y0 + 0.005, rz, bw, 0.035, bh,
                               pla)
                    self.box_c(mx, y0 + 0.024, rz + bh * 0.18,
                               bw * 0.5, 0.006, bh * 0.3, met)
                    if (mi + ri) % 3 == 0:
                        self.box_c(mx, y0 + 0.023, rz - bh * 0.25,
                                   0.008, 0.004, 0.008, emi)

        if p.panel_door == 'BLIND':
            self.box_c(0, y0 + 0.035, 0, w - 0.02, 0.018,
                       h - 0.02, pla)
            for fz in (-0.32, 0.32):
                self.cyl(-w / 2 + 0.005, y0 + 0.035, fz * h,
                         fz * h + 0.06, 0.011, 10, met)
            self.box_c(w / 2 - 0.06, y0 + 0.048, 0, 0.025,
                       0.015, 0.09, met)
            self.disc((w / 2 - 0.06, y0 + 0.056, 0.075),
                      (0, 1, 0), 0.009, 0.006, 12, met)
            self.box_c(-w / 2 + 0.10, y0 + 0.045, h / 2 - 0.08,
                       0.12, 0.004, 0.03, emi)
        elif p.panel_door == 'GLASS':
            ft, fy = 0.035, y0 + 0.035
            self.box_c(0, fy, h / 2 - 0.01 - ft / 2, w - 0.02,
                       0.018, ft, pla)
            self.box_c(0, fy, -h / 2 + 0.01 + ft / 2, w - 0.02,
                       0.018, ft, pla)
            for sx in (-1, 1):
                self.box_c(sx * (w / 2 - 0.01 - ft / 2), fy, 0,
                           ft, 0.018, h - 0.02 - 2 * ft, pla)
            self.box_c(0, fy, 0, w - 0.02 - 2 * ft, 0.008,
                       h - 0.02 - 2 * ft, gla)
            self.box_c(w / 2 - 0.06, fy + 0.012, 0, 0.025,
                       0.015, 0.09, met)
            for fz in (-0.32, 0.32):
                self.cyl(-w / 2 + 0.005, fy, fz * h,
                         fz * h + 0.06, 0.011, 10, met)

    def generate(self):
        t = self.props.item_type
        if t == 'OUTLET':
            self._build_outlet()
        elif t == 'SWITCH':
            self._build_switch()
        elif t == 'DATA':
            self._build_data()
        elif t == 'BULB':
            self._build_bulb()
        elif t == 'PENDANT':
            self._build_pendant()
        elif t == 'CEILING_LIGHT':
            self._build_ceiling_light()
        elif t == 'DOWNLIGHT':
            self._build_downlight()
        elif t == 'SCONCE':
            self._build_sconce()
        elif t == 'PANEL_BOARD':
            self._build_panel_board()
        return self.b


# UPDATE / REBUILD
def _find_electrical_object(props):
    name = props.object_name
    if name and name in bpy.data.objects:
        return bpy.data.objects[name]
    for obj in bpy.data.objects:
        if (obj.type == 'MESH'
                and hasattr(obj, AF_ELECTRICAL_PROP)
                and getattr(obj, AF_ELECTRICAL_PROP) is props):
            try:
                props.object_name = obj.name
            except Exception:
                pass
            return obj
    return None


def _get_light_obj(props):
    name = props.light_name
    if name and name in bpy.data.objects:
        ob = bpy.data.objects[name]
        if ob.type == 'LIGHT':
            return ob
    return None


def _update_light_transform(obj, props, local, kind):
    """Solo mueve/ajusta/oculta la luz existente (seguro en callbacks)."""
    try:
        light_ob = _get_light_obj(props)
        if light_ob is None:
            return
        if local is None or kind is None or not props.create_light:
            light_ob.hide_viewport = True
            light_ob.hide_render = True
            return
        light_ob.hide_viewport = False
        light_ob.hide_render = False
        try:
            light_ob.location = local
        except Exception:
            pass
        ld = light_ob.data
        try:
            ld.energy = float(props.light_power)
        except Exception:
            pass
        try:
            ld.color = (props.light_color[0], props.light_color[1],
                        props.light_color[2])
        except Exception:
            pass
        try:
            if hasattr(ld, 'shadow_soft_size'):
                ld.shadow_soft_size = props.light_size
            if ld.type == 'SPOT':
                ld.spot_size = math.radians(
                    max(5.0, min(props.spot_angle, 150.0)))
                ld.spot_blend = 0.3
        except Exception:
            pass
    except Exception:
        pass


def _ensure_light_object(context, obj, props, local, kind):
    """Crea/elimina la luz hija (solo llamar desde operadores)."""
    try:
        existing = _get_light_obj(props)
        want = bool(props.create_light and local is not None
                    and kind in ('POINT', 'SPOT'))
        if not want:
            if existing is not None:
                try:
                    bpy.data.objects.remove(existing, do_unlink=True)
                except Exception:
                    pass
            try:
                props.light_name = ""
            except Exception:
                pass
            return None
        if existing is not None and existing.data.type != kind:
            try:
                bpy.data.objects.remove(existing, do_unlink=True)
            except Exception:
                pass
            existing = None
        if existing is None:
            ldata = bpy.data.lights.new(obj.name + "_AF_LightData",
                                        kind)
            light_ob = bpy.data.objects.new(obj.name + "_AF_Light",
                                            ldata)
            try:
                context.collection.objects.link(light_ob)
            except Exception:
                context.scene.collection.objects.link(light_ob)
            light_ob.parent = obj
            try:
                light_ob.matrix_parent_inverse.identity()
            except Exception:
                pass
            try:
                props.light_name = light_ob.name
            except Exception:
                pass
            existing = light_ob
        _update_light_transform(obj, props, local, kind)
        return existing
    except Exception:
        return None


def _rebuild_electrical_mesh(obj, props, sync_light=False,
                             context=None):
    gen = AF_ElectricalGenerator(props)
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
    if sync_light and context is not None:
        _ensure_light_object(context, obj, props, gen.light_local,
                             gen.light_kind)
    else:
        _update_light_transform(obj, props, gen.light_local,
                                gen.light_kind)


# MATERIALES
def _setup_electrical_materials(obj):
    af_material.ensure_af_materials_for_object(obj, [
        "AF.Elec.Plastic",
        "AF.Elec.Metal",
        "AF.Elec.Glass",
        "AF.Elec.Emissive",
    ])
    _tune_elec_materials()


def _tune_elec_materials():
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

    _tune("AF.Elec.Plastic", base=(0.93, 0.93, 0.94, 1.0),
          metallic=0.0, rough=0.5)
    _tune("AF.Elec.Metal", base=(0.85, 0.86, 0.88, 1.0),
          metallic=1.0, rough=0.25)
    _tune("AF.Elec.Glass", base=(0.95, 0.97, 0.97, 1.0),
          metallic=0.0, rough=0.05, transmission=1.0)
    _tune("AF.Elec.Emissive", base=(0.0, 0.0, 0.0, 1.0),
          emission=(1.0, 0.92, 0.78, 1.0), emission_strength=4.0)


# CREACIÓN
def _create_electrical_object(context, name="AF_Electrical"):
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
        props = obj.archiforge_electrical
        props.is_af_electrical = True
        props.object_name = obj.name
        props.af_version = AF_ELEC_VERSION
    finally:
        _SUSPEND = False

    _setup_electrical_materials(obj)
    return obj, props


def _apply_type_defaults(props, item_type):
    global _SUSPEND
    w, h, d = AF_ELEC_DEFAULTS.get(item_type, (0.1, 0.1, 0.02))
    _SUSPEND = True
    try:
        props.width = w
        props.height = h
        props.depth = d
    finally:
        _SUSPEND = False


# OPERADORES
class ARCHIFORGE_OT_electrical(Operator):
    bl_idname = "archiforge.electrical"
    bl_label = "Add AF Electrical"
    bl_description = "Add a parametric ArchiForge electrical item"
    bl_options = {'REGISTER', 'UNDO'}

    item_type : EnumProperty(name="Type", items=AF_ELECTRICAL_TYPES,
                             default='OUTLET')
    auto_dimensions : BoolProperty(
        name="Real-World Dimensions", default=True,
        description="Use real-world default dimensions for the type",
    )
    width : FloatProperty(name="Width", default=0.086, min=0.005,
                          unit='LENGTH')
    height : FloatProperty(name="Height", default=0.086, min=0.005,
                           unit='LENGTH')
    depth : FloatProperty(name="Depth", default=0.012, min=0.002,
                          unit='LENGTH')
    add_light : BoolProperty(
        name="Create Real Light", default=False,
        description="Generate a Blender light child (luminous types)",
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        col = layout.column(align=True)
        col.label(text="New Electrical Item", icon='PLUGIN')
        col.prop(self, "item_type")
        col.separator()
        col.prop(self, "auto_dimensions")
        sub = col.column(align=True)
        sub.enabled = not self.auto_dimensions
        sub.prop(self, "width")
        sub.prop(self, "height")
        sub.prop(self, "depth")
        if self.item_type in LUMINOUS_TYPES:
            col.separator()
            col.prop(self, "add_light")

    def execute(self, context):
        global _SUSPEND
        obj, props = _create_electrical_object(context,
                                               "AF_Electrical")
        _SUSPEND = True
        try:
            props.item_type = self.item_type
            if self.auto_dimensions:
                _apply_type_defaults(props, self.item_type)
            else:
                props.width = self.width
                props.height = self.height
                props.depth = self.depth
            if self.add_light and self.item_type in LUMINOUS_TYPES:
                props.create_light = True
        finally:
            _SUSPEND = False
        _rebuild_electrical_mesh(obj, props, sync_light=True,
                                 context=context)
        self.report({'INFO'}, f"Electrical item created: {obj.name}")
        return {'FINISHED'}


class ARCHIFORGE_OT_electrical_update(Operator):
    bl_idname = "archiforge.electrical_update"
    bl_label = "Update"
    bl_description = "Force regeneration of the electrical item"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH'
                and hasattr(obj, AF_ELECTRICAL_PROP)
                and obj.archiforge_electrical.is_af_electrical)

    def execute(self, context):
        obj = context.active_object
        _rebuild_electrical_mesh(obj, obj.archiforge_electrical,
                                 sync_light=True, context=context)
        self.report({'INFO'}, "Electrical item updated")
        return {'FINISHED'}


class ARCHIFORGE_OT_electrical_reset(Operator):
    bl_idname = "archiforge.electrical_reset"
    bl_label = "Reset Dimensions"
    bl_description = "Reset to real-world default dimensions"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH'
                and hasattr(obj, AF_ELECTRICAL_PROP)
                and obj.archiforge_electrical.is_af_electrical)

    def execute(self, context):
        obj = context.active_object
        props = obj.archiforge_electrical
        _apply_type_defaults(props, props.item_type)
        _rebuild_electrical_mesh(obj, props)
        self.report({'INFO'}, "Dimensions reset to defaults")
        return {'FINISHED'}


class ARCHIFORGE_OT_electrical_light(Operator):
    bl_idname = "archiforge.electrical_light"
    bl_label = "Sync Light"
    bl_description = "Create/update/remove the real Blender light child"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH'
                and hasattr(obj, AF_ELECTRICAL_PROP)
                and obj.archiforge_electrical.is_af_electrical)

    def execute(self, context):
        obj = context.active_object
     
        props = obj.archiforge_electrical
        gen = AF_ElectricalGenerator(props)
        gen.generate()
        _ensure_light_object(context, obj, props, gen.light_local,
                             gen.light_kind)
        if _get_light_obj(props) is not None:
            self.report({'INFO'}, "Light synced")
        else:
            self.report({'INFO'}, "Light removed/hidden")
        return {'FINISHED'}


# PANEL
class ARCHIFORGE_PT_electrical(Panel):
    bl_label = "Electrical Properties"
    bl_idname = "ARCHIFORGE_PT_electrical"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "ArchiForge"
    bl_context = "objectmode"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH'
                and hasattr(obj, AF_ELECTRICAL_PROP)
                and obj.archiforge_electrical.is_af_electrical)

    def draw_header(self, context):
        self.layout.label(text="", icon='PLUGIN')

    def draw(self, context):
        props = context.active_object.archiforge_electrical
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
        if t in ('OUTLET', 'SWITCH', 'DATA'):
            col.label(text="Plate auto-sized from gangs")
            col.prop(props, "depth")
        elif t == 'BULB':
            col.prop(props, "width", text="Globe Diameter")
            col.prop(props, "pendant_drop")
        elif t == 'PENDANT':
            col.prop(props, "width", text="Shade Diameter")
            col.prop(props, "pendant_drop")
        elif t == 'CEILING_LIGHT':
            col.prop(props, "width", text="Diameter")
        elif t == 'DOWNLIGHT':
            col.prop(props, "width", text="Cutout Diameter")
            col.prop(props, "depth", text="Housing Depth")
        else:
            col.prop(props, "width")
            col.prop(props, "height")
            col.prop(props, "depth")
        col.operator("archiforge.electrical_reset",
                     text="Reset Real Dimensions", icon='LOOP_BACK')

        if t in ('OUTLET', 'SWITCH', 'DATA'):
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Plate", icon='MESH_PLANE')
            col.prop(props, "gangs")
            if props.gangs > 1:
                col.prop(props, "plate_orientation", text="")
            col.prop(props, "plate_style", text="")
            if props.plate_style != 'SCREWLESS':
                col.prop(props, "plate_screws")

        if t == 'OUTLET':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Socket", icon='PLUGIN')
            col.prop(props, "socket_standard", text="")
            col.prop(props, "outlet_switched")
            if props.socket_standard == 'CO':
                col.prop(props, "outlet_gfci")

        if t == 'SWITCH':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Switch", icon='TOGGLE')
            col.prop(props, "switch_type", text="")
            col.prop(props, "switch_led")

        if t in ('BULB', 'PENDANT'):
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Hanging", icon='DRIVER')
            col.prop(props, "cable_enable")
            col.prop(props, "canopy_enable")
            col.prop(props, "socket_type", text="")
            col.prop(props, "bulb_shape", text="")
            if t == 'BULB':
                col.prop(props, "bulb_cage")
            else:
                col.prop(props, "shade_style", text="")
                col.prop(props, "lens_enable")

        if t == 'CEILING_LIGHT':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Ceiling", icon='LIGHT')
            col.prop(props, "ceiling_style", text="")
            col.prop(props, "lens_enable")

        if t == 'DOWNLIGHT':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Downlight", icon='LIGHT_SPOT')
            col.prop(props, "trim_style", text="")
            if props.trim_style == 'ADJUSTABLE':
                col.prop(props, "downlight_tilt")
            col.prop(props, "housing_enable")
            col.prop(props, "lens_enable")

        if t == 'SCONCE':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Sconce", icon='LIGHT')
            col.prop(props, "sconce_style", text="")

        if t == 'PANEL_BOARD':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Panel Board", icon='PACKAGE')
            col.prop(props, "panel_rows")
            col.prop(props, "panel_modules")
            col.prop(props, "panel_door", text="")
            col.prop(props, "panel_recessed")

        if t in LUMINOUS_TYPES:
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Real Light", icon='LIGHT')
            col.prop(props, "create_light")
            col.prop(props, "light_power")
            col.prop(props, "light_color", text="")
            col.prop(props, "light_size")
            if t == 'DOWNLIGHT':
                col.prop(props, "spot_angle")
            col.operator("archiforge.electrical_light",
                         text="Sync Light", icon='LIGHT')

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Material Slots", icon='MATERIAL')
        col.prop(props, "mat_plastic", text="Plastic")
        col.prop(props, "mat_metal", text="Metal")
        col.prop(props, "mat_glass", text="Glass")
        col.prop(props, "mat_emissive", text="Emissive")

        layout.separator()
        layout.operator("archiforge.electrical_update",
                        text="Force Update", icon='FILE_REFRESH')


# REGISTRO
classes = [
    AF_ElectricalProperties,
    ARCHIFORGE_OT_electrical,
    ARCHIFORGE_OT_electrical_update,
    ARCHIFORGE_OT_electrical_reset,
    ARCHIFORGE_OT_electrical_light,
    ARCHIFORGE_PT_electrical,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Object.archiforge_electrical = PointerProperty(
        type=AF_ElectricalProperties,
        name="ArchiForge Electrical",
        description="ArchiForge electrical / lighting properties",
    )
    print("[ArchiForge] af_electrical v2 - registered")


def unregister():
    if hasattr(bpy.types.Object, "archiforge_electrical"):
        del bpy.types.Object.archiforge_electrical
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    print("[ArchiForge] af_electrical - unregistered")
