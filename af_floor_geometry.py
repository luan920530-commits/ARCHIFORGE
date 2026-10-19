# -*- coding: utf-8 -*-
"""Pure 2D polygon helpers used by the custom floor-outline generator.

This module has no Blender dependency so its clipping and triangulation can be
regression-tested with the standard library.
"""

import math

try:
    from .af_wall_path import build_wall_segments, signed_area
except ImportError:
    from af_wall_path import build_wall_segments, signed_area

_EPSILON = 1e-9
_POINT_DIGITS = 9


def _xy(point):
    if hasattr(point, "x") and hasattr(point, "y"):
        return float(point.x), float(point.y)
    return float(point[0]), float(point[1])


def _cross(a, b, c):
    return ((b[0] - a[0]) * (c[1] - a[1])
            - (b[1] - a[1]) * (c[0] - a[0]))


def _point_key(point):
    return (round(float(point[0]), _POINT_DIGITS),
            round(float(point[1]), _POINT_DIGITS))


def polygon_area(points):
    """Return a polygon's signed area (positive for counter-clockwise)."""
    return signed_area(points)


def normalize_outline(points, min_segment_length=0.01,
                      max_vertices=64, min_area=1e-4):
    """Validate a simple outline, remove its repeated closing point, and CCW it."""
    coords = [_xy(point) for point in points]
    if len(coords) > 1:
        if math.dist(coords[0], coords[-1]) < min_segment_length:
            coords.pop()

    build_wall_segments(
        coords,
        closed=True,
        min_segment_length=min_segment_length,
        max_segments=max_vertices,
        min_area=min_area,
    )

    if signed_area(coords) < 0.0:
        coords.reverse()
    return coords


def _remove_collinear(points, epsilon=1e-10):
    """Remove redundant points on straight, forward-running polygon edges."""
    result = list(points)
    changed = True
    while changed and len(result) > 3:
        changed = False
        for index in range(len(result)):
            previous = result[(index - 1) % len(result)]
            current = result[index]
            following = result[(index + 1) % len(result)]
            incoming = (current[0] - previous[0], current[1] - previous[1])
            outgoing = (following[0] - current[0],
                        following[1] - current[1])
            scale = max(math.hypot(*incoming) * math.hypot(*outgoing), 1.0)
            if (abs(incoming[0] * outgoing[1]
                    - incoming[1] * outgoing[0]) <= epsilon * scale
                    and incoming[0] * outgoing[0]
                    + incoming[1] * outgoing[1] >= -epsilon):
                result.pop(index)
                changed = True
                break
    return result


def triangulate_polygon(points):
    """Ear-clip a simple polygon into counter-clockwise triangles."""
    polygon = [_xy(point) for point in points]
    if len(polygon) < 3:
        raise ValueError("Se necesitan al menos 3 vértices para triangular")
    if signed_area(polygon) < 0.0:
        polygon.reverse()
    polygon = _remove_collinear(polygon)
    if len(polygon) < 3 or abs(signed_area(polygon)) <= _EPSILON:
        raise ValueError("El contorno no tiene área suficiente")

    remaining = list(range(len(polygon)))
    triangles = []
    while len(remaining) > 3:
        ear_found = False
        for position, current_index in enumerate(remaining):
            previous_index = remaining[position - 1]
            next_index = remaining[(position + 1) % len(remaining)]
            a = polygon[previous_index]
            b = polygon[current_index]
            c = polygon[next_index]
            if _cross(a, b, c) <= _EPSILON:
                continue

            contains_vertex = False
            for test_index in remaining:
                if test_index in (previous_index, current_index, next_index):
                    continue
                point = polygon[test_index]
                # A reflex vertex on the proposed diagonal must also block
                # the ear; otherwise the triangulation can cross a notch.
                if (_cross(a, b, point) >= -_EPSILON
                        and _cross(b, c, point) >= -_EPSILON
                        and _cross(c, a, point) >= -_EPSILON):
                    contains_vertex = True
                    break
            if contains_vertex:
                continue

            triangles.append((a, b, c))
            remaining.pop(position)
            ear_found = True
            break

        if not ear_found:
            raise ValueError("No se pudo triangular el contorno del piso")

    last_triangle = tuple(polygon[index] for index in remaining)
    if signed_area(last_triangle) < 0.0:
        last_triangle = tuple(reversed(last_triangle))
    triangles.append(last_triangle)
    return triangles


def _line_intersection(start, end, clip_start, clip_end):
    direction = (end[0] - start[0], end[1] - start[1])
    clip_direction = (clip_end[0] - clip_start[0],
                      clip_end[1] - clip_start[1])
    denominator = (direction[0] * clip_direction[1]
                   - direction[1] * clip_direction[0])
    if abs(denominator) <= _EPSILON:
        return end
    delta = (clip_start[0] - start[0], clip_start[1] - start[1])
    t = (delta[0] * clip_direction[1]
         - delta[1] * clip_direction[0]) / denominator
    return (start[0] + t * direction[0],
            start[1] + t * direction[1])


def clip_convex_polygon(subject, clip_polygon):
    """Intersect a convex subject polygon with a convex clip polygon."""
    output = [_xy(point) for point in subject]
    clip = [_xy(point) for point in clip_polygon]
    if len(output) < 3 or len(clip) < 3:
        return []
    if signed_area(output) < 0.0:
        output.reverse()
    if signed_area(clip) < 0.0:
        clip.reverse()

    for edge_index, clip_start in enumerate(clip):
        clip_end = clip[(edge_index + 1) % len(clip)]
        input_points = output
        output = []
        if not input_points:
            break
        start = input_points[-1]
        start_inside = _cross(clip_start, clip_end, start) >= -_EPSILON

        for end in input_points:
            end_inside = _cross(clip_start, clip_end, end) >= -_EPSILON
            if end_inside:
                if not start_inside:
                    output.append(_line_intersection(
                        start, end, clip_start, clip_end))
                output.append(end)
            elif start_inside:
                output.append(_line_intersection(
                    start, end, clip_start, clip_end))
            start = end
            start_inside = end_inside

        compact = []
        for point in output:
            if not compact or math.dist(point, compact[-1]) > 1e-8:
                compact.append(point)
        if len(compact) > 1 and math.dist(compact[0], compact[-1]) <= 1e-8:
            compact.pop()
        output = compact

    if len(output) < 3 or abs(signed_area(output)) <= 1e-10:
        return []
    if signed_area(output) < 0.0:
        output.reverse()
    return output


def clip_polygon_to_outline(subject, outline, triangles=None):
    """Return convex fragments of a convex subject intersected with an outline."""
    clip_triangles = triangles or triangulate_polygon(outline)
    fragments = []
    for triangle in clip_triangles:
        fragment = clip_convex_polygon(subject, triangle)
        if fragment:
            fragments.append(fragment)
    return fragments


def fragments_cover_polygon(fragments, polygon, tolerance=1e-7):
    """Whether fragments cover all of a polygon, comparing their total area."""
    target_area = abs(signed_area(polygon))
    covered_area = sum(abs(signed_area(fragment)) for fragment in fragments)
    return target_area > _EPSILON and covered_area >= target_area - tolerance


def _point_on_segment(point, start, end, epsilon=1e-7):
    dx, dy = end[0] - start[0], end[1] - start[1]
    px, py = point[0] - start[0], point[1] - start[1]
    length_sq = dx * dx + dy * dy
    if length_sq <= epsilon * epsilon:
        return math.dist(point, start) <= epsilon
    cross = dx * py - dy * px
    if abs(cross) > epsilon * max(math.sqrt(length_sq), 1.0):
        return False
    projection = px * dx + py * dy
    return -epsilon <= projection <= length_sq + epsilon


def split_polygon_edges(fragments):
    """Insert all shared fragment vertices along collinear fragment edges."""
    all_points = {}
    for polygon in fragments:
        for point in polygon:
            all_points.setdefault(_point_key(point), _point_key(point))
    candidates = list(all_points.values())

    split_fragments = []
    for polygon in fragments:
        expanded = []
        for index, start in enumerate(polygon):
            end = polygon[(index + 1) % len(polygon)]
            dx, dy = end[0] - start[0], end[1] - start[1]
            length_sq = dx * dx + dy * dy
            edge_points = []
            for point in candidates:
                if not _point_on_segment(point, start, end):
                    continue
                if length_sq <= _EPSILON:
                    t = 0.0
                else:
                    t = ((point[0] - start[0]) * dx
                         + (point[1] - start[1]) * dy) / length_sq
                edge_points.append((t, point))
            edge_points.sort(key=lambda item: item[0])
            for _, point in edge_points:
                point = _point_key(point)
                if not expanded or point != expanded[-1]:
                    expanded.append(point)
        if len(expanded) > 1 and expanded[0] == expanded[-1]:
            expanded.pop()
        if len(expanded) >= 3:
            split_fragments.append(expanded)
    return split_fragments


def polygon_boundary_edges(fragments):
    """Return directed boundary edges after canceling shared fragment edges."""
    split_fragments = split_polygon_edges(fragments)
    edge_counts = {}
    for polygon in split_fragments:
        for index, start in enumerate(polygon):
            end = polygon[(index + 1) % len(polygon)]
            start_key = _point_key(start)
            end_key = _point_key(end)
            if start_key == end_key:
                continue
            if start_key < end_key:
                key = (start_key, end_key)
                direction = 1
            else:
                key = (end_key, start_key)
                direction = -1
            edge_counts[key] = edge_counts.get(key, 0) + direction

    boundary = []
    for (start, end), direction in edge_counts.items():
        if direction > 0:
            boundary.append((start, end))
        elif direction < 0:
            boundary.append((end, start))
    return boundary
