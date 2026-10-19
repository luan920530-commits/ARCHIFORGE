import ast
import struct
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ICON_DIR = ROOT / "icons"
EXPECTED_ICONS = {
    "archiforge", "archipack", "wall", "wall_draw", "slab", "roof",
    "truss", "fence", "floor", "door", "window", "stair", "bathroom",
    "electrical", "furniture", "kitchen", "decor", "opening",
    "structure", "quantities", "control_center", "boolean", "snap",
    "material",
}


class IconAssetTests(unittest.TestCase):
    def test_all_custom_icon_assets_are_valid_128px_rgba_pngs(self):
        pngs = {path.stem: path for path in ICON_DIR.glob("*.png")}
        self.assertEqual(set(pngs), EXPECTED_ICONS)

        for name, path in pngs.items():
            data = path.read_bytes()
            self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"), name)
            self.assertGreaterEqual(len(data), 33, name)
            width, height = struct.unpack(">II", data[16:24])
            self.assertEqual((width, height), (128, 128), name)
            self.assertEqual(data[25], 6, f"{name} must be RGBA")

    def test_every_custom_icon_referenced_by_ui_has_an_asset(self):
        referenced = set()
        for filename in ("__init__.py", "af_control_center.py"):
            tree = ast.parse((ROOT / filename).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    function = node.func
                    if isinstance(function, ast.Name) and function.id == "_icon_kw":
                        if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
                            if isinstance(node.args[1].value, str):
                                referenced.add(node.args[1].value)
                if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
                    if node.value.id != "icons":
                        continue
                    key = node.slice
                    if isinstance(key, ast.Constant) and isinstance(key.value, str):
                        referenced.add(key.value)

        missing = referenced - EXPECTED_ICONS
        self.assertEqual(missing, set(), f"Missing PNG icon assets: {sorted(missing)}")


if __name__ == "__main__":
    unittest.main()
