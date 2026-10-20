# -*- coding: utf-8 -*-

# ╔══════════════════════════════════════════════════════════╗
# ║         ARCHIFORGE — af_bathroom.py  (v2.0)             ║
# ║         Sanitarios y accesorios de baño                 ║
# ║         GPL v3 — ArchiForge Devs                        ║
# ╚══════════════════════════════════════════════════════════╝
#
# v2.0 — Modelos reescritos:
#   * 9 tipos: Toilet, Bidet, Pedestal Sink, Vanity, Wall-hung
#     Basin, Shower, Bathtub, Mirror, Towel Rail.
#   * Dimensiones reales por defecto + botón "Reset".
#   * Calidad de malla (LOW/MEDIUM/HIGH), auto-smooth correcto
#     (antes TODO quedaba shade-smooth, incluidas las cajas).
#   * Detalles: asientos con/sin tapa, cisternas, griferías con
#     manijas, sifones, vidrios con perfilería y manijas, patas,
#     faldones, LEDs, marcos, repisas…
#   * 6 slots de material (Ceramic, Metal, Glass, Cabinet,
#     Mirror, Emissive) + auto-ajuste de nodos Principled.
#   * Creación en el cursor 3D, sin borrar la selección.
#
# CONVENCIÓN DE EJES (todos los tipos):
#   * Origen en el piso (z=0), pared al fondo en +Y, frente en -Y.
#   * MIRROR / TOWEL_RAIL y aparatos wallhung usan `mount_height`
#     (altura de la base / cara inferior sobre el piso).

# <pep8 compliant>

import bpy
import math

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


AF_BATH_PROP = "archiforge_bathroom"
AF_BATH_VERSION = 2

AF_BATH_TYPES = [
    ('TOILET',         "Toilet",         "Toilet, floor or wall-hung",      'MESH_CUBE',    0),
    ('BIDET',          "Bidet",          "Bidet, floor or wall-hung",       'MESH_CUBE',    1),
    ('PEDESTAL_SINK',  "Pedestal Sink",  "Standing sink with pedestal",     'SPHERE',       2),
    ('VANITY',         "Vanity Unit",    "Sink with cabinet",               'MESH_CUBE',    3),
    ('WALLHUNG_BASIN', "Wall-hung Basin","Compact wall-hung washbasin",     'SPHERE',       4),
    ('SHOWER',         "Shower",         "Shower enclosure + tray",         'DRAG_HANDLE',  5),
    ('BATHTUB',        "Bathtub",        "Freestanding / built-in tub",     'MESH_UVSPHERE', 6),
    ('MIRROR',         "Mirror",         "Mirror with frame / shelf / LED", 'MOD_MIRROR',   7),
    ('TOWEL_RAIL',     "Towel Rail",     "Heated towel rail / warmer",      'DRIVER',       8),
    ('ELECTRIC_SHOWER', "Electric Shower", "Ducha electrica (CO)", 'DRAG_HANDLE', 9),
]

AF_BASIN_TYPES = [
    ('INSET',  "Inset",  "Inset / undermount basin"),
    ('VESSEL', "Vessel", "Countertop vessel bowl"),
    ('DOUBLE', "Double", "Double inset basins"),
]

AF_VANITY_STYLES = [
    ('FLOOR',    "Floor + Plinth", "Floor standing with recessed plinth"),
    ('WALLHUNG', "Wall-hung",      "Floating cabinet"),
    ('LEGS',     "Legs",           "Cabinet on tapered legs"),
]

AF_ENCLOSURES = [
    ('CORNER',   "Corner",   "Glass on front + one side"),
    ('ALCOVE',   "Alcove",   "Glass on front only"),
    ('WALKIN',   "Walk-in",  "Single fixed glass panel, open"),
    ('TRAY_ONLY',"Tray Only","Tray + column, no glass"),
]

AF_DOOR_TYPES = [
    ('OPEN',    "Open Entry", "Fixed panels with open gap"),
    ('HINGED',  "Hinged",     "Hinged door + handle"),
    ('SLIDING', "Sliding",    "Sliding door + top rail"),
]

AF_FAUCET_TYPES = [
    ('NONE',  "None",        "No faucet"),
    ('DECK',  "Deck Mount",  "Faucet on the rim / deck"),
    ('WALL',  "Wall Mount",  "Wall spout + mixer"),
    ('FLOOR', "Floor Mount", "Freestanding floor column"),
]

AF_QUALITY = [
    ('LOW',    "Low",    "Fast preview mesh"),
    ('MEDIUM', "Medium", "Balanced (recommended)"),
    ('HIGH',   "High",   "Dense presentation mesh"),
]

# Dimensiones reales (ancho, fondo, alto) en metros por tipo.
AF_BATH_DEFAULTS = {
    'TOILET':         (0.42, 0.68, 0.82),
    'BIDET':          (0.37, 0.56, 0.42),
    'PEDESTAL_SINK':  (0.56, 0.46, 0.87),
    'VANITY':         (0.90, 0.52, 0.92),
    'WALLHUNG_BASIN': (0.55, 0.42, 0.90),
    'SHOWER':         (0.90, 0.90, 2.10),
    'BATHTUB':        (0.78, 1.70, 0.60),
    'MIRROR':         (0.70, 0.06, 0.90),
    'TOWEL_RAIL':     (0.60, 0.13, 1.10),
    'ELECTRIC_SHOWER': (0.18, 0.35, 0.30),
}


# ════════════════════════════════════════════════════════════
#  UPDATE — bandera anti-recursión para asignación en lote
# ════════════════════════════════════════════════════════════
_SUSPEND = False


def af_bathroom_update(self, context):
    """Callback de rebuild (seguro ante re-asignación en lote)."""
    if _SUSPEND:
        return
    # `context` puede ser None en algunos llamados internos.
    obj = _find_bathroom_object(self)
    if obj is None and context is not None:
        obj = getattr(context, "active_object", None)
    if obj is None or obj.type != 'MESH':
        return
    props = getattr(obj, AF_BATH_PROP, None)
    if props is None or not props.is_af_bathroom:
        return
    _rebuild_bathroom_mesh(obj, props)


# ════════════════════════════════════════════════════════════
#  PROPIEDADES
# ════════════════════════════════════════════════════════════
class AF_BathroomProperties(PropertyGroup):

    is_af_bathroom : BoolProperty(
        name="Is ArchiForge Bathroom", default=True, options={'HIDDEN'},
    )
    object_name : StringProperty(
        name="Object Name", default="", options={'HIDDEN'},
    )
    af_version : IntProperty(
        name="AF Version", default=AF_BATH_VERSION, options={'HIDDEN'},
    )

    item_type : EnumProperty(
        name="Item Type", items=AF_BATH_TYPES, default='TOILET',
        update=af_bathroom_update,
    )
    mesh_quality : EnumProperty(
        name="Mesh Quality", items=AF_QUALITY, default='MEDIUM',
        update=af_bathroom_update,
    )

    # ── Dimensiones generales ───────────────────────────────
    width : FloatProperty(
        name="Width", default=0.42, min=0.10, max=3.00,
        unit='LENGTH', update=af_bathroom_update,
    )
    depth : FloatProperty(
        name="Depth", default=0.68, min=0.10, max=3.00,
        unit='LENGTH', update=af_bathroom_update,
    )
    height : FloatProperty(
        name="Height", default=0.82, min=0.10, max=3.00,
        unit='LENGTH', update=af_bathroom_update,
    )
    mount_height : FloatProperty(
        name="Mount Height", default=0.24, min=0.0, max=2.00,
        unit='LENGTH', update=af_bathroom_update,
        description="Base height for wall-hung items and mirror/rail",
    )

    # ── Toilet / Bidet ──────────────────────────────────────
    toilet_wallhung : BoolProperty(
        name="Wall-hung", default=False, update=af_bathroom_update,
    )
    concealed_frame : BoolProperty(
        name="Concealed Frame", default=True, update=af_bathroom_update,
        description="Show in-wall cistern frame + flush plate (wall-hung)",
    )
    seat_closed : BoolProperty(
        name="Closed Lid", default=False, update=af_bathroom_update,
    )
    bidet_faucet : BoolProperty(
        name="Faucet", default=True, update=af_bathroom_update,
    )

    # ── Lavabos ─────────────────────────────────────────────
    faucet_enable : BoolProperty(
        name="Faucet", default=True, update=af_bathroom_update,
    )
    trap_enable : BoolProperty(
        name="Bottle Trap", default=True, update=af_bathroom_update,
    )

    # ── Vanity ──────────────────────────────────────────────
    vanity_style : EnumProperty(
        name="Vanity Style", items=AF_VANITY_STYLES, default='FLOOR',
        update=af_bathroom_update,
    )
    basin_type : EnumProperty(
        name="Basin", items=AF_BASIN_TYPES, default='INSET',
        update=af_bathroom_update,
    )
    cabinet_height : FloatProperty(
        name="Cabinet Height", default=0.58, min=0.25, max=1.20,
        unit='LENGTH', update=af_bathroom_update,
    )
    cabinet_depth : FloatProperty(
        name="Cabinet Depth", default=0.46, min=0.20, max=1.00,
        unit='LENGTH', update=af_bathroom_update,
    )
    vanity_handles : BoolProperty(
        name="Handles", default=True, update=af_bathroom_update,
    )
    vanity_backsplash : BoolProperty(
        name="Backsplash", default=True, update=af_bathroom_update,
    )
    vanity_led : BoolProperty(
        name="Under-glow LED", default=False, update=af_bathroom_update,
    )
    basin_towel_bar : BoolProperty(
        name="Front Towel Bar", default=False, update=af_bathroom_update,
    )

    # ── Shower ──────────────────────────────────────────────
    enclosure : EnumProperty(
        name="Enclosure", items=AF_ENCLOSURES, default='CORNER',
        update=af_bathroom_update,
    )
    door_type : EnumProperty(
        name="Door", items=AF_DOOR_TYPES, default='OPEN',
        update=af_bathroom_update,
    )
    tray_height : FloatProperty(
        name="Tray Height", default=0.06, min=0.02, max=0.25,
        unit='LENGTH', update=af_bathroom_update,
    )
    build_walls : BoolProperty(
        name="Build Tile Walls", default=False, update=af_bathroom_update,
        description="Build back/side tile walls (off if walls exist)",
    )
    glass_enable : BoolProperty(
        name="Glass Panels", default=True, update=af_bathroom_update,
    )
    rain_head : BoolProperty(
        name="Rain Head", default=True, update=af_bathroom_update,
    )
    hand_shower : BoolProperty(
        name="Hand Shower", default=True, update=af_bathroom_update,
    )
    shower_shelf : BoolProperty(
        name="Corner Shelf", default=True, update=af_bathroom_update,
    )
    ducha_level : IntProperty(
        name="Temp Level", default=2, min=0, max=3,
        update=af_bathroom_update,
        description="0=off, 1-3 heat levels (dial pointer)",
    )

    # ── Bathtub ─────────────────────────────────────────────
    tub_freestanding : BoolProperty(
        name="Freestanding", default=True, update=af_bathroom_update,
    )
    tub_apron : BoolProperty(
        name="Apron Panels", default=True, update=af_bathroom_update,
        description="Front/side skirt for built-in tubs",
    )
    tub_faucet : EnumProperty(
        name="Faucet", items=AF_FAUCET_TYPES, default='FLOOR',
        update=af_bathroom_update,
    )
    tub_water : BoolProperty(
        name="Water Surface", default=False, update=af_bathroom_update,
    )
    rim_width : FloatProperty(
        name="Rim Width", default=0.09, min=0.03, max=0.25,
        unit='LENGTH', update=af_bathroom_update,
    )

    # ── Mirror ──────────────────────────────────────────────
    mirror_frame : BoolProperty(
        name="Frame", default=True, update=af_bathroom_update,
    )
    mirror_shelf : BoolProperty(
        name="Shelf", default=True, update=af_bathroom_update,
    )
    mirror_led : BoolProperty(
        name="Backlit LED", default=True, update=af_bathroom_update,
    )
    mirror_cabinet : BoolProperty(
        name="Cabinet", default=False, update=af_bathroom_update,
        description="Mirrored wall cabinet instead of flat mirror",
    )

    # ── Towel rail ──────────────────────────────────────────
    towel_bars : IntProperty(
        name="Bars", default=5, min=2, max=9, update=af_bathroom_update,
    )
    towel_enable : BoolProperty(
        name="Draped Towel", default=False, update=af_bathroom_update,
    )
    rail_electric : BoolProperty(
        name="Electric (cable+switch)", default=False,
        update=af_bathroom_update,
    )

    # ── Material slots ──────────────────────────────────────
    mat_ceramic  : IntProperty(name="Ceramic Material",  default=0, min=0)
    mat_metal    : IntProperty(name="Metal Material",    default=1, min=0)
    mat_glass    : IntProperty(name="Glass Material",    default=2, min=0)
    mat_cabinet  : IntProperty(name="Cabinet Material",  default=3, min=0)
    mat_mirror   : IntProperty(name="Mirror Material",   default=4, min=0)
    mat_emissive : IntProperty(name="Emissive Material", default=5, min=0)


# ════════════════════════════════════════════════════════════
#  GENERADOR
# ════════════════════════════════════════════════════════════
class AF_BathroomGenerator:
    """Construye la geometría con primitivas del AF_ObjectBuilder.

    NOTA: los cilindros/conos del builder son verticales (+Z).
    Los tramos horizontales se aproximan con cajas delgadas.
    """

    def __init__(self, props):
        self.props = props
        self.b = AF_ObjectBuilder()
        q = getattr(props, "mesh_quality", "MEDIUM")
        self._qf = {"LOW": 0.5, "MEDIUM": 1.0, "HIGH": 1.7}.get(q, 1.0)

    # ── helpers de segmentos ─────────────────────────────────
    def seg(self, base):
        return max(6, int(base * self._qf))

    def rings(self, base):
        return max(4, int(base * self._qf))

    # ── helpers geométricos ───────────────────────────────────
    def box_c(self, cx, cy, cz, sx, sy, sz, mi):
        sx = max(sx, 0.001)
        sy = max(sy, 0.001)
        sz = max(sz, 0.001)
        self.b.box(cx - sx / 2, cx + sx / 2,
                   cy - sy / 2, cy + sy / 2,
                   cz - sz / 2, cz + sz / 2, mi)

    def box_r(self, x0, x1, y0, y1, z0, z1, mi):
        if x1 <= x0:
            x1 = x0 + 0.001
        if y1 <= y0:
            y1 = y0 + 0.001
        if z1 <= z0:
            z1 = z0 + 0.001
        self.b.box(x0, x1, y0, y1, z0, z1, mi)

    def cyl(self, cx, cy, z0, z1, r, base_seg=16, mi=0):
        r = max(r, 0.0012)
        if z1 <= z0:
            z1 = z0 + 0.001
        self.b.cylinder(cx, cy, z0, z1, r,
                        segments=self.seg(base_seg), mi=mi)

    def cone(self, cx, cy, z0, z1, r0, r1, base_seg=16, mi=0, cap=True):
        r0 = max(r0, 0.0012)
        r1 = max(r1, 0.0012)
        if z1 <= z0:
            z1 = z0 + 0.001
        try:
            self.b.cone(cx, cy, z0, z1, r0, r1,
                        segments=self.seg(base_seg), mi=mi, cap=cap)
        except TypeError:
            self.b.cone(cx, cy, z0, z1, r0, r1,
                        segments=self.seg(base_seg), mi=mi)

    def sph(self, cx, cy, cz, r, base_seg=16, base_rings=10, mi=0):
        r = max(r, 0.0012)
        self.b.sphere(cx, cy, cz, r, segments=self.seg(base_seg),
                      rings=self.rings(base_rings), mi=mi)

    def tor(self, cx, cy, cz, major, minor, base_seg=22, minor_seg=10, mi=0):
        major = max(major, 0.004)
        minor = max(minor, 0.0012)
        self.b.torus(cx, cy, cz, major, minor,
                     major_segs=self.seg(base_seg),
                     minor_segs=max(6, int(minor_seg * self._qf)), mi=mi)

    # ════════════════════════════════════════════════════════
    #  PIEZAS REUTILIZABLES
    # ════════════════════════════════════════════════════════
    def _mixer_faucet(self, x, y, z_base, spout_reach=0.16,
                      spout_h=0.16, mi_met=1, lever=True):
        """Monomando: base + cuerpo + caño + aireador + palanca."""
        self.cyl(x, y, z_base, z_base + 0.025, 0.024, 14, mi_met)
        self.cyl(x, y, z_base, z_base + spout_h, 0.016, 12, mi_met)
        # caño horizontal hacia -Y (frente)
        self.box_c(x, y - spout_reach / 2, z_base + spout_h - 0.008,
                   0.030, spout_reach, 0.026, mi_met)
        self.cyl(x, y - spout_reach, z_base + spout_h - 0.035,
                 z_base + spout_h - 0.006, 0.013, 10, mi_met)
        if lever:
            self.box_c(x + 0.028, y + 0.010, z_base + 0.075,
                       0.012, 0.055, 0.014, mi_met)
            self.cyl(x + 0.028, y + 0.032, z_base + 0.030,
                     z_base + 0.075, 0.007, 8, mi_met)

    def _two_handle_faucet(self, x, y, z_base, spread=0.16, mi_met=1):
        """Grifería clásica: caño central + 2 volantes."""
        self._mixer_faucet(x, y, z_base, spout_reach=0.15,
                           spout_h=0.13, mi_met=mi_met, lever=False)
        for sx in (-1, 1):
            hx = x + sx * spread / 2
            self.cyl(hx, y, z_base, z_base + 0.020, 0.020, 12, mi_met)
            self.cyl(hx, y, z_base + 0.020, z_base + 0.055,
                     0.010, 10, mi_met)
            self.cyl(hx, y, z_base + 0.055, z_base + 0.068,
                     0.026, 14, mi_met)
            self.box_c(hx, y, z_base + 0.062, 0.058, 0.012, 0.010, mi_met)

    def _drain(self, x, y, z, r=0.032, mi_met=1):
        self.cyl(x, y, z, z + 0.006, r, 16, mi_met)
        self.cyl(x, y, z + 0.006, z + 0.009, r * 0.45, 12, mi_met)

    def _bottle_trap(self, x, y_wall, z_rim_bottom, mi_met=1, mi_cer=0):
        """Sifón botella cromado + brazo a pared."""
        z0 = max(z_rim_bottom - 0.42, 0.06)
        self.cyl(x, y_wall - 0.16, z_rim_bottom - 0.02, z_rim_bottom + 0.01,
                 0.016, 10, mi_met)
        self.cyl(x, y_wall - 0.16, z0, z0 + 0.13, 0.036, 14, mi_met)
        self.cyl(x, y_wall - 0.16, z0 - 0.02, z0, 0.030, 12, mi_met)
        self.box_c(x, y_wall - 0.07, z0 + 0.06, 0.030, 0.20, 0.030, mi_met)
        self.cyl(x, y_wall - 0.005, z0 + 0.02, z0 + 0.10, 0.035, 12, mi_cer)

    def _rim_ring(self, cx, cy, z, w, d, rim, h, mi):
        """Marco rectangular (4 cajas) para bordes de bañera/pileta."""
        hw, hd = w / 2, d / 2
        self.box_r(cx - hw, cx + hw, cy + hd - rim, cy + hd, z, z + h, mi)
        self.box_r(cx - hw, cx + hw, cy - hd, cy - hd + rim, z, z + h, mi)
        self.box_r(cx - hw, cx - hw + rim, cy - hd + rim, cy + hd - rim,
                   z, z + h, mi)
        self.box_r(cx + hw - rim, cx + hw, cy - hd + rim, cy + hd - rim,
                   z, z + h, mi)

    # ════════════════════════════════════════════════════════
    #  INODORO
    # ════════════════════════════════════════════════════════
    def _build_toilet(self):
        p = self.props
        cer, met = p.mat_ceramic, p.mat_metal
        w = max(p.width, 0.30)
        d = max(p.depth, 0.45)
        h = max(p.height, 0.60)

        if p.toilet_wallhung:
            self._build_toilet_wallhung(w, d, h, cer, met)
            return

        seat_h = 0.40
        bowl_cy = -d * 0.06

        # pedestal / pie
        pw, pd = w * 0.60, d * 0.68
        self.box_c(0, 0.0, 0.035, pw, pd, 0.07, cer)
        for sx in (-1, 1):  # tapas de fijación
            self.cyl(sx * pw * 0.30, pd * 0.16, 0.070, 0.082,
                     0.013, 10, met)

        # cuerpo ahusado de la taza
        self.cone(0, bowl_cy, 0.07, seat_h - 0.04,
                  w * 0.250, w * 0.335, 22, cer)
        # conector trasero hacia el tanque
        self.box_r(-w * 0.19, w * 0.19, bowl_cy, d * 0.30,
                   seat_h - 0.15, seat_h - 0.02, cer)
        # interior (embudo escalonado = sensación de profundidad)
        self.cyl(0, bowl_cy, seat_h - 0.14, seat_h - 0.035,
                 w * 0.190, 20, cer)
        self.cone(0, bowl_cy, seat_h - 0.035, seat_h - 0.004,
                  w * 0.190, w * 0.255, 20, cer)

        # asiento
        self.tor(0, bowl_cy, seat_h, w * 0.285, 0.031, 26, 12, cer)
        if p.seat_closed:
            self.cyl(0, bowl_cy, seat_h + 0.026, seat_h + 0.048,
                     w * 0.300, 26, cer)
        # bisagras
        for sx in (-1, 1):
            self.box_c(sx * w * 0.13, bowl_cy + w * 0.305,
                       seat_h + 0.012, 0.032, 0.055, 0.026, met)

        # tanque adosado + tapa + doble pulsador
        tank_w, tank_d = w * 0.94, 0.175
        tank_cy = d * 0.30
        tank_z0, tank_z1 = seat_h - 0.03, h
        self.box_c(0, tank_cy, (tank_z0 + tank_z1) / 2,
                   tank_w, tank_d, tank_z1 - tank_z0, cer)
        self.box_c(0, tank_cy, tank_z1 + 0.014,
                   tank_w + 0.022, tank_d + 0.022, 0.036, cer)
        for sx in (-1, 1):
            self.cyl(sx * 0.036, tank_cy, tank_z1 + 0.032,
                     tank_z1 + 0.045, 0.023, 14, met)
        # acoples tanque-taza + alimentación
        for sx in (-1, 1):
            self.cyl(sx * w * 0.16, tank_cy - tank_d / 2 - 0.012,
                     seat_h - 0.10, seat_h - 0.015, 0.022, 12, cer)
        self.cyl(-tank_w / 2 + 0.035, tank_cy, 0.10,
                 tank_z0 + 0.03, 0.011, 10, met)
        self.box_c(-tank_w / 2 + 0.035, tank_cy, 0.055,
                   0.045, 0.045, 0.075, met)

    def _build_toilet_wallhung(self, w, d, h, cer, met):
        p = self.props
        mount = max(p.mount_height, 0.10)
        rim_h = mount + 0.165
        front_y = -d * 0.28
        back_y = d * 0.30

        # placa mural + cuerpo en voladizo (3 tramos)
        self.box_c(0, back_y, rim_h - 0.13, w * 0.72, 0.05, 0.26, cer)
        self.box_c(0, (back_y + front_y) / 2 + 0.10, mount + 0.085,
                   w * 0.62, (back_y - front_y) * 0.62, 0.13, cer)
        self.cone(0, front_y + 0.02, mount + 0.02, rim_h - 0.03,
                  w * 0.27, w * 0.335, 22, cer)
        # interior + asiento + tapa opcional
        self.cyl(0, front_y + 0.02, rim_h - 0.12, rim_h - 0.03,
                 w * 0.19, 20, cer)
        self.cone(0, front_y + 0.02, rim_h - 0.03, rim_h - 0.004,
                  w * 0.19, w * 0.255, 20, cer)
        self.tor(0, front_y + 0.02, rim_h, w * 0.285, 0.031, 26, 12, cer)
        if p.seat_closed:
            self.cyl(0, front_y + 0.02, rim_h + 0.026, rim_h + 0.048,
                     w * 0.30, 26, cer)
        for sx in (-1, 1):
            self.box_c(sx * w * 0.13, front_y + 0.02 + w * 0.305,
                       rim_h + 0.012, 0.032, 0.055, 0.026, met)

        if p.concealed_frame:
            # bastidor embutido + placa de doble descarga
            self.box_c(0, back_y + 0.075, 0.60, 0.52, 0.13, 1.14, met)
            self.box_c(0, back_y + 0.008, 1.02, 0.25, 0.018, 0.16, met)
            for sx in (-1, 1):
                self.box_c(sx * 0.048, back_y - 0.004, 1.02,
                           0.070, 0.012, 0.120, cer)

    # ════════════════════════════════════════════════════════
    #  BIDÉ
    # ════════════════════════════════════════════════════════
    def _build_bidet(self):
        p = self.props
        cer, met = p.mat_ceramic, p.mat_metal
        w = max(p.width, 0.28)
        d = max(p.depth, 0.40)
        rim_h = 0.40 if not p.toilet_wallhung else max(
            p.mount_height, 0.10) + 0.165
        bowl_cy = -d * 0.05

        if not p.toilet_wallhung:
            self.box_c(0, 0.0, 0.030, w * 0.58, d * 0.66, 0.06, cer)
            self.cone(0, bowl_cy, 0.06, rim_h - 0.04,
                      w * 0.24, w * 0.33, 20, cer)
        else:
            self.box_c(0, d * 0.28, rim_h - 0.12,
                       w * 0.70, 0.05, 0.24, cer)
            self.cone(0, bowl_cy, rim_h - 0.16, rim_h - 0.03,
                      w * 0.26, w * 0.33, 20, cer)

        # cubeta + borde + desagüe
        self.cyl(0, bowl_cy, rim_h - 0.11, rim_h - 0.03,
                 w * 0.20, 20, cer)
        self.cone(0, bowl_cy, rim_h - 0.03, rim_h - 0.002,
                  w * 0.20, w * 0.27, 20, cer)
        self.tor(0, bowl_cy, rim_h, w * 0.29, 0.028, 24, 10, cer)
        self._drain(0, bowl_cy, rim_h - 0.105, r=0.028, mi_met=met)

        # grifería trasera + rebalse
        if p.bidet_faucet:
            fy = bowl_cy + w * 0.34
            self._mixer_faucet(0, fy, rim_h, spout_reach=0.12,
                               spout_h=0.10, mi_met=met, lever=True)
            self.cyl(0, fy - 0.02, rim_h - 0.055, rim_h - 0.045,
                     0.008, 8, met)

    # ════════════════════════════════════════════════════════
    #  LAVAMANOS DE PEDESTAL
    # ════════════════════════════════════════════════════════
    def _build_pedestal_sink(self):
        p = self.props
        cer, met = p.mat_ceramic, p.mat_metal
        w = max(p.width, 0.35)
        h = max(p.height, 0.60)
        r = w * 0.47

        # pie + fuste + capitel
        self.cyl(0, 0, 0.0, 0.025, w * 0.155, 18, cer)
        self.cone(0, 0, 0.025, h - 0.24, w * 0.115, w * 0.155, 18, cer)
        self.cyl(0, 0, h - 0.24, h - 0.19, w * 0.185, 18, cer)

        # pileta exterior + borde + interior
        self.cyl(0, 0, h - 0.19, h - 0.045, r, 26, cer)
        self.tor(0, 0, h - 0.045, r - 0.035, 0.030, 28, 12, cer)
        self.cone(0, 0, h - 0.175, h - 0.055, r * 0.55, r - 0.045,
                  26, cer)
        self._drain(0, 0, h - 0.170, r=0.031, mi_met=met)
        # rebalse
        self.cyl(0, -(r - 0.075), h - 0.10, h - 0.09, 0.008, 8, met)

        # repisa trasera + grifería
        self.box_c(0, r * 0.72, h - 0.030, w * 0.52, 0.115, 0.035, cer)
        if p.faucet_enable:
            self._two_handle_faucet(0, r * 0.72, h - 0.012,
                                    spread=0.17, mi_met=met)
        if p.trap_enable:
            self._bottle_trap(0, r * 0.55, h - 0.19,
                              mi_met=met, mi_cer=cer)

    # ════════════════════════════════════════════════════════
    #  MUEBLE CON LAVABO
    # ════════════════════════════════════════════════════════
    def _build_vanity(self):
        p = self.props
        cab, cer, met = p.mat_cabinet, p.mat_ceramic, p.mat_metal
        emi = p.mat_emissive
        w = max(p.width, 0.45)
        ch = max(p.cabinet_height, 0.25)
        cd = max(p.cabinet_depth, 0.20)
        top = 0.86  # altura encimera

        y0, y1 = 0.0, cd  # fondo(pared) → frente
        yc = cd / 2

        if p.vanity_style == 'FLOOR':
            z0 = 0.10
            # zócalo retranqueado
            self.box_c(0, yc - 0.02, 0.05, w - 0.12, cd - 0.14, 0.10, cab)
        elif p.vanity_style == 'WALLHUNG':
            z0 = top - 0.03 - ch
        else:  # LEGS
            z0 = 0.22
            for sx in (-1, 1):
                for sy in (0.08, 0.92):
                    self.cone(sx * (w / 2 - 0.06), cd * sy, 0.0, z0,
                              0.028, 0.020, 10, met)
        z1 = z0 + ch

        # carcasa + frentes con sombra perimetral
        self.box_c(0, yc, (z0 + z1) / 2, w, cd, ch, cab)
        n_doors = 2 if w < 1.05 else 4
        dw = w / n_doors
        for i in range(n_doors):
            xc = -w / 2 + dw * (i + 0.5)
            self.box_c(xc, y1 + 0.009, (z0 + z1) / 2,
                       dw - 0.008, 0.018, ch - 0.03, cab)
            # línea cajón superior
            self.box_c(xc, y1 + 0.019, z1 - ch * 0.28,
                       dw - 0.008, 0.004, 0.006, cab)
            if p.vanity_handles:
                self.box_c(xc, y1 + 0.035, z1 - 0.10,
                           0.14, 0.012, 0.012, met)
                for sx in (-1, 1):
                    self.box_c(xc + sx * 0.06, y1 + 0.024, z1 - 0.10,
                               0.010, 0.022, 0.010, met)

        if p.vanity_style == 'WALLHUNG' and p.vanity_led:
            self.box_c(0, yc, z0 - 0.008, w - 0.06, cd - 0.10,
                       0.014, emi)

        # encimera con goterón + salpicadero
        self.box_c(0, yc, top + 0.0, w + 0.03, cd + 0.03, 0.022, cab)
        self.box_c(0, yc, top - 0.020, w - 0.02, cd - 0.02, 0.018, cab)
        if p.vanity_backsplash:
            self.box_c(0, 0.012, top + 0.065, w + 0.03, 0.024, 0.11, cab)

        # piletas
        basin_z = top + 0.011
        if p.basin_type == 'DOUBLE':
            xs = (-w * 0.25, w * 0.25)
            br = min(w * 0.17, 0.17)
            for xc in xs:
                self._inset_basin(xc, yc, basin_z, br, cer, met)
                if p.faucet_enable:
                    self._mixer_faucet(xc, 0.10, basin_z,
                                       spout_reach=br * 0.8,
                                       spout_h=0.14, mi_met=met)
        elif p.basin_type == 'VESSEL':
            br = min(w * 0.21, 0.20)
            self.cyl(0, yc, basin_z, basin_z + 0.115, br, 26, cer)
            self.tor(0, yc, basin_z + 0.115, br - 0.020, 0.021, 28, 10, cer)
            self.cone(0, yc, basin_z + 0.015, basin_z + 0.10,
                      br * 0.45, br - 0.025, 26, cer)
            self._drain(0, yc, basin_z + 0.018, r=0.031, mi_met=met)
             
            if p.faucet_enable:
                self._mixer_faucet(0, 0.10, basin_z, spout_reach=br * 0.9,
                                   spout_h=0.24, mi_met=met)
        else:  # INSET sencilla
            br = min(w * 0.21, 0.20)
            self._inset_basin(0, yc, basin_z, br, cer, met)
            if p.faucet_enable:
                self._mixer_faucet(0, 0.10, basin_z, spout_reach=br * 0.8,
                                   spout_h=0.14, mi_met=met)

    def _inset_basin(self, xc, yc, basin_z, br, cer, met):
        self.tor(xc, yc, basin_z + 0.008, br, 0.020, 28, 10, cer)
        self.cone(xc, yc, basin_z - 0.14, basin_z + 0.005,
                  br * 0.42, br - 0.015, 26, cer)
        self._drain(xc, yc, basin_z - 0.135, r=0.031, mi_met=met)

    # ════════════════════════════════════════════════════════
    #  LAVABO MURAL
    # ════════════════════════════════════════════════════════
    def _build_wallhung_basin(self):
        p = self.props
        cer, met = p.mat_ceramic, p.mat_metal
        w = max(p.width, 0.35)
        d = max(p.depth, 0.30)
        rim_z = max(p.height, 0.60)
        bh = 0.16
        z0 = rim_z - bh
        wt = 0.035

        # fondo + 4 paredes (cavidad real) + borde superior
        self.box_c(0, d / 2, z0 + 0.015, w, d, 0.030, cer)
        self.box_c(0, d - wt / 2, (z0 + rim_z) / 2, w, wt, bh, cer)
        self.box_c(0, wt / 2, (z0 + rim_z) / 2, w, wt, bh, cer)
        self.box_c(-w / 2 + wt / 2, d / 2, (z0 + rim_z) / 2,
                   wt, d - 2 * wt, bh, cer)
        self.box_c(w / 2 - wt / 2, d / 2, (z0 + rim_z) / 2,
                   wt, d - 2 * wt, bh, cer)
        self._rim_ring(0, d / 2, rim_z, w + 0.02, d + 0.02,
                       0.055, 0.025, cer)
        self._drain(0, d / 2 - 0.01, z0 + 0.030, r=0.031, mi_met=met)
        self.cyl(0, wt + 0.012, rim_z - 0.075, rim_z - 0.065,
                 0.008, 8, met)

        # ménsulas + sifón + grifería + toallero
        for sx in (-1, 1):
            self.box_c(sx * w * 0.30, d - 0.06, z0 - 0.05,
                       0.04, 0.14, 0.10, met)
        if p.trap_enable:
            self._bottle_trap(0, d, z0 + 0.02, mi_met=met, mi_cer=cer)
        if p.faucet_enable:
            self._mixer_faucet(0, d - 0.02, rim_z + 0.025,
                               spout_reach=d * 0.45, spout_h=0.15,
                               mi_met=met)
        if p.basin_towel_bar:
            for sx in (-1, 1):
                self.box_c(sx * (w / 2 - 0.10), -0.045, rim_z - 0.06,
                           0.02, 0.07, 0.02, met)
            self.box_c(0, -0.075, rim_z - 0.06, w - 0.20, 0.022, 0.022,
                       met)

    # ════════════════════════════════════════════════════════
    #  DUCHA
    # ════════════════════════════════════════════════════════
    def _glass_panel(self, x0, x1, y0, y1, z0, z1, gla, met,
                     handle=False, hinge_side=0):
        """Panel de vidrio en planta (tramo en X o en Y)."""
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        lx, ly = x1 - x0, y1 - y0
        along_x = lx >= ly
        length = max(lx if along_x else ly, 0.05)
        th = 0.008
        sx, sy = (length, th) if along_x else (th, length)

        self.box_c(cx, cy, (z0 + z1) / 2, sx, sy, z1 - z0, gla)
        self.box_c(cx, cy, z0 + 0.014, sx + 0.012, sy + 0.012, 0.028,
                   met)
        for f in (0.06, 0.94):
            if along_x:
                px, py = x0 + lx * f, cy
            else:
                px, py = cx, y0 + ly * f
            self.box_c(px, py, z1 - 0.10, 0.05, 0.05, 0.10, met)
        if hinge_side != 0:
            if along_x:
                hx = x0 + 0.03 if hinge_side < 0 else x1 - 0.03
                hy = cy
            else:
                hx = cx
                hy = y0 + 0.03 if hinge_side < 0 else y1 - 0.03
            for fz in (0.30, 0.70):
                self.box_c(hx, hy, z0 + (z1 - z0) * fz,
                           0.045, 0.045, 0.09, met)
        if handle:
            zmid = (z0 + z1) / 2
            if along_x:
                hx = x0 + lx * 0.82
                self.box_c(hx, cy + 0.032, zmid, 0.016, 0.055, 0.32,
                           met)
                for sz in (-1, 1):
                    self.box_c(hx, cy + 0.010, zmid + sz * 0.13,
                               0.014, 0.035, 0.028, met)
            else:
                hy = y0 + ly * 0.82
                self.box_c(cx + 0.032, hy, zmid, 0.055, 0.016, 0.32,
                           met)
                for sz in (-1, 1):
                    self.box_c(cx + 0.010, hy, zmid + sz * 0.13,
                               0.035, 0.014, 0.028, met)

    def _build_shower(self):
        p = self.props
        cer, met, gla = p.mat_ceramic, p.mat_metal, p.mat_glass
        w = max(p.width, 0.70)
        d = max(p.depth, 0.70)
        h = max(p.height, 1.80)
        th = max(p.tray_height, 0.02)
        x0, x1 = -w / 2, w / 2

        # plato + borde + desagüe de esquina
        self.box_c(0, d / 2, th / 2, w, d, th, cer)
        self._rim_ring(0, d / 2, th, w, d, 0.055, 0.014, cer)
        self.box_c(x1 - 0.16, d - 0.16, th + 0.004,
                   0.12, 0.12, 0.009, met)
        self.box_c(x1 - 0.16, d - 0.16, th + 0.009,
                   0.07, 0.07, 0.004, cer)

        # muros opcionales (fondo + lateral izquierdo)
        if p.build_walls:
            wt = 0.06
            self.box_c(0, d - wt / 2, (th + h) / 2, w, wt, h - th,
                       cer)
            self.box_c(x0 + wt / 2, d / 2, (th + h) / 2, wt, d,
                       h - th, cer)

        # vidrios
        gz0, gz1 = th + 0.01, h - 0.08
        if p.glass_enable and p.enclosure == 'WALKIN':
            self._glass_panel(x0, x0 + w * 0.55, 0.0, 0.0, gz0, gz1,
                              gla, met)
            self.box_c(x0 + w * 0.55, 0.0, gz1 + 0.02, 0.03, 0.03,
                       0.05, met)
        elif p.glass_enable and p.enclosure in ('CORNER', 'ALCOVE'):
            fw = w * 0.52
            self._glass_panel(x0, x0 + fw, 0.0, 0.0, gz0, gz1,
                              gla, met)
            if p.door_type == 'HINGED':
                self._glass_panel(x0 + fw + 0.015, x1, 0.0, 0.0, gz0,
                                  gz1, gla, met, handle=True,
                                  hinge_side=-1)
            elif p.door_type == 'SLIDING':
                self.box_c(0, 0.0, gz1 + 0.025, w - 0.04, 0.045,
                           0.05, met)
                self._glass_panel(x0 + fw - 0.06, x1 - 0.02, 0.028,
                                  0.028, gz0, gz1, gla, met,
                                  handle=True)
            # OPEN = hueco de entrada, sin hoja
            if p.enclosure == 'CORNER':
                self._glass_panel(x1, x1, d * 0.30, d, gz0, gz1,
                                  gla, met)

        # columna termostática + barra + lluvia + manual
        col_x = -w * 0.22
        self.box_c(col_x, d - 0.045, 1.02, 0.26, 0.055, 0.055, met)
        for sx in (-1, 1):
            self.box_c(col_x + sx * 0.148, d - 0.045, 1.02,
                       0.045, 0.060, 0.060, met)
        self.box_c(col_x, d - 0.040, 1.55, 0.035, 0.035, 1.06, met)
        self.box_c(col_x, d - 0.055, 1.45, 0.06, 0.06, 0.09, met)
        if p.rain_head:
            self.box_c(0, d - 0.17, h - 0.22, 0.035, 0.30, 0.035,
                       met)
            self.cyl(0, d - 0.30, h - 0.27, h - 0.22, 0.016, 10,
                     met)
            self.cyl(0, d - 0.30, h - 0.295, h - 0.270, 0.105, 24,
                     met)
            self.cyl(0, d - 0.30, h - 0.300, h - 0.295, 0.095, 24,
                     cer)
        if p.hand_shower:
            self.cyl(col_x + 0.10, d - 0.10, 1.32, 1.50, 0.023, 12,
                     met)
            self.cone(col_x + 0.10, d - 0.10, 1.50, 1.58, 0.023,
                      0.055, 14, met)
            self.box_c(col_x + 0.10, d - 0.085, 0.75, 0.014, 0.014,
                       1.10, met)
        if p.shower_shelf:
            self.box_c(x0 + 0.20, d - 0.20, 1.30, 0.26, 0.16,
                       0.018, gla)
            self.box_c(x0 + 0.20, d - 0.20, 1.16, 0.20, 0.12, 0.10,
                       cer)

    # ════════════════════════════════════════════════════════
    #  BAÑERA
    # ════════════════════════════════════════════════════════
    def _build_bathtub(self):
        p = self.props
        cer, met, gla = p.mat_ceramic, p.mat_metal, p.mat_glass
        w = max(p.width, 0.60)     # ancho (X)
        L = max(p.depth, 1.20)     # largo (Y)
        h = max(p.height, 0.45)
        rim = max(p.rim_width, 0.03)
        y0, y1 = -L / 2, L / 2
        base = 0.10 if p.tub_freestanding else 0.0

        if p.tub_freestanding:
            for sx in (-1, 1):
                for sy in (-1, 1):
                    self.cone(sx * (w / 2 - 0.14),
                              sy * (L / 2 - 0.22),
                              0.0, base + 0.02, 0.055, 0.040, 12,
                              met)
        # carcasa + borde + fondo interior
        self.box_c(0, 0, (base + h) / 2, w, L, h - base, cer)
        self._rim_ring(0, 0, h, w + 0.02, L + 0.02, rim + 0.01,
                       0.045, cer)
        iw, il = w - 2 * rim, L - 2 * rim
        inner_floor = base + 0.14
        self.box_c(0, 0, inner_floor - 0.02, iw, il, 0.05, cer)
        # pozo de desagüe + rebalse
        self._drain(0, -il / 2 + 0.18, inner_floor + 0.008,
                    r=0.036, mi_met=met)
        self.box_c(0, -il / 2 + 0.006, h - 0.16, 0.06, 0.014, 0.09,
                   met)
        if p.tub_water:
            self.box_c(0, 0, h - 0.13, iw - 0.02, il - 0.02, 0.008,
                       gla)

        # faldón para empotrada (frente + lateral)
        if not p.tub_freestanding and p.tub_apron:
            self.box_c(0, y0 - 0.015, (h - 0.05) / 2, w + 0.02,
                       0.03, h - 0.05, cer)
            self.box_c(-w / 2 - 0.015, 0, (h - 0.05) / 2, 0.03, L,
                       h - 0.05, cer)
            self.box_c(0, y0 - 0.032, h * 0.35, 0.50, 0.006, 0.40,
                       cer)

        # grifería
        if p.tub_faucet == 'DECK':
            self._two_handle_faucet(0, y1 - rim / 2, h + 0.045,
                                    spread=0.22, mi_met=met)
        elif p.tub_faucet == 'WALL':
            wy = y1 + 0.03
            self.box_c(0, wy - 0.10, h + 0.08, 0.045, 0.26, 0.045,
                       met)
            self.cyl(0, wy - 0.20, h - 0.02, h + 0.08, 0.016, 10,
                     met)
            self.box_c(0, wy, h - 0.20, 0.10, 0.025, 0.18, met)
            self.cyl(0, wy - 0.012, h - 0.24, h - 0.10, 0.030, 12,
                     met)
        elif p.tub_faucet == 'FLOOR':
            fx = w / 2 + 0.12
            fy = y1 - 0.25
            self.cyl(fx, fy, 0.0, h + 0.25, 0.024, 14, met)
            self.cone(fx, fy, 0.0, 0.06, 0.045, 0.028, 12, met)
            self.box_c(fx - 0.13, fy, h + 0.22, 0.26, 0.04, 0.04,
                       met)
            self.cyl(fx - 0.24, fy, h + 0.05, h + 0.22, 0.014, 10,
                     met)
            self.box_c(fx, fy + 0.09, 0.55, 0.06, 0.06, 0.12, met)
            self.cone(fx, fy + 0.09, 0.61, 0.68, 0.026, 0.048, 12,
                      met)

    # ════════════════════════════════════════════════════════
    #  ESPEJO
    # ════════════════════════════════════════════════════════
    def _build_mirror(self):
        p = self.props
        mir, met = p.mat_mirror, p.mat_metal
        gla, cab = p.mat_glass, p.mat_cabinet
        emi = p.mat_emissive
        w = max(p.width, 0.30)
        h = max(p.height, 0.40)
        z0 = max(p.mount_height, 0.0)
        cz = z0 + h / 2
        dep = max(p.depth, 0.03)

        if p.mirror_cabinet:
            self.box_c(0, dep / 2, cz, w, dep, h, cab)
            for sx in (-1, 1):
                self.box_c(sx * w / 4, dep + 0.008, cz,
                           w / 2 - 0.006, 0.016, h - 0.01, mir)
                self.box_c(sx * 0.035, dep + 0.022, cz,
                           0.014, 0.018, 0.22, met)
        else:
            self.box_c(0, 0.012, cz, w, 0.024, h, mir)
            if p.mirror_frame:
                ft = 0.035
                self.box_c(0, 0.014, z0 + h + ft / 2 - 0.005,
                           w + 2 * ft, 0.035, ft, cab)
                self.box_c(0, 0.014, z0 - ft / 2 + 0.005,
                           w + 2 * ft, 0.035, ft, cab)
                for sx in (-1, 1):
                    self.box_c(sx * (w / 2 + ft / 2), 0.014, cz,
                               ft, 0.035, h, cab)
            if p.mirror_led:
                self.box_c(0, -0.002, cz, w + 0.035, 0.012,
                           h + 0.035, emi)
                self.box_c(0, 0.055, z0 + h + 0.09, w * 0.6,
                           0.035, 0.035, met)
                self.box_c(0, 0.055, z0 + h + 0.068, w * 0.55,
                           0.020, 0.012, emi)
                for sx in (-1, 1):
                    self.box_c(sx * w * 0.25, 0.030, z0 + h + 0.09,
                               0.020, 0.060, 0.020, met)

        if p.mirror_shelf:
            sy = dep + 0.085 if p.mirror_cabinet else 0.10
            self.box_c(0, sy, z0 - 0.035, w * 0.7, 0.13, 0.014,
                       gla)
            for sx in (-1, 1):
                self.box_c(sx * w * 0.28, sy - 0.02, z0 - 0.075,
                           0.016, 0.10, 0.07, met)

    # ════════════════════════════════════════════════════════
    #  TOALLERO
    # ════════════════════════════════════════════════════════
    def _build_towel_rail(self):
        p = self.props
        met, cab = p.mat_metal, p.mat_cabinet
        emi = p.mat_emissive
        w = max(p.width, 0.30)
        h = max(p.height, 0.40)
        d = max(p.depth, 0.08)
        z0 = max(p.mount_height, 0.0)
        n = max(2, min(p.towel_bars, 9))
        cx = w / 2 - 0.03
        cy = d - 0.02

        for sx in (-1, 1):
            self.cyl(sx * cx, cy, z0, z0 + h, 0.021, 14, met)
            self.sph(sx * cx, cy, z0, 0.024, 10, 8, met)
            self.sph(sx * cx, cy, z0 + h, 0.024, 10, 8, met)
        for i in range(n):
            fz = z0 + 0.08 + (h - 0.16) * (i / (n - 1))
            self.box_c(0, cy, fz, w - 0.06, 0.024, 0.024, met)
        for sz in (z0 + 0.12, z0 + h - 0.12):
            for sx in (-1, 1):
                self.box_c(sx * cx, cy / 2, sz, 0.030, cy, 0.030,
                           met)
                self.box_c(sx * cx, 0.008, sz, 0.050, 0.016,
                           0.070, met)
        self.cyl(cx, cy, z0 - 0.09, z0, 0.018, 10, met)
        self.box_c(cx, cy, z0 - 0.115, 0.05, 0.05, 0.05, met)

        if p.rail_electric:
            ex = -cx
            self.box_c(ex, 0.05, z0 + 0.25, 0.07, 0.05, 0.11, met)
            self.box_c(ex, 0.078, z0 + 0.27, 0.02, 0.008, 0.02,
                       emi)
            self.box_c(ex, 0.015, (0.05 + z0 + 0.20) / 2,
                       0.016, 0.014, max(z0 + 0.15, 0.05), met)

        if p.towel_enable:
            tz = z0 + h * 0.55
            self.box_c(0, cy, tz + 0.10, w * 0.55, 0.05, 0.24,
                       cab)
            self.box_c(0, cy - 0.08, tz + 0.06, w * 0.55, 0.05,
                       0.16, cab)
            self.box_c(0, cy - 0.04, tz + 0.215, w * 0.55, 0.13,
                       0.03, cab)

    # DUCHA ELÉCTRICA (CO)
    def _build_electric_shower(self):
        p = self.props
        cer, met = p.mat_ceramic, p.mat_metal
        dia = max(p.width, 0.10)
        reach = max(p.depth, 0.15)
        hz = max(p.mount_height, 1.20)
        self.cyl(0, 0.01, hz + 0.06, hz + 0.10, 0.028, 14, met)
        self.box_c(0, reach / 2, hz + 0.08, 0.035, reach,
                   0.035, met)
        self.cyl(0, 0.01, hz + 0.10, hz + 0.45, 0.008, 8, met)
        self.cone(0, reach, hz - 0.02, hz + 0.08, dia / 2,
                  dia * 0.22, 24, cer)
        self.cyl(0, reach, hz - 0.035, hz - 0.02, dia / 2, 24,
                 cer)
        self.tor(0, reach, hz - 0.035, dia / 2 - 0.004, 0.006,
                 24, 8, cer)
        sc = dia / 0.18
        for ox, oy in ((0, 0), (0.045, 0), (-0.045, 0),
                       (0, 0.045), (0, -0.045), (0.032, 0.032),
                       (-0.032, -0.032)):
            self.cyl(ox * sc, reach + oy * sc, hz - 0.045,
                     hz - 0.035, 0.006, 8, met)
        self.box_c(0, reach - dia / 2 - 0.008, hz + 0.03,
                   0.05, 0.016, 0.05, met)
        ang = -0.6 + p.ducha_level * 0.4
        self.box_c(math.sin(ang) * 0.012,
                   reach - dia / 2 - 0.017,
                   hz + 0.03 + math.cos(ang) * 0.012, 0.008,
                   0.006, 0.020, cer)

    def generate(self):
        t = self.props.item_type
        if t == 'TOILET':
            self._build_toilet()
        elif t == 'BIDET':
            self._build_bidet()
        elif t == 'PEDESTAL_SINK':
            self._build_pedestal_sink()
        elif t == 'VANITY':
            self._build_vanity()
        elif t == 'WALLHUNG_BASIN':
            self._build_wallhung_basin()
        elif t == 'SHOWER':
            self._build_shower()
        elif t == 'BATHTUB':
            self._build_bathtub()
        elif t == 'MIRROR':
            self._build_mirror()
        elif t == 'TOWEL_RAIL':
            self._build_towel_rail()
        elif t == 'ELECTRIC_SHOWER':
            self._build_electric_shower()
        return self.b


# ════════════════════════════════════════════════════════════
#  UPDATE / REBUILD
# ════════════════════════════════════════════════════════════
def _find_bathroom_object(props):
    name = props.object_name
    if name and name in bpy.data.objects:
        return bpy.data.objects[name]
    for obj in bpy.data.objects:
        if (obj.type == 'MESH'
                and hasattr(obj, AF_BATH_PROP)
                and getattr(obj, AF_BATH_PROP) is props):
            try:
                props.object_name = obj.name
            except Exception:
                pass
            return obj
    return None


def _rebuild_bathroom_mesh(obj, props):
    gen = AF_BathroomGenerator(props)
    builder = gen.generate()
    if builder is None:
        return
    builder.finalize(obj.data)
    mesh = obj.data
    # shade smooth + auto_smooth: curvas suaves, cajas nítidas.
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


# ════════════════════════════════════════════════════════════
#  MATERIALES
# ════════════════════════════════════════════════════════════
def _setup_bathroom_materials(obj):
    af_material.ensure_af_materials_for_object(obj, [
        "AF.Bath.Ceramic",
        "AF.Bath.Metal",
        "AF.Bath.Glass",
        "AF.Bath.Cabinet",
        "AF.Bath.Mirror",
        "AF.Bath.Emissive",
    ])
    _tune_bath_materials()


def _tune_bath_materials():
    """Ajusta nodos Principled (si existen). Nunca falla."""
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

    _tune("AF.Bath.Ceramic", base=(0.96, 0.96, 0.97, 1.0),
          metallic=0.0, rough=0.15)
    _tune("AF.Bath.Metal", base=(0.9, 0.9, 0.92, 1.0),
          metallic=1.0, rough=0.12)
    _tune("AF.Bath.Glass", base=(0.9, 0.95, 0.95, 1.0),
          metallic=0.0, rough=0.05, transmission=1.0)
    _tune("AF.Bath.Cabinet", base=(0.45, 0.30, 0.18, 1.0),
          metallic=0.0, rough=0.6)
    _tune("AF.Bath.Mirror", base=(0.95, 0.96, 0.98, 1.0),
          metallic=1.0, rough=0.03)
    _tune("AF.Bath.Emissive", base=(0.0, 0.0, 0.0, 1.0),
          emission=(1.0, 0.97, 0.92, 1.0), emission_strength=3.0)


# ════════════════════════════════════════════════════════════
#  CREACIÓN
# ════════════════════════════════════════════════════════════
def _create_bathroom_object(context, name="AF_Bathroom"):
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
        props = obj.archiforge_bathroom
        props.is_af_bathroom = True
        props.object_name = obj.name
        props.af_version = AF_BATH_VERSION
    finally:
        _SUSPEND = False

    _setup_bathroom_materials(obj)
    return obj, props


def _apply_type_defaults(props, item_type):
    """Dimensiones reales según tipo (respeta cabinet si existe)."""
    global _SUSPEND
    w, d, h = AF_BATH_DEFAULTS.get(item_type, (0.5, 0.5, 0.9))
    _SUSPEND = True
    try:
        props.width = w
        props.depth = d
        props.height = h
        if item_type == 'VANITY':
            props.cabinet_depth = 0.46
            props.cabinet_height = 0.58
        if item_type in ('MIRROR',):
            props.mount_height = 1.10
        elif item_type in ('TOWEL_RAIL',):
            props.mount_height = 0.55
        elif item_type in ('ELECTRIC_SHOWER',):
            props.mount_height = 2.00
    finally:
        _SUSPEND = False


# ════════════════════════════════════════════════════════════
#  OPERADORES
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_OT_bathroom(Operator):
    bl_idname = "archiforge.bathroom"
    bl_label = "Add AF Bathroom"
    bl_description = "Add a parametric ArchiForge bathroom fixture"
    bl_options = {'REGISTER', 'UNDO'}

    item_type : EnumProperty(name="Type", items=AF_BATH_TYPES,
                             default='TOILET')
    auto_dimensions : BoolProperty(
        name="Real-World Dimensions", default=True,
        description="Use real-world default dimensions for the type",
    )
    width : FloatProperty(name="Width", default=0.42, min=0.05,
                          unit='LENGTH')
    depth : FloatProperty(name="Depth", default=0.68, min=0.05,
                          unit='LENGTH')
    height : FloatProperty(name="Height", default=0.82, min=0.05,
                           unit='LENGTH')

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        col = layout.column(align=True)
        col.label(text="New Bathroom Fixture",
                  **_icon(_item_icon(self.item_type, "bathroom"), 'SPHERE'))
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
        obj, props = _create_bathroom_object(context, "AF_Bathroom")
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
        _rebuild_bathroom_mesh(obj, props)
        self.report({'INFO'}, _tr("Bathroom item created: {}").format(obj.name))
        return {'FINISHED'}


class ARCHIFORGE_OT_bathroom_update(Operator):
    bl_idname = "archiforge.bathroom_update"
    bl_label = "Update"
    bl_description = "Force regeneration of the bathroom fixture"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH'
                and hasattr(obj, AF_BATH_PROP)
                and obj.archiforge_bathroom.is_af_bathroom)

    def execute(self, context):
        obj = context.active_object
        _rebuild_bathroom_mesh(obj, obj.archiforge_bathroom)
        self.report({'INFO'}, _tr("Bathroom item updated"))
        return {'FINISHED'}


class ARCHIFORGE_OT_bathroom_reset(Operator):
    bl_idname = "archiforge.bathroom_reset"
    bl_label = "Reset Dimensions"
    bl_description = "Reset to real-world default dimensions"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH'
                and hasattr(obj, AF_BATH_PROP)
                and obj.archiforge_bathroom.is_af_bathroom)

    def execute(self, context):
        obj = context.active_object
        props = obj.archiforge_bathroom
        _apply_type_defaults(props, props.item_type)
        _rebuild_bathroom_mesh(obj, props)
        self.report({'INFO'}, _tr("Dimensions reset to defaults"))
        return {'FINISHED'}


# ════════════════════════════════════════════════════════════
#  PANEL
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_PT_bathroom(Panel):
    bl_label = "Bathroom Properties"
    bl_idname = "ARCHIFORGE_PT_bathroom"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "ArchiForge"
    bl_context = "objectmode"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH'
                and hasattr(obj, AF_BATH_PROP)
                and obj.archiforge_bathroom.is_af_bathroom)

    def draw_header(self, context):
        self.layout.label(text="", **_icon("bathroom", 'SPHERE'))

    def draw(self, context):
        props = context.active_object.archiforge_bathroom
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        t = props.item_type

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Type",
                  **_icon(_item_icon(props.item_type, "bathroom"), 'MODIFIER'))
        col.prop(props, "item_type", text="")
        col.prop(props, "mesh_quality", text="Quality")

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Dimensions", icon='ARROW_LEFTRIGHT')
        col.prop(props, "width")
        col.prop(props, "depth")
        col.prop(props, "height")
        if t in ('TOILET', 'BIDET', 'MIRROR', 'TOWEL_RAIL',
                 'ELECTRIC_SHOWER'):
            col.prop(props, "mount_height")
        col.operator("archiforge.bathroom_reset",
                     text="Reset Real Dimensions", icon='LOOP_BACK')

        if t in ('TOILET', 'BIDET'):
            box = layout.box()
            col = box.column(align=True)
            col.label(text="WC Options",
                      **_icon(_item_icon(t, "bathroom"), 'MESH_CUBE'))
            col.prop(props, "toilet_wallhung")
            if props.toilet_wallhung:
                col.prop(props, "concealed_frame")
            if t == 'TOILET':
                col.prop(props, "seat_closed")
            else:
                col.prop(props, "bidet_faucet")

        if t in ('PEDESTAL_SINK', 'WALLHUNG_BASIN'):
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Basin",
                      **_icon(_item_icon(t, "bathroom"), 'SPHERE'))
            col.prop(props, "faucet_enable")
            col.prop(props, "trap_enable")
            if t == 'WALLHUNG_BASIN':
                col.prop(props, "basin_towel_bar")

        if t == 'VANITY':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Cabinet",
                      **_icon(_item_icon(t, "bathroom"), 'MESH_CUBE'))
            col.prop(props, "vanity_style", text="")
            col.prop(props, "basin_type", text="")
            col.prop(props, "cabinet_height")
            col.prop(props, "cabinet_depth")
            col.prop(props, "vanity_handles")
            col.prop(props, "vanity_backsplash")
            col.prop(props, "faucet_enable")
            if props.vanity_style == 'WALLHUNG':
                col.prop(props, "vanity_led")

        if t == 'SHOWER':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Shower",
                      **_icon(_item_icon(t, "bathroom"), 'DRAG_HANDLE'))
            col.prop(props, "enclosure", text="")
            col.prop(props, "tray_height")
            col.prop(props, "build_walls")
            col.prop(props, "glass_enable")
            if props.glass_enable and props.enclosure in (
                    'CORNER', 'ALCOVE'):
                col.prop(props, "door_type")
            col.prop(props, "rain_head")
            col.prop(props, "hand_shower")
            col.prop(props, "shower_shelf")

        if t == 'BATHTUB':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Bathtub",
                      **_icon(_item_icon(t, "bathroom"), 'MESH_UVSPHERE'))
            col.prop(props, "tub_freestanding")
            if not props.tub_freestanding:
                col.prop(props, "tub_apron")
            col.prop(props, "tub_faucet")
            col.prop(props, "rim_width")
            col.prop(props, "tub_water")

        if t == 'MIRROR':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Mirror",
                      **_icon(_item_icon(t, "bathroom"), 'MOD_MIRROR'))
            col.prop(props, "mirror_cabinet")
            if not props.mirror_cabinet:
                col.prop(props, "mirror_frame")
                col.prop(props, "mirror_led")
            col.prop(props, "mirror_shelf")

        if t == 'ELECTRIC_SHOWER':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Ducha (CO)",
                      **_icon(_item_icon(t, "bathroom"), 'DRAG_HANDLE'))
            col.prop(props, "ducha_level")

        if t == 'TOWEL_RAIL':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Towel Rail",
                      **_icon(_item_icon(t, "bathroom"), 'DRIVER'))
            col.prop(props, "towel_bars")
            col.prop(props, "towel_enable")
            col.prop(props, "rail_electric")

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Material Slots", icon='MATERIAL')
        col.prop(props, "mat_ceramic", text="Ceramic")
        col.prop(props, "mat_metal", text="Metal")
        col.prop(props, "mat_glass", text="Glass")
        if t in ('VANITY', 'MIRROR', 'TOWEL_RAIL'):
            col.prop(props, "mat_cabinet", text="Cabinet")
        if t == 'MIRROR':
            col.prop(props, "mat_mirror", text="Mirror")
        if t in ('VANITY', 'MIRROR', 'TOWEL_RAIL', 'SHOWER'):
            col.prop(props, "mat_emissive", text="Emissive")

        layout.separator()
        layout.operator("archiforge.bathroom_update",
                        text="Force Update", icon='FILE_REFRESH')


# ════════════════════════════════════════════════════════════
#  REGISTRO
# ════════════════════════════════════════════════════════════
classes = [
    AF_BathroomProperties,
    ARCHIFORGE_OT_bathroom,
    ARCHIFORGE_OT_bathroom_update,
    ARCHIFORGE_OT_bathroom_reset,
    ARCHIFORGE_PT_bathroom,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Object.archiforge_bathroom = PointerProperty(
        type=AF_BathroomProperties,
        name="ArchiForge Bathroom",
        description="ArchiForge bathroom fixture properties",
    )
    print("[ArchiForge] ✅ af_bathroom v2 — registered")


def unregister():
    if hasattr(bpy.types.Object, "archiforge_bathroom"):
        del bpy.types.Object.archiforge_bathroom
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    print("[ArchiForge] 🔴 af_bathroom — unregistered")

