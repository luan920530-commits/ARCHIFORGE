"""Blender 4.2+ extension packaging checks (``blender_manifest.toml``).

The authoritative validator is Blender's own CLI
(``blender --command extension validate``); these tests keep the manifest
coherent with the code base and with the rules that CLI enforces for the
extensions platform (https://extensions.blender.org) without needing Blender.
"""
import ast
import fnmatch
import importlib.util
import re
import sys
import types
import unittest
from pathlib import Path

try:
    import tomllib
except ImportError:  # Python < 3.11
    tomllib = None


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "blender_manifest.toml"
INIT = ROOT / "__init__.py"

# scripts/modules/_bpy_internal/extensions/tags.py (Blender 4.2+).
OFFICIAL_ADDON_TAGS = {
    "3D View", "Add Curve", "Add Mesh", "Animation", "Bake", "Camera",
    "Compositing", "Development", "Game Engine", "Geometry Nodes",
    "Grease Pencil", "Import-Export", "Lighting", "Material", "Mesh",
    "Modeling", "Node", "Object", "Paint", "Physics", "Pipeline", "Render",
    "Rigging", "Scene", "Sculpt", "Sequencer", "System", "Text Editor",
    "Tracking", "User Interface", "UV",
}
PERMISSION_KEYS = {"files", "network", "clipboard", "camera", "microphone"}
TERSE_MAX = 64  # tagline / permission reasons (blender_ext.py).
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")


def _bl_info():
    tree = ast.parse(INIT.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == "bl_info" for t in node.targets):
                return ast.literal_eval(node.value)
    raise AssertionError("bl_info not found")


def _manifest_text():
    return MANIFEST.read_text(encoding="utf-8")


def _manifest():
    if tomllib is None:
        raise unittest.SkipTest("tomllib (Python 3.11+) required to parse TOML")
    with MANIFEST.open("rb") as fh:
        return tomllib.load(fh)


def _terse_ok(value):
    """Rules of ``pkg_manifest_validate_terse_description_or_error``."""
    if not isinstance(value, str) or not value or value != value.strip():
        return False
    if len(value) > TERSE_MAX or any(ord(c) < 32 for c in value):
        return False
    return value[-1].isalnum() or value[-1] in {")", "]", "}"}


class ManifestVersionTests(unittest.TestCase):
    """Run on every Python version (plain text checks)."""

    def test_manifest_exists_next_to_init(self):
        self.assertTrue(MANIFEST.is_file())
        self.assertTrue(INIT.is_file())

    def test_manifest_version_matches_bl_info(self):
        version = ".".join(str(v) for v in _bl_info()["version"])
        match = re.search(r'^version\s*=\s*"([^"]+)"', _manifest_text(), re.M)
        self.assertIsNotNone(match, "version missing in manifest")
        self.assertEqual(match.group(1), version)
        self.assertRegex(version, SEMVER)

    def test_bl_info_is_only_read_at_import_time(self):
        """Blender 4.2+ deletes ``bl_info`` from extension modules before
        ``register()`` runs, so functions must never read it."""
        tree = ast.parse(INIT.read_text(encoding="utf-8"))
        offenders = []
        for top in tree.body:
            if isinstance(top, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                for node in ast.walk(top):
                    if isinstance(node, ast.Name) and node.id == "bl_info":
                        offenders.append(node.lineno)
        self.assertEqual(offenders, [], f"bl_info read inside a function/class at lines {offenders}")
        source = INIT.read_text(encoding="utf-8")
        self.assertIn('ADDON_VERSION = tuple(bl_info["version"])', source)
        self.assertNotIn("bl_info.get(", source)

    def test_package_name_is_never_truncated_at_the_first_dot(self):
        """Extensions are imported as ``bl_ext.<repo>.<id>``: splitting
        ``__package__`` at the first dot would point at ``bl_ext``."""
        for name in ("af_icons.py", "af_i18n.py", "af_control_center.py",
                     "af_material.py", "af_quantities.py", "af_annotation.py"):
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertNotIn('__package__ or "").split(".")[0]', text, name)
            self.assertNotIn('__package__ or "ArchiForge").split(".")[0]', text, name)
            self.assertNotRegex(text, r"__package__[^\n]*\.split\(['\"]\.['\"]\)\[0\]", name)


class ManifestContentTests(unittest.TestCase):
    def setUp(self):
        self.manifest = _manifest()

    def test_required_fields(self):
        m = self.manifest
        self.assertEqual(m["schema_version"], "1.0.0")
        self.assertEqual(m["id"], "archiforge")
        self.assertTrue(m["id"].isidentifier() and "__" not in m["id"])
        self.assertFalse(m["id"].startswith("_") or m["id"].endswith("_"))
        self.assertEqual(m["name"], "ArchiForge")
        self.assertNotIn("blender", m["name"].lower())
        self.assertEqual(m["type"], "add-on")
        self.assertTrue(m["maintainer"].strip())
        self.assertRegex(m["version"], SEMVER)
        self.assertTrue(_terse_ok(m["tagline"]), m["tagline"])
        self.assertFalse(m["tagline"].lower().startswith(m["name"].lower()))

    def test_blender_version_min_is_extension_capable(self):
        value = self.manifest["blender_version_min"]
        self.assertRegex(value, r"^\d+\.\d+\.\d+$")
        self.assertGreaterEqual(tuple(int(v) for v in value.split(".")), (4, 2, 0))
        maximum = self.manifest.get("blender_version_max", "")
        if maximum:
            self.assertRegex(maximum, r"^\d+\.\d+\.\d+$")

    def test_license_tags_copyright_and_permissions(self):
        m = self.manifest
        self.assertEqual(m["license"], ["SPDX:GPL-3.0-or-later"])
        self.assertTrue((ROOT / "LICENSE").is_file())
        self.assertTrue(set(m["tags"]) <= OFFICIAL_ADDON_TAGS, set(m["tags"]) - OFFICIAL_ADDON_TAGS)
        self.assertEqual(len(m["tags"]), len(set(m["tags"])))
        for entry in m.get("copyright", []):
            year, _, holder = entry.partition(" ")
            self.assertTrue(all(part.isdigit() for part in year.split("-")), entry)
            self.assertTrue(holder.strip(), entry)
        permissions = m.get("permissions", {})
        self.assertIsInstance(permissions, dict)
        self.assertTrue(set(permissions) <= PERMISSION_KEYS, set(permissions))
        for reason in permissions.values():
            self.assertTrue(_terse_ok(reason), reason)
        # The add-on writes presets / CSV files but never uses the network.
        self.assertIn("files", permissions)
        self.assertNotIn("network", permissions)
        self.assertTrue(m["website"].startswith("https://"))

    def test_build_excludes_development_files(self):
        patterns = self.manifest["build"]["paths_exclude_pattern"]
        self.assertNotIn("paths", self.manifest["build"])
        for required in ("__pycache__/", ".*", "/*.zip", "/tests/"):
            self.assertIn(required, patterns)
        # Every explicitly excluded *file* really exists (no stale patterns);
        # directory patterns such as "/dist/" may name future build output.
        for pattern in patterns:
            if (pattern.startswith("/") and not pattern.endswith("/")
                    and not any(ch in pattern for ch in "*?[")):
                self.assertTrue((ROOT / pattern.strip("/")).is_file(), pattern)
        # Files that must ship in the package are not excluded.
        shipped = ["__init__.py", "af_icons.py", "icons/wall.png", "LICENSE",
                   "blender_manifest.toml"]
        for rel in shipped:
            for pattern in patterns:
                root_only = pattern.startswith("/")
                pat = pattern.strip("/")
                target = rel if root_only else rel.split("/")[-1]
                self.assertFalse(fnmatch.fnmatch(target, pat.rstrip("/")), f"{rel} excluded by {pattern}")

    def test_manifest_matches_bl_info_metadata(self):
        info = _bl_info()
        self.assertEqual(self.manifest["name"], info["name"])
        self.assertEqual(self.manifest["version"], ".".join(str(v) for v in info["version"]))
        self.assertIn(info["author"], self.manifest["maintainer"])
        self.assertTrue(self.manifest["website"].startswith(info["doc_url"].split("#")[0]))


class ExtensionPackageNameTests(unittest.TestCase):
    """The helpers must resolve the add-on package when it is a dotted
    ``bl_ext.<repository>.archiforge`` extension module."""

    PACKAGE = "bl_ext.user_default.archiforge"

    def _load(self, module_name):
        spec = importlib.util.spec_from_file_location(
            f"{self.PACKAGE}.{module_name}", ROOT / f"{module_name}.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_af_icons_finds_the_extension_package(self):
        class _Preview:
            icon_id = 77
        package = types.ModuleType(self.PACKAGE)
        package.get_icons = lambda: {"wall": _Preview()}
        sys.modules[self.PACKAGE] = package
        sys.modules.setdefault("bl_ext", types.ModuleType("bl_ext"))
        try:
            af_icons = self._load("af_icons")
            self.assertEqual(af_icons.icon_kw("wall", 'SNAP_FACE'), {'icon_value': 77})
        finally:
            sys.modules.pop(self.PACKAGE, None)

    def test_af_i18n_uses_the_full_package_name_as_preferences_key(self):
        sys.path.insert(0, str(ROOT / "tests"))
        try:
            import blender_stub
            blender_stub.install()
            af_i18n = self._load("af_i18n")
            self.assertEqual(af_i18n._addon_name(), self.PACKAGE)
        finally:
            sys.path.remove(str(ROOT / "tests"))


if __name__ == "__main__":
    unittest.main()
