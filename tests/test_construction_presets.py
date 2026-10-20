import ast
import unittest
from pathlib import Path

from af_construction_presets import (
    CUSTOM_PRESET,
    TILE_FORMAT_PRESETS,
    WALL_PRESET_NOTE,
    WALL_SYSTEM_PRESETS,
    preset_for_tile_size,
    preset_for_wall_thickness,
    tile_preset_dimensions,
    tile_preset_items,
    values_match,
    wall_preset_items,
    wall_preset_thickness,
)


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_WALL_SYSTEMS = ('WOOD_FRAME', 'BRICK', 'CONCRETE', 'STRUCTURAL_BLOCK')
REQUIRED_TILE_FORMATS = {
    'T30x30': (0.30, 0.30),
    'T45x45': (0.45, 0.45),
    'T60x60': (0.60, 0.60),
    'T60x120': (0.60, 1.20),
}
# Wording that would overclaim what the single-solid wall actually models.
FORBIDDEN_WALL_CLAIMS = ("code-compliant", "complies with", "NSR", "layers "
                         "generated", "bond pattern generated")


def _annotated_property(tree, class_name, property_name):
    klass = next(node for node in tree.body
                 if isinstance(node, ast.ClassDef) and node.name == class_name)
    return next(node for node in klass.body
                if isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id == property_name)


def _update_callback_name(property_node):
    call = property_node.annotation
    for keyword in call.keywords:
        if keyword.arg == "update":
            return ast.dump(keyword.value)
    return ""


class WallSystemPresetTests(unittest.TestCase):
    def test_required_systems_have_distinct_editable_reference_thicknesses(self):
        identifiers = [preset[0] for preset in WALL_SYSTEM_PRESETS]
        self.assertEqual(len(identifiers), len(set(identifiers)))
        self.assertEqual(identifiers[0], CUSTOM_PRESET)
        for system in REQUIRED_WALL_SYSTEMS:
            self.assertIn(system, identifiers)
            thickness = wall_preset_thickness(system)
            self.assertIsInstance(thickness, float)
            self.assertTrue(0.05 <= thickness <= 0.60, system)
        thicknesses = [wall_preset_thickness(s) for s in REQUIRED_WALL_SYSTEMS]
        self.assertEqual(len(set(thicknesses)), len(thicknesses))
        self.assertIsNone(wall_preset_thickness(CUSTOM_PRESET))
        self.assertIsNone(wall_preset_thickness('UNKNOWN'))

    def test_enum_items_present_values_as_references_not_compliance(self):
        items = wall_preset_items()
        self.assertEqual([item[0] for item in items],
                         [preset[0] for preset in WALL_SYSTEM_PRESETS])
        for identifier, label, description in items:
            self.assertEqual(len((identifier, label, description)), 3)
            self.assertTrue(label.strip())
            if identifier != CUSTOM_PRESET:
                self.assertIn("reference", description.lower())
                self.assertIn(WALL_PRESET_NOTE, description)
            for claim in FORBIDDEN_WALL_CLAIMS:
                self.assertNotIn(claim.lower(), description.lower())
        self.assertIn("single solid", WALL_PRESET_NOTE)
        self.assertIn("not a code requirement", WALL_PRESET_NOTE)

    def test_manual_thickness_edits_fall_back_to_custom(self):
        brick = wall_preset_thickness('BRICK')
        self.assertEqual(preset_for_wall_thickness('BRICK', brick), 'BRICK')
        # Blender stores single-precision floats; tiny drift keeps the label.
        self.assertEqual(preset_for_wall_thickness('BRICK', brick + 2e-9),
                         'BRICK')
        self.assertEqual(preset_for_wall_thickness('BRICK', brick + 0.05),
                         CUSTOM_PRESET)
        self.assertEqual(preset_for_wall_thickness(CUSTOM_PRESET, 0.33),
                         CUSTOM_PRESET)


class TileFormatPresetTests(unittest.TestCase):
    def test_commercial_formats_are_exposed_with_exact_sizes(self):
        identifiers = [preset[0] for preset in TILE_FORMAT_PRESETS]
        self.assertEqual(identifiers[0], CUSTOM_PRESET)
        self.assertEqual(len(identifiers), len(set(identifiers)))
        for identifier, dims in REQUIRED_TILE_FORMATS.items():
            self.assertIn(identifier, identifiers)
            width, depth = tile_preset_dimensions(identifier)
            self.assertAlmostEqual(width, dims[0])
            self.assertAlmostEqual(depth, dims[1])
        self.assertIsNone(tile_preset_dimensions(CUSTOM_PRESET))
        items = tile_preset_items()
        self.assertEqual([item[0] for item in items], identifiers)
        self.assertTrue(all(len(item) == 3 for item in items))

    def test_manual_size_edits_fall_back_to_custom(self):
        self.assertEqual(preset_for_tile_size('T60x120', 0.60, 1.20),
                         'T60x120')
        self.assertEqual(preset_for_tile_size('T60x120', 0.60, 1.00),
                         CUSTOM_PRESET)
        self.assertEqual(preset_for_tile_size('T30x30', 0.3000000119, 0.30),
                         'T30x30')
        self.assertFalse(values_match(None, 0.3))
        self.assertFalse(values_match((0.3, 0.3), (0.3,)))


class PresetWiringTests(unittest.TestCase):
    def test_wall_properties_apply_presets_and_reset_on_manual_edits(self):
        tree = ast.parse((ROOT / "af_wall.py").read_text(encoding="utf-8"))
        preset = _annotated_property(tree, "AF_WallProperties", "wall_preset")
        self.assertIn("af_wall_preset_update", _update_callback_name(preset))
        width = _annotated_property(tree, "AF_WallProperties", "width")
        self.assertIn("af_wall_width_update", _update_callback_name(width))
        for operator in ("ARCHIFORGE_OT_wall", "ARCHIFORGE_OT_wall_draw"):
            _annotated_property(tree, operator, "wall_preset")
        source = (ROOT / "af_wall.py").read_text(encoding="utf-8")
        self.assertIn("wall_preset_thickness(self.wall_preset)", source)
        self.assertIn("preset_for_wall_thickness(", source)

    def test_floor_properties_apply_presets_and_reset_on_manual_edits(self):
        tree = ast.parse((ROOT / "af_floor.py").read_text(encoding="utf-8"))
        preset = _annotated_property(tree, "AF_FloorProperties", "tile_preset")
        self.assertIn("af_floor_tile_preset_update",
                      _update_callback_name(preset))
        for name in ("tile_width", "tile_depth"):
            size = _annotated_property(tree, "AF_FloorProperties", name)
            self.assertIn("af_floor_tile_size_update",
                          _update_callback_name(size))
        _annotated_property(tree, "ARCHIFORGE_OT_floor", "tile_preset")
        source = (ROOT / "af_floor.py").read_text(encoding="utf-8")
        self.assertIn("tile_preset_dimensions(self.tile_preset)", source)
        self.assertIn("preset_for_tile_size(", source)


if __name__ == "__main__":
    unittest.main()
