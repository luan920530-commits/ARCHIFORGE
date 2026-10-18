# -*- coding: utf-8 -*-
"""ArchiForge — Cantidades de obra a CSV/Excel.

v1.0 — Blender 3.3 LTS.
Escanea objetos AF de la escena y exporta tabla de cantidades
(muros m2/m3, losas m2/m3, aparatos/piezas und) compatible Excel ES-CO.
"""

import bpy

from bpy.types import Operator, Panel
from bpy_extras.io_utils import ExportHelper


def _f(props, default=0.0, *names):
    for nm in names:
        try:
            v = getattr(props, nm, None)
            if isinstance(v, (int, float)):
                return float(v)
        except Exception:
            pass
    return float(default)


def _t(props, *names):
    for nm in names:
        try:
            v = getattr(props, nm, None)
            if isinstance(v, str) and v:
                return v
        except Exception:
            pass
    return "—"


def _num(x):
    return f"{x:.2f}".replace(".", ",")


def collect_quantities():
    """[(categoria, tipo, objeto, cantidad, unidad, medidas)]."""
    rows = []
    fams = [
        ("archiforge_wall", "Muros"),
        ("archiforge_slab", "Losas"),
        ("archiforge_bathroom", "Baño"),
        ("archiforge_electrical", "Eléctrico"),
        ("archiforge_furniture", "Muebles"),
        ("archiforge_kitchen", "Cocina"),
        ("archiforge_decor", "Decoración"),
        ("archiforge_opening", "Aberturas"),
        ("archiforge_stair", "Escaleras"),
    ]
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        for attr, cat in fams:
            try:
                props = getattr(obj, attr, None)
            except Exception:
                props = None
            if props is None:
                continue
            try:
                if attr == "archiforge_wall":
                    L = _f(props, 0, "length", "width")
                    H = _f(props, 0, "height")
                    e = _f(props, 0, "thickness", "width",
                           "depth")
                    tp = _t(props, "wall_type", "item_type")
                    dim = (f"L={_num(L)} H={_num(H)} "
                           f"e={_num(e)} m")
                    if L > 0 and H > 0:
                        rows.append((cat, tp, obj.name, L * H,
                                     "m2", dim))
                    if L > 0 and H > 0 and e > 0:
                        rows.append((cat, tp, obj.name,
                                     L * H * e, "m3", dim))
                elif attr == "archiforge_slab":
                    w = _f(props, 0, "width")
                    d = _f(props, 0, "depth")
                    t = _f(props, 0, "thickness")
                    tp = _t(props, "slab_type")
                    dim = (f"{_num(w)}x{_num(d)} e={_num(t)} m")
                    if w > 0 and d > 0:
                        rows.append((cat, tp, obj.name, w * d,
                                     "m2", dim))
                    if w > 0 and d > 0 and t > 0:
                        rows.append((cat, tp, obj.name,
                                     w * d * t, "m3", dim))
                elif attr == "archiforge_stair":
                    tp = _t(props, "item_type")
                    h = _f(props, 0, "total_rise")
                    w = _f(props, 0, "width")
                    rows.append((cat, tp, obj.name, 1, "und",
                                 f"H={_num(h)} A={_num(w)} m"))
                else:
                    tp = _t(props, "item_type")
                    w = _f(props, 0, "width")
                    d = _f(props, 0, "depth")
                    h = _f(props, 0, "height")
                    dim = f"{_num(w)}x{_num(d)}x{_num(h)} m"
                    rows.append((cat, tp, obj.name, 1, "und",
                                 dim))
            except Exception:
                pass
            break
    return rows


def summarize(rows):
    """Totales por (categoria, tipo, unidad)."""
    tot = {}
    for cat, tp, _nm, q, u, _dm in rows:
        k = (cat, tp, u)
        tot[k] = tot.get(k, 0.0) + q
    return sorted(tot.items())


def write_csv(path, rows):
    import io as _io
    lines = ["Categoría;Tipo;Objeto;Cantidad;Unidad;Medidas"]
    for cat, tp, nm, q, u, dm in rows:
        qn = _num(q) if u != "und" else str(int(round(q)))
        lines.append(f"{cat};{tp};{nm};{qn};{u};{dm}")
    lines.append("")
    lines.append("RESUMEN")
    lines.append("Categoría;Tipo;Unidad;Total")
    for (cat, tp, u), q in summarize(rows):
        qn = _num(q) if u != "und" else str(int(round(q)))
        lines.append(f"{cat};{tp};{u};{qn}")
    with _io.open(path, "w", encoding="utf-8-sig",
                  newline="") as fh:
        fh.write("\n".join(lines))
    return len(rows)


class ARCHIFORGE_OT_quantities_export(Operator, ExportHelper):
    bl_idname = "archiforge.quantities_export"
    bl_label = "Export Quantities CSV"
    bl_description = "Export ArchiForge quantities to CSV (Excel)"
    bl_options = {'REGISTER'}

    filename_ext = ".csv"
    filter_glob : bpy.props.StringProperty(default="*.csv",
                                           options={'HIDDEN'})

    def execute(self, context):
        try:
            rows = collect_quantities()
            n = write_csv(self.filepath, rows)
        except Exception as e:
            self.report({'ERROR'}, f"Export failed: {e}")
            return {'CANCELLED'}
        self.report({'INFO'}, f"Exported {n} rows to CSV")
        return {'FINISHED'}


class ARCHIFORGE_PT_quantities(Panel):
    bl_label = "Quantities"
    bl_idname = "ARCHIFORGE_PT_quantities"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "ArchiForge"
    bl_context = "objectmode"
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        self.layout.label(text="", icon='SPREADSHEET')

    def draw(self, context):
        layout = self.layout
        try:
            rows = collect_quantities()
        except Exception:
            rows = []
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Bill of Quantities", icon='SPREADSHEET')
        if not rows:
            col.label(text="No AF objects in scene", icon='INFO')
        else:
            cats = {}
            for cat, _tp, _nm, q, u, _dm in rows:
                k = (cat, u)
                cats[k] = cats.get(k, 0.0) + q
            for (cat, u), q in sorted(cats.items()):
                qn = _num(q) if u != "und" else str(int(round(q)))
                col.label(text=f"{cat}: {qn} {u}")
        layout.separator()
        layout.operator("archiforge.quantities_export",
                        text="Export CSV (Excel)", icon='EXPORT')


classes = [
    ARCHIFORGE_OT_quantities_export,
    ARCHIFORGE_PT_quantities,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    print("[ArchiForge] af_quantities v1 - registered")


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    print("[ArchiForge] af_quantities - unregistered")
