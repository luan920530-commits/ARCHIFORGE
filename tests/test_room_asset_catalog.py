import ast
import unittest
from pathlib import Path

from af_room_assets_catalog import ROOM_ASSETS


ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_FAMILIES = {
    "accessory", "bed", "cabinet", "canopy", "headboard", "outdoor",
    "planter", "seat", "set", "shelf", "sofa", "table",
}


class RoomAssetCatalogTests(unittest.TestCase):
    def test_each_room_has_at_least_twenty_unique_assets_or_sets(self):
        all_ids = []
        for room, assets in ROOM_ASSETS.items():
            with self.subTest(room=room):
                self.assertGreaterEqual(len(assets), 20)
                self.assertEqual(len(assets), len({asset[0] for asset in assets}))
                all_ids.extend(asset[0] for asset in assets)
        self.assertEqual(len(all_ids), len(set(all_ids)))

    def test_catalog_dimensions_and_generator_families_are_valid(self):
        tree = ast.parse(
            (ROOT / "af_room_assets.py").read_text(encoding="utf-8"))
        generator = next(node for node in tree.body
                         if isinstance(node, ast.ClassDef)
                         and node.name == "AF_RoomAssetGenerator")
        build = next(node for node in generator.body
                     if isinstance(node, ast.FunctionDef)
                     and node.name == "_build")
        dispatch = next(node for node in ast.walk(build)
                        if isinstance(node, ast.Dict))
        implemented = {
            key.value for key in dispatch.keys
            if isinstance(key, ast.Constant) and isinstance(key.value, str)
        }

        for room, assets in ROOM_ASSETS.items():
            for asset in assets:
                asset_id, label, description, family, style, width, depth, height = asset
                with self.subTest(room=room, asset=asset_id):
                    self.assertTrue(label)
                    self.assertTrue(description)
                    self.assertTrue(style)
                    self.assertIn(family, SUPPORTED_FAMILIES)
                    self.assertIn(family, implemented)
                    self.assertGreater(width, 0.0)
                    self.assertGreater(depth, 0.0)
                    self.assertGreater(height, 0.0)

    def test_room_asset_materials_are_registered_in_the_shared_catalog(self):
        tree = ast.parse((ROOT / "af_material.py").read_text(encoding="utf-8"))
        assignment = next(
            node for node in tree.body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name)
                    and target.id == "AF_MATERIALS_CATALOG"
                    for target in node.targets)
        )
        registered = {
            key.value for key in assignment.value.keys
            if isinstance(key, ast.Constant) and isinstance(key.value, str)
        }
        self.assertTrue({
            "AF.Room.Wood", "AF.Room.Fabric",
            "AF.Room.Metal", "AF.Room.Accent",
        }.issubset(registered))

    def test_catalog_has_explicit_table_and_shelving_variants(self):
        bedroom_families = {asset[3] for asset in ROOM_ASSETS["BEDROOM"]}
        living_families = {asset[3] for asset in ROOM_ASSETS["LIVING"]}
        kitchen_families = {asset[3] for asset in ROOM_ASSETS["KITCHEN"]}

        self.assertIn("table", bedroom_families)
        self.assertIn("table", living_families)
        self.assertIn("shelf", living_families)
        self.assertIn("shelf", kitchen_families)


if __name__ == "__main__":
    unittest.main()
