"""Map catalog rows into the UI recipe shape without exposing mutable catalog lists."""


def map_recipe(row, locale, names):
    return {'id': row['id'], 'name': row['name'], 'country': row.get('country') or '',
            'countryCode': row.get('country_code') or '', 'region': row.get('region') or '',
            'continent': row.get('continent') or '', 'category': row.get('category') or '',
            'categoryLabel': row.get('category_label') or '', 'difficulty': row.get('difficulty') or '',
            'difficultyLabel': row.get('difficulty_label') or '', 'effort': row.get('effort') or '',
            'effortLabel': row.get('effort_label') or '', 'dietType': row.get('diet_type') or '',
            'dietTypeLabel': row.get('diet_type_label') or '', 'suitableFor': list(row.get('suitable_for') or []),
            'suitableForLabels': list(row.get('suitable_for_labels') or []),
            'ingredients': [{'name': names.get(item['ingredient_id'], item['name']),
                             'ingredientId': item['ingredient_id'], 'amount': item['amount'],
                             'unit': item['unit']} for item in row['ingredients']],
            'prepMinutes': row.get('prep_minutes', 0), 'cookMinutes': row.get('cook_minutes', 0),
            'totalMinutes': row.get('total_minutes', 0),
            'dataSourceLabel': row.get('data_source_label') or '', 'locale': locale,
            'images': list(row.get('images') or []),
            'instructions': [{'step': step.get('step', 0), 'text': step.get('text', ''),
                              'ingredientIds': list(step.get('ingredient_ids', []))}
                             for step in row.get('instructions', {}).get('steps', [])]}
