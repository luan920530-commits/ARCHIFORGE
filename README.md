# ArchiForge 🏗️

**Modelado arquitectónico paramétrico para Blender 3.3 LTS**

[![Blender](https://img.shields.io/badge/Blender-3.3_LTS-orange)](https://www.blender.org)
[![Version](https://img.shields.io/badge/version-1.5.1-blue)](CHANGELOG.md)
[![License](https://img.shields.io/badge/license-GPLv3-green)](LICENSE)
[![Colombia](https://img.shields.io/badge/pack-Colombia 🇨🇴-yellow)](README.md#pack-colombia-)

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

## ✨ Módulos

| Módulo | Contenido |
|---|---|
| 🧱 Muros / Losas | Muros (+Draw, desde curva), losas: **MACIZA · ALIGERADA · PLACA FÁCIL · STEELDECK** (v1.2), desde muro/curva, pisos y cielorrasos, huecos |
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

- **Blender 3.3 LTS** (probado en 3.3.x; iconos y llamadas `bmesh`
  100% compatibles con 3.3)
- Sin dependencias externas: solo Blender + Python estándar
- macOS / Windows / Linux

## 🚀 Instalación

**Opción A — ZIP (recomendada)**
1. Descargue el `.zip` del último [Release](../../releases) y descomprímalo
2. En Blender: `Edit → Preferences → Add-ons → Install…` → seleccione
   la carpeta `ArchiForge`
3. Active la casilla **ArchiForge**

**Opción B — Carpeta manual**
1. Copie la carpeta `ArchiForge` en sus addons:
   - Windows: `%APPDATA%\Blender Foundation\Blender\3.3\scripts\addons\`
   - macOS: `~/Library/Application Support/Blender/3.3/scripts/addons/`
   - Linux: `~/.config/blender/3.3/scripts/addons/`
2. En `Preferences → Add-ons`, active **ArchiForge**

**Opción C — Desarrollo**
```bash
git clone https://github.com/TU-USUARIO/archiforge.git
```
Luego enlace o copie la carpeta a su ruta de addons. Con el addon cargado,
pulse `F8` en Blender para recargar cambios sin reiniciar.

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

## 🎨 Materiales

Cada objeto trae slots `AF.*` auto-asignados (cerámica, metal, vidrio,
madera, tela…). Edite el material `AF.*` en el editor de shaders y el
cambio aplica a todos los objetos que lo usan.

## 🗂️ Estructura

```
ArchiForge/
├── __init__.py          # Registro, panel lateral, menú Shift+A (v1.5.1)
├── af_control_center.py # Ventana flotante lanzadora (v1.0)
├── af_material.py       # Gestión de materiales AF.*
├── af_objects_base.py   # Constructor base (AF_ObjectBuilder)
├── af_wall.py           # Muros
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
├── af_quantities.py     # Exportación CSV
└── ...                  # Escalera clásica, cerca, piso, cercha, snap, UI
```

## 📝 Versiones

Ver [CHANGELOG.md](CHANGELOG.md) para el detalle completo.

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
