# ArchiForge 🏗️

**Modelado arquitectónico paramétrico para Blender 3.3 LTS**

[![Blender](https://img.shields.io/badge/Blender-3.3_LTS-orange)](https://www.blender.org)
[![Version](https://img.shields.io/badge/version-1.2.0-blue)](CHANGELOG.md)
[![License](https://img.shields.io/badge/license-GPLv3-green)](LICENSE)

ArchiForge genera muros, losas, baños, instalaciones eléctricas, muebles, cocinas y decoración como objetos **paramétricos y editables**: cambie una medida en el panel y la geometría se regenera al instante.

---

## ✨ Módulos

| Módulo | Contenido |
|---|---|
| 🧱 Muros / Losas / Estructura | Muros, losas (rectangular, desde curva, desde muro, custom + huecos), cerchas |
| 🛁 Baño (v2) | Sanitario, lavamanos, vanitorio, ducha, tina, bidé, espejo, toallero, **ducha eléctrica 🇨🇴** |
| 🔌 Eléctrico (v2.1) | Tomas EU/US/UK/**CO+GFCI 🇨🇴**, interruptores, bombillos, lámparas de techo, colgantes, apliques, tablero |
| 🛋️ Muebles (v1.2 🆕) | Sillas, poltrona, sofá, mesas, **cama en medidas colombianas 🇨🇴**, nochero, chifonier, biblioteca |
| 🍳 Cocina (v1.2 🆕) | Nevera, estufa, campana, lavaplatos, lavavajillas, microondas, utensilios |
| 🪴 Decoración (v1.2 🆕) | Materas con plantas, lámparas, floreros, cuadros, reloj, libros, TV, tapete |

**Pack Colombia 🇨🇴**: tomas con GFCI, ducha eléctrica tipo Lorenzetti y camas sencilla / semidoble / doble / queen / king.

## 📋 Requisitos

- **Blender 3.3 LTS** (probado en 3.3.x; los iconos y llamadas `bmesh` son compatibles con 3.3)
- Sin dependencias externas: solo Blender + Python estándar

## 🚀 Instalación

**Opción A — ZIP (recomendada)**
1. Descargue el repositorio como `.zip` y descomprímalo
2. En Blender: `Edit → Preferences → Add-ons → Install…` → seleccione la carpeta `ArchiForge`
3. Active la casilla **ArchiForge**

**Opción B — Carpeta manual**
1. Copie la carpeta `ArchiForge` en sus addons:
   - Windows: `%APPDATA%\Blender Foundation\Blender\3.3\scripts\addons\`
   - macOS: `~/Library/Application Support/Blender/3.3/scripts/addons/`
   - Linux: `~/.config/blender/3.3/scripts/addons/`
2. En `Preferences → Add-ons`, active **ArchiForge**

**Opción C — Desarrollo**
```bash
git clone https://github.com/luan920530-commits/archiforge.git
```
Luego enlace o copie la carpeta a su ruta de addons. Con el addon cargado, pulse `F8` en Blender para recargar cambios sin reiniciar.

## 🎮 Uso rápido

1. En la vista 3D abra el panel lateral (`N`) → pestaña **ArchiForge**
2. Pulse el botón del objeto que quiere (o `Shift+A` → ArchiForge)
3. Ajuste medidas y opciones en las propiedades del objeto — la malla se regenera sola
4. Botón **Force Update** si necesita regenerar manualmente

> 💡 Los objetos se crean en el cursor 3D, con origen en el piso y frente hacia −Y.

## 🎨 Materiales

Cada objeto trae slots `AF.*` auto-asignados (cerámica, metal, vidrio, madera, tela…). Edite el material `AF.*` en el editor de shaders y el cambio aplica a todos los objetos que lo usan.

## 🗂️ Estructura

```
ArchiForge/
├── __init__.py          # Registro, panel lateral y menú Shift+A
├── af_material.py       # Gestión de materiales AF.*
├── af_objects_base.py   # Constructor base (AF_ObjectBuilder)
├── af_slab.py           # Losas y forjados
├── af_bathroom.py       # Baño v2 + ducha eléctrica CO
├── af_electrical.py     # Eléctrico v2.1 + norma CO/GFCI
├── af_furniture.py      # Muebles + camas CO
├── af_kitchen.py        # Cocina
├── af_decor.py          # Decoración
└── ...                  # Muros, techos, escaleras, estructura
```

## 📝 Versiones

- **v1.2.0** — Muebles, cocina y decoración · Pack Colombia (GFCI, ducha, camas) · Losa 100% compatible 3.3
- **v1.1.0** — Baño v2 y eléctrico v2.1 (más detalle/polígonos) · Corrección de iconos para 3.3
- **v1.0.0** — Versión original del addon

## ❓ Problemas frecuentes

| Síntoma | Solución |
|---|---|
| `TypeError` con `icon` al abrir el panel | Actualice a v1.1+: los iconos 4.x se reemplazaron por equivalentes 3.3 |
| `bmesh operators expect a single BMesh…` | Actualice `af_slab.py` a v1.1 (llamada posicional) |
| El objeto no se regenera | Pulse **Force Update** en su panel de propiedades |

¿Otro error? Abra un **Issue** pegando el traceback completo de la consola (`Window → Toggle System Console`).

## 🛣️ Roadmap

- Sets combinados (sala-comedor, baño CO completo, apartamento demo)
- Enchapes y acabados procedurales adicionales
- Exportación de cantidades (despieces)

## 🤝 Contribuir

1. Haga un fork y cree una rama (`git checkout -b mi-modulo`)
2. Siga el estilo del código (cabecera GPL, `py_compile` limpio, compatible 3.3)
3. Abra un Pull Request describiendo el cambio

## 📄 Licencia

GPL v3 — ArchiForge Devs. Ver [LICENSE](LICENSE).
