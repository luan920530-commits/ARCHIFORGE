# -*- coding: utf-8 -*-
# ArchiForge — presets CO para af_door.py (medidas comerciales Colombia)
# USO: Text Editor > Open > este archivo > Run Script > reiniciar (F8).
# Agrega propiedad "CO Preset": 0.70/0.75/0.80/0.90/1.00/1.20 m.
import bpy
import io
import os
import py_compile

TARGET = os.path.join(bpy.utils.script_path_user(), "addons",
                      "ArchiForge", "af_door.py")


def main():
    print("target:", TARGET)
    with io.open(TARGET, encoding="utf-8") as fh:
        src = fh.read()
    with io.open(TARGET + ".bak", "w", encoding="utf-8") as fh:
        fh.write(src)
    print("backup: af_door.py.bak")

    a1 = """AF_HINGE_SIDES = [
    ('LEFT',  "Left",  "Hinge on left side"),
    ('RIGHT', "Right", "Hinge on right side"),
]
"""
    b1 = a1 + """
AF_DOOR_CO_PRESETS = [
    ('CUSTOM',   "Custom",   "Medidas manuales"),
    ('P070x200', "0.70x2.00 Baño",    "Puerta baño"),
    ('P075x200', "0.75x2.00",         "Puerta servicio"),
    ('P080x210', "0.80x2.10 Alcoba",  "Puerta alcoba"),
    ('P090x210', "0.90x2.10 Acceso",  "Puerta principal"),
    ('P100x220', "1.00x2.20",         "Puerta amplia"),
    ('P120x220', "1.20x2.20 Doble",   "Referencia doble"),
]

AF_DOOR_CO_DIMS = {
    'P070x200': (0.70, 2.00),
    'P075x200': (0.75, 2.00),
    'P080x210': (0.80, 2.10),
    'P090x210': (0.90, 2.10),
    'P100x220': (1.00, 2.20),
    'P120x220': (1.20, 2.20),
}
"""
    assert src.count(a1) == 1, "fix1: ancla HINGE"
    src = src.replace(a1, b1)
    print("fix1 OK: constantes preset")

    a2 = """    door_type : EnumProperty(
        name    = "Door Type",
        items   = AF_DOOR_TYPES,
        default = 'SINGLE',
        update  = lambda s, c: af_door_update(s, c),
    )
"""
    b2 = a2 + """
    co_preset : EnumProperty(
        name    = "CO Preset",
        items   = AF_DOOR_CO_PRESETS,
        default = 'CUSTOM',
        update  = lambda s, c: af_door_co_preset_update(s, c),
    )
"""
    assert src.count(a2) == 1, "fix2: ancla door_type"
    src = src.replace(a2, b2)
    print("fix2 OK: propiedad co_preset")

    a3 = "def af_door_update(self, context):"
    b3 = '''def af_door_co_preset_update(self, context):
    dims = AF_DOOR_CO_DIMS.get(self.co_preset)
    if dims is None:
        return
    self.width, self.height = dims


def af_door_update(self, context):'''
    assert src.count(a3) == 1, "fix3: ancla update"
    src = src.replace(a3, b3)
    print("fix3 OK: funcion preset")

    a4 = '''        col.prop(props, "door_type", text="")'''
    b4 = a4 + '''
        col.prop(props, "co_preset", text="CO")'''
    assert src.count(a4) == 1, "fix4: ancla panel"
    src = src.replace(a4, b4)
    print("fix4 OK: fila panel")

    with io.open(TARGET, "w", encoding="utf-8") as fh:
        fh.write(src)
    py_compile.compile(TARGET, doraise=True)
    print("VERIFY OK: af_door.py compila. Reinicie Blender.")


main()
