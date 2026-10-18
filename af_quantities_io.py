# -*- coding: utf-8 -*-
"""Pure helpers for ArchiForge's quantity takeoff and CSV export.

This module deliberately has no Blender dependency so the calculations and
CSV safety rules can be regression-tested with the standard Python runtime.
"""

import csv
import math


CSV_HEADERS = ("Categoría", "Tipo", "Objeto", "Cantidad", "Unidad", "Medidas")
FORMULA_PREFIXES = ("=", "+", "-", "@")


def _number(value, default=0.0):
    """Return a finite float, or *default* for missing/invalid values."""
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return float(default)
    return result if math.isfinite(result) else float(default)


def _property_number(props, name, default=0.0):
    try:
        value = getattr(props, name, default)
    except (AttributeError, ReferenceError, TypeError):
        return float(default)
    return _number(value, default)


def _property_text(props, *names, default="—"):
    for name in names:
        try:
            value = getattr(props, name, None)
        except (AttributeError, ReferenceError, TypeError):
            continue
        if value is not None and str(value).strip():
            return str(value)
    return default


def _registered_props(obj, attr, marker):
    """Return a populated ArchiForge PropertyGroup, not its default shell.

    Blender exposes PointerProperty groups on every Object. Most AF marker
    booleans default to True, so checking the boolean alone classifies every
    mesh as an AF object. Every generator also writes ``object_name``; using
    that field distinguishes generated objects from unused default groups and
    continues to work if the user renames or duplicates the object.
    """
    try:
        props = getattr(obj, attr, None)
        if props is None or not bool(getattr(props, marker, False)):
            return None
        if not str(getattr(props, "object_name", "")).strip():
            return None
    except (AttributeError, ReferenceError, TypeError):
        return None
    return props


def _object_name(obj):
    try:
        return str(getattr(obj, "name", ""))
    except (ReferenceError, TypeError):
        return ""


def _segments_length(parts):
    """Sum the lengths of enabled wall/fence segments."""
    lengths = []
    try:
        for part in parts:
            try:
                if not bool(getattr(part, "enabled", True)):
                    continue
                length = _property_number(part, "length")
            except (AttributeError, ReferenceError, TypeError):
                continue
            if length > 0.0:
                lengths.append(length)
    except (ReferenceError, TypeError):
        return 0.0
    return math.fsum(lengths)


def _wall_length(props):
    """Sum enabled wall segments; never confuse thickness with length."""
    try:
        parts = getattr(props, "parts", ())
    except (AttributeError, ReferenceError, TypeError):
        parts = ()
    return _segments_length(parts)


def _polygon_bounds(vertices):
    """Return the X/Y extents of a polygon, or ``(0, 0)`` if invalid."""
    points = []
    try:
        for vertex in vertices:
            x = _property_number(vertex, "x", math.nan)
            y = _property_number(vertex, "y", math.nan)
            if not math.isfinite(x) or not math.isfinite(y):
                return 0.0, 0.0
            points.append((x, y))
    except (ReferenceError, TypeError):
        return 0.0, 0.0
    if len(points) < 3:
        return 0.0, 0.0
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return max(xs) - min(xs), max(ys) - min(ys)


def _polygon_area(vertices):
    """Area of a 2D polygon using the shoelace formula."""
    points = []
    try:
        for vertex in vertices:
            x = _property_number(vertex, "x", math.nan)
            y = _property_number(vertex, "y", math.nan)
            if not math.isfinite(x) or not math.isfinite(y):
                return 0.0
            points.append((x, y))
    except (ReferenceError, TypeError):
        return 0.0

    if len(points) < 3:
        return 0.0
    twice_area = math.fsum(
        points[i][0] * points[(i + 1) % len(points)][1]
        - points[(i + 1) % len(points)][0] * points[i][1]
        for i in range(len(points))
    )
    return abs(twice_area) * 0.5


def _slab_area(props):
    slab_type = _property_text(props, "slab_type", default="RECTANGLE")
    width = _property_number(props, "width")
    depth = _property_number(props, "depth")
    overhang = max(0.0, _property_number(props, "overhang"))

    if slab_type == "RECTANGLE":
        area = max(0.0, width + 2.0 * overhang) * max(
            0.0, depth + 2.0 * overhang)
    else:
        try:
            vertices = getattr(props, "vertices", ())
        except (AttributeError, ReferenceError, TypeError):
            vertices = ()
        area = _polygon_area(vertices)
        if area <= 0.0:
            area = max(0.0, width + 2.0 * overhang) * max(
                0.0, depth + 2.0 * overhang)

    # The generator cuts rectangular holes. Their rotation does not change
    # their area; overlapping holes are conservatively clamped at zero.
    hole_areas = []
    try:
        holes = getattr(props, "holes", ())
        for hole in holes:
            try:
                if not bool(getattr(hole, "enabled", True)):
                    continue
                hole_areas.append(
                    max(0.0, _property_number(hole, "width"))
                    * max(0.0, _property_number(hole, "depth"))
                )
            except (AttributeError, ReferenceError, TypeError):
                continue
    except (ReferenceError, TypeError):
        pass
    return max(0.0, area - math.fsum(hole_areas))


def _dimensions(props, width="width", depth="depth", height="height"):
    values = (
        _property_number(props, width),
        _property_number(props, depth),
        _property_number(props, height),
    )
    if not any(value > 0.0 for value in values):
        return "—"
    return "{}x{}x{} m".format(*(format_number(value) for value in values))


def _append_unit_row(rows, category, props, obj_name, type_fields,
                     dimension_fields=("width", "depth", "height")):
    item_type = _property_text(props, *type_fields, default=category)
    dimensions = _dimensions(props, *dimension_fields)
    rows.append((category, item_type, obj_name, 1, "und", dimensions))


def collect_quantities(objects):
    """Collect quantity rows from an iterable of scene objects.

    Each row is ``(category, type, object, quantity, unit, dimensions)``.
    Values are parametric estimates, not code-compliant material takeoffs.
    """
    rows = []
    for obj in objects:
        obj_name = _object_name(obj)

        props = _registered_props(obj, "archiforge_wall", "is_af_wall")
        if props is not None:
            length = _wall_length(props)
            height = _property_number(props, "height")
            thickness = _property_number(props, "width")
            if length > 0.0 and height > 0.0:
                item_type = _property_text(props, "wall_type", default="Muro")
                measures = "L={} H={} e={} m".format(
                    format_number(length), format_number(height),
                    format_number(thickness),
                )
                rows.append(("Muros", item_type, obj_name,
                             length * height, "m2", measures))
                if thickness > 0.0:
                    rows.append(("Muros", item_type, obj_name,
                                 length * height * thickness, "m3", measures))

        props = _registered_props(obj, "archiforge_slab", "is_af_slab")
        if props is not None:
            area = _slab_area(props)
            thickness = _property_number(props, "thickness")
            slab_type = _property_text(props, "slab_type", default="RECTANGLE")
            item_type = _property_text(
                props, "slab_system", "slab_type", default="Losa")
            width = _property_number(props, "width")
            depth = _property_number(props, "depth")
            if slab_type != "RECTANGLE":
                try:
                    vertices = getattr(props, "vertices", ())
                except (AttributeError, ReferenceError, TypeError):
                    vertices = ()
                polygon_width, polygon_depth = _polygon_bounds(vertices)
                if polygon_width > 0.0 and polygon_depth > 0.0:
                    width, depth = polygon_width, polygon_depth
            dimensions = "{}x{} e={} m (área neta aprox.)".format(
                format_number(width), format_number(depth),
                format_number(thickness),
            )
            if area > 0.0:
                rows.append(("Losas", item_type, obj_name,
                             area, "m2", dimensions))
                if thickness > 0.0:
                    rows.append(("Losas", item_type, obj_name,
                                 area * thickness, "m3", dimensions))

        props = _registered_props(obj, "archiforge_floor", "is_af_floor")
        if props is not None:
            width = _property_number(props, "width")
            depth = _property_number(props, "depth")
            if width > 0.0 and depth > 0.0:
                rows.append((
                    "Pisos", _property_text(props, "pattern", default="Piso"),
                    obj_name, width * depth, "m2",
                    "{}x{} m (área de planta)".format(
                        format_number(width), format_number(depth)),
                ))

        props = _registered_props(obj, "archiforge_fence", "is_af_fence")
        if props is not None:
            try:
                parts = getattr(props, "parts", ())
            except (AttributeError, ReferenceError, TypeError):
                parts = ()
            length = _segments_length(parts)
            if length > 0.0:
                rows.append((
                    "Cercas", _property_text(props, "fence_type", default="Valla"),
                    obj_name, length, "m",
                    "L={} H={} m".format(
                        format_number(length),
                        format_number(_property_number(props, "height")),
                    ),
                ))

        props = _registered_props(obj, "af_roof", "is_af_roof")
        if props is not None:
            width = _property_number(props, "width")
            depth = _property_number(props, "depth")
            if width > 0.0 and depth > 0.0:
                rows.append((
                    "Techos", _property_text(props, "roof_type", default="Techo"),
                    obj_name, width * depth, "m2 proy.",
                    "{}x{} m (proyección; no incluye pendiente)".format(
                        format_number(width), format_number(depth)),
                ))

        props = _registered_props(obj, "archiforge_truss", "is_af_truss")
        if props is not None:
            _append_unit_row(
                rows, "Cerchas", props, obj_name, ("truss_type",),
                ("span", "depth", "width"),
            )

        props = _registered_props(obj, "archiforge_struct", "is_af_struct")
        if props is not None:
            _append_unit_row(
                rows, "Estructura", props, obj_name, ("item_type",))

        props = _registered_props(obj, "archiforge_door", "is_af_door")
        if props is not None:
            _append_unit_row(rows, "Puertas", props, obj_name, ("door_type",))

        props = _registered_props(obj, "archiforge_window", "is_af_window")
        if props is not None:
            _append_unit_row(
                rows, "Ventanas", props, obj_name, ("window_type",))

        props = _registered_props(obj, "archiforge_opening", "is_af_opening")
        if props is not None:
            _append_unit_row(
                rows, "Aberturas", props, obj_name, ("item_type",))

        # Both the legacy staircase and the newer stair/ramp module are kept
        # for backwards compatibility and expose separate Object properties.
        for attr in ("archiforge_stair", "archiforge_stairs"):
            props = _registered_props(obj, attr, "is_af_stair")
            if props is None:
                continue
            item_type = _property_text(props, "item_type", default="Escalera")
            width = format_number(_property_number(props, "width"))
            rise = format_number(_property_number(props, "total_rise"))
            if item_type == "RAMP":
                slope = 100.0 * _property_number(props, "ramp_slope")
                measures = "A={} H={} pendiente={}%".format(
                    width, rise, format_number(slope))
            else:
                risers = int(max(0.0, _property_number(props, "n_risers")))
                measures = "A={} H={} contrahuellas={}".format(
                    width, rise, risers)
            rows.append(("Escaleras", item_type, obj_name, 1, "und", measures))

        unit_families = (
            ("archiforge_bathroom", "is_af_bathroom", "Baño"),
            ("archiforge_electrical", "is_af_electrical", "Eléctrico"),
            ("archiforge_furniture", "is_af_furniture", "Muebles"),
            ("archiforge_kitchen", "is_af_kitchen", "Cocina"),
            ("archiforge_decor", "is_af_decor", "Decoración"),
        )
        for attr, marker, category in unit_families:
            props = _registered_props(obj, attr, marker)
            if props is not None:
                _append_unit_row(
                    rows, category, props, obj_name, ("item_type",))

    return rows


def format_number(value):
    """Format a finite number with two decimals and ES-CO decimal comma."""
    number = _number(value, math.nan)
    if not math.isfinite(number):
        raise ValueError("La cantidad debe ser un número finito")
    return "{:.2f}".format(number).replace(".", ",")


def summarize(rows):
    """Sum quantities by ``(category, type, unit)`` in stable order."""
    totals = {}
    for category, item_type, _name, quantity, unit, _dimensions in rows:
        key = (category, item_type, unit)
        totals[key] = totals.get(key, 0.0) + _number(quantity, 0.0)
    return sorted(totals.items())


def _safe_text_cell(value):
    """Neutralize spreadsheet formulas in exported text cells."""
    text = "" if value is None else str(value)
    stripped = text.lstrip(" \t\r\n")
    if text.startswith(("\t", "\r", "\n")) or (
            stripped and stripped[0] in FORMULA_PREFIXES):
        return "'" + text
    return text


def _quantity_cell(quantity, unit):
    value = _number(quantity, math.nan)
    if not math.isfinite(value) or value < 0.0:
        raise ValueError("Las cantidades deben ser finitas y no negativas")
    if unit == "und":
        return str(int(round(value)))
    return format_number(value)


def write_csv(path, rows):
    """Write an Excel-friendly semicolon CSV and return its data row count.

    Text fields are quoted by the CSV writer and spreadsheet formulas are
    neutralized with a leading apostrophe. The UTF-8 BOM keeps Spanish labels
    readable in common Windows Excel installations.
    """
    rows = list(rows)
    data_rows = []
    for category, item_type, name, quantity, unit, dimensions in rows:
        data_rows.append((
            _safe_text_cell(category),
            _safe_text_cell(item_type),
            _safe_text_cell(name),
            _quantity_cell(quantity, unit),
            _safe_text_cell(unit),
            _safe_text_cell(dimensions),
        ))

    summary_rows = []
    for (category, item_type, unit), quantity in summarize(rows):
        summary_rows.append((
            _safe_text_cell(category),
            _safe_text_cell(item_type),
            _safe_text_cell(unit),
            _quantity_cell(quantity, unit),
        ))

    with open(path, "w", encoding="utf-8-sig", newline="") as file_obj:
        writer = csv.writer(
            file_obj, delimiter=";", quotechar='"', doublequote=True,
            lineterminator="\r\n",
        )
        writer.writerow(CSV_HEADERS)
        writer.writerows(data_rows)
        writer.writerow(())
        writer.writerow(("RESUMEN",))
        writer.writerow(("Categoría", "Tipo", "Unidad", "Total"))
        writer.writerows(summary_rows)
    return len(data_rows)
