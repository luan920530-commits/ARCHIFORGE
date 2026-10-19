# Iconos de ArchiForge

Esta carpeta contiene iconos PNG originales del addon, listos para cargar en
las vistas previas de Blender. Todos se renderizan a **128 × 128 px**, con
transparencia y un estilo coherente de azul noche, turquesa y dorado. No se
requieren descargas ni dependencias externas al instalar o ejecutar ArchiForge.

## Marca y módulos

- `archiforge.png` — logotipo AF, usado en el panel, las preferencias y el
  Control Center.
- `archipack.png` — alias de compatibilidad del mismo logotipo.
- `wall.png`, `wall_draw.png`, `slab.png`, `roof.png`, `truss.png`,
  `fence.png`, `floor.png`, `structure.png`.
- `door.png`, `window.png`, `opening.png`, `stair.png`.
- `bathroom.png`, `electrical.png`, `furniture.png`, `kitchen.png`,
  `decor.png`, `quantities.png`.
- `control_center.png`, `boolean.png`, `snap.png`, `material.png`.

Los nombres de archivo son los identificadores que consume `_icon_kw()` en
`__init__.py` y `af_control_center.py`. Si falta o falla una imagen, la UI
conserva el icono nativo de Blender como respaldo.

## Edición y regeneración

El arte y sus formas se definen en `generate_icons.py`. Para regenerar los PNG
hace falta Pillow solo en el entorno de desarrollo:

```bash
python -m pip install Pillow
python icons/generate_icons.py
```

Pillow **no** es una dependencia del addon. Las imágenes incluidas son
recursos originales de ArchiForge y se distribuyen con el proyecto bajo su
licencia GPL v3.
