import ast
import math
import unittest
from pathlib import Path
from types import SimpleNamespace

from af_floor_geometry import (
    GROUT_GEOMETRY_PATTERNS,
    GROUT_STYLES,
    clip_polygon_to_outline,
    fragments_cover_polygon,
    grout_joint_thickness,
    normalize_outline,
    polygon_area,
    polygon_boundary_edges,
    triangulate_polygon,
)
try:
    from blender_stub import bounds, face_vertices, load_addon_module
except ImportError:  # invoked as ``python -m unittest tests.<module>``
    from tests.blender_stub import bounds, face_vertices, load_addon_module


ROOT = Path(__file__).resolve().parents[1]

MAT_TILE, MAT_GROUT, MAT_BORDER, MAT_BASE, MAT_TILE_B = 0, 1, 2, 3, 4
TILE_THICKNESS = 0.010
GROUT_DEPTH = 0.003
BASE_THICKNESS = 0.05


def _floor_props(**overrides):
    base = dict(
        pattern='REGULAR', width=1.0, depth=1.0,
        tile_preset='CUSTOM', tile_width=0.3, tile_depth=0.3,
        tile_thickness=TILE_THICKNESS,
        grout_width=0.004, grout_depth=GROUT_DEPTH, grout_style='RECESSED',
        bevel_size=0.0, offset_x=0.0, offset_y=0.0, offset_row=0.5,
        pattern_rotation=0.0, herringbone_angle=math.radians(45),
        parquet_blocks=3, parquet_style='BLOCK', plank_width=0.12,
        plank_length_min=0.6, plank_length_max=2.4, plank_random_seed=42,
        hex_size=0.15, hex_flat_top=True, cobble_seed=1,
        cobble_size_min=0.08, cobble_size_max=0.2,
        border_enable=False, border_style='SINGLE', border_width=0.1,
        border_thickness=0.01, base_enable=True,
        base_thickness=BASE_THICKNESS, outline_vertices=[],
        outline_enabled=False, source_curve="", origin_center=False,
        mat_tile=MAT_TILE, mat_grout=MAT_GROUT, mat_border=MAT_BORDER,
        mat_base=MAT_BASE, mat_tile_b=MAT_TILE_B,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _generate(**overrides):
    af_floor = load_addon_module("af_floor")
    generator = af_floor.AF_FloorGenerator(_floor_props(**overrides))
    return generator.generate(), generator._mat


def _z_range(bm, layer, material_index):
    verts = face_vertices(bm, material_index, layer=layer)
    if not verts:
        return None
    return bounds(verts)[2]


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


class GroutJointTests(unittest.TestCase):
    def test_each_grout_style_produces_a_different_joint_height(self):
        heights = {style: grout_joint_thickness(style, TILE_THICKNESS,
                                                GROUT_DEPTH)
                   for style in GROUT_STYLES}

        self.assertEqual(len(set(heights.values())), len(GROUT_STYLES))
        self.assertAlmostEqual(heights['FLAT'], TILE_THICKNESS)
        self.assertAlmostEqual(heights['RAISED'], TILE_THICKNESS + GROUT_DEPTH)
        self.assertAlmostEqual(heights['RECESSED'],
                               TILE_THICKNESS - GROUT_DEPTH)
        self.assertGreater(heights['RAISED'], heights['FLAT'])
        self.assertGreater(heights['FLAT'], heights['RECESSED'])

    def test_recessed_joint_never_collapses_and_unknown_style_is_rejected(self):
        self.assertAlmostEqual(
            grout_joint_thickness('RECESSED', 0.002, 0.02), 0.001)
        self.assertAlmostEqual(
            grout_joint_thickness('RAISED', 0.01, -0.5), 0.01)
        with self.assertRaises(ValueError):
            grout_joint_thickness('CONCAVE', 0.01, 0.003)

    def test_floor_module_routes_every_joint_through_the_style_helper(self):
        source = (ROOT / "af_floor.py").read_text(encoding="utf-8")
        self.assertNotIn("tt - p.grout_depth", source)
        tree = ast.parse(source)
        generator = next(node for node in tree.body
                         if isinstance(node, ast.ClassDef)
                         and node.name == "AF_FloorGenerator")
        for name in ("_build_regular", "_build_offset",
                     "_grout_line_h", "_grout_line_v"):
            method = next(node for node in generator.body
                          if isinstance(node, ast.FunctionDef)
                          and node.name == name)
            self.assertIn("_joint_thickness", ast.dump(method), name)
        self.assertEqual(GROUT_GEOMETRY_PATTERNS, ('REGULAR', 'OFFSET'))


class FloorGeneratorHeadlessTests(unittest.TestCase):
    """Run the real bmesh builder against the stub and inspect the mesh."""

    def test_grout_styles_generate_distinct_prisms_on_regular_and_offset(self):
        for pattern in GROUT_GEOMETRY_PATTERNS:
            tops = {}
            for style in GROUT_STYLES:
                bm, layer = _generate(pattern=pattern, grout_style=style)
                tile_z = _z_range(bm, layer, MAT_TILE)
                grout_z = _z_range(bm, layer, MAT_GROUT)
                self.assertIsNotNone(grout_z, (pattern, style))
                self.assertAlmostEqual(grout_z[0], tile_z[0])
                tops[style] = round(grout_z[1], 6)
            self.assertAlmostEqual(tops['FLAT'], BASE_THICKNESS + TILE_THICKNESS)
            self.assertAlmostEqual(tops['RAISED'],
                                   BASE_THICKNESS + TILE_THICKNESS + GROUT_DEPTH)
            self.assertAlmostEqual(tops['RECESSED'],
                                   BASE_THICKNESS + TILE_THICKNESS - GROUT_DEPTH)

    def test_base_slab_sits_under_every_pattern_instead_of_covering_it(self):
        for pattern in ('REGULAR', 'OFFSET', 'HERRINGBONE', 'PARQUET',
                        'DIAGONAL', 'HEXAGONAL', 'BASKET_WEAVE', 'RANDOM',
                        'COBBLESTONE', 'WOOD_PLANK'):
            bm, layer = _generate(pattern=pattern)
            self.assertEqual(_z_range(bm, layer, MAT_BASE),
                             (0.0, BASE_THICKNESS), pattern)
            for material in (MAT_TILE, MAT_TILE_B, MAT_GROUT):
                z_range = _z_range(bm, layer, material)
                if z_range is None:
                    continue
                self.assertGreaterEqual(z_range[0], BASE_THICKNESS - 1e-9,
                                        (pattern, material))

        bm, layer = _generate(base_enable=False, grout_style='FLAT')
        self.assertIsNone(_z_range(bm, layer, MAT_BASE))
        self.assertEqual(_z_range(bm, layer, MAT_TILE), (0.0, TILE_THICKNESS))

    def test_border_and_custom_outline_floors_are_lifted_as_well(self):
        bm, layer = _generate(border_enable=True)
        self.assertAlmostEqual(_z_range(bm, layer, MAT_BORDER)[0],
                               BASE_THICKNESS)

        outline = [SimpleNamespace(x=x, y=y) for x, y in (
            (0, 0), (1, 0), (1, 0.5), (0.5, 0.5), (0.5, 1), (0, 1))]
        bm, layer = _generate(outline_enabled=True, outline_vertices=outline)
        self.assertEqual(_z_range(bm, layer, MAT_BASE), (0.0, BASE_THICKNESS))
        self.assertAlmostEqual(_z_range(bm, layer, MAT_TILE)[0], BASE_THICKNESS)
        self.assertAlmostEqual(_z_range(bm, layer, MAT_GROUT)[1],
                               BASE_THICKNESS + TILE_THICKNESS - GROUT_DEPTH)


if __name__ == "__main__":
    unittest.main()
