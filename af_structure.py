# -*- coding: utf-8 -*-
"""ArchiForge — Estructura paramétrica (NSR-10 friendly).

v1.0 — Blender 3.3 LTS.
Zapatas, columnas, vigas, placa aligerada, ejes y niveles NPT.
Origen en piso / desplante. Ejes y niveles crean rótulos (FONT) hijos.
"""

import bpy
import math

from mathutils import Euler, Matrix, Vector
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)

try:
    from . import af_material
    from .af_objects_base import AF_ObjectBuilder
except ImportError:
    af_material = None
    AF_ObjectBuilder = None

try:
    from .af_i18n import tr_report as _tr
except ImportError:  # pragma: no cover - fuera del paquete
    def _tr(text):
        return text

AF_STRUCT_PROP = "archiforge_struct"
AF_STRUCT_VERSION = 1

AF_STRUCT_TYPES = [
    ('FOOTING', "Footing", "Zapata aislada + pedestal"),
    ('COLUMN', "Column", "Columna rect/circular + acero"),
    ('BEAM', "Beam", "Viga aérea + estribos"),
    ('RIBBED_SLAB', "Ribbed Slab", "Placa aligerada real"),
    ('GRID', "Grid Axes", "Ejes A-B-C / 1-2-3"),
    ('LEVELS', "Levels NPT", "Niveles de piso"),
]

AF_STRUCT_DEFAULTS = {
    'FOOTING': (1.20, 1.20, 1.00),
    'COLUMN': (0.30, 0.30, 2.40),
    'BEAM': (4.00, 0.25, 0.40),
    'RIBBED_SLAB': (5.00, 4.00, 0.30),
    'GRID': (10.0, 8.00, 0.0),
    'LEVELS': (6.00, 6.00, 0.0),
}

AF_COL_SHAPES = [
    ('RECT', "Rectangular", "Sección rectangular"),
    ('ROUND', "Circular", "Sección circular"),
]

_SUSPEND = False


def af_struct_update(self, context):
    if _SUSPEND:
        return
    try:
        from .af_structure import _find_struct_object as _find
        from .af_structure import _rebuild_struct_mesh as _rb
        from .af_structure import _sync_struct_labels as _lb
    except ImportError:
        return
    props = self if hasattr(self, "is_af_struct") else None
    if props is None:
        return
    obj = _find(props)
    if obj is None:
        obj = context.active_object if context else None
    if obj is None or obj.type != 'MESH':
        return
    if not getattr(obj, AF_STRUCT_PROP, None):
        return
    _rb(obj, props)
    _lb(obj, props)


class AF_StructProperties(PropertyGroup):
    is_af_struct : BoolProperty(default=True, options={'HIDDEN'})
    object_name : StringProperty(default="", options={'HIDDEN'})
    af_version : IntProperty(default=AF_STRUCT_VERSION,
                             options={'HIDDEN'})

    item_type : EnumProperty(name="Type", items=AF_STRUCT_TYPES,
                             default='COLUMN',
                             update=af_struct_update)
    mesh_quality : EnumProperty(
        name="Quality",
        items=[('LOW', "Low", ""), ('MEDIUM', "Medium", ""),
               ('HIGH', "High", "")],
        default='MEDIUM', update=af_struct_update)

    width : FloatProperty(name="Width", default=0.30, min=0.05,
                          max=30.0, unit='LENGTH',
                          update=af_struct_update)
    depth : FloatProperty(name="Depth", default=0.30, min=0.05,
                          max=30.0, unit='LENGTH',
                          update=af_struct_update)
    height : FloatProperty(name="Height", default=2.40, min=0.05,
                           max=30.0, unit='LENGTH',
                           update=af_struct_update)

    col_shape : EnumProperty(name="Section", items=AF_COL_SHAPES,
                             default='RECT', update=af_struct_update)
    rebar : BoolProperty(name="Rebar Detail", default=True,
                         update=af_struct_update)
    stirrup_spacing : FloatProperty(name="Stirrup @", default=0.20,
                                    min=0.05, max=1.0, unit='LENGTH',
                                    update=af_struct_update)

    footing_base_h : FloatProperty(name="Base H", default=0.40,
                                   min=0.15, max=1.5, unit='LENGTH',
                                   update=af_struct_update)
    pedestal : FloatProperty(name="Pedestal", default=0.30,
                             min=0.15, max=1.0, unit='LENGTH',
                             update=af_struct_update)

    joist_w : FloatProperty(name="Joist W", default=0.10, min=0.05,
                            max=0.30, unit='LENGTH',
                            update=af_struct_update)
    joist_h : FloatProperty(name="Joist H", default=0.25, min=0.10,
                            max=0.60, unit='LENGTH',
                            update=af_struct_update)
    joist_spacing : FloatProperty(name="Joist @", default=0.60,
                                  min=0.30, max=1.20, unit='LENGTH',
                                  update=af_struct_update)
    topping : FloatProperty(name="Topping", default=0.05, min=0.03,
                            max=0.15, unit='LENGTH',
                            update=af_struct_update)
    edge_beam : BoolProperty(name="Edge Beams", default=True,
                             update=af_struct_update)

    grid_nx : IntProperty(name="Axes X (1..n)", default=4, min=2,
                          max=12, update=af_struct_update)
    grid_ny : IntProperty(name="Axes Y (A..)", default=3, min=2,
                          max=12, update=af_struct_update)
    grid_sx : FloatProperty(name="Spacing X", default=5.0, min=1.0,
                            max=20.0, unit='LENGTH',
                            update=af_struct_update)
    grid_sy : FloatProperty(name="Spacing Y", default=4.0, min=1.0,
                            max=20.0, unit='LENGTH',
                            update=af_struct_update)

    n_levels : IntProperty(name="Levels", default=3, min=1,
                           max=20, update=af_struct_update)
    h_first : FloatProperty(name="H First", default=2.40, min=0.5,
                            max=10.0, unit='LENGTH',
                            update=af_struct_update)
    h_typ : FloatProperty(name="H Typical", default=2.40, min=0.5,
                          max=10.0, unit='LENGTH',
                          update=af_struct_update)

    mat_concrete : IntProperty(name="Concrete Mat", default=0, min=0,
                               max=7, update=af_struct_update)
    mat_steel : IntProperty(name="Steel Mat", default=1, min=0,
                            max=7, update=af_struct_update)
    mat_void : IntProperty(name="Void Mat", default=2, min=0,
                           max=7, update=af_struct_update)
    mat_grid : IntProperty(name="Grid Mat", default=3, min=0,
                           max=7, update=af_struct_update)


class AF_StructGenerator:
    def __init__(self, props):
        self.props = props
        self.b = AF_ObjectBuilder()
        q = getattr(props, "mesh_quality", "MEDIUM")
        self._qf = {"LOW": 0.6, "MEDIUM": 1.15, "HIGH": 1.8}.get(q, 1.15)

    def seg(self, base):
        return max(8, int(base * self._qf))

    def box_c(self, cx, cy, cz, sx, sy, sz, mi):
        self.b.box(cx - max(sx, 0.001) / 2, cx + max(sx, 0.001) / 2,
                   cy - max(sy, 0.001) / 2, cy + max(sy, 0.001) / 2,
                   cz - max(sz, 0.001) / 2, cz + max(sz, 0.001) / 2,
                   mi)

    def cyl(self, cx, cy, z0, z1, r, base_seg=20, mi=0):
        self.b.cylinder(cx, cy, z0, max(z1, z0 + 0.001),
                        max(r, 0.0012), segments=self.seg(base_seg),
                        mi=mi)

    def tor(self, cx, cy, cz, major, minor, base_seg=24,
            minor_seg=10, mi=0):
        self.b.torus(cx, cy, cz, max(major, 0.004),
                     max(minor, 0.0012),
                     major_segs=self.seg(base_seg),
                     minor_segs=max(6, int(minor_seg * self._qf)),
                     mi=mi)

    def tube(self, p0, p1, r, base_seg=8, mi=0):
        a, b = Vector(p0), Vector(p1)
        d = b - a
        if d.length < 1e-6:
            return
        dn = d.normalized()
        if dn.dot(Vector((0, 0, 1))) < -0.9999:
            rot = Matrix.Rotation(math.pi, 3, 'X')
        else:
            rot = Vector((0, 0, 1)).rotation_difference(dn).to_matrix()
        m = rot.to_4x4()
        m.translation = a
        self.b.cylinder(0, 0, 0, d.length, max(r, 0.0008),
                        segments=self.seg(base_seg), mi=mi,
                        transform=m)

    # ZAPATA
    def _build_footing(self):
        p = self.props
        con, stl = p.mat_concrete, p.mat_steel
        bw, bd = max(p.width, 0.4), max(p.depth, 0.4)
        bh = max(p.footing_base_h, 0.15)
        ps = max(p.pedestal, 0.15)
        ph = max(p.height - bh, 0.2)

        self.box_c(0, 0, -0.025, bw + 0.10, bd + 0.10, 0.05,
                   con)
        self.box_c(0, 0, bh / 2, bw, bd, bh, con)
        self.box_c(0, 0, bh + ph / 2, ps, ps, ph, con)
        self.box_c(0, 0, bh + 0.015, ps + 0.10, ps + 0.10,
                   0.03, con)
        if p.rebar:
            nx = max(2, int(bw / 0.15))
            ny = max(2, int(bd / 0.15))
            for i in range(nx):
                x = -bw / 2 + 0.07 + i * (bw - 0.14) / max(
                    nx - 1, 1)
                self.tube((x, -bd / 2 + 0.05, 0.08),
                          (x, bd / 2 - 0.05, 0.08), 0.008, 6,
                          stl)
            for j in range(ny):
                y = -bd / 2 + 0.07 + j * (bd - 0.14) / max(
                    ny - 1, 1)
                self.tube((-bw / 2 + 0.05, y, 0.11),
                          (bw / 2 - 0.05, y, 0.11), 0.008, 6,
                          stl)
            for sx in (-1, 1):
                for sy in (-1, 1):
                    self.tube((sx * (ps / 2 - 0.05),
                               sy * (ps / 2 - 0.05), bh),
                              (sx * (ps / 2 - 0.05),
                               sy * (ps / 2 - 0.05),
                               bh + ph + 0.40), 0.010, 6, stl)

    # COLUMNA
    def _build_column(self):
        p = self.props
        con, stl = p.mat_concrete, p.mat_steel
        h = max(p.height, 0.3)
        if p.col_shape == 'ROUND':
            r = max(p.width, 0.1) / 2
            self.cyl(0, 0, 0, h, r, 28, con)
            self.cyl(0, 0, -0.02, 0.02, r + 0.02, 28, con)
            if p.rebar:
                for i in range(6):
                    a = i * math.pi / 3
                    self.tube(((r - 0.05) * math.cos(a),
                               (r - 0.05) * math.sin(a), 0),
                              ((r - 0.05) * math.cos(a),
                               (r - 0.05) * math.sin(a),
                               h + 0.40), 0.010, 6, stl)
                z = 0.10
                while z < h:
                    self.tor(0, 0, z, r - 0.04, 0.006, 24, 8,
                             stl)
                    z += max(p.stirrup_spacing, 0.05)
        else:
            w, d = max(p.width, 0.1), max(p.depth, 0.1)
            self.box_c(0, 0, h / 2, w, d, h, con)
            self.box_c(0, 0, 0.02, w + 0.04, d + 0.04, 0.04,
                       con)
            if p.rebar:
                for sx in (-1, 1):
                    for sy in (-1, 1):
                        self.tube((sx * (w / 2 - 0.05),
                                   sy * (d / 2 - 0.05), 0),
                                  (sx * (w / 2 - 0.05),
                                   sy * (d / 2 - 0.05),
                                   h + 0.40), 0.010, 6, stl)
                z = 0.10
                while z < h:
                    self.box_c(0, 0, z, w - 0.06, 0.012, 0.012,
                               stl)
                    self.box_c(0, 0, z, 0.012, d - 0.06, 0.012,
                               stl)
                    self.box_c(0, (d / 2 - 0.035), z, w - 0.06,
                               0.012, 0.012, stl)
                    self.box_c(0, -(d / 2 - 0.035), z, w - 0.06,
                               0.012, 0.012, stl)
                    self.box_c((w / 2 - 0.035), 0, z, 0.012,
                               d - 0.06, 0.012, stl)
                    self.box_c(-(w / 2 - 0.035), 0, z, 0.012,
                               d - 0.06, 0.012, stl)
                    z += max(p.stirrup_spacing, 0.05)

    # VIGA
    def _build_beam(self):
        p = self.props
        con, stl = p.mat_concrete, p.mat_steel
        ln = max(p.width, 0.5)
        b, h = max(p.depth, 0.1), max(p.height, 0.15)
        self.box_c(0, 0, 0, ln, b, h, con)
        if p.rebar:
            for sy in (-1, 1):
                for sz in (-1, 1):
                    self.tube((-ln / 2 - 0.15, sy * (b / 2 -
                               0.05), sz * (h / 2 - 0.05)),
                              (ln / 2 + 0.15, sy * (b / 2 -
                               0.05), sz * (h / 2 - 0.05)),
                              0.010, 6, stl)
            x = -ln / 2 + 0.10
            while x < ln / 2:
                self.box_c(x, 0, (h / 2 - 0.04), 0.012, b -
                           0.06, 0.012, stl)
                self.box_c(x, 0, -(h / 2 - 0.04), 0.012, b -
                           0.06, 0.012, stl)
                self.box_c(x, (b / 2 - 0.04), 0, 0.012, 0.012,
                           h - 0.06, stl)
                self.box_c(x, -(b / 2 - 0.04), 0, 0.012, 0.012,
                           h - 0.06, stl)
                x += max(p.stirrup_spacing, 0.05)

    # PLACA ALIGERADA
    def _build_ribbed_slab(self):
        p = self.props
        con, voy = p.mat_concrete, p.mat_void
        lx, ly = max(p.width, 1.0), max(p.depth, 1.0)
        jw = max(p.joist_w, 0.05)
        jh = max(p.joist_h, 0.10)
        sp = max(p.joist_spacing, 0.3)
        tp = max(p.topping, 0.03)
        tot = jh + tp

        self.box_c(0, 0, -tp / 2, lx, ly, tp, con)
        x = -lx / 2 + sp / 2
        while x < lx / 2:
            self.box_c(x, 0, -tp - jh / 2, jw, ly, jh, con)
            x += sp
        x = -lx / 2 + sp / 2 + sp / 2
        while x < lx / 2 - 0.01:
            cw = sp - jw
            if cw > 0.05:
                self.box_c(x, 0, -tp - jh / 2 + 0.01, cw,
                           ly - 0.02, jh - 0.02, voy)
            x += sp
        if p.edge_beam:
            ebw = 0.25
            for sx in (-1, 1):
                self.box_c(sx * (lx / 2 - ebw / 2), 0, -tot /
                           2, ebw, ly, tot, con)
            for sy in (-1, 1):
                self.box_c(0, sy * (ly / 2 - ebw / 2), -tot /
                           2, lx - 2 * ebw, ebw, tot, con)
            if p.rebar:
                stl = p.mat_steel
                for sx in (-1, 1):
                    for sz in (0.06, tot - 0.06):
                        self.tube((sx * (lx / 2 - ebw / 2),
                                   -ly / 2, -sz),
                                  (sx * (lx / 2 - ebw / 2),
                                   ly / 2, -sz), 0.010, 6, stl)

    # EJES
    def grid_lines(self):
        p = self.props
        nx = max(2, min(p.grid_nx, 12))
        ny = max(2, min(p.grid_ny, 12))
        sx = max(p.grid_sx, 1.0)
        sy = max(p.grid_sy, 1.0)
        xs = [(i - (nx - 1) / 2) * sx for i in range(nx)]
        ys = [(j - (ny - 1) / 2) * sy for j in range(ny)]
        return xs, ys

    def _build_grid(self):
        p = self.props
        gr = p.mat_grid
        xs, ys = self.grid_lines()
        ext = 1.20
        x0, x1 = xs[0] - ext, xs[-1] + ext
        y0, y1 = ys[0] - ext, ys[-1] + ext
        for y in ys:
            self.box_c((x0 + x1) / 2, y, 0.02, x1 - x0, 0.025,
                       0.012, gr)
        for x in xs:
            self.box_c(x, (y0 + y1) / 2, 0.02, 0.025, y1 - y0,
                       0.012, gr)
        for y in ys:
            for x in (x0, x1):
                self.tor(x, y, 0.03, 0.22, 0.018, 24, 8, gr)
        for x in xs:
            for y in (y0, y1):
                self.tor(x, y, 0.03, 0.22, 0.018, 24, 8, gr)

    def grid_labels(self):
        xs, ys = self.grid_lines()
        ext = 1.20
        x0, x1 = xs[0] - ext, xs[-1] + ext
        y0, y1 = ys[0] - ext, ys[-1] + ext
        items = []
        letters = "ABCDEFGHIJKLMN"
        for j, y in enumerate(ys):
            t = letters[j % len(letters)]
            items.append((f"GY{j}A", t, (x0, y, 0.05), 0.28))
            items.append((f"GY{j}B", t, (x1, y, 0.05), 0.28))
        for i, x in enumerate(xs):
            t = str(i + 1)
            items.append((f"GX{i}A", t, (x, y0, 0.05), 0.28))
            items.append((f"GX{i}B", t, (x, y1, 0.05), 0.28))
        return items

    # NIVELES
    def level_heights(self):
        p = self.props
        n = max(1, min(p.n_levels, 20))
        hs = [0.0]
        h = 0.0
        for i in range(1, n):
            h += max(p.h_first, 0.5) if i == 1 else max(
                p.h_typ, 0.5)
            hs.append(h)
        return hs

    def _build_levels(self):
        p = self.props
        gr = p.mat_grid
        for h in self.level_heights():
            self.box_c(0, 0, h, 6.0, 0.03, 0.015, gr)
            self.box_c(-3.0, 0, h + 0.14, 0.03, 0.03, 0.28,
                       gr)
            self.tor(-3.0, 0, h + 0.30, 0.16, 0.015, 20, 8,
                     gr)

    def level_labels(self):
        items = []
        for i, h in enumerate(self.level_heights()):
            items.append((f"LV{i}", f"N+{h:.2f}",
                          (-3.0, 0, h + 0.32), 0.22))
        return items

    def generate(self):
        t = self.props.item_type
        if t == 'FOOTING':
            self._build_footing()
        elif t == 'COLUMN':
            self._build_column()
        elif t == 'BEAM':
            self._build_beam()
        elif t == 'RIBBED_SLAB':
            self._build_ribbed_slab()
        elif t == 'GRID':
            self._build_grid()
        elif t == 'LEVELS':
            self._build_levels()
        return self.b


def _find_struct_object(props):
    name = props.object_name
    if name and name in bpy.data.objects:
        return bpy.data.objects[name]
    for obj in bpy.data.objects:
        if (obj.type == 'MESH' and hasattr(obj, AF_STRUCT_PROP)
                and getattr(obj, AF_STRUCT_PROP) is props):
            try:
                props.object_name = obj.name
            except Exception:
                pass
            return obj
    return None


def _rebuild_struct_mesh(obj, props):
    gen = AF_StructGenerator(props)
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
        poly.use_smooth = False
    try:
        mesh.update()
    except Exception:
        pass


def _sync_struct_labels(obj, props):
    """Rótulos FONT hijos para ejes y niveles. Limpia sobrantes."""
    try:
        gen = AF_StructGenerator(props)
        if props.item_type == 'GRID':
            items = gen.grid_labels()
        elif props.item_type == 'LEVELS':
            items = gen.level_labels()
        else:
            items = []
    except Exception:
        return
    try:
        keep = set()
        for suffix, text, loc, size in items:
            nm = f"{obj.name}@@{suffix}"
            keep.add(nm)
            fo = bpy.data.objects.get(nm)
            if fo is None or fo.type != 'FONT':
                if fo is not None:
                    bpy.data.objects.remove(fo, do_unlink=True)
                cu = bpy.data.curves.new(nm, type='FONT')
                fo = bpy.data.objects.new(nm, cu)
                bpy.context.collection.objects.link(fo)
            fo.data.body = text
            fo.data.size = size
            try:
                fo.data.align_x = 'CENTER'
                fo.data.align_y = 'CENTER'
            except Exception:
                pass
            fo.parent = obj
            fo.location = loc
        for o in list(bpy.data.objects):
            if o.name.startswith(obj.name + "@@") and \
                    o.name not in keep:
                bpy.data.objects.remove(o, do_unlink=True)
    except Exception:
        pass


def _setup_struct_materials(obj):
    af_material.ensure_af_materials_for_object(obj, [
        "AF.Struct.Concrete", "AF.Struct.Steel", "AF.Struct.Void",
        "AF.Struct.Grid",
    ])
    _tune_struct_materials()


def _tune_struct_materials():
    def _tune(name, base=None, metallic=None, rough=None,
              emission=None, emission_strength=None):
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
            if emission is not None and "Emission" in inp:
                inp["Emission"].default_value = emission
            if (emission_strength is not None
                    and "Emission Strength" in inp):
                inp["Emission Strength"].default_value = \
                    emission_strength
        except Exception:
            pass

    _tune("AF.Struct.Concrete", base=(0.60, 0.60, 0.61, 1.0),
          metallic=0.0, rough=0.85)
    _tune("AF.Struct.Steel", base=(0.25, 0.12, 0.08, 1.0),
          metallic=0.7, rough=0.5)
    _tune("AF.Struct.Void", base=(0.72, 0.42, 0.28, 1.0),
          metallic=0.0, rough=0.8)
    _tune("AF.Struct.Grid", base=(0.10, 0.50, 0.90, 1.0),
          emission=(0.10, 0.50, 0.90, 1.0), emission_strength=0.8)


def _create_struct_object(context, name="AF_Struct"):
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
        props = obj.archiforge_struct
        props.is_af_struct = True
        props.object_name = obj.name
        props.af_version = AF_STRUCT_VERSION
    finally:
        _SUSPEND = False
    _setup_struct_materials(obj)
    return obj, props


def _apply_type_defaults(props, item_type):
    global _SUSPEND
    w, d, h = AF_STRUCT_DEFAULTS.get(item_type, (0.3, 0.3, 2.4))
    _SUSPEND = True
    try:
        props.width = w
        props.depth = d
        props.height = h
    finally:
        _SUSPEND = False


class ARCHIFORGE_OT_structure(Operator):
    bl_idname = "archiforge.structure"
    bl_label = "Add AF Structure"
    bl_description = "Add a parametric ArchiForge structural element"
    bl_options = {'REGISTER', 'UNDO'}

    item_type : EnumProperty(name="Type", items=AF_STRUCT_TYPES,
                             default='COLUMN')
    auto_dimensions : BoolProperty(name="Real-World Dimensions",
                                   default=True)
    width : FloatProperty(name="Width", default=0.30, min=0.02,
                          unit='LENGTH')
    depth : FloatProperty(name="Depth", default=0.30, min=0.02,
                          unit='LENGTH')
    height : FloatProperty(name="Height", default=2.40, min=0.02,
                           unit='LENGTH')

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        col = layout.column(align=True)
        col.label(text="New Structural Element", icon='MESH_CUBE')
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
        obj, props = _create_struct_object(context, "AF_Struct")
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
        _rebuild_struct_mesh(obj, props)
        _sync_struct_labels(obj, props)
        self.report({'INFO'}, _tr("Structure created: {}").format(obj.name))
        return {'FINISHED'}


class ARCHIFORGE_OT_structure_update(Operator):
    bl_idname = "archiforge.structure_update"
    bl_label = "Update"
    bl_description = "Force regeneration of the element"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH'
                and hasattr(obj, AF_STRUCT_PROP)
                and obj.archiforge_struct.is_af_struct)

    def execute(self, context):
        obj = context.active_object
        _rebuild_struct_mesh(obj, obj.archiforge_struct)
        _sync_struct_labels(obj, obj.archiforge_struct)
        self.report({'INFO'}, _tr("Structure updated"))
        return {'FINISHED'}


class ARCHIFORGE_OT_structure_reset(Operator):
    bl_idname = "archiforge.structure_reset"
    bl_label = "Reset Dimensions"
    bl_description = "Reset to real-world default dimensions"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH'
                and hasattr(obj, AF_STRUCT_PROP)
                and obj.archiforge_struct.is_af_struct)

    def execute(self, context):
        obj = context.active_object
        props = obj.archiforge_struct
        _apply_type_defaults(props, props.item_type)
        _rebuild_struct_mesh(obj, props)
        _sync_struct_labels(obj, props)
        self.report({'INFO'}, _tr("Dimensions reset"))
        return {'FINISHED'}


class ARCHIFORGE_PT_structure(Panel):
    bl_label = "Structure Properties"
    bl_idname = "ARCHIFORGE_PT_structure"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "ArchiForge"
    bl_context = "objectmode"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH'
                and hasattr(obj, AF_STRUCT_PROP)
                and obj.archiforge_struct.is_af_struct)

    def draw_header(self, context):
        self.layout.label(text="", icon='MESH_CUBE')

    def draw(self, context):
        props = context.active_object.archiforge_struct
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        t = props.item_type

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Type", icon='MODIFIER')
        col.prop(props, "item_type", text="")
        col.prop(props, "mesh_quality", text="Quality")

        if t in ('FOOTING', 'COLUMN', 'BEAM'):
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Dimensions", icon='ARROW_LEFTRIGHT')
            if t == 'BEAM':
                col.prop(props, "width", text="Length")
                col.prop(props, "depth", text="Base")
                col.prop(props, "height", text="Height")
            elif t == 'COLUMN' and props.col_shape == 'ROUND':
                col.prop(props, "width", text="Diameter")
                col.prop(props, "height")
            else:
                col.prop(props, "width")
                col.prop(props, "depth")
                col.prop(props, "height")
            col.operator("archiforge.structure_reset",
                         text="Reset Real Dimensions",
                         icon='LOOP_BACK')

        if t == 'FOOTING':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Footing", icon='MESH_CUBE')
            col.prop(props, "footing_base_h")
            col.prop(props, "pedestal")
            col.prop(props, "rebar")

        if t == 'COLUMN':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Column", icon='MESH_CUBE')
            col.prop(props, "col_shape", text="")
            col.prop(props, "rebar")
            if props.rebar:
                col.prop(props, "stirrup_spacing")

        if t == 'BEAM':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Beam", icon='MESH_CUBE')
            col.prop(props, "rebar")
            if props.rebar:
                col.prop(props, "stirrup_spacing")

        if t == 'RIBBED_SLAB':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Ribbed Slab", icon='MESH_CUBE')
            col.prop(props, "width", text="Span X")
            col.prop(props, "depth", text="Span Y")
            col.prop(props, "joist_w")
            col.prop(props, "joist_h")
            col.prop(props, "joist_spacing")
            col.prop(props, "topping")
            col.prop(props, "edge_beam")
            col.prop(props, "rebar")

        if t == 'GRID':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Axes", icon='MESH_CUBE')
            col.prop(props, "grid_nx")
            col.prop(props, "grid_ny")
            col.prop(props, "grid_sx")
            col.prop(props, "grid_sy")

        if t == 'LEVELS':
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Levels", icon='MESH_CUBE')
            col.prop(props, "n_levels")
            col.prop(props, "h_first")
            col.prop(props, "h_typ")

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Material Slots", icon='MATERIAL')
        col.prop(props, "mat_concrete", text="Concrete")
        if t in ('FOOTING', 'COLUMN', 'BEAM', 'RIBBED_SLAB'):
            col.prop(props, "mat_steel", text="Steel")
        if t == 'RIBBED_SLAB':
            col.prop(props, "mat_void", text="Void")
        if t in ('GRID', 'LEVELS'):
            col.prop(props, "mat_grid", text="Grid")

        layout.separator()
        layout.operator("archiforge.structure_update",
                        text="Force Update", icon='FILE_REFRESH')


classes = [
    AF_StructProperties,
    ARCHIFORGE_OT_structure,
    ARCHIFORGE_OT_structure_update,
    ARCHIFORGE_OT_structure_reset,
    ARCHIFORGE_PT_structure,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Object.archiforge_struct = PointerProperty(
        type=AF_StructProperties,
        name="ArchiForge Structure",
        description="ArchiForge structure properties",
    )
    print("[ArchiForge] af_structure v1 - registered")


def unregister():
    if hasattr(bpy.types.Object, "archiforge_struct"):
        del bpy.types.Object.archiforge_struct
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    print("[ArchiForge] af_structure - unregistered")
