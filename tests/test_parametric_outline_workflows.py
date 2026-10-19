import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _class_node(tree, name):
    return next(node for node in tree.body
                if isinstance(node, ast.ClassDef) and node.name == name)


def _function_node(container, name):
    return next(node for node in container.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == name)


def _called_names(node):
    return {
        call.func.id for call in ast.walk(node)
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
    }


class ParametricOutlineWorkflowTests(unittest.TestCase):
    def test_draw_operators_share_closed_outline_modal(self):
        for filename, class_name, operator_id in (
                ("af_slab.py", "ARCHIFORGE_OT_slab_draw",
                 "archiforge.slab_draw"),
                ("af_floor.py", "ARCHIFORGE_OT_floor_draw",
                 "archiforge.floor_draw")):
            tree = ast.parse((ROOT / filename).read_text(encoding="utf-8"))
            operator = _class_node(tree, class_name)
            bases = {base.id for base in operator.bases
                     if isinstance(base, ast.Name)}
            self.assertIn("AF_OutlineDrawMixin", bases)
            self.assertTrue(any(
                isinstance(statement, ast.Assign)
                and any(isinstance(target, ast.Name)
                        and target.id == "bl_idname"
                        for target in statement.targets)
                and isinstance(statement.value, ast.Constant)
                and statement.value.value == operator_id
                for statement in operator.body
            ))

    def test_opening_creation_and_property_updates_manage_wall_boolean(self):
        tree = ast.parse((ROOT / "af_openings.py").read_text(encoding="utf-8"))
        operator = _class_node(tree, "ARCHIFORGE_OT_opening")
        execute = _function_node(operator, "execute")
        self.assertIn("_rebuild_opening_mesh", _called_names(execute))
        self.assertIn("_apply_wall_cut", _called_names(execute))

        update = _function_node(tree, "af_opening_update")
        self.assertIn("_cut", _called_names(update))

        target_wall = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "target_wall"
        )
        property_definition = target_wall.annotation
        self.assertIsInstance(property_definition, ast.Call)
        self.assertTrue(any(
            keyword.arg == "update"
            and isinstance(keyword.value, ast.Name)
            and keyword.value.id == "af_opening_update"
            for keyword in property_definition.keywords
        ))


if __name__ == "__main__":
    unittest.main()
