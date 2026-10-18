# -*- coding: utf-8 -*-
# ArchiForge — presets CO para af_window.py (ventanería aluminio CO)
# USO: Text Editor > Open > este archivo > Run Script > reiniciar (F8).
import bpy
import io
import os
import py_compile

TARGET = os.path.join(bpy.utils.script_path_user(), "addons",
                      "ArchiForge", "af_window.py")


def main():
    print("target:", TARGET)
    with io.open(TARGET, encoding="utf-8") as fh:
        src = fh.read()
    with io.open(TARGET + ".bak", "w", encoding="utf-8") as fh:
        fh.write(src)
    print("backup: af_window.py.bak")

    a1 = """AF_SILL_TYPES = [
    ('FLAT',   "Flat",   "Simple flat sill"),
    ('SLOPED', "Sloped", "Sloped drip sill"),
    ('MOLDED', "Molded", "Molded decorative sill"),
]
"""
    b1 = a1 + """
AF_WIN_CO_PRESETS = [
    ('CUSTOM',   "Custom",   "Medidas manuales"),
    ('V100x100', "1.00x1.00 Baño",   "Ventanilla baño"),
    ('V120x120', "1.20x1.20",        "Ventana típica CO"),
    ('V150x120', "1.50x1.20",        "Ventana alcoba"),
    ('V200x140', "2.00x1.40 Sala",   "Ventana sala"),
    ('V240x220', "2.40x2.20 Balcón", "Puerta-ventana"),
]

AF_WIN_CO_DIMS = {
    'V100x100': (1.00, 1.00, 1.20),
    'V120x120': (1.20, 1.20, 0.90),
    'V150x120': (1.50, 1.20, 0.90),
    'V200x140': (2.00, 1.40, 0.60),
    'V240x220': (2.40, 2.20, 0.10),
}
"""
    assert src.count(a1) == 1, "fix1: ancla SILL"
    src = src.replace(a1, b1)
    print("fix1 OK: constantes preset")

    a2 = """    window_type : EnumProperty(
        name="Window Type", items=AF_WIN_TYPES, default='CASEMENT',
        update=lambda s, c: af_window_update(s, c),
    )
"""
    b2 = a2 + """
    co_preset : EnumProperty(
        name="CO Preset", items=AF_WIN_CO_PRESETS, default='CUSTOM',
        update=lambda s, c: af_win_co_preset_update(s, c),
    )
"""
    assert src.count(a2) == 1, "fix2: ancla window_type"
    src = src.replace(a2, b2)
    print("fix2 OK: propiedad co_preset")

    a3 = "def af_window_update(self, context):"
    b3 = '''def af_win_co_preset_update(self, context):
    dims = AF_WIN_CO_DIMS.get(self.co_preset)
    if dims is None:
        return
    self.width, self.height, self.sill_height = dims


def af_window_update(self, context):'''
    assert src.count(a3) == 1, "fix3: ancla update"
    src = src.replace(a3, b3)
    print("fix3 OK: funcion preset")

    a4 = '''        col.prop(props, "window_type", text="")'''
    b4 = a4 + '''
        col.prop(props, "co_preset", text="CO")'''
    assert src.count(a4) == 1, "fix4: ancla panel"
    src = src.replace(a4, b4)
    print("fix4 OK: fila panel")

    with io.open(TARGET, "w", encoding="utf-8") as fh:
        fh.write(src)
    py_compile.compile(TARGET, doraise=True)
    print("VERIFY OK: af_window.py compila. Reinicie Blender.")


main()
