# SPDX-License-Identifier: GPL-3.0-or-later
"""Rules learned from running ArchiForge inside a real Blender 4.2.

The ``unittest`` suite runs on a ``bpy`` stub, so it cannot see what Blender
itself rejects. This module encodes, statically, the failures found when the
extension was installed in Blender 4.2.23 LTS (see ``tests/blender_smoke_42.py``):

* an ``EnumProperty`` with a callback ``items`` and a string ``default``
  raises ``TypeError`` (3.3 and 4.2 alike) and silently drops the module;
* a Panel whose ``bl_parent_id`` is registered *after* it is rejected
  ("parent ... not found"), hiding the sub-panel;
* ``Mesh.polygon_layers_int`` and friends were removed in Blender 4.0;
* ``BLENDER_EEVEE`` is called ``BLENDER_EEVEE_NEXT`` in 4.2-4.x;
* ``Mesh.use_auto_smooth`` was removed in 4.1.
"""

import ast
import importlib
import pathlib
import re
import sys
import unittest

TESTS_DIR = pathlib.Path(__file__).resolve().parent
ROOT = TESTS_DIR.parent
sys.path.insert(0, str(TESTS_DIR))

import blender_stub  # noqa: E402

ADDON_SOURCES = sorted(ROOT.glob("af_*.py")) + [ROOT / "__init__.py"]


def _module_order():
    """Registration order from the ``_modules = [...]`` list in __init__.py."""
    tree = ast.parse((ROOT / "__init__.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "_modules"
                and isinstance(node.value, ast.List)):
            return [elt.id for elt in node.value.elts if isinstance(elt, ast.Name)]
    raise AssertionError("_modules list not found in __init__.py")


def _class_attr(node, name):
    for stmt in node.body:
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    if isinstance(stmt.value, ast.Constant):
                        return stmt.value.value
    return None


def _panels(path):
    """``{class_name: (bl_idname, bl_parent_id)}`` for the Panels in ``path``."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            bases = {getattr(b, "id", getattr(b, "attr", "")) for b in node.bases}
            if "Panel" in bases:
                out[node.name] = (_class_attr(node, "bl_idname") or node.name,
                                  _class_attr(node, "bl_parent_id"))
    return out


def _classes_list_order(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "classes"
                and isinstance(node.value, (ast.List, ast.Tuple))):
            return [elt.id for elt in node.value.elts if isinstance(elt, ast.Name)]
    return []


class EnumPropertyRules(unittest.TestCase):

    def test_stub_rejects_string_default_with_callback_items(self):
        blender_stub.install()
        from bpy.props import EnumProperty
        with self.assertRaises(TypeError):
            EnumProperty(items=lambda self, context: [("A", "A", "")], default="A")
        with self.assertRaises(TypeError):
            EnumProperty(items=[("A", "A", "")], default="B")
        EnumProperty(items=lambda self, context: [("A", "A", "")])
        EnumProperty(items=[("A", "A", "")], default="A")

    def test_every_addon_module_imports_under_the_stub(self):
        """Class bodies run at import, so a bad EnumProperty fails here."""
        blender_stub.install()
        failures = {}
        for path in sorted(ROOT.glob("af_*.py")):
            try:
                importlib.import_module("{}.{}".format(blender_stub.PACKAGE_NAME, path.stem))
            except Exception as ex:  # noqa: BLE001 - reported below
                failures[path.name] = "{}: {}".format(type(ex).__name__, ex)
        self.assertEqual(failures, {})

    def test_no_string_default_on_callback_enum_in_source(self):
        """Static twin of the stub check (independent of import-ability)."""
        offenders = []
        for path in ADDON_SOURCES:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            functions = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Call)
                        and getattr(node.func, "id", getattr(node.func, "attr", "")) == "EnumProperty"):
                    continue
                kw = {k.arg: k.value for k in node.keywords}
                items, default = kw.get("items"), kw.get("default")
                callback = (isinstance(items, ast.Lambda)
                            or (isinstance(items, ast.Name) and items.id in functions))
                if callback and isinstance(default, ast.Constant) and isinstance(default.value, str):
                    offenders.append("{}:{}".format(path.name, node.lineno))
        self.assertEqual(offenders, [])


class PanelRegistrationOrder(unittest.TestCase):

    def test_child_panels_register_after_their_parents(self):
        order = _module_order()
        self.assertIn("af_panel", order)
        by_module = {name: _panels(ROOT / "{}.py".format(name)) for name in order}
        defined_in = {}
        for module, panels in by_module.items():
            for cls, (idname, _parent) in panels.items():
                defined_in[idname] = (module, cls)
        problems = []
        for module, panels in by_module.items():
            for cls, (idname, parent) in panels.items():
                if not parent:
                    continue
                self.assertIn(parent, defined_in, "{} refers to unknown parent {}".format(idname, parent))
                parent_module, parent_cls = defined_in[parent]
                if order.index(parent_module) > order.index(module):
                    problems.append("{} ({}) registers before its parent {} ({})".format(
                        idname, module, parent, parent_module))
                elif parent_module == module:
                    classes = _classes_list_order(ROOT / "{}.py".format(module))
                    if cls in classes and parent_cls in classes and classes.index(parent_cls) > classes.index(cls):
                        problems.append("{} listed before its parent {} in {}.classes".format(
                            cls, parent_cls, module))
        self.assertEqual(problems, [])

    def test_snap_and_manipulator_subpanels_follow_af_panel(self):
        order = _module_order()
        for child in ("af_snap", "af_manipulator"):
            self.assertGreater(order.index(child), order.index("af_panel"), child)


class RemovedBlender4Apis(unittest.TestCase):

    FORBIDDEN = {
        # removed in 4.0 (generic attributes replaced the typed layers)
        r"\bme\w*\.polygon_layers_(int|float|string)\b": "use getattr(me, 'polygon_layers_int', None)",
        r"\.(vertex|edge)_layers_(int|float|string)\b": "removed in Blender 4.0",
        r"\bcalc_normals(_split)?\(": "removed in Blender 4.1",
        r"^\s*import bgl\b": "bgl does not work on Metal and is removed in 4.x",
        # 4.2-4.x renamed the engine; af_rendering resolves it at runtime
        r"engine\s*=\s*['\"]BLENDER_EEVEE['\"]": "use af_rendering._set_render_engine()",
        # 4.0 removed the 2D_/3D_ prefixed shaders: only allowed with a fallback
        r"from_builtin\(['\"]3D_": "use 'UNIFORM_COLOR' (with 3.x fallback)",
    }

    def test_removed_apis_are_not_used_directly(self):
        offenders = []
        for path in ADDON_SOURCES:
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                for pattern, hint in self.FORBIDDEN.items():
                    if re.search(pattern, line):
                        offenders.append("{}:{}: {} -> {}".format(path.name, number, stripped, hint))
        self.assertEqual(offenders, [])

    def test_use_auto_smooth_is_guarded(self):
        """``Mesh.use_auto_smooth`` disappeared in 4.1: every write needs hasattr."""
        offenders = []
        for path in ADDON_SOURCES:
            lines = path.read_text(encoding="utf-8").splitlines()
            for number, line in enumerate(lines, 1):
                if re.search(r"\.use_auto_smooth\s*=", line):
                    window = "\n".join(lines[max(0, number - 4):number])
                    if "hasattr(" not in window:
                        offenders.append("{}:{}".format(path.name, number))
        self.assertEqual(offenders, [])

    def test_legacy_2d_shader_names_only_as_guarded_fallback(self):
        for path in ADDON_SOURCES:
            lines = path.read_text(encoding="utf-8").splitlines()
            for number, line in enumerate(lines, 1):
                if "from_builtin('2D_" in line or 'from_builtin("2D_' in line:
                    window = "\n".join(lines[max(0, number - 3):number + 3])
                    self.assertIn("UNIFORM_COLOR'", window.replace('"', "'"),
                                  "{}:{} needs the 4.x 'UNIFORM_COLOR' fallback".format(path.name, number))
                    self.assertTrue("try:" in window or "except" in window,
                                    "{}:{} must guard the legacy shader name".format(path.name, number))


class SmokeTestScript(unittest.TestCase):

    def test_smoke_script_compiles_and_documents_usage(self):
        path = TESTS_DIR / "blender_smoke_42.py"
        source = path.read_text(encoding="utf-8")
        compile(source, str(path), "exec")
        self.assertIn("extensions.package_install_files", source)
        self.assertIn("--python-exit-code 1", source)


if __name__ == "__main__":
    unittest.main()
