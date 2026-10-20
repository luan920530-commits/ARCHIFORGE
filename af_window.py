# -*- coding: utf-8 -*-

# ╔══════════════════════════════════════════════════════════╗
# ║         ARCHIFORGE — af_window.py                       ║
# ║         Ventanas Paramétricas para Blender 3.3 LTS      ║
# ║         GPL v3 — ArchiForge Devs                        ║
# ╚══════════════════════════════════════════════════════════╝
# v1.1 — presets CO (ventanería aluminio Colombia)
# v1.2 — hojas batientes/proyectantes giran completas (marco, vidrio y
#        divisiones) alrededor de la bisagra; bisagras físicas sobre el eje;
#        el toggle abrir/cerrar solo se ofrece en CASEMENT y AWNING.

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

from . import af_autoboolean
from . import af_material
from .af_window_geometry import (
    hinge_knuckle_length,
    hinge_positions,
    rotate_point,
    sash_hinge,
    window_type_can_open,
)

try:
    from .af_i18n import tr_report as _tr
except ImportError:  # pragma: no cover - fuera del paquete
    def _tr(text):
        return text


# ════════════════════════════════════════════════════════════
#  CONSTANTES
# ════════════════════════════════════════════════════════════
AF_WIN_PROP   = "archiforge_window"
AF_WIN_MIN_W  = 0.20
AF_WIN_MAX_W  = 8.00
AF_WIN_MIN_H  = 0.20
AF_WIN_MAX_H  = 6.00
AF_WIN_MIN_SH = 0.0
AF_WIN_MAX_SH = 3.0

AF_WIN_TYPES = [
    ('FIXED',       "Fixed",       "Fixed non-opening window",      'MESH_PLANE',    0),
    ('CASEMENT',    "Casement",    "Side-hinged opening window",    'TRIA_RIGHT',    1),
    ('SLIDING',     "Sliding",     "Horizontal sliding window",     'FORWARD',       2),
    ('AWNING',      "Awning",      "Top-hinged projecting window",  'TRIA_UP',       3),
    ('DOUBLE_HUNG', "Double Hung", "Vertical sliding guillotine",   'UV_SYNC_SELECT',4),
    ('ARCH',        "Arch",        "Window with arched top",        'MESH_CIRCLE',   5),
]

AF_WIN_SASH_STYLES = [
    ('SIMPLE',   "Simple",   "Plain glass pane"),
    ('DIVIDED',  "Divided",  "Grid divided panes (grille)"),
    ('COLONIAL', "Colonial", "Colonial style grid"),
]

AF_SILL_TYPES = [
    ('FLAT',   "Flat",   "Simple flat sill"),
    ('SLOPED', "Sloped", "Sloped drip sill"),
    ('MOLDED', "Molded", "Molded decorative sill"),
]

AF_WIN_HINGE_SIDES = [
    ('LEFT',  "Left",  "First leaf hinged on the left jamb "
                       "(adjacent leaves alternate)"),
    ('RIGHT', "Right", "First leaf hinged on the right jamb "
                       "(adjacent leaves alternate)"),
]

AF_WIN_SWING_DIRECTIONS = [
    ('OUT', "Outward", "Leaf projects to the exterior (-Y)"),
    ('IN',  "Inward",  "Leaf swings into the room (+Y)"),
]

AF_WIN_CO_PRESETS = [
    ('CUSTOM',   "Custom",   "Medidas manuales"),
    ('V100x100', "1.00x1.00 Baño",   "Ventanilla baño"),
    ('V120x120', "1.20x1.20",        "Ventana típica CO"),
    ('V150x120', "1.50x1.20",        "Ventana alcoba"),
    ('V200x140', "2.00x1.40 Sala",   "Ventana sala"),
    ('V240x220', "2.40x2.20 Balcón", "Puerta-ventana"),
]

AF_WIN_CO_DIMS = {
    'V100x100': (1.00, 1.00, 1.20),
    'V120x120': (1.20, 1.20, 0.90),
    'V150x120': (1.50, 1.20, 0.90),
    'V200x140': (2.00, 1.40, 0.60),
    'V240x220': (2.40, 2.20, 0.10),
}


# ════════════════════════════════════════════════════════════
#  PROPERTYGROUP
# ════════════════════════════════════════════════════════════
class AF_WindowProperties(PropertyGroup):

    is_af_window : BoolProperty(
        name="Is ArchiForge Window", default=True, options={'HIDDEN'},
    )
    object_name : StringProperty(
        name="Object Name", default="", options={'HIDDEN'},
    )

    window_type : EnumProperty(
        name="Window Type", items=AF_WIN_TYPES, default='CASEMENT',
        update=lambda s, c: af_window_update(s, c),
    )

    co_preset : EnumProperty(
        name="CO Preset", items=AF_WIN_CO_PRESETS, default='CUSTOM',
        update=lambda s, c: af_win_co_preset_update(s, c),
    )

    width : FloatProperty(
        name="Width", default=1.20,
        min=AF_WIN_MIN_W, max=AF_WIN_MAX_W,
        unit='LENGTH', update=lambda s, c: af_window_update(s, c),
    )
    height : FloatProperty(
        name="Height", default=1.20,
        min=AF_WIN_MIN_H, max=AF_WIN_MAX_H,
        unit='LENGTH', update=lambda s, c: af_window_update(s, c),
    )
    sill_height : FloatProperty(
        name="Sill Height", default=0.90,
        min=AF_WIN_MIN_SH, max=AF_WIN_MAX_SH,
        unit='LENGTH', update=lambda s, c: af_window_update(s, c),
    )

    frame_width : FloatProperty(
        name="Frame Width", default=0.07, min=0.01, max=0.25,
        unit='LENGTH', update=lambda s, c: af_window_update(s, c),
    )
    frame_depth : FloatProperty(
        name="Frame Depth", default=0.12, min=0.02, max=0.40,
        unit='LENGTH', update=lambda s, c: af_window_update(s, c),
    )
    frame_offset : FloatProperty(
        name="Frame Offset", default=0.0, min=-0.15, max=0.15,
        unit='LENGTH', update=lambda s, c: af_window_update(s, c),
    )

    h_panels : IntProperty(
        name="Horizontal Panels", default=1, min=1, max=6,
        update=lambda s, c: af_window_update(s, c),
    )
    v_panels : IntProperty(
        name="Vertical Panels", default=1, min=1, max=6,
        update=lambda s, c: af_window_update(s, c),
    )
    mullion_width : FloatProperty(
        name="Mullion Width", default=0.05, min=0.01, max=0.15,
        unit='LENGTH', update=lambda s, c: af_window_update(s, c),
    )

    sash_style : EnumProperty(
        name="Sash Style", items=AF_WIN_SASH_STYLES, default='SIMPLE',
        update=lambda s, c: af_window_update(s, c),
    )
    sash_width : FloatProperty(
        name="Sash Width", default=0.04, min=0.01, max=0.12,
        unit='LENGTH', update=lambda s, c: af_window_update(s, c),
    )
    sash_depth : FloatProperty(
        name="Sash Depth", default=0.04, min=0.01, max=0.15,
        unit='LENGTH', update=lambda s, c: af_window_update(s, c),
    )

    grille_rows  : IntProperty(
        name="Grille Rows", default=2, min=1, max=8,
        update=lambda s, c: af_window_update(s, c),
    )
    grille_cols  : IntProperty(
        name="Grille Columns", default=2, min=1, max=8,
        update=lambda s, c: af_window_update(s, c),
    )
    grille_width : FloatProperty(
        name="Grille Bar Width", default=0.015, min=0.005, max=0.05,
        unit='LENGTH', update=lambda s, c: af_window_update(s, c),
    )

    glass_thickness : FloatProperty(
        name="Glass Thickness", default=0.006, min=0.003, max=0.02,
        unit='LENGTH', update=lambda s, c: af_window_update(s, c),
    )

    open_angle : FloatProperty(
        name="Open Angle", default=0.0,
        description="Rotation of hinged sashes (CASEMENT / AWNING only)",
        min=0.0, max=math.radians(90),
        subtype='ANGLE', update=lambda s, c: af_window_update(s, c),
    )
    hinge_side : EnumProperty(
        name="Hinge Side", items=AF_WIN_HINGE_SIDES, default='LEFT',
        description="Hinge jamb of the first casement leaf",
        update=lambda s, c: af_window_update(s, c),
    )
    swing_direction : EnumProperty(
        name="Swing", items=AF_WIN_SWING_DIRECTIONS, default='OUT',
        description="Direction in which casement leaves open",
        update=lambda s, c: af_window_update(s, c),
    )
    hinge_enable : BoolProperty(
        name="Hinges", default=True,
        description="Generate hinge knuckles centred on the rotation axis",
        update=lambda s, c: af_window_update(s, c),
    )
    hinge_radius : FloatProperty(
        name="Hinge Radius", default=0.006, min=0.003, max=0.02,
        unit='LENGTH', update=lambda s, c: af_window_update(s, c),
    )
    hinge_length : FloatProperty(
        name="Hinge Length", default=0.06, min=0.02, max=0.20,
        unit='LENGTH', update=lambda s, c: af_window_update(s, c),
    )

    arch_height   : FloatProperty(
        name="Arch Height", default=0.30, min=0.05, max=2.0,
        unit='LENGTH', update=lambda s, c: af_window_update(s, c),
    )
    arch_segments : IntProperty(
        name="Arch Segments", default=12, min=4, max=32,
        update=lambda s, c: af_window_update(s, c),
    )

    outer_sill_enable : BoolProperty(
        name="Outer Sill", default=True,
        update=lambda s, c: af_window_update(s, c),
    )
    outer_sill_type : EnumProperty(
        name="Sill Type", items=AF_SILL_TYPES, default='SLOPED',
        update=lambda s, c: af_window_update(s, c),
    )
    outer_sill_width : FloatProperty(
        name="Sill Width", default=0.15, min=0.02, max=0.50,
        unit='LENGTH', update=lambda s, c: af_window_update(s, c),
    )
    outer_sill_height : FloatProperty(
        name="Sill Height", default=0.05, min=0.01, max=0.20,
        unit='LENGTH', update=lambda s, c: af_window_update(s, c),
    )

    inner_sill_enable : BoolProperty(
        name="Inner Sill", default=True,
        update=lambda s, c: af_window_update(s, c),
    )
    inner_sill_width : FloatProperty(
        name="Inner Sill Width", default=0.20, min=0.02, max=0.60,
        unit='LENGTH', update=lambda s, c: af_window_update(s, c),
    )
    inner_sill_height : FloatProperty(
        name="Inner Sill Height", default=0.03, min=0.005, max=0.15,
        unit='LENGTH', update=lambda s, c: af_window_update(s, c),
    )

    shutter_enable : BoolProperty(
        name="Shutters", default=False,
        update=lambda s, c: af_window_update(s, c),
    )
    shutter_open : BoolProperty(
        name="Shutters Open", default=True,
        update=lambda s, c: af_window_update(s, c),
    )
    shutter_depth : FloatProperty(
        name="Shutter Depth", default=0.03, min=0.01, max=0.10,
        unit='LENGTH', update=lambda s, c: af_window_update(s, c),
    )

    bars_enable : BoolProperty(
        name="Security Bars", default=False,
        update=lambda s, c: af_window_update(s, c),
    )
    bars_count  : IntProperty(
        name="Bar Count", default=4, min=1, max=20,
        update=lambda s, c: af_window_update(s, c),
    )
    bars_radius : FloatProperty(
        name="Bar Radius", default=0.012, min=0.005, max=0.05,
        unit='LENGTH', update=lambda s, c: af_window_update(s, c),
    )
    bars_offset : FloatProperty(
        name="Bars Offset", default=0.10, min=0.02, max=0.50,
        unit='LENGTH', update=lambda s, c: af_window_update(s, c),
    )

    auto_boolean : BoolProperty(
        name="Auto Boolean",
        description="Automatically cut opening in nearest wall",
        default=True,
    )

    mat_frame      : IntProperty(name="Frame Material",      default=0, min=0)
    mat_sash       : IntProperty(name="Sash Material",       default=1, min=0)
    mat_glass      : IntProperty(name="Glass Material",      default=2, min=0)
    mat_outer_sill : IntProperty(name="Outer Sill Material", default=3, min=0)
    mat_inner_sill : IntProperty(name="Inner Sill Material", default=4, min=0)
    mat_shutter    : IntProperty(name="Shutter Material",    default=5, min=0)
    mat_bars       : IntProperty(name="Bars Material",       default=6, min=0)
    mat_hinge      : IntProperty(name="Hinge Material",      default=6, min=0)


# ════════════════════════════════════════════════════════════
#  GENERADOR
# ════════════════════════════════════════════════════════════
class AF_WindowGenerator:

    def __init__(self, props):
        self.props = props
        self.bm    = bmesh.new()

    def _box(self, x0, x1, y0, y1, z0, z1, mat_idx=0):
        bm = self.bm
        if abs(x1 - x0) < 0.0001 or abs(z1 - z0) < 0.0001:
            return
        verts = [
            bm.verts.new(Vector((x0, y0, z0))),
            bm.verts.new(Vector((x1, y0, z0))),
            bm.verts.new(Vector((x1, y1, z0))),
            bm.verts.new(Vector((x0, y1, z0))),
            bm.verts.new(Vector((x0, y0, z1))),
            bm.verts.new(Vector((x1, y0, z1))),
            bm.verts.new(Vector((x1, y1, z1))),
            bm.verts.new(Vector((x0, y1, z1))),
        ]
        for fi in [(0,1,5,4),(2,3,7,6),(0,3,2,1),
                   (4,5,6,7),(0,4,7,3),(1,2,6,5)]:
            f = bm.faces.new([verts[i] for i in fi])
            f.material_index = mat_idx
        bm.verts.ensure_lookup_table()

    def _glass_pane(self, x0, x1, z0, z1, y_center, thickness, mat_idx):
        half_t = thickness / 2.0
        self._box(x0, x1, y_center - half_t,
                  y_center + half_t, z0, z1, mat_idx)

    def _build_frame(self):
        p   = self.props
        w   = p.width
        h   = p.height
        fw  = p.frame_width
        fd  = p.frame_depth
        off = p.frame_offset
        mi  = p.mat_frame
        sh  = p.sill_height

        y0     = off - fd / 2.0
        y1     = off + fd / 2.0
        z_base = sh
        z_top  = sh + h

        self._box(-fw, 0.0,    y0, y1, z_base, z_top, mi)
        self._box(w, w + fw,   y0, y1, z_base, z_top, mi)
        self._box(-fw, w + fw, y0, y1, z_base - fw, z_base, mi)

        if p.window_type != 'ARCH':
            self._box(-fw, w + fw, y0, y1, z_top, z_top + fw, mi)
        else:
            self._build_arch_frame(y0, y1, z_top, mi)

    def _build_arch_frame(self, y0, y1, z_spring, mi):
        p    = self.props
        w    = p.width
        fw   = p.frame_width
        ah   = p.arch_height
        segs = p.arch_segments
        bm   = self.bm

        cx  = w / 2.0
        r   = (w * w / 4.0 + ah * ah) / (2.0 * ah)
        z_c = z_spring + ah - r

        a_start    = math.asin((z_spring - z_c) / r)
        a_end      = math.pi - a_start
        angle_step = (a_end - a_start) / segs

        for i in range(segs):
            a0 = a_start + i * angle_step
            a1 = a_start + (i + 1) * angle_step

            x0_out = cx + (r + fw) * math.cos(a0)
            z0_out = z_c + (r + fw) * math.sin(a0)
            x1_out = cx + (r + fw) * math.cos(a1)
            z1_out = z_c + (r + fw) * math.sin(a1)

            x0_in  = cx + r * math.cos(a0)
            z0_in  = z_c + r * math.sin(a0)
            x1_in  = cx + r * math.cos(a1)
            z1_in  = z_c + r * math.sin(a1)

            verts = [
                bm.verts.new(Vector((x0_out, y0, z0_out))),
                bm.verts.new(Vector((x1_out, y0, z1_out))),
                bm.verts.new(Vector((x1_in,  y0, z1_in))),
                bm.verts.new(Vector((x0_in,  y0, z0_in))),
                bm.verts.new(Vector((x0_out, y1, z0_out))),
                bm.verts.new(Vector((x1_out, y1, z1_out))),
                bm.verts.new(Vector((x1_in,  y1, z1_in))),
                bm.verts.new(Vector((x0_in,  y1, z0_in))),
            ]
            bm.verts.ensure_lookup_table()
            for fi in [(0,1,5,4),(3,2,6,7),(0,3,7,4),
                       (1,2,6,5),(0,1,2,3),(4,5,6,7)]:
                f = bm.faces.new([verts[i] for i in fi])
                f.material_index = mi

    def _build_mullions(self):
        p   = self.props
        w   = p.width
        h   = p.height
        fd  = p.frame_depth
        off = p.frame_offset
        mw  = p.mullion_width
        sh  = p.sill_height
        hpa = p.h_panels
        vpa = p.v_panels
        mi  = p.mat_frame

        y0     = off - fd / 2.0
        y1     = off + fd / 2.0
        z_base = sh
        z_top  = sh + h

        if hpa > 1:
            pane_h = h / hpa
            for i in range(1, hpa):
                z_m = z_base + i * pane_h
                self._box(0.0, w, y0, y1, z_m - mw/2, z_m + mw/2, mi)

        if vpa > 1:
            pane_w = w / vpa
            for i in range(1, vpa):
                x_m = i * pane_w
                self._box(x_m - mw/2, x_m + mw/2, y0, y1, z_base, z_top, mi)

    def _build_sashes(self):
        p   = self.props
        w   = p.width
        h   = p.height
        fd  = p.frame_depth
        off = p.frame_offset
        sw  = p.sash_width
        sd  = p.sash_depth
        gt  = p.glass_thickness
        sh  = p.sill_height
        hpa = p.h_panels
        vpa = p.v_panels
        mw  = p.mullion_width

        mi_sash  = p.mat_sash
        mi_glass = p.mat_glass

        y_sash_outer = off + fd / 2.0 - sd
        y_sash_inner = off + fd / 2.0
        # The glazing sits in the middle of the sash depth so it travels
        # with the sash when the leaf rotates.
        y_glass      = (y_sash_outer + y_sash_inner) / 2.0

        z_base = sh

        pane_w = w / vpa
        pane_h = h / hpa

        for row in range(hpa):
            for col in range(vpa):
                px0 = col * pane_w + (mw / 2 if col > 0 else 0)
                px1 = (col + 1) * pane_w - (mw / 2 if col < vpa - 1 else 0)
                pz0 = z_base + row * pane_h + (mw / 2 if row > 0 else 0)
                pz1 = z_base + (row + 1) * pane_h - (mw / 2 if row < hpa - 1 else 0)

                self._build_sash_leaf(
                    col, px0, px1, pz0, pz1,
                    y_sash_outer, y_sash_inner, y_glass,
                    sw, gt, mi_sash, mi_glass,
                )

    def _build_sash_leaf(self, col, px0, px1, pz0, pz1,
                         y_sash_outer, y_sash_inner, y_glass,
                         sw, gt, mi_sash, mi_glass):
        """Build one leaf closed, then rotate every new vertex as a rigid body.

        Stiles, rails, glass and grille are created in the closed position;
        the vertex range added here is rotated afterwards around the hinge
        axis returned by ``sash_hinge`` so the whole leaf swings together.
        Hinge knuckles are generated last, centred on that same axis, and
        therefore stay fixed to the frame.
        """
        p  = self.props
        bm = self.bm

        hinge = sash_hinge(
            p.window_type, px0, px1, pz0, pz1,
            y_sash_outer, y_sash_inner, p.open_angle,
            hinge_side=p.hinge_side, column=col,
            swing=p.swing_direction,
        )

        bm.verts.ensure_lookup_table()
        n_before = len(bm.verts)

        self._box(px0, px0+sw, y_sash_outer, y_sash_inner, pz0, pz1, mi_sash)
        self._box(px1-sw, px1, y_sash_outer, y_sash_inner, pz0, pz1, mi_sash)
        self._box(px0, px1, y_sash_outer, y_sash_inner, pz0, pz0+sw, mi_sash)
        self._box(px0, px1, y_sash_outer, y_sash_inner, pz1-sw, pz1, mi_sash)

        self._glass_pane(
            px0+sw, px1-sw, pz0+sw, pz1-sw,
            y_glass, gt, mi_glass
        )

        if p.sash_style in ('DIVIDED', 'COLONIAL'):
            self._build_grille(
                px0+sw, px1-sw, pz0+sw, pz1-sw,
                y_glass, gt, mi_sash
            )

        if hinge is not None:
            self._rotate_verts_since(n_before, hinge)
            if p.hinge_enable:
                self._build_hinges(hinge, px0, px1, pz0, pz1)

    def _rotate_verts_since(self, n_before, hinge):
        """Apply the leaf rotation to every vertex created after ``n_before``."""
        if hinge is None or abs(hinge.angle) < 1e-6:
            return
        bm = self.bm
        bm.verts.ensure_lookup_table()
        for i in range(n_before, len(bm.verts)):
            v = bm.verts[i]
            v.co = Vector(rotate_point((v.co.x, v.co.y, v.co.z), hinge))

    def _build_hinges(self, hinge, px0, px1, pz0, pz1):
        """Knuckles centred on the hinge axis (never rotated with the leaf)."""
        p      = self.props
        length = hinge_knuckle_length(
            hinge, px0, px1, pz0, pz1, p.hinge_length)
        if length < 0.004:
            return
        for center in hinge_positions(hinge, px0, px1, pz0, pz1):
            self._cylinder(center, hinge.axis, p.hinge_radius, length,
                           mat_idx=p.mat_hinge)

    def _cylinder(self, center, axis, radius, length, segments=12,
                  mat_idx=0):
        """Closed cylinder whose centre line runs along ``axis`` ('X'|'Z')."""
        bm = self.bm
        if radius < 1e-5 or length < 1e-5:
            return
        cx, cy, cz = center
        half   = length / 2.0
        step   = 2.0 * math.pi / segments
        ring_a = []
        ring_b = []
        for i in range(segments):
            a = i * step
            u = radius * math.cos(a)
            v = radius * math.sin(a)
            if axis == 'Z':
                ring_a.append(bm.verts.new(Vector((cx + u, cy + v, cz - half))))
                ring_b.append(bm.verts.new(Vector((cx + u, cy + v, cz + half))))
            else:
                ring_a.append(bm.verts.new(Vector((cx - half, cy + u, cz + v))))
                ring_b.append(bm.verts.new(Vector((cx + half, cy + u, cz + v))))
        bm.verts.ensure_lookup_table()

        for i in range(segments):
            j = (i + 1) % segments
            f = bm.faces.new([ring_a[i], ring_a[j], ring_b[j], ring_b[i]])
            f.material_index = mat_idx
        f = bm.faces.new(list(reversed(ring_a)))
        f.material_index = mat_idx
        f = bm.faces.new(ring_b)
        f.material_index = mat_idx

    def _build_grille(self, x0, x1, z0, z1, y_center, gt, mi):
        p      = self.props
        gr     = p.grille_rows
        gc     = p.grille_cols
        gw     = p.grille_width
        half_t = gt / 2.0 + 0.002

        panel_w = x1 - x0
        panel_h = z1 - z0

        if gr > 1:
            bar_step_h = panel_h / gr
            for i in range(1, gr):
                gz = z0 + i * bar_step_h
                self._box(x0, x1,
                          y_center - half_t, y_center + half_t,
                          gz - gw/2, gz + gw/2, mi)

        if gc > 1:
            bar_step_w = panel_w / gc
            for j in range(1, gc):
                gx = x0 + j * bar_step_w
                self._box(gx - gw/2, gx + gw/2,
                          y_center - half_t, y_center + half_t,
                          z0, z1, mi)

    def _build_outer_sill(self):
        p   = self.props
        if not p.outer_sill_enable:
            return
        w   = p.width
        fw  = p.frame_width
        fd  = p.frame_depth
        off = p.frame_offset
        sw  = p.outer_sill_width
        sh  = p.outer_sill_height
        mi  = p.mat_outer_sill
        bm  = self.bm

        z_sill  = p.sill_height
        y_front = off - fd / 2.0

        if p.outer_sill_type == 'FLAT':
            self._box(-fw, w + fw, y_front - sw, y_front,
                      z_sill - sh, z_sill, mi)

        elif p.outer_sill_type == 'SLOPED':
            verts = [
                bm.verts.new(Vector((-fw,    y_front,      z_sill))),
                bm.verts.new(Vector((w + fw, y_front,      z_sill))),
                bm.verts.new(Vector((w + fw, y_front - sw, z_sill - sh))),
                bm.verts.new(Vector((-fw,    y_front - sw, z_sill - sh))),
                bm.verts.new(Vector((-fw,    y_front,      z_sill - sh * 0.3))),
                bm.verts.new(Vector((w + fw, y_front,      z_sill - sh * 0.3))),
                bm.verts.new(Vector((w + fw, y_front - sw, z_sill - sh * 1.3))),
                bm.verts.new(Vector((-fw,    y_front - sw, z_sill - sh * 1.3))),
            ]
            bm.verts.ensure_lookup_table()
            for fi in [(0,1,5,4),(3,2,6,7),(0,3,7,4),
                       (1,2,6,5),(0,1,2,3),(4,5,6,7)]:
                f = bm.faces.new([verts[i] for i in fi])
                f.material_index = mi

        elif p.outer_sill_type == 'MOLDED':
            self._box(-fw, w+fw, y_front-sw*0.3, y_front,
                      z_sill-sh, z_sill, mi)
            self._box(-fw, w+fw, y_front-sw, y_front-sw*0.3,
                      z_sill-sh*1.2, z_sill-sh*0.2, mi)
            self._box(-fw, w+fw, y_front-sw-0.01, y_front-sw,
                      z_sill-sh*1.3, z_sill-sh*0.15, mi)

    def _build_inner_sill(self):
        p   = self.props
        if not p.inner_sill_enable:
            return
        w   = p.width
        fw  = p.frame_width
        fd  = p.frame_depth
        off = p.frame_offset
        sw  = p.inner_sill_width
        sh  = p.inner_sill_height
        mi  = p.mat_inner_sill

        z_sill = p.sill_height
        y_back = off + fd / 2.0

        self._box(-fw * 0.5, w + fw * 0.5,
                  y_back, y_back + sw,
                  z_sill - sh, z_sill, mi)

    def _build_shutters(self):
        p   = self.props
        if not p.shutter_enable:
            return
        w   = p.width
        h   = p.height
        fw  = p.frame_width
        fd  = p.frame_depth
        off = p.frame_offset
        sd  = p.shutter_depth
        sh  = p.sill_height
        mi  = p.mat_shutter

        shutter_w = w / 2.0
        n_slats   = max(int(h / 0.06), 4)
        slat_h    = h / n_slats
        slat_t    = slat_h * 0.6
        y_back    = off + fd / 2.0 + 0.01

        if p.shutter_open:
            self._box(-fw - shutter_w, -fw, y_back, y_back + sd, sh, sh + h, mi)
            self._add_slats(-fw - shutter_w, -fw, y_back, y_back + sd,
                            sh, h, n_slats, slat_h, slat_t, mi)
            self._box(w + fw, w + fw + shutter_w, y_back, y_back + sd, sh, sh + h, mi)
            self._add_slats(w + fw, w + fw + shutter_w, y_back, y_back + sd,
                            sh, h, n_slats, slat_h, slat_t, mi)
        else:
            self._box(0.0, shutter_w, y_back, y_back + sd, sh, sh + h, mi)
            self._add_slats(0.0, shutter_w, y_back, y_back + sd,
                            sh, h, n_slats, slat_h, slat_t, mi)
            self._box(shutter_w, w, y_back, y_back + sd, sh, sh + h, mi)
            self._add_slats(shutter_w, w, y_back, y_back + sd,
                            sh, h, n_slats, slat_h, slat_t, mi)

    def _add_slats(self, x0, x1, y0, y1, z_base, h,
                   n_slats, slat_h, slat_t, mi):
        bm = self.bm
        for i in range(n_slats):
            z0 = z_base + i * slat_h + (slat_h - slat_t) / 2.0
            z1 = z0 + slat_t
            verts = [
                bm.verts.new(Vector((x0, y0, z0))),
                bm.verts.new(Vector((x1, y0, z0))),
                bm.verts.new(Vector((x1, y1, z0 + slat_t * 0.15))),
                bm.verts.new(Vector((x0, y1, z0 + slat_t * 0.15))),
                bm.verts.new(Vector((x0, y0, z1))),
                bm.verts.new(Vector((x1, y0, z1))),
                bm.verts.new(Vector((x1, y1, z1 - slat_t * 0.15))),
                bm.verts.new(Vector((x0, y1, z1 - slat_t * 0.15))),
            ]
            bm.verts.ensure_lookup_table()
            for fi in [(0,1,5,4),(3,2,6,7),(0,3,7,4),
                       (1,2,6,5),(0,1,2,3),(4,5,6,7)]:
                f = bm.faces.new([verts[i] for i in fi])
                f.material_index = mi

    def _build_bars(self):
        p   = self.props
        if not p.bars_enable:
            return
        w    = p.width
        h    = p.height
        sh   = p.sill_height
        bc   = p.bars_count
        br   = p.bars_radius
        boff = p.bars_offset
        fd   = p.frame_depth
        off  = p.frame_offset
        mi   = p.mat_bars

        y_bars   = off - fd / 2.0 - boff
        spacing  = w / (bc + 1)

        for i in range(bc):
            bx = spacing * (i + 1)
            self._box(bx - br, bx + br,
                      y_bars - br, y_bars + br,
                      sh, sh + h, mi)

        bar_h = br * 2
        for z_bar in [sh + h * 0.25, sh + h * 0.75]:
            self._box(0.0, w,
                      y_bars - br, y_bars + br,
                      z_bar - bar_h/2, z_bar + bar_h/2, mi)

    def generate(self):
        self._build_frame()
        self._build_mullions()
        self._build_sashes()
        self._build_outer_sill()
        self._build_inner_sill()
        self._build_shutters()
        self._build_bars()

        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
        return self.bm


# ════════════════════════════════════════════════════════════
#  UPDATE CALLBACKS
# ════════════════════════════════════════════════════════════
def _find_window_object(props):
    name = props.object_name
    if name and name in bpy.data.objects:
        return bpy.data.objects[name]
    for obj in bpy.data.objects:
        if (obj.type == 'MESH'
                and hasattr(obj, AF_WIN_PROP)
                and getattr(obj, AF_WIN_PROP) is props):
            return obj
    return None


def af_win_co_preset_update(self, context):
    dims = AF_WIN_CO_DIMS.get(self.co_preset)
    if dims is None:
        return
    self.width, self.height, self.sill_height = dims


def af_window_update(self, context):
    obj = _find_window_object(self)
    if obj is None:
        obj = context.active_object
    if obj is None or obj.type != 'MESH':
        return
    props = getattr(obj, AF_WIN_PROP, None)
    if props is None or not props.is_af_window:
        return
    _rebuild_window_mesh(obj, props)


def _rebuild_window_mesh(obj, props):
    gen = AF_WindowGenerator(props)
    bm  = gen.generate()
    if bm is None:
        return

    me = obj.data
    bm.to_mesh(me)
    bm.free()
    me.update()

    # ── FIX: Smooth inteligente ───────────────────────────────
    # Flat en geometría rectangular, smooth solo en curvas (ARCH)
    is_arch = props.window_type == 'ARCH'

    for poly in me.polygons:
        if is_arch:
            # Curvas del arco: normal no ortogonal a los ejes
            n        = poly.normal
            is_ortho = (
                abs(abs(n.x) - 1.0) < 0.01 or
                abs(abs(n.y) - 1.0) < 0.01 or
                abs(abs(n.z) - 1.0) < 0.01
            )
            poly.use_smooth = not is_ortho
        else:
            poly.use_smooth = False

    # ── Marcar aristas como sharp ─────────────────────────────
    for edge in me.edges:
        edge.use_edge_sharp = True

    # ── Desactivar auto smooth ─────────────────────────────────
    if hasattr(me, "use_auto_smooth"):
        me.use_auto_smooth = False


def _setup_window_materials(obj):
    mat_names = [
        "AF.Window.Frame",
        "AF.Window.Frame",
        "AF.Window.Glass",
        "AF.Wall.Base",
        "AF.Floor.Wood",
        "AF.Door.Wood",
        "AF.Fence.Metal",
    ]
    af_material.ensure_af_materials_for_object(obj, mat_names)


def _create_window_object(context, name="AF_Window", location=None):
    me  = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, me)

    if location is not None:
        obj.location = location

    context.collection.objects.link(obj)
    context.view_layer.objects.active = obj
    obj.select_set(True)

    props               = obj.archiforge_window
    props.is_af_window  = True
    props.object_name   = obj.name

    _setup_window_materials(obj)
    return obj, props


# ════════════════════════════════════════════════════════════
#  OPERADORES
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_OT_window(Operator):
    bl_idname      = "archiforge.window"
    bl_label       = "Add AF Window"
    bl_description = "Add a parametric ArchiForge window"
    bl_options     = {'REGISTER', 'UNDO'}

    window_type  : EnumProperty(name="Type",        items=AF_WIN_TYPES, default='CASEMENT')
    width        : FloatProperty(name="Width",       default=1.20, min=AF_WIN_MIN_W, unit='LENGTH')
    height       : FloatProperty(name="Height",      default=1.20, min=AF_WIN_MIN_H, unit='LENGTH')
    sill_height  : FloatProperty(name="Sill Height", default=0.90, min=0.0,          unit='LENGTH')
    auto_boolean : BoolProperty( name="Auto Boolean", default=True)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        col = layout.column(align=True)
        col.label(text="New Window", icon='MESH_PLANE')
        col.prop(self, "window_type")
        col.separator()
        col.prop(self, "width")
        col.prop(self, "height")
        col.prop(self, "sill_height")
        col.separator()
        col.prop(self, "auto_boolean")

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')

        obj, props = _create_window_object(context, "AF_Window")
        props.window_type  = self.window_type
        props.width        = self.width
        props.height       = self.height
        props.sill_height  = self.sill_height
        props.auto_boolean = self.auto_boolean

        _rebuild_window_mesh(obj, props)

        if self.auto_boolean:
            result = af_autoboolean.do_auto_boolean(
                context     = context,
                source_obj  = obj,
                cutter_type = 'WINDOW',
                width       = self.width,
                height      = self.height,
                sill_height = self.sill_height,
            )
            if result['wall']:
                self.report({'INFO'}, _tr("Window → boolean en '{}'")
                                      .format(result['wall'].name))
            else:
                self.report({'INFO'}, _tr("Window created (no wall nearby)"))
        else:
            self.report({'INFO'}, _tr("Window created: {}").format(obj.name))

        return {'FINISHED'}


class ARCHIFORGE_OT_window_place(Operator):
    """Coloca una ventana AF haciendo clic sobre un muro."""
    bl_idname      = "archiforge.window_place"
    bl_label       = "Place Window on Wall"
    bl_description = "Click on a wall to place a window there"
    bl_options     = {'REGISTER', 'UNDO'}

    window_type : EnumProperty(name="Type",        items=AF_WIN_TYPES, default='CASEMENT')
    width       : FloatProperty(name="Width",       default=1.20, min=AF_WIN_MIN_W, unit='LENGTH')
    height      : FloatProperty(name="Height",      default=1.20, min=AF_WIN_MIN_H, unit='LENGTH')
    sill_height : FloatProperty(name="Sill Height", default=0.90, min=0.0,          unit='LENGTH')

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)
        self.report({'INFO'}, _tr("Click on a wall to place the window (ESC to cancel)"))
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type in {'ESC', 'RIGHTMOUSE'}:
            return {'CANCELLED'}

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            hit = self._raycast_wall(context, event)
            if hit is None:
                self.report({'WARNING'}, _tr("Click on a wall surface"))
                return {'RUNNING_MODAL'}
            wall_obj, hit_loc, hit_normal = hit
            self._create_window_at(context, wall_obj, hit_loc, hit_normal)
            return {'FINISHED'}

        return {'RUNNING_MODAL'}

    def _raycast_wall(self, context, event):
        from bpy_extras.view3d_utils import (
            region_2d_to_origin_3d,
            region_2d_to_vector_3d,
        )
        region = context.region
        rv3d   = context.region_data
        if region is None or rv3d is None:
            return None
        coord  = (event.mouse_region_x, event.mouse_region_y)
        origin = region_2d_to_origin_3d(region, rv3d, coord)
        vector = region_2d_to_vector_3d(region, rv3d, coord)
        hit, loc, normal, idx, obj, mat = context.scene.ray_cast(
            context.view_layer.depsgraph, origin, vector,
        )
        if not hit:
            return None
        if not (hasattr(obj, "archiforge_wall")
                and obj.archiforge_wall.is_af_wall):
            return None
        return obj, loc, normal

    def _create_window_at(self, context, wall_obj, hit_loc, hit_normal):
        bpy.ops.object.select_all(action='DESELECT')
        obj, props = _create_window_object(context, "AF_Window")
        props.window_type = self.window_type
        props.width       = self.width
        props.height      = self.height
        props.sill_height = self.sill_height

        n      = hit_normal.normalized()
        z_axis = Vector((0, 0, 1))
        y_axis = n - n.dot(z_axis) * z_axis
        if y_axis.length < 1e-4:
            y_axis = Vector((0, 1, 0))
        y_axis.normalize()
        x_axis = y_axis.cross(z_axis).normalized()

        rot_mat = Matrix((
            (x_axis.x, y_axis.x, z_axis.x, 0),
            (x_axis.y, y_axis.y, z_axis.y, 0),
            (x_axis.z, y_axis.z, z_axis.z, 0),
            (0,        0,        0,        1),
        ))

        hit_centered     = hit_loc - x_axis * (self.width * 0.5)
        obj.matrix_world = Matrix.Translation(hit_centered) @ rot_mat

        _rebuild_window_mesh(obj, props)

        af_autoboolean.do_auto_boolean(
            context     = context,
            source_obj  = obj,
            cutter_type = 'WINDOW',
            width       = self.width,
            height      = self.height,
            sill_height = self.sill_height,
            wall_obj    = wall_obj,
        )
        self.report({'INFO'}, _tr("Window placed on '{}'").format(wall_obj.name))


class ARCHIFORGE_OT_window_update(Operator):
    bl_idname      = "archiforge.window_update"
    bl_label       = "Update Window"
    bl_description = "Force regeneration of the selected window"
    bl_options     = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj is not None and obj.type == 'MESH'
            and hasattr(obj, AF_WIN_PROP)
            and obj.archiforge_window.is_af_window
        )

    def execute(self, context):
        obj = context.active_object
        _rebuild_window_mesh(obj, obj.archiforge_window)
        self.report({'INFO'}, _tr("Window updated"))
        return {'FINISHED'}


class ARCHIFORGE_OT_window_toggle_shutters(Operator):
    bl_idname      = "archiforge.window_toggle_shutters"
    bl_label       = "Toggle Shutters"
    bl_description = "Open or close window shutters"
    bl_options     = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj is not None and obj.type == 'MESH'
            and hasattr(obj, AF_WIN_PROP)
            and obj.archiforge_window.is_af_window
            and obj.archiforge_window.shutter_enable
        )

    def execute(self, context):
        props = context.active_object.archiforge_window
        props.shutter_open = not props.shutter_open
        return {'FINISHED'}


class ARCHIFORGE_OT_window_apply_boolean(Operator):
    bl_idname      = "archiforge.window_apply_boolean"
    bl_label       = "Apply Boolean to Wall"
    bl_description = "Cut opening in nearest wall for this window"
    bl_options     = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj is not None and obj.type == 'MESH'
            and hasattr(obj, AF_WIN_PROP)
            and obj.archiforge_window.is_af_window
        )

    def execute(self, context):
        obj   = context.active_object
        props = obj.archiforge_window

        result = af_autoboolean.do_auto_boolean(
            context     = context,
            source_obj  = obj,
            cutter_type = 'WINDOW',
            width       = props.width,
            height      = props.height,
            sill_height = props.sill_height,
        )
        if result['success']:
            wn = result['wall'].name if result['wall'] else "none"
            self.report({'INFO'}, _tr("✅ Boolean applied to '{}'").format(wn))
        else:
            self.report({'WARNING'}, _tr("⚠️  Could not apply boolean"))
        return {'FINISHED'}


class ARCHIFORGE_OT_window_toggle_open(Operator):
    bl_idname      = "archiforge.window_toggle_open"
    bl_label       = "Toggle Open/Closed"
    bl_description = ("Toggle hinged sashes between open and closed "
                      "(casement and awning windows only)")
    bl_options     = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj is not None and obj.type == 'MESH'
            and hasattr(obj, AF_WIN_PROP)
            and obj.archiforge_window.is_af_window
            and window_type_can_open(obj.archiforge_window.window_type)
        )

    def execute(self, context):
        props = context.active_object.archiforge_window
        if props.open_angle < math.radians(5):
            props.open_angle = math.radians(45)
        else:
            props.open_angle = 0.0
        return {'FINISHED'}


# ════════════════════════════════════════════════════════════
#  PANEL
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_PT_window(Panel):
    bl_label       = "Window Properties"
    bl_idname      = "ARCHIFORGE_PT_window"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "ArchiForge"
    bl_context     = "objectmode"
    bl_options     = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj is not None and obj.type == 'MESH'
            and hasattr(obj, AF_WIN_PROP)
            and obj.archiforge_window.is_af_window
        )

    def draw_header(self, context):
        self.layout.label(text="", icon='MESH_PLANE')

    def draw(self, context):
        obj    = context.active_object
        props  = obj.archiforge_window
        layout = self.layout
        layout.use_property_split     = True
        layout.use_property_decorate  = False

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Type", icon='MODIFIER')
        col.prop(props, "window_type", text="")
        col.prop(props, "co_preset", text="CO")

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Dimensions", icon='ARROW_LEFTRIGHT')
        col.prop(props, "width")
        col.prop(props, "height")
        col.prop(props, "sill_height")

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Frame", icon='MESH_GRID')
        col.prop(props, "frame_width")
        col.prop(props, "frame_depth")
        col.prop(props, "frame_offset")

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Divisions (Mullions)", icon='MESH_GRID')
        col.prop(props, "h_panels", text="Rows")
        col.prop(props, "v_panels", text="Columns")
        col.prop(props, "mullion_width")

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Sash", icon='MESH_PLANE')
        col.prop(props, "sash_style", text="Style")
        col.prop(props, "sash_width")
        col.prop(props, "sash_depth")
        if props.sash_style in ('DIVIDED', 'COLONIAL'):
            col.separator(factor=0.3)
            col.label(text="Grille", icon='MESH_GRID')
            col.prop(props, "grille_rows")
            col.prop(props, "grille_cols")
            col.prop(props, "grille_width")

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Glass", icon='MATERIAL')
        col.prop(props, "glass_thickness")

        if props.window_type == 'ARCH':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Arch", icon='MESH_CIRCLE')
            col.prop(props, "arch_height")
            col.prop(props, "arch_segments")

        # Only hinged types rotate their sashes; sliding, double-hung,
        # fixed and arch windows never expose the open/close controls.
        if window_type_can_open(props.window_type):
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Opening", icon='DRIVER_ROTATIONAL_DIFFERENCE')
            col.prop(props, "open_angle")
            if props.window_type == 'CASEMENT':
                col.prop(props, "hinge_side", text="Hinge")
                col.prop(props, "swing_direction", text="Swing")
            else:
                col.label(text="Top hinge, projects outward", icon='INFO')
            col.operator("archiforge.window_toggle_open",
                         text="Toggle Open / Closed",
                         icon='DRIVER_ROTATIONAL_DIFFERENCE')
            col.separator(factor=0.3)
            col.prop(props, "hinge_enable", text="Hinges")
            if props.hinge_enable:
                col.prop(props, "hinge_radius")
                col.prop(props, "hinge_length")

        box = layout.box()
        row = box.row(align=True)
        row.prop(props, "outer_sill_enable", text="Outer Sill",
                 icon='TRIA_DOWN' if props.outer_sill_enable else 'TRIA_RIGHT',
                 toggle=True, emboss=False)
        if props.outer_sill_enable:
            col = box.column(align=True)
            col.prop(props, "outer_sill_type", text="Style")
            col.prop(props, "outer_sill_width")
            col.prop(props, "outer_sill_height")

        box = layout.box()
        row = box.row(align=True)
        row.prop(props, "inner_sill_enable", text="Inner Sill",
                 icon='TRIA_DOWN' if props.inner_sill_enable else 'TRIA_RIGHT',
                 toggle=True, emboss=False)
        if props.inner_sill_enable:
            col = box.column(align=True)
            col.prop(props, "inner_sill_width")
            col.prop(props, "inner_sill_height")

        box = layout.box()
        row = box.row(align=True)
        row.prop(props, "shutter_enable", text="Shutters",
                 icon='TRIA_DOWN' if props.shutter_enable else 'TRIA_RIGHT',
                 toggle=True, emboss=False)
        if props.shutter_enable:
            col = box.column(align=True)
            col.prop(props, "shutter_depth")
            col.operator(
                "archiforge.window_toggle_shutters",
                text=("Open Shutters" if not props.shutter_open
                      else "Close Shutters"),
                icon='TRIA_RIGHT' if not props.shutter_open else 'TRIA_LEFT',
            )

        box = layout.box()
        row = box.row(align=True)
        row.prop(props, "bars_enable", text="Security Bars",
                 icon='TRIA_DOWN' if props.bars_enable else 'TRIA_RIGHT',
                 toggle=True, emboss=False)
        if props.bars_enable:
            col = box.column(align=True)
            col.prop(props, "bars_count")
            col.prop(props, "bars_radius")
            col.prop(props, "bars_offset")

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Material Slots", icon='MATERIAL')
        col.prop(props, "mat_frame",  text="Frame")
        col.prop(props, "mat_sash",   text="Sash")
        col.prop(props, "mat_glass",  text="Glass")
        if props.outer_sill_enable:
            col.prop(props, "mat_outer_sill", text="Outer Sill")
        if props.inner_sill_enable:
            col.prop(props, "mat_inner_sill", text="Inner Sill")
        if props.shutter_enable:
            col.prop(props, "mat_shutter",    text="Shutters")
        if props.bars_enable:
            col.prop(props, "mat_bars",       text="Bars")
        if props.hinge_enable and window_type_can_open(props.window_type):
            col.prop(props, "mat_hinge",      text="Hinges")

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Boolean", icon='MOD_BOOLEAN')
        col.prop(props, "auto_boolean")
        col.operator("archiforge.window_apply_boolean",
                     text="Apply Boolean Now", icon='MOD_BOOLEAN')

        layout.separator()
        layout.operator("archiforge.window_place",
                        text="Place New Window on Wall (Click)",
                        icon='RESTRICT_SELECT_OFF')
        layout.operator("archiforge.window_update",
                        text="Force Update", icon='FILE_REFRESH')


# ════════════════════════════════════════════════════════════
#  REGISTRO
# ════════════════════════════════════════════════════════════
classes = [
    AF_WindowProperties,
    ARCHIFORGE_OT_window,
    ARCHIFORGE_OT_window_place,
    ARCHIFORGE_OT_window_update,
    ARCHIFORGE_OT_window_toggle_shutters,
    ARCHIFORGE_OT_window_apply_boolean,
    ARCHIFORGE_OT_window_toggle_open,
    ARCHIFORGE_PT_window,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Object.archiforge_window = PointerProperty(
        type        = AF_WindowProperties,
        name        = "ArchiForge Window",
        description = "ArchiForge parametric window properties",
    )
    print("[ArchiForge] ✅ af_window — registered")


def unregister():
    if hasattr(bpy.types.Object, "archiforge_window"):
        del bpy.types.Object.archiforge_window

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    print("[ArchiForge] 🔴 af_window — unregistered")
