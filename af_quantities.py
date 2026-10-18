# -*- coding: utf-8 -*-
"""ArchiForge — cantidades paramétricas de obra a CSV/Excel.

Las métricas se estiman desde los parámetros de los objetos ArchiForge; no
sustituyen una medición BIM ni un presupuesto validado por un profesional.
"""

import bpy

from bpy.types import Operator, Panel
from bpy_extras.io_utils import ExportHelper

from .af_quantities_io import (
    collect_quantities as _collect_quantities,
    format_number as _num,
    summarize,
    write_csv,
)


def collect_quantities(objects=None):
    """Return quantity rows for the requested scene objects.

    ``objects`` defaults to the active scene, not ``bpy.data.objects``; this
    avoids mixing objects from other scenes in the file.
    """
    if objects is None:
        scene = getattr(bpy.context, "scene", None)
        objects = scene.objects if scene is not None else bpy.data.objects
    return _collect_quantities(objects)


class ARCHIFORGE_OT_quantities_export(Operator, ExportHelper):
    bl_idname = "archiforge.quantities_export"
    bl_label = "Export Quantities CSV"
    bl_description = "Export ArchiForge quantity estimates to an Excel-friendly CSV"
    bl_options = {'REGISTER'}

    filename_ext = ".csv"
    filter_glob: bpy.props.StringProperty(default="*.csv", options={'HIDDEN'})

    def execute(self, context):
        try:
            rows = collect_quantities(context.scene.objects)
            count = write_csv(self.filepath, rows)
        except (OSError, TypeError, ValueError, ReferenceError) as exc:
            self.report({'ERROR'}, f"No se pudo exportar el CSV: {exc}")
            return {'CANCELLED'}
        self.report({'INFO'}, f"Se exportaron {count} filas a CSV")
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
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Bill of Quantities", icon='SPREADSHEET')
        try:
            rows = collect_quantities(context.scene.objects)
        except (TypeError, ValueError, ReferenceError) as exc:
            col.label(text=f"No se pudieron leer cantidades: {exc}",
                      icon='ERROR')
            rows = []

        if not rows:
            col.label(text="No hay objetos ArchiForge cuantificables",
                      icon='INFO')
        else:
            totals = {}
            for category, _item_type, _name, quantity, unit, _dimensions in rows:
                key = (category, unit)
                totals[key] = totals.get(key, 0.0) + quantity
            for (category, unit), quantity in sorted(totals.items()):
                formatted = (
                    str(int(round(quantity))) if unit == "und"
                    else _num(quantity)
                )
                col.label(text=f"{category}: {formatted} {unit}")

        layout.separator()
        layout.label(text="Estimaciones paramétricas; verifique antes de presupuestar.",
                     icon='INFO')
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
