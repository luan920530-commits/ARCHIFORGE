import math
import unittest

from af_wall_path import build_wall_segments, offset_polyline, signed_area


class WallPathTests(unittest.TestCase):
    def test_closed_rectangle_includes_return_edge_and_right_angle_turns(self):
        points = [(0, 0), (4, 0), (4, 3), (0, 3)]

        segments = build_wall_segments(points, closed=True)

        self.assertEqual([round(length, 6) for length, _ in segments], [4, 3, 4, 3])
        self.assertAlmostEqual(segments[0][1], 0.0)
        for _, angle in segments[1:]:
            self.assertAlmostEqual(angle, math.pi / 2)
        self.assertAlmostEqual(signed_area(points), 12.0)

    def test_closed_offset_uses_one_shared_miter_at_each_corner(self):
        points = [(0, 0), (4, 0), (4, 3), (0, 3)]

        offset_points = offset_polyline(points, 0.1, closed=True)

        expected = [(0.1, 0.1), (3.9, 0.1), (3.9, 2.9), (0.1, 2.9)]
        for actual, target in zip(offset_points, expected):
            self.assertAlmostEqual(actual[0], target[0])
            self.assertAlmostEqual(actual[1], target[1])

    def test_open_path_does_not_add_a_return_edge(self):
        points = [(1, 2), (4, 2), (4, 6)]

        segments = build_wall_segments(points)

        self.assertEqual(len(segments), 2)
        self.assertEqual([length for length, _ in segments], [3.0, 4.0])
        self.assertAlmostEqual(segments[0][1], 0.0)
        self.assertAlmostEqual(segments[1][1], math.pi / 2)

    def test_closed_path_may_repeat_its_first_point_once(self):
        points = [(0, 0), (2, 0), (2, 2), (0, 2), (0, 0)]

        segments = build_wall_segments(points, closed=True)

        self.assertEqual(len(segments), 4)
        self.assertEqual([length for length, _ in segments], [2.0] * 4)

    def test_rejects_zero_area_or_self_intersecting_room(self):
        with self.assertRaisesRegex(ValueError, "área nula"):
            build_wall_segments([(0, 0), (2, 2), (0, 2), (2, 0)], closed=True)

        with self.assertRaisesRegex(ValueError, "se cruza"):
            build_wall_segments(
                [(0, 0), (4, 0), (2, 2), (4, 4), (0, 4), (2, -1)],
                closed=True,
            )

    def test_rejects_short_segments_and_too_many_edges(self):
        with self.assertRaisesRegex(ValueError, "demasiado cercanos"):
            build_wall_segments([(0, 0), (0.001, 0)])

        points = [(float(index), 0.0) for index in range(66)]
        with self.assertRaisesRegex(ValueError, "máximo"):
            build_wall_segments(points, max_segments=64)


if __name__ == "__main__":
    unittest.main()
