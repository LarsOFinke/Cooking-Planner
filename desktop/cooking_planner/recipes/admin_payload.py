"""Validate recipe editor values and assemble the backend submission."""

from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from cooking_planner.recipes.admin_schema import CHOICES, LABELS, TIMES
from cooking_planner.ui.strings import t


class FormError(ValueError):
    """A localized message that the editor can show without changing its form."""


@dataclass
class RecipeFormSnapshot:
    recipe_id: str
    source: str
    locale: str
    locales: tuple[str, ...]
    choices: dict[str, str]
    shared_choices: dict[str, str]
    times: dict[str, str]
    diets: list[str]
    images: str
    ingredients: list[dict]
    steps: list[dict]
    names: dict[str, str]
    documents: dict[str, dict]
    options: dict


def option_labels(options, key, locale):
    labels = {item['value']: item['label'] for item in options.get(locale, {}).get(key, [])}
    if key == 'data_source':
        labels.setdefault('user_entry', t(locale, 'admin_user_entry'))
    return labels


def _label_for(snapshot, locale, key, value):
    labels = option_labels(snapshot.options, key, locale)
    if value in labels:
        return labels[value]
    document = snapshot.documents[locale]
    label_key = LABELS.get(key)
    if label_key and document.get(key) == value and document.get(label_key):
        return document[label_key]
    return value


def build_submission(snapshot):
    """Return (recipe ID, source locale, translations), or raise FormError."""
    locale = snapshot.locale
    recipe_id = snapshot.recipe_id.strip()
    source = snapshot.source.lower()
    if not recipe_id:
        raise FormError(t(locale, 'admin_missing_id'))
    if snapshot.choices[source] != t(locale, 'admin_translate'):
        raise FormError(t(locale, 'admin_source_required'))
    for code, choice in snapshot.choices.items():
        if choice == t(locale, 'admin_choose'):
            raise FormError(f"{code.upper()}: {t(locale, 'admin_choose_language')}")

    shared = {}
    for key, title in CHOICES:
        shared[key] = snapshot.shared_choices[key]
        if not shared[key] and key not in ('country_code', 'region_code', 'continent_code'):
            raise FormError(f"{t(locale, title)}: {t(locale, 'admin_select_option')}")
    for key, title in TIMES:
        try:
            shared[key] = int(snapshot.times[key].strip())
        except ValueError as error:
            raise FormError(f"{t(locale, title)}: {t(locale, 'admin_whole_number')}") from error
    shared['suitable_for'] = snapshot.diets
    shared['images'] = [line.strip() for line in snapshot.images.splitlines() if line.strip()]

    if not snapshot.ingredients:
        raise FormError(t(locale, 'admin_need_ingredient'))
    ingredients = []
    for ingredient in snapshot.ingredients:
        try:
            amount = Decimal(ingredient['amount'].strip())
            if not amount.is_finite() or amount <= 0 or amount > 1_000_000_000:
                raise InvalidOperation
        except InvalidOperation as error:
            raise FormError(f"{t(locale, 'admin_amount')}: {t(locale, 'admin_positive_number')}") from error
        ingredients.append((ingredient, int(amount) if amount == amount.to_integral_value() else float(amount)))

    if len(snapshot.steps) > 50:
        raise FormError(t(locale, 'admin_add_step') + ': 50')
    valid_ids = {item['ingredient_id'].strip() for item, _ in ingredients}
    instructions = {code: [] for code in snapshot.locales}
    for index, step in enumerate(snapshot.steps, 1):
        ids = [item.strip() for item in step['ingredient_ids'].split(',') if item.strip()]
        if any(item not in valid_ids for item in ids):
            raise FormError(t(locale, 'admin_step_ingredients'))
        for code in snapshot.locales:
            text = step['texts'][code].strip()
            if snapshot.choices[code] == t(locale, 'admin_translate') and (not text or len(text) > 2000):
                raise FormError(f"{code.upper()}: {t(locale, 'admin_step_text')} {index}")
            instructions[code].append({'step': index, 'text': text, 'ingredient_ids': ids})

    translations = {}
    for code, choice in snapshot.choices.items():
        if choice == t(locale, 'admin_omit'):
            translations[code] = None
            continue
        row = deepcopy(snapshot.documents[code])
        row.update(shared)
        row['id'] = recipe_id
        row['image_folder'] = f'recipe_images/{recipe_id}'
        row['name'] = snapshot.names[code].strip()
        for key, label_key in LABELS.items():
            row[label_key] = _label_for(snapshot, code, key, shared[key])
        row['suitable_for_labels'] = [_label_for(snapshot, code, 'suitable_for', value)
                                      for value in shared['suitable_for']]
        row['ingredients'] = []
        for ingredient, amount in ingredients:
            item = deepcopy(ingredient['original'])
            item.update({'ingredient_id': ingredient['ingredient_id'].strip(),
                         'amount': amount, 'unit': ingredient['unit'].strip(),
                         'name': ingredient['names'][code].strip()})
            row['ingredients'].append(item)
        row['instructions'] = {'steps': instructions[code]}
        translations[code] = row
    return recipe_id, source, translations
