import unittest
from types import SimpleNamespace

import af_units


class ConversionTests(unittest.TestCase):
    def test_normalize_falls_back_to_metric(self):
        self.assertEqual(af_units.normalize('IMPERIAL'), 'IMPERIAL')
        self.assertEqual(af_units.normalize('METRIC'), 'METRIC')
        self.assertEqual(af_units.normalize('FURLONGS'), 'METRIC')
        self.assertEqual(af_units.normalize(None), 'METRIC')
        self.assertEqual(af_units.DEFAULT_UNIT_SYSTEM, 'METRIC')

    def test_metric_is_identity(self):
        self.assertAlmostEqual(af_units.convert_length(2.5, 'METRIC'), 2.5)
        self.assertAlmostEqual(af_units.convert_area(2.5, 'METRIC'), 2.5)
        self.assertAlmostEqual(af_units.convert_volume(2.5, 'METRIC'), 2.5)
        self.assertEqual((af_units.length_unit('METRIC'),
                          af_units.area_unit('METRIC'),
                          af_units.volume_unit('METRIC')), ("m", "m2", "m3"))

    def test_imperial_uses_international_foot(self):
        self.assertAlmostEqual(af_units.convert_length(0.3048, 'IMPERIAL'), 1.0)
        self.assertAlmostEqual(af_units.convert_area(0.3048 ** 2, 'IMPERIAL'), 1.0)
        self.assertAlmostEqual(af_units.convert_volume(0.3048 ** 3, 'IMPERIAL'), 1.0)
        self.assertAlmostEqual(af_units.convert_length(1.0, 'IMPERIAL'),
                               3.280839895, places=6)
        self.assertEqual((af_units.length_unit('IMPERIAL'),
                          af_units.area_unit('IMPERIAL'),
                          af_units.volume_unit('IMPERIAL')),
                         ("ft", "ft2", "ft3"))

    def test_feet_and_inches_reading(self):
        self.assertEqual(af_units.feet_and_inches(3.048), "10' 0\"")
        self.assertEqual(af_units.feet_and_inches(0.3048 + 0.0254 * 6), "1' 6\"")
        self.assertEqual(af_units.feet_and_inches(0.0254 * 11.9), "1' 0\"")
        self.assertEqual(af_units.feet_and_inches(0.0254 * 2.5), "0' 2.5\"")
        self.assertEqual(af_units.feet_and_inches(0.0254 * 2.6,
                                                  inch_precision=1.0), "0' 3\"")

    def test_enum_items_cover_both_systems(self):
        identifiers = [item[0] for item in af_units.UNIT_SYSTEM_ITEMS]
        self.assertEqual(identifiers, list(af_units.UNIT_SYSTEMS))


class SceneSyncTests(unittest.TestCase):
    def _scene(self):
        return SimpleNamespace(unit_settings=SimpleNamespace(
            system='METRIC', length_unit='METERS', mass_unit='KILOGRAMS',
            scale_length=1.0))

    def test_apply_to_scene_sets_system_and_length_unit_only(self):
        scene = self._scene()
        self.assertTrue(af_units.apply_to_scene(scene, 'IMPERIAL'))
        self.assertEqual(scene.unit_settings.system, 'IMPERIAL')
        self.assertEqual(scene.unit_settings.length_unit, 'FEET')
        self.assertEqual(scene.unit_settings.mass_unit, 'POUNDS')
        self.assertEqual(scene.unit_settings.scale_length, 1.0)
        self.assertEqual(af_units.scene_system(scene), 'IMPERIAL')

        af_units.apply_to_scene(scene, 'METRIC')
        self.assertEqual(scene.unit_settings.system, 'METRIC')
        self.assertEqual(scene.unit_settings.length_unit, 'METERS')

    def test_apply_to_scenes_counts_and_tolerates_missing_settings(self):
        scenes = [self._scene(), self._scene(), SimpleNamespace()]
        self.assertEqual(af_units.apply_to_scenes(scenes, 'IMPERIAL'), 2)
        self.assertFalse(af_units.apply_to_scene(SimpleNamespace(), 'METRIC'))
        self.assertEqual(af_units.scene_system(SimpleNamespace()), 'METRIC')

    def test_settings_copies_are_independent(self):
        settings = af_units.scene_unit_settings('IMPERIAL')
        settings["system"] = 'BROKEN'
        self.assertEqual(af_units.scene_unit_settings('IMPERIAL')["system"],
                         'IMPERIAL')


if __name__ == "__main__":
    unittest.main()
