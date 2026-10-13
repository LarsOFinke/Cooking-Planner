"""Values collected from the recipe editor before validation."""

from dataclasses import dataclass


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
