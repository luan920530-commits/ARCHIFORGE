# ArchiForge 🏗️

**Modelado arquitectónico paramétrico para Blender 3.3 LTS y posteriores**

[![Blender](https://img.shields.io/badge/Blender-3.3_LTS_%E2%80%93_4.2%2B_extension-orange)](https://www.blender.org)
[![Version](https://img.shields.io/badge/version-1.14.1-blue)](CHANGELOG.md)
[![License](https://img.shields.io/badge/license-GPLv3-green)](LICENSE)

ArchiForge genera muros, losas, techos, puertas, ventanas, escaleras, baños,
instalaciones eléctricas, muebles, cocinas y más como objetos **paramétricos
y editables**: cambie una medida en el panel y la geometría se regenera al
instante. Incluye **Control Center** (ventana flotante lanzadora) y el
**Pack Colombia 🇨🇴** (tomas GFCI, ducha eléctrica, camas en medidas CO,
puertas y ventanas en anchos comerciales).

---

## 🎛️ Control Center (nuevo en v1.5)

Ventana flotante que lanza **todos los módulos** desde un solo lugar,
organizada en 4 pestañas: Structure · Openings · Interior · Electro & Tools.

Ábrala desde el panel ArchiForge → **Tools → Control Center**,
con `Shift+A → ArchiForge → Control Center`, o con `F3 → Control Center`.

---

## 🧱 Dibujo de muros y recintos (nuevo en v1.6)

Inicie **Draw Wall / Room** desde `Shift+A → ArchiForge` o busque la
herramienta con `F3`. Haga clic para marcar cada vértice; para crear un
recinto, haga clic cerca del primer punto o pulse `C`. Pulse `Enter` para
terminar una polilínea abierta, `Backspace` para quitar el último vértice y
`Esc` para cancelar. El dibujo ocurre en el plano horizontal a la altura Z
del cursor 3D y respeta el snap del addon si está activado.

Cada trazo crea un solo muro paramétrico con tramos conectados y esquinas
calculadas en conjunto. Los recintos cerrados incluyen el tramo de retorno y
se editan desde **Wall Properties** (por ejemplo, altura y espesor). Para
conectar esquinas, trace el recinto como una sola ruta; los muros creados por
separado todavía pueden requerir alineación manual.

## 📐 Dibujo de losas y pisos (nuevo en v1.7)

Inicie **Draw Slab** o **Draw Floor** desde `Shift+A → ArchiForge` o el
**Control Center**. Marque los vértices del perímetro con clics y cierre
haciendo clic cerca del primer punto o pulsando `C`/`Enter`; `Backspace` quita
el último punto y `Esc` cancela. El plano y el snap son los mismos que en
**Draw Wall / Room**. Los contornos cruzados, degenerados o demasiado pequeños
se rechazan antes de crear el objeto. El piso se genera como polígono real y
recorta la base y las piezas al borde; **Floor from Curve** conserva también
el contorno XY de la curva.

Para un corte booleano de puerta/ventana paramétrica, active **Cut in Wall**
y seleccione el muro objetivo. Si inicia la creación con un muro ArchiForge
seleccionado, queda preseleccionado; el cutter se actualiza al cambiar las
medidas o el muro objetivo.

## 🛋️ Biblioteca de objetos por ambiente (nuevo en v1.8)

Abra **Room Asset Library** desde el **Control Center**, el panel ArchiForge
o `Shift+A → ArchiForge`. Incluye **20 objetos o sets por ambiente (100 en
total)**:

- **Dormitorio:** mesas de noche de cajones, nicho, flotantes y redondas;
camas sencilla/queen/king con sets de tendido; cabeceros, cómodas, chifonier,
armarios abatibles/corredizos/abiertos, tocador, banca, espejo, canasto y par
de lámparas.
- **Sala:** sofás de 2–4 puestos y seccional, poltronas, butacas, ottoman,
puf, mesas de centro redonda/rectangular, mesas nido, auxiliares y consolas;
mueble de TV, vitrina, librero, escalera, cubos, repisas y set decorativo.
- **Cocina:** módulos bajos, cajoneras, gabinetes superiores, alacena,
esquinero, isla, barra, carrito, butaco, mesa de desayuno, banca, riel de
ollas, especiero, plato-rack, botellero, despensa y sets de reciclaje/café/
preparación.
- **Baño:** vanities sencillo/doble, torre de linos, gabinete espejo,
repisas, escalera y barras toalleras, ganchos, portarrollo, nicho/caddy,
bancas, canasto, tapetes, set spa, organizador, bandeja, escobillero y barras
de apoyo.
- **Solar/jardín:** mesa, silla, banca, asoleadora, sofá exterior, set bistró,
mesa picnic, pérgola, baúl, jardineras, huerta elevada, enrejado, arco,
sombrilla, parrilla, fogón, fuente, bebedero y sets de balizas/faroles.

Cada selección crea una malla editable con dimensiones sugeridas en metros;
puede ajustar ancho, fondo, altura, calidad y materiales. Los sets se generan
como un solo objeto paramétrico para mover y dimensionar en conjunto. Las
medidas son presets de referencia, no fichas de fabricante ni garantía de
cumplimiento normativo.

## 🪟 Ventanas abatibles, formatos de piso y referencias de muro (nuevo en v1.10)

Las ventanas **Casement** (abatibles) y **Awning** (proyectantes) abren de
verdad: **Open Angle** gira cada hoja completa —marco de hoja, vidrio y
divisiones— alrededor de su eje de bisagra. En las abatibles se elige **Hinge**
(izquierda/derecha; con varias hojas se alternan para que los cantos libres se
encuentren) y **Swing** (hacia fuera o hacia dentro); las proyectantes giran
desde el cabezal y se proyectan hacia el exterior. El botón **Toggle
Open / Closed** solo aparece para estos dos tipos; las ventanas fijas,
corredizas, de guillotina y de arco ignoran el ángulo. Si **Hinges** está
activo, los pernios se generan centrados sobre el mismo eje de giro.

En **Floor Properties**, **Tile Format** ofrece los formatos comerciales
**30 × 30, 45 × 45, 60 × 60 y 60 × 120 cm**; al elegir uno se cargan las
medidas y siguen siendo editables (cualquier cambio manual vuelve a *Custom*).
Los estilos de junta **Flat / Raised / Recessed** generan geometría distinta en
los patrones **Regular** y **Offset**: la junta queda a ras, sobresale o se
hunde la profundidad indicada en **Grout Depth**; los demás patrones no
modelan prismas de junta. La **losa base** se construye debajo de las piezas,
no superpuesta a ellas.

En **Wall Properties**, **Construction Reference** fija el espesor inicial para
**entramado de madera (11.5 cm), ladrillo (15 cm), concreto (25 cm) y bloque
estructural (20 cm)**, también disponible al crear o dibujar muros. Son valores
de referencia editables, no exigencias normativas: el muro sigue siendo un solo
sólido sin capas (desde v1.12 el aparejo de ladrillo o bloque se ve como
textura procedural, no como geometría), y al modificar el espesor a mano la
referencia pasa a *Custom*.

## 🌐 Idioma del addon: English / Español (nuevo en v1.11)

En **Edit ▸ Preferences ▸ Add-ons ▸ ArchiForge ▸ General ▸ Addon language**
se elige el idioma de ArchiForge sin tocar el idioma de Blender. En
**Español** se traducen paneles, menús, operadores, nombres de propiedades,
opciones de los desplegables y descripciones emergentes (unas 1 750 cadenas
cubiertas por `af_i18n_es.py`). En **English** las fichas de la biblioteca
por ambientes y algunos presets escritos originalmente en español se muestran
en inglés. El cambio es inmediato y queda guardado con las preferencias.

Cómo funciona y qué límites tiene:

- ArchiForge registra su diccionario mediante `bpy.app.translations` bajo el
  locale activo de Blender, de modo que la traducción aplica aunque Blender
  esté en inglés. Blender desactiva las casillas **Translate Interface** y
  **Translate Tooltips** cuando su idioma es inglés; el addon las activa al
  aplicar el idioma y las restaura al desactivarse. Si se apagan a mano (o al
  cambiar el idioma de Blender), el panel de preferencias lo avisa y permite
  volver a encenderlas.
- Si Blender ya se ejecuta en español, los términos genéricos que Blender
  traduce por su cuenta (p. ej. *Width*) conservan la traducción de Blender,
  también con el addon en *English*.
- Desde v1.12 también se traducen los mensajes de la barra de estado
  (`self.report`); los nombres de objetos/materiales generados (`AF_Wall`,
  `AF.Wall.Brick`…) siguen en inglés.

---

## 🧱 Materiales procedurales, unidades, anotaciones y conjuntos (nuevo en v1.12)

**Materiales procedurales.** Los materiales `AF.*` de muros, pisos, techos,
losas, puertas, escaleras, cercas y cerchas se construyen con nodos en lugar de
un color plano: aparejo de ladrillo (24 × 7 cm, junta 1.2 cm) y de bloque
(39 × 19 cm) con junta rehundida, cerámica con brillo, veta de madera,
concreto, mármol, arcilla de teja, pañete y tela. Se ven en los modos
**Material Preview** y **Rendered**; en *Solid* se mantiene el color base. La
preferencia **Procedural Materials** (activada por defecto) permite volver a
los materiales planos; al cambiarla se regeneran los materiales `AF.*` ya
presentes en el archivo. Los archivos guardados con versiones anteriores
conservan sus materiales planos hasta pulsar **Create All AF Materials**,
reiniciar el material o alternar la preferencia. Al elegir una
**Construction Reference** en un muro se asigna el material correspondiente
(`AF.Wall.Brick`, `AF.Wall.Block`, `AF.Wall.Concrete`, `AF.Wall.Plaster`);
*Custom* no toca el material. Las texturas usan coordenadas de objeto en
metros: las hiladas siguen la dirección del muro en tramos ortogonales y se
estiran hasta un 41 % en tramos diagonales. El nodo **Principled BSDF**
conserva su nombre, de modo que seguir editando el material `AF.*` en el
editor de shaders aplica a todos los objetos que lo usan.

**Sistema de unidades.** **Unit System** (Metric / Imperial) en las
preferencias sincroniza `Scene ▸ Units` de todas las escenas abiertas
(sistema y unidad de longitud; la escala no se modifica, así que los objetos
no cambian de tamaño) y el botón **Apply to Scenes** lo repite cuando haga
falta. Con *Imperial*, todas las propiedades de longitud se muestran y editan
en pies/pulgadas, las cotas se rotulan como `10' 6"` y la **exportación CSV**
convierte longitudes, áreas y volúmenes a `ft`, `ft2` y `ft3`. Internamente el
modelo sigue en metros.

**Anotaciones (panel Annotations).** **Dimension Selected** acota el ancho y
el fondo de la huella en planta de cada objeto seleccionado; **Draw
Dimension** acota entre dos clics en el visor; **Grid Axes** genera ejes
estructurales numerados en X y con letra en Y, con burbujas; **North Arrow**
coloca el símbolo de norte en el cursor. Las líneas son curvas con un bisel
pequeño (se renderizan) y los textos objetos de texto; todo queda en la
colección `AF_Annotations` con la propiedad `af_annotation`, se puede mostrar
u ocultar en bloque y nunca entra en las cantidades.

**Conjuntos (panel Sets).** **Complete Bathroom (CO)** construye en el cursor
un baño de 1.50 × 2.20 m (medidas editables): muros con referencia de
ladrillo, piso cerámico 30 × 30, puerta de 0.70, ventana alta, lavamanos,
sanitario, ducha con ducha eléctrica, espejo, toallero, toma GFCI,
interruptor y luz. **Demo Apartment** levanta un apartamento de 6 × 7 m con
muros perimetrales de bloque, divisiones de ladrillo, piso 60 × 60, el baño
anterior, cocina abierta, sala-comedor, dos alcobas, puertas y ventanas con
sus booleanos, mobiliario, eléctrico, cotas generales y norte. Cada pieza es
un objeto paramétrico normal (editable y contado en el CSV); si falta un
módulo o una pieza falla, el resto se construye y el mensaje indica qué se
omitió. Son distribuciones de referencia para empezar, no diseños normativos.

---

## 🎨 Iconos propios

El addon incluye **112 iconos PNG originales** con un estilo arquitectónico
consistente: la marca, cada módulo, cada función (dibujar, colocar, desde
curva, cotas, ejes, norte, conjuntos, unidades, idioma, presets, render…) y
**un icono por cada ítem de los catálogos** —inodoro, lavamanos, ducha,
tomacorriente, interruptor, lámparas, sillas, sofá, camas, nevera, estufa,
materas, cuadros, puertas y ventanas por tipo, escaleras L / caracol, rampa,
zapata, columna, viga, cubiertas a dos aguas / cuatro aguas / un agua, etc.—.
Se cargan como vistas previas de Blender a través del helper `af_icons.py`
(panel principal, Shift+A, Control Center, menús contextual y pie, cabeceras
y secciones de todos los paneles, preferencias) y conservan un icono nativo
de respaldo si falta algún recurso. No se descargan archivos ni se instalan
dependencias al usar el addon; las instrucciones para editar o regenerar los
iconos están en [`icons/README.md`](icons/README.md).

---

## ✨ Módulos

| Módulo | Contenido |
|---|---|
| 🧱 Muros / Losas | Muros paramétricos + **Draw Wall / Room** con **referencias de espesor** (madera, ladrillo, concreto, bloque); **Draw Slab / Draw Floor** para contornos cerrados; losas: **MACIZA · ALIGERADA · PLACA FÁCIL · STEELDECK**, pisos recortados al polígono, desde curva y huecos |
| 🏠 Techos (v1.1) | Gable, Shed, Hip, Saltbox, Butterfly, Mansard, Bóveda + **9 cubiertas**: zinc, eternit, termoacústica, metálica, española, romana, plana, tejuela |
| 🚪 Puertas / Ventanas (v1.1) | Presets CO: puertas 0.70–1.20 m, ventanas 1.00×1.00 → 2.40×2.20 + antepecho; modos Draw y Place; **abatibles y proyectantes con hoja, vidrio y divisiones que giran sobre la bisagra** (v1.10) |
| 🪜 Escaleras | Un solo módulo (`af_stair.py`): recta, en L, caracol y **rampa 8%**; los archivos con la copia duplicada de 1.x se migran solos |
| 🏗️ Estructura+ | Zapatas, columnas, vigas, losa aligerada, ejes/rejilla y niveles con rótulos |
| 🛁 Baño (v2) | Sanitarios y aparatos; vanities, torre de linos, espejo-gabinete y sets de toalleros, nichos, organizadores, tapetes y seguridad |
| 🔌 Eléctrico (v2.1) | Tomas EU/US/UK/**CO+GFCI 🇨🇴**, interruptores, datos RJ45, bombillos, colgantes, downlights, apliques, tablero + **luz real de Blender** |
| 🛋️ Muebles | Sillas, poltrona, sofás, camas CO 🇨🇴, mesas de noche, comedor/centro/laterales/nido/consola, libreros, repisas, clósets y tocadores |
| 🍳 Cocina | Nevera, estufa, campana, lavaplatos, lavavajillas, microondas, islas, módulos, despensas, butacos, racks y sets |
| 🌿 Exterior | Patio, bistró, picnic, pérgolas, baúles, jardineras, huerta, enrejados, parrilla, fogón, fuente e iluminación |
| 🪴 Decoración | Materas con plantas, lámparas, floreros, cuadros, reloj, libros, TV, tapete y sets decorativos por ambiente |
| 🗂️ Room Asset Library (v1.8) | **100 objetos o sets**: 20 opciones paramétricas para dormitorio, sala, cocina, baño y solar/jardín |
| 🚧 Extras | Cerchas (truss), cercas, pisos/patterns con **formatos 30×30 · 45×45 · 60×60 · 60×120 cm** y juntas a ras / resaltadas / rehundidas, booleanas automáticas |
| 📊 Cantidades | **Exportación CSV (Excel)** de cantidades del proyecto, en métrico o imperial según la preferencia |
| 📐 Anotaciones (v1.12) | Cotas de selección o entre dos clics, ejes estructurales con burbuja y símbolo de norte |
| 🏠 Conjuntos (v1.12) | **Baño completo (CO)** y **apartamento demo 6 × 7 m** compuestos con los módulos anteriores |

**Pack Colombia 🇨🇴**: tomas con GFCI, ducha eléctrica tipo Lorenzetti,
camas sencilla / semidoble / doble / queen / king, puertas y ventanas
en medidas comerciales colombianas.

## 📋 Requisitos

- **Blender 3.3 LTS o posterior** (3.3 es la versión mínima declarada en
  `bl_info`). Como **extensión** (`blender_manifest.toml`) el mínimo es
  **Blender 4.2 LTS**, que es cuando aparece el sistema de extensiones.
- **Verificado en Blender 4.2.23 LTS** (modo *background*): la CI instala el
  ZIP como extensión en un Blender 4.2 real y ejecuta los 125 operadores
  (`tests/blender_smoke_42.py`). La interacción con ratón/vista 3D sigue
  requiriendo prueba manual.
- **macOS**: según el código de compilación de Blender, 3.3 LTS requiere
  macOS 10.13 (Intel) / 11.0 (Apple Silicon), 3.6 requiere 10.15 y
  **4.1–4.2+ requieren macOS 11.2 (Big Sur)**. Si su Mac está en Catalina o
  anterior no podrá instalar 4.2 ni usar extensiones: use el ZIP clásico en
  3.3 LTS (opciones A–C más abajo).
- Sin dependencias externas: solo Blender + Python estándar
- macOS / Windows / Linux

## 🚀 Instalación

**Opción A — Release ZIP (recomendada)**
1. Descargue el `.zip` del último [Release](https://github.com/luan920530-commits/ARCHIFORGE/releases)
2. En Blender: `Edit → Preferences → Add-ons → Install…` y seleccione el ZIP
3. Active **ArchiForge**. Si instala desde código fuente, asegúrese de que
   `__init__.py` quede directamente dentro de la carpeta del addon.

**Opción B — Carpeta manual**
Copie o clone el paquete completo en la carpeta `scripts/addons/ArchiForge/`:
- Windows: `%APPDATA%\Blender Foundation\Blender\3.3\scripts\addons\ArchiForge\`
- macOS: `~/Library/Application Support/Blender/3.3/scripts/addons/ArchiForge/`
- Linux: `~/.config/blender/3.3/scripts/addons/ArchiForge/`

La carpeta `ArchiForge` debe contener `__init__.py` y los módulos `af_*.py`
(al mismo nivel). Luego active **ArchiForge** en `Preferences → Add-ons`.

**Opción C — Desarrollo**
Desde la carpeta `scripts/addons/`:
```bash
git clone https://github.com/luan920530-commits/ARCHIFORGE.git ArchiForge
```
Con el addon cargado, `F8` en Blender recarga scripts. El hot-reload intenta
desregistrar las clases y callbacks anteriores antes de recargar módulos.

### Blender 4.2+ — instalar como extensión

El repositorio incluye `blender_manifest.toml` (id `archiforge`,
`blender_version_min = "4.2.0"`), así que el mismo código funciona como
**extensión** de Blender 4.2 LTS o posterior y puede publicarse en
[extensions.blender.org](https://extensions.blender.org/submit/):

```bash
# desde la raíz del repositorio; genera archiforge-<versión>.zip
blender --command extension build
blender --command extension validate archiforge-1.14.1.zip
```

El paquete deja `blender_manifest.toml` en la raíz del ZIP y excluye
`tests/`, scripts de desarrollo y `icons/generate_icons.py` (ver `[build]`
en el manifiesto). Instálelo arrastrando el ZIP a la ventana de Blender o con
`Preferences → Get Extensions → ⌄ → Install from Disk…`. En Blender 3.3–4.1
siga usando las opciones A–C (`bl_info` se conserva para ese caso; Blender
4.2+ lo ignora y lee el manifiesto). El addon no usa red; declara el permiso
`files` porque guarda presets y exporta CSV.

> 💡 **Actualizando desde una versión anterior**: haga copia de su carpeta
> `ArchiForge`, copie los archivos nuevos encima y desactive/reactive
> el addon (o reinicie Blender). Desde v1.5.1, si falta algún módulo
> el addon igual carga y lo reporta en consola.

## 🎮 Uso rápido

1. Abra el **Control Center** (`Shift+A → ArchiForge → Control Center`)
   o el panel lateral (`N`) → pestaña **ArchiForge**
2. Pulse el botón del objeto que quiere crear
3. Ajuste medidas y opciones en sus propiedades — la malla se regenera sola
4. Use **Regenerate / Force Update** si necesita regenerar manualmente

> 💡 Los objetos se crean en el cursor 3D, con origen en el piso.

## 📊 Cantidades y alcance

El exportador genera un CSV separado por punto y coma, con BOM UTF-8 para
Excel, a partir de los objetos de la **escena activa**. Incluye longitudes de
muros/vallas (con el retorno de recintos cerrados), áreas de planta, geometría
de losas, piezas paramétricas y objetos de Room Asset Library por ambiente.
Los huecos rectangulares se descuentan de forma aproximada; los techos se
reportan como **área proyectada** (`m2 proy.`), sin aplicar la pendiente.

Son **estimaciones geométricas basadas en parámetros**, no un presupuesto ni
una medición normativa: no incluyen automáticamente escalas de objeto,
mermas, traslapos, acero, acabados ni la composición real de sistemas
aligerados. Verifique y ajuste los resultados antes de usarlos para compra,
licitación o construcción.

## 🎨 Materiales

Cada objeto trae slots `AF.*` auto-asignados (cerámica, metal, vidrio,
madera, tela…). Desde v1.12 los materiales de obra (ladrillo, bloque,
concreto, pañete, cerámica, madera, mármol, teja, tela) son árboles de nodos
procedurales —ver la sección v1.12— y la preferencia **Procedural
Materials** permite volver a colores planos. Edite el material `AF.*` en el
editor de shaders y el cambio aplica a todos los objetos que lo usan.

## 🗂️ Estructura

```
ArchiForge/
├── blender_manifest.toml # Manifiesto de extensión Blender 4.2+ (extensions.blender.org)
├── __init__.py          # Registro, panel lateral, menú Shift+A, preferencias (v1.14.1)
├── af_control_center.py # Ventana flotante lanzadora (v1.0)
├── af_i18n.py           # Idioma del addon: tablas para bpy.app.translations (v1.11)
├── af_icons.py          # Helper de iconos propios: icon_kw(), ITEM_ICONS, OBJECT_ICONS (v1.13)
├── af_i18n_es.py        # Diccionario English ⇄ Español de toda la interfaz
├── af_material.py       # Gestión de materiales AF.* (planos o procedurales)
├── af_material_procedural.py # Recetas de nodos puras (ladrillo, bloque, cerámica, madera…) + validador
├── af_units.py          # Sistema de unidades puro: factores, ft/in, sincronización de escena
├── af_annotation_geometry.py # Geometría pura de cotas, ejes con burbuja y norte
├── af_annotation.py     # Operadores y panel de anotaciones (curvas + textos)
├── af_sets.py           # Conjuntos: baño completo (CO) y apartamento demo
├── af_objects_base.py   # Constructor base (AF_ObjectBuilder)
├── af_room_assets_catalog.py # Catálogo puro de 100 presets por ambiente
├── af_room_assets.py        # Generador paramétrico de muebles y sets
├── af_wall_path.py      # Geometría y validación pura de trazos de muro
├── af_floor_geometry.py # Triangulación, recorte poligonal y alturas de junta (puro)
├── af_window_geometry.py # Cinemática pura de hojas abatibles/proyectantes y bisagras
├── af_construction_presets.py # Formatos de baldosa, espesores de muro de referencia y su material (puro)
├── af_outline_draw.py   # Interacción modal común de contornos cerrados
├── af_wall.py           # Muros paramétricos, referencias de espesor y Draw Wall / Room
├── af_slab.py           # Losas: 4 sistemas + Draw Slab Outline
├── af_floor.py          # Patrones de piso, formatos de baldosa, juntas y contornos
├── af_roof.py           # Techos + 9 cubiertas (v1.1)
├── af_door.py           # Puertas + presets CO (v1.1)
├── af_window.py         # Ventanas + presets CO; hojas abatibles/proyectantes (v1.10)
├── af_stair.py          # Escaleras (recta, L, caracol) + rampa; alias y migración de af_stairs
├── af_structure.py      # Estructura+ (v1.0)
├── af_bathroom.py       # Baño v2 + ducha eléctrica CO
├── af_electrical.py     # Eléctrico v2.1 + norma CO/GFCI
├── af_furniture.py      # Muebles + camas CO
├── af_kitchen.py        # Cocina
├── af_decor.py          # Decoración
├── af_openings.py       # Puertas/ventanas paramétricas
├── af_quantities.py     # Integración de exportación CSV con Blender
├── af_quantities_io.py  # Cálculos/CSV puros, testeables sin Blender
├── icons/               # 112 iconos PNG originales + generador procedural
└── tests/               # Regresiones, comprobaciones estáticas y stub headless de bpy
```

## 📝 Versiones

Ver [CHANGELOG.md](CHANGELOG.md) para el detalle completo.

- **v1.14.1** — Verificado en Blender 4.2.23 LTS real: corrige la generación de muros/pisos/vallas/cerchas en 4.x (`polygon_layers_int`), el registro de la biblioteca de ambientes, los sub-paneles Snap/Manipulador, Render Setup con EEVEE Next y los callbacks de segmentos; nuevo *smoke test* dentro de Blender, job de CI `blender-smoke` y reglas de API 4.x en la suite
- **v1.14.0** — Extensión para Blender 4.2+: `blender_manifest.toml` validado con el CLI oficial, versión única `ADDON_VERSION`, resolución del paquete `bl_ext.*` en iconos e idioma y nombres de sockets del Principled BSDF 4.x
- **v1.13.0** — Iconografía completa: 88 iconos nuevos (112 en total) para funciones y cada ítem de los catálogos, helper `af_icons.py` y menús/paneles/preferencias con iconos propios
- **v1.12.0** — Materiales procedurales de nodos, sistema de unidades métrico/imperial efectivo, mensajes de estado traducidos, anotaciones (cotas, ejes, norte), conjuntos baño CO / apartamento demo y unificación de los módulos de escaleras
- **v1.11.0** — Idioma del addon English/Español operativo: traduce paneles, operadores, propiedades, desplegables y descripciones sin cambiar el idioma de Blender
- **v1.10.0** — Ventanas abatibles/proyectantes que giran hoja, vidrio y divisiones; formatos de baldosa 30×30 → 60×120; juntas a ras/resaltadas/rehundidas; referencias de espesor de muro
- **v1.9.0** — Selector de idioma English/Español en preferencias (sin efecto hasta v1.11) y corrección de la manija de puertas con bisagra derecha
- **v1.8.0** — Biblioteca paramétrica de 100 objetos/sets para dormitorio, sala, cocina, baño y solar/jardín
- **v1.7.0** — Dibujo de contornos de losa/piso, recorte poligonal y ciclo de booleanos paramétricos
- **v1.6.0** — Dibujo de muros conectados y recintos cerrados con esquinas automáticas
- **v1.5.2** — Correcciones al hot-reload, conteo de cantidades, CSV seguro y CI
- **v1.5.1** — Hotfix: imports/reload tolerantes (un módulo ausente ya no tumba el addon)
- **v1.5.0** — 🎛️ Control Center flotante con todos los módulos
- **v1.4.0** — Estructura+ · Puertas/ventanas CO · Losas (4 sistemas) · Techos (9 cubiertas)
- **v1.3.0** — Aberturas paramétricas · Escaleras nuevas + rampa · Exportación CSV
- **v1.2.0** — Muebles, cocina, decoración · Pack Colombia
- **v1.1.0** — Baño v2 y eléctrico v2.x · Correcciones Blender 3.3
- **v1.0.0** — Versión original del addon

## ❓ Problemas frecuentes

| Síntoma | Solución |
|---|---|
| `NameError` / error al activar el addon | Actualice a v1.5.1+ y verifique que **todos** los `.py` estén en la carpeta |
| `TypeError` con `icon` al abrir el panel | Actualice a v1.1+: los iconos 4.x se reemplazaron por equivalentes 3.3 |
| `bmesh operators expect a single BMesh…` | Actualice `af_slab.py` a v1.1+ (llamada posicional) |
| El objeto no se regenera | Pulse **Regenerate / Force Update** en su panel de propiedades |
| Falta un módulo en el Control Center | El diálogo lo omite solo; revise la consola (`Window → Toggle System Console`) para ver qué archivo falta |
| En Blender 4.x no se crean muros/pisos (`polygon_layers_int`) o falla Render Setup (`BLENDER_EEVEE`) | Actualice a v1.14.1+ |
| macOS: «No puedes usar esta versión de Blender con esta versión de macOS» | Blender 4.1+ exige macOS 11.2; en Catalina o anterior use Blender 3.3 LTS con el ZIP clásico |

¿Otro error? Abra un **Issue** pegando el traceback completo de la consola.

## 🧪 Pruebas de desarrollo

El conjunto de pruebas no requiere Blender y se ejecuta con la biblioteca
estándar de Python:

```bash
python -m unittest discover -s tests -v
```

Comprueba sintaxis compatible con Python 3.10, unicidad de identificadores
Blender, cantidades/CSV en métrico e imperial, conversión de unidades,
triangulación y recorte poligonal, el catálogo de presets de muro/baldosa y
su material, las recetas de materiales procedurales (tipos de nodo y enlaces
válidos para Blender 3.3–4.x), la geometría de cotas/ejes/norte, la migración
de escaleras heredadas, el flujo de creación/actualización de booleanos y
la traducción del addon (`tests/test_i18n.py`: toda cadena de interfaz
detectada por `tests/ui_strings.py` debe existir en `af_i18n_es.py`, sin
claves duplicadas ni marcadores de formato perdidos; `python
tests/ui_strings.py` lista las que falten). `tests/blender_stub.py` sustituye `bpy`/`bmesh`/`mathutils` por contenedores
mínimos para ejecutar los generadores reales de ventanas y pisos y verificar
sus coordenadas (hojas giradas con vidrio y divisiones, pernios sobre el eje,
alturas de junta y losa base). La interacción modal, la construcción real de
los árboles de nodos, los conjuntos combinados y el resto de la geometría
deben validarse además dentro de Blender.

`tests/test_blender_api_rules.py` codifica lo aprendido al ejecutar el addon
en Blender 4.2 real: el stub aplica las reglas de `EnumProperty`, los
sub-paneles deben registrarse después de su `bl_parent_id` y no se admiten
APIs eliminadas en 4.x (`polygon_layers_*`, `calc_normals`, `bgl`,
`BLENDER_EEVEE` literal) sin su guarda.

**Dentro de Blender 4.2+** (requiere el ZIP de extensión):

```bash
blender --command extension build --output-dir dist
blender -b --python-exit-code 1 --python tests/blender_smoke_42.py -- \
    --zip dist/archiforge-1.14.1.zip --report smoke_report.json
```

Instala el ZIP con el mismo operador que *Install from Disk*, verifica el
registro como `bl_ext.user_default.archiforge`, ejecuta los 125 operadores y
termina con desactivar/reactivar/desinstalar. El job de CI `blender-smoke`
lo corre con el último Blender 4.2.x LTS oficial para Linux y publica el
reporte JSON como artefacto.

## 🛣️ Roadmap

- [x] Control Center flotante
- [x] Exportación de cantidades (CSV)
- [x] Módulo de anotaciones 📐 (cotas, ejes con burbuja, norte) — v1.12
- [x] Sets combinados (apartamento demo, baño CO completo) — v1.12
- [x] Materiales procedurales de nodos (ladrillo, bloque, cerámica, madera, concreto…) — v1.12
- [ ] Módulo hidrosanitario 🚿 (tuberías, aparatos, puntos hidráulicos)
- [ ] Capas de muro (estructura + acabados) y aparejo como geometría
- [ ] Rótulos de ambiente y niveles en el módulo de anotaciones

## 🤝 Contribuir

1. Haga un fork y cree una rama (`git checkout -b mi-modulo`)
2. Siga el estilo del código (cabecera GPL, `py_compile` limpio, compatible 3.3)
3. Abra un Pull Request describiendo el cambio

## 📄 Licencia

GPL v3 — ArchiForge Devs. Ver [LICENSE](LICENSE).
