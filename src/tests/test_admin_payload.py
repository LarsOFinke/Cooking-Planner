"""Recipe admin submission rules without a running Kivy window."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'frontend'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))

from cooking_planner.recipes.admin_payload import FormError, RecipeFormSnapshot, build_submission
from cooking_planner.recipes.admin_schema import CHOICES, TIMES, new_recipe_template


class RecipePayloadTest(unittest.TestCase):
    def snapshot(self):
        document = new_recipe_template('test-dish')
        return RecipeFormSnapshot(
            recipe_id='test-dish', source='EN', locale='en', locales=('en', 'de'),
            choices={'en': 'Translate', 'de': 'Omit intentionally'},
            shared_choices={key: document[key] for key, _ in CHOICES},
            times={key: str(document[key]) for key, _ in TIMES},
            diets=['omnivore'], images='',
            ingredients=[{'original': document['ingredients'][0], 'ingredient_id': 'rice',
                          'amount': '1.5', 'unit': 'g', 'names': {'en': 'Rice', 'de': 'Reis'}}],
            steps=[{'ingredient_ids': 'rice', 'texts': {'en': 'Cook the rice.', 'de': ''}}],
            names={'en': 'Rice dish', 'de': ''},
            documents={'en': document, 'de': new_recipe_template('test-dish')}, options={},
        )

    def test_builds_translations_without_changing_loaded_documents(self):
        snapshot = self.snapshot()
        recipe_id, source, translations = build_submission(snapshot)
        self.assertEqual(('test-dish', 'en'), (recipe_id, source))
        self.assertIsNone(translations['de'])
        self.assertEqual('Rice dish', translations['en']['name'])
        self.assertEqual(1.5, translations['en']['ingredients'][0]['amount'])
        self.assertEqual(['rice'], translations['en']['instructions']['steps'][0]['ingredient_ids'])
        self.assertEqual('', snapshot.documents['en']['name'])

    def test_rejects_invalid_amount_and_unknown_step_ingredient(self):
        snapshot = self.snapshot()
        snapshot.ingredients[0]['amount'] = '0'
        with self.assertRaisesRegex(FormError, 'positive number'):
            build_submission(snapshot)
        snapshot.ingredients[0]['amount'] = '1'
        snapshot.steps[0]['ingredient_ids'] = 'missing'
        with self.assertRaisesRegex(FormError, 'Ingredient'):
            build_submission(snapshot)


if __name__ == '__main__':
    unittest.main()
