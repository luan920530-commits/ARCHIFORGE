import math
import unittest

try:
    from blender_stub import load_addon_module
except ImportError:  # pragma: no cover
    from tests.blender_stub import load_addon_module

import af_annotation_geometry as geo
import af_units


def _length(a, b):
    return math.dist(a[:2], b[:2])


class DimensionLineTests(unittest.TestCase):
    def test_basic_dimension_along_x(self):
        result = geo.dimension_line((0, 0, 0), (3, 0, 0), offset=0.5)
        self.assertAlmostEqual(result["length"], 3.0)
        self.assertEqual(result["label"]["text"], "3.00 m")
        # dimension line, two extension lines, two ticks
        self.assertEqual(len(result["polylines"]), 5)
        main = result["polylines"][0]
        self.assertAlmostEqual(main[0][1], 0.5)      # offset to the left (+Y)
        self.assertAlmostEqual(main[1][1], 0.5)
        self.assertAlmostEqual(_length(main[0], main[1]), 3.0)
        self.assertAlmostEqual(result["label"]["rotation"], 0.0)
        self.assertGreater(result["label"]["position"][1], 0.5)

    def test_negative_offset_places_line_on_the_right_side(self):
        result = geo.dimension_line((0, 0, 0), (3, 0, 0), offset=-0.4)
        main = result["polylines"][0]
        self.assertAlmostEqual(main[0][1], -0.4)
        self.assertLess(result["label"]["position"][1], -0.4)

    def test_extension_lines_start_at_measured_points_and_overshoot(self):
        result = geo.dimension_line((1, 1, 0), (1, 4, 0), offset=0.5,
                                    extension=0.1)
        ext0, ext1 = result["polylines"][1], result["polylines"][2]
        self.assertEqual(tuple(ext0[0]), (1.0, 1.0, 0.0))
        self.assertEqual(tuple(ext1[0]), (1.0, 4.0, 0.0))
        # p0→p1 is +Y, left normal is −X: the line sits at x = 0.5 and the
        # extension overshoots to x = 0.4
        self.assertAlmostEqual(ext0[1][0], 0.4)
        self.assertAlmostEqual(ext1[1][0], 0.4)

    def test_ticks_are_centred_on_line_ends_with_requested_size(self):
        result = geo.dimension_line((0, 0, 0), (2, 0, 0), offset=0.3, tick=0.1)
        for tick, end in zip(result["polylines"][3:], result["polylines"][0]):
            self.assertAlmostEqual(_length(tick[0], tick[1]), 0.1)
            mid = ((tick[0][0] + tick[1][0]) / 2, (tick[0][1] + tick[1][1]) / 2)
            self.assertAlmostEqual(mid[0], end[0])
            self.assertAlmostEqual(mid[1], end[1])

    def test_text_is_never_upside_down(self):
        result = geo.dimension_line((3, 0, 0), (0, 0, 0), offset=0.5)
        self.assertAlmostEqual(result["label"]["rotation"], 0.0)
        diagonal = geo.dimension_line((0, 0, 0), (-1, -1, 0), offset=0.5)
        self.assertAlmostEqual(diagonal["label"]["rotation"], math.pi / 4)

    def test_imperial_label(self):
        result = geo.dimension_line((0, 0, 0), (3.048, 0, 0),
                                    unit_system=af_units.IMPERIAL)
        self.assertEqual(result["label"]["text"], "10' 0\"")

    def test_coincident_points_are_rejected(self):
        with self.assertRaises(ValueError):
            geo.dimension_line((1, 1, 0), (1, 1, 0))

    def test_footprint_dimensions_below_and_right(self):
        results = geo.footprint_dimensions((0, 0, 0), (4, 3, 0), offset=0.5)
        self.assertEqual([r["label"]["text"] for r in results],
                         ["4.00 m", "3.00 m"])
        width_line = results[0]["polylines"][0]
        depth_line = results[1]["polylines"][0]
        self.assertAlmostEqual(width_line[0][1], -0.5)   # below the box
        self.assertAlmostEqual(depth_line[0][0], 4.5)    # right of the box

    def test_footprint_skips_degenerate_axis(self):
        results = geo.footprint_dimensions((0, 0, 0), (4, 0, 0))
        self.assertEqual(len(results), 1)


class GridAxesTests(unittest.TestCase):
    def test_axis_letters(self):
        letters = geo.axis_letters(28)
        self.assertEqual(letters[:3], ["A", "B", "C"])
        self.assertEqual(letters[25], "Z")
        self.assertEqual(letters[26:], ["AA", "AB"])

    def test_regular_positions(self):
        self.assertEqual(geo.regular_positions(3, 5.0), [0.0, 5.0, 10.0])
        self.assertEqual(geo.regular_positions(0, 5.0), [0.0])

    def test_numbered_x_axes_and_lettered_y_axes(self):
        grid = geo.grid_axes([0, 5, 10], [0, 4], origin=(1, 1, 0),
                             extension=1.0, bubble_radius=0.3)
        names = [axis["name"] for axis in grid["axes"]]
        self.assertEqual(names, ["1", "2", "3", "A", "B"])
        axis_2 = grid["axes"][1]
        self.assertAlmostEqual(axis_2["line"][0][0], 6.0)       # x = 1 + 5
        self.assertAlmostEqual(axis_2["line"][0][1], 0.0)       # 1 + 0 − 1
        self.assertAlmostEqual(axis_2["line"][1][1], 6.0)       # 1 + 4 + 1
        self.assertAlmostEqual(axis_2["bubbles"][0][1], 6.3)    # beyond end
        axis_a = grid["axes"][3]
        self.assertAlmostEqual(axis_a["line"][0][0], 0.0)       # 1 + 0 − 1
        self.assertAlmostEqual(axis_a["line"][1][0], 12.0)      # 1 + 10 + 1
        self.assertAlmostEqual(axis_a["bubbles"][0][0], -0.3)   # left bubble

    def test_both_ends_adds_second_bubble(self):
        grid = geo.grid_axes([0, 3], [0, 3], both_ends=True)
        self.assertTrue(all(len(a["bubbles"]) == 2 for a in grid["axes"]))

    def test_unsorted_positions_are_sorted_and_empty_rejected(self):
        grid = geo.grid_axes([6, 0, 3], [0])
        self.assertEqual([a["line"][0][0] for a in grid["axes"][:3]],
                         [0.0, 3.0, 6.0])
        with self.assertRaises(ValueError):
            geo.grid_axes([], [0])

    def test_circle_points_lie_on_radius(self):
        ring = geo.circle_points((2, 3, 0), 0.5, 16)
        self.assertEqual(len(ring), 16)
        for point in ring:
            self.assertAlmostEqual(math.dist(point[:2], (2, 3)), 0.5)


class NorthArrowTests(unittest.TestCase):
    def test_arrow_points_to_plus_y_by_default(self):
        result = geo.north_arrow((0, 0, 0), size=2.0)
        arrow, ring = result["polylines"]
        tip = arrow[0]
        self.assertAlmostEqual(tip[0], 0.0)
        self.assertAlmostEqual(tip[1], 1.0)                    # size / 2
        self.assertEqual(arrow[0], arrow[-1])                  # closed
        self.assertEqual(ring[0], ring[-1])
        self.assertEqual(result["label"]["text"], "N")
        self.assertGreater(result["label"]["position"][1], tip[1])

    def test_rotation_turns_the_tip(self):
        result = geo.north_arrow((0, 0, 0), size=2.0, angle=math.pi / 2)
        tip = result["polylines"][0][0]
        self.assertAlmostEqual(tip[0], -1.0)
        self.assertAlmostEqual(tip[1], 0.0, places=6)


class FormattingTests(unittest.TestCase):
    def test_format_dimension(self):
        self.assertEqual(geo.format_dimension(2.5), "2.50 m")
        self.assertEqual(geo.format_dimension(2.5, decimals=1), "2.5 m")
        self.assertEqual(geo.format_dimension(0.3048, af_units.IMPERIAL),
                         "1' 0\"")

    def test_readable_angle(self):
        self.assertAlmostEqual(geo.readable_angle(math.pi), 0.0)
        self.assertAlmostEqual(geo.readable_angle(-3 * math.pi / 4),
                               math.pi / 4)
        self.assertAlmostEqual(geo.readable_angle(math.pi / 3), math.pi / 3)


class AnnotationModuleTests(unittest.TestCase):
    def test_module_registers_expected_operators(self):
        module = load_addon_module("af_annotation")
        idnames = {cls.bl_idname for cls in module.classes}
        self.assertTrue({"archiforge.dimension_selected",
                         "archiforge.dimension_draw", "archiforge.grid_axes",
                         "archiforge.north_arrow",
                         "archiforge.annotations_visibility",
                         "ARCHIFORGE_PT_annotations"} <= idnames)
        self.assertEqual(module.ANNOTATION_PROP, "af_annotation")

    def test_sets_module_registers_expected_operators(self):
        module = load_addon_module("af_sets")
        idnames = {cls.bl_idname for cls in module.classes}
        self.assertTrue({"archiforge.set_bathroom",
                         "archiforge.set_apartment"} <= idnames)
        self.assertTrue(callable(module.build_bathroom))
        self.assertTrue(callable(module.build_apartment))

    def test_wall_and_floor_expose_shared_creation_helpers(self):
        af_wall = load_addon_module("af_wall")
        af_floor = load_addon_module("af_floor")
        self.assertTrue(callable(af_wall.create_wall_from_points))
        self.assertTrue(callable(af_floor.create_floor_from_outline))


if __name__ == "__main__":
    unittest.main()
