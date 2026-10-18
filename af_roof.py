# -*- coding: utf-8 -*-

# ╔══════════════════════════════════════════════════════════╗
# ║         ARCHIFORGE — af_roof.py                         ║
# ║         Techos Paramétricos para Blender 3.3 LTS        ║
# ║         GPL v3 — ArchiForge Devs                        ║
# ╚══════════════════════════════════════════════════════════╝
# v1.1 — tejas CO (zinc/eternit/española/termoacústica) + fix 3.3 + mansarda

# <pep8 compliant>

# ════════════════════════════════════════════════════════════
#  ¿QUÉ HACE ESTE MÓDULO?
#
#  Genera techos paramétricos completos con:
#  - Varios tipos de techo: plano, a dos aguas, cuatro aguas,
#    shed (un agua), mansarda, bóveda, mariposa, saltbox
#  - Alero (eave) configurable
#  - Cumbrera (ridge) configurable
#  - Generación desde outline rectangular o polígono custom
#  - Capa de tejas / cubierta (9 sistemas incl. zinc y eternit)
#  - Cornisa / fascia board
#  - Soffit (entablado del alero)
#  - Lucernario / skylight opcional
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

from . import af_material


# ════════════════════════════════════════════════════════════
#  CONSTANTES
# ════════════════════════════════════════════════════════════
AF_ROOF_PROP = "archiforge_roof"

AF_ROOF_TYPES = [
    ('FLAT',      "Flat",       "Flat roof / azotea",              'MESH_PLANE',    0),
    ('GABLE',     "Gable",      "Two slopes / dos aguas",          'TRIA_UP',       1),
    ('HIP',       "Hip",        "Four slopes / cuatro aguas",      'MESH_UVSPHERE', 2),
    ('SHED',      "Shed",       "Single slope / un agua",          'TRIA_RIGHT',    3),
    ('MANSARD',   "Mansard",    "Mansard / Gambrail double slope",  'SNAP_VOLUME',   4),
    ('BUTTERFLY', "Butterfly",  "Butterfly / mariposa (V-shape)",  'TRIA_DOWN',     5),
    ('SALTBOX',   "Saltbox",    "Saltbox (asymmetric gable)",      'MOD_TRIANGULATE',6),
    ('VAULT',     "Barrel Vault","Barrel vault / bóveda",          'MESH_CYLINDER', 7),
]

AF_TILE_TYPES = [
    ('NONE',     "None",     "No tile surface"),
    ('FLAT_TILE',"Flat Tile","Flat tile rows"),
    ('ROMAN',    "Roman",    "Roman ribs + pans"),
    ('ESPANOLA', "Espanola", "Teja española de barril (CO)"),
    ('ZINC',     "Zinc",     "Teja de zinc ondulada (CO)"),
    ('ETERNIT',  "Eternit",  "Fibrocemento ondulado (CO)"),
    ('THERMO',   "Termoacustica","UPVC / sandwich moderno (CO)"),
    ('METAL',    "Metal",    "Corrugated metal sheet"),
    ('SHINGLE',  "Shingle",  "Wood / asphalt shingles"),
]


# ════════════════════════════════════════════════════════════
#  PROPERTYGROUP
# ════════════════════════════════════════════════════════════
class AF_RoofProperties(PropertyGroup):

    is_af_roof  : BoolProperty(
        name="Is ArchiForge Roof", default=True, options={'HIDDEN'},
    )
    object_name : StringProperty(
        name="Object Name", default="", options={'HIDDEN'},
    )

    # ── Tipo ─────────────────────────────────────────────────
    roof_type : EnumProperty(
        name="Roof Type", items=AF_ROOF_TYPES, default='GABLE',
        update=lambda s, c: af_roof_update(s, c),
    )

    # ── Dimensiones base ─────────────────────────────────────
    width : FloatProperty(
        name="Width",
        description="Roof base width (X axis)",
        default=8.0, min=0.5, max=200.0, unit='LENGTH',
        update=lambda s, c: af_roof_update(s, c),
    )
    depth : FloatProperty(
        name="Depth",
        description="Roof base depth (Y axis)",
        default=6.0, min=0.5, max=200.0, unit='LENGTH',
        update=lambda s, c: af_roof_update(s, c),
    )
    z_base : FloatProperty(
        name="Base Height",
        description="Z height of the roof base / eave",
        default=3.0, min=0.0, max=50.0, unit='LENGTH',
        update=lambda s, c: af_roof_update(s, c),
    )

    # ── Pendiente ─────────────────────────────────────────────
    pitch : FloatProperty(
        name="Pitch Angle",
        description="Roof slope angle",
        default=math.radians(30),
        min=math.radians(1),
        max=math.radians(89),
        subtype='ANGLE',
        update=lambda s, c: af_roof_update(s, c),
    )
    pitch_back : FloatProperty(
        name="Back Pitch",
        description="Back slope angle (SALTBOX / BUTTERFLY)",
        default=math.radians(20),
        min=math.radians(1),
        max=math.radians(89),
        subtype='ANGLE',
        update=lambda s, c: af_roof_update(s, c),
    )

    # ── Alero (Eave) ──────────────────────────────────────────
    eave_width : FloatProperty(
        name="Eave Width",
        description="Horizontal overhang of eave",
        default=0.50, min=0.0, max=3.0, unit='LENGTH',
        update=lambda s, c: af_roof_update(s, c),
    )
    eave_thickness : FloatProperty(
        name="Eave Thickness",
        description="Thickness of the roof slab at eave",
        default=0.20, min=0.05, max=0.80, unit='LENGTH',
        update=lambda s, c: af_roof_update(s, c),
    )

    # ── Fascia / Cornisa ──────────────────────────────────────
    fascia_enable : BoolProperty(
        name="Fascia Board",
        description="Generate fascia board at eave edge",
        default=True,
        update=lambda s, c: af_roof_update(s, c),
    )
    fascia_width : FloatProperty(
        name="Fascia Width",
        description="Height of fascia board",
        default=0.18, min=0.02, max=0.60, unit='LENGTH',
        update=lambda s, c: af_roof_update(s, c),
    )
    fascia_depth : FloatProperty(
        name="Fascia Depth",
        description="Thickness of fascia board",
        default=0.03, min=0.01, max=0.20, unit='LENGTH',
        update=lambda s, c: af_roof_update(s, c),
    )

    # ── Soffit (entablado inferior del alero) ─────────────────
    soffit_enable : BoolProperty(
        name="Soffit",
        description="Generate soffit panel under eave",
        default=True,
        update=lambda s, c: af_roof_update(s, c),
    )
    soffit_thickness : FloatProperty(
        name="Soffit Thickness",
        description="Thickness of soffit panel",
        default=0.012, min=0.005, max=0.05, unit='LENGTH',
        update=lambda s, c: af_roof_update(s, c),
    )

    # ── Cumbrera ──────────────────────────────────────────────
    ridge_enable : BoolProperty(
        name="Ridge Cap",
        description="Generate ridge cap at roof peak",
        default=True,
        update=lambda s, c: af_roof_update(s, c),
    )
    ridge_width : FloatProperty(
        name="Ridge Width",
        description="Width of ridge cap",
        default=0.20, min=0.05, max=1.0, unit='LENGTH',
        update=lambda s, c: af_roof_update(s, c),
    )
    ridge_height : FloatProperty(
        name="Ridge Height",
        description="Height of ridge cap",
        default=0.10, min=0.02, max=0.50, unit='LENGTH',
        update=lambda s, c: af_roof_update(s, c),
    )

    # ── Mansarda (solo MANSARD) ────────────────────────────────
    mansard_break : FloatProperty(
        name="Break Height",
        description="Height of break point (lower steep slope)",
        default=1.0, min=0.1, max=10.0, unit='LENGTH',
        update=lambda s, c: af_roof_update(s, c),
    )
    mansard_pitch_lower : FloatProperty(
        name="Lower Pitch",
        description="Angle of the lower steeper slope",
        default=math.radians(65),
        min=math.radians(10), max=math.radians(89),
        subtype='ANGLE',
        update=lambda s, c: af_roof_update(s, c),
    )

    # ── Bóveda (solo VAULT) ───────────────────────────────────
    vault_segments : IntProperty(
        name="Vault Segments",
        description="Number of segments along the vault arc",
        default=16, min=4, max=64,
        update=lambda s, c: af_roof_update(s, c),
    )

    # ── Tejas / cubierta ──────────────────────────────────────
    tile_type : EnumProperty(
        name="Tile Type", items=AF_TILE_TYPES, default='NONE',
        update=lambda s, c: af_roof_tile_update(s, c),
    )
    tile_length : FloatProperty(
        name="Tile Length",
        default=0.40, min=0.05, max=12.0, unit='LENGTH',
        update=lambda s, c: af_roof_update(s, c),
    )
    tile_width : FloatProperty(
        name="Tile Width",
        default=0.25, min=0.05, max=2.0, unit='LENGTH',
        update=lambda s, c: af_roof_update(s, c),
    )
    tile_thickness : FloatProperty(
        name="Tile Thickness",
        default=0.015, min=0.003, max=0.05, unit='LENGTH',
        update=lambda s, c: af_roof_update(s, c),
    )
    tile_overlap : FloatProperty(
        name="Tile Overlap",
        description="Overlap fraction between rows",
        default=0.30, min=0.05, max=0.70,
        update=lambda s, c: af_roof_update(s, c),
    )

    # ── Lucernario (skylight) ─────────────────────────────────
    skylight_enable : BoolProperty(
        name="Skylight",
        description="Add a skylight/velux window on the roof slope",
        default=False,
        update=lambda s, c: af_roof_update(s, c),
    )
    skylight_width : FloatProperty(
        name="Skylight Width", default=0.78, min=0.2, unit='LENGTH',
        update=lambda s, c: af_roof_update(s, c),
    )
    skylight_height : FloatProperty(
        name="Skylight Height", default=0.98, min=0.2, unit='LENGTH',
        update=lambda s, c: af_roof_update(s, c),
    )
    skylight_pos_x : FloatProperty(
        name="Position X", default=0.5, min=0.0, max=1.0,
        description="Normalized position along roof width",
        update=lambda s, c: af_roof_update(s, c),
    )
    skylight_pos_y : FloatProperty(
        name="Position Y", default=0.5, min=0.0, max=1.0,
        description="Normalized position along slope",
        update=lambda s, c: af_roof_update(s, c),
    )

    # ── Materiales ────────────────────────────────────────────
    mat_roof    : IntProperty(name="Roof Material",   default=0, min=0)
    mat_tile    : IntProperty(name="Tile Material",   default=1, min=0)
    mat_fascia  : IntProperty(name="Fascia Material", default=2, min=0)
    mat_soffit  : IntProperty(name="Soffit Material", default=3, min=0)
    mat_ridge   : IntProperty(name="Ridge Material",  default=4, min=0)
    mat_skylight: IntProperty(name="Skylight Glass",  default=5, min=0)


# ════════════════════════════════════════════════════════════
#  GENERADOR
# ════════════════════════════════════════════════════════════
class AF_RoofGenerator:
    """
    Motor de generación de techos paramétricos.
    Sistema de coordenadas:
      X = ancho (izquierda→derecha)
      Y = profundidad (frente→atrás)
      Z = altura (suelo→arriba)
    Origen: esquina inferior izquierda del perímetro base.
    """

    def __init__(self, props):
        self.props = props
        self.bm    = bmesh.new()
        # (3.3) material_index nativo, sin capa int custom

    # ────────────────────────────────────────────────────────
    #  UTILIDAD — Prisma rectangular
    # ────────────────────────────────────────────────────────
    def _box(self, x0, x1, y0, y1, z0, z1, mi=0):
        bm  = self.bm

        if (abs(x1-x0) < 1e-5 or abs(y1-y0) < 1e-5
                or abs(z1-z0) < 1e-5):
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
        bm.verts.ensure_lookup_table()

        for fi in [
            (0,1,5,4),(2,3,7,6),(0,3,2,1),
            (4,5,6,7),(0,4,7,3),(1,2,6,5),
        ]:
            f = bm.faces.new([verts[i] for i in fi])
            f.material_index = mi

    # ────────────────────────────────────────────────────────
    #  UTILIDAD — Cara plana desde lista de Vector3
    # ────────────────────────────────────────────────────────
    def _face(self, pts3d, mi=0):
        """Crea una cara n-gon desde lista de Vector((x,y,z))."""
        bm  = self.bm
        if len(pts3d) < 3:
            return
        verts = [bm.verts.new(p) for p in pts3d]
        bm.verts.ensure_lookup_table()
        try:
            f = bm.faces.new(verts)
            f.material_index = mi
        except Exception:
            pass

    def _quad(self, a, b, c, d, mi=0):
        bm = self.bm
        try:
            v = [bm.verts.new(p) for p in (a, b, c, d)]
            bm.verts.ensure_lookup_table()
            f = bm.faces.new(v)
            f.material_index = mi
        except Exception:
            pass

    def _slope_tube(self, p0, p1, r, mi=0, n=8):
        """Tubo cerrado entre 2 puntos (barriles de teja)."""
        bm = self.bm
        dd = p1 - p0
        if dd.length < 1e-6:
            return
        dn = dd.normalized()
        up = Vector((0, 0, 1)) if abs(dn.z) < 0.95 else Vector((0, 1, 0))
        u = dn.cross(up).normalized()
        v = dn.cross(u).normalized()
        try:
            ring = []
            for pp in (p0, p1):
                rr = []
                for i in range(n):
                    a = i * 2 * math.pi / n
                    rr.append(bm.verts.new(
                        pp + (u * math.cos(a) + v * math.sin(a)) * r))
                ring.append(rr)
            bm.verts.ensure_lookup_table()
            r0, r1 = ring
            for i in range(n):
                j = (i + 1) % n
                f = bm.faces.new([r0[i], r0[j], r1[j], r1[i]])
                f.material_index = mi
            for cap in (list(reversed(r0)), r1):
                f = bm.faces.new(cap)
                f.material_index = mi
        except Exception:
            pass

    # ────────────────────────────────────────────────────────
    #  UTILIDAD — Panel extruido desde quad-outline
    # ────────────────────────────────────────────────────────
    def _panel(self, pts3d, thickness_vec, mi=0):
        """
        Genera un panel con espesor:
        pts3d    = lista de Vector3 (cara frontal)
        thickness_vec = Vector3 desplazamiento para cara trasera
        """
        bm  = self.bm
        n   = len(pts3d)
        if n < 3:
            return

        vf = [bm.verts.new(p) for p in pts3d]
        vb = [bm.verts.new(p + thickness_vec) for p in pts3d]
        bm.verts.ensure_lookup_table()

        # Cara frontal
        try:
            f = bm.faces.new(vf)
            f.material_index = mi
        except Exception:
            pass
        # Cara trasera
        try:
            f = bm.faces.new(list(reversed(vb)))
            f.material_index = mi
        except Exception:
            pass
        # Laterales
        for i in range(n):
            j = (i+1) % n
            try:
                f = bm.faces.new([vf[i], vf[j], vb[j], vb[i]])
                f.material_index = mi
            except Exception:
                pass

    # ────────────────────────────────────────────────────────
    #  FASCIA + SOFFIT — Alero
    # ────────────────────────────────────────────────────────
    def _build_eave_details(self, slope_pts_2d, axis='X'):
        """
        Construye fascia y soffit para un alero.
        slope_pts_2d: [(y_or_x_pos, z_pos), ...] en el plano del alero
        axis: 'X' o 'Y' según la dirección del alero
        """
        p  = self.props
        w  = p.width
        d  = p.depth

        if not p.fascia_enable and not p.soffit_enable:
            return

        fw = p.fascia_width
        fd = p.fascia_depth
        st = p.soffit_thickness
        ew = p.eave_width

        if axis == 'X':
            length = w + ew * 2
            for y_base, z_base in slope_pts_2d:
                # Fascia
                if p.fascia_enable:
                    self._box(
                        -ew, w + ew,
                        y_base - fd, y_base,
                        z_base - fw, z_base,
                        p.mat_fascia
                    )
                # Soffit
                if p.soffit_enable:
                    self._box(
                        -ew, w + ew,
                        y_base, y_base + st,
                        z_base - fw, z_base - fw + st,
                        p.mat_soffit
                    )
        else:
            for x_base, z_base in slope_pts_2d:
                if p.fascia_enable:
                    self._box(
                        x_base - fd, x_base,
                        -ew, d + ew,
                        z_base - fw, z_base,
                        p.mat_fascia
                    )
                if p.soffit_enable:
                    self._box(
                        x_base, x_base + st,
                        -ew, d + ew,
                        z_base - fw, z_base - fw + st,
                        p.mat_soffit
                    )

    # ═══════════════════════════════════════════════════════
    #  TEJAS — versión 1.1 (láminas, barriles, ondas)
    # ═══════════════════════════════════════════════════════

    def _quad_slope_unit(self, orig, Ux, Uy, wid, up, thk, mi=0):
        """Hilera unitaria de tejas planas (FLAT / SHINGLE)."""
        n  = max(1, int(wid // up))
        dx = wid / n
        for i in range(n):
            o = orig + Ux * (i * dx)
            pts = [o + Ux * dx * 0.96,
                   o,
                   o + Uy * up,
                   o + Ux * dx * 0.96 + Uy * up]
            self._panel(pts, Vector((0, 0, -thk)), mi)

    def _terrace_types(self):
        return {'FLAT_TILE', 'SHINGLE'}

    def _tube_roof(self, orig, Ux, Uy, wid, up, r, mi=0, hollow=False):
        """Tejas medio tubo tipo española. Origen: [Vector]."""
        n = max(2, int(wid // (r * 2)) + 1)
        for i in range(n):
            o = orig + Ux * (i * (wid / (n - 1)))
            self._slope_tube(o, o + Uy * up, r, mi)

    def _build_tiles_on_slope(self, A, ex, U, ex_len, slope,
                              z0, panel='UP'):
        """Hileras de tejas sobre una pendiente. panel UP/DN."""
        p  = self.props
        bm = self.bm

        if p.tile_type == 'NONE':
            return

        if p.tile_type in {'ZINC', 'ETERNIT', 'THERMO', 'METAL'}:
            self._build_sheet_on_quad(
                A, ex, U, ex_len, slope, z0, panel)
            return

        op = p.tile_overlap
        up = p.tile_length * (1 - op) if panel == 'UP' else \
            p.tile_length * (1 - op)
        r  = p.tile_width / 2 * 0.98 if p.tile_type == 'ESPANOLA' \
            else p.tile_width / 2
        cw = p.tile_width * 0.96 if p.tile_type in {
            'ROMAN', 'ESPANOLA'} else p.tile_width * 0.9

        steps = int(slope / up) + 1
        slope_total = p.tile_length + (steps - 1) * up

        if p.tile_type in self._terrace_types():
            self._quad_slope_unit(A, ex, U, ex_len, up,
                                  p.tile_thickness, p.mat_tile)
        elif p.tile_type in {'ROMAN', 'ESPANOLA'}:
            self._tube_roof(A, ex, U, ex_len, up * steps, r,
                            p.mat_tile, True)
        else:
            self._quad_slope_unit(A, ex, U, ex_len, up,
                                  p.tile_thickness, p.mat_tile)

        # Nudge to ridge
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

    def _build_sheet_on_quad(self, A, ex, U, ex_len, slope, z0,
                             panel='UP'):
        """
        Láminas onduladas (ZINC/ETERNIT) o planas (THERMO/METAL).
        A: punto inicial alero. ex: dirección a lo largo del alero.
        U: dirección de la pendiente. ex_len: longitud del alero.
        slope: longitud de la pendiente. panel: cuneta arriba/abajo.
        """
        p   = self.props
        Lsh = max(0.30, p.tile_length)
        pitch = max(0.02, p.tile_width)
        n_sheets = max(1, int(math.ceil(ex_len / pitch)))
        dx  = ex_len / n_sheets
        n_rows = max(1, int(math.ceil(slope / (Lsh * 0.9))))
        dz = slope / n_rows

        wave = {'ZINC': 8, 'ETERNIT': 6}.get(p.tile_type, 0)
        thick = p.tile_thickness if wave == 0 else 0.002

        half = pitch / 2
        for si in range(n_sheets):
            o = A + ex * (si * dx)
            for ri in range(n_rows):
                q0 = o + U * (ri * dz)
                q1 = o + ex * dx + U * (ri * dz)
                q2 = o + ex * dx + U * ((ri + 1) * dz)
                q3 = o + U * ((ri + 1) * dz)
                if wave == 0:
                    self._quad(q0, q1, q2, q3, p.mat_tile)
                else:
                    prev = None
                    for k in range(wave + 1):
                        f = k / wave
                        zoff = Vector((0, 0, abs(math.sin(f * math.pi))
                                       * half))
                        b = q0.lerp(q1, f) + zoff
                        t = q3.lerp(q2, f) + zoff
                        if prev is not None:
                            self._quad(prev[0], b, t, prev[1],
                                       p.mat_tile)
                        prev = (b, t)
        # Cuneta
        bm = self.bm
        bm.verts.ensure_lookup_table()

    # ────────────────────────────────────────────────────────
    #  CUMBRERA — Remate en pico
    # ────────────────────────────────────────────────────────
    def _build_ridge_cap(self, ridge_start, ridge_end):
        """Cumbrera prismática desde inicio hasta fin."""
        p   = self.props
        if not p.ridge_enable:
            return

        rs = Vector(ridge_start) if not isinstance(
            ridge_start, Vector) else ridge_start
        re = Vector(ridge_end) if not isinstance(
            ridge_end, Vector) else ridge_end

        hw = p.ridge_width / 2
        hh = p.ridge_height
        direction = (re - rs)
        if direction.length < 1e-6:
            return
        dn = direction.normalized()

        # Perpendicular horizontal
        perp = Vector((-dn.y, dn.x, 0))
        if perp.length < 1e-6:
            perp = Vector((1, 0, 0))
        perp.normalize()

        # 2 pendientes de cumbrera
        p1 = rs - perp * hw
        p2 = rs + perp * hw
        p3 = (rs + re) / 2 + Vector((0, 0, hh))
        q1 = re - perp * hw
        q2 = re + perp * hw
        q3 = (rs + re) / 2 + Vector((0, 0, hh))

        self._quad(p1, q1, q3, p3, p.mat_ridge)
        self._quad(p3, q3, q2, p2, p.mat_ridge)

        # Tapas de extremos
        self._face([p1, p2, p3], p.mat_ridge)
        self._face([q2, q1, q3], p.mat_ridge)

    # ────────────────────────────────────────────────────────
    #  LUCERNARIO — Ventana sobre pendiente
    # ────────────────────────────────────────────────────────
    def _build_skylight(self, slope_origin, slope_dir, slope_len,
                        width_dir, width_len, z_eave):
        """
        Lucernario sobre una pendiente:
          slope_origin: punto en alero (eave)
          slope_dir:    dirección unitaria subiendo pendiente
          slope_len:    longitud de pendiente
          width_dir:    dirección a lo largo del alero
          width_len:    longitud del alero
          z_eave:       altura del alero
        """
        p = self.props
        if not p.skylight_enable:
            return

        cx = p.skylight_pos_x * width_len
        cy = p.skylight_pos_y * slope_len
        sw = min(p.skylight_width, width_len * 0.8)
        sh = min(p.skylight_height, slope_len * 0.6)

        center = slope_origin + width_dir * cx + slope_dir * cy

        hw = width_dir * (sw / 2)
        hh = slope_dir * (sh / 2)

        c00 = center - hw - hh
        c10 = center + hw - hh
        c11 = center + hw + hh
        c01 = center - hw + hh

        frame_h = 0.08
        up = Vector((0, 0, 1))
        self._quad(
            c00 + up * frame_h, c10 + up * frame_h,
            c11 + up * frame_h, c01 + up * frame_h,
            p.mat_skylight
        )

    # ═══════════════════════════════════════════════════════
    #  CONSTRUCTORES POR TIPO
    # ═══════════════════════════════════════════════════════

    # ────────────────────────────────────────────────────────
    #  1. GABLE — Dos aguas
    # ────────────────────────────────────────────────────────
    def _build_gable(self):
        p  = self.props
        w  = p.width
        d  = p.depth
        zb = p.z_base
        ew = p.eave_width
        et = p.eave_thickness
        an = p.pitch

        rise = math.tan(an) * (d / 2)
        zr   = zb + rise
        slope = (d / 2) / math.cos(an)

        x0, x1 = -ew, w + ew
        yB, yF = -ew, d + ew

        # ── Los dos faldones (paneles) ──
        # Trasero: desde cumbrera (y=d/2) hacia atrás (y=-ew)
        back_top  = [Vector((x0, d/2, zr)), Vector((x1, d/2, zr)),
                     Vector((x1, yB, zb)), Vector((x0, yB, zb))]
        # Delantero
        front_top = [Vector((x0, yF, zb)), Vector((x1, yF, zb)),
                     Vector((x1, d/2, zr)), Vector((x0, d/2, zr))]

        thick = Vector((0, 0, -et))
        self._panel(back_top,  thick, p.mat_roof)
        self._panel(front_top, thick, p.mat_roof)

        # ── Tejas sobre los dos faldones ──
        # Trasero: ex=+X, U va del alero (yB) a cumbrera (d/2)
        Ub = (Vector((0, d/2 - yB, rise))).normalized()
        self._build_tiles_on_slope(
            Vector((x0, yB, zb)), Vector((1, 0, 0)), Ub,
            x1 - x0, slope + ew / math.cos(an), zb, 'UP')
        # Delantero: ex=+X, U va de (yF) a (d/2)
        Uf = (Vector((0, d/2 - yF, rise))).normalized()
        self._build_tiles_on_slope(
            Vector((x0, yF, zb)), Vector((1, 0, 0)), Uf,
            x1 - x0, slope + ew / math.cos(an), zb, 'UP')

        # ── Hastiales (gable ends, triángulos) ──
        self._face([Vector((0, 0, zb)),
                    Vector((0, d, zb)),
                    Vector((0, d/2, zr))], p.mat_roof)
        self._face([Vector((w, d, zb)),
                    Vector((w, 0, zb)),
                    Vector((w, d/2, zr))], p.mat_roof)

        # ── Cumbrera ──
        self._build_ridge_cap(Vector((x0, d/2, zr)),
                              Vector((x1, d/2, zr)))

        # ── Fascia / Soffit ──
        self._build_eave_details([(yB, zb), (yF, zb)], axis='X')

        # ── Lucernario (faldón delantero) ──
        self._build_skylight(
            Vector((x0, yF, zb)), Uf,
            slope + ew / math.cos(an),
            Vector((1, 0, 0)), x1 - x0, zb)

    # ────────────────────────────────────────────────────────
    #  2. SHED — Una agua
    # ────────────────────────────────────────────────────────
    def _build_shed(self):
        p  = self.props
        w  = p.width
        d  = p.depth
        zb = p.z_base
        ew = p.eave_width
        et = p.eave_thickness
        an = p.pitch

        rise  = math.tan(an) * d
        ztop  = zb + rise
        slope = d / math.cos(an)

        x0, x1 = -ew, w + ew
        yB, yF = -ew, d + ew

        top = [Vector((x0, yB, zb)), Vector((x1, yB, zb)),
               Vector((x1, yF, ztop + math.tan(an) * ew * 2)),
               Vector((x0, yF, ztop + math.tan(an) * ew * 2))]
        zb_low = zb
        # Ajuste: el borde bajo incluye alero
        zB = zb - math.tan(an) * ew
        top = [Vector((x0, yB, zB)), Vector((x1, yB, zB)),
               Vector((x1, yF, ztop + math.tan(an) * ew)),
               Vector((x0, yF, ztop + math.tan(an) * ew))]
        self._panel(top, Vector((0, 0, -et)), p.mat_roof)

        # Tejas
        U = (Vector((0, (yF - yB), (ztop + math.tan(an) * ew) - zB))
             ).normalized()
        self._build_tiles_on_slope(
            Vector((x0, yB, zB)), Vector((1, 0, 0)), U,
            x1 - x0, slope + 2 * ew / math.cos(an), zB, 'UP')

        # Muros laterales (triángulos) y trasero alto
        self._face([Vector((0, 0, zb_low)),
                    Vector((0, d, ztop)),
                    Vector((0, 0, ztop))], p.mat_roof)
        self._face([Vector((w, 0, zb_low)),
                    Vector((w, 0, ztop)),
                    Vector((w, d, ztop))], p.mat_roof)
        self._face([Vector((0, d, ztop)), Vector((w, d, ztop)),
                    Vector((w, d, zb_low)),
                    Vector((0, d, zb_low))], p.mat_roof)

        self._build_eave_details([(yB, zB)], axis='X')

        self._build_skylight(
            Vector((x0, yB, zB)), U,
            slope + 2 * ew / math.cos(an),
            Vector((1, 0, 0)), x1 - x0, zB)

    # ────────────────────────────────────────────────────────
    #  3. HIP — Cuatro aguas (limatesas)
    # ────────────────────────────────────────────────────────
    def _build_hip(self):
        p  = self.props
        w  = p.width
        d  = p.depth
        zb = p.z_base
        ew = p.eave_width
        et = p.eave_thickness
        an = p.pitch

        rise = math.tan(an) * (min(w, d) / 2)
        zr   = zb + rise

        x0, x1 = -ew, w + ew
        yB, yF = -ew, d + ew
        cx0, cx1 = (w - d) / 2 if w >= d else 0, \
            (w + d) / 2 if w >= d else w
        if w < d:
            cx0, cx1 = 0, w
        # Cumbrera horizontal centrada
        if w >= d:
            r0 = Vector((cx0, d / 2, zr))
            r1 = Vector((cx1, d / 2, zr))
        else:
            r0 = Vector((w / 2, (d - w) / 2, zr))
            r1 = Vector((w / 2, (d + w) / 2, zr))

        th = Vector((0, 0, -et))

        if w >= d:
            # Faldones front/back trapezoidales
            self._panel([Vector((x0, yB, zb)), Vector((x1, yB, zb)),
                         r1, r0], th, p.mat_roof)
            self._panel([r0, r1, Vector((x1, yF, zb)),
                         Vector((x0, yF, zb))], th, p.mat_roof)
            # Laterales triangulares
            self._panel([Vector((x0, yB, zb)),
                         r0,
                         Vector((x0, yF, zb))], th, p.mat_roof)
            self._panel([r1,
                         Vector((x1, yB, zb)),
                         Vector((x1, yF, zb))], th, p.mat_roof)
        else:
            self._panel([Vector((x0, yB, zb)), Vector((x1, yB, zb)),
                         r1, r0], th, p.mat_roof)
            self._panel([r0, r1, Vector((x1, yF, zb)),
                         Vector((x0, yF, zb))], th, p.mat_roof)
            self._panel([Vector((x0, yB, zb)),
                         r0,
                         Vector((x0, yF, zb))], th, p.mat_roof)
            self._panel([r1,
                         Vector((x1, yB, zb)),
                         Vector((x1, yF, zb))], th, p.mat_roof)

        # Tejas: faldones principales (front/back) + laterales
        slope_fb = (d / 2 + ew) / math.cos(an)
        Ub = (Vector((0, d / 2 - yB, rise))).normalized()
        Uf = (Vector((0, d / 2 - yF, rise))).normalized()
        self._build_tiles_on_slope(
            Vector((x0, yB, zb)), Vector((1, 0, 0)), Ub,
            x1 - x0, slope_fb, zb, 'UP')
        self._build_tiles_on_slope(
            Vector((x0, yF, zb)), Vector((1, 0, 0)), Uf,
            x1 - x0, slope_fb, zb, 'UP')
        # Laterales (U a lo largo de X)
        slope_lr = (w / 2 + ew) / math.cos(an)
        Ul = (Vector((w / 2 - x0, 0, rise))).normalized()
        Ur = (Vector((w / 2 - x1, 0, rise))).normalized()
        self._build_tiles_on_slope(
            Vector((x0, yB, zb)), Vector((0, 1, 0)), Ul,
            yF - yB, slope_lr, zb, 'UP')
        self._build_tiles_on_slope(
            Vector((x1, yB, zb)), Vector((0, 1, 0)), Ur,
            yF - yB, slope_lr, zb, 'UP')

        self._build_ridge_cap(r0, r1)
        self._build_eave_details([(yB, zb), (yF, zb)], axis='X')

        self._build_skylight(
            Vector((x0, yF, zb)), Uf, slope_fb,
            Vector((1, 0, 0)), x1 - x0, zb)

    # ────────────────────────────────────────────────────────
    #  4. SALTBOX — Dos aguas asimétricas
    # ────────────────────────────────────────────────────────
    def _build_saltbox(self):
        p  = self.props
        w  = p.width
        d  = p.depth
        zb = p.z_base
        ew = p.eave_width
        et = p.eave_thickness
        anF = p.pitch
        anB = p.pitch_back

        # Cumbrera descentrada: 1/3 frontal
        yc = d * 0.35
        zc = zb + math.tan(anF) * (d - yc)
        # Ajuste trasero para empatar altura
        riseB = zc - zb
        yB, yF = -ew, d + ew
        x0, x1 = -ew, w + ew
        # Extensión trasera más larga
        yB2 = yB - d * 0.15

        th = Vector((0, 0, -et))
        # Faldón trasero largo
        self._panel([Vector((x0, yc, zc)), Vector((x1, yc, zc)),
                     Vector((x1, yB2, zb - math.tan(anB) * d * 0.15)),
                     Vector((x0, yB2, zb - math.tan(anB) * d * 0.15))],
                    th, p.mat_roof)
        # Faldón delantero corto
        self._panel([Vector((x0, yF, zb)), Vector((x1, yF, zb)),
                     Vector((x1, yc, zc)), Vector((x0, yc, zc))],
                    th, p.mat_roof)

        zbB = zb - math.tan(anB) * d * 0.15
        Ub = (Vector((0, yc - yB2, zc - zbB))).normalized()
        Uf = (Vector((0, yc - yF, zc - zb))).normalized()
        slopeB = math.hypot(yc - yB2, zc - zbB)
        slopeF = math.hypot(yc - yF, zc - zb)
        self._build_tiles_on_slope(
            Vector((x0, yB2, zbB)), Vector((1, 0, 0)), Ub,
            x1 - x0, slopeB, zbB, 'UP')
        self._build_tiles_on_slope(
            Vector((x0, yF, zb)), Vector((1, 0, 0)), Uf,
            x1 - x0, slopeF, zb, 'UP')

        # Hastiales
        self._face([Vector((0, 0, zb)), Vector((0, d, zb)),
                    Vector((0, yc, zc))], p.mat_roof)
        self._face([Vector((w, d, zb)), Vector((w, 0, zb)),
                    Vector((w, yc, zc))], p.mat_roof)

        self._build_ridge_cap(Vector((x0, yc, zc)),
                              Vector((x1, yc, zc)))
        self._build_eave_details([(yB2, zbB), (yF, zb)], axis='X')

        self._build_skylight(
            Vector((x0, yF, zb)), Uf, slopeF,
            Vector((1, 0, 0)), x1 - x0, zb)

    # ────────────────────────────────────────────────────────
    #  5. BUTTERFLY — Alas invertidas (valle central)
    # ────────────────────────────────────────────────────────
    def _build_butterfly(self):
        p  = self.props
        w  = p.width
        d  = p.depth
        zb = p.z_base
        ew = p.eave_width
        et = p.eave_thickness
        an = p.pitch

        x0, x1 = -ew, w + ew
        yB, yF = -ew, d + ew
        yc = d / 2
        # Bordes altos, centro bajo
        zEdge = zb + math.tan(an) * (d / 2)
        zv = zb  # valle

        th = Vector((0, 0, -et))
        # Ala trasera: alta en yB, baja en yc
        self._panel([Vector((x0, yB, zEdge)), Vector((x1, yB, zEdge)),
                     Vector((x1, yc, zv)), Vector((x0, yc, zv))],
                    th, p.mat_roof)
        # Ala delantera
        self._panel([Vector((x0, yc, zv)), Vector((x1, yc, zv)),
                     Vector((x1, yF, zEdge)), Vector((x0, yF, zEdge))],
                    th, p.mat_roof)

        # Tejas: del valle hacia afuera (panel DN)
        Ub = (Vector((0, yB - yc, zEdge - zv))).normalized()
        Uf = (Vector((0, yF - yc, zEdge - zv))).normalized()
        slope = math.hypot(d / 2 + ew, zEdge - zv)
        self._build_tiles_on_slope(
            Vector((x0, yc, zv)), Vector((1, 0, 0)), Ub,
            x1 - x0, slope, zv, 'DN')
        self._build_tiles_on_slope(
            Vector((x0, yc, zv)), Vector((1, 0, 0)), Uf,
            x1 - x0, slope, zv, 'DN')

        # Tímpanos laterales
        self._face([Vector((0, 0, zEdge)), Vector((0, d, zEdge)),
                    Vector((0, yc, zv))], p.mat_roof)
        self._face([Vector((w, d, zEdge)), Vector((w, 0, zEdge)),
                    Vector((w, yc, zv))], p.mat_roof)

        self._build_eave_details([(yB, zEdge), (yF, zEdge)],
                                 axis='X')

    # ────────────────────────────────────────────────────────
    #  6. MANSARD — Cubierta francesa (2 pendientes/lado)
    #  v1.1: superior directo con _panel (sin sub-bmesh,
    #        sin mutación temporal de props → sin recursión).
    # ────────────────────────────────────────────────────────
    def _build_mansard(self):
        p  = self.props
        w  = p.width
        d  = p.depth
        zb = p.z_base
        ew = p.eave_width
        et = p.eave_thickness
        anL = p.mansard_pitch_lower
        anU = p.pitch
        hb  = p.mansard_break

        x0, x1 = -ew, w + ew
        yB, yF = -ew, d + ew
        runL = hb / math.tan(anL)
        zbk = zb + hb  # altura del quiebre

        # Plataforma superior: gable a escala reducida
        w2 = max(0.5, w - runL * 2)
        d2 = max(0.5, d - runL * 2)
        ox = (w - w2) / 2
        oz = zbk
        rise2 = math.tan(anU) * (d2 / 2)
        zr2 = oz + rise2

        th = Vector((0, 0, -et))

        # ── Taludes inferiores (4 lados, empinados) ──
        # Trasero
        self._panel([Vector((x0, yB, zb)), Vector((x1, yB, zb)),
                     Vector((ox + w2 + runL, oz, zbk)),
                     Vector((ox - runL, oz, zbk))],
                    th, p.mat_roof)
        # Delantero
        self._panel([Vector((ox - runL, oz + d2, zbk)),
                     Vector((ox + w2 + runL, oz + d2, zbk)),
                     Vector((x1, yF, zb)), Vector((x0, yF, zb))],
                    th, p.mat_roof)
        # Izquierdo
        self._panel([Vector((x0, yB, zb)),
                     Vector((ox - runL, oz, zbk)),
                     Vector((ox - runL, oz + d2, zbk)),
                     Vector((x0, yF, zb))],
                    th, p.mat_roof)
        # Derecho
        self._panel([Vector((ox + w2 + runL, oz, zbk)),
                     Vector((x1, yB, zb)), Vector((x1, yF, zb)),
                     Vector((ox + w2 + runL, oz + d2, zbk))],
                    th, p.mat_roof)

        # ── Cubierta superior (gable directo) ──
        yc2 = oz + d2 / 2 if False else (d / 2)
        self._panel([Vector((ox - runL, yc2, zr2)),
                     Vector((ox + w2 + runL, yc2, zr2)),
                     Vector((ox + w2 + runL, oz + d2, zbk)),
                     Vector((ox - runL, oz + d2, zbk))],
                    th, p.mat_roof)
        self._panel([Vector((ox - runL, oz, zbk)),
                     Vector((ox + w2 + runL, oz, zbk)),
                     Vector((ox + w2 + runL, yc2, zr2)),
                     Vector((ox - runL, yc2, zr2))],
                    th, p.mat_roof)

        # ── Tejas: taludes inferiores + superior ──
        slopeL = hb / math.sin(anL)
        Ub = (Vector((0, oz - yB, hb))).normalized()
        Uf = (Vector((0, (oz + d2) - yF, hb))).normalized()
        self._build_tiles_on_slope(
            Vector((x0, yB, zb)), Vector((1, 0, 0)), Ub,
            x1 - x0, slopeL, zb, 'UP')
        self._build_tiles_on_slope(
            Vector((x0, yF, zb)), Vector((1, 0, 0)), Uf,
            x1 - x0, slopeL, zb, 'UP')
        Ul = (Vector((ox - runL - x0, 0, hb))).normalized()
        Ur = (Vector((ox + w2 + runL - x1, 0, hb))).normalized()
        self._build_tiles_on_slope(
            Vector((x0, yB, zb)), Vector((0, 1, 0)), Ul,
            yF - yB, slopeL, zb, 'UP')
        self._build_tiles_on_slope(
            Vector((x1, yB, zb)), Vector((0, 1, 0)), Ur,
            yF - yB, slopeL, zb, 'UP')
        slopeU = (d2 / 2) / math.cos(anU)
        Uu = (Vector((0, d2 / 2, rise2))).normalized()
        self._build_tiles_on_slope(
            Vector((ox - runL, oz, zbk)), Vector((1, 0, 0)), Uu,
            w2 + runL * 2, slopeU, zbk, 'UP')
        Ud = (Vector((0, -(d2 / 2), rise2))).normalized()
        self._build_tiles_on_slope(
            Vector((ox - runL, oz + d2, zbk)), Vector((1, 0, 0)),
            Ud, w2 + runL * 2, slopeU, zbk, 'UP')

        self._build_ridge_cap(
            Vector((ox - runL, yc2, zr2)),
            Vector((ox + w2 + runL, yc2, zr2)))
        self._build_eave_details([(yB, zb), (yF, zb)], axis='X')

    # ────────────────────────────────────────────────────────
    #  7. VAULT — Bóveda de cañón
    # ────────────────────────────────────────────────────────
    def _build_vault(self):
        p  = self.props
        w  = p.width
        d  = p.depth
        zb = p.z_base
        ew = p.eave_width
        et = p.eave_thickness
        an = p.pitch
        n  = max(4, p.vault_segments)

        rise = math.tan(an) * (d / 2)
        zr   = zb + rise

        x0, x1 = -ew, w + ew
        yB, yF = -ew, d + ew

        # Arco parabólico: n+1 puntos de yB a yF
        def arc(t):
            y = yB + (yF - yB) * t
            f = 1 - (2 * t - 1) ** 2
            return y, zb + (zr - zb) * f

        th = Vector((0, 0, -et))
        prev = None
        for i in range(n + 1):
            y, z = arc(i / n)
            cur = (Vector((x0, y, z)), Vector((x1, y, z)))
            if prev is not None:
                self._panel([prev[0], prev[1], cur[1], cur[0]],
                            th, p.mat_roof)
            prev = cur

        # Tímpanos (arco aproximado con fan de n segmentos)
        for xx in (0, w):
            c = Vector((xx, d / 2, zb))
            pts = []
            for i in range(n + 1):
                t = i / n
                y = (d + ew * 2) * t - ew
                f = 1 - (2 * t - 1) ** 2
                pts.append(Vector((xx, y, zb + (zr - zb) * f)))
            for i in range(len(pts) - 1):
                if xx == 0:
                    self._face([c, pts[i + 1], pts[i]],
                               p.mat_roof)
                else:
                    self._face([c, pts[i], pts[i + 1]],
                               p.mat_roof)

        self._build_eave_details([(yB, zb), (yF, zb)], axis='X')

    # ═══════════════════════════════════════════════════════
    #  GENERATE
    # ═══════════════════════════════════════════════════════
    def generate(self, create_mats=True):
        """Punto de entrada principal. Devuelve (mesh, ok)."""
        p  = self.props
        bm = self.bm

        builders = {
            'GABLE':     self._build_gable,
            'SHED':      self._build_shed,
            'HIP':       self._build_hip,
            'SALTBOX':   self._build_saltbox,
            'BUTTERFLY': self._build_butterfly,
            'MANSARD':   self._build_mansard,
            'VAULT':     self._build_vault,
        }
        fn = builders.get(p.roof_type, self._build_gable)
        fn()

        bm.faces.ensure_lookup_table()

        mesh = bpy.data.meshes.new(p.object_name or "AF_Roof")
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()

        if create_mats:
            self.ensure_materials(mesh)

        return mesh, True

    # ────────────────────────────────────────────────────────
    #  MATERIALES
    # ────────────────────────────────────────────────────────
    def ensure_materials(self, mesh):
        """Crea/asigna 6 slots: roof, tile, fascia, soffit,
        ridge, skylight."""
        p = self.props
        mat_names = [
            ("AF_Roof",      (0.35, 0.12, 0.08, 1.0), 0.8),
            ("AF_Roof_Tile", (0.45, 0.15, 0.10, 1.0), 0.75),
            ("AF_Fascia",    (0.90, 0.90, 0.90, 1.0), 0.6),
            ("AF_Soffit",    (0.95, 0.95, 0.95, 1.0), 0.7),
            ("AF_Ridge",     (0.30, 0.10, 0.08, 1.0), 0.8),
            ("AF_Skylight",  (0.60, 0.80, 0.90, 1.0), 0.1),
        ]
        tile_colors = {
            'ZINC':    (0.62, 0.64, 0.66, 1.0),
            'ETERNIT': (0.55, 0.55, 0.57, 1.0),
            'THERMO':  (0.85, 0.87, 0.88, 1.0),
            'METAL':   (0.25, 0.30, 0.35, 1.0),
            'ROMAN':   (0.50, 0.16, 0.10, 1.0),
            'ESPANOLA':(0.55, 0.20, 0.12, 1.0),
            'SHINGLE': (0.20, 0.18, 0.16, 1.0),
        }
        if p.tile_type in tile_colors:
            name, _, rough = mat_names[1]
            mat_names[1] = (name, tile_colors[p.tile_type], rough)

        while len(mesh.materials) < len(mat_names):
            mesh.materials.append(None)

        for i, (name, color, rough) in enumerate(mat_names):
            mat = bpy.data.materials.get(name)
            if mat is None:
                mat = bpy.data.materials.new(name=name)
                mat.use_nodes = True
                bsdf = None
                for node in mat.node_tree.nodes:
                    if node.type == 'BSDF_PRINCIPLED':
                        bsdf = node
                        break
                if bsdf is not None:
                    bsdf.inputs['Base Color'].default_value = color
                    bsdf.inputs['Roughness'].default_value = rough
            mesh.materials[i] = mat

        p.mat_roof     = 0
        p.mat_tile     = 1
        p.mat_fascia   = 2
        p.mat_soffit   = 3
        p.mat_ridge    = 4
        p.mat_skylight = 5


# ════════════════════════════════════════════════════════════
#  FUNCIÓN UPDATE
# ════════════════════════════════════════════════════════════
def af_roof_update(self, context):
    """Regenera el techo cuando cambia una propiedad."""
    obj = None
    if isinstance(self, bpy.types.Object):
        obj = self
    else:
        for o in bpy.data.objects:
            if getattr(o, "af_roof", None) == self:
                obj = o
                break

    if obj is None or obj.type != 'MESH':
        return

    props = obj.af_roof

    try:
        generator = AF_RoofGenerator(props)
        mesh, ok = generator.generate(create_mats=True)

        if ok and mesh is not None:
            old_mesh = obj.data
            old_name = old_mesh.name if old_mesh else "AF_Roof"
            obj.data = mesh
            mesh.name = old_name
            if old_mesh and old_mesh.users == 0:
                bpy.data.meshes.remove(old_mesh)
    except Exception as e:
        print(f"[AF Roof] Error regenerando: {e}")


def af_roof_sync_props_from_object(obj):
    """Sincroniza propiedades RNA desde custom properties."""
    if obj is None:
        return
    props = getattr(obj, "af_roof", None)
    if props is None:
        return
    for key in list(obj.keys()):
        if key.startswith("_"):
            continue
        try:
            if hasattr(props, key):
                setattr(props, key, obj[key])
        except Exception:
            pass


def af_roof_tile_update(self, context):
    """Presets por tipo de teja + regenera."""
    tile_presets = {
        'ZINC':     dict(tile_length=1.83, tile_width=0.08,
                         tile_thickness=0.002),
        'ETERNIT':  dict(tile_length=1.83, tile_width=0.15,
                         tile_thickness=0.006),
        'THERMO':   dict(tile_length=2.44, tile_width=1.00,
                         tile_thickness=0.05),
        'METAL':    dict(tile_length=2.44, tile_width=1.00,
                         tile_thickness=0.004),
        'ESPANOLA': dict(tile_length=0.40, tile_width=0.20,
                         tile_thickness=0.015),
        'ROMAN':    dict(tile_length=0.40, tile_width=0.09,
                         tile_thickness=0.015),
    }
    preset = tile_presets.get(getattr(self, "tile_type", "NONE"))
    if preset:
        for k, v in preset.items():
            try:
                setattr(self, k, v)
            except Exception:
                pass
    af_roof_update(self, context)


# ════════════════════════════════════════════════════════════
#  SETUP + CREATE
# ════════════════════════════════════════════════════════════
def af_roof_setup_object(obj, props=None):
    """Configura display + custom props espejo."""
    obj.display_type = 'TEXTURED'
    obj.show_all_edges = True

    if props is not None:
        for key in ('roof_type', 'width', 'depth', 'z_base',
                    'tile_type'):
            try:
                obj[key] = getattr(props, key)
            except Exception:
                pass


def af_roof_create(context, props_dict=None, name="AF_Roof",
                   link=True):
    """Crea un objeto techo paramétrico."""
    mesh = bpy.data.meshes.new(name)
    obj  = bpy.data.objects.new(name, mesh)

    if link and context.collection:
        context.collection.objects.link(obj)

    props = getattr(obj, "af_roof", None)
    if props is not None and props_dict:
        for k, v in props_dict.items():
            try:
                if hasattr(props, k):
                    setattr(props, k, v)
            except Exception:
                pass

    if props is not None:
        props.object_name = obj.name
        af_roof_setup_object(obj, props)
        af_roof_update(obj, context)

    return obj


# ════════════════════════════════════════════════════════════
#  OPERADORES
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_OT_roof_add(Operator):
    """Add ArchiForge parametric roof"""
    bl_idname = "archiforge.roof_add"
    bl_label = "Add Roof"
    bl_options = {'REGISTER', 'UNDO'}

    roof_type: EnumProperty(
        name="Roof Type", items=AF_ROOF_TYPES, default='GABLE',
    )

    def execute(self, context):
        obj = af_roof_create(
            context,
            props_dict={'roof_type': self.roof_type},
            name=f"AF_Roof_{self.roof_type.title()}",
        )
        if obj is not None:
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            context.view_layer.objects.active = obj
        return {'FINISHED'}


class ARCHIFORGE_OT_roof_place(Operator):
    """Click to place roof, ESC to cancel"""
    bl_idname = "archiforge.roof_place"
    bl_label = "Place Roof"

    roof_type: EnumProperty(
        name="Roof Type", items=AF_ROOF_TYPES, default='GABLE',
    )

    def modal(self, context, event):
        if event.type in {'RIGHTMOUSE', 'ESC'}:
            if self._obj is not None:
                bpy.data.objects.remove(self._obj, do_unlink=True)
            return {'CANCELLED'}
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            return {'FINISHED'}
        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        self._obj = af_roof_create(
            context,
            props_dict={'roof_type': self.roof_type},
            name=f"AF_Roof_{self.roof_type.title()}",
        )
        if self._obj is None:
            return {'CANCELLED'}
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


class ARCHIFORGE_OT_roof_edit(Operator):
    """Edit selected roof (regenerate)"""
    bl_idname = "archiforge.roof_edit"
    bl_label = "Edit Roof"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj is not None
                and getattr(obj, "af_roof", None) is not None
                and obj.af_roof.is_af_roof)

    def execute(self, context):
        obj = context.active_object
        af_roof_sync_props_from_object(obj)
        af_roof_update(obj, context)
        return {'FINISHED'}


class ARCHIFORGE_OT_roof_tile_preset(Operator):
    """Apply tile preset"""
    bl_idname = "archiforge.roof_tile_preset"
    bl_label = "Tile Preset"
    bl_options = {'REGISTER', 'UNDO'}

    tile_type: EnumProperty(
        name="Tile Type", items=AF_TILE_TYPES, default='ZINC',
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj is not None
                and getattr(obj, "af_roof", None) is not None)

    def execute(self, context):
        obj = context.active_object
        obj.af_roof.tile_type = self.tile_type
        af_roof_tile_update(obj.af_roof, context)
        return {'FINISHED'}


# ════════════════════════════════════════════════════════════
#  PANEL
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_PT_roof(Panel):
    bl_label = "ArchiForge Roof"
    bl_idname = "ARCHIFORGE_PT_roof"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ArchiForge"
    bl_context = "objectmode"

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj is not None
                and getattr(obj, "af_roof", None) is not None
                and obj.af_roof.is_af_roof)

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        p = obj.af_roof

        box = layout.box()
        box.label(text="Roof Type", icon='HOME')
        box.prop(p, "roof_type", text="")
        row = box.row(align=True)
        row.operator("archiforge.roof_edit", text="Regenerate",
                     icon='FILE_REFRESH')

        box = layout.box()
        box.label(text="Dimensions", icon='ARROW_LEFTRIGHT')
        box.prop(p, "width")
        box.prop(p, "depth")
        box.prop(p, "z_base")

        box = layout.box()
        box.label(text="Slope", icon='TRIA_UP')
        box.prop(p, "pitch")
        if p.roof_type in {'SALTBOX', 'BUTTERFLY'}:
            box.prop(p, "pitch_back")
        if p.roof_type == 'MANSARD':
            box.prop(p, "mansard_break")
            box.prop(p, "mansard_pitch_lower")
        if p.roof_type == 'VAULT':
            box.prop(p, "vault_segments")

        box = layout.box()
        box.label(text="Eave", icon='MOD_FLUID')
        box.prop(p, "eave_width")
        box.prop(p, "eave_thickness")
        box.prop(p, "fascia_enable")
        if p.fascia_enable:
            box.prop(p, "fascia_width")
            box.prop(p, "fascia_depth")
        box.prop(p, "soffit_enable")
        if p.soffit_enable:
            box.prop(p, "soffit_thickness")

        box = layout.box()
        box.label(text="Ridge", icon='ALIGN_TOP')
        box.prop(p, "ridge_enable")
        if p.ridge_enable:
            box.prop(p, "ridge_width")
            box.prop(p, "ridge_height")

        box = layout.box()
        box.label(text="Tiles / Cover", icon='GRID')
        box.prop(p, "tile_type", text="")
        if p.tile_type != 'NONE':
            if p.tile_type in {'ZINC', 'ETERNIT', 'THERMO',
                               'METAL'}:
                box.prop(p, "tile_length", text="Sheet Length")
                box.prop(p, "tile_width", text="Pitch / Width")
            else:
                box.prop(p, "tile_length")
                box.prop(p, "tile_width")
            box.prop(p, "tile_thickness")
            if p.tile_type in {'FLAT_TILE', 'SHINGLE'}:
                box.prop(p, "tile_overlap")

        box = layout.box()
        box.label(text="Skylight", icon='LIGHT_HEMI')
        box.prop(p, "skylight_enable")
        if p.skylight_enable:
            box.prop(p, "skylight_width")
            box.prop(p, "skylight_height")
            box.prop(p, "skylight_pos_x")
            box.prop(p, "skylight_pos_y")

        box = layout.box()
        box.label(text="Materials", icon='MATERIAL')
        box.prop(p, "mat_roof", text="Roof")
        box.prop(p, "mat_tile", text="Tile")
        box.prop(p, "mat_fascia", text="Fascia")
        box.prop(p, "mat_soffit", text="Soffit")
        box.prop(p, "mat_ridge", text="Ridge")
        box.prop(p, "mat_skylight", text="Skylight")


# ════════════════════════════════════════════════════════════
#  REGISTRO
# ════════════════════════════════════════════════════════════
classes = (
    AF_RoofProperties,
    ARCHIFORGE_OT_roof_add,
    ARCHIFORGE_OT_roof_place,
    ARCHIFORGE_OT_roof_edit,
    ARCHIFORGE_OT_roof_tile_preset,
    ARCHIFORGE_PT_roof,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Object.af_roof = PointerProperty(type=AF_RoofProperties)


def unregister():
    try:
        del bpy.types.Object.af_roof
    except Exception:
        pass
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
