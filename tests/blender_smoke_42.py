# SPDX-License-Identifier: GPL-3.0-or-later
"""Smoke test of ArchiForge installed as an EXTENSION inside a real Blender 4.2+.

Unlike the ``unittest`` suite (which runs on a ``bpy`` stub), this script needs
a real Blender and exercises the exact path a user follows on 4.2+:

1. install the built zip with ``extensions.package_install_files`` — the same
   operator behind *Preferences ▸ Add-ons ▸ Install from Disk*;
2. check that Blender enabled ``bl_ext.<repo>.archiforge`` (no ``bl_info``,
   module name provided by the extension system), that every panel, operator,
   preference, icon and translation table is in place;
3. run every ``archiforge.*`` operator against a suitable target object and
   fail on any exception that is not a background-mode limitation;
4. disable + re-enable the extension (register/unregister round trip) and
   uninstall it unless ``--keep`` is given.

Usage::

    blender -b --python-exit-code 1 --python tests/blender_smoke_42.py -- \
        --zip dist/archiforge-1.14.1.zip [--repo user_default] [--keep] \
        [--report smoke_report.json]

    # or with the PyPI ``bpy`` module (same Blender, no window system):
    python tests/blender_smoke_42.py --zip dist/archiforge-1.14.1.zip

The exit code is 0 only when nothing failed.
"""

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
import tomllib
import traceback
import zipfile

PACKAGE_ID = "archiforge"
EXPECTED_ICONS = 112
MIN_OPERATORS = 120
MIN_PANELS = 30

# Sub-panels / features that broke silently in real Blender before v1.14.1.
REQUIRED_TYPES = (
    "ARCHIFORGE_PT_create",
    "ARCHIFORGE_PT_tools",
    "ARCHIFORGE_PT_manipulator",   # child of ARCHIFORGE_PT_tools
    "ARCHIFORGE_PT_snap_tools",
    "ARCHIFORGE_PT_snap",          # child of ARCHIFORGE_PT_snap_tools
    "ARCHIFORGE_PT_room_asset",
    "ARCHIFORGE_PT_materials",
    "ARCHIFORGE_PT_material_active",
    "ARCHIFORGE_PT_presets",
    "ARCHIFORGE_PT_quantities",
    "ARCHIFORGE_PT_sets",
    "ARCHIFORGE_PT_annotations",
)
REQUIRED_PREFS = ("language", "unit_system", "procedural_materials",
                  "auto_boolean", "auto_material", "create_submenu")

# Operators that create geometry from an empty scene with default settings.
# The value is the name under which their first created object is remembered.
GENERATORS = (
    ("wall", "wall"), ("slab", "slab"), ("floor", "floor"),
    ("roof_add", "roof"), ("stair", "stair"), ("stairs", "stair_alias"),
    ("door", "door"), ("window", "window"), ("opening", "opening"),
    ("structure", "structure"), ("truss", "truss"), ("fence", "fence"),
    ("furniture", "furniture"), ("kitchen", "kitchen"),
    ("bathroom", "bathroom"), ("electrical", "electrical"), ("decor", "decor"),
    ("room_asset", "room_asset"), ("north_arrow", "north"),
    ("grid_axes", "axes"), ("rp_create", "rp"),
    ("set_bathroom", "set_bathroom"), ("set_apartment", "set_apartment"),
)

# Operators that need a 3D viewport, the mouse or a popup: not runnable in
# background mode, so they are reported as skipped instead of failed.
INTERACTIVE = {
    "wall_draw", "floor_draw", "slab_draw", "dimension_draw",
    "door_place", "window_place", "roof_place", "pie_call",
    "control_center", "preset_menu_invoke", "door_preset_menu",
    "window_preset_menu", "floor_preset_menu", "roof_preset_menu",
    "stair_preset_menu", "fence_preset_menu", "render_preview",
    "view_to_camera", "rp_center_view",
}
# Runnable, but a failure caused by the missing viewport is tolerated.
VIEWPORT_TOLERANT = {"manipulator_toggle", "dimensions_toggle", "camera_auto",
                     "snap_toggle", "snap_sync", "snap_set_grid", "set_grid"}

# Which remembered object each operator prefix wants as the active object.
TARGET_BY_PREFIX = (
    ("wall_", "wall"), ("slab_", "slab"), ("floor_", "floor"),
    ("roof_", "roof"), ("stair_", "stair"), ("door_", "door"),
    ("window_", "window"), ("opening_", "opening"),
    ("structure_", "structure"), ("truss_", "truss"), ("fence_", "fence"),
    ("furniture_", "furniture"), ("kitchen_", "kitchen"),
    ("bathroom_", "bathroom"), ("electrical_", "electrical"),
    ("decor_", "decor"), ("room_asset_", "room_asset"), ("rp_", "rp"),
    ("boolean_", "wall"), ("auto_boolean", "wall"), ("assign_", "wall"),
    ("dimension_", "wall"), ("preset_", "wall"), ("quantities_", "wall"),
)
FROM_CURVE = {"fence_from_curve", "floor_from_curve", "slab_from_curve"}
# Presets have a natural order: save → list → export → import → load → delete.
PRESET_ORDER = ("preset_save", "preset_refresh", "preset_export",
                "preset_import", "preset_load", "preset_delete")
# Operators that need an explicit argument to do anything meaningful.
OPERATOR_KWARGS = {
    "assign_material": {"material_name": "AF.Wall.Plaster"},
    "assign_from_catalog": {"material_name": "AF.Wall.Plaster"},
}
# ``load_material_library`` needs a .blend with materials; none is shipped.
NEEDS_EXTERNAL_FILE = {"load_material_library"}


class Report:
    def __init__(self):
        self.rows = []
        self.started = time.time()

    def add(self, section, name, status, detail=""):
        detail = " ".join(str(detail).split())
        self.rows.append({"section": section, "name": name,
                          "status": status, "detail": detail[:400]})
        print(f"[{status:4s}] {section:9s} {name}" + (f" — {detail[:200]}" if detail else ""),
              flush=True)

    def ok(self, section, name, condition, detail=""):
        self.add(section, name, "PASS" if condition else "FAIL", detail)
        return bool(condition)

    def counts(self):
        out = {"PASS": 0, "FAIL": 0, "SKIP": 0}
        for row in self.rows:
            out[row["status"]] = out.get(row["status"], 0) + 1
        return out


def _parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--zip", required=True, help="extension zip built with `blender --command extension build`")
    parser.add_argument("--repo", default="user_default", help="local extension repository module (default: user_default)")
    parser.add_argument("--keep", action="store_true", help="leave the extension installed and enabled")
    parser.add_argument("--report", default="", help="write the JSON report to this path")
    return parser.parse_args(argv)


def _manifest_from_zip(path):
    with zipfile.ZipFile(path) as zf:
        return tomllib.loads(zf.read("blender_manifest.toml").decode("utf-8"))


def _clear_scene():
    import bpy
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for block in (bpy.data.meshes, bpy.data.curves, bpy.data.lights,
                  bpy.data.cameras, bpy.data.collections):
        for datablock in list(block):
            if datablock.users == 0:
                block.remove(datablock)
    bpy.context.view_layer.update()


def _activate(objects):
    import bpy
    for obj in bpy.data.objects:
        try:
            obj.select_set(False)
        except RuntimeError:  # not in this view layer
            pass
    objects = [o for o in objects if o is not None and o.name in bpy.data.objects]
    for obj in objects:
        try:
            obj.select_set(True)
        except RuntimeError:
            pass
    bpy.context.view_layer.objects.active = objects[0] if objects else None
    return objects


def _select_user_preset(settings):
    """Point ``af_presets.active_index`` at the first user (file-backed) preset."""
    for index, item in enumerate(settings.items):
        if getattr(item, "file_path", ""):
            settings.active_index = index
            return True
    return False


def _call(op_name, **kwargs):
    """Run ``bpy.ops.archiforge.<op_name>`` → (result_set | None, error_text)."""
    import bpy
    op = getattr(bpy.ops.archiforge, op_name)
    try:
        if not op.poll():
            return None, "poll"
        return op(**kwargs), ""
    except Exception as ex:  # noqa: BLE001 - the whole point is to catch them
        return None, f"{type(ex).__name__}: {ex}"


def main():
    args = _parse_args()
    report = Report()

    import bpy
    import addon_utils

    module_name = f"bl_ext.{args.repo}.{PACKAGE_ID}"
    zip_path = os.path.abspath(args.zip)
    manifest = _manifest_from_zip(zip_path)
    print(f"Blender {bpy.app.version_string} ({'background' if bpy.app.background else 'ui'}), "
          f"python {sys.version.split()[0]}, zip {os.path.basename(zip_path)} "
          f"(manifest {manifest['id']} {manifest['version']})", flush=True)

    report.ok("env", "Blender >= 4.2.0 (extensions platform)", bpy.app.version >= (4, 2, 0),
              bpy.app.version_string)
    report.ok("env", f"repository '{args.repo}' configured",
              any(r.module == args.repo for r in bpy.context.preferences.extensions.repos))

    # ── 1. Install from disk (same operator as the Preferences button) ──────
    if module_name in sys.modules or addon_utils.check(module_name)[1]:
        addon_utils.disable(module_name, default_set=True)
    repo_dir = next(r.directory for r in bpy.context.preferences.extensions.repos
                    if r.module == args.repo)
    pkg_dir = os.path.join(repo_dir, PACKAGE_ID)
    if os.path.isdir(pkg_dir):
        shutil.rmtree(pkg_dir)
    try:
        result = bpy.ops.extensions.package_install_files(
            filepath=zip_path, repo=args.repo, enable_on_install=True)
    except Exception as ex:  # noqa: BLE001
        result = f"{type(ex).__name__}: {ex}"
    report.ok("install", "extensions.package_install_files", result == {'FINISHED'}, result)
    report.ok("install", "package extracted into the repository",
              os.path.isfile(os.path.join(pkg_dir, "blender_manifest.toml")), pkg_dir)

    # ── 2. Registration state ───────────────────────────────────────────────
    is_default, is_loaded = addon_utils.check(module_name)
    mod = sys.modules.get(module_name)
    if not report.ok("register", f"{module_name} enabled and loaded",
                     is_default and is_loaded and mod is not None,
                     f"default={is_default} loaded={is_loaded}"):
        _finish(report, args, module_name, pkg_dir)
        return

    report.ok("register", "Blender removed bl_info (extension mode) and register() survived",
              not hasattr(mod, "bl_info"))
    report.ok("register", "ADDON_VERSION_STR matches the manifest version",
              getattr(mod, "ADDON_VERSION_STR", None) == manifest["version"],
              f"{getattr(mod, 'ADDON_VERSION_STR', None)} vs {manifest['version']}")
    op_names = sorted(n for n in dir(bpy.ops.archiforge) if not n.startswith("_"))
    report.ok("register", f"operators registered ({len(op_names)})", len(op_names) >= MIN_OPERATORS)
    panels = [n for n in dir(bpy.types) if n.startswith("ARCHIFORGE_PT_")]
    report.ok("register", f"panels registered ({len(panels)})", len(panels) >= MIN_PANELS)
    for type_name in REQUIRED_TYPES:
        report.ok("register", f"bpy.types.{type_name}", hasattr(bpy.types, type_name))

    # ── 3. Preferences, icons, translations ────────────────────────────────
    addon_entry = bpy.context.preferences.addons.get(module_name)
    prefs = getattr(addon_entry, "preferences", None)
    report.ok("prefs", "AddonPreferences reachable through __package__", prefs is not None)
    if prefs is not None:
        for name in REQUIRED_PREFS:
            report.ok("prefs", f"preference '{name}'", hasattr(prefs, name))
        try:
            prefs.unit_system = 'IMPERIAL'
            prefs.unit_system = 'METRIC'
            report.add("prefs", "unit_system switch METRIC↔IMPERIAL", "PASS")
        except Exception as ex:  # noqa: BLE001
            report.add("prefs", "unit_system switch METRIC↔IMPERIAL", "FAIL", ex)

    icons = {}
    try:
        icons = mod.get_icons() or {}
    except Exception as ex:  # noqa: BLE001
        report.add("icons", "get_icons()", "FAIL", ex)
    report.ok("icons", f"preview icons loaded ({len(icons)})", len(icons) == EXPECTED_ICONS)
    try:
        sizes = [tuple(icons[k].image_size) for k in icons]
        report.ok("icons", "every preview decoded to a 128x128 PNG",
                  sizes and all(sz == (128, 128) for sz in sizes),
                  sorted(set(sizes))[:3])
        if bpy.app.background:
            # BKE_icon_preview_ensure() returns 0 in background mode by design.
            report.add("icons", "icon_id assigned", "SKIP", "icon ids are only allocated with a UI")
        else:
            bad = [k for k in icons if int(icons[k].icon_id) <= 0]
            report.ok("icons", "every icon has a valid icon_id", not bad, bad[:5])
    except Exception as ex:  # noqa: BLE001
        report.add("icons", "preview inspection", "FAIL", ex)

    if prefs is not None:
        try:
            i18n = mod.af_i18n
            msgid, msgstr = next(iter(i18n.messages('ES').items()))
            view = bpy.context.preferences.view
            if not bpy.app.translations.locale:
                # Headless builds without datafiles/locale report an empty
                # locale; pin an explicit language when the build offers one.
                languages = {item.identifier for item in view.bl_rna.properties["language"].enum_items}
                if "en_US" in languages:
                    view.language = 'en_US'
            prefs.language = 'ES'
            translated = bpy.app.translations.pgettext_iface(msgid)
            report.ok("i18n", "tr_report() follows the preference (ES)",
                      i18n.tr_report(msgid) == msgstr)
            prefs.language = 'EN'
            back = bpy.app.translations.pgettext_iface(msgid)
            report.ok("i18n", "tr_report() follows the preference (EN)",
                      i18n.tr_report(msgid) == msgid)
            if not bpy.app.translations.locale:
                report.add("i18n", "ES switch translates the UI (bpy.app.translations)", "SKIP",
                           "this Blender build has no locale/translation catalogs")
            else:
                report.ok("i18n", "ES switch translates the UI (bpy.app.translations)",
                          translated == msgstr,
                          f"locale={bpy.app.translations.locale!r} {msgid!r} -> {translated!r}")
                report.ok("i18n", "EN switch restores the source strings", back == msgid,
                          f"{msgid!r} -> {back!r}")
        except Exception as ex:  # noqa: BLE001
            report.add("i18n", "language switch", "FAIL", traceback.format_exc(limit=2) or ex)

    # ── 4. Operators ────────────────────────────────────────────────────────
    _clear_scene()
    bpy.context.scene.cursor.location = (0.0, 0.0, 0.0)
    targets = {}
    ran = set()
    for op_name, key in GENERATORS:
        if op_name not in op_names:
            report.add("ops", f"archiforge.{op_name}", "FAIL", "operator not registered")
            continue
        _activate([])
        before = set(bpy.data.objects)
        result, error = _call(op_name)
        ran.add(op_name)
        created = [o for o in bpy.data.objects if o not in before]
        if error == "poll":
            report.add("ops", f"archiforge.{op_name}", "FAIL", "poll() refused an empty scene")
        elif error:
            report.add("ops", f"archiforge.{op_name}", "FAIL", error)
        else:
            report.ok("ops", f"archiforge.{op_name}", result == {'FINISHED'} and created,
                      f"{result} created={len(created)}")
        if created and key not in targets:
            active = bpy.context.view_layer.objects.active
            targets[key] = active if active in created else created[0]
        if created and op_name in ("north_arrow", "grid_axes"):
            kinds = {o.get("af_annotation") for o in created} - {None}
            report.ok("ops", f"archiforge.{op_name} tags objects with af_annotation",
                      bool(kinds), sorted(kinds))
    targets.setdefault("stair", targets.get("stair_alias"))

    curve = None
    try:
        bpy.ops.curve.primitive_bezier_circle_add(radius=3.0)
        curve = bpy.context.view_layer.objects.active
    except Exception as ex:  # noqa: BLE001
        report.add("ops", "bezier circle for *_from_curve", "SKIP", ex)

    tmp_dir = tempfile.mkdtemp(prefix="archiforge_smoke_")
    file_kwargs = dict(OPERATOR_KWARGS)
    file_kwargs.update({
        "quantities_export": {"filepath": os.path.join(tmp_dir, "quantities.csv")},
        "preset_export": {"filepath": os.path.join(tmp_dir, "presets.json")},
        "preset_import": {"filepath": os.path.join(tmp_dir, "presets.json")},
    })
    try:
        presets = bpy.context.scene.af_presets
        presets.active_type = 'WALL'
        presets.preset_name = "Smoke test"
    except Exception as ex:  # noqa: BLE001
        report.add("ops", "scene.af_presets settings", "FAIL", ex)

    ordered = [n for n in PRESET_ORDER if n in op_names]
    ordered += [n for n in op_names if n not in ordered]
    for op_name in ordered:
        if op_name in ran:
            continue
        label = f"archiforge.{op_name}"
        if op_name in INTERACTIVE:
            report.add("ops", label, "SKIP", "interactive (viewport / mouse / popup)")
            continue
        if op_name in NEEDS_EXTERNAL_FILE:
            report.add("ops", label, "SKIP", "needs an external .blend material library")
            continue
        if op_name in FROM_CURVE:
            if curve is None:
                report.add("ops", label, "SKIP", "no curve available")
                continue
            _activate([curve])
        else:
            key = next((k for p, k in TARGET_BY_PREFIX if op_name.startswith(p)), None)
            chosen = [targets.get(key)] if key else []
            if op_name in ("door_apply_boolean", "window_apply_boolean",
                           "boolean_add_cutter", "auto_boolean"):
                chosen = [targets.get("wall"), targets.get("door")]
            if op_name == "wall_from_slab":
                chosen = [targets.get("slab")]
            if op_name in ("floor_from_wall", "slab_from_wall"):
                chosen = [targets.get("wall")]
            if op_name == "preset_import" and not os.path.isfile(file_kwargs["preset_import"]["filepath"]):
                report.add("ops", label, "SKIP", "preset_export did not produce a file")
                continue
            if op_name in ("preset_export", "preset_load", "preset_delete"):
                # Built-in presets have no file: operate on the one saved above.
                _select_user_preset(bpy.context.scene.af_presets)
            _activate([o for o in chosen if o])
        result, error = _call(op_name, **file_kwargs.get(op_name, {}))
        ran.add(op_name)
        if error == "poll":
            report.add("ops", label, "SKIP", "poll() False with this selection")
        elif error:
            if op_name in VIEWPORT_TOLERANT:
                report.add("ops", label, "SKIP", f"background limitation: {error}")
            else:
                report.add("ops", label, "FAIL", error)
        else:
            report.ok("ops", label, result in ({'FINISHED'}, {'CANCELLED'}), str(result))
        if op_name.endswith("_export") and not error:
            path = file_kwargs[op_name]["filepath"]
            report.ok("ops", f"{label} wrote {os.path.basename(path)}",
                      os.path.isfile(path) and os.path.getsize(path) > 0)

    rebuilt = [o for o in bpy.data.objects if o.type == 'MESH']
    report.ok("ops", f"scene still holds the generated meshes ({len(rebuilt)})", len(rebuilt) >= 20)
    shutil.rmtree(tmp_dir, ignore_errors=True)

    # ── 5. Register / unregister round trip ─────────────────────────────────
    errors = []
    addon_utils.disable(module_name, default_set=True, handle_error=errors.append)
    report.ok("lifecycle", "disable() without exceptions", not errors, errors[:1])
    report.ok("lifecycle", "operators gone after disable", not hasattr(bpy.types, "ARCHIFORGE_PT_create"))
    errors = []
    addon_utils.enable(module_name, default_set=True, handle_error=errors.append)
    report.ok("lifecycle", "enable() again without exceptions", not errors, errors[:1])
    report.ok("lifecycle", "operators back after re-enable",
              len([n for n in dir(bpy.ops.archiforge) if not n.startswith("_")]) == len(op_names))

    _finish(report, args, module_name, pkg_dir)


def _finish(report, args, module_name, pkg_dir):
    import addon_utils

    if not args.keep:
        errors = []
        addon_utils.disable(module_name, default_set=True, handle_error=errors.append)
        report.ok("lifecycle", "final disable() clean", not errors, errors[:1])
        shutil.rmtree(pkg_dir, ignore_errors=True)

    counts = report.counts()
    summary = {
        "blender": __import__("bpy").app.version_string,
        "zip": os.path.basename(args.zip),
        "seconds": round(time.time() - report.started, 1),
        "counts": counts,
        "rows": report.rows,
    }
    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=2, ensure_ascii=False)
    print("─" * 72)
    print(f"ArchiForge extension smoke test on Blender {summary['blender']}: "
          f"{counts['PASS']} passed, {counts['FAIL']} failed, {counts['SKIP']} skipped "
          f"({summary['seconds']} s)")
    if counts["FAIL"]:
        for row in report.rows:
            if row["status"] == "FAIL":
                print(f"  FAIL {row['section']}/{row['name']}: {row['detail']}")
    print("─" * 72)
    _exit(1 if counts["FAIL"] else 0)


def _exit(code):
    """Exit with ``code``.

    The PyPI ``bpy`` module (no ``binary_path``) segfaults during interpreter
    finalisation whenever a PropertyGroup with Python callbacks was registered
    in the session — any add-on triggers it — so there the process leaves
    through ``os._exit`` after flushing. The real Blender binary exits
    normally and keeps the code.
    """
    sys.stdout.flush()
    sys.stderr.flush()
    import bpy
    if not bpy.app.binary_path:
        os._exit(code)
    sys.exit(code)


if __name__ == "__main__":
    main()
