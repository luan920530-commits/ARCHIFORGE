# -*- coding: utf-8 -*-

# ╔══════════════════════════════════════════════════════════╗
# ║         ARCHIFORGE — af_roof.py                         ║
# ║         Techos Paramétricos para Blender 3.3 LTS        ║
# ║         GPL v3 — ArchiForge Devs                        ║
# ╚══════════════════════════════════════════════════════════╝

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
#  - Capa de tejas / cubierta
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
    ('ROMAN',    "Roman",    "Roman / curved tile"),
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
        update=lambda s, c: af_roof_update(s, c),
    )
    tile_length : FloatProperty(
        name="Tile Length",
        default=0.40, min=0.05, max=2.0, unit='LENGTH',
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
        self._mat  = self.bm.faces.layers.int.new("material_index")

    # ────────────────────────────────────────────────────────
    #  UTILIDAD — Prisma rectangular
    # ────────────────────────────────────────────────────────
    def _box(self, x0, x1, y0, y1, z0, z1, mi=0):
        bm  = self.bm
        mat = self._mat

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
            f[mat] = mi

    # ────────────────────────────────────────────────────────
    #  UTILIDAD — Cara plana desde lista de Vector3
    # ────────────────────────────────────────────────────────
    def _face(self, pts3d, mi=0):
        """Crea una cara n-gon desde lista de Vector((x,y,z))."""
        bm  = self.bm
        mat = self._mat
        if len(pts3d) < 3:
            return
        verts = [bm.verts.new(p) for p in pts3d]
        bm.verts.ensure_lookup_table()
        try:
            f = bm.faces.new(verts)
            f[mat] = mi
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
        mat = self._mat
        n   = len(pts3d)
        if n < 3:
            return

        vf = [bm.verts.new(p) for p in pts3d]
        vb = [bm.verts.new(p + thickness_vec) for p in pts3d]
        bm.verts.ensure_lookup_table()

        # Cara frontal
        try:
            f = bm.faces.new(vf)
            f[mat] = mi
        except Exception:
            pass
        # Cara trasera
        try:
            f = bm.faces.new(list(reversed(vb)))
            f[mat] = mi
        except Exception:
            pass
        # Laterales
        for i in range(n):
            j = (i+1) % n
            try:
                f = bm.faces.new([vf[i], vf[j], vb[j], vb[i]])
                f[mat] = mi
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

    # ────────────────────────────────────────────────────────
    #  TEJAS
    # ────────────────────────────────────────────────────────
    def _build_tiles_on_slope(
        self, slope_pts, length,
        slope_height, slope_run,
        start_x, tile_type, mi
    ):
        """
        Genera tejas sobre una superficie inclinada.
        slope_pts: [p0, p1, p2, p3] cuatro esquinas del plano inclinado
        """
        p = self.props
        if tile_type == 'NONE':
            return

        tl  = p.tile_length   * (1.0 - p.tile_overlap)
        tw  = p.tile_width
        tt  = p.tile_thickness
        bm  = self.bm
        mat = self._mat

        # Número de filas y columnas
        slope_length = math.sqrt(slope_height**2 + slope_run**2)
        n_rows = max(1, int(slope_length / tl))
        n_cols = max(1, int(length / tw))

        row_step = slope_length / n_rows
        col_step = length / n_cols

        # Ángulo del plano inclinado
        angle = math.atan2(slope_height, slope_run)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)

        for row in range(n_rows):
            for col in range(n_cols):
                # Posición local en el plano de la pendiente
                s  = row * row_step      # a lo largo de la pendiente
                cx = start_x + col * col_step + col_step * 0.5

                # Proyectar s sobre el plano inclinado
                sy = s * cos_a
                sz = s * sin_a + p.z_base

                if tile_type == 'FLAT_TILE':
                    # Teja plana: rectángulo sobre el plano inclinado
                    self._box(
                        cx - tw * 0.4, cx + tw * 0.4,
                        sy, sy + tl * cos_a,
                        sz, sz + tt + tl * sin_a,
                        mi
                    )

                elif tile_type == 'SHINGLE':
                    # Tablilla: aún más fina y uniforme
                    self._box(
                        cx - tw * 0.45, cx + tw * 0.45,
                        sy, sy + tl * cos_a * 0.8,
                        sz, sz + tt,
                        mi
                    )

                elif tile_type == 'METAL':
                    # Chapa: nervio longitudinal
                    self._box(
                        cx - 0.005, cx + 0.005,
                        sy, sy + tl * cos_a,
                        sz, sz + tt * 3,
                        mi
                    )

    # ────────────────────────────────────────────────────────
    #  LUCERNARIO
    # ────────────────────────────────────────────────────────
    def _build_skylight(self, slope_angle, slope_start_y, slope_start_z):
        """
        Genera un lucernario (velux) sobre la pendiente del techo.
        Posición relativa al plano de la pendiente principal.
        """
        p   = self.props
        if not p.skylight_enable:
            return

        sw  = p.skylight_width
        sh  = p.skylight_height
        cx  = p.width * p.skylight_pos_x
        pos = p.skylight_pos_y

        # Proyectar posición sobre el plano inclinado
        slope_run = p.depth * 0.5
        cos_a = math.cos(slope_angle)
        sin_a = math.sin(slope_angle)

        s   = pos * slope_run
        py  = slope_start_y + s * cos_a
        pz  = slope_start_z + s * sin_a

        # Frame del lucernario (inclinado)
        frame_w = 0.06
        gt      = 0.006

        # Marco
        self._box(
            cx - sw*0.5 - frame_w, cx + sw*0.5 + frame_w,
            py - frame_w, py + sh * cos_a + frame_w,
            pz - frame_w, pz + sh * sin_a + frame_w,
            p.mat_fascia
        )

        # Vidrio
        self._box(
            cx - sw*0.5, cx + sw*0.5,
            py, py + sh * cos_a,
            pz, pz + sh * sin_a,
            p.mat_skylight
        )

    # ────────────────────────────────────────────────────────
    #  TIPO: FLAT — Azotea plana
    # ────────────────────────────────────────────────────────
    def _build_flat(self):
        p  = self.props
        w  = p.width
        d  = p.depth
        z  = p.z_base
        et = p.eave_thickness
        ew = p.eave_width
        mi = p.mat_roof

        # Losa plana
        self._box(
            -ew, w + ew,
            -ew, d + ew,
            z - et, z,
            mi
        )

        # Pretil / parapet (borde elevado)
        parapet_h = 0.30
        parapet_t = 0.15
        for x0, x1, y0, y1 in [
            (-ew, w + ew, -ew, -ew + parapet_t),           # Front
            (-ew, w + ew, d + ew - parapet_t, d + ew),     # Back
            (-ew, -ew + parapet_t, -ew, d + ew),            # Left
            (w + ew - parapet_t, w + ew, -ew, d + ew),      # Right
        ]:
            self._box(x0, x1, y0, y1, z, z + parapet_h, p.mat_fascia)

    # ────────────────────────────────────────────────────────
    #  TIPO: GABLE — Dos aguas
    # ────────────────────────────────────────────────────────
    def _build_gable(self):
        p   = self.props
        w   = p.width
        d   = p.depth
        z   = p.z_base
        et  = p.eave_thickness
        ew  = p.eave_width
        pitch = p.pitch
        mi  = p.mat_roof
        bm  = self.bm
        mat = self._mat

        # — Altura de la cumbrera —
        ridge_h = math.tan(pitch) * (d * 0.5)
        z_ridge = z + ridge_h

        # — Pendiente frontal (+Y → Z) —
        # Plano inclinado frontal con espesor
        def slope_front():
            # 6 puntos: 4 de la cara exterior + 2 de la cumbrera
            pts_outer = [
                Vector((-ew, -ew, z)),
                Vector((w+ew, -ew, z)),
                Vector((w+ew, d*0.5, z_ridge)),
                Vector((-ew,  d*0.5, z_ridge)),
            ]
            # Desplazar hacia interior por espesor
            off = Vector((0, et * math.sin(pitch), -et * math.cos(pitch)))
            pts_inner = [v + off for v in pts_outer]
            # Caras
            self._face(pts_outer, mi)
            self._face(list(reversed(pts_inner)), mi)
            for i in range(len(pts_outer)):
                j = (i+1) % len(pts_outer)
                try:
                    f = bm.faces.new([
                        bm.verts.new(pts_inner[i]),
                        bm.verts.new(pts_inner[j]),
                        bm.verts.new(pts_outer[j]),
                        bm.verts.new(pts_outer[i]),
                    ])
                    f[mat] = mi
                except Exception:
                    pass

        # Pendiente delantera
        pts_f = [
            Vector((-ew, -ew, z)),
            Vector((w+ew, -ew, z)),
            Vector((w+ew, d*0.5, z_ridge)),
            Vector((-ew,  d*0.5, z_ridge)),
        ]
        nf = Vector((0.0, math.cos(pitch), math.sin(pitch))).normalized()
        off_f = -nf * et

        self._panel(pts_f, off_f, mi)

        # Pendiente trasera
        pts_b = [
            Vector((w+ew, d+ew, z)),
            Vector((-ew, d+ew, z)),
            Vector((-ew, d*0.5, z_ridge)),
            Vector((w+ew, d*0.5, z_ridge)),
        ]
        nb = Vector((0.0, -math.cos(pitch), math.sin(pitch))).normalized()
        off_b = -nb * et
        self._panel(pts_b, off_b, mi)

        # — Hastiales (Gable ends) —
        # Frontal (y=-ew → -ew+fascia)
        self._face([
            Vector((-ew, -ew, z)),
            Vector((w+ew, -ew, z)),
            Vector((w*0.5, -ew, z_ridge)),  # corregido: punta en centro
        ], mi)
        # Trasera
        self._face([
            Vector((w+ew, d+ew, z)),
            Vector((-ew, d+ew, z)),
            Vector((w*0.5, d+ew, z_ridge)),
        ], mi)

        # — Cumbrera (ridge cap) —
        if p.ridge_enable:
            rw = p.ridge_width * 0.5
            rh = p.ridge_height
            self._box(
                -rw, w + rw,
                d*0.5 - rw, d*0.5 + rw,
                z_ridge, z_ridge + rh,
                p.mat_ridge
            )

        # — Tejas —
        if p.tile_type != 'NONE':
            # Pendiente delantera
            self._build_tiles_on_slope(
                pts_f, w + ew*2, ridge_h, d*0.5,
                -ew, p.tile_type, p.mat_tile
            )
            # Pendiente trasera
            self._build_tiles_on_slope(
                pts_b, w + ew*2, ridge_h, d*0.5,
                -ew, p.tile_type, p.mat_tile
            )

        # — Fascia / soffit —
        self._build_eave_details(
            [(-ew, z), (d+ew, z)], axis='X'
        )

        # — Lucernario —
        if p.skylight_enable:
            self._build_skylight(pitch, -ew, z)

    # ────────────────────────────────────────────────────────
    #  TIPO: HIP — Cuatro aguas
    # ────────────────────────────────────────────────────────
    def _build_hip(self):
        p   = self.props
        w   = p.width
        d   = p.depth
        z   = p.z_base
        et  = p.eave_thickness
        ew  = p.eave_width
        pitch = p.pitch
        mi  = p.mat_roof
        bm  = self.bm
        mat = self._mat

        # Altura de la cumbrera (basada en la dimensión menor)
        half_min = min(w, d) * 0.5
        ridge_h  = math.tan(pitch) * half_min
        z_ridge  = z + ridge_h

        # Longitud de la cumbrera (si w > d, hay cumbrera horizontal)
        if w >= d:
            ridge_len = (w - d) * 0.5
            # Cumbrera central horizontal en X
            ridge_x0 = ridge_len
            ridge_x1 = w - ridge_len
        else:
            ridge_len = 0.0
            ridge_x0  = w * 0.5
            ridge_x1  = w * 0.5

        # — Pendiente frontal (triángulo o trapecio) —
        if ridge_len > 0.001:
            pts_f = [
                Vector((-ew, -ew, z)),
                Vector((w+ew, -ew, z)),
                Vector((ridge_x1, d*0.5, z_ridge)),
                Vector((ridge_x0, d*0.5, z_ridge)),
            ]
        else:
            pts_f = [
                Vector((-ew, -ew, z)),
                Vector((w+ew, -ew, z)),
                Vector((w*0.5, d*0.5, z_ridge)),
            ]
        nf = Vector((0.0, math.cos(pitch), math.sin(pitch))).normalized()
        self._panel(pts_f, -nf*et, mi)

        # — Pendiente trasera —
        if ridge_len > 0.001:
            pts_b = [
                Vector((w+ew, d+ew, z)),
                Vector((-ew, d+ew, z)),
                Vector((ridge_x0, d*0.5, z_ridge)),
                Vector((ridge_x1, d*0.5, z_ridge)),
            ]
        else:
            pts_b = [
                Vector((w+ew, d+ew, z)),
                Vector((-ew, d+ew, z)),
                Vector((w*0.5, d*0.5, z_ridge)),
            ]
        nb = Vector((0.0, -math.cos(pitch), math.sin(pitch))).normalized()
        self._panel(pts_b, -nb*et, mi)

        # — Pendiente lateral izquierda —
        pts_l = [
            Vector((-ew, -ew, z)),
            Vector((-ew, d+ew, z)),
            Vector((ridge_x0, d*0.5, z_ridge)),
        ]
        if ridge_len < 0.001:
            nl = Vector((-math.cos(pitch), 0, math.sin(pitch))).normalized()
            self._panel(pts_l, nl*et, mi)
        else:
            pts_l = [
                Vector((-ew, -ew, z)),
                Vector((-ew, d+ew, z)),
                Vector((ridge_x0, d*0.5, z_ridge)),
            ]
            nl = Vector((-math.cos(pitch), 0, math.sin(pitch))).normalized()
            self._panel(pts_l, nl*et, mi)

        # — Pendiente lateral derecha —
        pts_r = [
            Vector((w+ew, d+ew, z)),
            Vector((w+ew, -ew, z)),
            Vector((ridge_x1, d*0.5, z_ridge)),
        ]
        nr = Vector((math.cos(pitch), 0, math.sin(pitch))).normalized()
        self._panel(pts_r, -nr*et, mi)

        # — Cumbrera —
        if p.ridge_enable and ridge_len > 0.001:
            rw = p.ridge_width * 0.5
            rh = p.ridge_height
            self._box(
                ridge_x0 - rw, ridge_x1 + rw,
                d*0.5 - rw, d*0.5 + rw,
                z_ridge, z_ridge + rh,
                p.mat_ridge
            )

        # — Tejas —
        if p.tile_type != 'NONE':
            self._build_tiles_on_slope(
                pts_f, w+ew*2, ridge_h, half_min,
                -ew, p.tile_type, p.mat_tile
            )

        # — Fascia —
        self._build_eave_details(
            [(-ew, z), (d+ew, z)], axis='X'
        )

        # — Lucernario —
        if p.skylight_enable:
            self._build_skylight(pitch, -ew, z)

    # ────────────────────────────────────────────────────────
    #  TIPO: SHED — Un agua
    # ────────────────────────────────────────────────────────
    def _build_shed(self):
        p     = self.props
        w     = p.width
        d     = p.depth
        z     = p.z_base
        et    = p.eave_thickness
        ew    = p.eave_width
        pitch = p.pitch
        mi    = p.mat_roof

        # Altura en la parte alta (lado Y=d)
        ridge_h = math.tan(pitch) * d
        z_high  = z + ridge_h

        # Pendiente única (de Y=0 a Y=d)
        pts = [
            Vector((-ew,   -ew, z)),
            Vector((w+ew,  -ew, z)),
            Vector((w+ew, d+ew, z_high)),
            Vector((-ew,  d+ew, z_high)),
        ]
        n   = Vector((0.0, -math.cos(pitch), math.sin(pitch))).normalized()
        self._panel(pts, n * et, mi)

        # Hastiales triangulares
        self._face([
            Vector((-ew, -ew, z)),
            Vector((-ew, d+ew, z_high)),
            Vector((-ew, -ew, z_high)),
        ], mi)
        self._face([
            Vector((w+ew, -ew, z)),
            Vector((w+ew, -ew, z_high)),
            Vector((w+ew, d+ew, z_high)),
        ], mi)

        # Fascia / soffit
        self._build_eave_details([(-ew, z), (d+ew, z_high)], axis='X')

        # Tejas
        if p.tile_type != 'NONE':
            self._build_tiles_on_slope(
                pts, w+ew*2, ridge_h, d,
                -ew, p.tile_type, p.mat_tile
            )

        # Lucernario
        if p.skylight_enable:
            self._build_skylight(pitch, -ew, z)

    # ────────────────────────────────────────────────────────
    #  TIPO: MANSARD — Doble pendiente (mansarda)
    # ────────────────────────────────────────────────────────
    def _build_mansard(self):
        p   = self.props
        w   = p.width
        d   = p.depth
        z   = p.z_base
        et  = p.eave_thickness
        ew  = p.eave_width
        bh  = p.mansard_break   # altura del quiebre
        pl  = p.mansard_pitch_lower
        pu  = p.pitch
        mi  = p.mat_roof

        # — Calcular quiebre —
        run_lower = bh / math.tan(pl)   # retroceso horizontal de la pendiente baja
        z_break   = z + bh

        # Nivel del quiebre en planta
        x_break_l = run_lower
        x_break_r = w - run_lower
        y_break_f = run_lower
        y_break_b = d - run_lower

        # Altura superior
        upper_run = min(x_break_r - x_break_l, y_break_b - y_break_f) * 0.5
        z_ridge   = z_break + math.tan(pu) * upper_run

        # — Pendiente baja frontal (empinada) —
        pts_lf = [
            Vector((-ew,   -ew,   z)),
            Vector((w+ew,  -ew,   z)),
            Vector((x_break_r, y_break_f, z_break)),
            Vector((x_break_l, y_break_f, z_break)),
        ]
        nf_low = Vector((0.0, math.cos(pl), math.sin(pl))).normalized()
        self._panel(pts_lf, -nf_low * et, mi)

        # — Pendiente baja trasera —
        pts_lb = [
            Vector((w+ew, d+ew, z)),
            Vector((-ew,  d+ew, z)),
            Vector((x_break_l, y_break_b, z_break)),
            Vector((x_break_r, y_break_b, z_break)),
        ]
        nb_low = Vector((0.0, -math.cos(pl), math.sin(pl))).normalized()
        self._panel(pts_lb, -nb_low * et, mi)

        # — Pendiente baja lateral izquierda —
        pts_ll = [
            Vector((-ew, -ew, z)),
            Vector((-ew, d+ew, z)),
            Vector((x_break_l, y_break_b, z_break)),
            Vector((x_break_l, y_break_f, z_break)),
        ]
        nl_low = Vector((-math.cos(pl), 0, math.sin(pl))).normalized()
        self._panel(pts_ll, nl_low * et, mi)

        # — Pendiente baja lateral derecha —
        pts_lr = [
            Vector((w+ew, d+ew, z)),
            Vector((w+ew, -ew, z)),
            Vector((x_break_r, y_break_f, z_break)),
            Vector((x_break_r, y_break_b, z_break)),
        ]
        nr_low = Vector((math.cos(pl), 0, math.sin(pl))).normalized()
        self._panel(pts_lr, -nr_low * et, mi)

        # — Parte superior: techo a cuatro aguas sobre la mansarda —
        # Llamar _build_hip con dimensiones reducidas
        # Guardar props temporales
        orig_w, orig_d, orig_z, orig_pitch = (
            p.width, p.depth, p.z_base, p.pitch
        )
        p.width  = x_break_r - x_break_l
        p.depth  = y_break_b - y_break_f
        p.z_base = z_break
        p.pitch  = pu

        # Ajustar origen para la parte superior
        # (usar transform después)
        sub_gen = AF_RoofGenerator(p)
        sub_gen._build_hip()
        sub_bm = sub_gen.bm

        # Trasladar la geometría superior al lugar correcto
        offset = Vector((x_break_l, y_break_f, 0.0))
        for v in sub_bm.verts:
            v.co += offset

        sub_bm.to_mesh(bpy.data.meshes.new("__tmp_mansard__"))
        # Fusionar con el bmesh principal
        bmesh.ops.duplicate(
            self.bm,
            geom = list(sub_bm.faces) + list(sub_bm.verts) + list(sub_bm.edges)
        )
        sub_bm.free()

        # Restaurar props
        p.width, p.depth, p.z_base, p.pitch = (
            orig_w, orig_d, orig_z, orig_pitch
        )

        # — Fascia baja —
        self._build_eave_details([(-ew, z), (d+ew, z)], axis='X')

        # — Cumbrera —
        if p.ridge_enable:
            cx0 = x_break_l + upper_run
            cx1 = x_break_r - upper_run
            if cx1 > cx0:
                rw = p.ridge_width * 0.5
                self._box(
                    cx0 - rw, cx1 + rw,
                    (y_break_f + y_break_b)*0.5 - rw,
                    (y_break_f + y_break_b)*0.5 + rw,
                    z_ridge, z_ridge + p.ridge_height,
                    p.mat_ridge
                )

    # ────────────────────────────────────────────────────────
    #  TIPO: BUTTERFLY — Mariposa (V)
    # ────────────────────────────────────────────────────────
    def _build_butterfly(self):
        p     = self.props
        w     = p.width
        d     = p.depth
        z     = p.z_base
        et    = p.eave_thickness
        ew    = p.eave_width
        pitch = p.pitch
        mi    = p.mat_roof

        # La cumbrera está en el centro pero más BAJA
        valley_drop = math.tan(pitch) * (d * 0.5)
        z_valley    = z - valley_drop
        z_high_f    = z
        z_high_b    = z

        # — Pendiente frontal (desciende hacia el centro) —
        pts_f = [
            Vector((-ew, -ew, z_high_f)),
            Vector((w+ew, -ew, z_high_f)),
            Vector((w+ew, d*0.5, z_valley)),
            Vector((-ew, d*0.5, z_valley)),
        ]
        nf = Vector((0.0, math.cos(pitch), -math.sin(pitch))).normalized()
        self._panel(pts_f, -nf * et, mi)

        # — Pendiente trasera —
        pts_b = [
            Vector((w+ew, d+ew, z_high_b)),
            Vector((-ew, d+ew, z_high_b)),
            Vector((-ew, d*0.5, z_valley)),
            Vector((w+ew, d*0.5, z_valley)),
        ]
        nb = Vector((0.0, -math.cos(pitch), -math.sin(pitch))).normalized()
        self._panel(pts_b, -nb * et, mi)

        # Hastiales
        self._face([
            Vector((-ew, -ew, z_high_f)),
            Vector((-ew, d*0.5, z_valley)),
            Vector((-ew, d+ew, z_high_b)),
        ], mi)
        self._face([
            Vector((w+ew, d+ew, z_high_b)),
            Vector((w+ew, d*0.5, z_valley)),
            Vector((w+ew, -ew, z_high_f)),
        ], mi)

        # Fascia (en los bordes altos)
        self._build_eave_details([(-ew, z_high_f), (d+ew, z_high_b)], 'X')

        # Canalón en el valle (canal)
        canal_w = 0.15
        canal_h = 0.08
        self._box(
            -ew, w+ew,
            d*0.5 - canal_w*0.5, d*0.5 + canal_w*0.5,
            z_valley - canal_h, z_valley,
            p.mat_fascia
        )

    # ────────────────────────────────────────────────────────
    #  TIPO: SALTBOX — Asimétrico
    # ────────────────────────────────────────────────────────
    def _build_saltbox(self):
        p      = self.props
        w      = p.width
        d      = p.depth
        z      = p.z_base
        et     = p.eave_thickness
        ew     = p.eave_width
        pitch  = p.pitch
        pitchb = p.pitch_back
        mi     = p.mat_roof

        # La cumbrera está desplazada hacia el frente
        # Eje de la cumbrera en Y = d * 0.35 (aprox saltbox)
        ridge_y  = d * 0.35
        ridge_h  = math.tan(pitch) * ridge_y
        z_ridge  = z + ridge_h

        # Pendiente frontal (corta y empinada)
        pts_f = [
            Vector((-ew, -ew, z)),
            Vector((w+ew, -ew, z)),
            Vector((w+ew, ridge_y, z_ridge)),
            Vector((-ew, ridge_y, z_ridge)),
        ]
        nf = Vector((0.0, math.cos(pitch), math.sin(pitch))).normalized()
        self._panel(pts_f, -nf * et, mi)

        # Pendiente trasera (larga y suave)
        pts_b = [
            Vector((w+ew, d+ew, z)),
            Vector((-ew, d+ew, z)),
            Vector((-ew, ridge_y, z_ridge)),
            Vector((w+ew, ridge_y, z_ridge)),
        ]
        nb = Vector((0.0, -math.cos(pitchb), math.sin(pitchb))).normalized()
        self._panel(pts_b, -nb * et, mi)

        # Hastiales asimétricos
        self._face([
            Vector((-ew, -ew, z)),
            Vector((-ew, ridge_y, z_ridge)),
            Vector((-ew, d+ew, z)),
        ], mi)
        self._face([
            Vector((w+ew, d+ew, z)),
            Vector((w+ew, ridge_y, z_ridge)),
            Vector((w+ew, -ew, z)),
        ], mi)

        # Cumbrera
        if p.ridge_enable:
            rw = p.ridge_width * 0.5
            rh = p.ridge_height
            self._box(
                -rw, w+rw,
                ridge_y - rw, ridge_y + rw,
                z_ridge, z_ridge + rh,
                p.mat_ridge
            )

        self._build_eave_details([(-ew, z), (d+ew, z)], 'X')

        if p.skylight_enable:
            self._build_skylight(pitch, -ew, z)

    # ────────────────────────────────────────────────────────
    #  TIPO: VAULT — Bóveda de cañón
    # ────────────────────────────────────────────────────────
    def _build_vault(self):
        p    = self.props
        w    = p.width
        d    = p.depth
        z    = p.z_base
        et   = p.eave_thickness
        ew   = p.eave_width
        segs = p.vault_segments
        mi   = p.mat_roof
        bm   = self.bm
        mat  = self._mat

        # Radio del arco = la mitad del ancho
        r        = w * 0.5
        cx       = w * 0.5   # centro del arco en X
        a_start  = 0.0
        a_end    = math.pi
        a_step   = (a_end - a_start) / segs

        for seg in range(segs):
            a0 = a_start + seg * a_step
            a1 = a_start + (seg+1) * a_step

            # Exterior del arco
            x0_out = cx + (r + et) * math.cos(a0)
            z0_out = z + (r + et) * math.sin(a0)
            x1_out = cx + (r + et) * math.cos(a1)
            z1_out = z + (r + et) * math.sin(a1)

            # Interior
            x0_in  = cx + r * math.cos(a0)
            z0_in  = z + r * math.sin(a0)
            x1_in  = cx + r * math.cos(a1)
            z1_in  = z + r * math.sin(a1)

            # — Franja de la bóveda (extruida en Y) —
            y0 = -ew
            y1 = d + ew

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

            for fi in [
                (0,1,5,4),(3,2,6,7),(0,3,7,4),
                (1,2,6,5),(0,1,2,3),(4,5,6,7)
            ]:
                f = bm.faces.new([verts[i] for i in fi])
                f[mat] = mi

        # — Testeros semicirculares —
        for y_pos in [-ew, d+ew]:
            prev_out = None
            prev_in  = None
            for seg in range(segs + 1):
                a   = a_start + seg * a_step
                xo  = cx + (r + et) * math.cos(a)
                zo  = z  + (r + et) * math.sin(a)
                xi  = cx + r * math.cos(a)
                zi  = z  + r * math.sin(a)
                curr_out = bm.verts.new(Vector((xo, y_pos, zo)))
                curr_in  = bm.verts.new(Vector((xi, y_pos, zi)))
                bm.verts.ensure_lookup_table()

                if prev_out and prev_in:
                    try:
                        f = bm.faces.new([
                            prev_in, prev_out,
                            curr_out, curr_in
                        ])
                        f[mat] = mi
                    except Exception:
                        pass
                prev_out = curr_out
                prev_in  = curr_in

        # — Tejas sobre la bóveda —
        if p.tile_type != 'NONE':
            half_circ = math.pi * r
            self._build_tiles_on_slope(
                [], w, r, r,
                0.0, p.tile_type, p.mat_tile
            )

    # ────────────────────────────────────────────────────────
    #  GENERATE
    # ────────────────────────────────────────────────────────
    def generate(self):
        p = self.props

        dispatch = {
            'FLAT'     : self._build_flat,
            'GABLE'    : self._build_gable,
            'HIP'      : self._build_hip,
            'SHED'     : self._build_shed,
            'MANSARD'  : self._build_mansard,
            'BUTTERFLY': self._build_butterfly,
            'SALTBOX'  : self._build_saltbox,
            'VAULT'    : self._build_vault,
        }

        builder = dispatch.get(p.roof_type)
        if builder:
            builder()

        try:
            bmesh.ops.recalc_face_normals(
                bm=self.bm, faces=self.bm.faces
            )
        except Exception:
            pass

        return self.bm


# ════════════════════════════════════════════════════════════
#  UPDATE / REBUILD
# ════════════════════════════════════════════════════════════
def _find_roof_object(props):
    name = props.object_name
    if name and name in bpy.data.objects:
        return bpy.data.objects[name]
    for obj in bpy.data.objects:
        if (obj.type == 'MESH'
                and hasattr(obj, AF_ROOF_PROP)
                and getattr(obj, AF_ROOF_PROP) is props):
            return obj
    return None


def af_roof_update(self, context):
    obj = _find_roof_object(self)
    if obj is None:
        obj = context.active_object
    if obj is None or obj.type != 'MESH':
        return
    props = getattr(obj, AF_ROOF_PROP, None)
    if props is None or not props.is_af_roof:
        return
    _rebuild_roof_mesh(obj, props)


def _rebuild_roof_mesh(obj, props):
    gen = AF_RoofGenerator(props)
    bm  = gen.generate()
    if bm is None:
        return
    me = obj.data
    bm.to_mesh(me)
    bm.free()
    me.update()

    for poly in me.polygons:
        poly.use_smooth = True

    if "material_index" in me.polygon_layers_int:
        layer = me.polygon_layers_int["material_index"]
        for poly in me.polygons:
            poly.material_index = layer.data[poly.index].value


def _setup_roof_materials(obj):
    mat_names = [
        "AF.Roof.Concrete",
        "AF.Roof.Tile",
        "AF.Door.Frame",
        "AF.Wall.Plaster",
        "AF.Roof.Metal",
        "AF.Window.Glass",
    ]
    af_material.ensure_af_materials_for_object(obj, mat_names)


def _create_roof_object(context, name="AF_Roof"):
    me  = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, me)
    context.collection.objects.link(obj)
    context.view_layer.objects.active = obj
    obj.select_set(True)

    props             = obj.archiforge_roof
    props.is_af_roof  = True
    props.object_name = obj.name
    _setup_roof_materials(obj)
    return obj, props


# ════════════════════════════════════════════════════════════
#  OPERADORES
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_OT_roof(Operator):
    bl_idname      = "archiforge.roof"
    bl_label       = "Add AF Roof"
    bl_description = "Add a parametric ArchiForge roof"
    bl_options     = {'REGISTER', 'UNDO'}

    roof_type : EnumProperty(
        name="Type", items=AF_ROOF_TYPES, default='GABLE',
    )
    width : FloatProperty(
        name="Width", default=8.0, min=0.5, unit='LENGTH',
    )
    depth : FloatProperty(
        name="Depth", default=6.0, min=0.5, unit='LENGTH',
    )
    z_base : FloatProperty(
        name="Base Height", default=3.0, min=0.0, unit='LENGTH',
    )
    pitch : FloatProperty(
        name="Pitch", default=math.radians(30),
        min=math.radians(1), max=math.radians(89), subtype='ANGLE',
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        col = layout.column(align=True)
        col.label(text="New Roof", icon='HOME')
        col.prop(self, "roof_type")
        col.separator()
        col.prop(self, "width")
        col.prop(self, "depth")
        col.prop(self, "z_base")
        col.prop(self, "pitch")

        # Info: altura de cumbrera
        ridge_h = math.tan(self.pitch) * (self.depth * 0.5)
        col.separator()
        col.label(
            text=f"Ridge Height: {ridge_h:.2f} m",
            icon='INFO'
        )

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        obj, props = _create_roof_object(context, "AF_Roof")
        props.roof_type = self.roof_type
        props.width     = self.width
        props.depth     = self.depth
        props.z_base    = self.z_base
        props.pitch     = self.pitch
        _rebuild_roof_mesh(obj, props)
        self.report({'INFO'}, f"Roof created: {obj.name}")
        return {'FINISHED'}


class ARCHIFORGE_OT_roof_update(Operator):
    bl_idname  = "archiforge.roof_update"
    bl_label   = "Update Roof"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj is not None and obj.type == 'MESH'
            and hasattr(obj, AF_ROOF_PROP)
            and obj.archiforge_roof.is_af_roof
        )

    def execute(self, context):
        obj = context.active_object
        _rebuild_roof_mesh(obj, obj.archiforge_roof)
        self.report({'INFO'}, "Roof updated")
        return {'FINISHED'}


class ARCHIFORGE_OT_roof_from_wall(Operator):
    """Crea el techo adaptando dimensiones desde el muro activo."""
    bl_idname  = "archiforge.roof_from_wall"
    bl_label   = "Roof from Wall"
    bl_options = {'REGISTER', 'UNDO'}

    roof_type : EnumProperty(
        name="Type", items=AF_ROOF_TYPES, default='GABLE',
    )
    pitch : FloatProperty(
        name="Pitch", default=math.radians(30),
        min=math.radians(1), max=math.radians(89), subtype='ANGLE',
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj is not None and obj.type == 'MESH'
            and hasattr(obj, "archiforge_wall")
            and obj.archiforge_wall.is_af_wall
        )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        col = self.layout.column(align=True)
        col.prop(self, "roof_type")
        col.prop(self, "pitch")

    def execute(self, context):
        wall  = context.active_object
        wprops = wall.archiforge_wall

        # Obtener dimensiones del muro
        pts = [wall.matrix_world @ Vector(c) for c in wall.bound_box]
        xs  = [p.x for p in pts]
        ys  = [p.y for p in pts]
        w   = max(xs) - min(xs)
        d   = max(ys) - min(ys)
        z   = wprops.height

        bpy.ops.object.select_all(action='DESELECT')
        obj, props = _create_roof_object(context, "AF_Roof")

        props.roof_type = self.roof_type
        props.width     = w
        props.depth     = d
        props.z_base    = z
        props.pitch     = self.pitch

        # Mover el techo a la posición del muro
        obj.location = Vector((min(xs), min(ys), 0.0))

        _rebuild_roof_mesh(obj, props)
        self.report({'INFO'}, f"Roof from wall '{wall.name}'")
        return {'FINISHED'}


# ════════════════════════════════════════════════════════════
#  PANEL
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_PT_roof(Panel):
    bl_label       = "Roof Properties"
    bl_idname      = "ARCHIFORGE_PT_roof"
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
            and hasattr(obj, AF_ROOF_PROP)
            and obj.archiforge_roof.is_af_roof
        )

    def draw_header(self, context):
        self.layout.label(text="", icon='HOME')

    def draw(self, context):
        props  = context.active_object.archiforge_roof
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        # ── Tipo ─────────────────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Type", icon='MODIFIER')
        col.prop(props, "roof_type", text="")

        # Info de altura
        ridge_h = math.tan(props.pitch) * (props.depth * 0.5)
        col.label(text=f"Ridge: {ridge_h:.2f} m", icon='INFO')

        # ── Dimensiones ───────────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Dimensions", icon='ARROW_LEFTRIGHT')
        col.prop(props, "width")
        col.prop(props, "depth")
        col.prop(props, "z_base")

        # ── Pendiente ─────────────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Pitch / Slope", icon='TRIA_UP')
        col.prop(props, "pitch")
        if props.roof_type in ('SALTBOX', 'BUTTERFLY'):
            col.prop(props, "pitch_back")
        if props.roof_type == 'MANSARD':
            col.prop(props, "mansard_break")
            col.prop(props, "mansard_pitch_lower")
        if props.roof_type == 'VAULT':
            col.prop(props, "vault_segments")

        # ── Alero ─────────────────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Eave", icon='MOD_THICKNESS')
        col.prop(props, "eave_width")
        col.prop(props, "eave_thickness")

        # ── Fascia ────────────────────────────────────────────
        box = layout.box()
        row = box.row(align=True)
        row.prop(
            props, "fascia_enable",
            text="Fascia Board",
            icon='TRIA_DOWN' if props.fascia_enable else 'TRIA_RIGHT',
            toggle=True, emboss=False,
        )
        if props.fascia_enable:
            col = box.column(align=True)
            col.prop(props, "fascia_width")
            col.prop(props, "fascia_depth")

        # ── Soffit ────────────────────────────────────────────
        box = layout.box()
        row = box.row(align=True)
        row.prop(
            props, "soffit_enable",
            text="Soffit",
            icon='TRIA_DOWN' if props.soffit_enable else 'TRIA_RIGHT',
            toggle=True, emboss=False,
        )
        if props.soffit_enable:
            box.prop(props, "soffit_thickness")

        # ── Cumbrera ──────────────────────────────────────────
        if props.roof_type not in ('FLAT', 'SHED',
                                   'BUTTERFLY', 'VAULT'):
            box = layout.box()
            row = box.row(align=True)
            row.prop(
                props, "ridge_enable",
                text="Ridge Cap",
                icon='TRIA_DOWN' if props.ridge_enable else 'TRIA_RIGHT',
                toggle=True, emboss=False,
            )
            if props.ridge_enable:
                col = box.column(align=True)
                col.prop(props, "ridge_width")
                col.prop(props, "ridge_height")

        # ── Tejas ─────────────────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Tiles / Cladding", icon='MATERIAL')
        col.prop(props, "tile_type", text="")
        if props.tile_type != 'NONE':
            col.prop(props, "tile_length")
            col.prop(props, "tile_width")
            col.prop(props, "tile_thickness")
            col.prop(props, "tile_overlap")

        # ── Lucernario ────────────────────────────────────────
        if props.roof_type not in ('FLAT', 'VAULT'):
            box = layout.box()
            row = box.row(align=True)
            row.prop(
                props, "skylight_enable",
                text="Skylight",
                icon='TRIA_DOWN' if props.skylight_enable else 'TRIA_RIGHT',
                toggle=True, emboss=False,
            )
            if props.skylight_enable:
                col = box.column(align=True)
                col.prop(props, "skylight_width")
                col.prop(props, "skylight_height")
                col.prop(props, "skylight_pos_x")
                col.prop(props, "skylight_pos_y")

        # ── Materiales ────────────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Materials", icon='MATERIAL')
        col.prop(props, "mat_roof",   text="Roof")
        if props.tile_type != 'NONE':
            col.prop(props, "mat_tile", text="Tiles")
        if props.fascia_enable:
            col.prop(props, "mat_fascia", text="Fascia")
        if props.soffit_enable:
            col.prop(props, "mat_soffit", text="Soffit")
        if props.ridge_enable:
            col.prop(props, "mat_ridge", text="Ridge")
        if props.skylight_enable:
            col.prop(props, "mat_skylight", text="Skylight")

        # ── Acciones ──────────────────────────────────────────
        layout.separator()
        row = layout.row(align=True)
        row.operator("archiforge.roof_update", icon='FILE_REFRESH')
        row.operator("archiforge.roof_from_wall", text="From Wall", icon='SNAP_FACE')


# ════════════════════════════════════════════════════════════
#  REGISTRO
# ════════════════════════════════════════════════════════════
classes = [
    AF_RoofProperties,
    ARCHIFORGE_OT_roof,
    ARCHIFORGE_OT_roof_update,
    ARCHIFORGE_OT_roof_from_wall,
    ARCHIFORGE_PT_roof,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Object.archiforge_roof = PointerProperty(
        type        = AF_RoofProperties,
        name        = "ArchiForge Roof",
        description = "ArchiForge parametric roof properties",
    )
    print("[ArchiForge] ✅ af_roof — registered")


def unregister():
    if hasattr(bpy.types.Object, "archiforge_roof"):
        del bpy.types.Object.archiforge_roof

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    print("[ArchiForge] 🔴 af_roof — unregistered")