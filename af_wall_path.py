# -*- coding: utf-8 -*-
"""Pure geometry helpers for ArchiForge's parametric wall paths.

This module deliberately has no Blender dependency so path validation and
segment-angle calculations can be covered by the standard-library tests.
"""

import math


def _xy(point):
    """Return a point's XY coordinates from a tuple or vector-like object."""
    if hasattr(point, "x") and hasattr(point, "y"):
        return float(point.x), float(point.y)
    return float(point[0]), float(point[1])


def normalize_angle(angle):
    """Normalize an angle to Blender's signed [-pi, pi] range."""
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


def signed_area(points):
    """Return the signed XY area of a polygon, or zero for fewer than 3 points."""
    coords = [_xy(point) for point in points]
    if len(coords) < 3:
        return 0.0
    return 0.5 * sum(
        coords[i][0] * coords[(i + 1) % len(coords)][1]
        - coords[(i + 1) % len(coords)][0] * coords[i][1]
        for i in range(len(coords))
    )


def offset_polyline(points, offset, closed=False):
    """Offset a 2D polyline, using miter joins and cyclic joins for rooms."""
    coords = [_xy(point) for point in points]
    count = len(coords)
    if count < 2:
        return coords

    result = []
    for index, point in enumerate(coords):
        if closed:
            previous = coords[(index - 1) % count]
            following = coords[(index + 1) % count]
            dx1 = point[0] - previous[0]
            dy1 = point[1] - previous[1]
            dx2 = following[0] - point[0]
            dy2 = following[1] - point[1]
            length1 = math.hypot(dx1, dy1)
            length2 = math.hypot(dx2, dy2)
            d1 = (dx1 / length1, dy1 / length1) if length1 else (0.0, 0.0)
            d2 = (dx2 / length2, dy2 / length2) if length2 else (0.0, 0.0)
            n1 = (-d1[1], d1[0])
            n2 = (-d2[1], d2[0])
        elif index == 0:
            dx = coords[1][0] - point[0]
            dy = coords[1][1] - point[1]
            length = math.hypot(dx, dy)
            direction = (dx / length, dy / length) if length else (0.0, 0.0)
            n1 = n2 = (-direction[1], direction[0])
        elif index == count - 1:
            dx = point[0] - coords[index - 1][0]
            dy = point[1] - coords[index - 1][1]
            length = math.hypot(dx, dy)
            direction = (dx / length, dy / length) if length else (0.0, 0.0)
            n1 = n2 = (-direction[1], direction[0])
        else:
            previous = coords[index - 1]
            following = coords[index + 1]
            dx1 = point[0] - previous[0]
            dy1 = point[1] - previous[1]
            dx2 = following[0] - point[0]
            dy2 = following[1] - point[1]
            length1 = math.hypot(dx1, dy1)
            length2 = math.hypot(dx2, dy2)
            d1 = (dx1 / length1, dy1 / length1) if length1 else (0.0, 0.0)
            d2 = (dx2 / length2, dy2 / length2) if length2 else (0.0, 0.0)
            n1 = (-d1[1], d1[0])
            n2 = (-d2[1], d2[0])

        bisector = (n1[0] + n2[0], n1[1] + n2[1])
        bisector_length = math.hypot(*bisector)
        if bisector_length < 1e-6:
            normal = n1
        else:
            normal = (bisector[0] / bisector_length,
                      bisector[1] / bisector_length)
            projection = normal[0] * n1[0] + normal[1] * n1[1]
            if abs(projection) > 1e-3:
                normal = (normal[0] / projection, normal[1] / projection)
            else:
                normal = n1

        result.append((
            point[0] + normal[0] * offset,
            point[1] + normal[1] * offset,
        ))

    return result


def _orientation(a, b, c):
    return ((b[0] - a[0]) * (c[1] - a[1])
            - (b[1] - a[1]) * (c[0] - a[0]))


def _on_segment(a, b, point, epsilon):
    return (
        min(a[0], b[0]) - epsilon <= point[0] <= max(a[0], b[0]) + epsilon
        and min(a[1], b[1]) - epsilon <= point[1] <= max(a[1], b[1]) + epsilon
    )


def _segments_intersect(a, b, c, d, epsilon=1e-9):
    """Return whether two closed 2D segments intersect, including touching."""
    o1 = _orientation(a, b, c)
    o2 = _orientation(a, b, d)
    o3 = _orientation(c, d, a)
    o4 = _orientation(c, d, b)

    if ((o1 > epsilon and o2 < -epsilon)
            or (o1 < -epsilon and o2 > epsilon)):
        if ((o3 > epsilon and o4 < -epsilon)
                or (o3 < -epsilon and o4 > epsilon)):
            return True

    return (
        (abs(o1) <= epsilon and _on_segment(a, b, c, epsilon))
        or (abs(o2) <= epsilon and _on_segment(a, b, d, epsilon))
        or (abs(o3) <= epsilon and _on_segment(c, d, a, epsilon))
        or (abs(o4) <= epsilon and _on_segment(c, d, b, epsilon))
    )


def _validate_simple_polygon(coords, min_area):
    """Reject degenerate and self-intersecting closed wall paths."""
    if len(coords) < 3:
        raise ValueError("Se necesitan al menos 3 vértices para cerrar un recinto")

    if abs(signed_area(coords)) < min_area:
        raise ValueError("El contorno tiene área nula; revisa los vértices")

    count = len(coords)
    for i in range(count):
        a, b = coords[i], coords[(i + 1) % count]
        for j in range(i + 1, count):
            # Consecutive sides share an intended endpoint; the first and last
            # sides also share one. All other intersections make the loop invalid.
            if j == i + 1 or (i == 0 and j == count - 1):
                continue
            c, d = coords[j], coords[(j + 1) % count]
            if _segments_intersect(a, b, c, d):
                raise ValueError(
                    "El contorno se cruza o repite un vértice; ajusta los puntos"
                )


def build_wall_segments(
    points,
    closed=False,
    min_segment_length=0.01,
    max_segments=64,
    min_area=1e-4,
):
    """Convert XY vertices to ``(length, relative_angle)`` wall segments.

    The first angle is measured from +X. Subsequent angles are relative to the
    previous segment. For a closed path the final return segment is included,
    and the polygon is checked for nonzero area and self-intersections.
    """
    coords = [_xy(point) for point in points]
    if closed and len(coords) > 1:
        first, last = coords[0], coords[-1]
        if math.hypot(last[0] - first[0], last[1] - first[1]) < min_segment_length:
            coords.pop()

    minimum_vertices = 3 if closed else 2
    if len(coords) < minimum_vertices:
        if closed:
            raise ValueError("Se necesitan al menos 3 vértices para cerrar un recinto")
        raise ValueError("Se necesitan al menos 2 vértices")

    edge_count = len(coords) if closed else len(coords) - 1
    if edge_count > max_segments:
        raise ValueError(f"El muro admite un máximo de {max_segments} segmentos")

    if closed:
        _validate_simple_polygon(coords, min_area)

    edges = []
    previous_angle = 0.0
    for index in range(edge_count):
        start = coords[index]
        end = coords[(index + 1) % len(coords)]
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = math.hypot(dx, dy)
        if length < min_segment_length:
            raise ValueError("Hay dos vértices consecutivos demasiado cercanos")
        absolute_angle = math.atan2(dy, dx)
        relative_angle = normalize_angle(absolute_angle - previous_angle)
        edges.append((length, relative_angle))
        previous_angle = absolute_angle

    return edges
