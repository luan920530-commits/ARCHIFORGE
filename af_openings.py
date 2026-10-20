# -*- coding: utf-8 -*-
"""ArchiForge — Puertas y ventanas paramétricas + vanos en muros.

v1.0 — Blender 3.3 LTS.
Origen en piso, frente -Y. Ancho=comercial CO, depth=grosor muro.
Corte en muro vía booleana con objeto cutter hijo (oculto).
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

try:
    from .af_icons import icon_kw as _icon, item_icon as _item_icon
except ImportError:  # pragma: no cover - fuera del paquete
    def _icon(name, fallback='MESH_CUBE', icons=None):
        return {'icon': fallback}

    def _item_icon(item_type, default=None):
        return default

AF_OPEN_PROP = "archiforge_opening"
AF_OPEN_VERSION = 1

AF_OPEN_TYPES = [
    ('DOOR_SINGLE', "Single Door", "Puerta batiente 1 hoja"),
    ('DOOR_DOUBLE', "Double Door", "Puerta batiente 2 hojas"),
    ('DOOR_SLIDING', "Sliding Door", "Puerta corrediza 2 hojas"),
    ('WIN_SLIDING', "Sliding Window", "Ventana corrediza"),
    ('WIN_CASEMENT', "Casement Window", "Ventana batiente"),
    ('WIN_FIXED', "Fixed Window", "Ventana fija + antepecho"),
]

AF_OPEN_DEFAULTS = {
    'DOOR_SINGLE': (0.90, 0.15, 2.10),
    'DOOR_DOUBLE': (1.40, 0.15, 2.10),
    'DOOR_SLIDING': (1.60, 0.15, 2.10),
    'WIN_SLIDING': (1.50, 0.15, 1.20),
    'WIN_CASEMENT': (1.00, 0.15, 1.20),
    'WIN_FIXED': (1.20, 0.15, 1.00),
}

AF_DOOR_STYLES = [
    ('PANEL', "Tableros", "Hoja con tableros hundidos"),
    ('FLUSH', "Lisa", "Hoja lisa contemporánea"),
    ('GLASS', "Con vidrio", "Hoja con inserto en vidrio"),
]

_SUSPEND = False


def af_opening_update(self, context):
    if _SUSPEND:
        return
    try:
        from .af_openings import _find_opening_object as _find
        from .af_openings import _rebuild_opening_mesh as _rb
        from .af_openings import _apply_wall_cut as _cut
    except ImportError:
        return
    props = self if hasattr(self, "is_af_opening") else None
    if props is None:
        return
    obj = _find(props)
    if obj is None:
        obj = context.active_object if context else None
    if obj is None or obj.type != 'MESH':
        return
    if not getattr(obj, AF_OPEN_PROP, None):
        return
    _rb(obj, props)
    _cut(obj, props)


class AF_OpeningProperties(PropertyGroup):
    is_af_opening : BoolProperty(default=True, options={'HIDDEN'})
    object_name : StringProperty(default="", options={'HIDDEN'})
    af_version : IntProperty(default=AF_OPEN_VERSION,
                             options={'HIDDEN'})

    item_type : EnumProperty(name="Type", items=AF_OPEN_TYPES,
                             default='DOOR_SINGLE',
                             update=af_opening_update)
    mesh_quality : EnumProperty(
        name="Quality",
        items=[('LOW', "Low", ""), ('MEDIUM', "Medium", ""),
               ('HIGH', "High", "")],
        default='MEDIUM', update=af_opening_update)

    width : FloatProperty(name="Width", default=0.90, min=0.30,
                          max=4.0, unit='LENGTH',
                          update=af_opening_update)
    depth : FloatProperty(name="Wall Thick.", default=0.15,
                          min=0.05, max=0.60, unit='LENGTH',
                          update=af_opening_update)
    height : FloatProperty(name="Height", default=2.10, min=0.40,
                           max=3.0, unit='LENGTH',
                           update=af_opening_update)
    sill_height : FloatProperty(name="Sill Height", default=0.90,
                                min=0.0, max=2.0, unit='LENGTH',
                                update=af_opening_update)

    door_style : EnumProperty(name="Leaf Style", items=AF_DOOR_STYLES,
                              default='PANEL',
                              update=af_opening_update)
    leaf_count : IntProperty(name="Leaves", default=2, min=1,
                             max=3, update=af_opening_update)
    handle_side : EnumProperty(
        name="Hinge Side",
        items=[('LEFT', "Left", ""), ('RIGHT', "Right", "")],
        default='LEFT', update=af_opening_update)
    open_fraction : FloatProperty(name="Slide Open", default=0.25,
                                  min=0.0, max=0.5,
                                  update=af_opening_update,
                                  description="Sliding leaf offset (0-0.5)")
    open_angle : FloatProperty(name="Open Angle", default=0.0,
                               min=0.0, max=1.5708, subtype='ANGLE',
                               update=af_opening_update)

    sill_board : BoolProperty(name="Sill Board", default=True,
                              update=af_opening_update)
    lintel : BoolProperty(name="Lintel", default=False,
                          update=af_opening_update)

    target_wall : StringProperty(
        name="Target Wall", default="", update=af_opening_update,
    )
    cut_opening : BoolProperty(name="Cut in Wall", default=False,
                               update=af_opening_update)

    mat_frame : IntProperty(name="Frame Mat", default=0, min=0,
                            max=7, update=af_opening_update)
    mat_leaf : IntProperty(name="Leaf Mat", default=1, min=0,
                           max=7, update=af_opening_update)
    mat_glass : IntProperty(name="Glass Mat", default=2, min=0,
                            max=7, update=af_opening_update)
    mat_metal : IntProperty(name="Metal Mat", default=3, min=0,
                            max=7, update=af_opening_update)


class AF_OpeningGenerator:
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

    def box_t(self, m, x0, x1, y0, y1, z0, z1, mi):
        self.b.box(x0, x1, y0, y1, z0, z1, mi, transform=m)

    def cyl(self, cx, cy, z0, z1, r, base_seg=16, mi=0):
        self.b.cylinder(cx, cy, z0, max(z1, z0 + 0.001),
                        max(r, 0.0012), segments=self.seg(base_seg),
                        mi=mi)

    def hinge_m(self, xh, yh, zh, ang):
        m = Matrix.Translation(Vector((xh, yh, zh)))
        m = m @ Matrix.Rotation(ang, 4, 'Z')
        return m

    def _frame(self, w, d, h, z0, fw, frm, full_bottom=False):
        for sx in (-1, 1):
            self.box_c(sx * (w / 2 - fw / 2), 0, z0 + h / 2,
                       fw, d, h, frm)
        self.box_c(0, 0, z0 + h - fw / 2, w, d, fw, frm)
        if full_bottom:
            self.box_c(0, 0, z0 + fw / 2, w, d, fw, frm)

    def _architrave(self, w, d, h, z0, frm):
        for sz in (-1, 1):
            y = sz * (d / 2 + 0.008)
            for sx in (-1, 1):
                self.box_c(sx * (w / 2 + 0.025), y, z0 + h / 2,
                           0.07, 0.016, h + 0.05, frm)
            self.box_c(0, y, z0 + h + 0.025, w + 0.12, 0.016,
                       0.07, frm)

    def _door_leaf(self, m, sgn, lw, lh, lt, style, leaf, gla,
                   met, handle=True):
        x0, x1 = (0, lw) if sgn > 0 else (-lw, 0)
        if style == 'GLASS':
            st = 0.09
            self.box_t(m, x0, x0 + sgn * st, -lt / 2, lt / 2, 0,
                       lh, leaf)
            self.box_t(m, x1 - sgn * st, x1, -lt / 2, lt / 2, 0,
                       lh, leaf)
            self.box_t(m, x0, x1, -lt / 2, lt / 2, 0, 0.25,
                       leaf)
            self.box_t(m, x0, x1, -lt / 2, lt / 2, lh - 0.18,
                       lh, leaf)
            self.box_t(m, min(x0, x1) + st, max(x0, x1) - st,
                       -0.006, 0.006, 0.25, lh - 0.18, gla)
        else:
            self.box_t(m, x0, x1, -lt / 2, lt / 2, 0, lh, leaf)
            if style == 'PANEL':
                pw = (lw - 0.24) / 2
                for r in range(2):
                    zz = 0.35 + r * (lh / 2 - 0.10)
                    for c in range(2):
                        cx = (x0 + x1) / 2 + (c - 0.5) * (pw +
                                                          0.04)
                        self.box_t(m, cx - pw / 2, cx + pw / 2,
                                   -lt / 2 - 0.006, -lt / 2,
                                   zz, zz + lh / 2 - 0.30, leaf)
        if handle:
            hx = (x1 - sgn * 0.12)
            for sy in (-1, 1):
                self.box_t(m, hx - 0.025, hx + 0.025,
                           sy * lt / 2, sy * (lt / 2 + 0.008),
                           0.95, 1.10, met)
                self.box_t(m, hx - 0.11, hx,
                           sy * (lt / 2 + 0.008),
                           sy * (lt / 2 + 0.028), 1.045, 1.07,
                           met)

    # PUERTA BATIENTE 1 HOJA
    def _build_door_single(self):
        p = self.props
        frm, leaf = p.mat_frame, p.mat_leaf
        gla, met = p.mat_glass, p.mat_metal
        w, d, h = max(p.width, 0.4), max(p.depth, 0.05), max(
            p.height, 1.0)
        fw = 0.06
        self._frame(w, d, h, 0.0, fw, frm)
        self._architrave(w, d, h, 0.0, frm)
        sgn = 1 if p.handle_side == 'LEFT' else -1
        xh = -sgn * (w / 2 - fw)
        lw = w - 2 * fw - 0.012
        m = self.hinge_m(xh, 0, 0.008, -sgn * p.open_angle)
        self._door_leaf(m, sgn, lw, h - fw - 0.018, 0.045,
                        p.door_style, leaf, gla, met)
        for hz in (0.25, h / 2, h - 0.25):
            self.box_c(xh + sgn * 0.01, 0, hz, 0.03, d + 0.01,
                       0.09, met)
        if p.lintel:
            self.box_c(0, 0, h + 0.10, w + 0.30, d, 0.20, frm)

    # PUERTA BATIENTE 2 HOJAS
    def _build_door_double(self):
        p = self.props
        frm, leaf = p.mat_frame, p.mat_leaf
        gla, met = p.mat_glass, p.mat_metal
        w, d, h = max(p.width, 0.8), max(p.depth, 0.05), max(
            p.height, 1.0)
        fw = 0.06
        self._frame(w, d, h, 0.0, fw, frm)
        self._architrave(w, d, h, 0.0, frm)
        lw = (w - 2 * fw - 0.016) / 2
        for sgn in (1, -1):
            xh = -sgn * (w / 2 - fw)
            m = self.hinge_m(xh, 0, 0.008, -sgn * p.open_angle)
            self._door_leaf(m, sgn, lw, h - fw - 0.018, 0.045,
                            p.door_style, leaf, gla, met)
            for hz in (0.25, h / 2, h - 0.25):
                self.box_c(xh + sgn * 0.01, 0, hz, 0.03,
                           d + 0.01, 0.09, met)
        if p.lintel:
            self.box_c(0, 0, h + 0.10, w + 0.30, d, 0.20, frm)

    def _win_leaf(self, m, x0, x1, zl0, zl1, lt, frm, gla):
        st = 0.045
        xa, xb = min(x0, x1), max(x0, x1)
        self.box_t(m, xa, xa + st, -lt / 2, lt / 2, zl0, zl1,
                   frm)
        self.box_t(m, xb - st, xb, -lt / 2, lt / 2, zl0, zl1,
                   frm)
        self.box_t(m, xa, xb, -lt / 2, lt / 2, zl0, zl0 + st,
                   frm)
        self.box_t(m, xa, xb, -lt / 2, lt / 2, zl1 - st, zl1,
                   frm)
        self.box_t(m, xa + st, xb - st, -0.004, 0.004,
                   zl0 + st, zl1 - st, gla)

    def _tracks(self, w, d, z0, h, met):
        for zz in (z0 + 0.008, z0 + h - 0.008):
            self.box_c(0, 0, zz, w, d + 0.07, 0.016, met)

    def _sillboard(self, w, d, z0, frm):
        self.box_c(0, 0.01, z0 - 0.02, w + 0.08, d + 0.10,
                   0.04, frm)
        self.box_c(0, -(d / 2 + 0.035), z0 - 0.045, w + 0.08,
                   0.02, 0.03, frm)

    # PUERTA CORREDIZA
    def _build_door_sliding(self):
        p = self.props
        frm, gla, met = p.mat_frame, p.mat_glass, p.mat_metal
        w, d, h = max(p.width, 0.8), max(p.depth, 0.05), max(
            p.height, 1.0)
        fw = 0.06
        self._frame(w, d, h, 0.0, fw, frm)
        self._tracks(w - 2 * fw, d, 0.0, h, met)
        lw = (w - 2 * fw) / 2 + 0.03
        x0 = -w / 2 + fw
        z0, z1 = 0.02, h - fw - 0.005
        ide = Matrix.Identity(4)
        self._win_leaf(ide, x0, x0 + lw, z0, z1, 0.04, frm,
                       gla)
        sh = p.open_fraction * w
        m2 = Matrix.Translation(Vector((sh, 0.056, 0)))
        self._win_leaf(m2, x0, x0 + lw, z0, z1, 0.04, frm,
                       gla)
        for hx, hy in ((x0 + lw - 0.10, -0.028),
                       (x0 + sh + 0.10, 0.084)):
            self.box_c(hx, hy, 1.00, 0.025, 0.025, 0.30, met)
        if p.lintel:
            self.box_c(0, 0, h + 0.10, w + 0.30, d, 0.20, frm)

    # VENTANA CORREDIZA
    def _build_win_sliding(self):
        p = self.props
        frm, gla, met = p.mat_frame, p.mat_glass, p.mat_metal
        w, d, h = max(p.width, 0.4), max(p.depth, 0.05), max(
            p.height, 0.4)
        z0 = max(p.sill_height, 0.0)
        fw = 0.055
        self._frame(w, d, h, z0, fw, frm, full_bottom=True)
        self._tracks(w - 2 * fw, d, z0 + fw, h - 2 * fw, met)
        n = max(1, min(p.leaf_count, 3))
        lw = (w - 2 * fw) / 2 + 0.025
        x0 = -w / 2 + fw
        ide = Matrix.Identity(4)
        self._win_leaf(ide, x0, x0 + lw, z0 + fw + 0.005,
                       z0 + h - fw - 0.005, 0.035, frm, gla)
        if n >= 2:
            sh = p.open_fraction * w
            m2 = Matrix.Translation(Vector((sh, 0.048, 0)))
            self._win_leaf(m2, x0, x0 + lw, z0 + fw + 0.005,
                           z0 + h - fw - 0.005, 0.035, frm,
                           gla)
        if p.sill_board:
            self._sillboard(w, d, z0, frm)
        if p.lintel:
            self.box_c(0, 0, z0 + h + 0.10, w + 0.30, d, 0.20,
                       frm)

    # VENTANA BATIENTE
    def _build_win_casement(self):
        p = self.props
        frm, gla, met = p.mat_frame, p.mat_glass, p.mat_metal
        w, d, h = max(p.width, 0.4), max(p.depth, 0.05), max(
            p.height, 0.4)
        z0 = max(p.sill_height, 0.0)
        fw = 0.055
        self._frame(w, d, h, z0, fw, frm, full_bottom=True)
        n = max(1, min(p.leaf_count, 3))
        iw = w - 2 * fw - 0.01
        zl0, zl1 = z0 + fw + 0.005, z0 + h - fw - 0.005
        for i in range(n):
            xa = -iw / 2 + i * iw / n
            xb = -iw / 2 + (i + 1) * iw / n
            sgn = 1 if (i % 2 == 0) else -1
            if n == 1:
                sgn = 1 if p.handle_side == 'LEFT' else -1
            xh = xa if sgn > 0 else xb
            m = self.hinge_m(xh, 0, 0, -sgn * p.open_angle)
            self._win_leaf(m, 0 if sgn > 0 else -(xb - xa),
                           (xb - xa) if sgn > 0 else 0, zl0,
                           zl1, 0.04, frm, gla)
            # The handle rides on the leaf: express it in hinge-local
            # coordinates and apply the same transform as the sash.
            hx = (xb - 0.09 if sgn > 0 else xa + 0.09) - xh
            zc = (zl0 + zl1) / 2
            self.box_t(m, hx - 0.01, hx + 0.01, -0.045, -0.015,
                       zc - 0.07, zc + 0.07, met)
        if p.sill_board:
            self._sillboard(w, d, z0, frm)
        if p.lintel:
            self.box_c(0, 0, z0 + h + 0.10, w + 0.30, d, 0.20,
                       frm)

    # VENTANA FIJA
    def _build_win_fixed(self):
        p = self.props
        frm, gla = p.mat_frame, p.mat_glass
        w, d, h = max(p.width, 0.4), max(p.depth, 0.05), max(
            p.height, 0.4)
        z0 = max(p.sill_height, 0.0)
        fw = 0.055
        self._frame(w, d, h, z0, fw, frm, full_bottom=True)
        self.box_c(0, 0, z0 + h / 2, w - 2 * fw, 0.008,
                   h - 2 * fw, gla)
        if w > 1.0:
            self.box_c(0, 0, z0 + h / 2, 0.05, 0.03, h - 2 *
                       fw, frm)
        if h > 0.9:
            self.box_c(0, 0, z0 + h / 2, w - 2 * fw, 0.03,
                       0.05, frm)
        if p.sill_board:
            self._sillboard(w, d, z0, frm)
        if p.lintel:
            self.box_c(0, 0, z0 + h + 0.10, w + 0.30, d, 0.20,
                       frm)

    def generate(self):
        t = self.props.item_type
        if t == 'DOOR_SINGLE':
            self._build_door_single()
        elif t == 'DOOR_DOUBLE':
            self._build_door_double()
        elif t == 'DOOR_SLIDING':
            self._build_door_sliding()
        elif t == 'WIN_SLIDING':
            self._build_win_sliding()
        elif t == 'WIN_CASEMENT':
            self._build_win_casement()
        elif t == 'WIN_FIXED':
            self._build_win_fixed()
        return self.b


def _find_opening_object(props):
    name = props.object_name
    if name and name in bpy.data.objects:
        return bpy.data.objects[name]
    for obj in bpy.data.objects:
        if (obj.type == 'MESH' and hasattr(obj, AF_OPEN_PROP)
                and getattr(obj, AF_OPEN_PROP) is props):
            try:
                props.object_name = obj.name
            except Exception:
                pass
            return obj
    return None


def _rebuild_opening_mesh(obj, props):
    gen = AF_OpeningGenerator(props)
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
        poly.use_smooth = True
    try:
        mesh.update()
    except Exception:
        pass


def _find_opening_cutters(obj):
    """Find this opening's cutter(s), including pre-marker legacy objects."""
    cutters = []
    expected_name = obj.name + "_CUTTER"
    for candidate in bpy.data.objects:
        try:
            tagged = bool(candidate.get("archiforge_opening_cutter", False))
            owner = candidate.get("archiforge_opening_owner", "")
        except (AttributeError, TypeError):
            tagged = False
            owner = ""
        if (candidate.parent is obj and
                (tagged or candidate.name == expected_name
                 or candidate.name.endswith("_CUTTER"))):
            cutters.append(candidate)
        elif tagged and owner == obj.name:
            cutters.append(candidate)
    return cutters


def _remove_opening_cutters(obj, cutters):
    """Remove managed Boolean modifiers before deleting their cutter meshes."""
    modifier_name = "AF_CUT_" + obj.name
    if len(modifier_name) > 60:
        modifier_name = modifier_name[:60]
    for target in list(bpy.data.objects):
        for modifier in list(target.modifiers):
            if modifier.type != 'BOOLEAN':
                continue
            if (modifier.object in cutters
                    or modifier.name == modifier_name):
                try:
                    target.modifiers.remove(modifier)
                except (ReferenceError, RuntimeError, TypeError):
                    pass

    for cutter in cutters:
        mesh = cutter.data if cutter.type == 'MESH' else None
        try:
            bpy.data.objects.remove(cutter, do_unlink=True)
        except (ReferenceError, RuntimeError, TypeError):
            continue
        if mesh is not None and mesh.users == 0:
            try:
                bpy.data.meshes.remove(mesh)
            except (ReferenceError, RuntimeError, TypeError):
                pass


def _apply_wall_cut(obj, props):
    """Maintain a live DIFFERENCE Boolean on the selected target wall."""
    cutters = _find_opening_cutters(obj)
    wall = None
    if props.cut_opening and props.target_wall:
        wall = bpy.data.objects.get(props.target_wall)
        if (wall is None or wall.type != 'MESH' or wall is obj):
            wall = None

    if wall is None:
        _remove_opening_cutters(obj, cutters)
        return

    # Reuse a single cutter and remove stale duplicates/modifiers when the
    # target wall changes or the file contains legacy duplicate cutters.
    old_cut = cutters[0] if cutters else None
    if len(cutters) > 1:
        _remove_opening_cutters(obj, cutters[1:])

    cut_name = obj.name + "_CUTTER"
    if old_cut is None:
        mesh = bpy.data.meshes.new(cut_name)
        old_cut = bpy.data.objects.new(cut_name, mesh)
        try:
            collection = (obj.users_collection[0] if obj.users_collection
                          else bpy.context.collection)
            collection.objects.link(old_cut)
            mesh.from_pydata(
                [
                    (-0.5, -0.5, -0.5), (0.5, -0.5, -0.5),
                    (0.5, 0.5, -0.5), (-0.5, 0.5, -0.5),
                    (-0.5, -0.5, 0.5), (0.5, -0.5, 0.5),
                    (0.5, 0.5, 0.5), (-0.5, 0.5, 0.5),
                ],
                [],
                [
                    (0, 3, 2, 1), (4, 5, 6, 7),
                    (0, 1, 5, 4), (2, 3, 7, 6),
                    (0, 4, 7, 3), (1, 2, 6, 5),
                ],
            )
            mesh.update()
        except Exception:
            try:
                bpy.data.objects.remove(old_cut, do_unlink=True)
            except Exception:
                pass
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)
            return

    # Remove any modifier this opening previously left on another wall.
    for target in list(bpy.data.objects):
        for modifier in list(target.modifiers):
            if modifier.type == 'BOOLEAN' and modifier.object is old_cut:
                if target is not wall:
                    try:
                        target.modifiers.remove(modifier)
                    except (ReferenceError, RuntimeError, TypeError):
                        pass

    is_window = props.item_type.startswith('WIN')
    sill = max(float(props.sill_height), 0.0) if is_window else 0.0
    width = max(float(props.width), 0.1)
    height = max(float(props.height), 0.1)
    depth = max(float(props.depth), 0.05)
    cutter_width = width + 0.02
    cutter_height = height + 0.02
    cutter_depth = depth + 0.40

    old_cut.parent = obj
    old_cut.matrix_parent_inverse = Matrix.Identity(4)
    old_cut.location = (0.0, 0.0, sill + height * 0.5)
    old_cut.rotation_euler = (0.0, 0.0, 0.0)
    old_cut.scale = (cutter_width, cutter_depth, cutter_height)
    old_cut.hide_render = True
    old_cut.hide_set(True)
    old_cut.display_type = 'WIRE'
    old_cut["archiforge_opening_cutter"] = True
    old_cut["archiforge_opening_owner"] = obj.name

    modifier_name = "AF_CUT_" + obj.name
    if len(modifier_name) > 60:
        modifier_name = modifier_name[:60]
    modifier = None
    for existing in list(wall.modifiers):
        if (existing.type == 'BOOLEAN'
                and (existing.object is old_cut
                     or existing.name == modifier_name)):
            modifier = existing
            break
    if modifier is None:
        try:
            modifier = wall.modifiers.new(modifier_name, 'BOOLEAN')
        except Exception:
            _remove_opening_cutters(obj, [old_cut])
            return

    try:
        modifier.operation = 'DIFFERENCE'
        modifier.object = old_cut
        if hasattr(modifier, 'solver'):
            modifier.solver = 'EXACT'
        modifier.show_viewport = True
        modifier.show_render = True
    except (AttributeError, ReferenceError, RuntimeError, TypeError):
        _remove_opening_cutters(obj, [old_cut])
        return

    try:
        bpy.context.view_layer.update()
    except (AttributeError, RuntimeError, TypeError):
        pass


def _setup_opening_materials(obj):
    af_material.ensure_af_materials_for_object(obj, [
        "AF.Open.Frame", "AF.Open.Leaf", "AF.Open.Glass",
        "AF.Open.Metal",
    ])
    _tune_opening_materials()


def _tune_opening_materials():
    def _tune(name, base=None, metallic=None, rough=None,
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
        except Exception:
            pass

    _tune("AF.Open.Frame", base=(0.88, 0.88, 0.89, 1.0),
          metallic=0.6, rough=0.4)
    _tune("AF.Open.Leaf", base=(0.45, 0.30, 0.18, 1.0),
          metallic=0.0, rough=0.6)
    _tune("AF.Open.Glass", base=(0.85, 0.92, 0.95, 1.0),
          metallic=0.0, rough=0.05, transmission=0.92)
    _tune("AF.Open.Metal", base=(0.15, 0.15, 0.16, 1.0),
          metallic=0.9, rough=0.35)


def _create_opening_object(context, name="AF_Opening"):
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
    previous_suspend = _SUSPEND
    _SUSPEND = True
    try:
        props = obj.archiforge_opening
        props.is_af_opening = True
        props.object_name = obj.name
        props.af_version = AF_OPEN_VERSION
    finally:
        _SUSPEND = previous_suspend
    _setup_opening_materials(obj)
    return obj, props


def _apply_type_defaults(props, item_type):
    global _SUSPEND
    w, d, h = AF_OPEN_DEFAULTS.get(item_type, (0.9, 0.15, 2.1))
    previous_suspend = _SUSPEND
    _SUSPEND = True
    try:
        props.width = w
        props.depth = d
        props.height = h
    finally:
        _SUSPEND = previous_suspend


class ARCHIFORGE_OT_opening(Operator):
    bl_idname = "archiforge.opening"
    bl_label = "Add AF Opening"
    bl_description = "Add a parametric ArchiForge door/window"
    bl_options = {'REGISTER', 'UNDO'}

    item_type : EnumProperty(name="Type", items=AF_OPEN_TYPES,
                             default='DOOR_SINGLE')
    auto_dimensions : BoolProperty(name="Real-World Dimensions",
                                   default=True)
    width : FloatProperty(name="Width", default=0.90, min=0.10,
                          unit='LENGTH')
    depth : FloatProperty(name="Wall Thick.", default=0.15,
                          min=0.05, unit='LENGTH')
    height : FloatProperty(name="Height", default=2.10, min=0.10,
                           unit='LENGTH')
    cut_opening : BoolProperty(name="Cut in Target Wall", default=False)
    target_wall : StringProperty(name="Target Wall", default="")

    def invoke(self, context, event):
        active = context.active_object
        wall_props = getattr(active, "archiforge_wall", None)
        if (not self.target_wall and active is not None
                and active.type == 'MESH' and wall_props is not None
                and wall_props.is_af_wall
                and wall_props.object_name == active.name):
            self.target_wall = active.name
            self.cut_opening = True
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        col = layout.column(align=True)
        col.label(text="New Door / Window",
                  **_icon(_item_icon(self.item_type, "opening"), 'MESH_CUBE'))
        col.prop(self, "item_type")
        col.separator()
        col.prop(self, "auto_dimensions")
        sub = col.column(align=True)
        sub.enabled = not self.auto_dimensions
        sub.prop(self, "width")
        sub.prop(self, "depth")
        sub.prop(self, "height")
        col.separator()
        col.prop(self, "cut_opening")
        target = col.column(align=True)
        target.enabled = self.cut_opening
        target.prop_search(self, "target_wall", context.blend_data,
                           "objects", text="Wall")

    def execute(self, context):
        global _SUSPEND
        active_before_create = context.active_object
        target_wall = self.target_wall
        cut_opening = self.cut_opening
        wall_props = getattr(active_before_create, "archiforge_wall", None)
        if (not target_wall and active_before_create is not None
                and active_before_create.type == 'MESH'
                and wall_props is not None and wall_props.is_af_wall
                and wall_props.object_name == active_before_create.name):
            target_wall = active_before_create.name
            cut_opening = True
        obj, props = _create_opening_object(context, "AF_Opening")
        previous_suspend = _SUSPEND
        _SUSPEND = True
        try:
            props.item_type = self.item_type
            if self.auto_dimensions:
                _apply_type_defaults(props, self.item_type)
            else:
                props.width = self.width
                props.depth = self.depth
                props.height = self.height
            props.target_wall = target_wall
            props.cut_opening = cut_opening
        finally:
            _SUSPEND = previous_suspend
        _rebuild_opening_mesh(obj, props)
        _apply_wall_cut(obj, props)
        self.report({'INFO'}, _tr("Opening created: {}").format(obj.name))
        return {'FINISHED'}


class ARCHIFORGE_OT_opening_update(Operator):
    bl_idname = "archiforge.opening_update"
    bl_label = "Update"
    bl_description = "Force regeneration of the opening"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH'
                and hasattr(obj, AF_OPEN_PROP)
                and obj.archiforge_opening.is_af_opening)

    def execute(self, context):
        obj = context.active_object
        _rebuild_opening_mesh(obj, obj.archiforge_opening)
        _apply_wall_cut(obj, obj.archiforge_opening)
        self.report({'INFO'}, _tr("Opening updated"))
        return {'FINISHED'}


class ARCHIFORGE_OT_opening_reset(Operator):
    bl_idname = "archiforge.opening_reset"
    bl_label = "Reset Dimensions"
    bl_description = "Reset to real-world default dimensions"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH'
                and hasattr(obj, AF_OPEN_PROP)
                and obj.archiforge_opening.is_af_opening)

    def execute(self, context):
        obj = context.active_object
        props = obj.archiforge_opening
        _apply_type_defaults(props, props.item_type)
        _rebuild_opening_mesh(obj, props)
        _apply_wall_cut(obj, props)
        self.report({'INFO'}, _tr("Dimensions reset"))
        return {'FINISHED'}


class ARCHIFORGE_PT_opening(Panel):
    bl_label = "Opening Properties"
    bl_idname = "ARCHIFORGE_PT_opening"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "ArchiForge"
    bl_context = "objectmode"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH'
                and hasattr(obj, AF_OPEN_PROP)
                and obj.archiforge_opening.is_af_opening)

    def draw_header(self, context):
        self.layout.label(text="", **_icon("opening", 'MESH_CUBE'))

    def draw(self, context):
        props = context.active_object.archiforge_opening
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        t = props.item_type
        is_door = t.startswith('DOOR')
        is_win = t.startswith('WIN')

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Type",
                  **_icon(_item_icon(props.item_type, "opening"), 'MODIFIER'))
        col.prop(props, "item_type", text="")
        col.prop(props, "mesh_quality", text="Quality")

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Dimensions", icon='ARROW_LEFTRIGHT')
        col.prop(props, "width")
        col.prop(props, "depth")
        col.prop(props, "height")
        if is_win:
            col.prop(props, "sill_height")
        col.operator("archiforge.opening_reset",
                     text="Reset Real Dimensions", icon='LOOP_BACK')

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Leaves",
                  **_icon(_item_icon(t, "opening"), 'MESH_CUBE'))
        if is_door and t != 'DOOR_SLIDING':
            col.prop(props, "door_style", text="")
            col.prop(props, "handle_side", text="")
            col.prop(props, "open_angle")
        if is_win and t == 'WIN_CASEMENT':
            col.prop(props, "open_angle")
        if t in ('DOOR_SLIDING', 'WIN_SLIDING'):
            col.prop(props, "open_fraction")
        if is_win and t != 'WIN_FIXED':
            col.prop(props, "leaf_count")
        if is_win:
            col.prop(props, "sill_board")
        col.prop(props, "lintel")

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Wall Opening", **_icon("boolean", 'MOD_BOOLEAN'))
        col.prop(props, "cut_opening")
        sub = col.column(align=True)
        sub.enabled = props.cut_opening
        sub.prop_search(props, "target_wall", context.blend_data,
                        "objects", text="Wall")

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Material Slots", icon='MATERIAL')
        col.prop(props, "mat_frame", text="Frame")
        if is_door and t != 'DOOR_SLIDING':
            col.prop(props, "mat_leaf", text="Leaf")
        col.prop(props, "mat_glass", text="Glass")
        col.prop(props, "mat_metal", text="Metal")

        layout.separator()
        layout.operator("archiforge.opening_update",
                        text="Force Update", icon='FILE_REFRESH')


classes = [
    AF_OpeningProperties,
    ARCHIFORGE_OT_opening,
    ARCHIFORGE_OT_opening_update,
    ARCHIFORGE_OT_opening_reset,
    ARCHIFORGE_PT_opening,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Object.archiforge_opening = PointerProperty(
        type=AF_OpeningProperties,
        name="ArchiForge Opening",
        description="ArchiForge opening properties",
    )
    print("[ArchiForge] af_openings v1 - registered")


def unregister():
    if hasattr(bpy.types.Object, "archiforge_opening"):
        del bpy.types.Object.archiforge_opening
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    print("[ArchiForge] af_openings - unregistered")
