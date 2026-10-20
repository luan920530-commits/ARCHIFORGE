# Iconos de ArchiForge

Esta carpeta contiene los **112 iconos PNG originales** del addon, listos para
cargar en las vistas previas de Blender. Todos se renderizan a **128 × 128 px**,
con transparencia y un estilo coherente de azul noche, turquesa y dorado sobre
una baldosa redondeada. No se requieren descargas ni dependencias externas al
instalar o ejecutar ArchiForge.

## Cómo se usan

`__init__.py` carga cada PNG en una colección `bpy.utils.previews` usando el
nombre del archivo (sin extensión) como clave. Cualquier módulo los consume a
través de `af_icons.py`:

```python
from .af_icons import icon_kw as _icon, item_icon as _item_icon

row.operator("archiforge.wall", text="Wall", **_icon("wall", 'SNAP_FACE'))
row.operator("archiforge.bathroom", text="Toilet",
             **_icon(_item_icon('TOILET', "bathroom"), 'SPHERE'))
```

`icon_kw()` devuelve `{'icon_value': id}` si el icono está cargado y
`{'icon': <icono nativo>}` en caso contrario, de modo que la interfaz nunca
recibe `icon_value=0` ni se rompe si falta una imagen. `ITEM_ICONS` asocia
cada `item_type` de los catálogos con su icono y `OBJECT_ICONS` cada grupo de
propiedades (`archiforge_wall`, …) con el icono del módulo.

## Inventario

- **Marca:** `archiforge` (`archipack` es un alias de compatibilidad).
- **Módulos:** `wall`, `wall_draw`, `slab`, `roof`, `truss`, `fence`, `floor`,
  `door`, `window`, `stair`, `opening`, `structure`, `bathroom`, `electrical`,
  `furniture`, `kitchen`, `decor`, `quantities`, `control_center`, `boolean`,
  `snap`, `material`.
- **Funciones:** `annotation`, `dimension`, `dimension_draw`, `grid_axes`,
  `north_arrow`, `sets`, `set_bathroom`, `set_apartment`, `units`, `language`,
  `procedural`, `preferences`, `material_library`, `scene`, `tools`,
  `quick_edit`, `manipulator`, `reference_point`, `render`, `preset`,
  `room_assets`, `place`, `draw`, `curve`, `ceiling`.
- **Baño:** `toilet`, `bidet`, `pedestal_sink`, `vanity`, `basin`, `shower`,
  `bathtub`, `mirror`, `towel_rail`, `electric_shower`.
- **Eléctrico:** `outlet`, `switch`, `data`, `bulb`, `pendant`,
  `ceiling_light`, `downlight`, `sconce`, `panel_board`.
- **Muebles:** `dining_chair`, `office_chair`, `armchair`, `sofa`,
  `coffee_table`, `dining_table`, `bed`, `nightstand`, `dresser`, `shelf`.
- **Cocina:** `fridge`, `stove`, `range_hood`, `sink_cabinet`, `dishwasher`,
  `microwave`, `utensils`.
- **Decoración:** `planter`, `floor_lamp`, `table_lamp`, `vase_set`,
  `wall_art`, `clock`, `books`, `tv`, `rug`.
- **Aberturas:** `door_single`, `door_double`, `door_sliding`, `win_sliding`,
  `win_casement`, `win_fixed`.
- **Circulación:** `stair_l`, `stair_spiral`, `ramp` (la recta usa `stair`).
- **Estructura+:** `footing`, `column`, `beam`, `ribbed_slab`, `grid`,
  `levels`.
- **Cubiertas:** `roof_gable`, `roof_hip`, `roof_shed`.

`tests/test_icon_assets.py` comprueba que los PNG coinciden exactamente con
`generate_icons.ICONS`, que todo icono referenciado por la interfaz existe y
que cada `item_type` de los catálogos tiene icono.

## Edición y regeneración

El arte y sus formas se definen en `generate_icons.py` (trazos geométricos,
sin fuentes, renderizado a 4× y reducido con LANCZOS; el resultado es
determinista). Para regenerar los PNG hace falta Pillow solo en el entorno de
desarrollo:

```bash
python -m pip install Pillow
python icons/generate_icons.py            # todos
python icons/generate_icons.py sofa bed   # solo algunos
```

Pillow **no** es una dependencia del addon. Las imágenes incluidas son
recursos originales de ArchiForge y se distribuyen con el proyecto bajo su
licencia GPL v3.
