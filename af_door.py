# -*- coding: utf-8 -*-

# ╔══════════════════════════════════════════════════════════╗
# ║         ARCHIFORGE — af_door.py                         ║
# ║         Puertas Paramétricas para Blender 3.3 LTS       ║
# ║         GPL v3 — ArchiForge Devs                        ║
# ╚══════════════════════════════════════════════════════════╝

# <pep8 compliant>

# ════════════════════════════════════════════════════════════
#  ¿QUÉ HACE ESTE MÓDULO?
#
#  Genera puertas paramétricas completas con:
#  - Marco (frame) con perfil configurable
#  - Hoja (panel) con distintos estilos
#  - Paneles decorativos en la hoja
#  - Acristalamiento (glass panel) opcional
#  - Manija / handle
#  - Umbral (threshold) opcional
#  - Apertura animable (ángulo de apertura)
#  - Auto-Boolean al muro más cercano
#  - Colocación interactiva sobre muro (NUEVO)
#
#  Tipos de puerta:
#  - SINGLE   : Una hoja
#  - DOUBLE   : Dos hojas simétricas
#  - SLIDING  : Corredera
#  - POCKET   : Empotrada en muro
# ════════════════════════════════════════════════════════════

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

# — Importar módulos AF hermanos —
from . import af_autoboolean
from . import af_material


# ════════════════════════════════════════════════════════════
#  CONSTANTES
# ════════════════════════════════════════════════════════════
AF_DOOR_PROP     = "archiforge_door"

AF_DOOR_MIN_W    = 0.40
AF_DOOR_MAX_W    = 6.00
AF_DOOR_MIN_H    = 0.80
AF_DOOR_MAX_H    = 6.00
AF_DOOR_MIN_D    = 0.02
AF_DOOR_MAX_D    = 0.30

AF_DOOR_TYPES = [
    ('SINGLE',  "Single",  "Single swing door",         'TRIA_RIGHT', 0),
    ('DOUBLE',  "Double",  "Double swing door",         'CENTER_ONLY', 1),
    ('SLIDING', "Sliding", "Sliding door",              'FORWARD',    2),
    ('POCKET',  "Pocket",  "Pocket door (wall mounted)", 'HIDE_OFF',  3),
]

AF_DOOR_PANEL_STYLES = [
    ('FLAT',    "Flat",    "Flat smooth panel"),
    ('RAISED',  "Raised",  "Raised center panel"),
    ('GLASS',   "Glass",   "Full glass panel"),
    ('MIXED',   "Mixed",   "Lower solid + upper glass"),
]

AF_HANDLE_TYPES = [
    ('LEVER',   "Lever",    "Lever type handle"),
    ('KNOB',    "Knob",     "Round knob handle"),
    ('PULL',    "Pull Bar", "Pull bar handle"),
    ('NONE',    "None",     "No handle"),
]

AF_HINGE_SIDES = [
    ('LEFT',  "Left",  "Hinge on left side"),
    ('RIGHT', "Right", "Hinge on right side"),
]


# ════════════════════════════════════════════════════════════
#  PROPERTYGROUP
# ════════════════════════════════════════════════════════════
class AF_DoorProperties(PropertyGroup):

    is_af_door  : BoolProperty(
        name    = "Is ArchiForge Door",
        default = True,
        options = {'HIDDEN'},
    )
    object_name : StringProperty(
        name    = "Object Name",
        default = "",
        options = {'HIDDEN'},
    )

    door_type : EnumProperty(
        name    = "Door Type",
        items   = AF_DOOR_TYPES,
        default = 'SINGLE',
        update  = lambda s, c: af_door_update(s, c),
    )

    width : FloatProperty(
        name="Width", description="Total door width (opening)",
        default=0.90, min=AF_DOOR_MIN_W, max=AF_DOOR_MAX_W,
        unit='LENGTH', update=lambda s, c: af_door_update(s, c),
    )
    height : FloatProperty(
        name="Height", description="Total door height",
        default=2.10, min=AF_DOOR_MIN_H, max=AF_DOOR_MAX_H,
        unit='LENGTH', update=lambda s, c: af_door_update(s, c),
    )
    depth : FloatProperty(
        name="Panel Thickness", description="Thickness of the door panel/leaf",
        default=0.04, min=AF_DOOR_MIN_D, max=AF_DOOR_MAX_D,
        unit='LENGTH', update=lambda s, c: af_door_update(s, c),
    )

    frame_enable : BoolProperty(
        name="Frame", description="Generate door frame",
        default=True, update=lambda s, c: af_door_update(s, c),
    )
    frame_width : FloatProperty(
        name="Frame Width", description="Width of the door frame profile",
        default=0.08, min=0.01, max=0.30, unit='LENGTH',
        update=lambda s, c: af_door_update(s, c),
    )
    frame_depth : FloatProperty(
        name="Frame Depth", description="Depth (thickness) of the frame",
        default=0.12, min=0.02, max=0.40, unit='LENGTH',
        update=lambda s, c: af_door_update(s, c),
    )
    frame_offset : FloatProperty(
        name="Frame Offset", description="Offset of frame from wall face",
        default=0.0, min=-0.10, max=0.10, unit='LENGTH',
        update=lambda s, c: af_door_update(s, c),
    )

    panel_style : EnumProperty(
        name="Panel Style", items=AF_DOOR_PANEL_STYLES, default='RAISED',
        update=lambda s, c: af_door_update(s, c),
    )
    panel_rows : IntProperty(
        name="Panel Rows", default=2, min=1, max=6,
        update=lambda s, c: af_door_update(s, c),
    )
    panel_cols : IntProperty(
        name="Panel Columns", default=1, min=1, max=4,
        update=lambda s, c: af_door_update(s, c),
    )
    panel_border : FloatProperty(
        name="Panel Border", default=0.06, min=0.01, max=0.20, unit='LENGTH',
        update=lambda s, c: af_door_update(s, c),
    )
    panel_inset : FloatProperty(
        name="Panel Inset/Raise", default=0.01, min=-0.05, max=0.05, unit='LENGTH',
        update=lambda s, c: af_door_update(s, c),
    )

    glass_enable : BoolProperty(
        name="Glass Panel", default=False,
        update=lambda s, c: af_door_update(s, c),
    )
    glass_ratio : FloatProperty(
        name="Glass Ratio", default=0.35, min=0.05, max=0.90,
        update=lambda s, c: af_door_update(s, c),
    )
    glass_thickness : FloatProperty(
        name="Glass Thickness", default=0.006, min=0.003, max=0.02, unit='LENGTH',
        update=lambda s, c: af_door_update(s, c),
    )

    open_angle : FloatProperty(
        name="Open Angle", description="Door opening angle",
        default=0.0, min=0.0, max=math.radians(180),
        subtype='ANGLE', update=lambda s, c: af_door_update(s, c),
    )
    hinge_side : EnumProperty(
        name="Hinge Side", items=AF_HINGE_SIDES, default='LEFT',
        update=lambda s, c: af_door_update(s, c),
    )

    handle_type : EnumProperty(
        name="Handle Type", items=AF_HANDLE_TYPES, default='LEVER',
        update=lambda s, c: af_door_update(s, c),
    )
    handle_height : FloatProperty(
        name="Handle Height", default=1.05, min=0.50, max=1.80, unit='LENGTH',
        update=lambda s, c: af_door_update(s, c),
    )
    handle_offset : FloatProperty(
        name="Handle Offset", default=0.06, min=0.02, max=0.20, unit='LENGTH',
        update=lambda s, c: af_door_update(s, c),
    )

    threshold_enable : BoolProperty(
        name="Threshold", default=False,
        update=lambda s, c: af_door_update(s, c),
    )
    threshold_height : FloatProperty(
        name="Threshold Height", default=0.02, min=0.005, max=0.10, unit='LENGTH',
        update=lambda s, c: af_door_update(s, c),
    )
    threshold_width : FloatProperty(
        name="Threshold Width", default=0.10, min=0.02, max=0.30, unit='LENGTH',
        update=lambda s, c: af_door_update(s, c),
    )

    auto_boolean : BoolProperty(
        name="Auto Boolean",
        description="Automatically cut opening in nearest wall",
        default=True,
    )

    mat_frame   : IntProperty(name="Frame Material",   default=0, min=0)
    mat_panel   : IntProperty(name="Panel Material",   default=1, min=0)
    mat_glass   : IntProperty(name="Glass Material",   default=2, min=0)
    mat_handle  : IntProperty(name="Handle Material",  default=3, min=0)
    mat_thresh  : IntProperty(name="Threshold Mat.",   default=4, min=0)


# ════════════════════════════════════════════════════════════
#  GENERADOR DE GEOMETRÍA
# ════════════════════════════════════════════════════════════
class AF_DoorGenerator:
    """
    Motor de generación de mesh para puertas paramétricas.
    Usa material_index NATIVO de las caras del bmesh.
    """

    def __init__(self, props):
        self.props = props
        self.bm    = bmesh.new()

    def _box(self, x0, x1, y0, y1, z0, z1, mat_idx=0):
        bm = self.bm
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
        faces_idx = [
            (0, 1, 5, 4), (2, 3, 7, 6), (0, 3, 2, 1),
            (4, 5, 6, 7), (0, 4, 7, 3), (1, 2, 6, 5),
        ]
        for fi in faces_idx:
            f = bm.faces.new([verts[i] for i in fi])
            f.material_index = mat_idx
        bm.verts.ensure_lookup_table()

    def _build_frame(self):
        p   = self.props
        w   = p.width
        h   = p.height
        fw  = p.frame_width
        fd  = p.frame_depth
        off = p.frame_offset
        mi  = p.mat_frame
        half_d = fd / 2.0

        self._box(-fw, 0.0, -half_d + off, half_d + off, 0.0, h, mi)
        self._box(w, w + fw, -half_d + off, half_d + off, 0.0, h, mi)
        self._box(-fw, w + fw, -half_d + off, half_d + off, h, h + fw, mi)

        stop_d  = fd * 0.3
        stop_w  = fw * 0.4
        self._box(-stop_w, 0.0, -half_d + off, -half_d + off + stop_d, 0.0, h, mi)
        self._box(w, w + stop_w, -half_d + off, -half_d + off + stop_d, 0.0, h, mi)
        self._box(-stop_w, w + stop_w, -half_d + off, -half_d + off + stop_d, h - stop_w, h + fw, mi)

    def _build_leaf(self):
        p        = self.props
        w        = p.width
        h        = p.height
        d        = p.depth
        off      = p.frame_offset
        mi_panel = p.mat_panel
        mi_glass = p.mat_glass
        angle    = p.open_angle

        leaf_w = w
        if p.door_type == 'DOUBLE':
            leaf_w = w / 2.0

        gap   = 0.003
        lw    = leaf_w - gap * 2
        lh    = h - gap
        half_d = d / 2.0

        if p.door_type in ('SINGLE', 'POCKET'):
            self._build_single_leaf(lw, lh, d, gap, off, angle, mi_panel, mi_glass, flip=False)
        elif p.door_type == 'DOUBLE':
            self._build_single_leaf(lw, lh, d, gap, off, angle, mi_panel, mi_glass, flip=False)
            self._build_single_leaf(lw, lh, d, gap, off, angle, mi_panel, mi_glass, flip=True, x_offset=w)
        elif p.door_type == 'SLIDING':
            self._build_sliding_leaf(lw, lh, d, gap, off, angle, mi_panel, mi_glass)

    def _build_single_leaf(self, lw, lh, d, gap, off, angle,
                           mi_panel, mi_glass, flip=False, x_offset=0.0):
        p      = self.props
        bm     = self.bm
        half_d = d / 2.0

        if (p.hinge_side == 'LEFT' and not flip) or \
           (p.hinge_side == 'RIGHT' and flip):
            pivot_x = gap + x_offset
            sign    = 1.0
        else:
            pivot_x = lw + gap + x_offset
            sign    = -1.0

        x0_local = 0.0
        x1_local = lw
        y0       = -half_d + off
        y1       =  half_d + off
        z0       = gap
        z1       = lh

        cos_a = math.cos(sign * angle)
        sin_a = math.sin(sign * angle)

        def rotate_pt(lx, ly):
            tx = lx
            ty = ly
            rx = tx * cos_a - ty * sin_a
            ry = tx * sin_a + ty * cos_a
            return rx + pivot_x, ry

        corners_xz = [
            (x0_local, y0), (x1_local, y0),
            (x1_local, y1), (x0_local, y1),
        ]

        verts_bot = []
        verts_top = []
        for (lx, ly) in corners_xz:
            rx, ry = rotate_pt(lx, ly)
            verts_bot.append(bm.verts.new(Vector((rx, ry, z0))))
            verts_top.append(bm.verts.new(Vector((rx, ry, z1))))

        bm.verts.ensure_lookup_table()

        faces_idx = [
            (0, 1, 5, 4), (3, 2, 6, 7), (0, 3, 7, 4),
            (1, 2, 6, 5), (0, 1, 2, 3), (4, 5, 6, 7),
        ]
        all_v = verts_bot + verts_top
        for fi in faces_idx:
            f = bm.faces.new([all_v[i] for i in fi])
            f.material_index = mi_panel

        if p.panel_style in ('RAISED', 'FLAT') and p.panel_rows > 0:
            self._build_raised_panels(lw, lh, d, gap, off, pivot_x, sign, angle, mi_panel)
        if p.glass_enable or p.panel_style == 'GLASS':
            self._build_glass_panel(lw, lh, d, gap, off, pivot_x, sign, angle, mi_glass)

        # ── FIX: el pomo se genera aquí y rota con la hoja ──
        # Solo para puertas de una hoja (SINGLE/POCKET). Las puertas
        # DOUBLE/SLIDING generan su pomo desde generate() sin rotación.
        if p.door_type in ('SINGLE', 'POCKET'):
            self._build_handle(pivot_x=pivot_x, sign=sign, angle=angle)

    def _build_raised_panels(self, lw, lh, d, gap, off, pivot_x, sign, angle, mi):
        p      = self.props
        bm     = self.bm
        border = p.panel_border
        inset  = p.panel_inset
        rows   = p.panel_rows
        cols   = p.panel_cols
        half_d = d / 2.0

        cos_a = math.cos(sign * angle)
        sin_a = math.sin(sign * angle)

        def rotate_pt(lx, ly):
            rx = lx * cos_a - ly * sin_a
            ry = lx * sin_a + ly * cos_a
            return rx + pivot_x, ry

        avail_w = lw - border * 2
        avail_h = lh - border * 2
        panel_w = (avail_w - border * (cols - 1)) / cols
        panel_h = (avail_h - border * (rows - 1)) / rows

        if panel_w <= 0.01 or panel_h <= 0.01:
            return

        y_face_front = off - half_d + d + inset
        y_face_back  = off - half_d

        for row in range(rows):
            for col in range(cols):
                px0 = border + col * (panel_w + border)
                px1 = px0 + panel_w
                pz0 = gap + border + row * (panel_h + border)
                pz1 = pz0 + panel_h

                corners = [
                    (px0, y_face_front), (px1, y_face_front),
                    (px1, y_face_back),  (px0, y_face_back),
                ]
                vb, vt = [], []
                for (lx, ly) in corners:
                    rx, ry = rotate_pt(lx, ly)
                    vb.append(bm.verts.new(Vector((rx, ry, pz0))))
                    vt.append(bm.verts.new(Vector((rx, ry, pz1))))

                bm.verts.ensure_lookup_table()
                all_v = vb + vt
                pfaces = [
                    (0, 1, 5, 4), (3, 2, 6, 7), (0, 3, 7, 4),
                    (1, 2, 6, 5), (0, 1, 2, 3), (4, 5, 6, 7),
                ]
                for fi in pfaces:
                    f = bm.faces.new([all_v[i] for i in fi])
                    f.material_index = mi

    def _build_glass_panel(self, lw, lh, d, gap, off, pivot_x, sign, angle, mi):
        p      = self.props
        bm     = self.bm
        border = p.panel_border
        gt     = p.glass_thickness
        ratio  = p.glass_ratio
        half_d = d / 2.0

        cos_a = math.cos(sign * angle)
        sin_a = math.sin(sign * angle)

        def rotate_pt(lx, ly):
            rx = lx * cos_a - ly * sin_a
            ry = lx * sin_a + ly * cos_a
            return rx + pivot_x, ry

        gx0 = border
        gx1 = lw - border
        gz0 = lh * (1.0 - ratio) + gap
        gz1 = lh - border + gap
        gy0 = off - gt / 2.0
        gy1 = off + gt / 2.0

        corners = [(gx0, gy0), (gx1, gy0), (gx1, gy1), (gx0, gy1)]
        vb, vt = [], []
        for (lx, ly) in corners:
            rx, ry = rotate_pt(lx, ly)
            vb.append(bm.verts.new(Vector((rx, ry, gz0))))
            vt.append(bm.verts.new(Vector((rx, ry, gz1))))

        bm.verts.ensure_lookup_table()
        all_v = vb + vt
        gfaces = [
            (0, 1, 5, 4), (3, 2, 6, 7), (0, 3, 7, 4),
            (1, 2, 6, 5), (0, 1, 2, 3), (4, 5, 6, 7),
        ]
        for fi in gfaces:
            f = bm.faces.new([all_v[i] for i in fi])
            f.material_index = mi

    def _build_sliding_leaf(self, lw, lh, d, gap, off, slide, mi_panel, mi_glass):
        bm     = self.bm
        half_d = d / 2.0
        max_slide  = lw
        slide_dist = (slide / math.radians(90)) * max_slide
        x_off      = slide_dist
        y0 = off - half_d
        y1 = off + half_d

        verts_b = [
            bm.verts.new(Vector((x_off + gap, y0, gap))),
            bm.verts.new(Vector((x_off + lw,  y0, gap))),
            bm.verts.new(Vector((x_off + lw,  y1, gap))),
            bm.verts.new(Vector((x_off + gap, y1, gap))),
        ]
        verts_t = [
            bm.verts.new(Vector((x_off + gap, y0, lh))),
            bm.verts.new(Vector((x_off + lw,  y0, lh))),
            bm.verts.new(Vector((x_off + lw,  y1, lh))),
            bm.verts.new(Vector((x_off + gap, y1, lh))),
        ]
        bm.verts.ensure_lookup_table()
        all_v = verts_b + verts_t
        for fi in [(0,1,5,4),(3,2,6,7),(0,3,7,4),(1,2,6,5),(0,1,2,3),(4,5,6,7)]:
            f = bm.faces.new([all_v[i] for i in fi])
            f.material_index = mi_panel

    # ────────────────────────────────────────────────────────
    #  POMO — ahora acepta pivot_x/sign/angle para rotar con la hoja
    # ────────────────────────────────────────────────────────
    def _build_handle(self, pivot_x=None, sign=1.0, angle=0.0):
        p  = self.props
        if p.handle_type == 'NONE':
            return

        bm       = self.bm
        n_before = len(bm.verts)

        w   = p.width
        d   = p.depth
        off = p.frame_offset
        hh  = p.handle_height
        ho  = p.handle_offset
        mi  = p.mat_handle
        hx  = (w - ho) if p.hinge_side == 'LEFT' else ho
        hy  = off

        if p.handle_type == 'LEVER':
            self._build_lever_handle(hx, hy, hh, d, mi)
        elif p.handle_type == 'KNOB':
            self._build_knob_handle(hx, hy, hh, d, mi)
        elif p.handle_type == 'PULL':
            self._build_pull_handle(hx, hy, hh, d, mi)

        # ── FIX: rotar los vértices nuevos con la hoja ──
        # Aplica la misma transformación que rotate_pt() de la hoja,
        # tomando como referencia el pivote de la bisagra.
        if pivot_x is not None and abs(angle) > 1e-6:
            cos_a = math.cos(sign * angle)
            sin_a = math.sin(sign * angle)
            bm.verts.ensure_lookup_table()
            for i in range(n_before, len(bm.verts)):
                v  = bm.verts[i]
                lx = v.co.x - pivot_x
                ly = v.co.y
                v.co.x = lx * cos_a - ly * sin_a + pivot_x
                v.co.y = lx * sin_a + ly * cos_a

    def _build_lever_handle(self, hx, hy, hh, d, mi):
        bm  = self.bm
        pw, ph, pd = 0.04, 0.14, 0.01
        self._box(hx - pw/2, hx + pw/2, hy - pd, hy + pd, hh - ph/2, hh + ph/2, mi)

        lx  = hx + 0.005
        ly0 = hy - pd
        ly1 = hy - pd - 0.07
        lw  = 0.012
        lh  = 0.012
        lz  = hh
        verts = [
            bm.verts.new(Vector((lx - lw/2, ly0, lz - lh/2))),
            bm.verts.new(Vector((lx + lw/2, ly0, lz - lh/2))),
            bm.verts.new(Vector((lx + lw/2, ly0, lz + lh/2))),
            bm.verts.new(Vector((lx - lw/2, ly0, lz + lh/2))),
            bm.verts.new(Vector((lx - lw/2, ly1, lz - lh/2 - 0.02))),
            bm.verts.new(Vector((lx + lw/2, ly1, lz - lh/2 - 0.02))),
            bm.verts.new(Vector((lx + lw/2, ly1, lz + lh/2))),
            bm.verts.new(Vector((lx - lw/2, ly1, lz + lh/2))),
        ]
        bm.verts.ensure_lookup_table()
        for fi in [(0,1,5,4),(3,2,6,7),(0,3,7,4),(1,2,6,5),(0,1,2,3),(4,5,6,7)]:
            f = bm.faces.new([verts[i] for i in fi])
            f.material_index = mi

    def _build_knob_handle(self, hx, hy, hh, d, mi):
        r = 0.025
        self._box(hx - r, hx + r, hy - r - d, hy + r - d, hh - r, hh + r, mi)
        self._box(hx - 0.006, hx + 0.006, hy - d, hy + 0.005, hh - 0.005, hh + 0.005, mi)

    def _build_pull_handle(self, hx, hy, hh, d, mi):
        bar_h = 0.20
        bar_r = 0.012
        reach = 0.06
        self._box(hx - bar_r, hx + bar_r, hy - d - reach, hy - d - reach + bar_r, hh - bar_h/2, hh + bar_h/2, mi)
        for dz in [-bar_h/2 + bar_r, bar_h/2 - bar_r]:
            self._box(hx - bar_r, hx + bar_r, hy - d - reach, hy - d + 0.005, hh + dz - bar_r, hh + dz + bar_r, mi)

    def _build_threshold(self):
        p = self.props
        if not p.threshold_enable:
            return
        w  = p.width
        th = p.threshold_height
        tw = p.threshold_width
        mi = p.mat_thresh
        self._box(-tw / 2, w + tw / 2, -tw / 2, tw / 2, -th, 0.0, mi)

    def generate(self):
        p = self.props
        if p.frame_enable:
            self._build_frame()
        self._build_leaf()  # ← dentro de _build_single_leaf se genera el pomo
                            #    para SINGLE/POCKET (con rotación).

        # ── FIX: solo DOUBLE/SLIDING generan el pomo aquí (sin rotación) ──
        if p.door_type in ('DOUBLE', 'SLIDING'):
            self._build_handle()

        self._build_threshold()

        # — Recalcular normales (BMesh POSICIONAL) —
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
        return self.bm


# ════════════════════════════════════════════════════════════
#  UPDATE CALLBACKS
# ════════════════════════════════════════════════════════════
def _find_door_object(props):
    name = props.object_name
    if name and name in bpy.data.objects:
        return bpy.data.objects[name]
    for obj in bpy.data.objects:
        if (obj.type == 'MESH'
                and hasattr(obj, AF_DOOR_PROP)
                and getattr(obj, AF_DOOR_PROP) is props):
            return obj
    return None


def af_door_update(self, context):
    obj = _find_door_object(self)
    if obj is None:
        obj = context.active_object
    if obj is None or obj.type != 'MESH':
        return
    props = getattr(obj, AF_DOOR_PROP, None)
    if props is None or not props.is_af_door:
        return
    _rebuild_door_mesh(obj, props)


def _rebuild_door_mesh(obj, props):
    gen = AF_DoorGenerator(props)
    bm  = gen.generate()
    if bm is None:
        return

    me = obj.data
    bm.to_mesh(me)
    bm.free()
    me.update()

    for poly in me.polygons:
        poly.use_smooth = True


# ════════════════════════════════════════════════════════════
#  SETUP DE MATERIALES
# ════════════════════════════════════════════════════════════
def _setup_door_materials(obj):
    mat_names = [
        "AF.Door.Frame",
        "AF.Door.Wood",
        "AF.Door.Glass",
        "AF.Door.Handle",
        "AF.Wall.Base",
    ]
    af_material.ensure_af_materials_for_object(obj, mat_names)


# ════════════════════════════════════════════════════════════
#  HELPER — Crear objeto puerta
# ════════════════════════════════════════════════════════════
def _create_door_object(context, name="AF_Door", location=None):
    me  = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, me)

    if location is not None:
        obj.location = location

    context.collection.objects.link(obj)
    context.view_layer.objects.active = obj
    obj.select_set(True)

    props             = obj.archiforge_door
    props.is_af_door  = True
    props.object_name = obj.name

    _setup_door_materials(obj)
    return obj, props


# ════════════════════════════════════════════════════════════
#  OPERADORES
# ════════════════════════════════════════════════════════════

class ARCHIFORGE_OT_door(Operator):
    bl_idname      = "archiforge.door"
    bl_label       = "Add AF Door"
    bl_description = "Add a parametric ArchiForge door"
    bl_options     = {'REGISTER', 'UNDO'}

    door_type : EnumProperty(name="Type", items=AF_DOOR_TYPES, default='SINGLE')
    width : FloatProperty(name="Width", default=0.90, min=AF_DOOR_MIN_W, unit='LENGTH')
    height : FloatProperty(name="Height", default=2.10, min=AF_DOOR_MIN_H, unit='LENGTH')
    auto_boolean : BoolProperty(name="Auto Boolean", default=True)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        col = layout.column(align=True)
        col.label(text="New Door", icon='MESH_PLANE')
        col.prop(self, "door_type")
        col.separator()
        col.prop(self, "width")
        col.prop(self, "height")
        col.separator()
        col.prop(self, "auto_boolean")

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')

        obj, props = _create_door_object(context, "AF_Door")
        props.door_type    = self.door_type
        props.width        = self.width
        props.height       = self.height
        props.auto_boolean = self.auto_boolean

        _rebuild_door_mesh(obj, props)

        if self.auto_boolean:
            result = af_autoboolean.do_auto_boolean(
                context     = context,
                source_obj  = obj,
                cutter_type = 'DOOR',
                width       = self.width,
                height      = self.height,
            )
            if result['wall']:
                self.report({'INFO'}, f"Door → boolean en '{result['wall'].name}'")
            else:
                self.report({'INFO'}, "Door created (no wall found)")
        else:
            self.report({'INFO'}, f"Door created: {obj.name}")

        return {'FINISHED'}


# ────────────────────────────────────────────────────────────
#  OP: COLOCAR PUERTA INTERACTIVAMENTE SOBRE MURO
# ────────────────────────────────────────────────────────────
class ARCHIFORGE_OT_door_place(Operator):
    """
    Coloca una puerta AF haciendo clic sobre un muro.
    Usa ray_cast para encontrar la posición exacta y
    orientar la puerta perpendicular a la cara del muro.
    """
    bl_idname      = "archiforge.door_place"
    bl_label       = "Place Door on Wall"
    bl_description = "Click on a wall to place a door there"
    bl_options     = {'REGISTER', 'UNDO'}

    door_type : EnumProperty(name="Type", items=AF_DOOR_TYPES, default='SINGLE')
    width : FloatProperty(name="Width", default=0.90, min=AF_DOOR_MIN_W, unit='LENGTH')
    height : FloatProperty(name="Height", default=2.10, min=AF_DOOR_MIN_H, unit='LENGTH')

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)
        self.report({'INFO'}, "Click on a wall to place the door (ESC to cancel)")
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type in {'ESC', 'RIGHTMOUSE'}:
            self.report({'INFO'}, "Placement cancelled")
            return {'CANCELLED'}

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            hit = self._raycast_wall(context, event)
            if hit is None:
                self.report({'WARNING'}, "Click on a wall surface")
                return {'RUNNING_MODAL'}

            wall_obj, hit_loc, hit_normal = hit
            self._create_door_at(context, wall_obj, hit_loc, hit_normal)
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
            context.view_layer.depsgraph,
            origin,
            vector,
        )

        if not hit:
            return None
        if not (hasattr(obj, "archiforge_wall")
                and obj.archiforge_wall.is_af_wall):
            return None

        return obj, loc, normal

    def _create_door_at(self, context, wall_obj, hit_loc, hit_normal):
        # ── 1. Crear objeto ──
        bpy.ops.object.select_all(action='DESELECT')
        obj, props = _create_door_object(context, "AF_Door")

        props.door_type = self.door_type
        props.width     = self.width
        props.height    = self.height

        # ── 2. Orientar perpendicular al muro ──
        n = hit_normal.normalized()

        tangent = Vector((-n.y, n.x, 0.0))
        if tangent.length < 1e-4:
            tangent = Vector((1, 0, 0))
        tangent.normalize()

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

        hit_centered = hit_loc - x_axis * (self.width * 0.5)
        obj.matrix_world = Matrix.Translation(hit_centered) @ rot_mat

        # ── 3. Regenerar mesh ──
        _rebuild_door_mesh(obj, props)

        # ── 4. Auto boolean ──
        result = af_autoboolean.do_auto_boolean(
            context     = context,
            source_obj  = obj,
            cutter_type = 'DOOR',
            width       = self.width,
            height      = self.height,
            wall_obj    = wall_obj,
        )

        if result['wall']:
            self.report({'INFO'}, f"Door placed on '{wall_obj.name}'")
        else:
            self.report({'INFO'}, "Door placed (boolean failed)")


class ARCHIFORGE_OT_door_update(Operator):
    bl_idname      = "archiforge.door_update"
    bl_label       = "Update Door"
    bl_description = "Force regeneration of the selected door"
    bl_options     = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj is not None and obj.type == 'MESH'
            and hasattr(obj, AF_DOOR_PROP)
            and obj.archiforge_door.is_af_door
        )

    def execute(self, context):
        obj   = context.active_object
        props = obj.archiforge_door
        _rebuild_door_mesh(obj, props)
        self.report({'INFO'}, "Door updated")
        return {'FINISHED'}


class ARCHIFORGE_OT_door_flip_hinge(Operator):
    bl_idname      = "archiforge.door_flip_hinge"
    bl_label       = "Flip Hinge Side"
    bl_description = "Switch hinge from left to right or vice versa"
    bl_options     = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj is not None and obj.type == 'MESH'
            and hasattr(obj, AF_DOOR_PROP)
            and obj.archiforge_door.is_af_door
        )

    def execute(self, context):
        props = context.active_object.archiforge_door
        props.hinge_side = 'RIGHT' if props.hinge_side == 'LEFT' else 'LEFT'
        return {'FINISHED'}


class ARCHIFORGE_OT_door_toggle_open(Operator):
    bl_idname      = "archiforge.door_toggle_open"
    bl_label       = "Toggle Open/Closed"
    bl_description = "Toggle door between open and closed state"
    bl_options     = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj is not None and obj.type == 'MESH'
            and hasattr(obj, AF_DOOR_PROP)
            and obj.archiforge_door.is_af_door
        )

    def execute(self, context):
        props = context.active_object.archiforge_door
        if props.open_angle < math.radians(5):
            props.open_angle = math.radians(90)
        else:
            props.open_angle = 0.0
        return {'FINISHED'}


class ARCHIFORGE_OT_door_apply_boolean(Operator):
    bl_idname      = "archiforge.door_apply_boolean"
    bl_label       = "Apply Boolean to Wall"
    bl_description = "Cut opening in nearest wall for this door"
    bl_options     = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj is not None and obj.type == 'MESH'
            and hasattr(obj, AF_DOOR_PROP)
            and obj.archiforge_door.is_af_door
        )

    def execute(self, context):
        obj   = context.active_object
        props = obj.archiforge_door

        result = af_autoboolean.do_auto_boolean(
            context     = context,
            source_obj  = obj,
            cutter_type = 'DOOR',
            width       = props.width,
            height      = props.height,
        )

        if result['success']:
            wall_name = result['wall'].name if result['wall'] else "none"
            self.report({'INFO'}, f"✅ Boolean applied to '{wall_name}'")
        else:
            self.report({'WARNING'}, "⚠️  Could not apply boolean")

        return {'FINISHED'}


# ════════════════════════════════════════════════════════════
#  PANEL
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_PT_door(Panel):
    bl_label       = "Door Properties"
    bl_idname      = "ARCHIFORGE_PT_door"
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
            and hasattr(obj, AF_DOOR_PROP)
            and obj.archiforge_door.is_af_door
        )

    def draw_header(self, context):
        self.layout.label(text="", icon='MESH_PLANE')

    def draw(self, context):
        obj    = context.active_object
        props  = obj.archiforge_door
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Type", icon='MODIFIER')
        col.prop(props, "door_type", text="")

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Dimensions", icon='ARROW_LEFTRIGHT')
        col.prop(props, "width")
        col.prop(props, "height")
        col.prop(props, "depth", text="Thickness")

        box = layout.box()
        row = box.row(align=True)
        row.prop(
            props, "frame_enable", text="Frame",
            icon='TRIA_DOWN' if props.frame_enable else 'TRIA_RIGHT',
            toggle=True, emboss=False,
        )
        if props.frame_enable:
            col = box.column(align=True)
            col.prop(props, "frame_width")
            col.prop(props, "frame_depth")
            col.prop(props, "frame_offset")

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Panel Style", icon='MESH_GRID')
        col.prop(props, "panel_style", text="")
        if props.panel_style in ('RAISED', 'FLAT'):
            col.separator(factor=0.3)
            col.prop(props, "panel_rows")
            col.prop(props, "panel_cols")
            col.prop(props, "panel_border")
            col.prop(props, "panel_inset")

        box = layout.box()
        row = box.row(align=True)
        row.prop(
            props, "glass_enable", text="Glass Panel",
            icon='TRIA_DOWN' if props.glass_enable else 'TRIA_RIGHT',
            toggle=True, emboss=False,
        )
        if props.glass_enable:
            col = box.column(align=True)
            col.prop(props, "glass_ratio")
            col.prop(props, "glass_thickness")

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Opening", icon='DRIVER_ROTATIONAL_DIFFERENCE')
        col.prop(props, "open_angle")
        col.prop(props, "hinge_side", text="Hinge")
        row = col.row(align=True)
        row.operator("archiforge.door_toggle_open", text="Open / Close",
                     icon='DRIVER_ROTATIONAL_DIFFERENCE')
        row.operator("archiforge.door_flip_hinge", text="Flip Hinge",
                     icon='UV_SYNC_SELECT')

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Handle", icon='HANDLE_FREE')
        col.prop(props, "handle_type", text="")
        if props.handle_type != 'NONE':
            col.prop(props, "handle_height")
            col.prop(props, "handle_offset")

        box = layout.box()
        row = box.row(align=True)
        row.prop(
            props, "threshold_enable", text="Threshold",
            icon='TRIA_DOWN' if props.threshold_enable else 'TRIA_RIGHT',
            toggle=True, emboss=False,
        )
        if props.threshold_enable:
            col = box.column(align=True)
            col.prop(props, "threshold_height")
            col.prop(props, "threshold_width")

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Material Slots", icon='MATERIAL')
        if props.frame_enable:
            col.prop(props, "mat_frame",  text="Frame")
        col.prop(props, "mat_panel",  text="Panel")
        if props.glass_enable:
            col.prop(props, "mat_glass",  text="Glass")
        if props.handle_type != 'NONE':
            col.prop(props, "mat_handle", text="Handle")
        if props.threshold_enable:
            col.prop(props, "mat_thresh", text="Threshold")

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Boolean", icon='MOD_BOOLEAN')
        col.prop(props, "auto_boolean")
        col.operator("archiforge.door_apply_boolean",
                     text="Apply Boolean Now", icon='MOD_BOOLEAN')

        layout.separator()
        layout.operator(
            "archiforge.door_place",
            text="Place New Door on Wall (Click)",
            icon='RESTRICT_SELECT_OFF',
        )
        layout.operator(
            "archiforge.door_update",
            text="Force Update",
            icon='FILE_REFRESH',
        )


# ════════════════════════════════════════════════════════════
#  REGISTRO
# ════════════════════════════════════════════════════════════
classes = [
    AF_DoorProperties,

    ARCHIFORGE_OT_door,
    ARCHIFORGE_OT_door_place,
    ARCHIFORGE_OT_door_update,
    ARCHIFORGE_OT_door_flip_hinge,
    ARCHIFORGE_OT_door_toggle_open,
    ARCHIFORGE_OT_door_apply_boolean,

    ARCHIFORGE_PT_door,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Object.archiforge_door = PointerProperty(
        type        = AF_DoorProperties,
        name        = "ArchiForge Door",
        description = "ArchiForge parametric door properties",
    )

    print("[ArchiForge] ✅ af_door — registered")


def unregister():
    if hasattr(bpy.types.Object, "archiforge_door"):
        del bpy.types.Object.archiforge_door

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    print("[ArchiForge] 🔴 af_door — unregistered")