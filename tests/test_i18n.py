"""Regression tests for the addon-level language switch (af_i18n*)."""
import ast
import re
import unittest
from pathlib import Path

try:
    import blender_stub
    import ui_strings
except ImportError:  # pragma: no cover - imported as tests.test_i18n
    from tests import blender_stub, ui_strings

blender_stub.install()

import af_i18n  # noqa: E402  (needs the stub for the optional bpy import)
import af_i18n_es  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
ADDON = "ArchiForge"
PLACEHOLDER = re.compile(r"\{[^{}]*\}|%\(\w+\)[sd]|%[sd]")


def _dict_literal_keys(source, name):
    """Keys of the dict literal assigned to ``name`` (duplicates included)."""
    tree = ast.parse(source)
    for node in tree.body:
        if (isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict)
                and node.targets[0].id == name):
            return [key.value for key in node.value.keys]
    raise AssertionError("dict literal {} not found".format(name))


class CatalogueTests(unittest.TestCase):
    """The translation data must stay complete and well formed."""

    def test_every_ui_string_in_the_sources_is_covered(self):
        labels, tooltips = ui_strings.all_ui_strings()
        missing = (labels | tooltips) - ui_strings.known_ui_strings(af_i18n_es)
        self.assertFalse(
            missing,
            "UI strings without translation (run `python tests/ui_strings.py`): "
            "{}".format(sorted(missing)[:15]))

    def test_dict_literals_have_no_duplicate_keys(self):
        source = (ROOT / "af_i18n_es.py").read_text(encoding="utf-8")
        for name in ("TRANSLATIONS", "ENGLISH_FOR_SPANISH_SOURCE"):
            keys = _dict_literal_keys(source, name)
            duplicates = sorted({k for k in keys if keys.count(k) > 1})
            self.assertEqual(duplicates, [], "{} repeats {}".format(name, duplicates))

    def test_entries_are_non_empty_and_not_identity(self):
        for name in ("TRANSLATIONS", "ENGLISH_FOR_SPANISH_SOURCE"):
            table = getattr(af_i18n_es, name)
            for msgid, msgstr in table.items():
                self.assertTrue(msgid.strip() and msgstr.strip(), (name, msgid))
                self.assertNotEqual(msgid, msgstr,
                                    "{}: identity entry {!r} belongs in "
                                    "SAME_IN_SPANISH".format(name, msgid))

    def test_tables_do_not_overlap(self):
        en_es = set(af_i18n_es.TRANSLATIONS)
        es_en = set(af_i18n_es.ENGLISH_FOR_SPANISH_SOURCE)
        same = set(af_i18n_es.SAME_IN_SPANISH)
        self.assertFalse(en_es & es_en)
        self.assertFalse(same & (en_es | es_en))

    def test_placeholders_and_edges_are_preserved(self):
        for name in ("TRANSLATIONS", "ENGLISH_FOR_SPANISH_SOURCE"):
            for msgid, msgstr in getattr(af_i18n_es, name).items():
                self.assertEqual(sorted(PLACEHOLDER.findall(msgid)),
                                 sorted(PLACEHOLDER.findall(msgstr)), msgid)
                self.assertEqual(msgid[:1].isspace(), msgstr[:1].isspace(), msgid)
                self.assertEqual(msgid[-1:].isspace(), msgstr[-1:].isspace(), msgid)
                self.assertEqual(msgid.endswith(":"), msgstr.endswith(":"), msgid)

    def test_core_terminology_is_consistent(self):
        tr = af_i18n_es.TRANSLATIONS
        expected = {
            "Wall": "Muro", "Slab": "Losa", "Floor": "Piso", "Roof": "Techo",
            "Stair": "Escalera", "Ramp Slope": "Pendiente de rampa", "Footing": "Zapata",
            "Truss": "Cercha", "Fence": "Cerca", "Width": "Ancho",
            "Height": "Altura", "Thickness": "Espesor",
        }
        for msgid, msgstr in expected.items():
            self.assertEqual(tr.get(msgid), msgstr, msgid)

    def test_disambiguated_source_labels_exist(self):
        """Short labels renamed so one msgid has one meaning (no contexts in 3.3)."""
        electrical = (ROOT / "af_electrical.py").read_text(encoding="utf-8")
        furniture = (ROOT / "af_furniture.py").read_text(encoding="utf-8")
        window = (ROOT / "af_window.py").read_text(encoding="utf-8")
        self.assertIn('"Recessed in Wall"', electrical)
        self.assertIn('"Top Shape"', furniture)
        self.assertIn('"Open Shutters"', window)
        self.assertIn('"Close Shutters"', window)
        for msgid in ("Recessed in Wall", "Top Shape", "Open Shutters",
                      "Close Shutters"):
            self.assertIn(msgid, af_i18n_es.TRANSLATIONS)


class PureHelperTests(unittest.TestCase):

    def test_messages_per_language(self):
        self.assertEqual(af_i18n.messages('ES')["Wall"], "Muro")
        self.assertEqual(af_i18n.messages('EN')["Mesa de comedor"], "Dining Table")
        with self.assertRaises(ValueError):
            af_i18n.messages('FR')

    def test_tr_passes_unknown_strings_through(self):
        self.assertEqual(af_i18n.tr("Wall", 'ES'), "Muro")
        self.assertEqual(af_i18n.tr("not a ui string", 'ES'), "not a ui string")
        self.assertEqual(af_i18n.tr("", 'ES'), "")

    def test_translation_table_uses_default_and_operator_contexts(self):
        table = af_i18n.translation_table('ES')
        self.assertEqual(table[("*", "Wall")], "Muro")
        self.assertEqual(table[("Operator", "Wall")], "Muro")
        self.assertEqual(len(table), len(af_i18n_es.TRANSLATIONS) * 2)
        for (context, msgid), msgstr in table.items():
            self.assertIn(context, af_i18n.TRANSLATION_CONTEXTS)
            self.assertIsInstance(msgid, str)
            self.assertIsInstance(msgstr, str)

    def test_locale_keys_cover_blender_lookup_order(self):
        keys = af_i18n.locale_keys("fr_FR")
        self.assertEqual(keys[0], "fr_FR")
        self.assertIn("fr", keys)
        for key in ("en_US", "es", "es_ES"):
            self.assertIn(key, keys)
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(af_i18n.locale_keys("")[0], "en_US")

    def test_blender_translations_share_one_table(self):
        translations = af_i18n.blender_translations('ES', "en_US")
        tables = list(translations.values())
        self.assertTrue(all(t is tables[0] for t in tables))
        self.assertEqual(translations["en_US"][("*", "Add Roof")], "Añadir techo")

    def test_language_items_match_addon_preferences(self):
        source = (ROOT / "__init__.py").read_text(encoding="utf-8")
        for identifier, label, description in af_i18n.LANGUAGE_ITEMS:
            self.assertIn("('{}', \"{}\", \"{}\")".format(identifier, label, description),
                          source)
        self.assertIn("update=_on_language_update", source)
        self.assertIn("i18n.apply_language(i18n.current_language(__name__), __name__)",
                      source)
        self.assertIn("i18n.release(__name__)", source)


class BlenderIntegrationTests(unittest.TestCase):
    """apply_language/release against the bpy stand-in."""

    def setUp(self):
        self.bpy = blender_stub.install_ui_context(addon_name=ADDON)
        af_i18n.release(ADDON)
        self.area = self.bpy.context.window_manager.windows[0].screen.areas[0]

    def tearDown(self):
        af_i18n.release(ADDON)

    def test_spanish_translates_the_addon_in_an_english_blender(self):
        self.assertTrue(af_i18n.apply_language('ES', ADDON))
        tr = self.bpy.app.translations
        self.assertEqual(tr.pgettext_iface("Add Roof"), "Añadir techo")
        self.assertEqual(tr.pgettext_iface("Add Roof", "Operator"), "Añadir techo")
        self.assertEqual(tr.pgettext_tip("Force regeneration of the stair"),
                         "Forzar la regeneración de la escalera")
        self.assertTrue(af_i18n.is_registered())
        self.assertGreater(self.area.redraws, 0)

    def test_blender_flags_are_forced_and_restored(self):
        view = self.bpy.context.preferences.view
        prefs = self.bpy.context.preferences.addons[ADDON].preferences
        self.assertFalse(view.use_translate_interface)
        af_i18n.apply_language('ES', ADDON)
        self.assertTrue(view.use_translate_interface)
        self.assertTrue(view.use_translate_tooltips)
        self.assertTrue(prefs.i18n_forced_use_translate_interface)
        # tooltips were already on: must not be claimed by the addon
        self.assertFalse(prefs.i18n_forced_use_translate_tooltips)
        af_i18n.release(ADDON)
        self.assertFalse(view.use_translate_interface)
        self.assertTrue(view.use_translate_tooltips)
        self.assertFalse(prefs.i18n_forced_use_translate_interface)
        self.assertFalse(af_i18n.is_registered())

    def test_user_enabled_flags_are_left_alone(self):
        bpy = blender_stub.install_ui_context(addon_name=ADDON, translate_interface=True)
        af_i18n.apply_language('ES', ADDON)
        af_i18n.release(ADDON)
        self.assertTrue(bpy.context.preferences.view.use_translate_interface)

    def test_switching_language_replaces_the_catalogue(self):
        tr = self.bpy.app.translations
        af_i18n.apply_language('ES', ADDON)
        af_i18n.apply_language('EN', ADDON)  # must not raise "already registered"
        self.assertEqual(tr.pgettext_iface("Add Roof"), "Add Roof")
        self.assertEqual(tr.pgettext_iface("Mesa de comedor"), "Dining Table")
        self.assertEqual(len(tr.registered), 1)

    def test_english_mode_translates_spanish_sources_only(self):
        af_i18n.apply_language('EN', ADDON)
        tr = self.bpy.app.translations
        self.assertEqual(tr.pgettext_iface("Nochero"), "Nightstand")
        self.assertEqual(tr.pgettext_iface("Wall"), "Wall")

    def test_works_when_blender_runs_in_spanish_or_another_language(self):
        for locale in ("es", "es_ES", "fr_FR", "de_DE"):
            bpy = blender_stub.install_ui_context(locale=locale, addon_name=ADDON,
                                                  translate_interface=True)
            af_i18n.release(ADDON)
            af_i18n.apply_language('ES', ADDON)
            self.assertEqual(bpy.app.translations.pgettext_iface("Add Roof"),
                             "Añadir techo", locale)
            af_i18n.release(ADDON)

    def test_current_language_falls_back_to_english(self):
        prefs = self.bpy.context.preferences.addons[ADDON].preferences
        prefs.language = 'ES'
        self.assertEqual(af_i18n.current_language(ADDON), 'ES')
        prefs.language = 'XX'
        self.assertEqual(af_i18n.current_language(ADDON), 'EN')
        self.assertEqual(af_i18n.current_language("missing"), 'EN')

    def test_unknown_language_is_applied_as_english(self):
        self.assertTrue(af_i18n.apply_language('XX', ADDON))
        self.assertEqual(self.bpy.app.translations.pgettext_iface("Nochero"),
                         "Nightstand")


if __name__ == "__main__":
    unittest.main()
