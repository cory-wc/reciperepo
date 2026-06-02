from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml

from recipe_tool.load import load_recipe
from recipe_tool.metadata_editor import apply_metadata_update, list_recipe_rows, recipe_to_row
from recipe_tool.metadata_facets import is_filterable_metadata
from recipe_tool.paths import RepoPaths


class MetadataEditorTest(unittest.TestCase):
    def test_apply_metadata_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            recipes = root / "recipes"
            recipes.mkdir()
            recipe_id = "wc-kitchen.test-soup"
            path = recipes / f"{recipe_id}.yaml"
            path.write_text(
                yaml.dump(
                    {
                        "recipe_uuid": recipe_id,
                        "recipe_name": "Test Soup",
                        "X-category": ["Soup"],
                        "X-tags": ["weeknight"],
                        "yields": [{"amount": 4, "unit": "servings"}],
                        "ingredients": [{"water": {"amounts": [{"amount": 1, "unit": "cup"}]}}],
                        "steps": [{"step": "Simmer."}],
                        "X-source-verification": {"status": "needs-review", "notes": []},
                    },
                    default_flow_style=False,
                ),
                encoding="utf-8",
            )
            paths = RepoPaths(root=root)

            row = apply_metadata_update(
                recipe_id,
                {
                    "dish_type": "soup",
                    "meal_type": "dinner",
                    "cuisine": "american",
                    "method": "stovetop",
                },
                paths,
            )
            self.assertTrue(row["filterable"])
            _, data, _ = load_recipe(recipe_id, paths)
            self.assertEqual(data["X-categories"]["dish_type"], ["soup"])
            self.assertEqual(data["X-tags"]["cuisine"], ["american"])
            self.assertNotIn("X-category", data)
            self.assertIsInstance(data["X-tags"], dict)

    def test_recipe_to_row(self) -> None:
        data = {
            "recipe_name": "Example",
            "X-categories": {"dish_type": ["main"], "meal_type": ["dinner"]},
            "X-tags": {"method": ["oven"]},
        }
        row = recipe_to_row("wc-kitchen.example", data)
        self.assertEqual(row["fields"]["dish_type"], "main")
        self.assertTrue(is_filterable_metadata(data))


if __name__ == "__main__":
    unittest.main()
