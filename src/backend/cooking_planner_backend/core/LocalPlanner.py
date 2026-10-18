"""In-process operations used by the desktop and Android application."""

from pathlib import Path

from cooking_planner_backend.repositories.Storage import Storage
from cooking_planner_backend.stores.IngredientStore import IngredientStore
from cooking_planner_backend.stores.PlanStore import PlanStore
from cooking_planner_backend.stores.RecipeStore import RecipeStore


class LocalPlanner:
    def __init__(self, data_dir: Path, catalog_dir: Path):
        if not Path(catalog_dir).is_dir():
            raise ValueError('Recipe catalogs are missing')
        self.storage = Storage(data_dir)
        try:
            self.recipe_store = RecipeStore(self.storage, catalog_dir)
            self.ingredient_store = IngredientStore(self.storage, self.recipe_store)
            self.plan_store = PlanStore(self.storage, self.recipe_store)
        except BaseException:
            self.storage.close()
            raise

    def close(self):
        self.storage.close()

    def locales(self):
        return self.recipe_store.locales()

    def recipes(self, locale):
        return self.recipe_store.list(locale)

    def catalog_info(self, locale):
        return self.recipe_store.info(locale)

    def plans(self, start, end, locale):
        return self.plan_store.list(start, end, locale)

    def ingredients(self, locale, query):
        return self.ingredient_store.search(locale, query)

    def register_ingredient(self, ingredient_id, locale, name):
        return self.ingredient_store.create(ingredient_id, locale, name)

    def ingredient_prices(self, week):
        return self.ingredient_store.prices(week)

    def reference_prices(self):
        return self.ingredient_store.reference_prices()

    def save_reference_price(self, key, price, basis_quantity):
        ingredient_id, unit = key.rsplit(':', 1)
        self.ingredient_store.save_price(ingredient_id, '*', unit, price, basis_quantity)

    def save_ingredient_price(self, week, key, price):
        ingredient_id, unit = key.rsplit(':', 1)
        self.ingredient_store.save_price(ingredient_id, week, unit, price)

    def clear_ingredient_prices(self, week):
        self.ingredient_store.clear_prices(week)

    def save_plan(self, day, meal_type, recipe_id, servings):
        return self.plan_store.save(day, meal_type, recipe_id, servings)

    def delete_plan(self, plan_id):
        self.plan_store.delete(plan_id)

    def admin_recipes(self):
        return self.recipe_store.admin_list()

    def admin_options(self):
        return self.recipe_store.options()

    def admin_recipe(self, recipe_id):
        return self.recipe_store.admin_get(recipe_id)

    def save_recipe(self, recipe_id, source_locale, translations, create, image_uploads=None):
        return self.recipe_store.save(recipe_id, source_locale, translations, create, image_uploads)

    def delete_recipe(self, recipe_id):
        self.recipe_store.delete(recipe_id)

    def admin_ingredients(self, query=''):
        return self.ingredient_store.catalog(query)

    def admin_ingredient(self, ingredient_id):
        return self.ingredient_store.catalog_entry(ingredient_id)

    def save_admin_ingredient(self, ingredient_id, translations):
        return self.ingredient_store.save_catalog_entry(ingredient_id, translations)

    def delete_admin_ingredient(self, ingredient_id):
        self.ingredient_store.delete_catalog_entry(ingredient_id)
