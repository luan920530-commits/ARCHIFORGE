# -*- coding: utf-8 -*-

# ╔══════════════════════════════════════════════════════════╗
# ║         ARCHIFORGE — af_floor.py                        ║
# ║         Patrones de Piso Paramétricos Blender 3.3 LTS   ║
# ║         GPL v3 — ArchiForge Devs                        ║
# ╚══════════════════════════════════════════════════════════╝

# <pep8 compliant>

# ════════════════════════════════════════════════════════════
#  ¿QUÉ HACE ESTE MÓDULO?
#
#  Genera patrones de piso / revestimiento paramétricos:
#
#  Patrones disponibles:
#  - REGULAR      : Baldosa cuadrada / rectangular alineada
#  - OFFSET       : Baldosa offset (brick pattern)
#  - HERRINGBONE  : Espiga / chevron (45° y 90°)
#  - PARQUET      : Parquet de madera (bloques / versalles)
#  - DIAGONAL     : Diagonal a 45°
#  - HEXAGONAL    : Baldosa hexagonal
#  - BASKET_WEAVE : Entrelazado (cesta)
#  - RANDOM       : Tamaños aleatorios (large format)
#  - COBBLESTONE  : Adoquín irregular
#  - WOOD_PLANK   : Tablones de madera corridos
#
#  Características:
#  - Dimensiones globales configurables
#  - Formatos comerciales de baldosa (30x30, 45x45, 60x60, 60x120 cm)
#    como tamaño inicial editable
#  - Junta (grout) entre piezas: plana, elevada o retraída en REGULAR y
#    OFFSET (los demás patrones solo dejan la separación)
#  - Losa base opcional debajo de las piezas
#  - Espesor y bisel de cada pieza
#  - Borde perimetral (border trim)
#  - Generación desde curva o contorno manual
#  - Offset del patrón (X/Y)
#  - Rotación del patrón
#  - Múltiples zonas de material
# ════════════════════════════════════════════════════════════

import bpy
import bmesh
import math
import random

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
from .af_construction_presets import (
    CUSTOM_PRESET,
    preset_for_tile_size,
    tile_preset_dimensions,
    tile_preset_items,
)
from .af_floor_geometry import (
    GROUT_GEOMETRY_PATTERNS,
    clip_polygon_to_outline,
    fragments_cover_polygon,
    grout_joint_thickness,
    normalize_outline,
    polygon_area,
    polygon_boundary_edges,
    split_polygon_edges,
    triangulate_polygon,
)
from .af_outline_draw import AF_OutlineDrawMixin

try:
    from .af_i18n import tr_report as _tr
except ImportError:  # pragma: no cover - fuera del paquete
    def _tr(text):
        return text

try:
    from .af_icons import icon_kw as _icon
except ImportError:  # pragma: no cover - fuera del paquete
    def _icon(name, fallback='MESH_CUBE', icons=None):
        return {'icon': fallback}


# ════════════════════════════════════════════════════════════
#  CONSTANTES
# ════════════════════════════════════════════════════════════
AF_FLOOR_PROP = "archiforge_floor"
_FLOOR_UPDATE_SUSPENDED = False

AF_FLOOR_PATTERNS = [
    ('REGULAR',      "Regular",       "Aligned square/rect tiles",       'MESH_GRID',     0),
    ('OFFSET',       "Offset",        "Brick / offset bond pattern",     'MESH_PLANE',    1),
    ('HERRINGBONE',  "Herringbone",   "Herringbone / espiga pattern",    'DRIVER_ROTATIONAL_DIFFERENCE', 2),
    ('PARQUET',      "Parquet",       "Wood parquet blocks",             'MESH_CUBE',     3),
    ('DIAGONAL',     "Diagonal",      "Tiles rotated 45°",               'ORIENTATION_GIMBAL', 4),
    ('HEXAGONAL',    "Hexagonal",     "Hexagonal tile pattern",          'MESH_CIRCLE',   5),
    ('BASKET_WEAVE', "Basket Weave",  "Interlocked basket weave",        'MOD_LATTICE',   6),
    ('RANDOM',       "Random",        "Random large format tiles",       'RNDCURVE',      7),
    ('COBBLESTONE',  "Cobblestone",   "Irregular cobblestone pattern",   'MESH_UVSPHERE', 8),
    ('WOOD_PLANK',   "Wood Planks",   "Continuous wood planks",          'MESH_PLANE',    9),
]

AF_TILE_SHAPES = [
    ('SQUARE',  "Square",  "Square tiles"),
    ('RECT',    "Rect",    "Rectangular tiles"),
    ('CUSTOM',  "Custom",  "Custom width/height ratio"),
]

AF_BORDER_STYLES = [
    ('NONE',   "None",   "No border"),
    ('SINGLE', "Single", "Single row border"),
    ('DOUBLE', "Double", "Double row border"),
    ('PICTURE',"Picture Frame", "Picture frame border"),
]

AF_GROUT_STYLES = [
    ('FLAT',    "Flat",     "Joint flush with the tile surface"),
    ('RAISED',  "Raised",   "Joint stands Grout Depth above the tiles"),
    ('RECESSED',"Recessed", "Joint sits Grout Depth below the tiles"),
]

# Commercial tile formats (editable starting sizes, see
# af_construction_presets.py).
AF_TILE_PRESETS = tile_preset_items()


# ════════════════════════════════════════════════════════════
#  PROPERTYGROUP
# ════════════════════════════════════════════════════════════
class AF_FloorVertex(PropertyGroup):
    """One XY point in a floor's saved custom outline."""

    x : FloatProperty(name="X", default=0.0, unit='LENGTH')
    y : FloatProperty(name="Y", default=0.0, unit='LENGTH')


class AF_FloorProperties(PropertyGroup):

    is_af_floor : BoolProperty(
        name="Is ArchiForge Floor", default=True, options={'HIDDEN'},
    )
    object_name : StringProperty(
        name="Object Name", default="", options={'HIDDEN'},
    )

    # ── Patrón ───────────────────────────────────────────────
    pattern : EnumProperty(
        name    = "Pattern",
        items   = AF_FLOOR_PATTERNS,
        default = 'REGULAR',
        update  = lambda s, c: af_floor_update(s, c),
    )

    # ── Dimensiones del área ──────────────────────────────────
    width : FloatProperty(
        name        = "Width (X)",
        description = "Total floor width",
        default     = 4.0,
        min         = 0.10,
        max         = 200.0,
        unit        = 'LENGTH',
        update      = lambda s, c: af_floor_update(s, c),
    )
    depth : FloatProperty(
        name        = "Depth (Y)",
        description = "Total floor depth",
        default     = 3.0,
        min         = 0.10,
        max         = 200.0,
        unit        = 'LENGTH',
        update      = lambda s, c: af_floor_update(s, c),
    )

    # ── Dimensiones de la pieza ────────────────────────────────
    tile_preset : EnumProperty(
        name        = "Tile Format",
        description = ("Commercial tile format used as an editable starting "
                       "size; switches back to Custom when the size is edited"),
        items       = AF_TILE_PRESETS,
        default     = CUSTOM_PRESET,
        update      = lambda s, c: af_floor_tile_preset_update(s, c),
    )
    tile_width : FloatProperty(
        name        = "Tile Width",
        description = "Width of each tile/plank",
        default     = 0.60,
        min         = 0.02,
        max         = 5.0,
        unit        = 'LENGTH',
        update      = lambda s, c: af_floor_tile_size_update(s, c),
    )
    tile_depth : FloatProperty(
        name        = "Tile Depth",
        description = "Depth of each tile/plank",
        default     = 0.60,
        min         = 0.02,
        max         = 5.0,
        unit        = 'LENGTH',
        update      = lambda s, c: af_floor_tile_size_update(s, c),
    )
    tile_thickness : FloatProperty(
        name        = "Tile Thickness",
        description = "Thickness of each tile",
        default     = 0.010,
        min         = 0.002,
        max         = 0.10,
        unit        = 'LENGTH',
        update      = lambda s, c: af_floor_update(s, c),
    )

    # ── Junta (Grout) ─────────────────────────────────────────
    grout_width : FloatProperty(
        name        = "Grout Width",
        description = "Width of grout joint between tiles",
        default     = 0.004,
        min         = 0.0,
        max         = 0.05,
        unit        = 'LENGTH',
        update      = lambda s, c: af_floor_update(s, c),
    )
    grout_depth : FloatProperty(
        name        = "Grout Depth",
        description = "Depth of grout joint (recessed from tile surface)",
        default     = 0.003,
        min         = 0.0,
        max         = 0.02,
        unit        = 'LENGTH',
        update      = lambda s, c: af_floor_update(s, c),
    )
    grout_style : EnumProperty(
        name    = "Grout Style",
        items   = AF_GROUT_STYLES,
        default = 'RECESSED',
        update  = lambda s, c: af_floor_update(s, c),
    )

    # ── Bisel del borde ───────────────────────────────────────
    bevel_size : FloatProperty(
        name        = "Tile Bevel",
        description = "Chamfer on top edge of each tile",
        default     = 0.001,
        min         = 0.0,
        max         = 0.01,
        unit        = 'LENGTH',
        update      = lambda s, c: af_floor_update(s, c),
    )

    # ── Offsets del patrón ────────────────────────────────────
    offset_x : FloatProperty(
        name        = "Offset X",
        description = "Horizontal shift of the whole pattern",
        default     = 0.0,
        min         = -5.0,
        max         = 5.0,
        unit        = 'LENGTH',
        update      = lambda s, c: af_floor_update(s, c),
    )
    offset_y : FloatProperty(
        name        = "Offset Y",
        description = "Vertical shift of the whole pattern",
        default     = 0.0,
        min         = -5.0,
        max         = 5.0,
        unit        = 'LENGTH',
        update      = lambda s, c: af_floor_update(s, c),
    )
    offset_row : FloatProperty(
        name        = "Row Offset",
        description = "Offset fraction per row (OFFSET / WOOD_PLANK)",
        default     = 0.5,
        min         = 0.0,
        max         = 1.0,
        update      = lambda s, c: af_floor_update(s, c),
    )

    # ── Rotación del patrón ───────────────────────────────────
    pattern_rotation : FloatProperty(
        name        = "Pattern Rotation",
        description = "Overall rotation of the floor pattern",
        default     = 0.0,
        min         = -math.pi,
        max         = math.pi,
        subtype     = 'ANGLE',
        update      = lambda s, c: af_floor_update(s, c),
    )

    # ── Herringbone específico ────────────────────────────────
    herringbone_angle : FloatProperty(
        name        = "Herringbone Angle",
        description = "Angle of herringbone pattern (45 or 90)",
        default     = math.radians(45),
        min         = math.radians(30),
        max         = math.radians(90),
        subtype     = 'ANGLE',
        update      = lambda s, c: af_floor_update(s, c),
    )

    # ── Parquet específico ────────────────────────────────────
    parquet_blocks : IntProperty(
        name        = "Blocks per Cell",
        description = "Number of planks per parquet cell",
        default     = 3,
        min         = 2,
        max         = 8,
        update      = lambda s, c: af_floor_update(s, c),
    )
    parquet_style : EnumProperty(
        name    = "Parquet Style",
        items   = [
            ('BLOCK',     "Block",     "Simple block parquet"),
            ('VERSAILLES',"Versailles","Versailles / Versalles pattern"),
            ('HERRING',   "Herring",   "Herringbone parquet"),
        ],
        default = 'BLOCK',
        update  = lambda s, c: af_floor_update(s, c),
    )

    # ── Wood Plank específico ─────────────────────────────────
    plank_width : FloatProperty(
        name        = "Plank Width",
        description = "Width of each wood plank",
        default     = 0.12,
        min         = 0.03,
        max         = 0.50,
        unit        = 'LENGTH',
        update      = lambda s, c: af_floor_update(s, c),
    )
    plank_length_min : FloatProperty(
        name        = "Min Length",
        description = "Minimum plank length",
        default     = 0.60,
        min         = 0.10,
        max         = 5.0,
        unit        = 'LENGTH',
        update      = lambda s, c: af_floor_update(s, c),
    )
    plank_length_max : FloatProperty(
        name        = "Max Length",
        description = "Maximum plank length",
        default     = 2.40,
        min         = 0.20,
        max         = 10.0,
        unit        = 'LENGTH',
        update      = lambda s, c: af_floor_update(s, c),
    )
    plank_random_seed : IntProperty(
        name        = "Random Seed",
        description = "Seed for random plank layout",
        default     = 42,
        min         = 0,
        max         = 9999,
        update      = lambda s, c: af_floor_update(s, c),
    )

    # ── Hexagonal específico ──────────────────────────────────
    hex_size : FloatProperty(
        name        = "Hex Size",
        description = "Size (circumradius) of each hexagon",
        default     = 0.15,
        min         = 0.02,
        max         = 2.0,
        unit        = 'LENGTH',
        update      = lambda s, c: af_floor_update(s, c),
    )
    hex_flat_top : BoolProperty(
        name        = "Flat Top",
        description = "Flat-top hexagons vs pointy-top",
        default     = True,
        update      = lambda s, c: af_floor_update(s, c),
    )

    # ── Cobblestone específico ────────────────────────────────
    cobble_seed : IntProperty(
        name="Seed", default=1, min=0, max=9999,
        update=lambda s, c: af_floor_update(s, c),
    )
    cobble_size_min : FloatProperty(
        name="Min Size", default=0.08, min=0.02, unit='LENGTH',
        update=lambda s, c: af_floor_update(s, c),
    )
    cobble_size_max : FloatProperty(
        name="Max Size", default=0.20, min=0.04, unit='LENGTH',
        update=lambda s, c: af_floor_update(s, c),
    )

    # ── Borde / Border ────────────────────────────────────────
    border_enable : BoolProperty(
        name        = "Border",
        description = "Add a perimeter border strip",
        default     = False,
        update      = lambda s, c: af_floor_update(s, c),
    )
    border_style : EnumProperty(
        name    = "Border Style",
        items   = AF_BORDER_STYLES,
        default = 'SINGLE',
        update  = lambda s, c: af_floor_update(s, c),
    )
    border_width : FloatProperty(
        name        = "Border Width",
        description = "Width of the border strip",
        default     = 0.10,
        min         = 0.02,
        max         = 1.0,
        unit        = 'LENGTH',
        update      = lambda s, c: af_floor_update(s, c),
    )
    border_thickness : FloatProperty(
        name        = "Border Thickness",
        description = "Thickness of border tiles",
        default     = 0.010,
        min         = 0.002,
        max         = 0.10,
        unit        = 'LENGTH',
        update      = lambda s, c: af_floor_update(s, c),
    )

    # ── Base (losa base debajo del patrón) ────────────────────
    base_enable : BoolProperty(
        name        = "Base Slab",
        description = "Generate base slab under the tile pattern",
        default     = True,
        update      = lambda s, c: af_floor_update(s, c),
    )
    base_thickness : FloatProperty(
        name        = "Base Thickness",
        description = "Thickness of base slab",
        default     = 0.05,
        min         = 0.01,
        max         = 0.50,
        unit        = 'LENGTH',
        update      = lambda s, c: af_floor_update(s, c),
    )

    # ── Contorno poligonal opcional ──────────────────────────
    outline_vertices : CollectionProperty(
        name="Outline", type=AF_FloorVertex,
    )
    outline_enabled : BoolProperty(
        name="Use Custom Outline", default=False, options={'HIDDEN'},
    )
    source_curve : StringProperty(
        name="Source Curve", default="", options={'HIDDEN'},
    )

    # ── Origen ────────────────────────────────────────────────
    origin_center : BoolProperty(
        name        = "Center Origin",
        description = "Center the floor pattern on the origin",
        default     = False,
        update      = lambda s, c: af_floor_update(s, c),
    )

    # ── Material slots ────────────────────────────────────────
    mat_tile    : IntProperty(name="Tile Material",    default=0, min=0)
    mat_grout   : IntProperty(name="Grout Material",   default=1, min=0)
    mat_border  : IntProperty(name="Border Material",  default=2, min=0)
    mat_base    : IntProperty(name="Base Material",    default=3, min=0)
    mat_tile_b  : IntProperty(name="Tile B Material",  default=4, min=0)


# ════════════════════════════════════════════════════════════
#  GENERADOR
# ════════════════════════════════════════════════════════════
class AF_FloorGenerator:
    """
    Motor de generación de patrones de piso.
    Sistema de coordenadas:
      X = ancho
      Y = profundidad
      Z = espesor (hacia arriba)
    Origen en (0,0,0) o centrado según origin_center.
    """

    def __init__(self, props):
        self.props = props
        self.bm    = bmesh.new()
        self._mat  = self.bm.faces.layers.int.new("material_index")
        p = props
        if p.origin_center:
            self.ox = -p.width * 0.5
            self.oy = -p.depth * 0.5
        else:
            self.ox = 0.0
            self.oy = 0.0

        # The optional base slab occupies 0..base_thickness; every piece,
        # joint and border is laid on top of it instead of inside it.
        self.z_lift = p.base_thickness if p.base_enable else 0.0

        self.outline = []
        self._outline_triangles = []
        self._pattern_rotation_active = False
        if p.outline_enabled and len(p.outline_vertices) >= 3:
            try:
                raw_outline = normalize_outline([
                    (vertex.x, vertex.y) for vertex in p.outline_vertices
                ])
                self.outline = [
                    (x + self.ox, y + self.oy) for x, y in raw_outline
                ]
                self._outline_triangles = triangulate_polygon(self.outline)
            except ValueError:
                # Keep legacy rectangular floors editable if saved outline
                # data is incomplete or was manually corrupted.
                self.outline = []
                self._outline_triangles = []

    def _rotate_pattern_points(self, points):
        if not self._pattern_rotation_active:
            return points
        angle = float(self.props.pattern_rotation)
        if abs(angle) <= 0.001:
            return points
        if self.props.origin_center:
            cx = cy = 0.0
        else:
            cx = self.props.width * 0.5
            cy = self.props.depth * 0.5
        cosa = math.cos(angle)
        sina = math.sin(angle)
        return [
            (cx + (x - cx) * cosa - (y - cy) * sina,
             cy + (x - cx) * sina + (y - cy) * cosa)
            for x, y in points
        ]

    def _add_prism_fragments(self, fragments, z0, z1, mi):
        """Create a closed prism from clipped convex fragments."""
        split_fragments = split_polygon_edges(fragments)
        vertices = {}

        def get_vert(x, y, z):
            key = (round(float(x), 9), round(float(y), 9), round(float(z), 9))
            vert = vertices.get(key)
            if vert is None:
                vert = self.bm.verts.new(Vector((x, y, z)))
                vertices[key] = vert
            return vert

        for fragment in split_fragments:
            if abs(polygon_area(fragment)) < 1e-9:
                continue
            top = [get_vert(x, y, z1) for x, y in fragment]
            bottom = [get_vert(x, y, z0) for x, y in fragment]
            try:
                face = self.bm.faces.new(top)
                face[self._mat] = mi
            except Exception:
                pass
            try:
                face = self.bm.faces.new(list(reversed(bottom)))
                face[self._mat] = mi
            except Exception:
                pass

        for start, end in polygon_boundary_edges(split_fragments):
            try:
                bottom_start = get_vert(start[0], start[1], z0)
                bottom_end = get_vert(end[0], end[1], z0)
                top_end = get_vert(end[0], end[1], z1)
                top_start = get_vert(start[0], start[1], z1)
                face = self.bm.faces.new(
                    [bottom_start, bottom_end, top_end, top_start])
                face[self._mat] = mi
            except Exception:
                pass

    def _clip_shape_to_outline(self, points, z0, z1, mi):
        """Clip a tile to a custom concave outline; return False if unchanged."""
        if not self.outline:
            return False
        fragments = clip_polygon_to_outline(
            points, self.outline, self._outline_triangles)
        if not fragments:
            return True
        if fragments_cover_polygon(fragments, points):
            if (self._pattern_rotation_active
                    and abs(self.props.pattern_rotation) > 0.001):
                self._add_prism_fragments([points], z0, z1, mi)
                return True
            return False
        self._add_prism_fragments(fragments, z0, z1, mi)
        return True

    def _border_inset(self):
        """The rectangular border pattern is not valid for custom outlines."""
        if self.outline or not self.props.border_enable:
            return 0.0
        return self.props.border_width

    def _joint_thickness(self):
        """Height of the grout prisms for the selected grout style."""
        p = self.props
        return grout_joint_thickness(
            p.grout_style, p.tile_thickness, p.grout_depth)

    # ────────────────────────────────────────────────────────
    #  UTILIDADES
    # ────────────────────────────────────────────────────────
    def _tile(self, x0, y0, tw, td, thick, mi=0, bevel=0.0, z_base=None):
        """
        Genera una baldosa/pieza en la posición (x0,y0)
        con dimensiones tw×td y espesor thick.
        Si bevel > 0, aplica un bisel en los bordes superiores.
        Las piezas se apoyan sobre la losa base (z_lift) salvo que se
        indique un z_base explícito.
        """
        bm  = self.bm
        mat = self._mat
        ox  = self.ox
        oy  = self.oy

        x0 += ox
        y0 += oy
        x1  = x0 + tw
        y1  = y0 + td
        z0  = self.z_lift if z_base is None else z_base
        z1  = z0 + thick

        if tw < 0.001 or td < 0.001 or thick < 0.001:
            return

        subject = self._rotate_pattern_points([
            (x0, y0), (x1, y0), (x1, y1), (x0, y1),
        ])
        if self._clip_shape_to_outline(subject, z0, z1, mi):
            return

        if bevel > 0.001 and bevel < tw * 0.4 and bevel < td * 0.4:
            # — Cara superior con bisel (8 vértices en la cara top) —
            bv = bevel
            top_pts = [
                Vector((x0 + bv, y0,      z1)),
                Vector((x1 - bv, y0,      z1)),
                Vector((x1,      y0 + bv, z1)),
                Vector((x1,      y1 - bv, z1)),
                Vector((x1 - bv, y1,      z1)),
                Vector((x0 + bv, y1,      z1)),
                Vector((x0,      y1 - bv, z1)),
                Vector((x0,      y0 + bv, z1)),
            ]
            bot_pts = [
                Vector((x0, y0, z0)),
                Vector((x1, y0, z0)),
                Vector((x1, y1, z0)),
                Vector((x0, y1, z0)),
            ]
            vt = [bm.verts.new(p) for p in top_pts]
            vb = [bm.verts.new(p) for p in bot_pts]
            bm.verts.ensure_lookup_table()

            # Cara top
            try:
                f = bm.faces.new(vt)
                f[mat] = mi
            except Exception:
                pass

            # Cara bottom
            try:
                f = bm.faces.new(list(reversed(vb)))
                f[mat] = mi
            except Exception:
                pass

            # Caras laterales + bisel
            # Frente (-Y): vb[0]→vb[1] → vt[1]→vt[0]
            side_pairs = [
                ([vb[0], vb[1]], [vt[1], vt[0]]),
                ([vb[1], vb[2]], [vt[4], vt[3], vt[2], vt[1]]),
                ([vb[2], vb[3]], [vt[5], vt[4]]),
                ([vb[3], vb[0]], [vt[0], vt[7], vt[6], vt[5]]),
            ]
            for bot_side, top_side in side_pairs:
                try:
                    f = bm.faces.new(
                        bot_side + list(reversed(top_side))
                    )
                    f[mat] = mi
                except Exception:
                    pass

        else:
            # — Prisma simple sin bisel —
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

    def _tile_rotated(self, cx, cy, tw, td, thick,
                       angle, mi=0, bevel=0.0):
        """
        Genera una baldosa rotada angle radianes alrededor
        de su centro (cx, cy).
        """
        bm   = self.bm
        mat  = self._mat
        ox   = self.ox
        oy   = self.oy
        cosa = math.cos(angle)
        sina = math.sin(angle)
        z0   = self.z_lift
        z1   = z0 + thick

        hw = tw * 0.5
        hd = td * 0.5

        local = [
            Vector((-hw, -hd)),
            Vector(( hw, -hd)),
            Vector(( hw,  hd)),
            Vector((-hw,  hd)),
        ]

        def rot(v):
            return Vector((
                cx + ox + v.x * cosa - v.y * sina,
                cy + oy + v.x * sina + v.y * cosa,
            ))

        corners = [rot(v) for v in local]
        corners = [
            Vector(point) for point in self._rotate_pattern_points(
                [(corner.x, corner.y) for corner in corners]
            )
        ]
        if self._clip_shape_to_outline(
                [(corner.x, corner.y) for corner in corners], z0, z1, mi):
            return

        vb = [bm.verts.new(Vector((c.x, c.y, z0))) for c in corners]
        vt = [bm.verts.new(Vector((c.x, c.y, z1))) for c in corners]
        bm.verts.ensure_lookup_table()

        try:
            bm.faces.new(list(reversed(vb)))[mat] = mi
            bm.faces.new(vt)[mat] = mi
        except Exception:
            pass

        for i in range(4):
            j = (i+1) % 4
            try:
                f = bm.faces.new([vb[i], vb[j], vt[j], vt[i]])
                f[mat] = mi
            except Exception:
                pass

    def _hex_tile(self, cx, cy, r, thick, flat_top, mi=0):
        """
        Genera una baldosa hexagonal.
        flat_top=True → aristas horizontales arriba/abajo
        flat_top=False → vértice en la parte superior
        """
        bm  = self.bm
        mat = self._mat
        ox  = self.ox
        oy  = self.oy
        z0  = self.z_lift
        z1  = z0 + thick
        segs = 6

        base_angle = 0.0 if flat_top else math.radians(30)

        pts = []
        for i in range(segs):
            a = base_angle + i * (2 * math.pi / segs)
            pts.append(Vector((
                cx + ox + r * math.cos(a),
                cy + oy + r * math.sin(a),
            )))

        pts = [
            Vector(point) for point in self._rotate_pattern_points(
                [(point.x, point.y) for point in pts]
            )
        ]
        if self._clip_shape_to_outline(
                [(point.x, point.y) for point in pts], z0, z1, mi):
            return

        vb = [bm.verts.new(Vector((p.x, p.y, z0))) for p in pts]
        vt = [bm.verts.new(Vector((p.x, p.y, z1))) for p in pts]
        bm.verts.ensure_lookup_table()

        try:
            bm.faces.new(list(reversed(vb)))[mat] = mi
            bm.faces.new(vt)[mat] = mi
        except Exception:
            pass

        for i in range(segs):
            j = (i+1) % segs
            try:
                f = bm.faces.new([vb[i], vb[j], vt[j], vt[i]])
                f[mat] = mi
            except Exception:
                pass

    def _grout_line_h(self, x0, x1, y, gw, mi):
        """Línea de junta horizontal (altura según grout_style)."""
        if gw < 0.0001:
            return
        self._tile(
            x0 - self.ox, y - gw * 0.5 - self.oy,
            x1 - x0, gw,
            self._joint_thickness(),
            mi
        )

    def _grout_line_v(self, y0, y1, x, gw, mi):
        """Línea de junta vertical (altura según grout_style)."""
        if gw < 0.0001:
            return
        self._tile(
            x - gw * 0.5 - self.ox, y0 - self.oy,
            gw, y1 - y0,
            self._joint_thickness(),
            mi
        )

    # ────────────────────────────────────────────────────────
    #  LOSA BASE
    # ────────────────────────────────────────────────────────
    def _build_base(self):
        """Genera la losa base debajo del patrón."""
        p  = self.props
        if not p.base_enable:
            return
        bt = p.base_thickness
        w  = p.width
        d  = p.depth
        self._tile(0, 0, w, d, bt, p.mat_base, z_base=0.0)

    # ────────────────────────────────────────────────────────
    #  BORDE PERIMETRAL
    # ────────────────────────────────────────────────────────
    def _build_border(self):
        """Genera el borde perimetral del piso."""
        p  = self.props
        if not p.border_enable or self.outline:
            return

        bw = p.border_width
        bt = p.border_thickness
        w  = p.width
        d  = p.depth
        mi = p.mat_border
        bev = p.bevel_size

        # — Borde frontal (Y=0) —
        self._tile(0, 0, w, bw, bt, mi, bev)
        # — Borde trasero —
        self._tile(0, d - bw, w, bw, bt, mi, bev)
        # — Borde izquierdo —
        self._tile(0, bw, bw, d - bw * 2, bt, mi, bev)
        # — Borde derecho —
        self._tile(w - bw, bw, bw, d - bw * 2, bt, mi, bev)

        if p.border_style == 'DOUBLE':
            bw2 = bw * 0.5
            self._tile(bw, bw, w - bw*2, bw2, bt, mi, bev)
            self._tile(bw, d - bw - bw2, w - bw*2, bw2, bt, mi, bev)
            self._tile(bw, bw + bw2, bw2, d - bw*2 - bw2*2, bt, mi, bev)
            self._tile(w - bw - bw2, bw + bw2, bw2, d - bw*2 - bw2*2, bt, mi, bev)

    # ────────────────────────────────────────────────────────
    #  PATTERN: REGULAR
    # ────────────────────────────────────────────────────────
    def _build_regular(self):
        """
        Baldosa cuadrada/rectangular alineada.
        Filas y columnas perfectamente alineadas.
        """
        p   = self.props
        tw  = p.tile_width
        td  = p.tile_depth
        tt  = p.tile_thickness
        gw  = p.grout_width
        bev = p.bevel_size
        mi  = p.mat_tile
        mi_g = p.mat_grout
        ox  = p.offset_x
        oy  = p.offset_y
        w   = p.width
        d   = p.depth

        # Área interior (dejando espacio para el borde si aplica)
        bw   = self._border_inset()
        x_s  = bw + ox
        y_s  = bw + oy
        x_e  = w - bw
        y_e  = d - bw

        step_x = tw + gw
        step_y = td + gw

        n_cols = max(1, int((x_e - x_s) / step_x) + 2)
        n_rows = max(1, int((y_e - y_s) / step_y) + 2)

        for row in range(n_rows):
            for col in range(n_cols):
                x0 = x_s + col * step_x
                y0 = y_s + row * step_y

                # Recortar al área
                if x0 >= x_e or y0 >= y_e:
                    continue
                tw_clip = min(tw, x_e - x0)
                td_clip = min(td, y_e - y0)
                if tw_clip < 0.005 or td_clip < 0.005:
                    continue

                self._tile(x0, y0, tw_clip, td_clip, tt, mi, bev)

        # — Juntas — (flush / raised / recessed según grout_style)
        if gw > 0.0001:
            jt = self._joint_thickness()
            # Horizontales
            for row in range(n_rows):
                y_grout = y_s + (row + 1) * step_y - gw
                if y_s <= y_grout <= y_e:
                    self._tile(
                        bw, y_grout, w - bw*2, gw,
                        jt,
                        mi_g
                    )
            # Verticales
            for col in range(n_cols):
                x_grout = x_s + (col + 1) * step_x - gw
                if x_s <= x_grout <= x_e:
                    self._tile(
                        x_grout, bw, gw, d - bw*2,
                        jt,
                        mi_g
                    )

    # ────────────────────────────────────────────────────────
    #  PATTERN: OFFSET (Brick Bond)
    # ────────────────────────────────────────────────────────
    def _build_offset(self):
        """
        Patrón de junta corrida (brick bond).
        Las filas alternas están desplazadas por offset_row.
        """
        p    = self.props
        tw   = p.tile_width
        td   = p.tile_depth
        tt   = p.tile_thickness
        gw   = p.grout_width
        bev  = p.bevel_size
        mi   = p.mat_tile
        mi_g = p.mat_grout
        off  = p.offset_row
        ox   = p.offset_x
        oy   = p.offset_y
        w    = p.width
        d    = p.depth
        bw   = self._border_inset()

        x_s  = bw + ox
        y_s  = bw + oy
        x_e  = w - bw
        y_e  = d - bw

        step_x = tw + gw
        step_y = td + gw
        n_cols = max(1, int((x_e - x_s) / step_x) + 2)
        n_rows = max(1, int((y_e - y_s) / step_y) + 2)

        for row in range(n_rows):
            row_off = (off * step_x) if row % 2 == 1 else 0.0
            for col in range(n_cols):
                x0 = x_s + col * step_x - row_off
                y0 = y_s + row * step_y
                if x0 + tw < x_s or x0 >= x_e:
                    continue
                if y0 >= y_e:
                    continue
                x0_c = max(x0, x_s)
                tw_c = min(x0 + tw, x_e) - x0_c
                td_c = min(td, y_e - y0)
                if tw_c < 0.005 or td_c < 0.005:
                    continue
                self._tile(x0_c, y0, tw_c, td_c, tt, mi, bev)

        # Juntas (flush / raised / recessed según grout_style)
        if gw > 0.0001:
            jt = self._joint_thickness()
            for row in range(n_rows):
                yg = y_s + (row + 1) * step_y - gw
                if y_s <= yg < y_e:
                    self._tile(bw, yg, w - bw*2, gw, jt, mi_g)
            for col in range(n_cols + 1):
                for row in range(n_rows):
                    row_off = (off * step_x) if row % 2 == 1 else 0.0
                    xg = x_s + col * step_x - row_off - gw
                    y0 = y_s + row * step_y
                    y1 = min(y0 + td, y_e)
                    if x_s <= xg < x_e and y0 < y_e:
                        self._tile(xg, y0, gw, y1 - y0, jt, mi_g)

    # ────────────────────────────────────────────────────────
    #  PATTERN: HERRINGBONE
    # ────────────────────────────────────────────────────────
    def _build_herringbone(self):
        """
        Patrón en espiga / herringbone.
        Las piezas se alternan a ±angle° respecto al eje X.
        """
        p    = self.props
        tw   = p.tile_width
        td   = p.tile_depth
        tt   = p.tile_thickness
        gw   = p.grout_width
        bev  = p.bevel_size
        mi   = p.mat_tile
        mi_b = p.mat_tile_b
        a    = p.herringbone_angle
        w    = p.width
        d    = p.depth
        bw   = self._border_inset()
        ox   = p.offset_x
        oy   = p.offset_y

        # — Calcula el paso de la celda de espiga —
        # Celda unitaria del herringbone: 2 piezas forman un módulo
        cell_w = tw * math.cos(a) + td * math.sin(a)
        cell_d = tw * math.sin(a) + td * math.cos(a)

        n_cols = max(1, int((w - bw*2) / cell_w) + 3)
        n_rows = max(1, int((d - bw*2) / cell_d) + 3)

        for row in range(-1, n_rows + 1):
            for col in range(-1, n_cols + 1):
                # Pieza A (ángulo positivo)
                cx_a = bw + ox + col * cell_w + tw * 0.5 * math.cos(a)
                cy_a = bw + oy + row * cell_d + tw * 0.5 * math.sin(a)
                self._tile_rotated(
                    cx_a, cy_a, tw, td, tt, a, mi, bev
                )
                # Pieza B (ángulo negativo / perpendicular)
                cx_b = bw + ox + col * cell_w + td * 0.5 * math.sin(a) + tw * math.cos(a)
                cy_b = bw + oy + row * cell_d + td * 0.5 * math.cos(a) - tw * math.sin(a) + td
                self._tile_rotated(
                    cx_b, cy_b, tw, td, tt, -a, mi_b, bev
                )

    # ────────────────────────────────────────────────────────
    #  PATTERN: PARQUET
    # ────────────────────────────────────────────────────────
    def _build_parquet(self):
        """
        Parquet de madera en bloques.
        Cada celda contiene n tablones perpendiculares.
        Las celdas alternas rotan 90°.
        """
        p    = self.props
        tt   = p.tile_thickness
        gw   = p.grout_width
        bev  = p.bevel_size
        mi   = p.mat_tile
        mi_b = p.mat_tile_b
        nb   = p.parquet_blocks
        ox   = p.offset_x
        oy   = p.offset_y
        w    = p.width
        d    = p.depth
        bw   = self._border_inset()

        # La celda del parquet es cuadrada
        plank_w = p.tile_width  / nb
        plank_d = p.tile_depth
        cell    = p.tile_depth    # celda cuadrada

        step_x = cell + gw
        step_y = cell + gw

        n_cols = max(1, int((w - bw*2 + ox) / step_x) + 2)
        n_rows = max(1, int((d - bw*2 + oy) / step_y) + 2)

        for row in range(n_rows):
            for col in range(n_cols):
                x_cell = bw + ox + col * step_x
                y_cell = bw + oy + row * step_y
                rotate = (row + col) % 2 == 1

                for i in range(nb):
                    if rotate:
                        # Tablones horizontales (Y)
                        x0 = x_cell
                        y0 = y_cell + i * (plank_w + gw * 0.5)
                        pw_t = plank_d
                        pd_t = plank_w
                    else:
                        # Tablones verticales (X)
                        x0 = x_cell + i * (plank_w + gw * 0.5)
                        y0 = y_cell
                        pw_t = plank_w
                        pd_t = plank_d

                    mat_idx = mi if not rotate else mi_b
                    self._tile(x0, y0, pw_t, pd_t, tt, mat_idx, bev)

    # ────────────────────────────────────────────────────────
    #  PATTERN: DIAGONAL
    # ────────────────────────────────────────────────────────
    def _build_diagonal(self):
        """
        Baldosas rotadas 45°.
        La malla de centros se rota para llenar el área.
        """
        p    = self.props
        tw   = p.tile_width
        td   = p.tile_depth
        tt   = p.tile_thickness
        bev  = p.bevel_size
        mi   = p.mat_tile
        mi_b = p.mat_tile_b
        gw   = p.grout_width
        w    = p.width
        d    = p.depth
        bw   = self._border_inset()
        ox   = p.offset_x
        oy   = p.offset_y

        a    = math.radians(45)
        step = (tw + gw) * math.cos(a)

        n = max(1, int(max(w, d) / step) + 4)

        for row in range(-n, n*2):
            for col in range(-n, n*2):
                cx = bw + ox + col * step * 2
                cy = bw + oy + row * step * 2

                # Alternar color
                mat_idx = mi if (row + col) % 2 == 0 else mi_b

                self._tile_rotated(cx, cy, tw, td, tt, a, mat_idx, bev)

    # ────────────────────────────────────────────────────────
    #  PATTERN: HEXAGONAL
    # ────────────────────────────────────────────────────────
    def _build_hexagonal(self):
        """
        Baldosa hexagonal en trama offset.
        """
        p   = self.props
        r   = p.hex_size
        tt  = p.tile_thickness
        gw  = p.grout_width
        mi  = p.mat_tile
        ft  = p.hex_flat_top
        w   = p.width
        d   = p.depth
        bw  = self._border_inset()
        ox  = p.offset_x
        oy  = p.offset_y

        # Paso entre hexágonos
        if ft:
            step_x = r * math.sqrt(3) + gw
            step_y = r * 1.5 + gw * 0.5
        else:
            step_x = r * 1.5 + gw * 0.5
            step_y = r * math.sqrt(3) + gw

        n_cols = max(1, int((w - bw*2) / step_x) + 3)
        n_rows = max(1, int((d - bw*2) / step_y) + 3)

        for row in range(-1, n_rows + 1):
            for col in range(-1, n_cols + 1):
                if ft:
                    cx = bw + ox + col * step_x + (step_x * 0.5 if row % 2 == 1 else 0.0)
                    cy = bw + oy + row * step_y
                else:
                    cx = bw + ox + col * step_x
                    cy = bw + oy + row * step_y + (step_y * 0.5 if col % 2 == 1 else 0.0)

                self._hex_tile(cx, cy, r - gw * 0.5, tt, ft, mi)

    # ────────────────────────────────────────────────────────
    #  PATTERN: BASKET WEAVE
    # ────────────────────────────────────────────────────────
    def _build_basket_weave(self):
        """
        Patrón de cesta entrelazada (basket weave).
        2 tablones horizontales + 2 tablones verticales por celda.
        """
        p    = self.props
        tw   = p.tile_width
        td   = p.tile_depth
        tt   = p.tile_thickness
        gw   = p.grout_width
        bev  = p.bevel_size
        mi   = p.mat_tile
        mi_b = p.mat_tile_b
        ox   = p.offset_x
        oy   = p.offset_y
        w    = p.width
        d    = p.depth
        bw   = self._border_inset()

        # Celda = 2×tw + gw × 2×td + gw
        cell_w = 2 * tw + gw
        cell_d = 2 * td + gw

        n_cols = max(1, int((w - bw*2) / cell_w) + 2)
        n_rows = max(1, int((d - bw*2) / cell_d) + 2)

        for row in range(n_rows):
            for col in range(n_cols):
                cx = bw + ox + col * cell_w
                cy = bw + oy + row * cell_d

                # Horizontal pair (arriba de la celda)
                self._tile(cx,        cy,          tw, td, tt, mi, bev)
                self._tile(cx + tw + gw, cy,       tw, td, tt, mi, bev)
                # Vertical pair (debajo de la celda)
                self._tile(cx,        cy + td + gw, td, tw, tt, mi_b, bev)
                self._tile(cx + tw + gw, cy + td + gw, td, tw, tt, mi_b, bev)

    # ────────────────────────────────────────────────────────
    #  PATTERN: WOOD PLANK
    # ────────────────────────────────────────────────────────
    def _build_wood_plank(self):
        """
        Tablones de madera corridos con juntas aleatorias.
        Las filas van en la dirección Y.
        Los tablones se cortan aleatoriamente en X.
        """
        p    = self.props
        pw   = p.plank_width
        tt   = p.tile_thickness
        gw   = p.grout_width
        bev  = p.bevel_size
        mi   = p.mat_tile
        mi_b = p.mat_tile_b
        ox   = p.offset_x
        oy   = p.offset_y
        w    = p.width
        d    = p.depth
        bw   = self._border_inset()
        lmin = p.plank_length_min
        lmax = p.plank_length_max
        off  = p.offset_row
        seed = p.plank_random_seed

        rng = random.Random(seed)

        x_s = bw + ox
        y_s = bw + oy
        x_e = w - bw
        y_e = d - bw

        step_x = pw + gw
        n_rows = max(1, int((x_e - x_s) / step_x) + 2)

        for row in range(n_rows):
            x0_row = x_s + row * step_x
            if x0_row >= x_e:
                break
            pw_row = min(pw, x_e - x0_row)

            # Offset de la fila (alternas)
            row_off = off * rng.uniform(lmin, lmax) if row % 2 == 1 else 0.0

            y_cur = y_s - row_off
            plank_idx = 0

            while y_cur < y_e:
                length = rng.uniform(lmin, lmax)
                y1     = min(y_cur + length, y_e)
                y0_c   = max(y_cur, y_s)
                len_c  = y1 - y0_c

                if len_c > 0.02 and pw_row > 0.01:
                    mat_idx = mi if plank_idx % 2 == 0 else mi_b
                    self._tile(x0_row, y0_c, pw_row, len_c, tt, mat_idx, bev)

                y_cur += length + gw
                plank_idx += 1

    # ────────────────────────────────────────────────────────
    #  PATTERN: RANDOM TILES
    # ────────────────────────────────────────────────────────
    def _build_random(self):
        """
        Baldosas de formato libre / random.
        Mezcla de piezas de distintos tamaños en una cuadrícula.
        """
        p    = self.props
        tw   = p.tile_width
        td   = p.tile_depth
        tt   = p.tile_thickness
        gw   = p.grout_width
        bev  = p.bevel_size
        mi   = p.mat_tile
        mi_b = p.mat_tile_b
        ox   = p.offset_x
        oy   = p.offset_y
        w    = p.width
        d    = p.depth
        bw   = self._border_inset()
        seed = p.plank_random_seed

        rng  = random.Random(seed)
        x_s  = bw + ox
        y_s  = bw + oy
        x_e  = w - bw
        y_e  = d - bw

        # Tamaños posibles (múltiplos del tile base)
        sizes = [(1, 1), (1, 2), (2, 1), (2, 2), (1, 3), (3, 1)]

        step = (tw + gw)
        n_cols = max(1, int((x_e - x_s) / step) + 2)
        n_rows = max(1, int((y_e - y_s) / step) + 2)

        placed = set()

        for row in range(n_rows):
            for col in range(n_cols):
                if (col, row) in placed:
                    continue

                x0 = x_s + col * step
                y0 = y_s + row * step

                if x0 >= x_e or y0 >= y_e:
                    continue

                # Elegir tamaño aleatorio
                sc, sr = rng.choice(sizes)

                # Marcar celdas ocupadas
                for dc in range(sc):
                    for dr in range(sr):
                        placed.add((col + dc, row + dr))

                tw_r = min(sc * step - gw, x_e - x0)
                td_r = min(sr * step - gw, y_e - y0)

                if tw_r < 0.02 or td_r < 0.02:
                    continue

                mat_idx = mi if (col + row) % 2 == 0 else mi_b
                self._tile(x0, y0, tw_r, td_r, tt, mat_idx, bev)

    # ────────────────────────────────────────────────────────
    #  PATTERN: COBBLESTONE
    # ────────────────────────────────────────────────────────
    def _build_cobblestone(self):
        """
        Adoquín irregular.
        Piezas pseudo-rectangulares con tamaños aleatorios
        y ligeras variaciones de posición.
        """
        p    = self.props
        tt   = p.tile_thickness
        bev  = p.bevel_size
        gw   = p.grout_width
        mi   = p.mat_tile
        mi_b = p.mat_tile_b
        ox   = p.offset_x
        oy   = p.offset_y
        w    = p.width
        d    = p.depth
        bw   = self._border_inset()
        smin = p.cobble_size_min
        smax = p.cobble_size_max
        seed = p.cobble_seed

        rng  = random.Random(seed)
        x_s  = bw + ox
        y_s  = bw + oy
        x_e  = w - bw
        y_e  = d - bw

        y_cur = y_s
        idx   = 0

        while y_cur < y_e:
            row_h = rng.uniform(smin, smax)
            x_cur = x_s

            while x_cur < x_e:
                cw = rng.uniform(smin, smax)
                # Variación de posición y tamaño
                jitter_x = rng.uniform(-gw, gw)
                jitter_y = rng.uniform(-gw, gw)

                x0 = x_cur + gw * 0.5 + jitter_x * 0.5
                y0 = y_cur + gw * 0.5 + jitter_y * 0.5
                tw_c = min(cw - gw, x_e - x0)
                td_c = min(row_h - gw, y_e - y0)

                if tw_c > 0.02 and td_c > 0.02:
                    mat_idx = mi if idx % 3 != 0 else mi_b
                    self._tile(x0, y0, tw_c, td_c, tt, mat_idx, bev)

                x_cur += cw
                idx   += 1

            y_cur += row_h

    # ────────────────────────────────────────────────────────
    #  GENERATE
    # ────────────────────────────────────────────────────────
    def generate(self):
        """Genera el patrón completo."""
        p = self.props

        # 1) Base y borde conservan el contorno dibujado sin rotación.
        self._build_base()
        self._build_border()

        # 2) Patrón principal. En contornos personalizados, la rotación se
        # aplica a cada pieza antes de recortarla, no al límite del suelo.
        self._pattern_rotation_active = bool(self.outline)
        dispatch = {
            'REGULAR'     : self._build_regular,
            'OFFSET'      : self._build_offset,
            'HERRINGBONE' : self._build_herringbone,
            'PARQUET'     : self._build_parquet,
            'DIAGONAL'    : self._build_diagonal,
            'HEXAGONAL'   : self._build_hexagonal,
            'BASKET_WEAVE': self._build_basket_weave,
            'RANDOM'      : self._build_random,
            'COBBLESTONE' : self._build_cobblestone,
            'WOOD_PLANK'  : self._build_wood_plank,
        }

        builder = dispatch.get(p.pattern)
        if builder:
            builder()
        self._pattern_rotation_active = False

        # 3) Conserva el comportamiento legacy rectangular. Los contornos
        # personalizados ya rotaron cada baldosa antes del recorte.
        if not self.outline and abs(p.pattern_rotation) > 0.001:
            rot = Matrix.Rotation(p.pattern_rotation, 4, 'Z')
            cx  = p.width  * 0.5
            cy  = p.depth  * 0.5
            for v in self.bm.verts:
                v.co = rot @ (v.co - Vector((cx, cy, 0))) + Vector((cx, cy, 0))

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
def _find_floor_object(props):
    name = props.object_name
    if name and name in bpy.data.objects:
        return bpy.data.objects[name]
    for obj in bpy.data.objects:
        if (obj.type == 'MESH'
                and hasattr(obj, AF_FLOOR_PROP)
                and getattr(obj, AF_FLOOR_PROP) is props):
            return obj
    return None


def af_floor_update(self, context):
    if _FLOOR_UPDATE_SUSPENDED:
        return
    obj = _find_floor_object(self)
    if obj is None:
        obj = context.active_object
    if obj is None or obj.type != 'MESH':
        return
    props = getattr(obj, AF_FLOOR_PROP, None)
    if props is None or not props.is_af_floor:
        return
    _rebuild_floor_mesh(obj, props)


def af_floor_tile_preset_update(self, context):
    """Apply a commercial tile format as the new (editable) tile size."""
    global _FLOOR_UPDATE_SUSPENDED
    dims = tile_preset_dimensions(self.tile_preset)
    if dims is None:
        # CUSTOM keeps whatever size the user typed.
        return
    previous_suspend = _FLOOR_UPDATE_SUSPENDED
    _FLOOR_UPDATE_SUSPENDED = True
    try:
        self.tile_width, self.tile_depth = dims
    finally:
        _FLOOR_UPDATE_SUSPENDED = previous_suspend
    af_floor_update(self, context)


def af_floor_tile_size_update(self, context):
    """Manual size edits fall back to Custom once they leave the preset."""
    if _FLOOR_UPDATE_SUSPENDED:
        return
    expected = preset_for_tile_size(
        self.tile_preset, self.tile_width, self.tile_depth)
    if expected != self.tile_preset:
        # Assigning CUSTOM does not rebuild (no dimensions to apply).
        self.tile_preset = expected
    af_floor_update(self, context)


def _rebuild_floor_mesh(obj, props):
    gen = AF_FloorGenerator(props)
    bm  = gen.generate()
    if bm is None:
        return
    me = obj.data
    bm.to_mesh(me)
    bm.free()
    me.update()

    for poly in me.polygons:
        poly.use_smooth = False

    # Blender <= 3.6 exports the bmesh int layer as polygon_layers_int and
    # its values must be copied; 4.0+ removed that API and a face layer
    # named "material_index" already *is* the material index.
    _layers = getattr(me, "polygon_layers_int", None)
    if _layers is not None and "material_index" in _layers:
        layer = _layers["material_index"]
        for poly in me.polygons:
            poly.material_index = layer.data[poly.index].value


def _setup_floor_materials(obj):
    mat_names = [
        "AF.Floor.Tile",     # 0 tile A
        "AF.Floor.Marble",   # 1 grout / tile B
        "AF.Wall.Concrete",  # 2 border
        "AF.Slab.Default",   # 3 base
        "AF.Floor.Wood",     # 4 tile B alternate
    ]
    af_material.ensure_af_materials_for_object(obj, mat_names)


def _set_floor_outline(props, points):
    """Store a validated world-space path as an object-local CCW outline."""
    global _FLOOR_UPDATE_SUSPENDED
    coords = normalize_outline(
        points, min_segment_length=0.01, max_vertices=64)
    triangulate_polygon(coords)
    xs = [point[0] for point in coords]
    ys = [point[1] for point in coords]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    width, depth = x1 - x0, y1 - y0
    if width < 0.10 or depth < 0.10:
        raise ValueError("El contorno debe medir al menos 0.10 m en X e Y")

    previous_suspend = _FLOOR_UPDATE_SUSPENDED
    _FLOOR_UPDATE_SUSPENDED = True
    try:
        while len(props.outline_vertices) > len(coords):
            props.outline_vertices.remove(len(props.outline_vertices) - 1)
        while len(props.outline_vertices) < len(coords):
            props.outline_vertices.add()
        for vertex, point in zip(props.outline_vertices, coords):
            vertex.x = point[0] - x0
            vertex.y = point[1] - y0
        props.width = width
        props.depth = depth
        props.origin_center = False
        props.border_enable = False
        props.outline_enabled = True
    finally:
        _FLOOR_UPDATE_SUSPENDED = previous_suspend

    return (x0, y0), width, depth


def _create_floor_object(context, name="AF_Floor"):
    mesh = bpy.data.meshes.new(name)
    obj = None
    try:
        obj = bpy.data.objects.new(name, mesh)
        context.collection.objects.link(obj)
        context.view_layer.objects.active = obj
        obj.select_set(True)

        props = obj.archiforge_floor
        props.is_af_floor = True
        props.object_name = obj.name
        _setup_floor_materials(obj)
        return obj, props
    except Exception:
        if obj is not None and obj.name in bpy.data.objects:
            bpy.data.objects.remove(obj, do_unlink=True)
        if mesh.users == 0 and mesh.name in bpy.data.meshes:
            bpy.data.meshes.remove(mesh)
        raise


# ════════════════════════════════════════════════════════════
#  OPERADORES
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_OT_floor(Operator):
    bl_idname      = "archiforge.floor"
    bl_label       = "Add AF Floor"
    bl_description = "Add a parametric ArchiForge floor pattern"
    bl_options     = {'REGISTER', 'UNDO'}

    pattern : EnumProperty(
        name="Pattern", items=AF_FLOOR_PATTERNS, default='REGULAR',
    )
    width : FloatProperty(
        name="Width", default=4.0, min=0.1, unit='LENGTH',
    )
    depth : FloatProperty(
        name="Depth", default=3.0, min=0.1, unit='LENGTH',
    )
    tile_preset : EnumProperty(
        name="Tile Format", items=AF_TILE_PRESETS, default=CUSTOM_PRESET,
        description="Commercial tile format (editable afterwards)",
    )
    tile_width : FloatProperty(
        name="Tile Width", default=0.60, min=0.02, unit='LENGTH',
    )
    tile_depth : FloatProperty(
        name="Tile Depth", default=0.60, min=0.02, unit='LENGTH',
    )

    def _tile_size(self):
        dims = tile_preset_dimensions(self.tile_preset)
        if dims is None:
            return self.tile_width, self.tile_depth
        return dims

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        col = layout.column(align=True)
        col.label(text="New Floor Pattern", **_icon("floor", 'MESH_GRID'))
        col.prop(self, "pattern")
        col.separator()
        col.prop(self, "width")
        col.prop(self, "depth")
        col.separator()
        col.prop(self, "tile_preset")
        size = col.column(align=True)
        size.enabled = self.tile_preset == CUSTOM_PRESET
        size.prop(self, "tile_width")
        size.prop(self, "tile_depth")

        # Info — número aprox de piezas
        tile_w, tile_d = self._tile_size()
        n_x = max(1, int(self.width / max(tile_w, 0.01)))
        n_y = max(1, int(self.depth / max(tile_d, 0.01)))
        col.separator()
        col.label(
            text=f"≈ {n_x * n_y} tiles ({n_x}×{n_y})",
            icon='INFO'
        )

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        obj, props = _create_floor_object(context, "AF_Floor")
        tile_w, tile_d = self._tile_size()
        props.pattern    = self.pattern
        props.width      = self.width
        props.depth      = self.depth
        props.tile_width = tile_w
        props.tile_depth = tile_d
        props.tile_preset = self.tile_preset
        _rebuild_floor_mesh(obj, props)
        self.report({'INFO'}, _tr("Floor created: {}").format(obj.name))
        return {'FINISHED'}


class ARCHIFORGE_OT_floor_draw(AF_OutlineDrawMixin, Operator):
    """Draw a closed custom outline for a parametric floor pattern."""
    bl_idname = "archiforge.floor_draw"
    bl_label = "Draw Floor Outline"
    bl_description = (
        "Click the floor perimeter vertices, then click the first point or "
        "press C/Enter to close"
    )
    bl_options = {'REGISTER', 'UNDO'}
    outline_tool_label = "Floor"

    pattern : EnumProperty(
        name="Pattern", items=AF_FLOOR_PATTERNS, default='REGULAR',
    )
    tile_width : FloatProperty(
        name="Tile Width", default=0.60, min=0.02, unit='LENGTH',
    )
    tile_depth : FloatProperty(
        name="Tile Depth", default=0.60, min=0.02, unit='LENGTH',
    )

    def _create_from_outline(self, context, points):
        return create_floor_from_outline(
            context, points, z=self._draw_z, pattern=self.pattern,
            tile_width=self.tile_width, tile_depth=self.tile_depth)


def create_floor_from_outline(context, points, z=0.0, pattern='REGULAR',
                              tile_width=0.60, tile_depth=0.60,
                              tile_preset=CUSTOM_PRESET, name="AF_Floor"):
    """Create a floor from a closed XY outline (world coordinates).

    Shared by the viewport draw tool and the combined sets. Raises
    ``ValueError`` for an invalid outline and removes the object if the
    mesh rebuild fails.
    """
    global _FLOOR_UPDATE_SUSPENDED
    obj = None
    previous_suspend = _FLOOR_UPDATE_SUSPENDED
    _FLOOR_UPDATE_SUSPENDED = True
    try:
        obj, props = _create_floor_object(context, name)
        origin, _, _ = _set_floor_outline(props, points)
        obj.location = (origin[0], origin[1], float(z))
        props.pattern = pattern
        props.tile_width = tile_width
        props.tile_depth = tile_depth
        props.tile_preset = tile_preset
        props.source_curve = ""
        _rebuild_floor_mesh(obj, props)
        return obj
    except Exception:
        if obj is not None and obj.name in bpy.data.objects:
            mesh = obj.data if obj.type == 'MESH' else None
            bpy.data.objects.remove(obj, do_unlink=True)
            if mesh is not None and mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        raise
    finally:
        _FLOOR_UPDATE_SUSPENDED = previous_suspend


class ARCHIFORGE_OT_floor_update(Operator):
    bl_idname  = "archiforge.floor_update"
    bl_label   = "Update Floor"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj is not None and obj.type == 'MESH'
            and hasattr(obj, AF_FLOOR_PROP)
            and obj.archiforge_floor.is_af_floor
        )

    def execute(self, context):
        obj = context.active_object
        _rebuild_floor_mesh(obj, obj.archiforge_floor)
        self.report({'INFO'}, _tr("Floor updated"))
        return {'FINISHED'}


class ARCHIFORGE_OT_floor_from_wall(Operator):
    """Crea un piso con las dimensiones del muro activo."""
    bl_idname  = "archiforge.floor_from_wall"
    bl_label   = "Floor from Wall"
    bl_options = {'REGISTER', 'UNDO'}

    pattern : EnumProperty(
        name="Pattern", items=AF_FLOOR_PATTERNS, default='REGULAR',
    )
    tile_width : FloatProperty(
        name="Tile Width", default=0.60, min=0.02, unit='LENGTH',
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
        col.prop(self, "pattern")
        col.prop(self, "tile_width")

    def execute(self, context):
        wall  = context.active_object
        pts   = [wall.matrix_world @ Vector(c) for c in wall.bound_box]
        xs    = [p.x for p in pts]
        ys    = [p.y for p in pts]
        w     = max(xs) - min(xs)
        d     = max(ys) - min(ys)

        bpy.ops.object.select_all(action='DESELECT')
        obj, props = _create_floor_object(context, "AF_Floor")
        props.pattern    = self.pattern
        props.width      = w
        props.depth      = d
        props.tile_width = self.tile_width
        props.tile_depth = self.tile_width
        obj.location     = Vector((min(xs), min(ys), 0.0))
        _rebuild_floor_mesh(obj, props)
        self.report({'INFO'}, _tr("Floor from wall '{}'").format(wall.name))
        return {'FINISHED'}


class ARCHIFORGE_OT_floor_from_curve(Operator):
    """Crea un piso siguiendo el contorno de una curva."""
    bl_idname  = "archiforge.floor_from_curve"
    bl_label   = "Floor from Curve"
    bl_options = {'REGISTER', 'UNDO'}

    pattern : EnumProperty(
        name="Pattern", items=AF_FLOOR_PATTERNS, default='REGULAR',
    )
    tile_width : FloatProperty(
        name="Tile Width", default=0.60, min=0.02, unit='LENGTH',
    )

    @classmethod
    def poll(cls, context):
        return (
            context.active_object is not None
            and context.active_object.type == 'CURVE'
        )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        col = self.layout.column(align=True)
        col.prop(self, "pattern")
        col.prop(self, "tile_width")

    def execute(self, context):
        global _FLOOR_UPDATE_SUSPENDED
        curve = context.active_object
        if not curve.data.splines:
            self.report({'ERROR'}, _tr("The curve has no outline spline"))
            return {'CANCELLED'}

        spline = curve.data.splines[0]
        points = []
        if spline.type == 'BEZIER':
            points = [curve.matrix_world @ point.co
                      for point in spline.bezier_points]
        else:
            points = [curve.matrix_world @ Vector(point.co[:3])
                      for point in spline.points]
        if len(points) < 3:
            self.report({'ERROR'}, _tr("Curve outline needs at least 3 points"))
            return {'CANCELLED'}

        bpy.ops.object.select_all(action='DESELECT')
        obj = None
        previous_suspend = _FLOOR_UPDATE_SUSPENDED
        _FLOOR_UPDATE_SUSPENDED = True
        try:
            obj, props = _create_floor_object(context, "AF_Floor")
            origin, _, _ = _set_floor_outline(props, points)
            obj.location = (origin[0], origin[1], min(point.z for point in points))
            props.pattern = self.pattern
            props.tile_width = self.tile_width
            props.tile_depth = self.tile_width
            props.source_curve = curve.name
            _rebuild_floor_mesh(obj, props)
        except ValueError as exc:
            if obj is not None:
                mesh = obj.data
                bpy.data.objects.remove(obj, do_unlink=True)
                if mesh.users == 0:
                    bpy.data.meshes.remove(mesh)
            self.report({'ERROR'}, _tr(str(exc)))
            return {'CANCELLED'}
        except Exception:
            if obj is not None:
                mesh = obj.data
                bpy.data.objects.remove(obj, do_unlink=True)
                if mesh.users == 0:
                    bpy.data.meshes.remove(mesh)
            raise
        finally:
            _FLOOR_UPDATE_SUSPENDED = previous_suspend

        self.report({'INFO'}, _tr("Floor from curve '{}'").format(curve.name))
        return {'FINISHED'}


# ════════════════════════════════════════════════════════════
#  PANEL
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_PT_floor(Panel):
    bl_label       = "Floor Properties"
    bl_idname      = "ARCHIFORGE_PT_floor"
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
            and hasattr(obj, AF_FLOOR_PROP)
            and obj.archiforge_floor.is_af_floor
        )

    def draw_header(self, context):
        self.layout.label(text="", **_icon("floor", 'MESH_GRID'))

    def draw(self, context):
        props  = context.active_object.archiforge_floor
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        # ── Patrón ───────────────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Pattern", icon='MODIFIER')
        col.prop(props, "pattern", text="")
        origin = col.row()
        origin.enabled = not props.outline_enabled
        origin.prop(props, "origin_center")

        # ── Área ─────────────────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Area", icon='ARROW_LEFTRIGHT')
        dimensions = col.column(align=True)
        dimensions.enabled = not props.outline_enabled
        dimensions.prop(props, "width")
        dimensions.prop(props, "depth")
        if props.outline_enabled:
            col.label(
                text=f"Custom outline · {len(props.outline_vertices)} points",
                icon='MOD_BOOLEAN',
            )

        # Info
        n_x = max(1, int(props.width / max(props.tile_width, 0.01)))
        n_y = max(1, int(props.depth / max(props.tile_depth, 0.01)))
        col.label(
            text=f"≈ {n_x * n_y} tiles",
            icon='INFO'
        )

        # ── Baldosa ───────────────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Tile / Piece", icon='MESH_PLANE')
        col.prop(props, "tile_preset", text="Format")
        col.prop(props, "tile_width")
        col.prop(props, "tile_depth")
        col.prop(props, "tile_thickness")
        col.prop(props, "bevel_size")

        # ── Patrón específico ─────────────────────────────────
        if props.pattern == 'OFFSET':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Offset Settings", icon='MODIFIER')
            col.prop(props, "offset_row")

        elif props.pattern == 'HERRINGBONE':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Herringbone Settings")
            col.prop(props, "herringbone_angle")

        elif props.pattern == 'PARQUET':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Parquet Settings", icon='MESH_CUBE')
            col.prop(props, "parquet_style")
            col.prop(props, "parquet_blocks")

        elif props.pattern == 'HEXAGONAL':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Hex Settings", icon='MESH_CIRCLE')
            col.prop(props, "hex_size")
            col.prop(props, "hex_flat_top")

        elif props.pattern == 'WOOD_PLANK':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Plank Settings", icon='MESH_PLANE')
            col.prop(props, "plank_width")
            col.prop(props, "plank_length_min")
            col.prop(props, "plank_length_max")
            col.prop(props, "offset_row")
            col.prop(props, "plank_random_seed")

        elif props.pattern in ('RANDOM', 'COBBLESTONE'):
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Random Settings", icon='RNDCURVE')
            if props.pattern == 'COBBLESTONE':
                col.prop(props, "cobble_size_min")
                col.prop(props, "cobble_size_max")
                col.prop(props, "cobble_seed")
            else:
                col.prop(props, "plank_random_seed")

        # ── Junta ─────────────────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Grout / Joint", icon='MOD_THICKNESS')
        col.prop(props, "grout_style")
        col.prop(props, "grout_width")
        col.prop(props, "grout_depth")
        if props.pattern not in GROUT_GEOMETRY_PATTERNS:
            col.label(
                text="Joint prisms only in Regular / Offset; "
                     "this pattern leaves a gap",
                icon='INFO',
            )

        # ── Offset / Rotación ─────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Layout", icon='ORIENTATION_GLOBAL')
        col.prop(props, "offset_x")
        col.prop(props, "offset_y")
        col.prop(props, "pattern_rotation")

        # ── Borde ─────────────────────────────────────────────
        box = layout.box()
        row = box.row(align=True)
        row.enabled = not props.outline_enabled
        row.prop(
            props, "border_enable",
            text="Border",
            icon='TRIA_DOWN' if props.border_enable else 'TRIA_RIGHT',
            toggle=True, emboss=False,
        )
        if props.outline_enabled:
            box.label(
                text="Border pattern is available for rectangular floors",
                icon='INFO',
            )
        elif props.border_enable:
            col = box.column(align=True)
            col.prop(props, "border_style")
            col.prop(props, "border_width")
            col.prop(props, "border_thickness")

        # ── Base ──────────────────────────────────────────────
        box = layout.box()
        row = box.row(align=True)
        row.prop(
            props, "base_enable",
            text="Base Slab",
            icon='TRIA_DOWN' if props.base_enable else 'TRIA_RIGHT',
            toggle=True, emboss=False,
        )
        if props.base_enable:
            box.prop(props, "base_thickness")

        # ── Materiales ────────────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Materials", icon='MATERIAL')
        col.prop(props, "mat_tile",   text="Tile A")
        col.prop(props, "mat_tile_b", text="Tile B")
        col.prop(props, "mat_grout",  text="Grout")
        if props.border_enable:
            col.prop(props, "mat_border", text="Border")
        if props.base_enable:
            col.prop(props, "mat_base",   text="Base")

        # ── Acciones ──────────────────────────────────────────
        layout.separator()
        row = layout.row(align=True)
        row.operator(
            "archiforge.floor_update",
            text="Force Update",
            icon='FILE_REFRESH',
        )
        row.operator(
            "archiforge.floor_from_wall",
            text="From Wall",
            **_icon("wall", 'SNAP_FACE'),
        )


# ════════════════════════════════════════════════════════════
#  REGISTRO
# ════════════════════════════════════════════════════════════
classes = [
    AF_FloorVertex,
    AF_FloorProperties,

    ARCHIFORGE_OT_floor,
    ARCHIFORGE_OT_floor_draw,
    ARCHIFORGE_OT_floor_update,
    ARCHIFORGE_OT_floor_from_wall,
    ARCHIFORGE_OT_floor_from_curve,

    ARCHIFORGE_PT_floor,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Object.archiforge_floor = PointerProperty(
        type        = AF_FloorProperties,
        name        = "ArchiForge Floor",
        description = "ArchiForge parametric floor pattern properties",
    )
    print("[ArchiForge] ✅ af_floor — registered")


def unregister():
    if hasattr(bpy.types.Object, "archiforge_floor"):
        del bpy.types.Object.archiforge_floor

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    print("[ArchiForge] 🔴 af_floor — unregistered")