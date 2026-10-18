# Changelog — ArchiForge

Todos los cambios notables del proyecto. Formato basado en
[Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/).

---

## [1.5.1] — 2026-10-18 — Hotfix de carga

### Corregido
- `NameError: af_control_center` al re-activar el addon sin cerrar Blender:
  el hot-reload ahora **importa módulos nuevos**, no solo recarga los conocidos.
- `af_control_center` agregado a `_RELOAD_ORDER`.

### Mejorado
- **Imports tolerantes**: si un `af_*.py` falta o tiene un error, se reporta
  en consola y el addon carga con los demás (antes moría todo).
- `_modules` filtra entradas `None` automáticamente.

---

## [1.5.0] — 2026-10-18 — 🎛️ Control Center

### Agregado
- **`af_control_center.py` v1.0**: ventana flotante lanzadora con pestañas
  Structure · Openings · Interior · Electro & Tools.
  - Acceso: panel ArchiForge → Tools, `Shift+A → ArchiForge`
    (primera opción) o `F3 → Control Center`.
  - Cada botón verifica que el operador exista; cada tipo verifica el enum
    real del módulo: el diálogo **nunca se rompe** por un módulo ausente.
  - Reutiliza los íconos custom del addon automáticamente.

---

## [1.4.0] — 2026-10-17 — Estructura, CO, losas y techos

### Agregado
- **`af_structure.py` v1.0**: zapatas, columnas, vigas, losa aligerada,
  rejilla de ejes y niveles con rótulos 3D.
- **Puertas/ventanas con presets Colombia** (`af_door.py` / `af_window.py`
  v1.1, archivos completos): puertas P070–P120, ventanas V100×100–V240×220
  con antepecho; modos Draw y Place.
- **Losas con 4 sistemas constructivos** (`af_slab.py` v1.2): MACIZA,
  ALIGERADA (viguetas + torta), PLACA FÁCIL y STEELDECK (deck metálico +
  malla), con recorte a contorno y huecos.
- **Techos con 9 cubiertas** (`af_roof.py` v1.1): zinc ondulada, eternit,
  termoacústica sándwich, metálica, española (barril), romana, plana y
  tejuela, sobre los 7 tipos de techo.

### Corregido
- Mansard crasheaba (recursión infinita + leak en `_build_mansard`):
  reescrito sin sub-bmesh ni mutación temporal de props.
- Teja ROMANA estaba listada sin geometría: ahora genera tubos romanos.
- Compatibilidad Blender 3.3: `face.material_index` nativo (sin
  `polygon_layers_int`), bmesh posicional, iconos válidos 3.3.

---

## [1.3.0] — 2026-10-1x — Aberturas, escaleras, cantidades

### Agregado
- **`af_openings.py`**: puertas (1H, 2H, corrediza) y ventanas
  (corrediza, batiente, fija) paramétricas.
- **`af_stairs.py`**: escalera recta, en L, caracol y **rampa 8%**
  (ids plurales para no colisionar con la escalera clásica).
- **`af_quantities.py`**: exportación de cantidades a **CSV (Excel)**.

---

## [1.2.0] — 2026-10-1x — Interiores + Pack Colombia 🇨🇴

### Agregado
- **`af_furniture.py` v1.0**: 10 muebles incl. **camas en medidas CO**
  (sencilla → king), nochero, chifonier, biblioteca.
- **`af_kitchen.py` v1.0**: nevera, estufa, campana, lavaplatos,
  lavavajillas, microondas, utensilios.
- **`af_decor.py` v1.0**: materas, lámparas, floreros, cuadros, reloj,
  libros, TV, tapete.
- **Pack Colombia**: tomas CO + GFCI, ducha eléctrica tipo Lorenzetti,
  camas colombianas.

---

## [1.1.0] — 2026-10-17 — Baño v2, eléctrico v2.x, fixes 3.3

### Agregado
- **`af_bathroom.py` v2.0**: 9 tipos (sanitario, bidé, lavamanos, vanitorio,
  ducha, tina, espejo, toallero + ducha eléctrica), calidad LOW/MED/HIGH,
  auto-smooth 35°, 6 materiales, creación en cursor 3D.
- **`af_electrical.py` v2.0 → v2.1**: 9 tipos (tomas EU/US/UK, switch, datos
  RJ45, bombillo, colgante, techo, downlight, aplique, tablero), redondez
  real con matrices 4×4, **luz real de Blender** opcional.

### Corregido
- Bathroom/Electrical se registraban pero **no aparecían** en panel ni
  Shift+A → secciones agregadas.
- Iconos 4.x (`DRAG_HANDLE`, `LIGHT_HEM`, `TOGGLE`) → equivalentes 3.3.
- `icon_value=0` inválido → helper `_icon_kw()`.
- Hot-reload blindado por módulo; `af_objects_base` incluido en registro.

---

## [1.0.0] — Versión original

- Addon original: muros, puertas, ventanas, escalera, losa, techo,
  cerca, pisos, cercha, materiales, snap, presets, booleanas, UI base.
