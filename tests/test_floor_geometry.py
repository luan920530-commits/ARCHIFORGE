import math
import unittest

from af_floor_geometry import (
    clip_polygon_to_outline,
    fragments_cover_polygon,
    normalize_outline,
    polygon_area,
    polygon_boundary_edges,
    triangulate_polygon,
)


class FloorGeometryTests(unittest.TestCase):
    def test_normalize_outline_removes_closing_duplicate_and_orients_ccw(self):
        outline = normalize_outline(
            [(0, 0), (0, 3), (4, 3), (4, 0), (0, 0)])

        self.assertEqual(outline, [(4.0, 0.0), (4.0, 3.0),
                                   (0.0, 3.0), (0.0, 0.0)])
        self.assertGreater(polygon_area(outline), 0.0)

    def test_ear_clipping_preserves_area_of_concave_outline(self):
        outline = normalize_outline(
            [(0, 0), (4, 0), (4, 4), (2, 2), (0, 4)])

        triangles = triangulate_polygon(outline)

        self.assertEqual(len(triangles), len(outline) - 2)
        self.assertAlmostEqual(
            sum(abs(polygon_area(triangle)) for triangle in triangles),
            abs(polygon_area(outline)),
        )

    def test_rectangle_clipping_respects_a_concave_notch(self):
        outline = normalize_outline(
            [(0, 0), (4, 0), (4, 4), (2, 2), (0, 4)])
        triangles = triangulate_polygon(outline)
        rectangle = [(1, 1), (3, 1), (3, 3), (1, 3)]

        fragments = clip_polygon_to_outline(rectangle, outline, triangles)

        self.assertAlmostEqual(
            sum(abs(polygon_area(fragment)) for fragment in fragments), 3.0)
        self.assertFalse(fragments_cover_polygon(fragments, rectangle))
        boundary = polygon_boundary_edges(fragments)
        perimeter = sum(math.dist(start, end) for start, end in boundary)
        self.assertAlmostEqual(perimeter, 6.0 + 2.0 * math.sqrt(2.0))

    def test_rectangle_fully_inside_outline_is_reported_unchanged(self):
        outline = normalize_outline(
            [(0, 0), (4, 0), (4, 4), (2, 2), (0, 4)])
        triangles = triangulate_polygon(outline)
        rectangle = [(0.2, 0.2), (1.0, 0.2), (1.0, 1.0), (0.2, 1.0)]

        fragments = clip_polygon_to_outline(rectangle, outline, triangles)

        self.assertTrue(fragments_cover_polygon(fragments, rectangle))

    def test_invalid_outline_is_rejected_before_generation(self):
        with self.assertRaisesRegex(ValueError, "se cruza"):
            normalize_outline(
                [(0, 0), (4, 0), (2, 2), (4, 4), (0, 4), (2, -1)])


if __name__ == "__main__":
    unittest.main()
