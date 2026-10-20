# -*- coding: utf-8 -*-

# ╔══════════════════════════════════════════════════════════╗
# ║              ARCHIFORGE — af_units.py                   ║
# ║              Sistema de unidades del addon              ║
# ║              GPL v3 — ArchiForge Devs                   ║
# ╚══════════════════════════════════════════════════════════╝

# <pep8 compliant>

"""Pure helpers behind the *Unit System* preference.

ArchiForge models in metres internally. The preference does two things:

* It is pushed to the ``unit_settings`` of the open scenes, so every
  ``unit='LENGTH'`` property of the addon is displayed and edited by
  Blender in metres or in feet/inches.
* The quantity takeoff (``af_quantities_io``) converts lengths, areas and
  volumes with the factors below and labels the units accordingly.

No ``bpy`` import: everything here is covered by ``tests/test_units.py``.
"""

METRIC = 'METRIC'
IMPERIAL = 'IMPERIAL'
UNIT_SYSTEMS = (METRIC, IMPERIAL)
DEFAULT_UNIT_SYSTEM = METRIC

UNIT_SYSTEM_ITEMS = (
    (METRIC, "Metric (m/cm)", "Use meters and centimeters"),
    (IMPERIAL, "Imperial (ft/in)", "Use feet and inches"),
)

FOOT = 0.3048          # metres per international foot
INCH = FOOT / 12.0

_LENGTH_FACTOR = {METRIC: 1.0, IMPERIAL: 1.0 / FOOT}
_LENGTH_UNIT = {METRIC: "m", IMPERIAL: "ft"}
_AREA_UNIT = {METRIC: "m2", IMPERIAL: "ft2"}
_VOLUME_UNIT = {METRIC: "m3", IMPERIAL: "ft3"}

# Values Blender expects in ``scene.unit_settings`` for each system.
SCENE_UNIT_SETTINGS = {
    METRIC: {"system": 'METRIC', "length_unit": 'METERS',
             "mass_unit": 'KILOGRAMS'},
    IMPERIAL: {"system": 'IMPERIAL', "length_unit": 'FEET',
               "mass_unit": 'POUNDS'},
}


def normalize(system):
    """Return a valid system identifier (unknown values fall back to metric)."""
    return system if system in UNIT_SYSTEMS else DEFAULT_UNIT_SYSTEM


def length_factor(system):
    return _LENGTH_FACTOR[normalize(system)]


def length_unit(system):
    return _LENGTH_UNIT[normalize(system)]


def area_unit(system):
    return _AREA_UNIT[normalize(system)]


def volume_unit(system):
    return _VOLUME_UNIT[normalize(system)]


def convert_length(meters, system):
    return float(meters) * length_factor(system)


def convert_area(square_meters, system):
    return float(square_meters) * length_factor(system) ** 2


def convert_volume(cubic_meters, system):
    return float(cubic_meters) * length_factor(system) ** 3


def feet_and_inches(meters, inch_precision=0.5):
    """Human reading of a metric length as feet and inches, e.g. ``9' 6"``.

    Inches are rounded to ``inch_precision`` (half an inch by default) and
    carried into the feet when they round up to twelve.
    """
    total_inches = float(meters) / INCH
    step = max(float(inch_precision), 1e-9)
    total_inches = round(total_inches / step) * step
    feet = int(total_inches // 12)
    inches = total_inches - feet * 12
    if inches >= 12.0 - 1e-9:
        feet += 1
        inches = 0.0
    if abs(inches - round(inches)) < 1e-9:
        inch_text = "{:d}".format(int(round(inches)))
    else:
        inch_text = "{:.1f}".format(inches)
    return "{}' {}\"".format(feet, inch_text)


def scene_unit_settings(system):
    """Copy of the ``unit_settings`` values for ``system``."""
    return dict(SCENE_UNIT_SETTINGS[normalize(system)])


def apply_to_scene(scene, system):
    """Write the unit system into ``scene.unit_settings``.

    ``scale_length`` is never touched: changing it would rescale every
    existing object. Returns True when at least one setting was written.
    """
    settings = getattr(scene, "unit_settings", None)
    if settings is None:
        return False
    written = False
    for attr, value in scene_unit_settings(system).items():
        try:
            setattr(settings, attr, value)
            written = True
        except Exception:  # noqa: BLE001 - enum not available in this build
            continue
    return written


def apply_to_scenes(scenes, system):
    """Apply :func:`apply_to_scene` to every scene; returns the count."""
    return sum(1 for scene in scenes if apply_to_scene(scene, system))


def scene_system(scene):
    """Unit system currently set on ``scene`` (``'METRIC'`` when unknown)."""
    settings = getattr(scene, "unit_settings", None)
    return normalize(getattr(settings, "system", METRIC))
