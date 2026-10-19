# Changelog — ArchiForge

Todos los cambios notables del proyecto. Formato basado en
[Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/).

---

## [1.9.0] — 2026-10-19 — Idioma del addon y correcciones de puertas

### Agregado
- Selector de idioma English/Español en las preferencias de ArchiForge,
  independiente del idioma configurado en Blender.

### Corregido
- Posición local de la manija de puertas de una hoja: con bisagra a la derecha
  ahora se calcula desde el canto libre de la hoja y queda vinculada al giro.

---

## [1.8.0] — 2026-10-19 — Biblioteca paramétrica por ambientes

### Agregado
- Catálogo navegable de **100 objetos o sets, 20 para cada ambiente**:
  dormitorio, sala, cocina, baño y solar/jardín. Incluye dimensiones métricas
  sugeridas, calidad de malla, materiales y controles editables.
- Mesas de noche, camas, cabeceros, cómodas, clósets, tocadores; sofás,
  mesas de centro redondas/rectangulares, mesas nido, auxiliares, consolas,
  libreros y repisas de varios formatos.
- Nuevos módulos y sets para cocinas, baños y exteriores, con gabinetes,
  despensas, accesorios, asadores, pérgolas, jardineras, iluminación y
  decoración.
- Acceso desde **Room Asset Library** en el panel ArchiForge, Control Center
  y menú `Shift+A → ArchiForge`.
- Los objetos de la biblioteca se incluyen en las cantidades CSV agrupados por
  ambiente, con sus dimensiones métricas.

---

## [1.7.0] — 2026-10-19 — Contornos de losas/pisos y booleanos paramétricos

### Agregado
- **Draw Slab Outline** y **Draw Floor Outline**: trazos modales cerrados en
  el plano Z del cursor 3D, con snap del addon, vista previa, cierre en el
  primer punto o con `C`/`Enter`, deshacer vértice con `Backspace` y cancelar
  con `Esc`.
- Los pisos guardan su polígono personalizado y recortan tanto la base como
  las baldosas al contorno (incluidos polígonos cóncavos). **Floor from Curve**
  también utiliza el contorno XY, no solo su caja envolvente. Las cantidades
  de pisos dibujados usan el área poligonal, no el rectángulo envolvente.

### Corregido
- Los paramétricos de Doors & Windows (`af_openings.py`) ahora crean o
  actualizan el Boolean al crear/editar la abertura y al cambiar el muro
  objetivo. El cutter se mantiene como hijo oculto, se dimensiona en el espacio
  local de la abertura, y se limpia/reasigna al desactivar o cambiar de muro.
  Crear la abertura con un muro ArchiForge seleccionado lo preselecciona como
  objetivo y activa el corte.

---

## [1.6.0] — 2026-10-18 — Dibujo de muros y recintos

### Agregado
- **Draw Wall / Room**: herramienta modal para trazar muros conectados con
  clics; permite cerrar un recinto haciendo clic en el primer vértice o con
  `C`, terminar un muro abierto con `Enter`, quitar el último vértice con
  `Backspace` y cancelar con `Esc`.
- Cada trazo genera un único objeto paramétrico. Las esquinas se calculan con
  offsets cíclicos; el contorno incluye el tramo de retorno y se rechazan
  polígonos cerrados degenerados o autointersectados.
- Cálculos puros y pruebas de geometría de caminos en `af_wall_path.py`, sin
  depender de Blender.
- Conjunto de 24 iconos PNG originales, incluido el logotipo de ArchiForge y
  pictogramas para los módulos principales.

### Mejorado
- El generador de muros y sus zócalos/cornisas conectan cíclicamente los
  extremos al cerrar un recinto, en vez de dejar tapas o una junta final.
- El exportador de cantidades suma el tramo de retorno implícito de muros
  cerrados para informar el perímetro completo.
- README con instrucciones de trazado, atajos y requisitos del plano de dibujo.

---

## [1.5.2] — 2026-10-18 — Estabilidad, cantidades y calidad

### Corregido
- El hot-reload intenta desregistrar clases, menús y callbacks existentes
  antes de recargar módulos, evitando reemplazar referencias de clases que
  Blender todavía conserva registradas.
- El exportador ya no interpreta cada `PointerProperty` por defecto como un
  objeto ArchiForge. Comprueba el marcador y el nombre persistido del objeto;
  las longitudes de muro se calculan sumando segmentos activos, no usando el
  espesor como largo.
- Losas personalizadas calculan el área con el polígono; se descuentan huecos
  rectangulares y se incluyen las escaleras del módulo nuevo, pisos, vallas,
  techos, cerchas, estructura, puertas y ventanas.
- El exportador trabaja sobre la escena activa, no sobre todos los objetos
  `bpy.data` del archivo.
- CSV con quoting correcto para `;`, comillas y saltos de línea, y neutraliza
  celdas de texto que podrían interpretarse como fórmulas en Excel.
- Eliminada una copia accidental de `af_structure.py` dentro de `icons/`, que
  duplicaba cuatro `bl_idname` de Blender.

### Mejorado
- Separadas las funciones puras de cantidades/CSV para probarlas sin `bpy`;
  se añadieron pruebas de regresión, verificación estática y CI en Python 3.10
  y 3.11.
- La exportación muestra una advertencia explícita de que sus resultados son
  estimaciones paramétricas, no un presupuesto normativo.
- README corregido con pasos de instalación, URL canónica, alcance de
  cantidades y comando de pruebas. El directorio de iconos ahora documenta el
  fallback a iconos nativos de Blender.

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
