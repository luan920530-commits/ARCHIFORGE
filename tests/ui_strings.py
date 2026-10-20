"""Collect the user-facing strings ArchiForge hands to Blender's UI.

Blender translates panel/operator/menu labels, property names, enum items,
tooltips and ``text=`` arguments through ``bpy.app.translations`` as long as
the exact English string (the *msgid*) is present in the registered
dictionary. This module walks the addon sources with ``ast`` and gathers
those msgids so ``tests/test_i18n.py`` can check that every one of them has
a Spanish entry in ``af_i18n_es.py``.

Run it directly to list the strings that still lack a translation::

    python tests/ui_strings.py
"""

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Modules whose UI strings must be translatable. Pure geometry/data helpers
# without a user interface are left out on purpose.
UI_MODULES = tuple(sorted(
    path.name for path in ROOT.glob("*.py")
    if path.name == "__init__.py"
    or (path.name.startswith("af_")
        and path.name not in {
            "af_floor_geometry.py", "af_wall_path.py", "af_window_geometry.py",
            "af_quantities_io.py", "af_objects_base.py", "af_outline_draw.py",
            "af_i18n.py", "af_i18n_es.py", "af_units.py",
        })
))

LABEL_KEYWORDS = ("name", "text", "heading", "bl_label")
REPORT_TRANSLATORS = ("_tr", "tr_report")
TOOLTIP_KEYWORDS = ("description", "bl_description")
CLASS_ATTRIBUTES = ("bl_label", "bl_description")

_IDENTIFIER = re.compile(r"^[A-Z0-9_]+$")
_BL_IDNAME = re.compile(r"^[a-z_]+\.[a-z_0-9]+$")
_PROPERTY_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


def _string(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _dotted_name(node):
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def _candidate_strings(node):
    """Strings reachable from an expression used as a label."""
    text = _string(node)
    if text is not None:
        return [text]
    if isinstance(node, ast.IfExp):
        return _candidate_strings(node.body) + _candidate_strings(node.orelse)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        # "Long " "literal" concatenations are folded by the parser already;
        # explicit ``a + b`` label pieces are not translatable as a whole.
        return []
    return []


def is_translatable(text, allow_templates=False):
    """Heuristic filter for strings that are real UI text, not identifiers.

    ``allow_templates`` accepts ``str.format`` templates, which is how
    operator report messages are written (``_tr("Created {}")``).
    """
    stripped = text.strip()
    if not stripped or not re.search(r"[A-Za-zÀ-ÿ]", stripped):
        return False
    if _IDENTIFIER.match(stripped) or _BL_IDNAME.match(stripped):
        return False
    if _PROPERTY_NAME.match(stripped) and " " not in stripped:
        return False
    if re.fullmatch(r"[A-Za-z0-9_.]+", stripped) and ("_" in stripped
                                                       or "." in stripped):
        return False  # class names, idnames, file names
    if "{" in stripped and "}" in stripped and not allow_templates:
        return False  # str.format templates are filled before display
    if stripped.startswith(("AF.", "AF_", "archiforge_")):
        return False
    return True


def _collect_from_tree(tree):
    labels, tooltips = set(), set()

    def add(bucket, node, allow_templates=False):
        for text in _candidate_strings(node):
            if is_translatable(text, allow_templates):
                bucket.add(text)

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if _dotted_name(node.func).startswith("bpy.ops."):
                continue  # operator invocation parameters, not UI text
            for keyword in node.keywords:
                if keyword.arg in LABEL_KEYWORDS:
                    add(labels, keyword.value)
                elif keyword.arg in TOOLTIP_KEYWORDS:
                    add(tooltips, keyword.value)
            func = node.func
            func_name = func.attr if isinstance(func, ast.Attribute) else (
                func.id if isinstance(func, ast.Name) else "")
            if func_name.endswith(("_btn", "_button", "_item")):
                # Local helpers such as ``bath_btn(row, "Toilet", 'TOILET')``.
                for arg in node.args[1:2]:
                    add(labels, arg)
            elif func_name in REPORT_TRANSLATORS:
                # Operator report templates: ``_tr("Created {}").format(n)``.
                for arg in node.args[:1]:
                    add(labels, arg, allow_templates=True)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in CLASS_ATTRIBUTES:
                    add(labels if target.id == "bl_label" else tooltips,
                        node.value)
        elif isinstance(node, ast.Tuple) and len(node.elts) >= 2:
            first, second = node.elts[0], node.elts[1]
            key = _string(first)
            label = _string(second)
            if key is None or label is None:
                continue
            if len(node.elts) >= 3 and _string(node.elts[2]) is not None \
                    and _IDENTIFIER.match(key):
                # Enum item ``(ID, label, description[, icon, number])``.
                add(labels, second)
                add(tooltips, node.elts[2])
            elif _IDENTIFIER.match(key) or _BL_IDNAME.match(key):
                # Button tables ``(ID, "Label")`` / ``("op.id", "Label")``.
                add(labels, second)
    return labels, tooltips


def collect_ui_strings(modules=UI_MODULES):
    """Return ``{module_name: (labels, tooltips)}`` for the given modules."""
    result = {}
    for name in modules:
        tree = ast.parse((ROOT / name).read_text(encoding="utf-8"))
        result[name] = _collect_from_tree(tree)
    return result


def dynamic_enum_strings():
    """Labels/descriptions produced by enum item builders at runtime."""
    sys.path.insert(0, str(ROOT))
    try:
        import af_construction_presets as presets
    finally:
        sys.path.pop(0)
    labels, tooltips = set(), set()
    for items in (presets.wall_preset_items(), presets.tile_preset_items()):
        for identifier, label, description in items:
            if is_translatable(label):
                labels.add(label)
            if is_translatable(description):
                tooltips.add(description)
    return labels, tooltips


def all_ui_strings():
    """Flat ``(labels, tooltips)`` sets across every UI module."""
    labels, tooltips = dynamic_enum_strings()
    for module_labels, module_tooltips in collect_ui_strings().values():
        labels |= module_labels
        tooltips |= module_tooltips
    return labels, tooltips - labels


def known_ui_strings(catalogue):
    """Every msgid the catalogue module accounts for."""
    return (set(catalogue.TRANSLATIONS)
            | set(catalogue.ENGLISH_FOR_SPANISH_SOURCE)
            | set(catalogue.SAME_IN_SPANISH))


def _main():
    sys.path.insert(0, str(ROOT))
    import af_i18n_es
    known = known_ui_strings(af_i18n_es)
    missing_total = 0
    for name, (labels, tooltips) in collect_ui_strings().items():
        missing = sorted((labels | tooltips) - known)
        if missing:
            missing_total += len(missing)
            print("== {} ({} missing)".format(name, len(missing)))
            for text in missing:
                print("    {!r}".format(text))
    dyn_labels, dyn_tooltips = dynamic_enum_strings()
    missing = sorted((dyn_labels | dyn_tooltips) - known)
    if missing:
        missing_total += len(missing)
        print("== dynamic enum items ({} missing)".format(len(missing)))
        for text in missing:
            print("    {!r}".format(text))
    print("Missing translations: {}".format(missing_total))
    return 1 if missing_total else 0


if __name__ == "__main__":
    sys.exit(_main())
