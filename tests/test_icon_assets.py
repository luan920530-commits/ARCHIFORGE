import ast
import struct
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ICON_DIR = ROOT / "icons"
GENERATOR = ICON_DIR / "generate_icons.py"
ICON_HELPER = ROOT / "af_icons.py"

# Helper names whose first/second positional argument is a custom icon key.
#   _icon_kw(icons, "wall", 'SNAP_FACE')   → argument index 1
#   icon_kw("wall", 'SNAP_FACE') / _icon("wall", ...) → argument index 0
ICON_CALLS = {"_icon_kw": 1, "icon_kw": 0, "_icon": 0}
ITEM_CALLS = {"_item_icon", "item_icon"}


def _string_constant(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _dict_literal(tree, name):
    """Top-level ``NAME = {...}`` assignment as ``{key: value}`` of strings."""
    for node in tree.body:
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Dict):
            continue
        if any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            result = {}
            for key, value in zip(node.value.keys, node.value.values):
                key_str = _string_constant(key)
                if key_str is None:
                    continue
                if isinstance(value, ast.Name):
                    result[key_str] = value.id
                else:
                    result[key_str] = _string_constant(value)
            return result
    raise AssertionError(f"{name} dict literal not found")


def _generator_icon_names():
    tree = ast.parse(GENERATOR.read_text(encoding="utf-8"))
    icons = _dict_literal(tree, "ICONS")
    draw_functions = {
        node.name for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name.startswith("icon_")
    }
    for name, function in icons.items():
        assert function in draw_functions, f"{name}: {function} is not defined"
    return set(icons)


def _referenced_icon_names():
    """Every literal custom icon key used by the add-on UI modules."""
    referenced = {}
    files = sorted(ROOT.glob("af_*.py")) + [ROOT / "__init__.py"]
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                function = node.func
                name = None
                if isinstance(function, ast.Name):
                    name = function.id
                elif isinstance(function, ast.Attribute):
                    name = function.attr
                index = ICON_CALLS.get(name)
                if index is not None and len(node.args) > index:
                    key = _string_constant(node.args[index])
                    if key is not None:
                        referenced.setdefault(key, set()).add(path.name)
                    elif isinstance(node.args[index], ast.Call):
                        inner = node.args[index].func
                        inner_name = getattr(inner, "id", getattr(inner, "attr", None))
                        if inner_name in ITEM_CALLS and len(node.args[index].args) > 1:
                            default = _string_constant(node.args[index].args[1])
                            if default is not None:
                                referenced.setdefault(default, set()).add(path.name)
            if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
                if node.value.id != "icons":
                    continue
                key = _string_constant(node.slice)
                if key is not None:
                    referenced.setdefault(key, set()).add(path.name)
    return referenced


class IconAssetTests(unittest.TestCase):
    def setUp(self):
        self.expected = _generator_icon_names()
        self.pngs = {path.stem: path for path in ICON_DIR.glob("*.png")}

    def test_generator_defines_full_icon_set(self):
        # Brand + the module/feature/item sets introduced in v1.13.
        self.assertGreaterEqual(len(self.expected), 112)
        self.assertEqual(set(self.pngs), self.expected,
                         "icons/*.png must match generate_icons.ICONS exactly "
                         "(regenerate with: python icons/generate_icons.py)")

    def test_all_custom_icon_assets_are_valid_128px_rgba_pngs(self):
        for name, path in self.pngs.items():
            data = path.read_bytes()
            self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"), name)
            self.assertGreaterEqual(len(data), 33, name)
            width, height = struct.unpack(">II", data[16:24])
            self.assertEqual((width, height), (128, 128), name)
            self.assertEqual(data[25], 6, f"{name} must be RGBA")

    def test_every_custom_icon_referenced_by_ui_has_an_asset(self):
        referenced = _referenced_icon_names()
        # The shared helpers are used by every panel/menu module.
        self.assertGreaterEqual(len(referenced), 45)
        self.assertGreaterEqual(len({f for files in referenced.values() for f in files}), 25)
        missing = set(referenced) - self.expected
        self.assertEqual(missing, set(), f"Missing PNG icon assets: {sorted(missing)}")

    def test_item_and_object_icon_maps_point_to_assets(self):
        tree = ast.parse(ICON_HELPER.read_text(encoding="utf-8"))
        item_icons = _dict_literal(tree, "ITEM_ICONS")
        object_icons = _dict_literal(tree, "OBJECT_ICONS")
        self.assertGreaterEqual(len(item_icons), 64)
        self.assertGreaterEqual(len(object_icons), 17)
        for mapping in (item_icons, object_icons):
            missing = set(mapping.values()) - self.expected
            self.assertEqual(missing, set(), f"ITEM/OBJECT icon without PNG: {sorted(missing)}")
        # Every catalogue item type has its own, non-generic icon.
        generic = {"bathroom", "electrical", "furniture", "kitchen", "decor",
                   "opening", "structure", "roof"}
        self.assertEqual(set(item_icons.values()) & generic, set())
        for prop in object_icons:
            self.assertTrue(prop.startswith("archiforge_"), prop)

    def test_item_icon_map_covers_every_catalogue_item_type(self):
        """Each ``item_type`` enum of the catalogue modules has an icon."""
        tree = ast.parse(ICON_HELPER.read_text(encoding="utf-8"))
        item_icons = _dict_literal(tree, "ITEM_ICONS")
        modules = {
            "af_bathroom.py": "AF_BATH_TYPES",
            "af_electrical.py": "AF_ELECTRICAL_TYPES",
            "af_furniture.py": "AF_FURN_TYPES",
            "af_kitchen.py": "AF_KIT_TYPES",
            "af_decor.py": "AF_DECOR_TYPES",
            "af_openings.py": "AF_OPEN_TYPES",
            "af_structure.py": "AF_STRUCT_TYPES",
            "af_stair.py": "AF_STAIR_TYPES",
        }
        for filename, enum_name in modules.items():
            ids = self._enum_ids(ROOT / filename, enum_name)
            self.assertTrue(ids, f"{filename}: {enum_name} not found")
            missing = ids - set(item_icons)
            self.assertEqual(missing, set(), f"{filename}: item types without icon {sorted(missing)}")
        # Control Center roof buttons (GABLE/HIP/SHED) are also covered.
        roofs = self._enum_ids(ROOT / "af_roof.py", "AF_ROOF_TYPES")
        self.assertTrue({"GABLE", "HIP", "SHED"} <= roofs)
        self.assertTrue({"GABLE", "HIP", "SHED"} <= set(item_icons))

    @staticmethod
    def _enum_ids(path, enum_name):
        """Identifiers of a module-level EnumProperty items list."""
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            if not any(isinstance(t, ast.Name) and t.id == enum_name for t in node.targets):
                continue
            ids = set()
            for element in getattr(node.value, "elts", ()):
                if isinstance(element, ast.Tuple) and element.elts:
                    key = _string_constant(element.elts[0])
                    if key:
                        ids.add(key)
            return ids
        return set()


if __name__ == "__main__":
    unittest.main()
