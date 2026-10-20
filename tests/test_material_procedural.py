import ast
import unittest
from pathlib import Path

try:
    from blender_stub import load_addon_module
except ImportError:  # pragma: no cover
    from tests.blender_stub import load_addon_module

import af_material_procedural as proc
from af_construction_presets import (
    CUSTOM_PRESET,
    WALL_PRESET_MATERIALS,
    WALL_SYSTEM_PRESETS,
    wall_preset_material,
)


ROOT = Path(__file__).resolve().parents[1]


class RecipeTests(unittest.TestCase):
    def test_every_recipe_kind_builds_and_validates(self):
        for kind in proc.RECIPES:
            with self.subTest(kind=kind):
                recipe = proc.build_recipe(kind, (0.5, 0.4, 0.3, 1.0), 0.6, 0.0)
                self.assertEqual(proc.recipe_problems(recipe), [],
                                 "recipe {} is inconsistent".format(kind))
                self.assertTrue(recipe["nodes"], "recipe without nodes")
                self.assertTrue(recipe["links"], "recipe without links")
                types = {node["type"] for node in recipe["nodes"]}
                self.assertTrue(types <= set(proc.ALLOWED_NODE_TYPES),
                                "unknown node type(s) {}".format(
                                    types - set(proc.ALLOWED_NODE_TYPES)))

    def test_output_node_is_the_principled_bsdf_callers_expect(self):
        recipe = proc.build_recipe('BRICK', (0.6, 0.3, 0.2, 1.0), 0.8, 0.0)
        names = [node.get("name") for node in recipe["nodes"]]
        self.assertIn(proc.BSDF_NODE_NAME, names)
        self.assertEqual(proc.BSDF_NODE_NAME, "Principled BSDF")
        self.assertIn(proc.OUTPUT_NODE_NAME, names)

    def test_unknown_kind_returns_none_so_builder_falls_back_to_flat(self):
        self.assertIsNone(
            proc.build_recipe('UNOBTAINIUM', (0.5, 0.5, 0.5, 1.0), 0.5, 0.0))

    def test_validator_reports_dangling_links_and_bad_types(self):
        recipe = proc.build_recipe('WOOD', (0.5, 0.4, 0.3, 1.0), 0.5, 0.0)
        recipe["links"].append(("missing", "Color", "bsdf", "Base Color"))
        recipe["nodes"].append({"id": "evil", "type": "ShaderNodeScript",
                                "loc": (0, 0)})
        problems = proc.recipe_problems(recipe)
        self.assertTrue(any("missing" in p for p in problems), problems)
        self.assertTrue(any("ShaderNodeScript" in p for p in problems),
                        problems)

    def test_brick_and_block_use_physical_sizes(self):
        brick = proc.build_recipe('BRICK', (0.6, 0.3, 0.2, 1.0), 0.8, 0.0,
                                  {"brick_width": 0.24, "row_height": 0.07})
        block = proc.build_recipe('BRICK', (0.6, 0.6, 0.6, 1.0), 0.8, 0.0,
                                  {"brick_width": 0.39, "row_height": 0.19})
        for recipe, width, height in ((brick, 0.24, 0.07), (block, 0.39, 0.19)):
            tex = next(n for n in recipe["nodes"]
                       if n["type"] == "ShaderNodeTexBrick")
            self.assertAlmostEqual(tex["inputs"]["Brick Width"], width)
            self.assertAlmostEqual(tex["inputs"]["Row Height"], height)
            # Scale 1.0 keeps the sizes in metres (object coordinates).
            self.assertAlmostEqual(tex["inputs"]["Scale"], 1.0)

    def test_every_recipe_feeds_the_bsdf_base_color(self):
        for kind in proc.RECIPES:
            recipe = proc.build_recipe(kind, (0.5, 0.4, 0.3, 1.0), 0.6, 0.0)
            targets = {(dst, inp) for _s, _o, dst, inp in recipe["links"]}
            bsdf = next(n for n in recipe["nodes"] if n["id"] == "bsdf")
            self.assertTrue(
                ("bsdf", "Base Color") in targets
                or "Base Color" in bsdf.get("inputs", {}),
                "{}: base colour neither linked nor set".format(kind))
            self.assertIn(("out", "Surface"), targets, kind)


class CatalogueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.af_material = load_addon_module("af_material")

    def test_catalogue_procedural_entries_are_valid(self):
        catalog = self.af_material.AF_MATERIALS_CATALOG
        procedural = {name: spec for name, spec in catalog.items()
                      if spec.get("proc")}
        self.assertGreaterEqual(len(procedural), 10)
        for name, spec in procedural.items():
            with self.subTest(material=name):
                self.assertIn(spec["proc"], proc.RECIPES)
                recipe = proc.build_recipe(
                    spec["proc"], spec["color"], spec.get("rough", 0.5),
                    spec.get("metal", 0.0), spec.get("proc_params"))
                self.assertIsNotNone(recipe)
                self.assertEqual(proc.recipe_problems(recipe), [])

    def test_block_material_exists_for_structural_block_preset(self):
        catalog = self.af_material.AF_MATERIALS_CATALOG
        self.assertIn("AF.Wall.Block", catalog)
        self.assertEqual(catalog["AF.Wall.Block"]["proc"], 'BRICK')
        params = catalog["AF.Wall.Block"]["proc_params"]
        self.assertAlmostEqual(params["brick_width"], 0.39)
        self.assertAlmostEqual(params["row_height"], 0.19)

    def test_tile_floor_has_no_grid_because_grout_is_geometry(self):
        catalog = self.af_material.AF_MATERIALS_CATALOG
        self.assertEqual(catalog["AF.Floor.Tile"]["proc"], 'CERAMIC')

    def test_preference_toggle_and_refresh_helpers_exist(self):
        self.assertTrue(callable(self.af_material.procedural_materials_enabled))
        self.assertTrue(callable(self.af_material.refresh_existing_af_materials))
        self.assertTrue(callable(self.af_material.create_catalog_material))


class WallPresetMaterialTests(unittest.TestCase):
    def test_every_non_custom_preset_maps_to_a_catalogue_material(self):
        af_material = load_addon_module("af_material")
        for identifier, _label, _thickness, _basis in WALL_SYSTEM_PRESETS:
            material = wall_preset_material(identifier)
            if identifier == CUSTOM_PRESET:
                self.assertIsNone(material)
                continue
            self.assertIsNotNone(material, identifier)
            self.assertIn(material, af_material.AF_MATERIALS_CATALOG)

    def test_brick_and_block_presets_get_bond_textures(self):
        self.assertEqual(WALL_PRESET_MATERIALS['BRICK'], "AF.Wall.Brick")
        self.assertEqual(WALL_PRESET_MATERIALS['STRUCTURAL_BLOCK'],
                         "AF.Wall.Block")

    def test_wall_module_applies_preset_material_on_creation_and_update(self):
        source = (ROOT / "af_wall.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        callers = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for sub in ast.walk(node):
                    if (isinstance(sub, ast.Call)
                            and isinstance(sub.func, ast.Name)
                            and sub.func.id == "_apply_wall_preset_material"):
                        callers.add(node.name)
        self.assertTrue({"af_wall_preset_update", "execute",
                         "create_wall_from_points"} <= callers, callers)


if __name__ == "__main__":
    unittest.main()
