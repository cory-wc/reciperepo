from __future__ import annotations

import unittest

from recipe_tool.metadata_facets import (
    build_filter_tree,
    extract_facets,
    facet_tokens,
    is_filterable_metadata,
    is_reference_entry,
    metadata_cleanup_issues,
    recipe_matches_filters,
)


class MetadataFacetsTest(unittest.TestCase):
    def test_structured_recipe(self) -> None:
        data = {
            "X-categories": {
                "dish_type": ["soup"],
                "meal_type": ["dinner"],
            },
            "X-tags": {
                "cuisine": ["japanese"],
                "dietary": ["vegan", "vegetarian"],
            },
        }
        self.assertTrue(is_filterable_metadata(data))
        facets = extract_facets(data)
        self.assertEqual(facets["dish_type"], ["soup"])
        self.assertEqual(facets["meal_type"], ["dinner"])
        self.assertEqual(facets["cuisine"], ["japanese"])
        self.assertIn("vegan", facets["dietary"])
        tokens = facet_tokens(facets)
        self.assertIn("cuisine:japanese", tokens)
        self.assertIn("dietary:vegan", tokens)

    def test_legacy_recipe_needs_cleanup(self) -> None:
        data = {
            "X-category": ["Salad", "Side Dish", "Dinner"],
            "X-dietary": ["Vegan", "Vegetarian"],
            "X-tags": ["meal prep", "hearty", "potluck"],
        }
        self.assertFalse(is_filterable_metadata(data))
        issues = metadata_cleanup_issues(data)
        self.assertIn("legacy X-category", issues)
        self.assertIn("legacy X-dietary", issues)
        self.assertIn("flat X-tags list (use structured X-tags)", issues)
        self.assertEqual(extract_facets(data), {})

    def test_reference_entry(self) -> None:
        data = {
            "X-flags": ["index-page-not-a-recipe"],
            "X-categories": {"dish_type": ["reference"]},
        }
        self.assertTrue(is_reference_entry(data))
        self.assertTrue(is_filterable_metadata(data))
        facets = extract_facets(data)
        self.assertEqual(facets["dish_type"], ["reference"])

    def test_filter_semantics(self) -> None:
        tokens = [
            "cuisine:japanese",
            "dietary:vegan",
            "meal_type:dinner",
            "dish_type:soup",
        ]
        self.assertTrue(
            recipe_matches_filters(
                tokens,
                {
                    "cuisine": {"japanese"},
                    "dietary": {"vegan"},
                },
            )
        )
        self.assertFalse(
            recipe_matches_filters(
                tokens,
                {
                    "cuisine": {"thai"},
                    "dietary": {"vegan"},
                },
            )
        )
        self.assertTrue(
            recipe_matches_filters(
                tokens,
                {"dietary": {"vegan", "vegetarian"}},
            )
        )
        self.assertFalse(
            recipe_matches_filters(
                tokens,
                {"dietary": {"gluten_free"}},
            )
        )

    def test_build_filter_tree_skips_reference(self) -> None:
        entries = [
            {
                "is_reference": True,
                "facets": {"dish_type": ["reference"]},
            },
            {
                "is_reference": False,
                "facets": {"cuisine": ["thai"], "dish_type": ["sauce"]},
            },
        ]
        tree = build_filter_tree(entries)
        keys = [g["key"] for g in tree]
        self.assertIn("cuisine", keys)
        self.assertIn("dish_type", keys)
        dish_values = next(g["options"] for g in tree if g["key"] == "dish_type")
        self.assertEqual(dish_values[0]["value"], "sauce")
        self.assertNotIn("reference", [v["value"] for v in dish_values])


if __name__ == "__main__":
    unittest.main()
