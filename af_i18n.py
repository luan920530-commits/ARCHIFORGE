# -*- coding: utf-8 -*-

# ╔══════════════════════════════════════════════════════════╗
# ║              ARCHIFORGE — af_i18n.py                    ║
# ║              Idioma del addon (English / Español)       ║
# ║              GPL v3 — ArchiForge Devs                   ║
# ╚══════════════════════════════════════════════════════════╝

# <pep8 compliant>

"""Addon-level language switch, independent of Blender's UI language.

Blender translates every label, property name, enum item and tooltip
through ``bpy.app.translations``: for each ``(context, msgid)`` it first
asks its own catalogue for the active locale and then the dictionaries
registered by addons. ArchiForge therefore registers the catalogue of
``af_i18n_es.py`` under the locale Blender is currently using (``en_US``
included), so the addon can show Spanish while the rest of Blender stays
in English, or English while Blender runs in Spanish for the strings
Blender itself does not translate.

Two Blender preferences gate those lookups: *Translate Interface* and
*Translate Tooltips*. Blender switches them off when its language is
English, so :func:`apply_language` turns them on while a catalogue is
registered and :func:`release` restores them.

The pure helpers (table building, ``tr``) have no ``bpy`` dependency and
are covered by ``tests/test_i18n.py``.
"""

try:
    import bpy
except ImportError:  # pragma: no cover - test environment without Blender
    bpy = None

try:
    from . import af_i18n_es as _catalogue
except ImportError:  # pragma: no cover - imported outside the package
    import af_i18n_es as _catalogue

LANGUAGE_ENGLISH = 'EN'
LANGUAGE_SPANISH = 'ES'
DEFAULT_LANGUAGE = LANGUAGE_ENGLISH
LANGUAGE_ITEMS = (
    (LANGUAGE_ENGLISH, "English", "Show ArchiForge in English"),
    (LANGUAGE_SPANISH, "Español", "Mostrar ArchiForge en español"),
)
LANGUAGES = tuple(item[0] for item in LANGUAGE_ITEMS)

# Python-defined panels, menus and properties use the default context;
# operator labels and button texts use Blender's operator context.
TRANSLATION_CONTEXTS = ("*", "Operator")

# Locale keys Blender may try besides the active one (full locale,
# language+country and bare language are all looked up).
FALLBACK_LOCALES = ("en_US", "en", "es_ES", "es")

# Blender view preferences that must be enabled for lookups to happen.
BLENDER_TRANSLATION_FLAGS = ("use_translate_interface", "use_translate_tooltips")

_messages_cache = {}
_registered_name = None


# ════════════════════════════════════════════════════════════
#  Pure helpers (no bpy)
# ════════════════════════════════════════════════════════════
def messages(language):
    """``{msgid: msgstr}`` for ``language`` (``'EN'`` or ``'ES'``).

    Spanish mode translates the English sources; English mode translates
    the few source strings that are written in Spanish (room asset
    catalogue, some presets). Unknown languages raise ``ValueError``.
    """
    if language not in LANGUAGES:
        raise ValueError("Unknown ArchiForge language: {!r}".format(language))
    table = _messages_cache.get(language)
    if table is None:
        if language == LANGUAGE_SPANISH:
            table = dict(_catalogue.TRANSLATIONS)
        else:
            table = dict(_catalogue.ENGLISH_FOR_SPANISH_SOURCE)
        _messages_cache[language] = table
    return table


def tr(text, language):
    """Translate ``text`` for ``language``; unknown strings pass through."""
    if not text:
        return text
    return messages(language).get(text, text)


def translation_table(language):
    """Blender-style ``{(context, msgid): msgstr}`` for ``language``."""
    table = {}
    for msgid, msgstr in messages(language).items():
        for context in TRANSLATION_CONTEXTS:
            table[(context, msgid)] = msgstr
    return table


def locale_keys(locale):
    """Every dictionary key Blender might try for ``locale``."""
    keys = []
    for key in (locale, (locale or "").split("_")[0], *FALLBACK_LOCALES):
        if key and key not in keys:
            keys.append(key)
    return tuple(keys)


def blender_translations(language, locale):
    """``{locale_key: table}`` ready for ``bpy.app.translations.register``.

    The same table object is shared by every key, so whichever key
    Blender resolves for the active locale yields identical results.
    """
    table = translation_table(language)
    return {key: table for key in locale_keys(locale)}


# ════════════════════════════════════════════════════════════
#  Blender integration
# ════════════════════════════════════════════════════════════
def _view_preferences():
    try:
        return bpy.context.preferences.view
    except Exception:  # noqa: BLE001 - no context during startup
        return None


def _addon_preferences(addon_name):
    try:
        addon = bpy.context.preferences.addons.get(addon_name)
    except Exception:  # noqa: BLE001
        return None
    return getattr(addon, "preferences", None) if addon else None


def current_language(addon_name):
    """Language stored in the addon preferences (default English)."""
    prefs = _addon_preferences(addon_name)
    language = getattr(prefs, "language", DEFAULT_LANGUAGE) if prefs else DEFAULT_LANGUAGE
    return language if language in LANGUAGES else DEFAULT_LANGUAGE


def blender_flags_enabled():
    """True when Blender will consult addon translations for UI text."""
    view = _view_preferences()
    if view is None:
        return False
    return all(getattr(view, flag, False) for flag in BLENDER_TRANSLATION_FLAGS)


def _enable_blender_flags(addon_name):
    """Turn the translation flags on, remembering which ones we changed."""
    view = _view_preferences()
    prefs = _addon_preferences(addon_name)
    if view is None:
        return
    for flag in BLENDER_TRANSLATION_FLAGS:
        if getattr(view, flag, True):
            continue
        try:
            setattr(view, flag, True)
        except Exception:  # noqa: BLE001 - read-only during some events
            continue
        if prefs is not None and hasattr(prefs, "i18n_forced_" + flag):
            setattr(prefs, "i18n_forced_" + flag, True)


def _restore_blender_flags(addon_name):
    """Switch off only the flags this addon switched on."""
    view = _view_preferences()
    prefs = _addon_preferences(addon_name)
    if view is None or prefs is None:
        return
    for flag in BLENDER_TRANSLATION_FLAGS:
        marker = "i18n_forced_" + flag
        if getattr(prefs, marker, False):
            try:
                setattr(view, flag, False)
            except Exception:  # noqa: BLE001
                pass
            setattr(prefs, marker, False)


def _redraw_all():
    try:
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()
    except Exception:  # noqa: BLE001 - no window manager (background)
        pass


def release(addon_name, restore_flags=True):
    """Unregister the addon catalogue (safe to call when not registered)."""
    global _registered_name
    if bpy is None:
        return
    try:
        bpy.app.translations.unregister(addon_name)
    except Exception:  # noqa: BLE001
        pass
    _registered_name = None
    if restore_flags:
        _restore_blender_flags(addon_name)


def apply_language(language, addon_name):
    """Register the catalogue for ``language`` and refresh the UI.

    Returns ``True`` when Blender accepted the dictionary. Both languages
    register a table (English mode translates the Spanish-written
    catalogue), so the Blender translation flags are enabled in both.
    """
    global _registered_name
    if bpy is None:
        return False
    if language not in LANGUAGES:
        language = DEFAULT_LANGUAGE
    release(addon_name, restore_flags=False)
    locale = getattr(bpy.app.translations, "locale", "") or "en_US"
    try:
        bpy.app.translations.register(
            addon_name, blender_translations(language, locale))
    except Exception as err:  # noqa: BLE001 - never break the addon
        print("[ArchiForge] i18n: could not register translations: {}".format(err))
        return False
    _registered_name = addon_name
    _enable_blender_flags(addon_name)
    _redraw_all()
    return True


def is_registered():
    return _registered_name is not None
