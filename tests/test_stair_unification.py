"""The two stair modules of 1.x were merged into ``af_stair.py`` (1.12)."""
import ast
import contextlib
import io
import re
import unittest
from pathlib import Path

try:
    from blender_stub import load_addon_module
except ImportError:  # pragma: no cover
    from tests.blender_stub import load_addon_module


ROOT = Path(__file__).resolve().parents[1]


class _Props(dict):
    """Stand-in for the ``archiforge_stair`` PropertyGroup."""

    def __setattr__(self, name, value):
        self[name] = value

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)


class _LegacyObject:
    type = 'MESH'

    def __init__(self, name, legacy):
        self.name = name
        self._idprops = {"archiforge_stairs": dict(legacy)}
        self.archiforge_stair = _Props()

    def get(self, key, default=None):
        return self._idprops.get(key, default)

    def __delitem__(self, key):
        del self._idprops[key]


class StairUnificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.af_stair = load_addon_module("af_stair")

    def test_duplicate_module_is_gone_and_not_referenced(self):
        self.assertFalse((ROOT / "af_stairs.py").exists())
        pattern = re.compile(r"\bimport af_stairs\b|from \.\s*af_stairs|"
                             r"[\"']af_stairs[\"']")
        for path in sorted(ROOT.glob("*.py")):
            self.assertIsNone(pattern.search(path.read_text(encoding="utf-8")),
                              "{} still references af_stairs".format(path.name))

    def test_manifest_lists_single_stair_module(self):
        source = (ROOT / "__init__.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        names = []
        for node in ast.walk(tree):
            if (isinstance(node, ast.Assign)
                    and isinstance(node.targets[0], ast.Name)
                    and node.targets[0].id in ("_FIRST_ORDER", "_RELOAD_ORDER")):
                names.append([elt.value for elt in node.value.elts])
        self.assertEqual(len(names), 2)
        for manifest in names:
            self.assertIn("af_stair", manifest)
            self.assertNotIn("af_stairs", manifest)

    def test_legacy_operator_id_is_kept_as_internal_alias(self):
        ids = {cls.bl_idname: cls for cls in self.af_stair.classes
               if hasattr(cls, "bl_idname")}
        self.assertIn("archiforge.stair", ids)
        self.assertIn("archiforge.stairs", ids)
        self.assertIn('INTERNAL', ids["archiforge.stairs"].bl_options)
        self.assertNotIn('INTERNAL', ids["archiforge.stair"].bl_options)

    def test_legacy_objects_are_migrated_to_the_single_property_group(self):
        legacy = {"item_type": 1, "width": 1.2, "total_rise": 2.7,
                  "n_risers": 15, "is_af_stair": True}
        obj = _LegacyObject("AF_Stairs", legacy)
        log = io.StringIO()
        with contextlib.redirect_stdout(log):
            migrated = self.af_stair.migrate_legacy_stairs([obj])
        self.assertIn("1 legacy stair object(s) migrated", log.getvalue())

        self.assertEqual(migrated, [obj])
        self.assertIsNone(obj.get("archiforge_stairs"))
        props = obj.archiforge_stair
        self.assertEqual(props["width"], 1.2)
        self.assertEqual(props["n_risers"], 15)
        self.assertTrue(props["is_af_stair"])
        self.assertEqual(props["object_name"], "AF_Stairs")
        self.assertEqual(props["af_version"], self.af_stair.AF_STAIR_VERSION)

    def test_objects_without_legacy_data_are_left_alone(self):
        class Plain:
            type = 'MESH'
            name = "Cube"

            def get(self, key, default=None):
                return default

        self.assertEqual(self.af_stair.migrate_legacy_stairs([Plain()]), [])
        self.assertEqual(self.af_stair.migrate_legacy_stairs([]), [])


if __name__ == "__main__":
    unittest.main()
