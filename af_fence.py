# -*- coding: utf-8 -*-

# ╔══════════════════════════════════════════════════════════╗
# ║         ARCHIFORGE — af_fence.py                        ║
# ║         Cercas y Vallas Paramétricas Blender 3.3 LTS    ║
# ║         GPL v3 — ArchiForge Devs                        ║
# ╚══════════════════════════════════════════════════════════╝

# <pep8 compliant>

# ════════════════════════════════════════════════════════════
#  ¿QUÉ HACE ESTE MÓDULO?
#
#  Genera cercas / vallas / barandillas paramétricas:
#
#  Tipos:
#  - WOOD_PICKET  : Valla de madera con tablas verticales
#  - WOOD_PRIVACY : Valla de privacidad (tablas sin huecos)
#  - METAL_RAIL   : Barandilla metálica con balaustres
#  - CHAIN_LINK   : Malla ciclónica (romboidal)
#  - SPLIT_RAIL   : Valla rústica de troncos
#  - BRICK_WALL   : Muro de ladrillo decorativo
#  - GLASS_RAIL   : Barandilla de vidrio con postes
#  - CUSTOM       : Perfil custom por segmento
#
#  Características:
#  - Multi-segmento con ángulo entre segmentos
#  - Postes con distintos estilos de remate (cap)
#  - Rieles superior / inferior / central
#  - Seguir curva seleccionada
#  - Terreno: seguir plano inclinado
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
AF_FENCE_PROP = "archiforge_fence"

AF_FENCE_TYPES = [
    ('WOOD_PICKET',  "Wood Picket",  "Classic wooden picket fence",       'MESH_PLANE',   0),
    ('WOOD_PRIVACY', "Wood Privacy", "Solid privacy fence",               'MESH_CUBE',    1),
    ('METAL_RAIL',   "Metal Rail",   "Metal railing with balusters",      'PARTICLE_POINT',2),
    ('CHAIN_LINK',   "Chain Link",   "Chain link / wire mesh fence",      'MOD_WIREFRAME',3),
    ('SPLIT_RAIL',   "Split Rail",   "Rustic split rail fence",           'CURVE_PATH',   4),
    ('BRICK_WALL',   "Brick Wall",   "Decorative brick garden wall",      'MESH_GRID',    5),
    ('GLASS_RAIL',   "Glass Rail",   "Glass panel railing with posts",    'MATERIAL',     6),
    ('CUSTOM',       "Custom",       "Custom picket profile",             'GREASEPENCIL', 7),
]

AF_POST_CAP_TYPES = [
    ('FLAT',    "Flat",    "Flat top cap"),
    ('POINTED', "Pointed", "Pointed / pyramid cap"),
    ('BALL',    "Ball",    "Round ball cap"),
    ('CHAMFER', "Chamfer", "Chamfered / beveled cap"),
    ('NONE',    "None",    "No cap"),
]

AF_RAIL_PROFILE = [
    ('SQUARE', "Square", "Square section rail"),
    ('ROUND',  "Round",  "Round / pipe rail"),
    ('FLAT',   "Flat",   "Flat board rail"),
]

AF_PICKET_TOPS = [
    ('FLAT',    "Flat",    "Flat top"),
    ('POINTED', "Pointed", "Pointed / gothic top"),
    ('FRENCH',  "French",  "French / curved top"),
    ('DOG_EAR', "Dog Ear", "Dog ear top"),
]


# ════════════════════════════════════════════════════════════
#  PROPERTYGROUP — Segmento de valla
# ════════════════════════════════════════════════════════════
class AF_FenceSegment(PropertyGroup):
    """Un segmento de valla con su largo y ángulo."""

    length : FloatProperty(
        name        = "Length",
        description = "Length of this fence segment",
        default     = 3.0,
        min         = 0.10,
        max         = 100.0,
        unit        = 'LENGTH',
        update      = lambda s, c: af_fence_update(s, c),
    )
    angle : FloatProperty(
        name        = "Angle",
        description = "Turn angle at end of this segment",
        default     = 0.0,
        min         = -math.pi,
        max         = math.pi,
        subtype     = 'ANGLE',
        update      = lambda s, c: af_fence_update(s, c),
    )
    enabled : BoolProperty(
        name="Enabled", default=True,
        update=lambda s, c: af_fence_update(s, c),
    )


# ════════════════════════════════════════════════════════════
#  PROPERTYGROUP — Valla completa
# ════════════════════════════════════════════════════════════
class AF_FenceProperties(PropertyGroup):

    is_af_fence : BoolProperty(
        name="Is ArchiForge Fence", default=True, options={'HIDDEN'},
    )
    object_name : StringProperty(
        name="Object Name", default="", options={'HIDDEN'},
    )

    # ── Tipo ─────────────────────────────────────────────────
    fence_type : EnumProperty(
        name    = "Fence Type",
        items   = AF_FENCE_TYPES,
        default = 'WOOD_PICKET',
        update  = lambda s, c: af_fence_update(s, c),
    )

    # ── Segmentos ─────────────────────────────────────────────
    n_parts : IntProperty(
        name        = "Segments",
        default     = 1,
        min         = 1,
        max         = 64,
        update      = lambda s, c: af_fence_parts_update(s, c),
    )
    parts : CollectionProperty(
        name = "Parts",
        type = AF_FenceSegment,
    )

    # ── Dimensiones generales ────────────────────────────────
    height : FloatProperty(
        name        = "Height",
        description = "Total fence height",
        default     = 1.20,
        min         = 0.10,
        max         = 10.0,
        unit        = 'LENGTH',
        update      = lambda s, c: af_fence_update(s, c),
    )
    z_offset : FloatProperty(
        name        = "Z Offset",
        description = "Vertical offset of fence base from origin",
        default     = 0.0,
        min         = -5.0,
        max         = 5.0,
        unit        = 'LENGTH',
        update      = lambda s, c: af_fence_update(s, c),
    )

    # ── Postes (Posts) ────────────────────────────────────────
    post_enable : BoolProperty(
        name        = "Posts",
        description = "Generate fence posts",
        default     = True,
        update      = lambda s, c: af_fence_update(s, c),
    )
    post_width : FloatProperty(
        name        = "Post Width",
        description = "Width/diameter of posts",
        default     = 0.10,
        min         = 0.02,
        max         = 0.80,
        unit        = 'LENGTH',
        update      = lambda s, c: af_fence_update(s, c),
    )
    post_depth : FloatProperty(
        name        = "Post Depth",
        description = "Depth of post (if rectangular)",
        default     = 0.10,
        min         = 0.02,
        max         = 0.80,
        unit        = 'LENGTH',
        update      = lambda s, c: af_fence_update(s, c),
    )
    post_height_extra : FloatProperty(
        name        = "Post Extra Height",
        description = "How much the post extends above fence top",
        default     = 0.05,
        min         = 0.0,
        max         = 0.50,
        unit        = 'LENGTH',
        update      = lambda s, c: af_fence_update(s, c),
    )
    post_spacing : FloatProperty(
        name        = "Post Spacing",
        description = "Distance between posts (center to center)",
        default     = 2.40,
        min         = 0.30,
        max         = 10.0,
        unit        = 'LENGTH',
        update      = lambda s, c: af_fence_update(s, c),
    )
    post_cap : EnumProperty(
        name    = "Post Cap",
        items   = AF_POST_CAP_TYPES,
        default = 'POINTED',
        update  = lambda s, c: af_fence_update(s, c),
    )
    post_round : BoolProperty(
        name        = "Round Posts",
        description = "Use round (octagonal) posts instead of square",
        default     = False,
        update      = lambda s, c: af_fence_update(s, c),
    )

    # ── Rieles (Rails) ────────────────────────────────────────
    rail_enable : BoolProperty(
        name        = "Rails",
        description = "Generate horizontal rails",
        default     = True,
        update      = lambda s, c: af_fence_update(s, c),
    )
    rail_count : IntProperty(
        name        = "Rail Count",
        description = "Number of horizontal rails",
        default     = 2,
        min         = 1,
        max         = 6,
        update      = lambda s, c: af_fence_update(s, c),
    )
    rail_width : FloatProperty(
        name        = "Rail Width",
        description = "Width of each rail",
        default     = 0.09,
        min         = 0.01,
        max         = 0.30,
        unit        = 'LENGTH',
        update      = lambda s, c: af_fence_update(s, c),
    )
    rail_depth : FloatProperty(
        name        = "Rail Depth",
        description = "Thickness of each rail",
        default     = 0.04,
        min         = 0.01,
        max         = 0.20,
        unit        = 'LENGTH',
        update      = lambda s, c: af_fence_update(s, c),
    )
    rail_profile : EnumProperty(
        name    = "Rail Profile",
        items   = AF_RAIL_PROFILE,
        default = 'SQUARE',
        update  = lambda s, c: af_fence_update(s, c),
    )
    rail_offset_top : FloatProperty(
        name        = "Top Rail Offset",
        description = "Distance of top rail from fence top",
        default     = 0.05,
        min         = 0.0,
        max         = 0.50,
        unit        = 'LENGTH',
        update      = lambda s, c: af_fence_update(s, c),
    )
    rail_offset_bot : FloatProperty(
        name        = "Bottom Rail Offset",
        description = "Distance of bottom rail from fence base",
        default     = 0.20,
        min         = 0.0,
        max         = 1.0,
        unit        = 'LENGTH',
        update      = lambda s, c: af_fence_update(s, c),
    )

    # ── Tablas / Pickets ──────────────────────────────────────
    picket_enable : BoolProperty(
        name        = "Pickets",
        description = "Generate pickets / boards",
        default     = True,
        update      = lambda s, c: af_fence_update(s, c),
    )
    picket_width : FloatProperty(
        name        = "Picket Width",
        description = "Width of each picket board",
        default     = 0.09,
        min         = 0.01,
        max         = 0.60,
        unit        = 'LENGTH',
        update      = lambda s, c: af_fence_update(s, c),
    )
    picket_thickness : FloatProperty(
        name        = "Picket Thickness",
        description = "Thickness of each picket",
        default     = 0.022,
        min         = 0.005,
        max         = 0.10,
        unit        = 'LENGTH',
        update      = lambda s, c: af_fence_update(s, c),
    )
    picket_gap : FloatProperty(
        name        = "Picket Gap",
        description = "Gap between pickets (0 = privacy fence)",
        default     = 0.05,
        min         = 0.0,
        max         = 0.30,
        unit        = 'LENGTH',
        update      = lambda s, c: af_fence_update(s, c),
    )
    picket_top : EnumProperty(
        name    = "Picket Top Style",
        items   = AF_PICKET_TOPS,
        default = 'POINTED',
        update  = lambda s, c: af_fence_update(s, c),
    )
    picket_z_offset : FloatProperty(
        name        = "Picket Bottom Offset",
        description = "How much the picket starts above the base",
        default     = 0.0,
        min         = 0.0,
        max         = 0.50,
        unit        = 'LENGTH',
        update      = lambda s, c: af_fence_update(s, c),
    )

    # ── Metal Rail específico ──────────────────────────────────
    baluster_size : FloatProperty(
        name        = "Baluster Size",
        description = "Size of metal balusters",
        default     = 0.025,
        min         = 0.005,
        max         = 0.10,
        unit        = 'LENGTH',
        update      = lambda s, c: af_fence_update(s, c),
    )
    baluster_spacing : FloatProperty(
        name        = "Baluster Spacing",
        description = "Space between balusters",
        default     = 0.10,
        min         = 0.02,
        max         = 0.50,
        unit        = 'LENGTH',
        update      = lambda s, c: af_fence_update(s, c),
    )
    baluster_round : BoolProperty(
        name        = "Round Balusters",
        description = "Use round balusters (octagonal approx)",
        default     = True,
        update      = lambda s, c: af_fence_update(s, c),
    )

    # ── Brick Wall específico ──────────────────────────────────
    brick_length : FloatProperty(
        name="Brick Length", default=0.215, min=0.05, unit='LENGTH',
        update=lambda s, c: af_fence_update(s, c),
    )
    brick_height : FloatProperty(
        name="Brick Height", default=0.065, min=0.02, unit='LENGTH',
        update=lambda s, c: af_fence_update(s, c),
    )
    brick_depth : FloatProperty(
        name="Brick Depth",  default=0.102, min=0.02, unit='LENGTH',
        update=lambda s, c: af_fence_update(s, c),
    )
    mortar_gap : FloatProperty(
        name="Mortar Gap",  default=0.010, min=0.0,  unit='LENGTH',
        update=lambda s, c: af_fence_update(s, c),
    )

    # ── Glass Rail específico ──────────────────────────────────
    glass_thickness : FloatProperty(
        name="Glass Thickness", default=0.012, min=0.006, unit='LENGTH',
        update=lambda s, c: af_fence_update(s, c),
    )
    glass_height : FloatProperty(
        name="Glass Panel Height", default=1.0, min=0.1, unit='LENGTH',
        update=lambda s, c: af_fence_update(s, c),
    )
    top_rail_enable : BoolProperty(
        name="Top Handrail", default=True,
        update=lambda s, c: af_fence_update(s, c),
    )

    # ── Chain Link específico ──────────────────────────────────
    chain_cell_size : FloatProperty(
        name="Cell Size", default=0.05, min=0.01, unit='LENGTH',
        update=lambda s, c: af_fence_update(s, c),
    )
    chain_wire_r : FloatProperty(
        name="Wire Radius", default=0.002, min=0.001, unit='LENGTH',
        update=lambda s, c: af_fence_update(s, c),
    )

    # ── Materiales ────────────────────────────────────────────
    mat_post   : IntProperty(name="Post Material",    default=0, min=0)
    mat_rail   : IntProperty(name="Rail Material",    default=1, min=0)
    mat_picket : IntProperty(name="Picket Material",  default=2, min=0)
    mat_cap    : IntProperty(name="Cap Material",     default=3, min=0)
    mat_glass  : IntProperty(name="Glass Material",   default=4, min=0)
    mat_brick  : IntProperty(name="Brick Material",   default=5, min=0)
    mat_mortar : IntProperty(name="Mortar Material",  default=6, min=0)


# ════════════════════════════════════════════════════════════
#  GENERADOR
# ════════════════════════════════════════════════════════════
class AF_FenceGenerator:
    """
    Motor de generación de cercas y vallas.
    Sistema de coordenadas:
      X = avance a lo largo de la valla
      Y = profundidad (espesor)
      Z = altura
    El generador trabaja en espacio local; la rotación entre
    segmentos se aplica con Matrix.
    """

    def __init__(self, props):
        self.props = props
        self.bm    = bmesh.new()
        self._mat  = self.bm.faces.layers.int.new("material_index")

    # ────────────────────────────────────────────────────────
    #  UTILIDADES BÁSICAS
    # ────────────────────────────────────────────────────────
    def _box(self, x0, x1, y0, y1, z0, z1, mi=0, transform=None):
        """Prisma rectangular, con transformación opcional."""
        bm  = self.bm
        mat = self._mat

        if (abs(x1-x0) < 1e-5 or abs(y1-y0) < 1e-5
                or abs(z1-z0) < 1e-5):
            return

        local = [
            Vector((x0, y0, z0)), Vector((x1, y0, z0)),
            Vector((x1, y1, z0)), Vector((x0, y1, z0)),
            Vector((x0, y0, z1)), Vector((x1, y0, z1)),
            Vector((x1, y1, z1)), Vector((x0, y1, z1)),
        ]

        if transform:
            verts = [bm.verts.new(transform @ v) for v in local]
        else:
            verts = [bm.verts.new(v) for v in local]

        bm.verts.ensure_lookup_table()

        for fi in [
            (0,1,5,4),(2,3,7,6),(0,3,2,1),
            (4,5,6,7),(0,4,7,3),(1,2,6,5),
        ]:
            f = bm.faces.new([verts[i] for i in fi])
            f[mat] = mi

    def _oct_column(self, cx, cy, r, z0, z1, mi=0, transform=None):
        """Columna octagonal (aproximación de redondo)."""
        bm    = self.bm
        mat   = self._mat
        segs  = 8
        astep = (2 * math.pi) / segs

        vb, vt = [], []
        for i in range(segs):
            a  = i * astep
            pt_b = Vector((cx + r * math.cos(a),
                            cy + r * math.sin(a), z0))
            pt_t = Vector((cx + r * math.cos(a),
                            cy + r * math.sin(a), z1))
            if transform:
                vb.append(bm.verts.new(transform @ pt_b))
                vt.append(bm.verts.new(transform @ pt_t))
            else:
                vb.append(bm.verts.new(pt_b))
                vt.append(bm.verts.new(pt_t))

        bm.verts.ensure_lookup_table()

        for i in range(segs):
            ni = (i+1) % segs
            f = bm.faces.new([vb[i], vb[ni], vt[ni], vt[i]])
            f[mat] = mi
        try:
            fb = bm.faces.new(vb)
            fb[mat] = mi
            ft = bm.faces.new(list(reversed(vt)))
            ft[mat] = mi
        except Exception:
            pass

    # ────────────────────────────────────────────────────────
    #  POSTE
    # ────────────────────────────────────────────────────────
    def _build_post(self, x_pos, length, transform=None):
        """
        Genera un poste en la posición x_pos con la altura
        total y su remate (cap).
        """
        p    = self.props
        pw   = p.post_width
        pd   = p.post_depth
        h    = p.height + p.z_offset
        he   = p.post_height_extra
        z0   = p.z_offset
        z1   = h + he
        cy   = 0.0
        mi   = p.mat_post
        mi_c = p.mat_cap

        if p.post_round:
            r = pw * 0.5
            self._oct_column(
                x_pos, cy, r, z0, z1, mi, transform
            )
        else:
            self._box(
                x_pos - pw*0.5, x_pos + pw*0.5,
                cy - pd*0.5, cy + pd*0.5,
                z0, z1,
                mi, transform
            )

        # — Cap —
        if p.post_cap != 'NONE':
            self._build_post_cap(
                x_pos, cy, pw, pd, z1, mi_c, transform
            )

    def _build_post_cap(self, cx, cy, pw, pd, z_base, mi, transform):
        """Genera el remate del poste."""
        p    = self.props
        cap  = p.post_cap
        bm   = self.bm
        mat  = self._mat

        if cap == 'FLAT':
            self._box(
                cx - pw*0.55, cx + pw*0.55,
                cy - pd*0.55, cy + pd*0.55,
                z_base, z_base + 0.03,
                mi, transform
            )

        elif cap == 'POINTED':
            # Pirámide
            h_cap = pw * 0.8
            local = [
                Vector((cx - pw*0.55, cy - pd*0.55, z_base)),
                Vector((cx + pw*0.55, cy - pd*0.55, z_base)),
                Vector((cx + pw*0.55, cy + pd*0.55, z_base)),
                Vector((cx - pw*0.55, cy + pd*0.55, z_base)),
                Vector((cx, cy, z_base + h_cap)),
            ]
            if transform:
                bm_v = [bm.verts.new(transform @ v) for v in local]
            else:
                bm_v = [bm.verts.new(v) for v in local]
            bm.verts.ensure_lookup_table()
            # Base
            try:
                f = bm.faces.new(bm_v[:4])
                f[mat] = mi
            except Exception:
                pass
            # Caras laterales de la pirámide
            for i in range(4):
                j = (i+1) % 4
                try:
                    f = bm.faces.new([bm_v[i], bm_v[j], bm_v[4]])
                    f[mat] = mi
                except Exception:
                    pass

        elif cap == 'BALL':
            # Esfera aproximada (icosfera simple con oct)
            r     = pw * 0.55
            z_ctr = z_base + r
            segs  = 6
            rings = 4
            for ring in range(rings):
                a0 = math.pi * ring / rings
                a1 = math.pi * (ring + 1) / rings
                for seg in range(segs):
                    b0 = 2 * math.pi * seg / segs
                    b1 = 2 * math.pi * (seg+1) / segs
                    pts = [
                        Vector((cx + r*math.sin(a0)*math.cos(b0),
                                cy + r*math.sin(a0)*math.sin(b0),
                                z_ctr + r*math.cos(a0))),
                        Vector((cx + r*math.sin(a0)*math.cos(b1),
                                cy + r*math.sin(a0)*math.sin(b1),
                                z_ctr + r*math.cos(a0))),
                        Vector((cx + r*math.sin(a1)*math.cos(b1),
                                cy + r*math.sin(a1)*math.sin(b1),
                                z_ctr + r*math.cos(a1))),
                        Vector((cx + r*math.sin(a1)*math.cos(b0),
                                cy + r*math.sin(a1)*math.sin(b0),
                                z_ctr + r*math.cos(a1))),
                    ]
                    if transform:
                        bm_v = [bm.verts.new(transform @ v) for v in pts]
                    else:
                        bm_v = [bm.verts.new(v) for v in pts]
                    bm.verts.ensure_lookup_table()
                    try:
                        f = bm.faces.new(bm_v)
                        f[mat] = mi
                    except Exception:
                        pass

        elif cap == 'CHAMFER':
            ch = pw * 0.15
            self._box(
                cx - pw*0.55 + ch, cx + pw*0.55 - ch,
                cy - pd*0.55 + ch, cy + pd*0.55 - ch,
                z_base, z_base + ch * 2,
                mi, transform
            )

    # ────────────────────────────────────────────────────────
    #  RIEL (RAIL)
    # ────────────────────────────────────────────────────────
    def _build_rails(self, x_start, x_end, transform=None):
        """
        Genera los rieles horizontales entre dos postes.
        """
        p   = self.props
        if not p.rail_enable:
            return

        rw   = p.rail_width
        rd   = p.rail_depth
        h    = p.height
        z0   = p.z_offset
        mi   = p.mat_rail
        rc   = p.rail_count
        rt   = p.rail_offset_top
        rb   = p.rail_offset_bot
        cy   = 0.0

        # Posición de los rieles distribuidos
        if rc == 1:
            z_positions = [z0 + h * 0.5]
        elif rc == 2:
            z_positions = [
                z0 + rb,
                z0 + h - rt,
            ]
        else:
            z_inner_start = z0 + rb
            z_inner_end   = z0 + h - rt
            z_span        = z_inner_end - z_inner_start
            z_positions   = [
                z_inner_start + i * z_span / (rc - 1)
                for i in range(rc)
            ]

        for z_rail in z_positions:
            if p.rail_profile == 'SQUARE':
                self._box(
                    x_start, x_end,
                    cy - rd*0.5, cy + rd*0.5,
                    z_rail - rw*0.5, z_rail + rw*0.5,
                    mi, transform
                )
            elif p.rail_profile == 'FLAT':
                self._box(
                    x_start, x_end,
                    cy - rw*0.5, cy + rw*0.5,
                    z_rail - rd*0.5, z_rail + rd*0.5,
                    mi, transform
                )
            elif p.rail_profile == 'ROUND':
                # Tubo octagonal
                r_rail = rw * 0.5
                segs   = 6
                astep  = (2 * math.pi) / segs
                bm     = self.bm
                mat    = self._mat

                for xi in [x_start, x_end]:
                    circ_v = []
                    for i in range(segs):
                        a  = i * astep
                        pt = Vector((
                            xi,
                            cy + r_rail * math.cos(a),
                            z_rail + r_rail * math.sin(a)
                        ))
                        if transform:
                            circ_v.append(bm.verts.new(transform @ pt))
                        else:
                            circ_v.append(bm.verts.new(pt))

                bm.verts.ensure_lookup_table()

                n_v = len(circ_v) // 2
                v_start = circ_v[:n_v]
                v_end   = circ_v[n_v:]

                for i in range(n_v):
                    ni = (i+1) % n_v
                    try:
                        f = bm.faces.new([
                            v_start[i], v_start[ni],
                            v_end[ni], v_end[i]
                        ])
                        f[mat] = mi
                    except Exception:
                        pass
                try:
                    bm.faces.new(list(reversed(v_start)))[mat] = mi
                    bm.faces.new(v_end)[mat] = mi
                except Exception:
                    pass

    # ────────────────────────────────────────────────────────
    #  PICKET (tabla individual)
    # ────────────────────────────────────────────────────────
    def _build_picket(self, x_center, transform=None):
        """
        Genera una tabla/picket en la posición x_center.
        Aplica el estilo de remate en la punta.
        """
        p   = self.props
        pw  = p.picket_width
        pt  = p.picket_thickness
        h   = p.height
        z0  = p.z_offset + p.picket_z_offset
        z1  = p.z_offset + h
        cy  = 0.0
        mi  = p.mat_picket
        top = p.picket_top
        bm  = self.bm
        mat = self._mat

        if top == 'FLAT':
            self._box(
                x_center - pw*0.5, x_center + pw*0.5,
                cy - pt*0.5, cy + pt*0.5,
                z0, z1,
                mi, transform
            )

        elif top == 'POINTED':
            # Cuerpo + punta triangular
            point_h = pw * 0.6
            self._box(
                x_center - pw*0.5, x_center + pw*0.5,
                cy - pt*0.5, cy + pt*0.5,
                z0, z1 - point_h,
                mi, transform
            )
            # Punta (prisma triangular)
            local = [
                Vector((x_center - pw*0.5, cy - pt*0.5, z1 - point_h)),
                Vector((x_center + pw*0.5, cy - pt*0.5, z1 - point_h)),
                Vector((x_center + pw*0.5, cy + pt*0.5, z1 - point_h)),
                Vector((x_center - pw*0.5, cy + pt*0.5, z1 - point_h)),
                Vector((x_center, cy - pt*0.3, z1)),
                Vector((x_center, cy + pt*0.3, z1)),
            ]
            if transform:
                bv = [bm.verts.new(transform @ v) for v in local]
            else:
                bv = [bm.verts.new(v) for v in local]
            bm.verts.ensure_lookup_table()
            try:
                bm.faces.new([bv[0], bv[1], bv[2], bv[3]])[mat] = mi
                bm.faces.new([bv[0], bv[1], bv[4]])[mat] = mi
                bm.faces.new([bv[2], bv[3], bv[5]])[mat] = mi
                bm.faces.new([bv[1], bv[2], bv[5], bv[4]])[mat] = mi
                bm.faces.new([bv[0], bv[5], bv[3]])[mat] = mi
                bm.faces.new([bv[0], bv[4], bv[5]])[mat] = mi
            except Exception:
                pass

        elif top == 'DOG_EAR':
            # Esquinas cortadas en diagonal
            cut = pw * 0.25
            self._box(
                x_center - pw*0.5, x_center + pw*0.5,
                cy - pt*0.5, cy + pt*0.5,
                z0, z1 - cut,
                mi, transform
            )
            # Trapecio superior
            local = [
                Vector((x_center - pw*0.5 + cut, cy - pt*0.5, z1 - cut)),
                Vector((x_center + pw*0.5 - cut, cy - pt*0.5, z1 - cut)),
                Vector((x_center + pw*0.5 - cut, cy + pt*0.5, z1 - cut)),
                Vector((x_center - pw*0.5 + cut, cy + pt*0.5, z1 - cut)),
                Vector((x_center - pw*0.5 + cut, cy - pt*0.5, z1)),
                Vector((x_center + pw*0.5 - cut, cy - pt*0.5, z1)),
                Vector((x_center + pw*0.5 - cut, cy + pt*0.5, z1)),
                Vector((x_center - pw*0.5 + cut, cy + pt*0.5, z1)),
            ]
            if transform:
                bv = [bm.verts.new(transform @ v) for v in local]
            else:
                bv = [bm.verts.new(v) for v in local]
            bm.verts.ensure_lookup_table()
            for fi in [
                (0,1,5,4),(2,3,7,6),(0,3,2,1),
                (4,5,6,7),(0,4,7,3),(1,2,6,5)
            ]:
                try:
                    bm.faces.new([bv[i] for i in fi])[mat] = mi
                except Exception:
                    pass

        elif top == 'FRENCH':
            # Remate redondeado (aproximado con escalones)
            r     = pw * 0.5
            segs  = 4
            self._box(
                x_center - pw*0.5, x_center + pw*0.5,
                cy - pt*0.5, cy + pt*0.5,
                z0, z1 - r,
                mi, transform
            )
            # Semicírculo en la punta
            z_arc_ctr = z1 - r
            for i in range(segs):
                a0 = math.pi * i / segs
                a1 = math.pi * (i+1) / segs
                rx0 = x_center + r * math.cos(math.pi - a0)
                rz0 = z_arc_ctr + r * math.sin(math.pi - a0)
                rx1 = x_center + r * math.cos(math.pi - a1)
                rz1 = z_arc_ctr + r * math.sin(math.pi - a1)

                self._box(
                    min(rx0, rx1), max(rx0, rx1),
                    cy - pt*0.5, cy + pt*0.5,
                    min(rz0, rz1), max(rz0, rz1),
                    mi, transform
                )

    # ────────────────────────────────────────────────────────
    #  BALUSTER METÁLICO
    # ────────────────────────────────────────────────────────
    def _build_baluster(self, x_pos, transform=None):
        """Balaustre metálico para barandilla."""
        p  = self.props
        bs = p.baluster_size
        h  = p.height
        z0 = p.z_offset
        z1 = p.z_offset + h
        cy = 0.0
        mi = p.mat_rail

        if p.baluster_round:
            self._oct_column(
                x_pos, cy, bs*0.5, z0, z1, mi, transform
            )
        else:
            self._box(
                x_pos - bs*0.5, x_pos + bs*0.5,
                cy - bs*0.5, cy + bs*0.5,
                z0, z1,
                mi, transform
            )

    # ────────────────────────────────────────────────────────
    #  LADRILLO
    # ────────────────────────────────────────────────────────
    def _build_bricks(self, x_start, x_end,
                       wall_depth, transform=None):
        """
        Genera un muro de ladrillos en aparejo inglés.
        x_start → x_end: largo del muro
        wall_depth: espesor del muro
        """
        p   = self.props
        bl  = p.brick_length
        bh  = p.brick_height
        bd  = p.brick_depth
        mg  = p.mortar_gap
        h   = p.height
        z0  = p.z_offset
        mi  = p.mat_brick
        mm  = p.mat_mortar

        # Número de hiladas
        n_rows = max(1, int(h / (bh + mg)))
        # Número de ladrillos por hilada
        length = x_end - x_start
        n_cols = max(1, int(length / (bl + mg)))

        for row in range(n_rows):
            z_row = z0 + row * (bh + mg)
            # Aparejo: hiladas pares desplazadas la mitad
            offset = (bl * 0.5 + mg * 0.5) if row % 2 == 1 else 0.0

            for col in range(n_cols + 1):
                x0_br = x_start + col * (bl + mg) - offset
                x1_br = x0_br + bl

                # Recortar si sale del rango
                x0_br = max(x0_br, x_start)
                x1_br = min(x1_br, x_end)
                if x1_br - x0_br < 0.01:
                    continue

                self._box(
                    x0_br, x1_br,
                    0.0, bd,
                    z_row, z_row + bh,
                    mi, transform
                )

        # — Remate superior (hilada de remate) —
        z_top = z0 + n_rows * (bh + mg)
        self._box(
            x_start, x_end,
            -mg, bd + mg,
            z_top, z_top + bh * 0.5,
            mm, transform
        )

    # ────────────────────────────────────────────────────────
    #  PANEL DE VIDRIO
    # ────────────────────────────────────────────────────────
    def _build_glass_panel(self, x_start, x_end, transform=None):
        """Panel de vidrio + postes laterales."""
        p   = self.props
        gt  = p.glass_thickness
        gh  = p.glass_height
        pw  = p.post_width
        pd  = p.post_depth
        z0  = p.z_offset
        z1  = z0 + gh
        cy  = 0.0
        mi  = p.mat_glass
        mi_p = p.mat_post

        # Vidrio
        self._box(
            x_start + pw * 0.5, x_end - pw * 0.5,
            cy - gt*0.5, cy + gt*0.5,
            z0, z1,
            mi, transform
        )

        # Pasamanos superior
        if p.top_rail_enable:
            rw = p.rail_width
            rd = p.rail_depth
            self._box(
                x_start, x_end,
                cy - rw*0.5, cy + rw*0.5,
                z1, z1 + rd,
                mi_p, transform
            )

    # ────────────────────────────────────────────────────────
    #  MALLA CICLÓNICA (CHAIN LINK) — representación visual
    # ────────────────────────────────────────────────────────
    def _build_chain_link(self, x_start, x_end, transform=None):
        """
        Genera una aproximación visual de malla ciclónica.
        Las celdas se representan como rombos de alambre.
        (Aproximación en bmesh; para producción se puede
         usar un modifier Array + curve.)
        """
        p    = self.props
        cs   = p.chain_cell_size
        wr   = p.chain_wire_r
        h    = p.height
        z0   = p.z_offset
        cy   = 0.0
        mi   = p.mat_rail
        bm   = self.bm
        mat  = self._mat

        length = x_end - x_start
        n_cols = max(1, int(length / cs))
        n_rows = max(1, int(h / cs))

        col_step = length / n_cols
        row_step = h / n_rows

        # — Alambres verticales diagonales —
        for col in range(n_cols + 1):
            x_base = x_start + col * col_step
            for row in range(n_rows):
                z_base = z0 + row * row_step
                # Diagonal izquierda→derecha
                xs = x_base
                xe = x_base + col_step * 0.5
                zs = z_base
                ze = z_base + row_step

                self._box(
                    xs - wr, xs + wr,
                    cy - wr, cy + wr,
                    zs, ze,
                    mi, transform
                )

        # — Rieles de borde (top + bottom + tensores) —
        self._box(
            x_start, x_end,
            cy - wr*2, cy + wr*2,
            z0, z0 + wr*3,
            mi, transform
        )
        self._box(
            x_start, x_end,
            cy - wr*2, cy + wr*2,
            z0 + h - wr*3, z0 + h,
            mi, transform
        )

    # ────────────────────────────────────────────────────────
    #  SPLIT RAIL (Valla rústica de troncos)
    # ────────────────────────────────────────────────────────
    def _build_split_rail(self, x_start, x_end, transform=None):
        """
        Genera una valla rústica de troncos:
        - Postes cilíndricos robustos
        - Rieles horizontales que se encajan en muescas
        """
        p   = self.props
        pw  = p.post_width * 1.5    # Postes más gruesos
        h   = p.height
        z0  = p.z_offset
        cy  = 0.0
        mi  = p.mat_post
        mi_r = p.mat_rail

        # Rieles: 2 o 3 horizontales de sección ovalada
        rc  = min(p.rail_count, 3)
        rw  = pw * 0.5
        rd  = pw * 0.4

        if rc == 2:
            z_rails = [z0 + h * 0.30, z0 + h * 0.75]
        elif rc == 3:
            z_rails = [z0 + h * 0.20, z0 + h * 0.55, z0 + h * 0.85]
        else:
            z_rails = [z0 + h * 0.50]

        for z_rail in z_rails:
            self._box(
                x_start, x_end,
                cy - rw * 0.5, cy + rw * 0.5,
                z_rail - rd * 0.5, z_rail + rd * 0.5,
                mi_r, transform
            )

    # ────────────────────────────────────────────────────────
    #  SEGMENTO — núcleo común
    # ────────────────────────────────────────────────────────
    def _build_segment(self, x_start, seg_length, transform=None):
        """
        Construye un segmento de valla de longitud seg_length
        a partir de x_start, aplicando el tipo seleccionado.
        """
        p      = self.props
        x_end  = x_start + seg_length
        pw     = p.post_width
        ps     = p.post_spacing

        # — Postes en este segmento —
        if p.post_enable:
            n_posts  = max(2, int(seg_length / ps) + 1)
            post_sep = seg_length / (n_posts - 1)
            for i in range(n_posts):
                xp = x_start + i * post_sep
                self._build_post(xp, seg_length, transform)

        # — Contenido según tipo —
        if p.fence_type in ('WOOD_PICKET', 'CUSTOM'):
            # Rieles
            self._build_rails(x_start, x_end, transform)

            # Pickets
            if p.picket_enable:
                pitch = p.picket_width + p.picket_gap
                n_pk  = max(1, int(seg_length / pitch))
                for i in range(n_pk):
                    xp = x_start + (i + 0.5) * (seg_length / n_pk)
                    self._build_picket(xp, transform)

        elif p.fence_type == 'WOOD_PRIVACY':
            # Sin hueco entre tablas
            self._build_rails(x_start, x_end, transform)
            if p.picket_enable:
                pw_s  = p.picket_width
                n_pk  = max(1, int(seg_length / pw_s))
                for i in range(n_pk):
                    xp = x_start + (i + 0.5) * (seg_length / n_pk)
                    self._build_picket(xp, transform)

        elif p.fence_type == 'METAL_RAIL':
            # Rieles + balaustres
            self._build_rails(x_start, x_end, transform)
            bs    = p.baluster_spacing
            n_bal = max(1, int(seg_length / bs))
            for i in range(n_bal):
                xb = x_start + (i + 0.5) * (seg_length / n_bal)
                self._build_baluster(xb, transform)

        elif p.fence_type == 'CHAIN_LINK':
            self._build_rails(x_start, x_end, transform)
            self._build_chain_link(x_start, x_end, transform)

        elif p.fence_type == 'SPLIT_RAIL':
            self._build_split_rail(x_start, x_end, transform)

        elif p.fence_type == 'BRICK_WALL':
            bd = p.brick_depth
            self._build_bricks(x_start, x_end, bd, transform)

        elif p.fence_type == 'GLASS_RAIL':
            self._build_rails(x_start, x_end, transform)
            self._build_glass_panel(x_start, x_end, transform)

    # ────────────────────────────────────────────────────────
    #  GENERATE — multi-segmento
    # ────────────────────────────────────────────────────────
    def generate(self):
        """
        Genera todos los segmentos de la valla con sus
        rotaciones acumuladas.
        """
        p = self.props

        x_cursor = 0.0
        angle    = 0.0   # ángulo acumulado global

        for seg in p.parts:
            if not seg.enabled:
                continue

            # Transformación del segmento actual
            rot   = Matrix.Rotation(angle, 4, 'Z')
            trans = Matrix.Translation(
                Vector((x_cursor, 0.0, 0.0))
            )
            # Para segmentos con ángulo, usamos la rotación
            transform = trans @ rot

            self._build_segment(0.0, seg.length, transform)

            # Avanzar en la dirección actual
            x_cursor += seg.length * math.cos(angle)
            angle    += seg.angle

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
def _find_fence_object(props):
    name = props.object_name
    if name and name in bpy.data.objects:
        return bpy.data.objects[name]
    for obj in bpy.data.objects:
        if (obj.type == 'MESH'
                and hasattr(obj, AF_FENCE_PROP)
                and getattr(obj, AF_FENCE_PROP) is props):
            return obj
    return None


def af_fence_update(self, context):
    obj = _find_fence_object(self)
    if obj is None:
        obj = context.active_object
    if obj is None or obj.type != 'MESH':
        return
    props = getattr(obj, AF_FENCE_PROP, None)
    if props is None or not props.is_af_fence:
        return
    _rebuild_fence_mesh(obj, props)


def af_fence_parts_update(self, context):
    obj = _find_fence_object(self)
    if obj is None:
        obj = context.active_object
    if obj is None:
        return
    props = obj.archiforge_fence
    target = props.n_parts

    while len(props.parts) < target:
        seg        = props.parts.add()
        seg.length = 3.0
        seg.angle  = 0.0
        seg.enabled = True

    while len(props.parts) > target:
        props.parts.remove(len(props.parts) - 1)

    _rebuild_fence_mesh(obj, props)


def _rebuild_fence_mesh(obj, props):
    gen = AF_FenceGenerator(props)
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


def _setup_fence_materials(obj):
    mat_names = [
        "AF.Fence.Wood",   # 0 post
        "AF.Fence.Wood",   # 1 rail
        "AF.Fence.Wood",   # 2 picket
        "AF.Fence.Wood",   # 3 cap
        "AF.Window.Glass", # 4 glass
        "AF.Wall.Brick",   # 5 brick
        "AF.Wall.Plaster", # 6 mortar
    ]
    af_material.ensure_af_materials_for_object(obj, mat_names)


def _create_fence_object(context, name="AF_Fence"):
    me  = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, me)
    context.collection.objects.link(obj)
    context.view_layer.objects.active = obj
    obj.select_set(True)

    props              = obj.archiforge_fence
    props.is_af_fence  = True
    props.object_name  = obj.name

    seg        = props.parts.add()
    seg.length = 3.0
    seg.angle  = 0.0
    seg.enabled = True

    _setup_fence_materials(obj)
    return obj, props


# ════════════════════════════════════════════════════════════
#  OPERADORES
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_OT_fence(Operator):
    bl_idname      = "archiforge.fence"
    bl_label       = "Add AF Fence"
    bl_description = "Add a parametric ArchiForge fence"
    bl_options     = {'REGISTER', 'UNDO'}

    fence_type : EnumProperty(
        name="Type", items=AF_FENCE_TYPES, default='WOOD_PICKET',
    )
    height : FloatProperty(
        name="Height", default=1.20, min=0.10, unit='LENGTH',
    )
    length : FloatProperty(
        name="Length", default=3.0, min=0.1, unit='LENGTH',
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        col = layout.column(align=True)
        col.label(text="New Fence", **_icon("fence", 'MESH_PLANE'))
        col.prop(self, "fence_type")
        col.separator()
        col.prop(self, "height")
        col.prop(self, "length")

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        obj, props = _create_fence_object(context, "AF_Fence")
        props.fence_type     = self.fence_type
        props.height         = self.height
        props.parts[0].length = self.length
        _rebuild_fence_mesh(obj, props)
        self.report({'INFO'}, _tr("Fence created: {}").format(obj.name))
        return {'FINISHED'}


class ARCHIFORGE_OT_fence_update(Operator):
    bl_idname  = "archiforge.fence_update"
    bl_label   = "Update Fence"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj is not None and obj.type == 'MESH'
            and hasattr(obj, AF_FENCE_PROP)
            and obj.archiforge_fence.is_af_fence
        )

    def execute(self, context):
        obj = context.active_object
        _rebuild_fence_mesh(obj, obj.archiforge_fence)
        self.report({'INFO'}, _tr("Fence updated"))
        return {'FINISHED'}


class ARCHIFORGE_OT_fence_add_segment(Operator):
    bl_idname  = "archiforge.fence_add_segment"
    bl_label   = "Add Segment"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj is not None
            and hasattr(obj, AF_FENCE_PROP)
            and obj.archiforge_fence.is_af_fence
        )

    def execute(self, context):
        props = context.active_object.archiforge_fence
        props.n_parts += 1
        return {'FINISHED'}


class ARCHIFORGE_OT_fence_remove_segment(Operator):
    bl_idname  = "archiforge.fence_remove_segment"
    bl_label   = "Remove Segment"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj is not None
            and hasattr(obj, AF_FENCE_PROP)
            and obj.archiforge_fence.is_af_fence
            and obj.archiforge_fence.n_parts > 1
        )

    def execute(self, context):
        props = context.active_object.archiforge_fence
        props.n_parts -= 1
        return {'FINISHED'}


class ARCHIFORGE_OT_fence_from_curve(Operator):
    """Crea una valla siguiendo una curva seleccionada."""
    bl_idname  = "archiforge.fence_from_curve"
    bl_label   = "Fence from Curve"
    bl_options = {'REGISTER', 'UNDO'}

    fence_type : EnumProperty(
        name="Type", items=AF_FENCE_TYPES, default='WOOD_PICKET',
    )
    height : FloatProperty(
        name="Height", default=1.20, min=0.10, unit='LENGTH',
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
        col.prop(self, "fence_type")
        col.prop(self, "height")

    def execute(self, context):
        curve = context.active_object

        # Extraer segmentos de la curva
        mw     = curve.matrix_world
        points = []

        for spline in curve.data.splines:
            if spline.type == 'BEZIER':
                for bp in spline.bezier_points:
                    points.append(mw @ bp.co)
            else:
                for bp in spline.points:
                    points.append(mw @ Vector(bp.co[:3]))

        if len(points) < 2:
            self.report({'ERROR'}, _tr("Curve needs at least 2 points"))
            return {'CANCELLED'}

        bpy.ops.object.select_all(action='DESELECT')
        obj, props = _create_fence_object(context, "AF_Fence")
        props.fence_type = self.fence_type
        props.height     = self.height

        # Crear segmentos desde los puntos de la curva
        props.parts.clear()
        props.n_parts = len(points) - 1

        prev_angle = 0.0
        for i in range(len(points) - 1):
            seg_vec = points[i+1] - points[i]
            seg_len = seg_vec.length
            seg_ang = math.atan2(seg_vec.y, seg_vec.x)

            rel_angle = seg_ang - prev_angle
            # Normalizar ángulo
            while rel_angle >  math.pi: rel_angle -= 2 * math.pi
            while rel_angle < -math.pi: rel_angle += 2 * math.pi

            seg           = props.parts.add()
            seg.length    = max(0.1, seg_len)
            seg.angle     = rel_angle if i > 0 else 0.0
            seg.enabled   = True
            prev_angle    = seg_ang

        # Posicionar el objeto en el primer punto
        obj.location = points[0]

        _rebuild_fence_mesh(obj, props)
        self.report({'INFO'}, _tr("Fence from curve '{}'").format(curve.name))
        return {'FINISHED'}


# ════════════════════════════════════════════════════════════
#  PANEL
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_PT_fence(Panel):
    bl_label       = "Fence Properties"
    bl_idname      = "ARCHIFORGE_PT_fence"
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
            and hasattr(obj, AF_FENCE_PROP)
            and obj.archiforge_fence.is_af_fence
        )

    def draw_header(self, context):
        self.layout.label(text="", **_icon("fence", 'MESH_PLANE'))

    def draw(self, context):
        props  = context.active_object.archiforge_fence
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        # ── Tipo ─────────────────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Type", icon='MODIFIER')
        col.prop(props, "fence_type", text="")

        # ── Dimensiones ───────────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Dimensions", icon='ARROW_LEFTRIGHT')
        col.prop(props, "height")
        col.prop(props, "z_offset")

        # ── Segmentos ─────────────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        row = col.row(align=True)
        row.label(text="Segments", icon='MESH_DATA')
        row.prop(props, "n_parts", text="")
        row = col.row(align=True)
        row.operator(
            "archiforge.fence_add_segment",
            text="Add", icon='ADD'
        )
        row.operator(
            "archiforge.fence_remove_segment",
            text="Remove", icon='REMOVE'
        )
        col.separator(factor=0.3)
        for i, seg in enumerate(props.parts):
            sb = col.box()
            row = sb.row(align=True)
            row.prop(
                seg, "enabled",
                text=f"Seg {i+1}",
                icon='CHECKMARK' if seg.enabled else 'PANEL_CLOSE',
                toggle=True,
            )
            if seg.enabled:
                inn = sb.column(align=True)
                inn.prop(seg, "length")
                if i > 0:
                    inn.prop(seg, "angle")

        # ── Postes ────────────────────────────────────────────
        box = layout.box()
        row = box.row(align=True)
        row.prop(
            props, "post_enable",
            text="Posts",
            icon='TRIA_DOWN' if props.post_enable else 'TRIA_RIGHT',
            toggle=True, emboss=False,
        )
        if props.post_enable:
            col = box.column(align=True)
            col.prop(props, "post_width")
            col.prop(props, "post_depth")
            col.prop(props, "post_height_extra")
            col.prop(props, "post_spacing")
            col.prop(props, "post_cap")
            col.prop(props, "post_round")

        # ── Rieles ────────────────────────────────────────────
        box = layout.box()
        row = box.row(align=True)
        row.prop(
            props, "rail_enable",
            text="Rails",
            icon='TRIA_DOWN' if props.rail_enable else 'TRIA_RIGHT',
            toggle=True, emboss=False,
        )
        if props.rail_enable:
            col = box.column(align=True)
            col.prop(props, "rail_count")
            col.prop(props, "rail_profile")
            col.prop(props, "rail_width")
            col.prop(props, "rail_depth")
            col.prop(props, "rail_offset_top")
            col.prop(props, "rail_offset_bot")

        # ── Tablas / Pickets ──────────────────────────────────
        if props.fence_type in (
            'WOOD_PICKET', 'WOOD_PRIVACY', 'CUSTOM'
        ):
            box = layout.box()
            row = box.row(align=True)
            row.prop(
                props, "picket_enable",
                text="Pickets / Boards",
                icon='TRIA_DOWN' if props.picket_enable else 'TRIA_RIGHT',
                toggle=True, emboss=False,
            )
            if props.picket_enable:
                col = box.column(align=True)
                col.prop(props, "picket_width")
                col.prop(props, "picket_thickness")
                col.prop(props, "picket_gap")
                col.prop(props, "picket_top")
                col.prop(props, "picket_z_offset")

        # ── Metal Rail ────────────────────────────────────────
        if props.fence_type == 'METAL_RAIL':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Balusters", icon='PARTICLE_POINT')
            col.prop(props, "baluster_size")
            col.prop(props, "baluster_spacing")
            col.prop(props, "baluster_round")

        # ── Glass Rail ────────────────────────────────────────
        if props.fence_type == 'GLASS_RAIL':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Glass Panel", icon='MATERIAL')
            col.prop(props, "glass_thickness")
            col.prop(props, "glass_height")
            col.prop(props, "top_rail_enable")

        # ── Chain Link ────────────────────────────────────────
        if props.fence_type == 'CHAIN_LINK':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Chain Link", icon='MOD_WIREFRAME')
            col.prop(props, "chain_cell_size")
            col.prop(props, "chain_wire_r")

        # ── Brick Wall ────────────────────────────────────────
        if props.fence_type == 'BRICK_WALL':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Brick Settings", icon='MESH_GRID')
            col.prop(props, "brick_length")
            col.prop(props, "brick_height")
            col.prop(props, "brick_depth")
            col.prop(props, "mortar_gap")

        # ── Materiales ────────────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Materials", icon='MATERIAL')
        if props.post_enable:
            col.prop(props, "mat_post",   text="Post")
            col.prop(props, "mat_cap",    text="Post Cap")
        if props.rail_enable:
            col.prop(props, "mat_rail",   text="Rail")
        if props.fence_type in (
            'WOOD_PICKET', 'WOOD_PRIVACY', 'CUSTOM'
        ):
            col.prop(props, "mat_picket", text="Picket")
        if props.fence_type == 'GLASS_RAIL':
            col.prop(props, "mat_glass",  text="Glass")
        if props.fence_type == 'BRICK_WALL':
            col.prop(props, "mat_brick",  text="Brick")
            col.prop(props, "mat_mortar", text="Mortar")

        # ── Acciones ──────────────────────────────────────────
        layout.separator()
        layout.operator(
            "archiforge.fence_update",
            text="Force Update",
            icon='FILE_REFRESH',
        )


# ════════════════════════════════════════════════════════════
#  REGISTRO
# ════════════════════════════════════════════════════════════
classes = [
    AF_FenceSegment,
    AF_FenceProperties,

    ARCHIFORGE_OT_fence,
    ARCHIFORGE_OT_fence_update,
    ARCHIFORGE_OT_fence_add_segment,
    ARCHIFORGE_OT_fence_remove_segment,
    ARCHIFORGE_OT_fence_from_curve,

    ARCHIFORGE_PT_fence,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Object.archiforge_fence = PointerProperty(
        type        = AF_FenceProperties,
        name        = "ArchiForge Fence",
        description = "ArchiForge parametric fence properties",
    )
    print("[ArchiForge] ✅ af_fence — registered")


def unregister():
    if hasattr(bpy.types.Object, "archiforge_fence"):
        del bpy.types.Object.archiforge_fence

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    print("[ArchiForge] 🔴 af_fence — unregistered")