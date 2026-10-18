# -*- coding: utf-8 -*-

# ╔══════════════════════════════════════════════════════════╗
# ║         ARCHIFORGE — af_objects_base.py                 ║
# ║         Constructores geométricos compartidos           ║
# ║         GPL v3 — ArchiForge Devs                        ║
# ╚══════════════════════════════════════════════════════════╝

# <pep8 compliant>

import bmesh
import math

from mathutils import Vector, Matrix


class AF_ObjectBuilder:
    """
    Constructor geométrico compartido.

    Todas las primitivas escriben el material_index NATIVO del bmesh
    (f.material_index = mi). Al llamar a bm.to_mesh(me), Blender
    transfiere automáticamente el material_index a la malla final.
    No hace falta usar custom layers ni copiar a mano.
    """

    def __init__(self):
        self.bm = bmesh.new()

    # ────────────────────────────────────────────────────────
    #  Primitivas
    # ────────────────────────────────────────────────────────
    def _face(self, verts, mi=0):
        try:
            f = self.bm.faces.new(verts)
            f.material_index = mi
            return f
        except ValueError:
            return None

    def box(self, x0, x1, y0, y1, z0, z1, mi=0, transform=None):
        if (abs(x1 - x0) < 1e-5
                or abs(y1 - y0) < 1e-5
                or abs(z1 - z0) < 1e-5):
            return

        corners = [
            (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
            (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
        ]
        if transform:
            corners = [transform @ Vector(c) for c in corners]
        else:
            corners = [Vector(c) for c in corners]

        bv = [self.bm.verts.new(v) for v in corners]
        self.bm.verts.ensure_lookup_table()

        for fi in [(0,1,5,4),(2,3,7,6),(0,3,2,1),
                   (4,5,6,7),(0,4,7,3),(1,2,6,5)]:
            self._face([bv[i] for i in fi], mi)

    def cylinder(self, cx, cy, z0, z1, radius,
                 segments=16, mi=0, cap=True, transform=None):
        if abs(z1 - z0) < 1e-5 or radius < 1e-5:
            return

        segs = max(3, segments)
        a_step = 2 * math.pi / segs
        bot, top = [], []

        for i in range(segs):
            a = i * a_step
            x = cx + radius * math.cos(a)
            y = cy + radius * math.sin(a)
            pb = Vector((x, y, z0))
            pt = Vector((x, y, z1))
            if transform:
                pb = transform @ pb
                pt = transform @ pt
            bot.append(self.bm.verts.new(pb))
            top.append(self.bm.verts.new(pt))

        self.bm.verts.ensure_lookup_table()

        for i in range(segs):
            ni = (i + 1) % segs
            self._face([bot[i], bot[ni], top[ni], top[i]], mi)

        if cap:
            if len(bot) >= 3:
                self._face(list(reversed(bot)), mi)
            if len(top) >= 3:
                self._face(top, mi)

    def cone(self, cx, cy, z0, z1, r0, r1,
             segments=16, mi=0, cap=True, transform=None):
        if abs(z1 - z0) < 1e-5 or (r0 < 1e-5 and r1 < 1e-5):
            return

        segs = max(3, segments)
        a_step = 2 * math.pi / segs
        bot, top = [], []

        for i in range(segs):
            a = i * a_step
            xb = cx + r0 * math.cos(a)
            yb = cy + r0 * math.sin(a)
            xt = cx + r1 * math.cos(a)
            yt = cy + r1 * math.sin(a)
            pb = Vector((xb, yb, z0))
            pt = Vector((xt, yt, z1))
            if transform:
                pb = transform @ pb
                pt = transform @ pt
            bot.append(self.bm.verts.new(pb))
            top.append(self.bm.verts.new(pt))

        self.bm.verts.ensure_lookup_table()

        for i in range(segs):
            ni = (i + 1) % segs
            self._face([bot[i], bot[ni], top[ni], top[i]], mi)

        if cap:
            if r0 > 1e-5 and len(bot) >= 3:
                self._face(list(reversed(bot)), mi)
            if r1 > 1e-5 and len(top) >= 3:
                self._face(top, mi)

    def sphere(self, cx, cy, cz, radius,
               segments=16, rings=8, mi=0, transform=None):
        if radius < 1e-5:
            return

        segs   = max(6, segments)
        nrings = max(3, rings)
        a_step = 2 * math.pi / segs
        b_step = math.pi / nrings
        grid   = []

        for ri in range(nrings + 1):
            b = ri * b_step
            row = []
            for si in range(segs):
                a = si * a_step
                x = cx + radius * math.sin(b) * math.cos(a)
                y = cy + radius * math.sin(b) * math.sin(a)
                z = cz + radius * math.cos(b)
                p = Vector((x, y, z))
                if transform:
                    p = transform @ p
                row.append(self.bm.verts.new(p))
            grid.append(row)

        self.bm.verts.ensure_lookup_table()

        for ri in range(nrings):
            for si in range(segs):
                nsi = (si + 1) % segs
                self._face([
                    grid[ri][si], grid[ri][nsi],
                    grid[ri + 1][nsi], grid[ri + 1][si],
                ], mi)

    def torus(self, cx, cy, cz, major_r, minor_r,
              major_segs=16, minor_segs=8, mi=0, transform=None):
        if major_r < 1e-5 or minor_r < 1e-5:
            return

        M = max(6, major_segs)
        m = max(4, minor_segs)
        ma_step = 2 * math.pi / M
        mi_step = 2 * math.pi / m
        grid    = []

        for i in range(M):
            ma = i * ma_step
            row = []
            for j in range(m):
                mb = j * mi_step
                x = cx + (major_r + minor_r * math.cos(mb)) * math.cos(ma)
                y = cy + (major_r + minor_r * math.cos(mb)) * math.sin(ma)
                z = cz + minor_r * math.sin(mb)
                p = Vector((x, y, z))
                if transform:
                    p = transform @ p
                row.append(self.bm.verts.new(p))
            grid.append(row)

        self.bm.verts.ensure_lookup_table()

        for i in range(M):
            ni = (i + 1) % M
            for j in range(m):
                nj = (j + 1) % m
                self._face([
                    grid[i][j], grid[ni][j],
                    grid[ni][nj], grid[i][nj],
                ], mi)

    # ────────────────────────────────────────────────────────
    #  Finalización
    # ────────────────────────────────────────────────────────
    def finalize(self, mesh):
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
        self.bm.to_mesh(mesh)
        self.bm.free()
        self.bm = None
        mesh.update()

    def free(self):
        if self.bm:
            self.bm.free()
            self.bm = None