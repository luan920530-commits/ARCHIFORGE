# -*- coding: utf-8 -*-

# ╔══════════════════════════════════════════════════════════╗
# ║         ARCHIFORGE — af_stair.py                        ║
# ║         Escaleras Paramétricas para Blender 3.3 LTS     ║
# ║         GPL v3 — ArchiForge Devs                        ║
# ╚══════════════════════════════════════════════════════════╝

# <pep8 compliant>

# ════════════════════════════════════════════════════════════
#  ¿QUÉ HACE ESTE MÓDULO?
#
#  Genera escaleras paramétricas completas con:
#  - Peldaños (steps): huella + contrahuella
#  - Zanca (stringer): lateral o central
#  - Barandilla + pasamanos (railing + handrail)
#  - Balaustres (balusters)
#  - Descanso intermedio (landing)
#
#  Tipos de escalera:
#  - STRAIGHT   : Recta simple
#  - L_SHAPE    : En L (un giro de 90°)
#  - U_SHAPE    : En U (doble giro de 90°)
#  - SPIRAL     : Caracol / helicoidal
#  - WINDER     : Con peldaños de abanico en el giro
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
AF_STAIR_PROP = "archiforge_stair"

# Tipos de escalera
AF_STAIR_TYPES = [
    ('STRAIGHT', "Straight",  "Simple straight staircase",        'FORWARD',       0),
    ('L_SHAPE',  "L-Shape",   "L-shaped staircase (one turn)",    'TRIA_RIGHT',    1),
    ('U_SHAPE',  "U-Shape",   "U-shaped staircase (two turns)",   'UV_SYNC_SELECT',2),
    ('SPIRAL',   "Spiral",    "Spiral/helical staircase",         'MESH_CIRCLE',   3),
    ('WINDER',   "Winder",    "Stair with winder steps at turn",  'DRIVER_ROTATIONAL_DIFFERENCE', 4),
]

# Tipos de zanca (stringer)
AF_STRINGER_TYPES = [
    ('CLOSED', "Closed", "Solid closed stringer on both sides"),
    ('OPEN',   "Open",   "Open cut stringer (sawtooth profile)"),
    ('CENTER', "Center", "Single central spine stringer"),
    ('NONE',   "None",   "No stringer"),
]

# Tipos de balaustre
AF_BALUSTER_TYPES = [
    ('SQUARE',  "Square",  "Square section balusters"),
    ('ROUND',   "Round",   "Round section balusters"),
    ('FLAT',    "Flat",    "Flat panel balusters"),
    ('NONE',    "None",    "No balusters"),
]

# Tipos de pasamanos
AF_HANDRAIL_TYPES = [
    ('ROUND',  "Round",  "Round handrail profile"),
    ('SQUARE', "Square", "Square handrail profile"),
    ('FLAT',   "Flat",   "Flat/wide handrail"),
    ('NONE',   "None",   "No handrail"),
]


# ════════════════════════════════════════════════════════════
#  PROPERTYGROUP
# ════════════════════════════════════════════════════════════
class AF_StairProperties(PropertyGroup):

    is_af_stair : BoolProperty(
        name    = "Is ArchiForge Stair",
        default = True,
        options = {'HIDDEN'},
    )
    object_name : StringProperty(
        name    = "Object Name",
        default = "",
        options = {'HIDDEN'},
    )

    # ── Tipo ─────────────────────────────────────────────────
    stair_type : EnumProperty(
        name    = "Stair Type",
        items   = AF_STAIR_TYPES,
        default = 'STRAIGHT',
        update  = lambda s, c: af_stair_update(s, c),
    )

    # ── Peldaños ─────────────────────────────────────────────
    step_count : IntProperty(
        name        = "Step Count",
        description = "Total number of steps",
        default     = 12,
        min         = 2,
        max         = 64,
        update      = lambda s, c: af_stair_update(s, c),
    )
    step_width : FloatProperty(
        name        = "Step Width",
        description = "Width of each step (perpendicular to travel)",
        default     = 1.00,
        min         = 0.40,
        max         = 4.00,
        unit        = 'LENGTH',
        update      = lambda s, c: af_stair_update(s, c),
    )
    step_run : FloatProperty(
        name        = "Step Run (Tread)",
        description = "Horizontal depth of each step (huella)",
        default     = 0.28,
        min         = 0.15,
        max         = 0.80,
        unit        = 'LENGTH',
        update      = lambda s, c: af_stair_update(s, c),
    )
    step_rise : FloatProperty(
        name        = "Step Rise (Riser)",
        description = "Vertical height of each step (contrahuella)",
        default     = 0.175,
        min         = 0.05,
        max         = 0.40,
        unit        = 'LENGTH',
        update      = lambda s, c: af_stair_update(s, c),
    )
    step_thickness : FloatProperty(
        name        = "Step Thickness",
        description = "Thickness of the step/tread slab",
        default     = 0.035,
        min         = 0.010,
        max         = 0.20,
        unit        = 'LENGTH',
        update      = lambda s, c: af_stair_update(s, c),
    )
    step_nose : FloatProperty(
        name        = "Nosing",
        description = "Horizontal overhang (vuelo del peldaño)",
        default     = 0.025,
        min         = 0.0,
        max         = 0.10,
        unit        = 'LENGTH',
        update      = lambda s, c: af_stair_update(s, c),
    )

    # ── Contrahuella ──────────────────────────────────────────
    riser_enable : BoolProperty(
        name        = "Risers",
        description = "Generate vertical riser panels",
        default     = True,
        update      = lambda s, c: af_stair_update(s, c),
    )
    riser_thickness : FloatProperty(
        name        = "Riser Thickness",
        description = "Thickness of the riser panel",
        default     = 0.018,
        min         = 0.005,
        max         = 0.10,
        unit        = 'LENGTH',
        update      = lambda s, c: af_stair_update(s, c),
    )

    # ── Zanca (Stringer) ──────────────────────────────────────
    stringer_type : EnumProperty(
        name    = "Stringer Type",
        items   = AF_STRINGER_TYPES,
        default = 'CLOSED',
        update  = lambda s, c: af_stair_update(s, c),
    )
    stringer_width : FloatProperty(
        name        = "Stringer Width",
        description = "Width/thickness of stringer",
        default     = 0.04,
        min         = 0.01,
        max         = 0.30,
        unit        = 'LENGTH',
        update      = lambda s, c: af_stair_update(s, c),
    )
    stringer_height : FloatProperty(
        name        = "Stringer Height",
        description = "Extra height below steps for closed stringer",
        default     = 0.20,
        min         = 0.0,
        max         = 1.0,
        unit        = 'LENGTH',
        update      = lambda s, c: af_stair_update(s, c),
    )

    # ── Descanso (Landing) ────────────────────────────────────
    landing_enable : BoolProperty(
        name        = "Landing",
        description = "Add intermediate landing platform",
        default     = False,
        update      = lambda s, c: af_stair_update(s, c),
    )
    landing_step : IntProperty(
        name        = "Landing at Step",
        description = "Step number where landing is placed",
        default     = 6,
        min         = 1,
        max         = 63,
        update      = lambda s, c: af_stair_update(s, c),
    )
    landing_depth : FloatProperty(
        name        = "Landing Depth",
        description = "Depth of the landing platform",
        default     = 1.00,
        min         = 0.60,
        max         = 4.00,
        unit        = 'LENGTH',
        update      = lambda s, c: af_stair_update(s, c),
    )
    landing_thickness : FloatProperty(
        name        = "Landing Thickness",
        description = "Thickness of landing slab",
        default     = 0.15,
        min         = 0.05,
        max         = 0.50,
        unit        = 'LENGTH',
        update      = lambda s, c: af_stair_update(s, c),
    )

    # ── Barandilla ────────────────────────────────────────────
    railing_enable : BoolProperty(
        name        = "Railing",
        description = "Generate railing system",
        default     = True,
        update      = lambda s, c: af_stair_update(s, c),
    )
    railing_sides : EnumProperty(
        name  = "Railing Sides",
        items = [
            ('LEFT',  "Left",  "Railing on left side only"),
            ('RIGHT', "Right", "Railing on right side only"),
            ('BOTH',  "Both",  "Railing on both sides"),
        ],
        default = 'BOTH',
        update  = lambda s, c: af_stair_update(s, c),
    )
    railing_height : FloatProperty(
        name        = "Railing Height",
        description = "Height of railing from step surface",
        default     = 0.90,
        min         = 0.60,
        max         = 1.50,
        unit        = 'LENGTH',
        update      = lambda s, c: af_stair_update(s, c),
    )
    railing_offset : FloatProperty(
        name        = "Railing Offset",
        description = "Horizontal offset from step edge",
        default     = 0.04,
        min         = 0.0,
        max         = 0.20,
        unit        = 'LENGTH',
        update      = lambda s, c: af_stair_update(s, c),
    )

    # ── Balaustres ────────────────────────────────────────────
    baluster_type : EnumProperty(
        name    = "Baluster Type",
        items   = AF_BALUSTER_TYPES,
        default = 'SQUARE',
        update  = lambda s, c: af_stair_update(s, c),
    )
    baluster_size : FloatProperty(
        name        = "Baluster Size",
        description = "Cross-section size of each baluster",
        default     = 0.04,
        min         = 0.01,
        max         = 0.15,
        unit        = 'LENGTH',
        update      = lambda s, c: af_stair_update(s, c),
    )
    baluster_spacing : FloatProperty(
        name        = "Baluster Spacing",
        description = "Distance between balusters",
        default     = 0.12,
        min         = 0.05,
        max         = 0.50,
        unit        = 'LENGTH',
        update      = lambda s, c: af_stair_update(s, c),
    )

    # ── Pasamanos ─────────────────────────────────────────────
    handrail_type : EnumProperty(
        name    = "Handrail Type",
        items   = AF_HANDRAIL_TYPES,
        default = 'ROUND',
        update  = lambda s, c: af_stair_update(s, c),
    )
    handrail_size : FloatProperty(
        name        = "Handrail Size",
        description = "Diameter or width of handrail",
        default     = 0.05,
        min         = 0.02,
        max         = 0.20,
        unit        = 'LENGTH',
        update      = lambda s, c: af_stair_update(s, c),
    )

    # ── Espiral (solo tipo SPIRAL) ────────────────────────────
    spiral_radius : FloatProperty(
        name        = "Spiral Radius",
        description = "Radius of the spiral staircase",
        default     = 0.80,
        min         = 0.30,
        max         = 5.00,
        unit        = 'LENGTH',
        update      = lambda s, c: af_stair_update(s, c),
    )
    spiral_turns : FloatProperty(
        name        = "Spiral Turns",
        description = "Number of full rotations (360°)",
        default     = 1.0,
        min         = 0.25,
        max         = 5.0,
        update      = lambda s, c: af_stair_update(s, c),
    )
    spiral_column : BoolProperty(
        name        = "Center Column",
        description = "Generate central support column",
        default     = True,
        update      = lambda s, c: af_stair_update(s, c),
    )
    spiral_column_r : FloatProperty(
        name        = "Column Radius",
        description = "Radius of the center column",
        default     = 0.10,
        min         = 0.03,
        max         = 0.50,
        unit        = 'LENGTH',
        update      = lambda s, c: af_stair_update(s, c),
    )
    spiral_column_segs : IntProperty(
        name        = "Column Segments",
        description = "Number of segments for column circle",
        default     = 12,
        min         = 6,
        max         = 32,
        update      = lambda s, c: af_stair_update(s, c),
    )

    # ── Material slots ────────────────────────────────────────
    mat_tread     : IntProperty(name="Tread Material",     default=0, min=0)
    mat_riser     : IntProperty(name="Riser Material",     default=1, min=0)
    mat_stringer  : IntProperty(name="Stringer Material",  default=2, min=0)
    mat_railing   : IntProperty(name="Railing Material",   default=3, min=0)
    mat_handrail  : IntProperty(name="Handrail Material",  default=4, min=0)
    mat_landing   : IntProperty(name="Landing Material",   default=5, min=0)


# ════════════════════════════════════════════════════════════
#  GENERADOR DE GEOMETRÍA
# ════════════════════════════════════════════════════════════
class AF_StairGenerator:
    """
    Motor de generación de escaleras paramétricas.
    Sistema de coordenadas:
      X = ancho (izquierda → derecha)
      Y = profundidad (avance de la escalera)
      Z = altura (suelo → arriba)
    """

    def __init__(self, props):
        self.props = props
        self.bm    = bmesh.new()
        self._mat  = self.bm.faces.layers.int.new("material_index")

    # ────────────────────────────────────────────────────────
    #  UTILIDAD — Prisma rectangular
    # ────────────────────────────────────────────────────────
    def _box(self, x0, x1, y0, y1, z0, z1, mat_idx=0):
        """Genera un prisma rectangular en el bmesh."""
        bm  = self.bm
        mat = self._mat

        if (abs(x1 - x0) < 0.0001
                or abs(y1 - y0) < 0.0001
                or abs(z1 - z0) < 0.0001):
            return

        verts = [
            bm.verts.new(Vector((x0, y0, z0))),  # 0
            bm.verts.new(Vector((x1, y0, z0))),  # 1
            bm.verts.new(Vector((x1, y1, z0))),  # 2
            bm.verts.new(Vector((x0, y1, z0))),  # 3
            bm.verts.new(Vector((x0, y0, z1))),  # 4
            bm.verts.new(Vector((x1, y0, z1))),  # 5
            bm.verts.new(Vector((x1, y1, z1))),  # 6
            bm.verts.new(Vector((x0, y1, z1))),  # 7
        ]
        bm.verts.ensure_lookup_table()

        for fi in [
            (0, 1, 5, 4), (2, 3, 7, 6),
            (0, 3, 2, 1), (4, 5, 6, 7),
            (0, 4, 7, 3), (1, 2, 6, 5),
        ]:
            f = bm.faces.new([verts[i] for i in fi])
            f[mat] = mat_idx

    # ────────────────────────────────────────────────────────
    #  UTILIDAD — Prisma con transformación (Matrix)
    # ────────────────────────────────────────────────────────
    def _box_transformed(self, x0, x1, y0, y1, z0, z1,
                          transform, mat_idx=0):
        """
        Genera un prisma rectangular con transformación
        de matriz aplicada (para escaleras en L, U, espiral).
        """
        bm  = self.bm
        mat = self._mat

        local_verts = [
            Vector((x0, y0, z0)), Vector((x1, y0, z0)),
            Vector((x1, y1, z0)), Vector((x0, y1, z0)),
            Vector((x0, y0, z1)), Vector((x1, y0, z1)),
            Vector((x1, y1, z1)), Vector((x0, y1, z1)),
        ]

        bm_verts = [
            bm.verts.new(transform @ v) for v in local_verts
        ]
        bm.verts.ensure_lookup_table()

        for fi in [
            (0, 1, 5, 4), (2, 3, 7, 6),
            (0, 3, 2, 1), (4, 5, 6, 7),
            (0, 4, 7, 3), (1, 2, 6, 5),
        ]:
            f = bm.faces.new([bm_verts[i] for i in fi])
            f[mat] = mat_idx

    # ────────────────────────────────────────────────────────
    #  PELDAÑOS RECTOS — núcleo compartido
    # ────────────────────────────────────────────────────────
    def _build_straight_steps(
        self, n_steps, step_width, step_run, step_rise,
        step_thickness, step_nose, y_start, z_start,
        transform=None, mi_tread=0, mi_riser=1
    ):
        """
        Genera n_steps peldaños rectos a partir de
        (y_start, z_start), opcionalmente con transform.

        Retorna la posición Y y Z del último peldaño.
        """
        p  = self.props
        rt = p.riser_thickness

        for i in range(n_steps):
            y0 = y_start + i * step_run
            y1 = y0 + step_run + step_nose
            z0 = z_start + i * step_rise
            z1 = z0 + step_thickness

            # — Huella (tread) —
            if transform:
                self._box_transformed(
                    0.0, step_width,
                    y0 - step_nose, y1,
                    z0, z1,
                    transform, mi_tread
                )
            else:
                self._box(
                    0.0, step_width,
                    y0 - step_nose, y1,
                    z0, z1,
                    mi_tread
                )

            # — Contrahuella (riser) —
            if p.riser_enable:
                rz0 = z0 - step_rise + step_thickness
                rz1 = z0
                if transform:
                    self._box_transformed(
                        0.0, step_width,
                        y0, y0 + rt,
                        rz0, rz1,
                        transform, mi_riser
                    )
                else:
                    self._box(
                        0.0, step_width,
                        y0, y0 + rt,
                        rz0, rz1,
                        mi_riser
                    )

        y_end = y_start + n_steps * step_run
        z_end = z_start + n_steps * step_rise
        return y_end, z_end

    # ────────────────────────────────────────────────────────
    #  ZANCA (STRINGER)
    # ────────────────────────────────────────────────────────
    def _build_stringer(
        self, n_steps, step_run, step_rise, step_width,
        stringer_w, stringer_h, stringer_type,
        y_start, z_start, transform=None, mi=2
    ):
        """
        Genera las zancas laterales de la escalera.
        Tipos: CLOSED, OPEN (sawtooth), CENTER, NONE.
        """
        if stringer_type == 'NONE':
            return

        total_run  = n_steps * step_run
        total_rise = n_steps * step_rise

        if stringer_type == 'CLOSED':
            # — Zanca cerrada: bloque sólido inclinado —
            # Izquierda
            if transform:
                self._box_transformed(
                    -stringer_w, 0.0,
                    y_start, y_start + total_run,
                    z_start - stringer_h,
                    z_start + total_rise,
                    transform, mi
                )
                # Derecha
                self._box_transformed(
                    step_width, step_width + stringer_w,
                    y_start, y_start + total_run,
                    z_start - stringer_h,
                    z_start + total_rise,
                    transform, mi
                )
            else:
                self._box(
                    -stringer_w, 0.0,
                    y_start, y_start + total_run,
                    z_start - stringer_h,
                    z_start + total_rise,
                    mi
                )
                self._box(
                    step_width, step_width + stringer_w,
                    y_start, y_start + total_run,
                    z_start - stringer_h,
                    z_start + total_rise,
                    mi
                )

        elif stringer_type == 'OPEN':
            # — Zanca abierta: perfil escalonado (sawtooth) —
            p = self.props
            st = p.step_thickness
            for i in range(n_steps):
                y0 = y_start + i * step_run
                z0 = z_start + i * step_rise

                # Segmento horizontal
                for x0, x1 in [
                    (-stringer_w, 0.0),
                    (step_width, step_width + stringer_w)
                ]:
                    if transform:
                        self._box_transformed(
                            x0, x1,
                            y0, y0 + step_run,
                            z0 - stringer_h * 0.4,
                            z0 + st,
                            transform, mi
                        )
                    else:
                        self._box(
                            x0, x1,
                            y0, y0 + step_run,
                            z0 - stringer_h * 0.4,
                            z0 + st,
                            mi
                        )

        elif stringer_type == 'CENTER':
            # — Zanca central: una sola viga central —
            cx0 = step_width / 2.0 - stringer_w / 2.0
            cx1 = step_width / 2.0 + stringer_w / 2.0

            if transform:
                self._box_transformed(
                    cx0, cx1,
                    y_start, y_start + total_run,
                    z_start - stringer_h,
                    z_start + total_rise,
                    transform, mi
                )
            else:
                self._box(
                    cx0, cx1,
                    y_start, y_start + total_run,
                    z_start - stringer_h,
                    z_start + total_rise,
                    mi
                )

    # ────────────────────────────────────────────────────────
    #  BARANDILLA (RAILING)
    # ────────────────────────────────────────────────────────
    def _build_railing(
        self, n_steps, step_run, step_rise, step_width,
        rail_h, rail_offset, baluster_type,
        baluster_size, baluster_spacing,
        handrail_type, handrail_size,
        y_start, z_start, transform=None,
        mi_rail=3, mi_hand=4
    ):
        """
        Genera el sistema de barandilla:
        - Balaustres verticales
        - Pasamanos inclinado
        """
        p = self.props
        if not p.railing_enable:
            return

        sides = p.railing_sides
        total_run  = n_steps * step_run
        total_rise = n_steps * step_rise

        # — Posiciones X de cada lado —
        x_positions = []
        if sides in ('LEFT', 'BOTH'):
            x_positions.append(-rail_offset)
        if sides in ('RIGHT', 'BOTH'):
            x_positions.append(step_width + rail_offset)

        for x_rail in x_positions:
            # — Balaustres —
            if baluster_type != 'NONE':
                self._build_balusters(
                    x_rail, x_rail,
                    n_steps, step_run, step_rise,
                    rail_h, baluster_size,
                    baluster_spacing, baluster_type,
                    y_start, z_start,
                    transform, mi_rail
                )

            # — Pasamanos —
            if handrail_type != 'NONE':
                self._build_handrail(
                    x_rail, total_run, total_rise,
                    rail_h, handrail_size,
                    handrail_type, y_start, z_start,
                    transform, mi_hand
                )

    def _build_balusters(
        self, x_left, x_right, n_steps, step_run, step_rise,
        rail_h, baluster_size, baluster_spacing,
        baluster_type, y_start, z_start, transform, mi
    ):
        """
        Genera los balaustres verticales a lo largo de la escalera.
        Se colocan en cada peldaño según el spacing.
        """
        half_s = baluster_size / 2.0
        bm     = self.bm
        mat    = self._mat

        for i in range(n_steps):
            y_step = y_start + i * step_run
            z_step = z_start + i * step_rise

            # — Cuántos balaustres por peldaño —
            n_per_step = max(
                1, int(step_run / baluster_spacing)
            )
            step_spacing = step_run / n_per_step

            for j in range(n_per_step):
                by = y_step + j * step_spacing + step_spacing / 2.0
                bz = z_step   # base en la superficie del peldaño
                bz_top = bz + rail_h

                # — Interpolación de altura en pasamanos —
                # El pasamanos sigue la línea de la escalera
                progress = (by - y_start) / (n_steps * step_run)
                bz_top   = bz + rail_h

                if baluster_type == 'SQUARE':
                    if transform:
                        self._box_transformed(
                            x_left - half_s,
                            x_left + half_s,
                            by - half_s,
                            by + half_s,
                            bz, bz_top,
                            transform, mi
                        )
                    else:
                        self._box(
                            x_left - half_s,
                            x_left + half_s,
                            by - half_s,
                            by + half_s,
                            bz, bz_top,
                            mi
                        )

                elif baluster_type == 'ROUND':
                    # — Aproximar círculo con octágono —
                    self._octagonal_column(
                        cx   = x_left,
                        cy   = by,
                        r    = half_s,
                        z0   = bz,
                        z1   = bz_top,
                        transform = transform,
                        mi   = mi
                    )

                elif baluster_type == 'FLAT':
                    # — Panel plano (tabla) —
                    if transform:
                        self._box_transformed(
                            x_left - half_s * 0.3,
                            x_left + half_s * 0.3,
                            by - half_s * 2,
                            by + half_s * 2,
                            bz, bz_top,
                            transform, mi
                        )
                    else:
                        self._box(
                            x_left - half_s * 0.3,
                            x_left + half_s * 0.3,
                            by - half_s * 2,
                            by + half_s * 2,
                            bz, bz_top,
                            mi
                        )

    def _octagonal_column(self, cx, cy, r, z0, z1,
                           transform, mi):
        """
        Genera una columna octagonal (aproximación de redondo).
        """
        bm     = self.bm
        mat    = self._mat
        n_segs = 8
        angle_step = (2 * math.pi) / n_segs

        verts_bot = []
        verts_top = []

        for i in range(n_segs):
            a   = i * angle_step
            vx  = cx + r * math.cos(a)
            vy  = cy + r * math.sin(a)
            pt_b = Vector((vx, vy, z0))
            pt_t = Vector((vx, vy, z1))

            if transform:
                verts_bot.append(bm.verts.new(transform @ pt_b))
                verts_top.append(bm.verts.new(transform @ pt_t))
            else:
                verts_bot.append(bm.verts.new(pt_b))
                verts_top.append(bm.verts.new(pt_t))

        bm.verts.ensure_lookup_table()

        # — Caras laterales —
        for i in range(n_segs):
            next_i = (i + 1) % n_segs
            f = bm.faces.new([
                verts_bot[i],
                verts_bot[next_i],
                verts_top[next_i],
                verts_top[i],
            ])
            f[mat] = mi

        # — Tapas —
        try:
            fb = bm.faces.new(verts_bot)
            fb[mat] = mi
            ft = bm.faces.new(list(reversed(verts_top)))
            ft[mat] = mi
        except Exception:
            pass

    def _build_handrail(
        self, x_rail, total_run, total_rise,
        rail_h, handrail_size, handrail_type,
        y_start, z_start, transform, mi
    ):
        """
        Genera el pasamanos a lo largo de la escalera.
        Se construye como una barra inclinada.
        """
        hs   = handrail_size
        half = hs / 2.0

        y0_h = y_start
        y1_h = y_start + total_run
        z0_h = z_start + rail_h
        z1_h = z_start + total_rise + rail_h

        if handrail_type == 'SQUARE':
            bm  = self.bm
            mat = self._mat

            verts = [
                Vector((x_rail - half, y0_h, z0_h - half)),
                Vector((x_rail + half, y0_h, z0_h - half)),
                Vector((x_rail + half, y0_h, z0_h + half)),
                Vector((x_rail - half, y0_h, z0_h + half)),
                Vector((x_rail - half, y1_h, z1_h - half)),
                Vector((x_rail + half, y1_h, z1_h - half)),
                Vector((x_rail + half, y1_h, z1_h + half)),
                Vector((x_rail - half, y1_h, z1_h + half)),
            ]

            if transform:
                bm_verts = [bm.verts.new(transform @ v) for v in verts]
            else:
                bm_verts = [bm.verts.new(v) for v in verts]

            bm.verts.ensure_lookup_table()
            for fi in [
                (0, 1, 5, 4), (2, 3, 7, 6),
                (0, 3, 2, 1), (4, 5, 6, 7),
                (0, 4, 7, 3), (1, 2, 6, 5),
            ]:
                f = bm.faces.new([bm_verts[i] for i in fi])
                f[mat] = mi

        elif handrail_type in ('ROUND', 'FLAT'):
            # — Aproximar el pasamanos con secciones —
            n_segs  = 8
            seg_len = total_run / max(n_segs, 1)
            rise_per_seg = total_rise / max(n_segs, 1)

            for s in range(n_segs):
                y0_s = y_start + s * seg_len
                y1_s = y0_s + seg_len
                z0_s = z_start + rail_h + s * rise_per_seg
                z1_s = z0_s + rise_per_seg

                if handrail_type == 'ROUND':
                    bm  = self.bm
                    mat = self._mat
                    segs_c = 6
                    a_step = (2 * math.pi) / segs_c

                    vb, vt = [], []
                    for i in range(segs_c):
                        a  = i * a_step
                        vx = x_rail + half * math.cos(a)
                        vz0 = z0_s + half * math.sin(a)
                        vz1 = z1_s + half * math.sin(a)

                        pt_b = Vector((vx, y0_s, vz0))
                        pt_t = Vector((vx, y1_s, vz1))

                        if transform:
                            vb.append(bm.verts.new(transform @ pt_b))
                            vt.append(bm.verts.new(transform @ pt_t))
                        else:
                            vb.append(bm.verts.new(pt_b))
                            vt.append(bm.verts.new(pt_t))

                    bm.verts.ensure_lookup_table()
                    for i in range(segs_c):
                        ni = (i + 1) % segs_c
                        f = bm.faces.new([vb[i], vb[ni], vt[ni], vt[i]])
                        f[mat] = mi
                else:
                    # FLAT
                    if transform:
                        self._box_transformed(
                            x_rail - half * 1.5, x_rail + half * 1.5,
                            y0_s, y1_s,
                            z0_s - half * 0.4, z0_s + half * 0.4,
                            transform, mi
                        )
                    else:
                        self._box(
                            x_rail - half * 1.5, x_rail + half * 1.5,
                            y0_s, y1_s,
                            z0_s - half * 0.4, z0_s + half * 0.4,
                            mi
                        )

    # ────────────────────────────────────────────────────────
    #  DESCANSO (LANDING)
    # ────────────────────────────────────────────────────────
    def _build_landing(
        self, y_pos, z_pos, step_width,
        landing_depth, landing_thickness,
        transform=None, mi=5
    ):
        """Genera la plataforma de descanso."""
        if transform:
            self._box_transformed(
                -self.props.stringer_width,
                step_width + self.props.stringer_width,
                y_pos, y_pos + landing_depth,
                z_pos - landing_thickness, z_pos,
                transform, mi
            )
        else:
            self._box(
                -self.props.stringer_width,
                step_width + self.props.stringer_width,
                y_pos, y_pos + landing_depth,
                z_pos - landing_thickness, z_pos,
                mi
            )

    # ────────────────────────────────────────────────────────
    #  COLUMNA CENTRAL ESPIRAL
    # ────────────────────────────────────────────────────────
    def _build_spiral_column(self, total_height, mi=2):
        """
        Genera la columna central de la escalera de caracol.
        """
        p   = self.props
        r   = p.spiral_column_r
        seg = p.spiral_column_segs
        bm  = self.bm
        mat = self._mat

        verts_bot = []
        verts_top = []
        a_step = (2 * math.pi) / seg

        for i in range(seg):
            a = i * a_step
            vx = r * math.cos(a)
            vy = r * math.sin(a)
            verts_bot.append(bm.verts.new(Vector((vx, vy, 0.0))))
            verts_top.append(bm.verts.new(Vector((vx, vy, total_height))))

        bm.verts.ensure_lookup_table()

        for i in range(seg):
            ni = (i + 1) % seg
            f = bm.faces.new([
                verts_bot[i], verts_bot[ni],
                verts_top[ni], verts_top[i]
            ])
            f[mat] = mat

        try:
            fb = bm.faces.new(verts_bot)
            fb[mat] = mat
            ft = bm.faces.new(list(reversed(verts_top)))
            ft[mat] = mat
        except Exception:
            pass

    # ────────────────────────────────────────────────────────
    #  TIPO: STRAIGHT (Recta)
    # ────────────────────────────────────────────────────────
    def _build_straight(self):
        """Escalera recta simple."""
        p  = self.props
        n  = p.step_count
        sw = p.step_width
        sr = p.step_run
        si = p.step_rise
        st = p.step_thickness
        sn = p.step_nose

        # — Descanso: dividir steps —
        if p.landing_enable and p.landing_step < n:
            ls = min(p.landing_step, n - 1)

            # Tramo 1
            y_end, z_end = self._build_straight_steps(
                ls, sw, sr, si, st, sn,
                0.0, 0.0,
                mi_tread=p.mat_tread,
                mi_riser=p.mat_riser
            )

            self._build_stringer(
                ls, sr, si, sw,
                p.stringer_width, p.stringer_height,
                p.stringer_type,
                0.0, 0.0, mi=p.mat_stringer
            )

            self._build_railing(
                ls, sr, si, sw,
                p.railing_height, p.railing_offset,
                p.baluster_type, p.baluster_size,
                p.baluster_spacing,
                p.handrail_type, p.handrail_size,
                0.0, 0.0,
                mi_rail=p.mat_railing,
                mi_hand=p.mat_handrail
            )

            # — Descanso —
            self._build_landing(
                y_end, z_end, sw,
                p.landing_depth,
                p.landing_thickness,
                mi=p.mat_landing
            )

            # Tramo 2
            y_start2 = y_end + p.landing_depth
            y_end2, z_end2 = self._build_straight_steps(
                n - ls, sw, sr, si, st, sn,
                y_start2, z_end,
                mi_tread=p.mat_tread,
                mi_riser=p.mat_riser
            )

            self._build_stringer(
                n - ls, sr, si, sw,
                p.stringer_width, p.stringer_height,
                p.stringer_type,
                y_start2, z_end, mi=p.mat_stringer
            )

            self._build_railing(
                n - ls, sr, si, sw,
                p.railing_height, p.railing_offset,
                p.baluster_type, p.baluster_size,
                p.baluster_spacing,
                p.handrail_type, p.handrail_size,
                y_start2, z_end,
                mi_rail=p.mat_railing,
                mi_hand=p.mat_handrail
            )

        else:
            # Sin descanso
            self._build_straight_steps(
                n, sw, sr, si, st, sn,
                0.0, 0.0,
                mi_tread=p.mat_tread,
                mi_riser=p.mat_riser
            )
            self._build_stringer(
                n, sr, si, sw,
                p.stringer_width, p.stringer_height,
                p.stringer_type,
                0.0, 0.0, mi=p.mat_stringer
            )
            self._build_railing(
                n, sr, si, sw,
                p.railing_height, p.railing_offset,
                p.baluster_type, p.baluster_size,
                p.baluster_spacing,
                p.handrail_type, p.handrail_size,
                0.0, 0.0,
                mi_rail=p.mat_railing,
                mi_hand=p.mat_handrail
            )

    # ────────────────────────────────────────────────────────
    #  TIPO: L-SHAPE (En L)
    # ────────────────────────────────────────────────────────
    def _build_l_shape(self):
        """
        Escalera en L con giro de 90°.
        Primer tramo: avanza en Y.
        Segundo tramo: avanza en X (rotado 90°).
        """
        p  = self.props
        n  = p.step_count
        sw = p.step_width
        sr = p.step_run
        si = p.step_rise
        st = p.step_thickness
        sn = p.step_nose

        # — Dividir steps en dos tramos —
        n1 = n // 2
        n2 = n - n1

        # — Tramo 1: dirección +Y —
        y_end, z_end = self._build_straight_steps(
            n1, sw, sr, si, st, sn,
            0.0, 0.0,
            mi_tread=p.mat_tread,
            mi_riser=p.mat_riser
        )

        self._build_stringer(
            n1, sr, si, sw,
            p.stringer_width, p.stringer_height,
            p.stringer_type,
            0.0, 0.0, mi=p.mat_stringer
        )

        self._build_railing(
            n1, sr, si, sw,
            p.railing_height, p.railing_offset,
            p.baluster_type, p.baluster_size,
            p.baluster_spacing,
            p.handrail_type, p.handrail_size,
            0.0, 0.0,
            mi_rail=p.mat_railing,
            mi_hand=p.mat_handrail
        )

        # — Descanso de giro —
        self._build_landing(
            y_end, z_end, sw,
            sw,   # El descanso es cuadrado (sw × sw)
            p.landing_thickness,
            mi=p.mat_landing
        )

        # — Tramo 2: rotado 90° —
        # Transformación: rotación 90° en Z + traslación
        angle    = math.radians(90)
        pivot_x  = 0.0
        pivot_y  = y_end + sw

        rot_z = Matrix.Rotation(angle, 4, 'Z')
        trans = Matrix.Translation(Vector((
            pivot_x + sw,
            pivot_y,
            z_end
        )))
        transform2 = trans @ rot_z

        self._build_straight_steps(
            n2, sw, sr, si, st, sn,
            0.0, 0.0,
            transform = transform2,
            mi_tread  = p.mat_tread,
            mi_riser  = p.mat_riser
        )

        self._build_stringer(
            n2, sr, si, sw,
            p.stringer_width, p.stringer_height,
            p.stringer_type,
            0.0, 0.0,
            transform = transform2,
            mi        = p.mat_stringer
        )

        self._build_railing(
            n2, sr, si, sw,
            p.railing_height, p.railing_offset,
            p.baluster_type, p.baluster_size,
            p.baluster_spacing,
            p.handrail_type, p.handrail_size,
            0.0, 0.0,
            transform = transform2,
            mi_rail   = p.mat_railing,
            mi_hand   = p.mat_handrail
        )

    # ────────────────────────────────────────────────────────
    #  TIPO: U-SHAPE (En U)
    # ────────────────────────────────────────────────────────
    def _build_u_shape(self):
        """
        Escalera en U con dos giros de 90°.
        Tramo 1: +Y, Tramo 2: -Y (paralelo), Tramo 3: +Y de nuevo.
        """
        p  = self.props
        n  = p.step_count
        sw = p.step_width
        sr = p.step_run
        si = p.step_rise
        st = p.step_thickness
        sn = p.step_nose

        n1 = n // 3
        n2 = n // 3
        n3 = n - n1 - n2

        # — Tramo 1 —
        y_end1, z_end1 = self._build_straight_steps(
            n1, sw, sr, si, st, sn, 0.0, 0.0,
            mi_tread=p.mat_tread, mi_riser=p.mat_riser
        )
        self._build_stringer(
            n1, sr, si, sw, p.stringer_width,
            p.stringer_height, p.stringer_type,
            0.0, 0.0, mi=p.mat_stringer
        )
        self._build_railing(
            n1, sr, si, sw, p.railing_height,
            p.railing_offset, p.baluster_type,
            p.baluster_size, p.baluster_spacing,
            p.handrail_type, p.handrail_size,
            0.0, 0.0,
            mi_rail=p.mat_railing, mi_hand=p.mat_handrail
        )

        # — Descanso 1 —
        self._build_landing(
            y_end1, z_end1, sw, sw,
            p.landing_thickness, mi=p.mat_landing
        )

        # — Tramo 2: rotado 90°, paralelo al primero —
        gap = sw * 0.5  # Espacio entre tramos
        rot1 = Matrix.Rotation(math.radians(90), 4, 'Z')
        tr1  = Matrix.Translation(Vector((
            sw + gap + sw,
            y_end1 + sw,
            z_end1
        )))
        t2 = tr1 @ rot1

        y_end2, z_end2 = self._build_straight_steps(
            n2, sw, sr, si, st, sn, 0.0, 0.0,
            transform=t2,
            mi_tread=p.mat_tread, mi_riser=p.mat_riser
        )
        self._build_stringer(
            n2, sr, si, sw, p.stringer_width,
            p.stringer_height, p.stringer_type,
            0.0, 0.0, transform=t2, mi=p.mat_stringer
        )
        self._build_railing(
            n2, sr, si, sw, p.railing_height,
            p.railing_offset, p.baluster_type,
            p.baluster_size, p.baluster_spacing,
            p.handrail_type, p.handrail_size,
            0.0, 0.0, transform=t2,
            mi_rail=p.mat_railing, mi_hand=p.mat_handrail
        )

        # — Descanso 2 —
        y_land2 = n2 * sr
        z_land2 = z_end1 + n2 * si
        rot1b = Matrix.Rotation(math.radians(90), 4, 'Z')
        tr1b  = Matrix.Translation(Vector((
            sw + gap + sw,
            y_end1 + sw + y_land2,
            z_land2
        )))
        t_land2 = tr1b @ rot1b

        self._build_landing(
            0.0, 0.0, sw, sw,
            p.landing_thickness,
            transform=t_land2, mi=p.mat_landing
        )

        # — Tramo 3: de vuelta —
        rot2 = Matrix.Rotation(math.radians(180), 4, 'Z')
        tr2  = Matrix.Translation(Vector((
            sw + gap + sw,
            y_end1 + sw + y_land2 + sw,
            z_land2
        )))
        t3 = tr2 @ rot2

        self._build_straight_steps(
            n3, sw, sr, si, st, sn, 0.0, 0.0,
            transform=t3,
            mi_tread=p.mat_tread, mi_riser=p.mat_riser
        )
        self._build_stringer(
            n3, sr, si, sw, p.stringer_width,
            p.stringer_height, p.stringer_type,
            0.0, 0.0, transform=t3, mi=p.mat_stringer
        )
        self._build_railing(
            n3, sr, si, sw, p.railing_height,
            p.railing_offset, p.baluster_type,
            p.baluster_size, p.baluster_spacing,
            p.handrail_type, p.handrail_size,
            0.0, 0.0, transform=t3,
            mi_rail=p.mat_railing, mi_hand=p.mat_handrail
        )

    # ────────────────────────────────────────────────────────
    #  TIPO: SPIRAL (Caracol / Helicoidal)
    # ────────────────────────────────────────────────────────
    def _build_spiral(self):
        """
        Escalera de caracol helicoidal.
        Cada peldaño es un sector circular que rota y sube.
        """
        p   = self.props
        n   = p.step_count
        r   = p.spiral_radius
        col_r = p.spiral_column_r if p.spiral_column else 0.0
        si  = p.step_rise
        st  = p.step_thickness
        sn  = p.step_nose
        bm  = self.bm
        mat = self._mat

        total_angle = p.spiral_turns * 2 * math.pi
        angle_step  = total_angle / n
        total_height = n * si

        # — Peldaños en espiral —
        segs = 8   # Segmentos del arco por peldaño

        for i in range(n):
            a0 = i * angle_step
            a1 = a0 + angle_step
            z0 = i * si
            z1 = z0 + st

            # — Cara superior del peldaño (huella) —
            verts_top = []
            verts_bot = []

            # Centro (columna)
            pt_center_top = Vector((col_r * math.cos(a0),
                                     col_r * math.sin(a0), z1))
            pt_center_bot = Vector((col_r * math.cos(a0),
                                     col_r * math.sin(a0), z0))

            for j in range(segs + 1):
                a   = a0 + (angle_step / segs) * j
                rx  = (r + sn) * math.cos(a)
                ry  = (r + sn) * math.sin(a)
                verts_top.append(
                    bm.verts.new(Vector((rx, ry, z1)))
                )
                verts_bot.append(
                    bm.verts.new(Vector((rx, ry, z0)))
                )

            # Centro
            vc_top = bm.verts.new(pt_center_top)
            vc_bot = bm.verts.new(pt_center_bot)

            bm.verts.ensure_lookup_table()

            # — Cara superior (huella) —
            for j in range(segs):
                try:
                    f = bm.faces.new([
                        vc_top,
                        verts_top[j],
                        verts_top[j + 1],
                    ])
                    f[mat] = p.mat_tread
                except Exception:
                    pass

            # — Cara inferior —
            for j in range(segs):
                try:
                    f = bm.faces.new([
                        vc_bot,
                        verts_bot[j + 1],
                        verts_bot[j],
                    ])
                    f[mat] = p.mat_tread
                except Exception:
                    pass

            # — Cara exterior (arco) —
            for j in range(segs):
                try:
                    f = bm.faces.new([
                        verts_bot[j],
                        verts_bot[j + 1],
                        verts_top[j + 1],
                        verts_top[j],
                    ])
                    f[mat] = p.mat_riser
                except Exception:
                    pass

        # — Columna central —
        if p.spiral_column:
            self._build_spiral_column(total_height, mi=p.mat_stringer)

        # — Barandilla exterior en espiral —
        if p.railing_enable and p.handrail_type != 'NONE':
            hs   = p.handrail_size
            half = hs / 2.0
            rh   = p.railing_height
            n_hr = n * 4   # Segmentos del pasamanos

            for i in range(n_hr):
                a0   = (i / n_hr) * total_angle
                a1   = ((i + 1) / n_hr) * total_angle
                z0_h = (i / n_hr) * (n * si) + rh
                z1_h = ((i + 1) / n_hr) * (n * si) + rh

                rx0 = (r + sn) * math.cos(a0)
                ry0 = (r + sn) * math.sin(a0)
                rx1 = (r + sn) * math.cos(a1)
                ry1 = (r + sn) * math.sin(a1)

                self._box(
                    rx0 - half, rx0 + half,
                    ry0 - half, ry0 + half,
                    z0_h - half, z0_h + half,
                    p.mat_handrail
                )

    # ────────────────────────────────────────────────────────
    #  TIPO: WINDER (Abanico en el giro)
    # ────────────────────────────────────────────────────────
    def _build_winder(self):
        """
        Escalera con peldaños de abanico (winder) en el giro.
        Primer tramo recto → 3 peldaños abanico → segundo tramo recto.
        """
        p  = self.props
        n  = p.step_count
        sw = p.step_width
        sr = p.step_run
        si = p.step_rise
        st = p.step_thickness
        sn = p.step_nose

        n_winder = 3
        n1 = max(2, (n - n_winder) // 2)
        n2 = max(2, n - n1 - n_winder)

        # — Tramo 1 recto —
        y_end1, z_end1 = self._build_straight_steps(
            n1, sw, sr, si, st, sn, 0.0, 0.0,
            mi_tread=p.mat_tread, mi_riser=p.mat_riser
        )
        self._build_stringer(
            n1, sr, si, sw, p.stringer_width,
            p.stringer_height, p.stringer_type,
            0.0, 0.0, mi=p.mat_stringer
        )

        # — Peldaños abanico —
        bm  = self.bm
        mat = self._mat
        cx  = 0.0          # Pivote del abanico
        cy  = y_end1

        winder_angle = math.radians(90) / n_winder
        r_inner = 0.15
        r_outer = sw + r_inner

        for w in range(n_winder):
            a0 = w * winder_angle
            a1 = a0 + winder_angle
            z0 = z_end1 + w * si
            z1 = z0 + st

            verts = []
            for (a, r_arr) in [
                (a0, [r_inner, r_outer]),
                (a1, [r_inner, r_outer]),
            ]:
                for r in r_arr:
                    vx = cx + r * math.cos(a + math.radians(180))
                    vy = cy + r * math.sin(a + math.radians(180))
                    verts.append(Vector((vx, vy, z0)))
                    verts.append(Vector((vx, vy, z1)))

            bm_v = [bm.verts.new(v) for v in verts]
            bm.verts.ensure_lookup_table()

            # Cara superior
            try:
                f = bm.faces.new([
                    bm_v[1], bm_v[3],
                    bm_v[7], bm_v[5]
                ])
                f[mat] = p.mat_tread
            except Exception:
                pass

        # — Tramo 2 recto: rotado 90° —
        rot = Matrix.Rotation(math.radians(90), 4, 'Z')
        tr  = Matrix.Translation(Vector((
            sw, y_end1, z_end1 + n_winder * si
        )))
        t2  = tr @ rot

        self._build_straight_steps(
            n2, sw, sr, si, st, sn, 0.0, 0.0,
            transform=t2,
            mi_tread=p.mat_tread, mi_riser=p.mat_riser
        )
        self._build_stringer(
            n2, sr, si, sw, p.stringer_width,
            p.stringer_height, p.stringer_type,
            0.0, 0.0, transform=t2, mi=p.mat_stringer
        )

      # ────────────────────────────────────────────────────────
    #  GENERATE — Ensambla todo
    # ────────────────────────────────────────────────────────
    def generate(self):
        """
        Genera la escalera completa según el tipo seleccionado.
        Retorna el bmesh completo.
        """
        p = self.props

        if p.stair_type == 'STRAIGHT':
            self._build_straight()

        elif p.stair_type == 'L_SHAPE':
            self._build_l_shape()

        elif p.stair_type == 'U_SHAPE':
            self._build_u_shape()

        elif p.stair_type == 'SPIRAL':
            self._build_spiral()

        elif p.stair_type == 'WINDER':
            self._build_winder()

        # — Normales —
        # FIX: bmesh.ops.recalc_face_normals recibe bm POSICIONAL,
        #      no como keyword (bm=self.bm falla con TypeError).
        bmesh.ops.recalc_face_normals(
            self.bm,
            faces=self.bm.faces
        )

        return self.bm
# ════════════════════════════════════════════════════════════
#  UPDATE CALLBACKS
# ════════════════════════════════════════════════════════════
def _find_stair_object(props):
    """Busca el objeto Blender que tiene estas propiedades."""
    name = props.object_name
    if name and name in bpy.data.objects:
        return bpy.data.objects[name]
    for obj in bpy.data.objects:
        if (obj.type == 'MESH'
                and hasattr(obj, AF_STAIR_PROP)
                and getattr(obj, AF_STAIR_PROP) is props):
            return obj
    return None


def af_stair_update(self, context):
    """Callback: regenera cuando cambia una propiedad."""
    obj = _find_stair_object(self)
    if obj is None:
        obj = context.active_object
    if obj is None or obj.type != 'MESH':
        return
    props = getattr(obj, AF_STAIR_PROP, None)
    if props is None or not props.is_af_stair:
        return
    _rebuild_stair_mesh(obj, props)


def _rebuild_stair_mesh(obj, props):
    """Regenera el mesh de la escalera."""
    gen = AF_StairGenerator(props)
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


# ════════════════════════════════════════════════════════════
#  SETUP DE MATERIALES
# ════════════════════════════════════════════════════════════
def _setup_stair_materials(obj):
    """Asigna los materiales base de la escalera."""
    mat_names = [
        "AF.Stair.Wood",     # 0 — tread
        "AF.Stair.Wood",     # 1 — riser
        "AF.Stair.Concrete", # 2 — stringer
        "AF.Stair.Metal",    # 3 — railing
        "AF.Stair.Rail",     # 4 — handrail
        "AF.Slab.Default",   # 5 — landing
    ]
    af_material.ensure_af_materials_for_object(obj, mat_names)


# ════════════════════════════════════════════════════════════
#  HELPER — Crear objeto escalera
# ════════════════════════════════════════════════════════════
def _create_stair_object(context, name="AF_Stair"):
    """Crea un objeto escalera ArchiForge."""
    me  = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, me)

    context.collection.objects.link(obj)
    context.view_layer.objects.active = obj
    obj.select_set(True)

    props              = obj.archiforge_stair
    props.is_af_stair  = True
    props.object_name  = obj.name

    _setup_stair_materials(obj)
    return obj, props


# ════════════════════════════════════════════════════════════
#  OPERADORES
# ════════════════════════════════════════════════════════════

class ARCHIFORGE_OT_stair(Operator):
    bl_idname      = "archiforge.stair"
    bl_label       = "Add AF Stair"
    bl_description = "Add a parametric ArchiForge staircase"
    bl_options     = {'REGISTER', 'UNDO'}

    stair_type : EnumProperty(
        name    = "Type",
        items   = AF_STAIR_TYPES,
        default = 'STRAIGHT',
    )
    step_count : IntProperty(
        name    = "Steps",
        default = 12,
        min     = 2,
        max     = 64,
    )
    step_width : FloatProperty(
        name    = "Width",
        default = 1.00,
        min     = 0.40,
        unit    = 'LENGTH',
    )
    step_run : FloatProperty(
        name    = "Run (Tread)",
        default = 0.28,
        min     = 0.15,
        unit    = 'LENGTH',
    )
    step_rise : FloatProperty(
        name    = "Rise",
        default = 0.175,
        min     = 0.05,
        unit    = 'LENGTH',
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        col = layout.column(align=True)
        col.label(text="New Staircase", icon='FORWARD')
        col.prop(self, "stair_type")
        col.separator()
        col.prop(self, "step_count")
        col.prop(self, "step_width")
        col.prop(self, "step_run")
        col.prop(self, "step_rise")

        # — Info de altura total —
        total_h = self.step_count * self.step_rise
        col.separator()
        col.label(
            text=f"Total Height: {total_h:.3f} m",
            icon='INFO'
        )
        total_run = self.step_count * self.step_run
        col.label(
            text=f"Total Run: {total_run:.3f} m",
            icon='INFO'
        )

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')

        obj, props = _create_stair_object(context, "AF_Stair")

        props.stair_type  = self.stair_type
        props.step_count  = self.step_count
        props.step_width  = self.step_width
        props.step_run    = self.step_run
        props.step_rise   = self.step_rise

        _rebuild_stair_mesh(obj, props)

        total_h = self.step_count * self.step_rise
        self.report(
            {'INFO'},
            f"Stair created: {self.step_count} steps, "
            f"{total_h:.2f}m height"
        )
        return {'FINISHED'}


class ARCHIFORGE_OT_stair_update(Operator):
    bl_idname      = "archiforge.stair_update"
    bl_label       = "Update Stair"
    bl_description = "Force regeneration of the selected staircase"
    bl_options     = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj is not None
            and obj.type == 'MESH'
            and hasattr(obj, AF_STAIR_PROP)
            and obj.archiforge_stair.is_af_stair
        )

    def execute(self, context):
        obj   = context.active_object
        props = obj.archiforge_stair
        _rebuild_stair_mesh(obj, props)
        self.report({'INFO'}, "Stair updated")
        return {'FINISHED'}


class ARCHIFORGE_OT_stair_info(Operator):
    """
    Muestra información ergonómica de la escalera.
    Fórmula de Blondel: 2R + T debe estar entre 60 y 65 cm.
    """
    bl_idname      = "archiforge.stair_info"
    bl_label       = "Stair Ergonomic Info"
    bl_description = "Show ergonomic analysis (Blondel formula)"
    bl_options     = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj is not None
            and obj.type == 'MESH'
            and hasattr(obj, AF_STAIR_PROP)
            and obj.archiforge_stair.is_af_stair
        )

    def execute(self, context):
        props  = context.active_object.archiforge_stair
        r      = props.step_rise * 100   # en cm
        t      = props.step_run  * 100   # en cm
        blondel = 2 * r + t

        ok = 60.0 <= blondel <= 65.0

        self.report(
            {'INFO'} if ok else {'WARNING'},
            f"Blondel: 2R+T = {blondel:.1f} cm "
            f"({'✅ OK' if ok else '⚠️  Should be 60-65 cm'}) | "
            f"Rise={r:.1f}cm  Run={t:.1f}cm | "
            f"Total H={props.step_count * props.step_rise:.2f}m"
        )
        return {'FINISHED'}


# ════════════════════════════════════════════════════════════
#  PANEL — N-Panel
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_PT_stair(Panel):
    bl_label       = "Stair Properties"
    bl_idname      = "ARCHIFORGE_PT_stair"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "ArchiForge"
    bl_context     = "objectmode"
    bl_options     = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj is not None
            and obj.type == 'MESH'
            and hasattr(obj, AF_STAIR_PROP)
            and obj.archiforge_stair.is_af_stair
        )

    def draw_header(self, context):
        self.layout.label(text="", icon='FORWARD')

    def draw(self, context):
        obj    = context.active_object
        props  = obj.archiforge_stair
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        # ── Tipo ─────────────────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Type", icon='MODIFIER')
        col.prop(props, "stair_type", text="")

        # ── Info ergonómica ───────────────────────────────────
        r = props.step_rise * 100
        t = props.step_run  * 100
        blondel = 2 * r + t
        ok_color = '✅' if 60 <= blondel <= 65 else '⚠️ '
        box.label(
            text=f"{ok_color} Blondel: 2R+T = {blondel:.1f} cm",
            icon='INFO'
        )
        box.operator(
            "archiforge.stair_info",
            text="Full Analysis",
            icon='INFO'
        )

        # ── Peldaños ──────────────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Steps", icon='MESH_DATA')
        col.prop(props, "step_count")
        col.prop(props, "step_width")
        col.prop(props, "step_run",       text="Tread (Run)")
        col.prop(props, "step_rise",      text="Riser (Rise)")
        col.prop(props, "step_thickness", text="Thickness")
        col.prop(props, "step_nose",      text="Nosing")

        # — Stats —
        total_h   = props.step_count * props.step_rise
        total_run = props.step_count * props.step_run
        col.separator(factor=0.3)
        col.label(text=f"Height: {total_h:.3f} m", icon='EMPTY_ARROWS')
        col.label(text=f"Run:    {total_run:.3f} m", icon='EMPTY_ARROWS')

        # ── Contrahuella ──────────────────────────────────────
        box = layout.box()
        row = box.row(align=True)
        row.prop(
            props, "riser_enable",
            text="Risers",
            icon='TRIA_DOWN' if props.riser_enable else 'TRIA_RIGHT',
            toggle=True, emboss=False,
        )
        if props.riser_enable:
            box.prop(props, "riser_thickness")

        # ── Zanca ─────────────────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Stringer", icon='MESH_CUBE')
        col.prop(props, "stringer_type",   text="Type")
        if props.stringer_type != 'NONE':
            col.prop(props, "stringer_width")
            col.prop(props, "stringer_height")

        # ── Descanso ──────────────────────────────────────────
        if props.stair_type == 'STRAIGHT':
            box = layout.box()
            row = box.row(align=True)
            row.prop(
                props, "landing_enable",
                text="Landing",
                icon='TRIA_DOWN' if props.landing_enable else 'TRIA_RIGHT',
                toggle=True, emboss=False,
            )
            if props.landing_enable:
                col = box.column(align=True)
                col.prop(props, "landing_step")
                col.prop(props, "landing_depth")
                col.prop(props, "landing_thickness")

        # ── Espiral ───────────────────────────────────────────
        if props.stair_type == 'SPIRAL':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Spiral Settings", icon='MESH_CIRCLE')
            col.prop(props, "spiral_radius")
            col.prop(props, "spiral_turns")
            col.separator(factor=0.3)
            row = col.row(align=True)
            row.prop(props, "spiral_column", toggle=True)
            if props.spiral_column:
                col.prop(props, "spiral_column_r")
                col.prop(props, "spiral_column_segs")

        # ── Barandilla ────────────────────────────────────────
        box = layout.box()
        row = box.row(align=True)
        row.prop(
            props, "railing_enable",
            text="Railing",
            icon='TRIA_DOWN' if props.railing_enable else 'TRIA_RIGHT',
            toggle=True, emboss=False,
        )
        if props.railing_enable:
            col = box.column(align=True)
            col.prop(props, "railing_sides",  text="Sides")
            col.prop(props, "railing_height")
            col.prop(props, "railing_offset")

            col.separator(factor=0.3)
            col.label(text="Balusters", icon='PARTICLE_POINT')
            col.prop(props, "baluster_type",    text="Type")
            if props.baluster_type != 'NONE':
                col.prop(props, "baluster_size")
                col.prop(props, "baluster_spacing")

            col.separator(factor=0.3)
            col.label(text="Handrail", icon='CURVE_PATH')
            col.prop(props, "handrail_type",  text="Type")
            if props.handrail_type != 'NONE':
                col.prop(props, "handrail_size")

        # ── Materiales ────────────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Material Slots", icon='MATERIAL')
        col.prop(props, "mat_tread",    text="Tread")
        if props.riser_enable:
            col.prop(props, "mat_riser",    text="Riser")
        if props.stringer_type != 'NONE':
            col.prop(props, "mat_stringer", text="Stringer")
        if props.railing_enable:
            col.prop(props, "mat_railing",  text="Railing")
        if (props.railing_enable
                and props.handrail_type != 'NONE'):
            col.prop(props, "mat_handrail", text="Handrail")
        if props.landing_enable:
            col.prop(props, "mat_landing",  text="Landing")

        # ── Acciones ──────────────────────────────────────────
        layout.separator()
        layout.operator(
            "archiforge.stair_update",
            text="Force Update",
            icon='FILE_REFRESH',
        )


# ════════════════════════════════════════════════════════════
#  REGISTRO
# ════════════════════════════════════════════════════════════
classes = [
    AF_StairProperties,

    ARCHIFORGE_OT_stair,
    ARCHIFORGE_OT_stair_update,
    ARCHIFORGE_OT_stair_info,

    ARCHIFORGE_PT_stair,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Object.archiforge_stair = PointerProperty(
        type        = AF_StairProperties,
        name        = "ArchiForge Stair",
        description = "ArchiForge parametric staircase properties",
    )

    print("[ArchiForge] ✅ af_stair — registered")


def unregister():
    if hasattr(bpy.types.Object, "archiforge_stair"):
        del bpy.types.Object.archiforge_stair

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    print("[ArchiForge] 🔴 af_stair — unregistered")