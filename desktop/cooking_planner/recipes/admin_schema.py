"""Raw catalog fields and templates used by the recipe editor."""

from copy import deepcopy

CHOICES = (
    ('country_code', 'admin_country'), ('region_code', 'admin_region'),
    ('continent_code', 'admin_continent'), ('category', 'category'),
    ('difficulty', 'difficulty'), ('effort', 'effort'),
    ('diet_type', 'diet'), ('data_source', 'admin_data_source_label'),
)
LABELS = {
    'country_code': 'country', 'region_code': 'region', 'continent_code': 'continent',
    'category': 'category_label', 'difficulty': 'difficulty_label',
    'effort': 'effort_label', 'diet_type': 'diet_type_label', 'data_source': 'data_source_label',
}
TIMES = (('prep_minutes', 'admin_prep_minutes'), ('cook_minutes', 'admin_cook_minutes'),
         ('total_minutes', 'admin_total_minutes'))


def new_recipe_template(recipe_id):
    return {
        'id': recipe_id, 'name': '', 'country': '', 'country_code': '', 'region': '', 'continent': '',
        'category': 'main', 'difficulty': 'medium', 'effort': 'medium', 'data_source': 'user_entry',
        'prep_minutes': 0, 'cook_minutes': 0, 'total_minutes': 0, 'diet_type': 'omnivore',
        'suitable_for': ['flexitarian', 'omnivore'],
        'ingredients': [{'name': '', 'ingredient_id': 'ingredient-id', 'amount': 1, 'unit': 'g'}],
        'region_code': '', 'continent_code': '', 'category_label': '', 'difficulty_label': '',
        'effort_label': '', 'diet_type_label': '', 'suitable_for_labels': [],
        'data_source_label': '', 'image_folder': f'recipe_images/{recipe_id}', 'images': [],
        'instructions': {'steps': []},
    }


def translation_template(recipe):
    translated = deepcopy(recipe)
    for key in ('name', *LABELS.values()):
        translated[key] = ''
    translated['suitable_for_labels'] = []
    for ingredient in translated['ingredients']:
        ingredient['name'] = ''
    for step in translated.get('instructions', {}).get('steps', []):
        step['text'] = ''
    return translated
