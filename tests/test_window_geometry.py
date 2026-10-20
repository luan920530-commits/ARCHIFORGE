import ast
import math
import unittest
from pathlib import Path
from types import SimpleNamespace

from af_window_geometry import (
    OPENABLE_WINDOW_TYPES,
    distance_to_axis,
    hinge_knuckle_length,
    hinge_positions,
    leaf_hinge_side,
    rotate_point,
    sash_hinge,
    window_type_can_open,
)
try:
    from blender_stub import bounds, face_vertices, load_addon_module
except ImportError:  # invoked as ``python -m unittest tests.<module>``
    from tests.blender_stub import bounds, face_vertices, load_addon_module


ROOT = Path(__file__).resolve().parents[1]

# Closed sash used by the pure tests: 1.2 m wide, 1.2 m high, sill at 0.9 m,
# sash depth between y=0.02 (exterior face) and y=0.06 (interior face).
X0, X1, Z0, Z1 = 0.0, 1.2, 0.9, 2.1
Y_OUT, Y_IN = 0.02, 0.06
ANGLE = math.radians(60)

MAT_SASH, MAT_GLASS, MAT_HINGE = 1, 2, 6


def _window_props(**overrides):
    base = dict(
        window_type='CASEMENT', width=1.2, height=1.2, sill_height=0.9,
        frame_width=0.07, frame_depth=0.12, frame_offset=0.0,
        h_panels=1, v_panels=1, mullion_width=0.05,
        sash_style='DIVIDED', sash_width=0.04, sash_depth=0.04,
        grille_rows=2, grille_cols=2, grille_width=0.015,
        glass_thickness=0.006, open_angle=0.0,
        hinge_side='LEFT', swing_direction='OUT', hinge_enable=True,
        hinge_radius=0.006, hinge_length=0.06,
        arch_height=0.3, arch_segments=12,
        outer_sill_enable=False, outer_sill_type='FLAT',
        outer_sill_width=0.15, outer_sill_height=0.05,
        inner_sill_enable=False, inner_sill_width=0.2, inner_sill_height=0.03,
        shutter_enable=False, shutter_open=True, shutter_depth=0.03,
        bars_enable=False, bars_count=4, bars_radius=0.012, bars_offset=0.1,
        mat_frame=0, mat_sash=MAT_SASH, mat_glass=MAT_GLASS, mat_outer_sill=3,
        mat_inner_sill=4, mat_shutter=5, mat_bars=6, mat_hinge=MAT_HINGE,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _generate(**overrides):
    af_window = load_addon_module("af_window")
    return af_window.AF_WindowGenerator(_window_props(**overrides)).generate()


def _clusters(verts, axis_index, digits=2):
    groups = {}
    for vert in verts:
        key = round(vert.co[axis_index], digits)
        groups.setdefault(key, []).append(vert)
    return groups


class SashHingeKinematicsTests(unittest.TestCase):
    def test_only_hinged_types_can_open(self):
        self.assertEqual(OPENABLE_WINDOW_TYPES, ('CASEMENT', 'AWNING'))
        for window_type in ('FIXED', 'SLIDING', 'DOUBLE_HUNG', 'ARCH'):
            self.assertFalse(window_type_can_open(window_type), window_type)
            self.assertIsNone(sash_hinge(
                window_type, X0, X1, Z0, Z1, Y_OUT, Y_IN, ANGLE))
        for window_type in OPENABLE_WINDOW_TYPES:
            self.assertTrue(window_type_can_open(window_type))

    def test_casement_swings_outward_about_the_exterior_hinge_edge(self):
        hinge = sash_hinge('CASEMENT', X0, X1, Z0, Z1, Y_OUT, Y_IN, ANGLE,
                           hinge_side='LEFT', swing='OUT')

        self.assertEqual(hinge.axis, 'Z')
        self.assertEqual(hinge.pivot, (X0, Y_OUT, Z0))
        # Points on the hinge axis stay put.
        self.assertEqual(rotate_point((X0, Y_OUT, 1.5), hinge),
                         (X0, Y_OUT, 1.5))
        # The free edge moves to the exterior (-Y) and keeps its length.
        free_x, free_y, _ = rotate_point((X1, Y_OUT, Z0), hinge)
        self.assertLess(free_y, Y_OUT - 0.5)
        self.assertAlmostEqual(math.hypot(free_x - X0, free_y - Y_OUT),
                               X1 - X0)
        # The interior corner of the hinge stile sweeps into the daylight
        # opening, never into the jamb.
        stile_x, _, _ = rotate_point((X0, Y_IN, Z0), hinge)
        self.assertGreaterEqual(stile_x, X0)

    def test_right_hinge_and_inward_swing_are_mirrored(self):
        hinge = sash_hinge('CASEMENT', X0, X1, Z0, Z1, Y_OUT, Y_IN, ANGLE,
                           hinge_side='RIGHT', swing='IN')

        self.assertEqual(hinge.pivot, (X1, Y_IN, Z0))
        free_x, free_y, _ = rotate_point((X0, Y_IN, Z0), hinge)
        self.assertGreater(free_y, Y_IN + 0.5)
        self.assertLessEqual(free_x, X1)
        stile_x, _, _ = rotate_point((X1, Y_OUT, Z0), hinge)
        self.assertLessEqual(stile_x, X1 + 1e-12)

    def test_adjacent_casement_leaves_alternate_hinge_sides(self):
        self.assertEqual([leaf_hinge_side('LEFT', c) for c in range(4)],
                         ['LEFT', 'RIGHT', 'LEFT', 'RIGHT'])
        self.assertEqual([leaf_hinge_side('RIGHT', c) for c in range(3)],
                         ['RIGHT', 'LEFT', 'RIGHT'])

    def test_awning_is_top_hinged_and_projects_outward(self):
        hinge = sash_hinge('AWNING', X0, X1, Z0, Z1, Y_OUT, Y_IN,
                           math.radians(45))

        self.assertEqual(hinge.axis, 'X')
        self.assertEqual(hinge.pivot, (X0, Y_OUT, Z1))
        _, bottom_y, bottom_z = rotate_point((0.5, Y_OUT, Z0), hinge)
        self.assertLess(bottom_y, Y_OUT)
        self.assertGreater(bottom_z, Z0)
        # Nothing may rise above the hinge line into the head / mullion.
        for corner in ((X0, Y_IN, Z1), (X1, Y_IN, Z0), (X0, Y_OUT, Z0)):
            self.assertLessEqual(rotate_point(corner, hinge)[2], Z1 + 1e-12)

    def test_glass_and_grille_points_move_rigidly_with_the_sash(self):
        hinge = sash_hinge('CASEMENT', X0, X1, Z0, Z1, Y_OUT, Y_IN, ANGLE)
        sash_corner = (X1, Y_OUT, Z1)
        glass_corner = (X1 - 0.04, (Y_OUT + Y_IN) / 2, Z1 - 0.04)
        grille_bar = ((X0 + X1) / 2, (Y_OUT + Y_IN) / 2 + 0.005, 1.5)

        before = [math.dist(sash_corner, glass_corner),
                  math.dist(sash_corner, grille_bar),
                  math.dist(glass_corner, grille_bar)]
        moved = [rotate_point(p, hinge)
                 for p in (sash_corner, glass_corner, grille_bar)]
        after = [math.dist(moved[0], moved[1]), math.dist(moved[0], moved[2]),
                 math.dist(moved[1], moved[2])]

        for expected, actual in zip(before, after):
            self.assertAlmostEqual(expected, actual, places=9)

    def test_hinge_knuckles_lie_on_the_rotation_axis(self):
        for window_type, kwargs in (('CASEMENT', {'hinge_side': 'RIGHT'}),
                                    ('AWNING', {})):
            hinge = sash_hinge(window_type, X0, X1, Z0, Z1, Y_OUT, Y_IN,
                               ANGLE, **kwargs)
            centres = hinge_positions(hinge, X0, X1, Z0, Z1)
            self.assertEqual(len(centres), 2)
            for centre in centres:
                self.assertAlmostEqual(distance_to_axis(centre, hinge), 0.0)
                # Axis points are invariant under the leaf rotation.
                for a, b in zip(rotate_point(centre, hinge), centre):
                    self.assertAlmostEqual(a, b)
        self.assertEqual(hinge_positions(None, X0, X1, Z0, Z1), [])

    def test_knuckle_length_is_clamped_to_the_leaf(self):
        hinge = sash_hinge('CASEMENT', X0, X1, Z0, 1.0, Y_OUT, Y_IN, 0.0)
        self.assertAlmostEqual(
            hinge_knuckle_length(hinge, X0, X1, Z0, 1.0, 0.06), 0.04)
        self.assertAlmostEqual(
            hinge_knuckle_length(hinge, X0, X1, Z0, Z1, 0.06), 0.06)


class WindowGeneratorHeadlessTests(unittest.TestCase):
    """Run the real bmesh builder against the stub and inspect the mesh."""

    def test_closed_glass_sits_inside_the_sash_depth(self):
        bm = _generate()
        (_, (glass_y0, glass_y1), _) = bounds(face_vertices(bm, MAT_GLASS))
        (_, (sash_y0, sash_y1), _) = bounds(face_vertices(bm, MAT_SASH))
        self.assertGreater(glass_y0, sash_y0)
        self.assertLess(glass_y1, sash_y1)

    def test_open_casement_carries_glass_and_grille_with_the_sash(self):
        bm = _generate(open_angle=ANGLE)
        sash = bounds(face_vertices(bm, MAT_SASH))
        glass = bounds(face_vertices(bm, MAT_GLASS))

        # Free edge swings to the exterior, hinge stile stays out of the jamb.
        self.assertLess(sash[1][0], -0.5)
        self.assertGreaterEqual(sash[0][0], -1e-9)
        # Glazing (and the grille bars sharing its material) stays enclosed
        # by the rotated sash instead of remaining in the closed plane.
        for axis in range(3):
            self.assertGreaterEqual(glass[axis][0], sash[axis][0] - 1e-9)
            self.assertLessEqual(glass[axis][1], sash[axis][1] + 1e-9)
        self.assertLess(glass[1][1], 0.0)

    def test_generated_hinges_are_centred_on_the_axis_and_not_rotated(self):
        bm = _generate(open_angle=ANGLE)
        hinge = sash_hinge('CASEMENT', X0, X1, Z0, Z1, Y_OUT, Y_IN, ANGLE)
        knuckles = _clusters(face_vertices(bm, MAT_HINGE), axis_index=2)
        self.assertEqual(len(knuckles), 4)  # two rings per knuckle
        for z, verts in knuckles.items():
            cx = sum(v.co.x for v in verts) / len(verts)
            cy = sum(v.co.y for v in verts) / len(verts)
            self.assertLess(distance_to_axis((cx, cy, z), hinge), 1e-6)

        bm = _generate(window_type='AWNING', open_angle=math.radians(45))
        hinge = sash_hinge('AWNING', X0, X1, Z0, Z1, Y_OUT, Y_IN,
                           math.radians(45))
        for x, verts in _clusters(face_vertices(bm, MAT_HINGE), 0).items():
            cy = sum(v.co.y for v in verts) / len(verts)
            cz = sum(v.co.z for v in verts) / len(verts)
            self.assertLess(distance_to_axis((x, cy, cz), hinge), 1e-6)

    def test_awning_projects_outward_below_its_top_hinge(self):
        bm = _generate(window_type='AWNING', open_angle=math.radians(45))
        sash = bounds(face_vertices(bm, MAT_SASH))
        self.assertLess(sash[1][0], -0.5)
        self.assertLessEqual(sash[2][1], Z1 + 1e-9)

    def test_non_hinged_types_ignore_open_angle_and_add_no_hinges(self):
        for window_type in ('FIXED', 'SLIDING', 'DOUBLE_HUNG', 'ARCH'):
            bm = _generate(window_type=window_type, open_angle=ANGLE)
            sash = bounds(face_vertices(bm, MAT_SASH))
            self.assertGreaterEqual(sash[1][0], Y_OUT - 1e-9, window_type)
            self.assertEqual(face_vertices(bm, MAT_HINGE), [], window_type)

    def test_paired_leaves_open_towards_each_other(self):
        bm = _generate(open_angle=ANGLE, v_panels=2, sash_style='SIMPLE')
        sash = face_vertices(bm, MAT_SASH)
        left = bounds([v for v in sash if v.co.x < 0.6])
        right = bounds([v for v in sash if v.co.x >= 0.6])
        self.assertAlmostEqual(left[0][0], 0.0)
        self.assertAlmostEqual(right[0][1], 1.2)
        self.assertLess(left[1][0], -0.3)
        self.assertLess(right[1][0], -0.3)


class WindowModuleStructureTests(unittest.TestCase):
    def setUp(self):
        self.tree = ast.parse(
            (ROOT / "af_window.py").read_text(encoding="utf-8"))

    def _function(self, container, name):
        return next(node for node in container.body
                    if isinstance(node, ast.FunctionDef)
                    and node.name == name)

    def _class(self, name):
        return next(node for node in self.tree.body
                    if isinstance(node, ast.ClassDef) and node.name == name)

    def _calls_in_order(self, node):
        names = []
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call):
                func = sub.func
                if isinstance(func, ast.Attribute):
                    names.append((func.lineno, func.attr))
                elif isinstance(func, ast.Name):
                    names.append((func.lineno, func.id))
        return [name for _, name in sorted(names)]

    def test_toggle_operator_and_panel_only_offer_hinged_types(self):
        toggle = self._class("ARCHIFORGE_OT_window_toggle_open")
        poll = self._function(toggle, "poll")
        self.assertIn("window_type_can_open", self._calls_in_order(poll))
        self.assertNotIn("FIXED", ast.dump(poll))

        panel_draw = self._function(self._class("ARCHIFORGE_PT_window"),
                                    "draw")
        gated = False
        for node in ast.walk(panel_draw):
            if (isinstance(node, ast.If)
                    and "window_type_can_open" in ast.dump(node.test)
                    and "window_toggle_open" in ast.dump(node)):
                gated = True
        self.assertTrue(gated, "open toggle must be gated by window_type_can_open")

    def test_leaf_rotation_happens_after_glass_and_grille_but_before_hinges(self):
        generator = self._class("AF_WindowGenerator")
        leaf = self._function(generator, "_build_sash_leaf")
        calls = self._calls_in_order(leaf)
        rotate = calls.index("_rotate_verts_since")
        self.assertLess(calls.index("sash_hinge"), rotate)
        self.assertLess(calls.index("_glass_pane"), rotate)
        self.assertLess(calls.index("_build_grille"), rotate)
        self.assertGreater(calls.index("_build_hinges"), rotate)


if __name__ == "__main__":
    unittest.main()
