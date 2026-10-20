import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class _Preview:
    def __init__(self, icon_id):
        self.icon_id = icon_id


class _Broken:
    @property
    def icon_id(self):
        raise RuntimeError("preview released")


def _load(package_name=None):
    """Import af_icons standalone or as a submodule of a fake package."""
    name = "af_icons" if package_name is None else f"{package_name}.af_icons"
    spec = importlib.util.spec_from_file_location(name, ROOT / "af_icons.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class IconHelperTests(unittest.TestCase):
    def test_icon_kw_uses_icon_value_when_preview_exists(self):
        af_icons = _load()
        icons = {"wall": _Preview(42)}
        self.assertEqual(af_icons.icon_kw("wall", 'SNAP_FACE', icons), {'icon_value': 42})
        self.assertEqual(af_icons.icon_id("wall", icons), 42)

    def test_icon_kw_falls_back_to_builtin_icon(self):
        af_icons = _load()
        icons = {"wall": _Preview(42), "broken": _Broken(), "zero": _Preview(0)}
        # Missing PNG, broken preview, unloaded (id 0) and None → builtin icon,
        # never ``icon_value=0``.
        for name in ("missing", "broken", "zero", None, ""):
            self.assertEqual(af_icons.icon_kw(name, 'HOME', icons), {'icon': 'HOME'}, name)
            self.assertEqual(af_icons.icon_id(name, icons), 0, name)

    def test_get_icons_reads_package_collection(self):
        package = types.ModuleType("fake_af_pkg")
        collection = {"door": _Preview(7)}
        package.get_icons = lambda: collection
        sys.modules["fake_af_pkg"] = package
        try:
            af_icons = _load("fake_af_pkg")
            self.assertIs(af_icons.get_icons(), collection)
            self.assertEqual(af_icons.icon_kw("door", 'MESH_PLANE'), {'icon_value': 7})
            package.get_icons = lambda: None
            self.assertEqual(af_icons.get_icons(), {})
            self.assertEqual(af_icons.icon_kw("door", 'MESH_PLANE'), {'icon': 'MESH_PLANE'})

            def _raise():
                raise RuntimeError("previews gone")
            package.get_icons = _raise
            self.assertEqual(af_icons.get_icons(), {})
        finally:
            sys.modules.pop("fake_af_pkg", None)

    def test_get_icons_outside_blender_is_empty(self):
        af_icons = _load()
        self.assertEqual(af_icons.get_icons(), {})
        self.assertEqual(af_icons.icon_kw("wall", 'SNAP_FACE'), {'icon': 'SNAP_FACE'})

    def test_item_icon_lookup(self):
        af_icons = _load()
        self.assertEqual(af_icons.item_icon("TOILET", "bathroom"), "toilet")
        self.assertEqual(af_icons.item_icon("UNKNOWN", "bathroom"), "bathroom")
        self.assertIsNone(af_icons.item_icon("UNKNOWN"))
        # Item identifiers are unique across the catalogue modules so a flat
        # map cannot mix e.g. a stair type with a furniture type.
        self.assertEqual(len(af_icons.ITEM_ICONS), len(set(af_icons.ITEM_ICONS)))
        self.assertEqual(af_icons.item_icon("STRAIGHT", "stair"), "stair")
        self.assertEqual(af_icons.item_icon("RAMP", "stair"), "ramp")
        self.assertEqual(af_icons.item_icon("GABLE", "roof"), "roof_gable")

    def test_ui_modules_import_the_shared_helper_with_a_fallback(self):
        """Every panel/menu module must survive a missing af_icons module."""
        modules = sorted(p.name for p in ROOT.glob("af_*.py")
                         if p.name != "af_icons.py"
                         and "from .af_icons import" in p.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(modules), 25)
        for name in modules:
            text = (ROOT / name).read_text(encoding="utf-8")
            for start in [i for i in range(len(text))
                          if text.startswith("from .af_icons import", i)]:
                block = text[start:start + 400]
                self.assertIn("except ImportError", block, name)
                if "icon_kw as _icon" in block:
                    self.assertIn("def _icon(", block, name)
                if "item_icon" in block:
                    self.assertIn("return default", block, name)


if __name__ == "__main__":
    unittest.main()
