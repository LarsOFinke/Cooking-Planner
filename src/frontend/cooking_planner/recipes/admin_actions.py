"""Admin API actions used by the Kivy application."""

from cooking_planner.ui.dialogs import confirm_popup
from cooking_planner.ui.strings import t


class AdminActions:
    def load_admin(self):
        def load():
            return self.client.locales(), self.client.admin_recipes(), self.client.admin_options()
        def loaded(data):
            locales, records, options = data
            self.locales = tuple(locales)
            self.admin_records = records
            self.admin_options = options
            if self.tab == 'admin':
                self._render_tab()
                self._status(f"{len(records)} {t(self.locale, 'results')}")
        self._submit(load, loaded)

    def search_ingredients(self, locale, query, on_result):
        self._submit(lambda: self.client.ingredients(locale, query), on_result, show_status=False)

    def show_ingredient_admin(self):
        self.admin_mode = 'ingredients'
        self._render_tab()

    def show_recipe_admin(self):
        self.admin_mode = 'recipes'
        self._render_tab()

    def list_admin_ingredients(self, query, on_result):
        self._submit(lambda: self.client.admin_ingredients(query), on_result)

    def save_admin_ingredient(self, ingredient_id, translations):
        def saved(entry):
            self.ingredient_admin_entry = entry
            self.refresh()
        self._submit(lambda: self.client.save_admin_ingredient(ingredient_id, translations), saved)

    def save_admin_price(self, ingredient_id, unit, price, basis_quantity):
        def save_and_reload():
            self.client.save_reference_price(f'{ingredient_id}:{unit}', price, basis_quantity)
            return self.client.reference_prices()
        def saved(prices):
            self.shopping_draft.use_reference_prices(prices)
            if self.tab == 'admin' and self.admin_mode == 'ingredients':
                self.admin_panel.update_prices(prices)
            self._status(t(self.locale, 'admin_price_saved'))
        self._submit(save_and_reload, saved)

    def delete_admin_ingredient(self, ingredient_id):
        def deleted(_):
            self.ingredient_admin_entry = None
            self.refresh()
        self._submit(lambda: self.client.delete_admin_ingredient(ingredient_id), deleted)

    def select_admin_recipe(self, recipe_id):
        def loaded(entry):
            self.admin_entry = entry
            if self.tab == 'admin':
                self.admin_panel.show_recipe(entry)
        self._submit(lambda: self.client.admin_recipe(recipe_id), loaded)

    def save_admin_recipe(self, recipe_id, source_locale, translations, create):
        def saved(entry):
            self.admin_entry = entry
            self.refresh()
            self.load_admin()
        self._submit(lambda: self.client.save_recipe(recipe_id, source_locale, translations, create), saved)

    def delete_admin_recipe(self, recipe_id):
        def delete():
            def deleted(_):
                self.admin_entry = None
                self.refresh()
                self.load_admin()
            self._submit(lambda: self.client.delete_recipe(recipe_id), deleted)
        confirm_popup(t(self.locale, 'admin_delete_question'), self.locale, delete,
                      title=t(self.locale, 'admin_delete'), confirm_label=t(self.locale, 'admin_delete'))
