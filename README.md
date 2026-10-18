# ArchiForge 🏗️

**Modelado arquitectónico paramétrico para Blender 3.3 LTS y posteriores**

[![Blender](https://img.shields.io/badge/Blender-3.3_LTS-orange)](https://www.blender.org)
[![Version](https://img.shields.io/badge/version-1.6.0-blue)](CHANGELOG.md)
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
calculadas en conjunto. Los recintos cerrados incluyen el tramo de retorno,
cierran las esquinas automáticamente y se pueden editar desde **Wall
Properties** (por ejemplo, altura y espesor); no hace falta alinear muros
independientes a mano.

---

## ✨ Módulos

| Módulo | Contenido |
|---|---|
| 🧱 Muros / Losas | Muros paramétricos + **Draw Wall / Room** (trazo conectado, recintos cerrados), desde curva; losas: **MACIZA · ALIGERADA · PLACA FÁCIL · STEELDECK** (v1.2), pisos/cielorrasos y huecos |
| 🏠 Techos (v1.1) | Gable, Shed, Hip, Saltbox, Butterfly, Mansard, Bóveda + **9 cubiertas**: zinc, eternit, termoacústica, metálica, española, romana, plana, tejuela |
| 🚪 Puertas / Ventanas (v1.1) | Presets CO: puertas 0.70–1.20 m, ventanas 1.00×1.00 → 2.40×2.20 + antepecho; modos Draw y Place |
| 🪜 Escaleras | Clásicas (presets) + nuevas: recta, en L, caracol y **rampa 8%** |
| 🏗️ Estructura+ | Zapatas, columnas, vigas, losa aligerada, ejes/rejilla y niveles con rótulos |
| 🛁 Baño (v2) | Sanitario, bidé, lavamanos, vanitorio, ducha, tina, espejo, toallero, **ducha eléctrica 🇨🇴** |
| 🔌 Eléctrico (v2.1) | Tomas EU/US/UK/**CO+GFCI 🇨🇴**, interruptores, datos RJ45, bombillos, colgantes, downlights, apliques, tablero + **luz real de Blender** |
| 🛋️ Muebles | Sillas, poltrona, sofá, mesas, **camas CO 🇨🇴** (sencilla → king), nochero, chifonier, biblioteca |
| 🍳 Cocina | Nevera, estufa, campana, lavaplatos, lavavajillas, microondas, utensilios |
| 🪴 Decoración | Materas con plantas, lámparas, floreros, cuadros, reloj, libros, TV, tapete |
| 🚧 Extras | Cerchas (truss), cercas, pisos/patterns, booleanas automáticas |
| 📊 Cantidades | **Exportación CSV (Excel)** de cantidades del proyecto |

**Pack Colombia 🇨🇴**: tomas con GFCI, ducha eléctrica tipo Lorenzetti,
camas sencilla / semidoble / doble / queen / king, puertas y ventanas
en medidas comerciales colombianas.

## 📋 Requisitos

- **Blender 3.3 LTS o posterior** (3.3 es la versión mínima declarada en el addon).
  La compatibilidad real debe verificarse en la versión de Blender de destino;
  no se incluye Blender en las pruebas automatizadas del repositorio.
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
de losas y conteo de piezas paramétricas. Los huecos rectangulares se
descuentan de forma aproximada; los techos se reportan como **área
proyectada** (`m2 proy.`), sin aplicar la pendiente.

Son **estimaciones geométricas basadas en parámetros**, no un presupuesto ni
una medición normativa: no incluyen automáticamente escalas de objeto,
mermas, traslapos, acero, acabados ni la composición real de sistemas
aligerados. Verifique y ajuste los resultados antes de usarlos para compra,
licitación o construcción.

## 🎨 Materiales

Cada objeto trae slots `AF.*` auto-asignados (cerámica, metal, vidrio,
madera, tela…). Edite el material `AF.*` en el editor de shaders y el
cambio aplica a todos los objetos que lo usan.

## 🗂️ Estructura

```
ArchiForge/
├── __init__.py          # Registro, panel lateral, menú Shift+A (v1.6.0)
├── af_control_center.py # Ventana flotante lanzadora (v1.0)
├── af_material.py       # Gestión de materiales AF.*
├── af_objects_base.py   # Constructor base (AF_ObjectBuilder)
├── af_wall_path.py      # Geometría y validación pura de trazos de muro
├── af_wall.py           # Muros paramétricos y herramienta Draw Wall / Room
├── af_slab.py           # Losas: 4 sistemas constructivos (v1.2)
├── af_roof.py           # Techos + 9 cubiertas (v1.1)
├── af_door.py           # Puertas + presets CO (v1.1)
├── af_window.py         # Ventanas + presets CO (v1.1)
├── af_stairs.py         # Escaleras nuevas + rampa
├── af_structure.py      # Estructura+ (v1.0)
├── af_bathroom.py       # Baño v2 + ducha eléctrica CO
├── af_electrical.py     # Eléctrico v2.1 + norma CO/GFCI
├── af_furniture.py      # Muebles + camas CO
├── af_kitchen.py        # Cocina
├── af_decor.py          # Decoración
├── af_openings.py       # Puertas/ventanas paramétricas
├── af_quantities.py     # Integración de exportación CSV con Blender
├── af_quantities_io.py  # Cálculos/CSV puros, testeables sin Blender
├── icons/               # Iconos opcionales (fallback nativo de Blender)
└── tests/               # Regresiones y comprobaciones estáticas
```

## 📝 Versiones

Ver [CHANGELOG.md](CHANGELOG.md) para el detalle completo.

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

¿Otro error? Abra un **Issue** pegando el traceback completo de la consola.

## 🧪 Pruebas de desarrollo

El conjunto de pruebas no requiere Blender y se ejecuta con la biblioteca
estándar de Python:

```bash
python -m unittest discover -s tests -v
```

Comprueba sintaxis compatible con Python 3.10, unicidad de identificadores
Blender y regresiones del cálculo/exportación de cantidades y de la geometría
pura de los trazos de muro. La geometría generada y la interfaz modal deben
probarse además dentro de Blender; CI no sustituye esa validación.

## 🛣️ Roadmap

- [x] Control Center flotante
- [x] Exportación de cantidades (CSV)
- [ ] Módulo hidrosanitario 🚿 (tuberías, aparatos, puntos hidráulicos)
- [ ] Módulo de anotaciones 📐 (cotas, ejes, rótulos, norte)
- [ ] Sets combinados (apartamento demo, baño CO completo)
- [ ] Enchapes y acabados procedurales adicionales

## 🤝 Contribuir

1. Haga un fork y cree una rama (`git checkout -b mi-modulo`)
2. Siga el estilo del código (cabecera GPL, `py_compile` limpio, compatible 3.3)
3. Abra un Pull Request describiendo el cambio

## 📄 Licencia

GPL v3 — ArchiForge Devs. Ver [LICENSE](LICENSE).
