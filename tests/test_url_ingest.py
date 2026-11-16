"""URL ingest stays on structured page data and refuses unsafe inputs."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "chili.html"

sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from recipe_tool.extract.url import (  # noqa: E402
    RecipeFetchError,
    assert_public_url,
    build_recipe,
)
from recipe_tool.ids import RecipeIdError, slug_from_title, validate_recipe_id  # noqa: E402
from recipe_tool.taxonomy import infer_dietary  # noqa: E402
from schema.orf_models import parse_recipe_yaml  # noqa: E402

import yaml  # noqa: E402


class UrlIngestTests(unittest.TestCase):
    def test_fixture_becomes_orf_without_a_model(self) -> None:
        self.assertNotIn("openai", sys.modules)
        self.assertNotIn("anthropic", sys.modules)
        html = FIXTURE.read_text(encoding="utf-8")
        with patch("recipe_tool.extract.url.assert_public_url"):
            data = build_recipe(html, "https://example.com/chili")
        text = yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
        parse_recipe_yaml(text)
        self.assertNotIn("as listed", text)
        self.assertEqual(data["source_url"], "https://example.com/chili")
        self.assertNotIn("javascript:", data["source_url"])
        self.assertEqual(data["recipe_uuid"], "wc-kitchen.vegetarian-chili-secret")
        self.assertNotIn("/", data["recipe_uuid"].split(".", 1)[1])
        self.assertEqual(data["X-total_time"], "45 minutes")
        tomatoes = data["ingredients"][0]["crushed tomatoes"]
        self.assertEqual(tomatoes["amounts"][0]["amount"], 1.5)
        self.assertEqual(tomatoes["amounts"][0]["unit"], "cups")
        self.assertIn("soup", data["X-categories"]["dish_type"])
        self.assertIn("dinner", data["X-categories"]["meal_type"])
        self.assertIn("italian", data["X-tags"]["cuisine"])
        self.assertIn("vegetarian", data["X-tags"]["dietary"])
        self.assertNotIn("openai", sys.modules)
        self.assertNotIn("anthropic", sys.modules)

    def test_private_and_metadata_urls_are_refused(self) -> None:
        for url in (
            "http://127.0.0.1/admin",
            "http://169.254.169.254/latest/meta-data",
            "http://10.0.0.1/",
            "javascript:alert(1)",
        ):
            with self.subTest(url=url):
                with self.assertRaises(RecipeFetchError):
                    assert_public_url(url)

    def test_title_cannot_escape_recipes_dir(self) -> None:
        self.assertEqual(
            slug_from_title("Pasta ../ Secret"),
            "wc-kitchen.pasta-secret",
        )

    def test_form_id_with_path_is_rejected(self) -> None:
        with self.assertRaises(RecipeIdError):
            validate_recipe_id("wc-kitchen.ok/../../x")

    def test_adaptation_phrasing_is_not_a_dietary_tag(self) -> None:
        data = {
            "recipe_name": "Beans",
            "description": "Add mushrooms to make vegetarian.",
            "ingredients": [],
            "steps": [],
        }
        self.assertEqual(infer_dietary(data), [])


if __name__ == "__main__":
    unittest.main()
