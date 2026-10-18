import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _python_sources():
    return sorted(
        path for path in ROOT.rglob("*.py")
        if ".git" not in path.parts and "__pycache__" not in path.parts
    )


def _literal_assignment(tree, name):
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == name
               for target in node.targets):
            try:
                return ast.literal_eval(node.value)
            except (ValueError, TypeError):
                return None
    return None


class RepositoryHealthTests(unittest.TestCase):
    def test_python_sources_parse_with_blender_33_python_syntax(self):
        failures = []
        for path in _python_sources():
            source = path.read_text(encoding="utf-8")
            try:
                ast.parse(source, filename=str(path), feature_version=(3, 10))
            except SyntaxError as exc:
                failures.append(f"{path.relative_to(ROOT)}: {exc}")
        self.assertEqual(failures, [])

    def test_registered_blender_ids_are_unique(self):
        locations = {}
        duplicates = []
        for path in _python_sources():
            if path.parent == ROOT / "tests":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                for statement in node.body:
                    if not isinstance(statement, ast.Assign):
                        continue
                    targets = [target for target in statement.targets
                               if isinstance(target, ast.Name)
                               and target.id == "bl_idname"]
                    if not targets or not isinstance(statement.value, ast.Constant):
                        continue
                    value = statement.value.value
                    if not isinstance(value, str):
                        continue
                    location = f"{path.relative_to(ROOT)}:{node.name}"
                    if value in locations:
                        duplicates.append(
                            f"{value}: {locations[value]} and {location}")
                    else:
                        locations[value] = location
        self.assertEqual(duplicates, [])

    def test_import_and_reload_manifests_match_existing_modules(self):
        init_path = ROOT / "__init__.py"
        tree = ast.parse(init_path.read_text(encoding="utf-8"), filename=str(init_path))
        initial = _literal_assignment(tree, "_FIRST_ORDER")
        reload = _literal_assignment(tree, "_RELOAD_ORDER")

        self.assertIsInstance(initial, tuple)
        self.assertIsInstance(reload, tuple)
        self.assertEqual(initial, reload)
        self.assertEqual(len(initial), len(set(initial)))
        for module_name in initial:
            self.assertTrue((ROOT / f"{module_name}.py").is_file(), module_name)


if __name__ == "__main__":
    unittest.main()
