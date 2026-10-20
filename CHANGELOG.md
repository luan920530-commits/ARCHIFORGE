# Changelog — ArchiForge

Todos los cambios notables del proyecto. Formato basado en
[Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/).

---

## [1.13.0] — 2026-10-20 — Iconografía completa

### Agregado
- **88 iconos PNG nuevos** (112 en total) dibujados con el mismo estilo
  procedural de `icons/generate_icons.py` (azul noche, turquesa, dorado;
  128 × 128 RGBA, sin fuentes ni dependencias en tiempo de ejecución):
  - *Funciones*: `annotation`, `dimension`, `dimension_draw`, `grid_axes`,
    `north_arrow`, `sets`, `set_bathroom`, `set_apartment`, `units`,
    `language`, `procedural`, `preferences`, `material_library`, `scene`,
    `tools`, `quick_edit`, `manipulator`, `reference_point`, `render`,
    `preset`, `room_assets`, `place`, `draw`, `curve`, `ceiling`.
  - *Catálogos* (un icono por `item_type`): baño (10), eléctrico (9),
    muebles (10), cocina (7), decoración (9), puertas y ventanas (6),
    escaleras (`stair_l`, `stair_spiral`, `ramp`), Estructura+ (6) y
    cubiertas (`roof_gable`, `roof_hip`, `roof_shed`).
- **`af_icons.py`**: helper compartido sin `bpy` — `icon_kw(name,
  fallback)`, `icon_id()`, `get_icons()`, `item_icon()` y los mapas
  `ITEM_ICONS` (item_type → icono) y `OBJECT_ICONS` (grupo de propiedades →
  icono). Si falta el PNG, falla la vista previa o el addon corre fuera de
  Blender, devuelve el icono nativo (`{'icon': ...}`), nunca
  `icon_value=0`.
- Pruebas: `tests/test_icon_assets.py` exige que los PNG coincidan
  exactamente con `generate_icons.ICONS`, que todo icono referenciado por
  cualquier módulo exista, que `ITEM_ICONS` cubra todos los `item_type` de
  los ocho catálogos y que `OBJECT_ICONS` apunte a recursos reales;
  `tests/test_icon_helper.py` cubre el helper y el patrón de importación
  con respaldo (144 pruebas).

### Cambiado
- **Panel principal, Shift+A y Control Center**: cada botón de catálogo usa
  el icono de su ítem (inodoro, sofá, nevera, columna, puerta corrediza…) y
  los botones Draw / Place / From Curve / Ceiling / Room Assets, las
  anotaciones y los conjuntos usan los suyos. El submenú Shift+A suma
  *Dimension Selected*, *Grid Axes*, *North Arrow*, *Complete Bathroom (CO)*
  y *Demo Apartment*.
- **Menús `af_menu.py`** (Shift+A, contextual, pie) y **paneles de todos los
  módulos**: cabeceras con el icono del módulo (incluidas las nuevas de
  Techo, Room Assets y Manipuladores), etiqueta *Type* y secciones por tipo
  con el icono del ítem activo, *Boolean*, *Wall Opening*, *Build All*, etc.
  `af_panel.py` muestra el icono propio del tipo AF en Object Info y en los
  listados de escena.
- **Preferencias**: pestañas Interface/Units/Manipulators, idioma, sistema
  de unidades, biblioteca de materiales y tamaños con iconos propios. Las
  casillas booleanas se mantienen sin icono (Blender las convertiría en
  botones de conmutación).
- `icons/generate_icons.py` acepta nombres de iconos como argumentos para
  regenerar solo algunos; los 24 originales se reproducen byte a byte.

### Notas
- Los iconos se verificaron en hojas de contacto renderizadas; la carga en
  Blender usa el mismo `bpy.utils.previews` que la versión anterior.

---

## [1.12.0] — 2026-10-20 — Materiales procedurales, unidades, anotaciones y conjuntos

### Agregado
- **Materiales procedurales** (`af_material_procedural.py` + `af_material.py`):
  los materiales `AF.*` de obra se construyen con árboles de nodos en lugar de
  un color plano —aparejo de ladrillo 24 × 7 cm y de bloque 39 × 19 cm con
  junta rehundida (`ShaderNodeTexBrick` + `Bump`), cerámica, veta de madera,
  concreto, mármol, arcilla de teja, pañete y tela—. Las recetas son datos
  puros validados por `recipe_problems()` y solo usan nodos presentes en
  Blender 3.3 LTS y 4.x. Nuevo material `AF.Wall.Block`. Preferencia
  **Procedural Materials** (activa por defecto) que regenera los materiales
  `AF.*` presentes en el archivo al cambiarla; **Create All AF Materials** y
  **Reset** también usan la receta activa. El nodo `Principled BSDF` conserva
  su nombre para que escaleras, muebles y aberturas sigan ajustándolo.
- **Material según referencia de muro**: al elegir *Brick*, *Concrete*,
  *Structural Block* o *Wood Frame* en un muro (al crear, al dibujar o en el
  panel) el slot de cara recibe `AF.Wall.Brick`, `AF.Wall.Concrete`,
  `AF.Wall.Block` o `AF.Wall.Plaster` (`wall_preset_material()` en
  `af_construction_presets.py`); *Custom* no toca el material. La nota de la
  referencia aclara que el aparejo es textura, no geometría.
- **Sistema de unidades efectivo** (`af_units.py`): la preferencia
  **Unit System** sincroniza `unit_settings` (sistema y unidad de longitud,
  nunca la escala) de todas las escenas al cambiarla y con el botón **Apply
  to Scenes**; `collect_quantities(objects, unit_system)` convierte
  longitudes, áreas y volúmenes a `ft`, `ft2`, `ft3` en el CSV imperial;
  `feet_and_inches()` rotula `10' 6"` en las cotas.
- **Mensajes de estado traducidos**: 170 llamadas `self.report()` en 29
  módulos pasan por `af_i18n.tr_report`, que busca el texto en el diccionario
  del idioma activo del addon; las plantillas `{}` se traducen antes de
  `format()`. `tests/test_i18n.py` exige que todo `self.report()` esté
  envuelto en `_tr()` y que cada módulo con reportes importe el traductor.
- **Anotaciones** (`af_annotation_geometry.py` puro + `af_annotation.py`):
  **Dimension Selected** (ancho y fondo de la huella de cada objeto
  seleccionado), **Draw Dimension** (dos clics en el visor, con previsualización
  y snap de rejilla), **Grid Axes** (ejes numerados en X y con letra en Y,
  burbujas en uno o ambos extremos) y **North Arrow**. Líneas como curvas con
  bisel (renderizables) y textos como objetos de texto, agrupados en la
  colección `AF_Annotations` con la propiedad `af_annotation`; botones de
  mostrar/ocultar; panel propio, sección en el panel principal y entradas en
  el menú Shift+A. Las etiquetas respetan el sistema de unidades.
- **Conjuntos** (`af_sets.py`): **Complete Bathroom (CO)** —1.50 × 2.20 m
  editables: muros, piso 30 × 30, puerta 0.70, ventana alta, lavamanos,
  sanitario, ducha + ducha eléctrica, espejo, toallero, toma GFCI,
  interruptor, luz— y **Demo Apartment** —6 × 7 m: perímetro de bloque,
  divisiones de ladrillo, piso 60 × 60 recortado al baño, baño completo,
  cocina abierta, sala-comedor, dos alcobas, 4 puertas y 5 ventanas con sus
  booleanos sobre el muro correcto, mobiliario, eléctrico, cotas generales y
  norte—. Cada paso está aislado: lo que falle se omite y se informa.
  Nuevos helpers compartidos `af_wall.create_wall_from_points()` y
  `af_floor.create_floor_from_outline()` (los usan también las herramientas
  de dibujo).
- Pruebas nuevas: `test_material_procedural.py`, `test_units.py`,
  `test_annotation_geometry.py`, `test_stair_unification.py`, caso imperial
  en `test_quantities_io.py` y comprobaciones de reportes en `test_i18n.py`
  (135 pruebas). El stub headless expone `bpy.app.handlers`/`timers`.

### Cambiado
- **Escaleras unificadas**: `af_stairs.py` (copia idéntica que registraba
  `archiforge.stairs` y `archiforge_stairs`) desaparece; `af_stair.py` es el
  único módulo, mantiene el alias interno `archiforge.stairs` y migra en
  `load_post` (y al activar el addon) los objetos guardados con el grupo
  antiguo copiando sus propiedades y regenerando la malla.
- `WALL_PRESET_NOTE` y la etiqueta del panel de muro: "sólido único sin capas,
  aparejo como textura".
- README: secciones v1.12, estructura de módulos, roadmap y límites del idioma
  (los nombres generados siguen en inglés; los reportes ya se traducen).

### Notas
- Las texturas usan coordenadas de objeto en metros; en tramos diagonales el
  aparejo se estira hasta un 41 %. Los archivos de versiones anteriores
  conservan materiales planos hasta pulsar **Create All AF Materials**,
  reiniciar el material o alternar la preferencia.
- Las distribuciones de los conjuntos son referencias de partida (orientación
  de aparatos, posiciones y medidas editables), no diseños normativos.
- Fuera del alcance de esta versión (siguiente): módulo hidrosanitario, capas
  de muro/aparejo como geometría, prueba de humo en Blender real dentro de CI
  y `blender_manifest.toml`.

---

## [1.11.0] — 2026-10-20 — Idioma del addon operativo (English / Español)

### Agregado
- El selector **Addon language** de las preferencias ahora traduce de verdad
  la interfaz de ArchiForge sin cambiar el idioma de Blender: paneles, menús,
  operadores, nombres de propiedades, opciones de desplegables y descripciones
  emergentes. `af_i18n.py` construye el diccionario `{(contexto, msgid):
  msgstr}` y lo registra con `bpy.app.translations` bajo el locale activo
  (incluido `en_US`); el cambio es inmediato y se conserva con las
  preferencias.
- `af_i18n_es.py`: unas 1 750 cadenas English → Español, 320 cadenas escritas
  en español (biblioteca por ambientes, algunos presets) con su versión en
  inglés para el modo *English*, y la lista de términos invariantes.
- Las casillas **Translate Interface / Translate Tooltips** de Blender —que
  Blender apaga cuando su idioma es inglés— se activan al aplicar el idioma y
  se restauran al desactivar el addon si fue este quien las encendió. Si
  quedan apagadas, el panel de preferencias lo avisa y las ofrece.
- Pruebas: `tests/ui_strings.py` extrae por AST todas las cadenas de interfaz
  (`text=`, `name=`, `description=`, `bl_label`, items de enum, enums
  dinámicos) y `tests/test_i18n.py` exige que todas estén en el diccionario,
  sin duplicados, entradas vacías ni marcadores `{}`/`%` perdidos, y comprueba
  registro, cambio de idioma, restauración de casillas y resolución de
  locale contra el stub de `bpy.app.translations`.

### Cambiado
- Etiquetas cortas que compartían msgid con significados distintos se
  renombraron en inglés para traducirse sin ambigüedad: el tablero eléctrico
  *Recessed* pasa a **Recessed in Wall**, la forma de tablero de mesa *Top* a
  **Top Shape** y el botón de contraventanas *Open / Close* a **Open Shutters /
  Close Shutters**.

### Limitaciones conocidas
- Si Blender se ejecuta en español, sus propias traducciones de términos
  genéricos prevalecen también con el addon en *English*.
- Los mensajes de `self.report()` y los nombres de objetos/materiales
  generados permanecen en inglés.
- Al cambiar el idioma de Blender, este restablece sus casillas de
  traducción; el addon las vuelve a activar al reiniciar o al elegir de
  nuevo el idioma.

---

## [1.10.0] — 2026-10-20 — Ventanas abatibles, formatos de piso y referencias de muro

### Agregado
- Ventanas **Casement** y **Awning**: propiedades **Hinge Side**
  (izquierda/derecha), **Swing** (hacia fuera/hacia dentro) y **Hinges** con
  radio y longitud. Los pernios se generan centrados sobre el eje de giro de
  cada hoja y no rotan con ella; con varias hojas abatibles las bisagras se
  alternan para que los cantos libres coincidan en el centro.
- Pisos: selector **Tile Format** con los formatos comerciales **30 × 30,
  45 × 45, 60 × 60 y 60 × 120 cm**, disponible en el diálogo de creación y en
  **Floor Properties**. El preset carga las medidas y estas siguen siendo
  editables; cualquier cambio manual devuelve el selector a *Custom*.
- Muros: selector **Construction Reference** con espesores iniciales para
  **entramado de madera (11.5 cm), ladrillo (15 cm), concreto (25 cm) y bloque
  estructural (20 cm)**, disponible al crear, al dibujar con **Draw Wall /
  Room** y en **Wall Properties**. Son referencias editables, no exigencias
  normativas; el panel lo indica y el muro sigue siendo un único sólido sin
  aparejo ni capas. Editar el espesor a mano devuelve la referencia a
  *Custom*.
- Módulos puros `af_window_geometry.py` (cinemática de hojas y bisagras) y
  `af_construction_presets.py` (catálogo de formatos y espesores);
  `grout_joint_thickness` en `af_floor_geometry.py`.
- Pruebas: `tests/test_window_geometry.py`,
  `tests/test_construction_presets.py`, nuevos casos en
  `tests/test_floor_geometry.py` y `tests/blender_stub.py`, un sustituto
  mínimo de `bpy`/`bmesh`/`mathutils` que permite ejecutar los generadores
  reales de ventanas y pisos sin Blender y comprobar sus coordenadas.

### Cambiado
- Los estilos de junta **Flat / Raised / Recessed** generan geometría
  distinta en los patrones **Regular** y **Offset**: la junta queda a ras de
  la baldosa, sobresale o se hunde según **Grout Depth**. Antes los tres
  estilos producían la misma junta rehundida. Los demás patrones siguen sin
  modelar prismas de junta y el panel lo indica.
- La **losa base** del piso ocupa `0..Base Thickness` y las piezas, juntas y
  bordes se apoyan sobre ella; antes compartían la cota de origen y la base se
  superponía a las baldosas. Aplica también a contornos personalizados y a
  **Floor from Curve**.

### Corregido
- **Open Angle** ahora mueve la geometría de las ventanas abatibles y
  proyectantes: la hoja completa —marco de hoja, vidrio y divisiones
  (grille)— gira alrededor de la bisagra. Antes el ángulo y el botón de
  apertura cambiaban la propiedad sin modificar la malla y el vidrio se
  generaba en el centro del marco, fuera del espesor de la hoja. El eje pasa
  por la arista exterior o interior del montante según **Swing**, de modo que
  el montante no atraviesa la jamba al abrir.
- El botón **Toggle Open / Closed** y los controles de apertura solo se
  ofrecen para ventanas abatibles y proyectantes; antes aparecían en todos los
  tipos salvo el fijo. Las fijas, corredizas, de guillotina y de arco ignoran
  **Open Angle** y no generan bisagras.
- La manija de las ventanas abatibles paramétricas (`af_openings.py`) se
  ubica en coordenadas locales de la hoja y acompaña su giro.

---

## [1.9.0] — 2026-10-19 — Idioma del addon y correcciones de puertas

### Agregado
- Selector de idioma English/Español en las preferencias de ArchiForge,
  independiente del idioma configurado en Blender (solo la preferencia; la
  traducción efectiva llega en 1.11.0).

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
