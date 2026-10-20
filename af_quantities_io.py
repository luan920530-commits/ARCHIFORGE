# -*- coding: utf-8 -*-
"""Pure helpers for ArchiForge's quantity takeoff and CSV export.

This module deliberately has no Blender dependency so the calculations and
CSV safety rules can be regression-tested with the standard Python runtime.
"""

import csv
import math

try:
    from . import af_units
except ImportError:  # pragma: no cover - imported outside the package
    import af_units


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
    """Sum enabled wall segments, including an implicit closing edge."""
    try:
        parts = list(getattr(props, "parts", ()))
    except (AttributeError, ReferenceError, TypeError):
        parts = []
    length = _segments_length(parts)
    try:
        is_closed = bool(getattr(props, "closed", False))
    except (AttributeError, ReferenceError, TypeError):
        is_closed = False
    if not is_closed:
        return length

    # Older manually-closed walls may rely on the Closed toggle without a
    # stored final segment. Include that generated edge in the perimeter.
    x = y = angle = 0.0
    for part in parts:
        try:
            if not bool(getattr(part, "enabled", True)):
                continue
            angle += _property_number(part, "angle")
            segment_length = _property_number(part, "length")
            x += math.cos(angle) * segment_length
            y += math.sin(angle) * segment_length
        except (AttributeError, ReferenceError, TypeError):
            continue
    closing_length = math.hypot(x, y)
    if closing_length > 1e-5:
        length += closing_length
    return length


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


class _UnitFormatter:
    """Converts internal metres to the requested unit system."""

    def __init__(self, system):
        self.system = af_units.normalize(system)
        self.length_unit = af_units.length_unit(self.system)
        self.area_unit = af_units.area_unit(self.system)
        self.volume_unit = af_units.volume_unit(self.system)

    def length(self, meters):
        return af_units.convert_length(meters, self.system)

    def area(self, square_meters):
        return af_units.convert_area(square_meters, self.system)

    def volume(self, cubic_meters):
        return af_units.convert_volume(cubic_meters, self.system)

    def fmt(self, meters):
        """Formatted length in the target unit (number only)."""
        return format_number(self.length(meters))


def _dimensions(props, width="width", depth="depth", height="height",
                units=None):
    units = units or _UnitFormatter(af_units.METRIC)
    values = (
        _property_number(props, width),
        _property_number(props, depth),
        _property_number(props, height),
    )
    if not any(value > 0.0 for value in values):
        return "—"
    return "{}x{}x{} {}".format(*(units.fmt(value) for value in values),
                                units.length_unit)


def _append_unit_row(rows, category, props, obj_name, type_fields,
                     dimension_fields=("width", "depth", "height"),
                     units=None):
    item_type = _property_text(props, *type_fields, default=category)
    dimensions = _dimensions(props, *dimension_fields, units=units)
    rows.append((category, item_type, obj_name, 1, "und", dimensions))


def collect_quantities(objects, unit_system=af_units.METRIC):
    """Collect quantity rows from an iterable of scene objects.

    Each row is ``(category, type, object, quantity, unit, dimensions)``.
    Values are parametric estimates, not code-compliant material takeoffs.
    Objects are modelled in metres; ``unit_system`` (``'METRIC'`` or
    ``'IMPERIAL'``) converts lengths, areas and volumes and labels the
    units (``m``/``m2``/``m3`` or ``ft``/``ft2``/``ft3``).
    """
    rows = []
    u = _UnitFormatter(unit_system)
    for obj in objects:
        obj_name = _object_name(obj)

        props = _registered_props(obj, "archiforge_wall", "is_af_wall")
        if props is not None:
            length = _wall_length(props)
            height = _property_number(props, "height")
            thickness = _property_number(props, "width")
            if length > 0.0 and height > 0.0:
                item_type = _property_text(props, "wall_type", default="Muro")
                measures = "L={} H={} e={} {}".format(
                    u.fmt(length), u.fmt(height), u.fmt(thickness),
                    u.length_unit,
                )
                rows.append(("Muros", item_type, obj_name,
                             u.area(length * height), u.area_unit, measures))
                if thickness > 0.0:
                    rows.append(("Muros", item_type, obj_name,
                                 u.volume(length * height * thickness),
                                 u.volume_unit, measures))

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
            dimensions = "{}x{} e={} {} (área neta aprox.)".format(
                u.fmt(width), u.fmt(depth), u.fmt(thickness), u.length_unit,
            )
            if area > 0.0:
                rows.append(("Losas", item_type, obj_name,
                             u.area(area), u.area_unit, dimensions))
                if thickness > 0.0:
                    rows.append(("Losas", item_type, obj_name,
                                 u.volume(area * thickness), u.volume_unit,
                                 dimensions))

        props = _registered_props(obj, "archiforge_floor", "is_af_floor")
        if props is not None:
            width = _property_number(props, "width")
            depth = _property_number(props, "depth")
            floor_area = width * depth
            try:
                has_outline = bool(getattr(props, "outline_enabled", False))
                outline = getattr(props, "outline_vertices", ())
            except (AttributeError, ReferenceError, TypeError):
                has_outline = False
                outline = ()
            area_label = "área de planta"
            if has_outline:
                polygon_area = _polygon_area(outline)
                if polygon_area > 0.0:
                    floor_area = polygon_area
                    area_label = "área poligonal"
            if floor_area > 0.0:
                rows.append((
                    "Pisos", _property_text(props, "pattern", default="Piso"),
                    obj_name, u.area(floor_area), u.area_unit,
                    "{}x{} {} ({})".format(
                        u.fmt(width), u.fmt(depth), u.length_unit, area_label),
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
                    obj_name, u.length(length), u.length_unit,
                    "L={} H={} {}".format(
                        u.fmt(length),
                        u.fmt(_property_number(props, "height")),
                        u.length_unit,
                    ),
                ))

        props = _registered_props(obj, "af_roof", "is_af_roof")
        if props is not None:
            width = _property_number(props, "width")
            depth = _property_number(props, "depth")
            if width > 0.0 and depth > 0.0:
                rows.append((
                    "Techos", _property_text(props, "roof_type", default="Techo"),
                    obj_name, u.area(width * depth), u.area_unit + " proy.",
                    "{}x{} {} (proyección; no incluye pendiente)".format(
                        u.fmt(width), u.fmt(depth), u.length_unit),
                ))

        props = _registered_props(obj, "archiforge_truss", "is_af_truss")
        if props is not None:
            _append_unit_row(
                rows, "Cerchas", props, obj_name, ("truss_type",),
                ("span", "depth", "width"), units=u,
            )

        props = _registered_props(obj, "archiforge_struct", "is_af_struct")
        if props is not None:
            _append_unit_row(
                rows, "Estructura", props, obj_name, ("item_type",), units=u)

        props = _registered_props(obj, "archiforge_door", "is_af_door")
        if props is not None:
            _append_unit_row(rows, "Puertas", props, obj_name, ("door_type",),
                             units=u)

        props = _registered_props(obj, "archiforge_window", "is_af_window")
        if props is not None:
            _append_unit_row(
                rows, "Ventanas", props, obj_name, ("window_type",), units=u)

        props = _registered_props(obj, "archiforge_opening", "is_af_opening")
        if props is not None:
            _append_unit_row(
                rows, "Aberturas", props, obj_name, ("item_type",), units=u)

        # ``archiforge_stairs`` belonged to the duplicate module removed in
        # 1.12; af_stair migrates it on load, but objects exported before
        # that migration are still counted.
        for attr in ("archiforge_stair", "archiforge_stairs"):
            props = _registered_props(obj, attr, "is_af_stair")
            if props is None:
                continue
            item_type = _property_text(props, "item_type", default="Escalera")
            width = u.fmt(_property_number(props, "width"))
            rise = u.fmt(_property_number(props, "total_rise"))
            if item_type == "RAMP":
                slope = 100.0 * _property_number(props, "ramp_slope")
                measures = "A={} H={} pendiente={}%".format(
                    width, rise, format_number(slope))
            else:
                risers = int(max(0.0, _property_number(props, "n_risers")))
                measures = "A={} H={} contrahuellas={}".format(
                    width, rise, risers)
            rows.append(("Escaleras", item_type, obj_name, 1, "und", measures))

        room_asset = _registered_props(
            obj, "archiforge_room_asset", "is_af_room_asset")
        if room_asset is not None:
            room = _property_text(room_asset, "room", default="")
            category = {
                "BEDROOM": "Muebles dormitorio",
                "LIVING": "Muebles sala",
                "KITCHEN": "Cocina",
                "BATHROOM": "Baño",
                "YARD": "Exterior / jardín",
            }.get(room, "Muebles y decoración")
            item_type = _property_text(
                room_asset, "asset_type", default="Objeto / set")
            measures = "{}×{}×{} {}".format(
                u.fmt(_property_number(room_asset, "width")),
                u.fmt(_property_number(room_asset, "depth")),
                u.fmt(_property_number(room_asset, "height")),
                u.length_unit,
            )
            rows.append((category, item_type, obj_name, 1, "und", measures))

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
                    rows, category, props, obj_name, ("item_type",), units=u)

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
