# -*- coding: utf-8 -*-

# ╔══════════════════════════════════════════════════════════╗
# ║         ARCHIFORGE — af_slab.py                         ║
# ║         Losas / Forjados paramétricos Blender 3.3 LTS   ║
# ║         GPL v3 — ArchiForge Devs                        ║
# ╚══════════════════════════════════════════════════════════╝
# v1.1 — parche Blender 3.3: bmesh posicional + material_index nativo
# v1.2 — sistemas: MACIZA / ALIGERADA / PLACA_FACIL / STEELDECK

# <pep8 compliant>

# ════════════════════════════════════════════════════════════
#  ¿QUÉ HACE ESTE MÓDULO?
#
#  Genera losas / forjados / techos planos paramétricos:
#  - Losa rectangular simple
#  - Losa desde curva (polyline / curve)
#  - Losa desde muro (floor o ceiling)
#  - Espesor, offset, bisel de borde
#  - Capa superior / inferior (acabado)
#  - Huecos rectangulares (patios / cajas de escalera)
#
#  Tipos:
#  - RECTANGLE  : Losa rectangular
#  - FROM_CURVE : Desde curva seleccionada
#  - FROM_WALL  : Desde contorno de muro AF
#  - CUSTOM     : Polígono editable por vértices
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
    FloatVectorProperty,
    EnumProperty,
    CollectionProperty,
    PointerProperty,
)

from . import af_material
from .af_floor_geometry import normalize_outline
from .af_outline_draw import AF_OutlineDrawMixin

try:
    from .af_i18n import tr_report as _tr
except ImportError:  # pragma: no cover - fuera del paquete
    def _tr(text):
        return text


# ════════════════════════════════════════════════════════════
#  CONSTANTES
# ════════════════════════════════════════════════════════════
AF_SLAB_PROP = "archiforge_slab"
_SLAB_UPDATE_SUSPENDED = False

AF_SLAB_TYPES = [
    ('RECTANGLE', "Rectangle", "Simple rectangular slab",           'MESH_PLANE', 0),
    ('FROM_CURVE', "From Curve", "Slab from selected curve outline", 'CURVE_DATA', 1),
    ('FROM_WALL', "From Wall", "Slab from ArchiForge wall outline", 'SNAP_FACE',  2),
    ('CUSTOM',    "Custom",    "Custom polygon slab",               'MESH_DATA',  3),
]

AF_SLAB_USE = [
    ('FLOOR',   "Floor",   "Floor slab / forjado"),
    ('CEILING', "Ceiling", "Ceiling slab"),
    ('ROOF',    "Roof",    "Flat roof slab"),
    ('GENERIC', "Generic", "Generic slab"),
]

AF_SLAB_SYSTEMS = [
    ('MACIZA',      "Maciza",      "Losa maciza en concreto"),
    ('ALIGERADA',   "Aligerada",   "Viguetas + casetones + torta"),
    ('PLACA_FACIL', "Placa facil", "Vigueta pretensada + bloquelon"),
    ('STEELDECK',   "Steeldeck",   "Lamina colaborante + torta"),
]


# ════════════════════════════════════════════════════════════
#  PROPERTYGROUP — Vértice de contorno custom
# ════════════════════════════════════════════════════════════
class AF_SlabVertex(PropertyGroup):
    """Vértice 2D del contorno de la losa custom."""

    x : FloatProperty(
        name="X", default=0.0, unit='LENGTH',
        update=lambda s, c: af_slab_update(s, c),
    )
    y : FloatProperty(
        name="Y", default=0.0, unit='LENGTH',
        update=lambda s, c: af_slab_update(s, c),
    )


# ════════════════════════════════════════════════════════════
#  PROPERTYGROUP — Hueco en la losa
# ════════════════════════════════════════════════════════════
class AF_SlabHole(PropertyGroup):
    """Hueco rectangular en la losa (patio, caja de escalera)."""

    enabled : BoolProperty(
        name="Enabled", default=True,
        update=lambda s, c: af_slab_update(s, c),
    )
    name : StringProperty(name="Name", default="Hole")

    # Centro del hueco en coords locales de la losa
    center_x : FloatProperty(
        name="Center X", default=0.0, unit='LENGTH',
        update=lambda s, c: af_slab_update(s, c),
    )
    center_y : FloatProperty(
        name="Center Y", default=0.0, unit='LENGTH',
        update=lambda s, c: af_slab_update(s, c),
    )
    width : FloatProperty(
        name="Width", default=1.0, min=0.1, unit='LENGTH',
        update=lambda s, c: af_slab_update(s, c),
    )
    depth : FloatProperty(
        name="Depth", default=1.0, min=0.1, unit='LENGTH',
        update=lambda s, c: af_slab_update(s, c),
    )
    rotation : FloatProperty(
        name="Rotation", default=0.0, subtype='ANGLE',
        update=lambda s, c: af_slab_update(s, c),
    )


# ════════════════════════════════════════════════════════════
#  PROPERTYGROUP — Losa completa
# ════════════════════════════════════════════════════════════
class AF_SlabProperties(PropertyGroup):

    is_af_slab : BoolProperty(
        name="Is ArchiForge Slab", default=True, options={'HIDDEN'},
    )
    object_name : StringProperty(
        name="Object Name", default="", options={'HIDDEN'},
    )

    # ── Tipo / uso ───────────────────────────────────────────
    slab_type : EnumProperty(
        name="Type", items=AF_SLAB_TYPES, default='RECTANGLE',
        update=lambda s, c: af_slab_update(s, c),
    )
    slab_use : EnumProperty(
        name="Use", items=AF_SLAB_USE, default='FLOOR',
        update=lambda s, c: af_slab_update(s, c),
    )
    slab_system : EnumProperty(
        name="System", items=AF_SLAB_SYSTEMS, default='MACIZA',
        update=lambda s, c: af_slab_system_update(s, c),
    )
    joist_width : FloatProperty(
        name="Joist W", default=0.10, min=0.05, max=0.30,
        unit='LENGTH', update=lambda s, c: af_slab_update(s, c),
    )
    joist_depth : FloatProperty(
        name="Joist H", default=0.25, min=0.10, max=0.60,
        unit='LENGTH', update=lambda s, c: af_slab_update(s, c),
    )
    joist_spacing : FloatProperty(
        name="Joist @", default=0.60, min=0.30, max=1.20,
        unit='LENGTH', update=lambda s, c: af_slab_update(s, c),
    )
    topping : FloatProperty(
        name="Topping", default=0.05, min=0.03, max=0.15,
        unit='LENGTH', update=lambda s, c: af_slab_update(s, c),
    )
    deck_height : FloatProperty(
        name="Deck H", default=0.075, min=0.04, max=0.12,
        unit='LENGTH', update=lambda s, c: af_slab_update(s, c),
    )
    deck_pitch : FloatProperty(
        name="Deck Pitch", default=0.30, min=0.15, max=0.60,
        unit='LENGTH', update=lambda s, c: af_slab_update(s, c),
    )

    # ── Dimensiones rectángulo ───────────────────────────────
    width : FloatProperty(
        name="Width (X)", description="Slab width",
        default=4.0, min=0.1, max=200.0, unit='LENGTH',
        update=lambda s, c: af_slab_update(s, c),
    )
    depth : FloatProperty(
        name="Depth (Y)", description="Slab depth",
        default=3.0, min=0.1, max=200.0, unit='LENGTH',
        update=lambda s, c: af_slab_update(s, c),
    )

    # ── Espesor y altura ─────────────────────────────────────
    thickness : FloatProperty(
        name="Thickness", description="Slab thickness",
        default=0.20, min=0.02, max=2.0, unit='LENGTH',
        update=lambda s, c: af_slab_update(s, c),
    )
    z_offset : FloatProperty(
        name="Z Offset", description="Vertical offset of slab top surface",
        default=0.0, min=-50.0, max=50.0, unit='LENGTH',
        update=lambda s, c: af_slab_update(s, c),
    )

    # ── Acabado superior / inferior ──────────────────────────
    top_finish_enable : BoolProperty(
        name="Top Finish", default=False,
        update=lambda s, c: af_slab_update(s, c),
    )
    top_finish_thickness : FloatProperty(
        name="Top Finish Thickness",
        default=0.02, min=0.005, max=0.20, unit='LENGTH',
        update=lambda s, c: af_slab_update(s, c),
    )
    bottom_finish_enable : BoolProperty(
        name="Bottom Finish", default=False,
        update=lambda s, c: af_slab_update(s, c),
    )
    bottom_finish_thickness : FloatProperty(
        name="Bottom Finish Thickness",
        default=0.015, min=0.005, max=0.20, unit='LENGTH',
        update=lambda s, c: af_slab_update(s, c),
    )

    # ── Bordes ───────────────────────────────────────────────
    edge_bevel : FloatProperty(
        name="Edge Bevel",
        description="Slight bevel on top outer edge",
        default=0.0, min=0.0, max=0.10, unit='LENGTH',
        update=lambda s, c: af_slab_update(s, c),
    )
    overhang : FloatProperty(
        name="Overhang",
        description="Extra extension beyond base outline",
        default=0.0, min=0.0, max=2.0, unit='LENGTH',
        update=lambda s, c: af_slab_update(s, c),
    )

    # ── Contorno custom ──────────────────────────────────────
    vertices : CollectionProperty(type=AF_SlabVertex)
    n_vertices : IntProperty(
        name="Vertices", default=4, min=3, max=64,
        update=lambda s, c: af_slab_verts_update(s, c),
    )

    # ── Huecos ───────────────────────────────────────────────
    holes : CollectionProperty(type=AF_SlabHole)
    n_holes : IntProperty(
        name="Holes", default=0, min=0, max=16,
        update=lambda s, c: af_slab_holes_update(s, c),
    )
    active_hole : IntProperty(name="Active Hole", default=0, min=0)

    # ── Origen / alineación ──────────────────────────────────
    origin_mode : EnumProperty(
        name="Origin",
        items=[
            ('CENTER', "Center", "Origin at slab center"),
            ('CORNER', "Corner", "Origin at min X/Y corner"),
        ],
        default='CORNER',
        update=lambda s, c: af_slab_update(s, c),
    )

    # ── Referencias ──────────────────────────────────────────
    source_curve : StringProperty(
        name="Source Curve", default="",
        description="Name of curve used for FROM_CURVE",
    )
    source_wall : StringProperty(
        name="Source Wall", default="",
        description="Name of wall used for FROM_WALL",
    )
    is_ceiling : BoolProperty(
        name="Is Ceiling", default=False, options={'HIDDEN'},
    )

    # ── Materiales ───────────────────────────────────────────
    mat_core   : IntProperty(name="Core Material",   default=0, min=0)
    mat_top    : IntProperty(name="Top Finish Mat",  default=1, min=0)
    mat_bottom : IntProperty(name="Bottom Finish",   default=2, min=0)
    mat_edge   : IntProperty(name="Edge Material",   default=3, min=0)
    mat_steel    : IntProperty(name="Steel Material",   default=4, min=0)
    mat_void     : IntProperty(name="Void Material",    default=5, min=0)


# ════════════════════════════════════════════════════════════
#  GENERADOR
# ════════════════════════════════════════════════════════════
class AF_SlabGenerator:
    """
    Motor de generación de losas.
    Coordenadas:
      X,Y = planta
      Z   = espesor (hacia abajo desde la cara superior)
    """

    def __init__(self, props):
        self.props = props
        self.bm    = bmesh.new()
        # (3.3) sin capa int custom: se usa face.material_index nativo

    # ────────────────────────────────────────────────────────
    def _outline_points(self):
        """
        Devuelve lista de Vector((x,y)) del contorno exterior
        en coords locales, en sentido CCW.
        """
        p = self.props

        if p.slab_type == 'RECTANGLE':
            w = p.width
            d = p.depth
            if p.origin_mode == 'CENTER':
                x0, x1 = -w * 0.5, w * 0.5
                y0, y1 = -d * 0.5, d * 0.5
            else:
                x0, x1 = 0.0, w
                y0, y1 = 0.0, d

            oh = p.overhang
            return [
                Vector((x0 - oh, y0 - oh)),
                Vector((x1 + oh, y0 - oh)),
                Vector((x1 + oh, y1 + oh)),
                Vector((x0 - oh, y1 + oh)),
            ]

        elif p.slab_type in ('CUSTOM', 'FROM_CURVE', 'FROM_WALL'):
            pts = []
            for v in p.vertices:
                pts.append(Vector((v.x, v.y)))
            if len(pts) < 3:
                # Fallback rectángulo
                return [
                    Vector((0, 0)), Vector((p.width, 0)),
                    Vector((p.width, p.depth)), Vector((0, p.depth)),
                ]
            # Overhang simple: offset outward (aprox)
            if p.overhang > 0.001:
                pts = self._offset_polygon(pts, p.overhang)
            return pts

        return [
            Vector((0, 0)), Vector((p.width, 0)),
            Vector((p.width, p.depth)), Vector((0, p.depth)),
        ]

    def _offset_polygon(self, pts, offset):
        """Offset outward simple de un polígono 2D cerrado."""
        n = len(pts)
        if n < 3:
            return pts
        result = []
        for i in range(n):
            prev = pts[(i - 1) % n]
            curr = pts[i]
            nxt  = pts[(i + 1) % n]
            d1 = (curr - prev).normalized()
            d2 = (nxt - curr).normalized()
            n1 = Vector((-d1.y, d1.x))
            n2 = Vector((-d2.y, d2.x))
            nrm = (n1 + n2)
            if nrm.length > 0.001:
                nrm.normalize()
                cos_a = nrm.dot(n1)
                if abs(cos_a) > 0.001:
                    nrm = nrm / cos_a
            result.append(curr + nrm * offset)
        return result

    def _hole_points(self, hole):
        """4 puntos del hueco rectangular, con rotación."""
        hw = hole.width * 0.5
        hd = hole.depth * 0.5
        cx, cy = hole.center_x, hole.center_y
        ca, sa = math.cos(hole.rotation), math.sin(hole.rotation)

        local = [
            Vector((-hw, -hd)),
            Vector(( hw, -hd)),
            Vector(( hw,  hd)),
            Vector((-hw,  hd)),
        ]
        out = []
        for p in local:
            rx = p.x * ca - p.y * sa + cx
            ry = p.x * sa + p.y * ca + cy
            out.append(Vector((rx, ry)))
        return out

    def _in_poly(self, x, y, outline):
        """Point-in-polygon (ray casting) para recortar al contorno."""
        inside = False
        n = len(outline)
        for i in range(n):
            x1, y1 = outline[i].x, outline[i].y
            x2, y2 = outline[(i + 1) % n].x, outline[(i + 1) % n].y
            if ((y1 > y) != (y2 > y)):
                xin = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
                if x < xin:
                    inside = not inside
        return inside

    def _clip_runs(self, xm, y0, y1, outline, step=0.10):
        """Tramos en Y dentro del contorno para una X dada."""
        runs = []
        run = None
        y = y0
        while y < y1 - 1e-9:
            ym = min(y + step / 2, y1)
            inside = self._in_poly(xm, ym, outline)
            if inside and run is None:
                run = y
            if run is not None and (not inside or
                                    y + step >= y1 - 1e-9):
                runs.append((run, y if not inside else y1))
                run = None
            y += step
        return runs

    def _box(self, x0, x1, y0, y1, z0, z1, mat_idx=0):
        bm = self.bm
        if x1 - x0 < 0.005 or y1 - y0 < 0.005 or z1 - z0 < 0.004:
            return
        try:
            v = [bm.verts.new(Vector((x, y, z))) for z in (z0, z1)
                 for (x, y) in ((x0, y0), (x1, y0), (x1, y1),
                                (x0, y1))]
            for fi in [(0, 1, 5, 4), (2, 3, 7, 6), (0, 3, 2, 1),
                       (4, 5, 6, 7), (0, 4, 7, 3), (1, 2, 6, 5)]:
                f = bm.faces.new([v[i] for i in fi])
                f.material_index = mat_idx
        except Exception:
            pass

    def _side_walls(self, outline, z_top, z_bot, mat_idx):
        """Solo caras laterales del contorno (cierra bordes)."""
        bm = self.bm
        n = len(outline)
        for i in range(n):
            j = (i + 1) % n
            try:
                v0 = bm.verts.new(Vector((outline[i].x, outline[i].y,
                                          z_bot)))
                v1 = bm.verts.new(Vector((outline[j].x, outline[j].y,
                                          z_bot)))
                v2 = bm.verts.new(Vector((outline[j].x, outline[j].y,
                                          z_top)))
                v3 = bm.verts.new(Vector((outline[i].x, outline[i].y,
                                          z_top)))
                f = bm.faces.new([v0, v1, v2, v3])
                f.material_index = mat_idx
            except Exception:
                pass
        bm.verts.ensure_lookup_table()

    # ────────────────────────────────────────────────────────
    def _extrude_profile(self, outline, z_top, z_bot, mat_top, mat_bot, mat_side):
        """
        Extruye un contorno 2D cerrado entre z_bot y z_top.
        Crea cara superior, inferior y laterales.
        """
        bm  = self.bm
        n   = len(outline)
        if n < 3:
            return

        v_top = [bm.verts.new(Vector((p.x, p.y, z_top))) for p in outline]
        v_bot = [bm.verts.new(Vector((p.x, p.y, z_bot))) for p in outline]
        bm.verts.ensure_lookup_table()

        # Cara superior (CCW visto desde arriba → normal +Z)
        try:
            f = bm.faces.new(v_top)
            f.material_index = mat_top
        except Exception:
            pass

        # Cara inferior (CW → normal -Z)
        try:
            f = bm.faces.new(list(reversed(v_bot)))
            f.material_index = mat_bot
        except Exception:
            pass

        # Laterales
        for i in range(n):
            j = (i + 1) % n
            try:
                f = bm.faces.new([v_bot[i], v_bot[j], v_top[j], v_top[i]])
                f.material_index = mat_side
            except Exception:
                pass

    def _extrude_with_holes(
        self, outline, holes_outlines,
        z_top, z_bot, mat_top, mat_bot, mat_side
    ):
        """
        Versión con huecos: usa bmesh faces + bmesh.ops para
        crear la losa y luego “agujerearla” con geometría lateral.
        Estrategia simple y robusta:
          1) extruir contorno exterior
          2) para cada hueco: extruir prismas del hueco y
             marcar como geometría de corte visual (laterales +
             anillo en top/bottom se resuelve uniendo anillos).

        Para mantener el código estable en 3.3 sin boolean
        booleano interno, generamos:
          - anillo superior e inferior (exterior)
          - caras laterales del hueco
          - NO rellenamos el interior del hueco
        """
        bm  = self.bm

        # Si no hay huecos → extrusión simple
        if not holes_outlines:
            self._extrude_profile(
                outline, z_top, z_bot, mat_top, mat_bot, mat_side
            )
            return

        # Con huecos: usamos bmesh + bridges
        # Crear loops top/bottom exterior
        n = len(outline)
        v_top = [bm.verts.new(Vector((p.x, p.y, z_top))) for p in outline]
        v_bot = [bm.verts.new(Vector((p.x, p.y, z_bot))) for p in outline]
        bm.verts.ensure_lookup_table()

        # Laterales exterior
        for i in range(n):
            j = (i + 1) % n
            try:
                f = bm.faces.new([v_bot[i], v_bot[j], v_top[j], v_top[i]])
                f.material_index = mat_side
            except Exception:
                pass

        # Huecos
        hole_top_loops = []
        hole_bot_loops = []
        for hpts in holes_outlines:
            hn = len(hpts)
            ht = [bm.verts.new(Vector((p.x, p.y, z_top))) for p in hpts]
            hb = [bm.verts.new(Vector((p.x, p.y, z_bot))) for p in hpts]
            bm.verts.ensure_lookup_table()
            hole_top_loops.append(ht)
            hole_bot_loops.append(hb)

            # Laterales del hueco (normal hacia el interior del hueco)
            for i in range(hn):
                j = (i + 1) % hn
                try:
                    # Invertido respecto al exterior
                    f = bm.faces.new([ht[i], ht[j], hb[j], hb[i]])
                    f.material_index = mat_side
                except Exception:
                    pass

        # Caras superior e inferior con huecos:
        # bmesh no crea fácilmente n-gons con holes sin ops.
        # Usamos fill + edges.
        def _make_face_with_holes(outer_loop, inner_loops, mat_idx, flip=False):
            # Crear edges
            def loop_edges(loop):
                edges = []
                m = len(loop)
                for i in range(m):
                    edges.append(bm.edges.new((loop[i], loop[(i + 1) % m])))
                return edges

            try:
                loop_edges(outer_loop)
                for il in inner_loops:
                    # inner loop en sentido opuesto ayuda al fill
                    loop_edges(list(reversed(il)) if not flip else il)
            except Exception:
                pass

            bm.edges.ensure_lookup_table()
            bm.verts.ensure_lookup_table()

            # Intentar fill del contorno exterior; si falla, n-gon simple sin hueco visual perfecto
            try:
                # Face outer only as fallback visual: connect as triangle fan is complex;
                # Mejor: una cara exterior y caras no rellenan hueco → usamos bmesh.ops.holes_fill si existe
                result = bmesh.ops.contextual_create(bm, geom=outer_loop)
                for f in result.get('faces', []):
                    f.material_index = mat_idx
                    if flip:
                        f.normal_flip()
            except Exception:
                try:
                    f = bm.faces.new(outer_loop if not flip else list(reversed(outer_loop)))
                    f.material_index = mat_idx
                except Exception:
                    pass

        _make_face_with_holes(v_top, hole_top_loops, mat_top, flip=False)
        _make_face_with_holes(v_bot, hole_bot_loops, mat_bot, flip=True)

        # Nota: el relleno perfecto con huecos en bmesh puro es limitado.
        # Para huecos limpios en producción se puede aplicar un boolean
        # interno; aquí priorizamos estabilidad en 3.3.

    # ────────────────────────────────────────────────────────
    def _hole_sides(self, holes, z_top, z_bot, mat_idx):
        bm = self.bm
        for hpts in holes:
            n = len(hpts)
            vt = [bm.verts.new(Vector((q.x, q.y, z_top)))
                  for q in hpts]
            vb = [bm.verts.new(Vector((q.x, q.y, z_bot)))
                  for q in hpts]
            bm.verts.ensure_lookup_table()
            for i in range(n):
                j = (i + 1) % n
                try:
                    f = bm.faces.new([vt[i], vt[j], vb[j], vb[i]])
                    f.material_index = mat_idx
                except Exception:
                    pass

    def _build_ribbed(self, outline, z_top, z_bot, mat_conc,
                      mat_void):
        """Aligerada / placa facil recortada al contorno."""
        p = self.props
        tp = max(p.topping, 0.03)
        jw = max(p.joist_width, 0.05)
        jh = max(p.joist_depth, 0.10)
        sp = max(p.joist_spacing, 0.3)
        self._extrude_profile(outline, z_top, z_top - tp,
                              mat_conc, mat_conc, mat_conc)
        zj = max(z_top - tp - jh, z_bot)
        self._side_walls(outline, z_top - tp, zj, mat_conc)
        xs = [q.x for q in outline]
        ys = [q.y for q in outline]
        x0, x1 = min(xs), max(xs)
        y0, y1 = min(ys), max(ys)
        x = x0 + sp / 2
        while x < x1:
            for ya, yb in self._clip_runs(x, y0, y1, outline):
                self._box(x - jw / 2, x + jw / 2, ya, yb, zj,
                          z_top - tp, mat_conc)
            x += sp
        x = x0 + sp / 2 + sp / 2
        while x < x1:
            cw = sp - jw
            if cw > 0.05:
                for ya, yb in self._clip_runs(x, y0, y1, outline):
                    self._box(x - cw / 2 + 0.01, x + cw / 2 - 0.01,
                              ya, yb, zj + 0.01,
                              z_top - tp - 0.005, mat_void)
            x += sp

    def _build_steeldeck(self, outline, z_top, z_bot, mat_conc,
                         mat_steel):
        """Steeldeck: torta + lamina trapezoidal recortada."""
        p = self.props
        tp = max(p.topping, 0.03)
        dh = max(p.deck_height, 0.04)
        pitch = max(p.deck_pitch, 0.15)
        self._extrude_profile(outline, z_top, z_top - tp,
                              mat_conc, mat_conc, mat_conc)
        zr = max(z_top - tp - dh, z_bot)
        self._side_walls(outline, z_top - tp, zr, mat_conc)
        prof = [(0.00, 0.0), (0.30, 0.0), (0.38, 1.0),
                (0.62, 1.0), (0.70, 0.0), (1.00, 0.0)]
        xs = [q.x for q in outline]
        ys = [q.y for q in outline]
        x0, x1 = min(xs), max(xs)
        y0, y1 = min(ys), max(ys)
        bm = self.bm
        k = 0
        while x0 + k * pitch < x1:
            xb = x0 + k * pitch
            for sg in range(len(prof) - 1):
                fa, za = prof[sg]
                fb, zb = prof[sg + 1]
                xa, xe = xb + fa * pitch, xb + fb * pitch
                if xe <= x0 or xa >= x1:
                    continue
                z0s, z1s = zr + za * dh, zr + zb * dh
                xm = (xa + xe) / 2
                for ya, yb in self._clip_runs(xm, y0, y1, outline):
                    try:
                        v0 = bm.verts.new(Vector((xa, ya, z0s)))
                        v1 = bm.verts.new(Vector((xa, yb, z0s)))
                        v2 = bm.verts.new(Vector((xe, yb, z1s)))
                        v3 = bm.verts.new(Vector((xe, ya, z1s)))
                        f = bm.faces.new([v0, v1, v2, v3])
                        f.material_index = mat_steel
                    except Exception:
                        pass
            k += 1
        bm.verts.ensure_lookup_table()

    def generate(self):
        p = self.props

        outline = self._outline_points()

        holes = []
        for h in p.holes:
            if h.enabled and h.width > 0.05 and h.depth > 0.05:
                holes.append(self._hole_points(h))

        z_top = p.z_offset
        z_bot = p.z_offset - p.thickness

        # — Núcleo según sistema constructivo —
        sys_ = p.slab_system
        if sys_ == 'MACIZA':
            self._extrude_profile(
                outline, z_top, z_bot,
                p.mat_core, p.mat_core, p.mat_edge
            )
        elif sys_ in ('ALIGERADA', 'PLACA_FACIL'):
            self._build_ribbed(outline, z_top, z_bot,
                               p.mat_core, p.mat_void)
        elif sys_ == 'STEELDECK':
            self._build_steeldeck(outline, z_top, z_bot,
                                  p.mat_core, p.mat_steel)
        if holes:
            self._hole_sides(holes, z_top, z_bot, p.mat_edge)

        # — Acabado superior —
        if p.top_finish_enable:
            zt0 = z_top
            zt1 = z_top + p.top_finish_thickness
            self._extrude_profile(
                outline, zt1, zt0,
                p.mat_top, p.mat_top, p.mat_top
            )

        # — Acabado inferior —
        if p.bottom_finish_enable:
            zb0 = z_bot - p.bottom_finish_thickness
            zb1 = z_bot
            self._extrude_profile(
                outline, zb1, zb0,
                p.mat_bottom, p.mat_bottom, p.mat_bottom
            )

        # — Bisel simple de borde superior (opcional, geom. approx) —
        # (omitido si bevel=0; un bevel real requeriría bmesh.ops.bevel)
        if p.edge_bevel > 0.0001:
            try:
                bmesh.ops.bevel(
                    self.bm,
                    geom=[e for e in self.bm.edges if abs(e.verts[0].co.z - z_top) < 1e-4
                          and abs(e.verts[1].co.z - z_top) < 1e-4],
                    offset=p.edge_bevel,
                    segments=1,
                    affect='EDGES',
                )
            except Exception:
                pass

        # (3.3) bmesh.ops exige el BMesh posicional, no como keyword
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
        return self.bm


# ════════════════════════════════════════════════════════════
#  UPDATE / REBUILD
# ════════════════════════════════════════════════════════════
def _find_slab_object(props):
    name = props.object_name
    if name and name in bpy.data.objects:
        return bpy.data.objects[name]
    for obj in bpy.data.objects:
        if (obj.type == 'MESH'
                and hasattr(obj, AF_SLAB_PROP)
                and getattr(obj, AF_SLAB_PROP) is props):
            return obj
    return None


def af_slab_system_update(self, context):
    if _SLAB_UPDATE_SUSPENDED:
        return
    presets = {
        'MACIZA': {'thickness': 0.20},
        'ALIGERADA': {'thickness': 0.30, 'joist_width': 0.10,
                      'joist_depth': 0.25, 'joist_spacing': 0.60,
                      'topping': 0.05},
        'PLACA_FACIL': {'thickness': 0.20, 'joist_width': 0.10,
                        'joist_depth': 0.14, 'joist_spacing': 0.50,
                        'topping': 0.04},
        'STEELDECK': {'thickness': 0.13, 'deck_height': 0.075,
                      'deck_pitch': 0.30, 'topping': 0.055},
    }
    for k, v in presets.get(self.slab_system, {}).items():
        try:
            setattr(self, k, v)
        except Exception:
            pass
    af_slab_update(self, context)


def af_slab_update(self, context):
    if _SLAB_UPDATE_SUSPENDED:
        return
    # self puede ser AF_SlabProperties, AF_SlabVertex o AF_SlabHole
    props = self
    if not hasattr(self, "is_af_slab"):
        # buscar dueño
        obj = context.active_object
        if obj and hasattr(obj, AF_SLAB_PROP):
            props = obj.archiforge_slab
        else:
            return
    obj = _find_slab_object(props)
    if obj is None:
        obj = context.active_object
    if obj is None or obj.type != 'MESH':
        return
    if not getattr(obj, AF_SLAB_PROP, None) or not obj.archiforge_slab.is_af_slab:
        return
    _rebuild_slab_mesh(obj, obj.archiforge_slab)


def af_slab_verts_update(self, context):
    if _SLAB_UPDATE_SUSPENDED:
        return
    obj = _find_slab_object(self) or context.active_object
    if obj is None:
        return
    props = obj.archiforge_slab
    target = props.n_vertices
    while len(props.vertices) < target:
        props.vertices.add()
    while len(props.vertices) > target:
        props.vertices.remove(len(props.vertices) - 1)

    # Si es rectángulo recién pasado a custom, inicializar
    if props.slab_type == 'CUSTOM' and len(props.vertices) >= 4:
        # Solo inicializa si todos están en 0
        if all(abs(v.x) < 1e-8 and abs(v.y) < 1e-8 for v in props.vertices):
            w, d = props.width, props.depth
            defaults = [(0, 0), (w, 0), (w, d), (0, d)]
            for i, v in enumerate(props.vertices):
                if i < len(defaults):
                    v.x, v.y = defaults[i]
                else:
                    # puntos extra en el borde
                    t = i / max(len(props.vertices) - 1, 1)
                    v.x, v.y = w * t, 0.0
    _rebuild_slab_mesh(obj, props)


def af_slab_holes_update(self, context):
    if _SLAB_UPDATE_SUSPENDED:
        return
    obj = _find_slab_object(self) or context.active_object
    if obj is None:
        return
    props = obj.archiforge_slab
    target = props.n_holes
    while len(props.holes) < target:
        h = props.holes.add()
        h.name = f"Hole {len(props.holes)}"
        h.width = 1.0
        h.depth = 1.0
        h.center_x = props.width * 0.5
        h.center_y = props.depth * 0.5
    while len(props.holes) > target:
        props.holes.remove(len(props.holes) - 1)
    _rebuild_slab_mesh(obj, props)


def _rebuild_slab_mesh(obj, props):
    gen = AF_SlabGenerator(props)
    bm  = gen.generate()
    if bm is None:
        return
    me = obj.data
    bm.to_mesh(me)
    bm.free()
    me.update()
    for poly in me.polygons:
        poly.use_smooth = False
    # (3.3) material_index ya viene de las caras bmesh;
    # polygon_layers_int no existe en Blender 3.3.


def _setup_slab_materials(obj):
    mat_names = [
        "AF.Slab.Default",
        "AF.Floor.Concrete",
        "AF.Wall.Plaster",
        "AF.Wall.Concrete",
        "AF.Slab.Steel",
        "AF.Slab.Void",
    ]
    af_material.ensure_af_materials_for_object(obj, mat_names)


def _create_slab_object(context, name="AF_Slab"):
    mesh = bpy.data.meshes.new(name)
    obj = None
    try:
        obj = bpy.data.objects.new(name, mesh)
        context.collection.objects.link(obj)
        context.view_layer.objects.active = obj
        obj.select_set(True)

        props = obj.archiforge_slab
        props.is_af_slab = True
        props.object_name = obj.name
        _setup_slab_materials(obj)
        return obj, props
    except Exception:
        if obj is not None and obj.name in bpy.data.objects:
            bpy.data.objects.remove(obj, do_unlink=True)
        if mesh.users == 0 and mesh.name in bpy.data.meshes:
            bpy.data.meshes.remove(mesh)
        raise


def _fill_vertices_from_points(props, points):
    global _SLAB_UPDATE_SUSPENDED
    previous_suspend = _SLAB_UPDATE_SUSPENDED
    _SLAB_UPDATE_SUSPENDED = True
    try:
        props.n_vertices = max(len(points), 3)
        while len(props.vertices) < len(points):
            props.vertices.add()
        while len(props.vertices) > len(points):
            props.vertices.remove(len(props.vertices) - 1)
        for index, point in enumerate(points):
            props.vertices[index].x = point[0]
            props.vertices[index].y = point[1]
    finally:
        _SLAB_UPDATE_SUSPENDED = previous_suspend


def _set_slab_outline(props, points):
    """Store a validated world-space path in slab-local XY coordinates."""
    global _SLAB_UPDATE_SUSPENDED
    coords = normalize_outline(
        points, min_segment_length=0.01, max_vertices=64)
    xs = [point[0] for point in coords]
    ys = [point[1] for point in coords]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    width, depth = x1 - x0, y1 - y0
    if width < 0.10 or depth < 0.10:
        raise ValueError("El contorno debe medir al menos 0.10 m en X e Y")

    previous_suspend = _SLAB_UPDATE_SUSPENDED
    _SLAB_UPDATE_SUSPENDED = True
    try:
        props.slab_type = 'CUSTOM'
        props.origin_mode = 'CORNER'
        props.width = width
        props.depth = depth
        props.overhang = 0.0
        props.n_vertices = len(coords)
        _fill_vertices_from_points(
            props, [(x - x0, y - y0) for x, y in coords])
    finally:
        _SLAB_UPDATE_SUSPENDED = previous_suspend

    return (x0, y0), width, depth


def _points_from_curve(curve_obj):
    """Extrae puntos 2D (XY) de una curva en world → local simple."""
    points = []
    mw = curve_obj.matrix_world
    if curve_obj.type != 'CURVE':
        return points
    for spline in curve_obj.data.splines:
        if spline.type == 'BEZIER':
            for bp in spline.bezier_points:
                co = mw @ bp.co
                points.append((co.x, co.y))
        else:
            for bp in spline.points:
                co = mw @ Vector(bp.co[:3])
                points.append((co.x, co.y))
    return points


def _points_from_wall(wall_obj):
    """
    Aproxima el contorno de un muro AF:
    usa la bbox XY del muro expandida.
    (Versión robusta; más adelante se puede leer la baseline real.)
    """
    mw = wall_obj.matrix_world
    pts = [mw @ Vector(corner) for corner in wall_obj.bound_box]
    xs = [p.x for p in pts]
    ys = [p.y for p in pts]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


# ════════════════════════════════════════════════════════════
#  OPERADORES
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_OT_slab(Operator):
    bl_idname = "archiforge.slab"
    bl_label = "Add AF Slab"
    bl_description = "Add a parametric ArchiForge slab"
    bl_options = {'REGISTER', 'UNDO'}

    slab_type : EnumProperty(name="Type", items=AF_SLAB_TYPES, default='RECTANGLE')
    slab_use  : EnumProperty(name="Use",  items=AF_SLAB_USE,   default='FLOOR')
    width     : FloatProperty(name="Width",  default=4.0, min=0.1, unit='LENGTH')
    depth     : FloatProperty(name="Depth",  default=3.0, min=0.1, unit='LENGTH')
    thickness : FloatProperty(name="Thickness", default=0.20, min=0.02, unit='LENGTH')
    z_offset  : FloatProperty(name="Z Offset", default=0.0, unit='LENGTH')

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        col = layout.column(align=True)
        col.prop(self, "slab_type")
        col.prop(self, "slab_use")
        col.separator()
        col.prop(self, "width")
        col.prop(self, "depth")
        col.prop(self, "thickness")
        col.prop(self, "z_offset")

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        obj, props = _create_slab_object(context, "AF_Slab")
        props.slab_type = self.slab_type
        props.slab_use  = self.slab_use
        props.width     = self.width
        props.depth     = self.depth
        props.thickness = self.thickness
        props.z_offset  = self.z_offset
        props.is_ceiling = (self.slab_use == 'CEILING')
        _rebuild_slab_mesh(obj, props)
        self.report({'INFO'}, _tr("Slab created: {}").format(obj.name))
        return {'FINISHED'}


class ARCHIFORGE_OT_slab_draw(AF_OutlineDrawMixin, Operator):
    """Draw a closed custom outline for a parametric slab."""
    bl_idname = "archiforge.slab_draw"
    bl_label = "Draw Slab Outline"
    bl_description = (
        "Click slab perimeter vertices, then click the first point or "
        "press C/Enter to close"
    )
    bl_options = {'REGISTER', 'UNDO'}
    outline_tool_label = "Slab"

    slab_use : EnumProperty(
        name="Use", items=AF_SLAB_USE, default='FLOOR',
    )
    thickness : FloatProperty(
        name="Thickness", default=0.20, min=0.02, unit='LENGTH',
    )

    def _create_from_outline(self, context, points):
        global _SLAB_UPDATE_SUSPENDED
        obj = None
        previous_suspend = _SLAB_UPDATE_SUSPENDED
        _SLAB_UPDATE_SUSPENDED = True
        try:
            obj, props = _create_slab_object(context, "AF_Slab")
            origin, _, _ = _set_slab_outline(props, points)
            obj.location = (origin[0], origin[1], self._draw_z)
            props.slab_use = self.slab_use
            props.thickness = self.thickness
            props.z_offset = 0.0
            props.is_ceiling = self.slab_use == 'CEILING'
            props.source_curve = ""
            props.source_wall = ""
            _rebuild_slab_mesh(obj, props)
            return obj
        except Exception:
            if obj is not None and obj.name in bpy.data.objects:
                mesh = obj.data if obj.type == 'MESH' else None
                bpy.data.objects.remove(obj, do_unlink=True)
                if mesh is not None and mesh.users == 0:
                    bpy.data.meshes.remove(mesh)
            raise
        finally:
            _SLAB_UPDATE_SUSPENDED = previous_suspend


class ARCHIFORGE_OT_slab_from_curve(Operator):
    bl_idname = "archiforge.slab_from_curve"
    bl_label = "Slab from Curve"
    bl_description = "Create slab from selected curve outline"
    bl_options = {'REGISTER', 'UNDO'}

    thickness : FloatProperty(name="Thickness", default=0.20, min=0.02, unit='LENGTH')
    z_offset  : FloatProperty(name="Z Offset", default=0.0, unit='LENGTH')
    slab_use  : EnumProperty(name="Use", items=AF_SLAB_USE, default='FLOOR')

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'CURVE'

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        col = self.layout.column(align=True)
        col.prop(self, "slab_use")
        col.prop(self, "thickness")
        col.prop(self, "z_offset")

    def execute(self, context):
        curve = context.active_object
        pts = _points_from_curve(curve)
        if len(pts) < 3:
            self.report({'ERROR'}, _tr("Curve needs at least 3 points"))
            return {'CANCELLED'}

        bpy.ops.object.select_all(action='DESELECT')
        obj, props = _create_slab_object(context, "AF_Slab")
        props.slab_type = 'FROM_CURVE'
        props.slab_use  = self.slab_use
        props.thickness = self.thickness
        props.z_offset  = self.z_offset
        props.source_curve = curve.name
        props.is_ceiling = (self.slab_use == 'CEILING')
        _fill_vertices_from_points(props, pts)
        _rebuild_slab_mesh(obj, props)
        self.report({'INFO'}, _tr("Slab from curve '{}'").format(curve.name))
        return {'FINISHED'}


class ARCHIFORGE_OT_slab_from_wall(Operator):
    bl_idname = "archiforge.slab_from_wall"
    bl_label = "Slab from Wall"
    bl_description = "Create floor/ceiling slab from selected ArchiForge wall"
    bl_options = {'REGISTER', 'UNDO'}

    ceiling : BoolProperty(
        name="Ceiling",
        description="If true, place slab as ceiling on top of wall height",
        default=False,
    )
    thickness : FloatProperty(name="Thickness", default=0.20, min=0.02, unit='LENGTH')
    overhang  : FloatProperty(name="Overhang", default=0.0, min=0.0, unit='LENGTH')

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
        col.prop(self, "ceiling")
        col.prop(self, "thickness")
        col.prop(self, "overhang")

    def execute(self, context):
        wall = context.active_object
        wprops = wall.archiforge_wall
        pts = _points_from_wall(wall)
        if len(pts) < 3:
            self.report({'ERROR'}, _tr("Could not read wall outline"))
            return {'CANCELLED'}

        z_off = wprops.height if self.ceiling else 0.0

        bpy.ops.object.select_all(action='DESELECT')
        name = "AF_Ceiling" if self.ceiling else "AF_Floor"
        obj, props = _create_slab_object(context, name)
        props.slab_type = 'FROM_WALL'
        props.slab_use  = 'CEILING' if self.ceiling else 'FLOOR'
        props.thickness = self.thickness
        props.overhang  = self.overhang
        props.z_offset  = z_off
        props.source_wall = wall.name
        props.is_ceiling  = self.ceiling
        _fill_vertices_from_points(props, pts)

        # Posicionar la losa en world origin del muro (bbox already world-ish)
        # Los puntos ya están en world XY; objeto en (0,0,0)
        _rebuild_slab_mesh(obj, props)

        self.report(
            {'INFO'},
            _tr("{} slab from '{}'")
            .format('Ceiling' if self.ceiling else 'Floor', wall.name)
        )
        return {'FINISHED'}


class ARCHIFORGE_OT_wall_from_slab(Operator):
    """Crea un muro AF rectangular aproximado desde una losa."""
    bl_idname = "archiforge.wall_from_slab"
    bl_label = "Wall from Slab"
    bl_description = "Create a simple wall perimeter from selected slab"
    bl_options = {'REGISTER', 'UNDO'}

    height : FloatProperty(name="Wall Height", default=2.7, min=0.1, unit='LENGTH')
    width  : FloatProperty(name="Wall Thickness", default=0.20, min=0.05, unit='LENGTH')

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj is not None and obj.type == 'MESH'
            and hasattr(obj, AF_SLAB_PROP)
            and obj.archiforge_slab.is_af_slab
        )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        # Delega al operador de muro si existe; si no, crea muro simple
        try:
            bpy.ops.archiforge.wall(
                'EXEC_DEFAULT',
                height=self.height,
                width=self.width,
                length=context.active_object.archiforge_slab.width,
            )
            self.report({'INFO'}, _tr("Wall created from slab dimensions"))
        except Exception as e:
            self.report({'WARNING'}, _tr("Could not create wall: {}").format(e))
            return {'CANCELLED'}
        return {'FINISHED'}


class ARCHIFORGE_OT_slab_update(Operator):
    bl_idname = "archiforge.slab_update"
    bl_label = "Update Slab"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj is not None and obj.type == 'MESH'
            and hasattr(obj, AF_SLAB_PROP)
            and obj.archiforge_slab.is_af_slab
        )

    def execute(self, context):
        obj = context.active_object
        _rebuild_slab_mesh(obj, obj.archiforge_slab)
        self.report({'INFO'}, _tr("Slab updated"))
        return {'FINISHED'}


class ARCHIFORGE_OT_slab_add_hole(Operator):
    bl_idname = "archiforge.slab_add_hole"
    bl_label = "Add Hole"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj is not None and hasattr(obj, AF_SLAB_PROP)
            and obj.archiforge_slab.is_af_slab
        )

    def execute(self, context):
        props = context.active_object.archiforge_slab
        props.n_holes += 1
        return {'FINISHED'}


class ARCHIFORGE_OT_slab_remove_hole(Operator):
    bl_idname = "archiforge.slab_remove_hole"
    bl_label = "Remove Hole"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj is not None and hasattr(obj, AF_SLAB_PROP)
            and obj.archiforge_slab.is_af_slab
            and obj.archiforge_slab.n_holes > 0
        )

    def execute(self, context):
        props = context.active_object.archiforge_slab
        props.n_holes = max(0, props.n_holes - 1)
        return {'FINISHED'}


# ════════════════════════════════════════════════════════════
#  PANEL
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_PT_slab(Panel):
    bl_label = "Slab Properties"
    bl_idname = "ARCHIFORGE_PT_slab"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "ArchiForge"
    bl_context = "objectmode"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj is not None and obj.type == 'MESH'
            and hasattr(obj, AF_SLAB_PROP)
            and obj.archiforge_slab.is_af_slab
        )

    def draw_header(self, context):
        self.layout.label(text="", icon='MESH_PLANE')

    def draw(self, context):
        props  = context.active_object.archiforge_slab
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Type", icon='MODIFIER')
        col.prop(props, "slab_type", text="")
        col.prop(props, "slab_use", text="Use")
        origin = col.row()
        origin.enabled = props.slab_type == 'RECTANGLE'
        origin.prop(props, "origin_mode")

        box = layout.box()
        col = box.column(align=True)
        col.label(text="System", icon='MODIFIER')
        col.prop(props, "slab_system", text="")
        if props.slab_system in ('ALIGERADA', 'PLACA_FACIL'):
            col.prop(props, "joist_width")
            col.prop(props, "joist_depth")
            col.prop(props, "joist_spacing")
            col.prop(props, "topping")
        if props.slab_system == 'STEELDECK':
            col.prop(props, "deck_height")
            col.prop(props, "deck_pitch")
            col.prop(props, "topping", text="Concrete")

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Dimensions", icon='ARROW_LEFTRIGHT')
        if props.slab_type == 'RECTANGLE':
            col.prop(props, "width")
            col.prop(props, "depth")
        col.prop(props, "thickness")
        col.prop(props, "z_offset")
        col.prop(props, "overhang")
        col.prop(props, "edge_bevel")

        # Custom verts
        if props.slab_type in ('CUSTOM', 'FROM_CURVE', 'FROM_WALL'):
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Outline Vertices", icon='VERTEXSEL')
            col.prop(props, "n_vertices")
            for i, v in enumerate(props.vertices):
                row = col.row(align=True)
                row.label(text=f"V{i+1}")
                row.prop(v, "x", text="X")
                row.prop(v, "y", text="Y")

        # Finishes
        box = layout.box()
        row = box.row(align=True)
        row.prop(props, "top_finish_enable", text="Top Finish", toggle=True)
        if props.top_finish_enable:
            box.prop(props, "top_finish_thickness")
        row = box.row(align=True)
        row.prop(props, "bottom_finish_enable", text="Bottom Finish", toggle=True)
        if props.bottom_finish_enable:
            box.prop(props, "bottom_finish_thickness")

        # Holes
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Holes", icon='SELECT_SET')
        row = col.row(align=True)
        row.prop(props, "n_holes")
        row.operator("archiforge.slab_add_hole", text="", icon='ADD')
        row.operator("archiforge.slab_remove_hole", text="", icon='REMOVE')
        for i, h in enumerate(props.holes):
            hb = col.box()
            hb.prop(h, "enabled", text=h.name or f"Hole {i+1}")
            if h.enabled:
                hb.prop(h, "center_x")
                hb.prop(h, "center_y")
                hb.prop(h, "width")
                hb.prop(h, "depth")
                hb.prop(h, "rotation")

        # Materials
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Materials", icon='MATERIAL')
        col.prop(props, "mat_core", text="Core")
        col.prop(props, "mat_edge", text="Edge")
        if props.slab_system == 'STEELDECK':
            col.prop(props, "mat_steel", text="Steel")
        if props.slab_system in ('ALIGERADA', 'PLACA_FACIL'):
            col.prop(props, "mat_void", text="Void")
        if props.top_finish_enable:
            col.prop(props, "mat_top", text="Top")
        if props.bottom_finish_enable:
            col.prop(props, "mat_bottom", text="Bottom")

        layout.separator()
        layout.operator("archiforge.slab_update", icon='FILE_REFRESH')


# ════════════════════════════════════════════════════════════
#  REGISTER
# ════════════════════════════════════════════════════════════
classes = [
    AF_SlabVertex,
    AF_SlabHole,
    AF_SlabProperties,
    ARCHIFORGE_OT_slab,
    ARCHIFORGE_OT_slab_draw,
    ARCHIFORGE_OT_slab_from_curve,
    ARCHIFORGE_OT_slab_from_wall,
    ARCHIFORGE_OT_wall_from_slab,
    ARCHIFORGE_OT_slab_update,
    ARCHIFORGE_OT_slab_add_hole,
    ARCHIFORGE_OT_slab_remove_hole,
    ARCHIFORGE_PT_slab,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Object.archiforge_slab = PointerProperty(type=AF_SlabProperties)
    print("[ArchiForge] ✅ af_slab — registered")


def unregister():
    if hasattr(bpy.types.Object, "archiforge_slab"):
        del bpy.types.Object.archiforge_slab
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    print("[ArchiForge] 🔴 af_slab — unregistered")
