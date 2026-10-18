import math
import random
import webbrowser
from decimal import Decimal

from kivy.metrics import dp
from kivy.uix.label import Label

from cooking_planner.recipes.gallery import RecipePhoto, open_gallery
from cooking_planner.recipes.images import attributions, image_file
from cooking_planner.recipes.RecipeFilters import RecipeFilters
from cooking_planner.ui.strings import t
from cooking_planner.ui.theme import (
    BG,
    GOLD,
    GREEN,
    MUTED,
    PANEL,
    PANEL_LIGHT,
    WHITE,
    box,
    button,
    label,
    scroll_view,
    set_tab_active,
    tab_button,
)


class RecipeBrowser(RecipeFilters):
    PAGE_SIZE = 16

    def __init__(self, recipes: list[dict], locale: str, on_plan, on_select=None,
                 reference_price_for=None, cooking_progress=None, user_data_dir=None) -> None:
        self.recipes = recipes
        self._search_index = [
            (recipe, " ".join((recipe["name"], recipe["country"], recipe["region"],
                                recipe["categoryLabel"],
                                " ".join(item["name"] for item in recipe["ingredients"]))).casefold())
            for recipe in recipes
        ]
        self.locale = locale
        self.on_plan = on_plan
        self.on_select = on_select
        self.reference_price_for = reference_price_for
        self.cooking_progress = cooking_progress if cooking_progress is not None else {}
        self.user_data_dir = user_data_dir
        self.page = 0
        self.selected_id = None
        self.image_index = 0
        self.detail_tab = 'overview'
        self.filters_open = False
        self._search_event = None
        self.root = box(spacing=6)
        self.results_scroll = scroll_view(do_scroll_y=False)
        self.columns = box(False, spacing=6, size_hint_x=None)
        self.results_scroll.bind(width=lambda _, width: setattr(self.columns, 'width', max(width, dp(500))))
        self.results_scroll.add_widget(self.columns)
        self._build_filters()
        self._build_results()
        self._build_detail()
        self.root.add_widget(self.results_scroll)
        self.refresh()




    def _build_results(self) -> None:
        center = box(padding=7, spacing=5, color=PANEL, size_hint_x=0.36)
        self.result_count = label("", 14, WHITE, 27, True)
        center.add_widget(self.result_count)
        pager = box(padding=6, spacing=4, color=PANEL_LIGHT, hover=True, size_hint_y=None, height=dp(78))
        pager_heading = box(False, spacing=4, size_hint_y=None, height=dp(24))
        pager_heading.add_widget(label(t(self.locale, 'recipe_pages'), 13, GOLD, 24, True))
        self.page_label = label("", 12, WHITE, 24, True)
        self.page_label.halign = 'right'
        pager_heading.add_widget(self.page_label)
        pager.add_widget(pager_heading)
        pager_actions = box(False, spacing=6, size_hint_y=None, height=dp(40))
        self.previous_button = button(t(self.locale, 'previous'), self.previous_page, height=40)
        self.next_button = button(t(self.locale, 'next'), self.next_page, 'primary', height=40)
        pager_actions.add_widget(self.previous_button)
        pager_actions.add_widget(self.next_button)
        pager.add_widget(pager_actions)
        center.add_widget(pager)
        scroll = scroll_view(do_scroll_x=False)
        self.rows = box(spacing=6, size_hint_y=None)
        self.rows.bind(minimum_height=self.rows.setter("height"))
        scroll.add_widget(self.rows)
        center.add_widget(scroll)
        self.columns.add_widget(center)

    def _build_detail(self) -> None:
        detail = box(padding=7, spacing=5, color=PANEL, size_hint_x=0.64)
        header = box(False, spacing=6, size_hint_y=None, height=dp(36))
        tabs_scroll = scroll_view(do_scroll_y=False)
        tabs = box(False, spacing=5, size_hint_x=None)
        tabs_scroll.bind(width=lambda _, width: setattr(tabs, 'width', max(width, dp(320))))
        self.detail_tabs = {}
        for tab, key in (('overview', 'detail_overview'), ('ingredients', 'admin_ingredients'),
                         ('recipe', 'admin_recipe_tab')):
            control = tab_button(t(self.locale, key), lambda chosen=tab: self._show_detail_tab(chosen),
                                 tab == self.detail_tab, height=36)
            self.detail_tabs[tab] = control
            tabs.add_widget(control)
        tabs_scroll.add_widget(tabs)
        header.add_widget(tabs_scroll)
        header.add_widget(button(t(self.locale, "plan_this"), self._plan_selected, "primary",
                                 size_hint_x=None, width=dp(112), height=36))
        detail.add_widget(header)
        scroll = scroll_view(do_scroll_x=False)
        self.detail_scroll = scroll
        self.detail_body = box(spacing=5, size_hint_y=None)
        self.detail_body.bind(minimum_height=self.detail_body.setter("height"))
        scroll.add_widget(self.detail_body)
        detail.add_widget(scroll)
        self.columns.add_widget(detail)

    def _show_detail_tab(self, tab):
        self.detail_tab = tab
        for name, control in self.detail_tabs.items():
            key = {'overview': 'detail_overview', 'ingredients': 'admin_ingredients',
                   'recipe': 'admin_recipe_tab'}[name]
            set_tab_active(control, t(self.locale, key), name == tab)
        self._render_detail()




    def refresh(self) -> None:
        filtered = self._filtered()
        self.filtered = filtered
        total_pages = max(1, math.ceil(len(filtered) / self.PAGE_SIZE))
        self.page = min(self.page, total_pages - 1)
        self.result_count.text = f"{len(filtered)} {t(self.locale, 'results')}"
        self.page_label.text = f"{t(self.locale, 'page')} {self.page + 1} {t(self.locale, 'of')} {total_pages}"
        self.previous_button.disabled = self.page == 0
        self.next_button.disabled = self.page == total_pages - 1
        if self.selected_id not in {recipe["id"] for recipe in filtered}:
            self.selected_id = filtered[0]["id"] if filtered else None
        self.rows.clear_widgets()
        if not filtered:
            self.rows.add_widget(label(t(self.locale, "no_results"), 14, MUTED, 90))
        for recipe in filtered[self.page * self.PAGE_SIZE:(self.page + 1) * self.PAGE_SIZE]:
            selected = recipe["id"] == self.selected_id
            text = f"{recipe['name']}\n{recipe['country'] or t(self.locale, 'no_country')}  ·  {recipe['categoryLabel']}  ·  {recipe['totalMinutes']} {t(self.locale, 'minutes')}"
            row = button(text, lambda item=recipe: self.select(item),
                         "primary" if selected else "secondary", height=52)
            row.halign = "left"
            row.valign = "middle"
            row.bind(size=lambda widget, _: setattr(widget, "text_size", (widget.width - dp(20), widget.height)))
            self.rows.add_widget(row)
        self._render_detail()

    def select(self, recipe: dict) -> None:
        if self.selected_id != recipe["id"]:
            self.image_index = 0
        self.selected_id = recipe["id"]
        self._show_detail_tab('overview')
        if self.on_select:
            self.on_select(self.selected_id)
        self.refresh()

    def select_id(self, recipe_id: str) -> None:
        self.clear_filters()
        self.selected_id = recipe_id
        self._show_detail_tab('overview')
        filtered = self._filtered()
        index = next((i for i, recipe in enumerate(filtered) if recipe["id"] == recipe_id), 0)
        self.page = index // self.PAGE_SIZE
        self.refresh()

    def _render_detail(self) -> None:
        self.detail_body.clear_widgets()
        self.detail_scroll.scroll_y = 1
        recipe = next((item for item in self.recipes if item["id"] == self.selected_id), None)
        if recipe is None:
            self.detail_body.add_widget(label(t(self.locale, "no_results"), 16, MUTED, 90))
            return
        if self.detail_tab == 'ingredients':
            self.detail_body.add_widget(label(recipe['name'], 17, GOLD, 32, True))
            self.detail_body.add_widget(label(t(self.locale, 'ingredients'), 18, GOLD, 36, True))
            for ingredient in recipe['ingredients']:
                amount = f"{ingredient['amount']:g}" if isinstance(ingredient['amount'], float) else str(ingredient['amount'])
                quote = self._ingredient_price(ingredient)
                card = box(spacing=2, padding=5, color=PANEL_LIGHT, hover=True,
                           size_hint_y=None, height=dp(58))
                card.add_widget(label(f"{ingredient['name']}    {amount} {ingredient['unit']}",
                                      14, WHITE, 27))
                if quote is None:
                    detail = t(self.locale, 'price_unavailable')
                else:
                    price, basis, cost = quote
                    detail = (f"{self._money(cost)} · {self._money(price)} / "
                              f"{basis} {ingredient['unit']}")
                card.add_widget(label(detail, 12, GOLD if quote is not None else MUTED, 23))
                self.detail_body.add_widget(card)
            self.detail_body.add_widget(self._cost_summary(recipe))
            return
        if self.detail_tab == 'recipe':
            self.detail_body.add_widget(label(recipe['name'], 17, GOLD, 32, True))
            steps = recipe.get('instructions') or []
            progress = self.cooking_progress.setdefault(
                recipe['id'], {'steps': set(), 'ingredients': set(), 'current_step': 0})
            progress_label = label('', 13, MUTED, 25)
            self.detail_body.add_widget(progress_label)
            self._update_step_progress(progress_label, progress, len(steps))
            if not steps:
                self.detail_body.add_widget(label(t(self.locale, 'no_instructions'), 15, MUTED, 85))
            else:
                index = min(progress['current_step'], len(steps) - 1)
                progress['current_step'] = index
                controls = box(False, spacing=6, size_hint_y=None, height=dp(42))
                previous = button(f"‹  {t(self.locale, 'previous')}",
                                  lambda: self._change_step(-1), height=42,
                                  size_hint_x=None, width=dp(110))
                previous.disabled = index == 0
                controls.add_widget(previous)
                controls.add_widget(label(
                    f"{t(self.locale, 'instruction_step')} {index + 1} {t(self.locale, 'of')} {len(steps)}",
                    14, WHITE, 42, True))
                following = button(f"{t(self.locale, 'next')}  ›",
                                   lambda: self._change_step(1), height=42,
                                   size_hint_x=None, width=dp(110))
                following.disabled = index == len(steps) - 1
                controls.add_widget(following)
                self.detail_body.add_widget(controls)
                self.detail_body.add_widget(self._cooking_step_card(
                    recipe, steps[index], progress, progress_label, len(steps)))
            self.detail_body.add_widget(self._cost_summary(recipe))
            return
        photos = [(reference, photo) for reference in recipe.get("images", [])
                  if (photo := image_file(recipe["id"], reference, self.user_data_dir)) is not None]
        summary = box(False, spacing=7, size_hint_y=None, height=dp(92))
        if photos:
            self.image_index %= len(photos)
            reference, photo = photos[self.image_index]
            thumbnail = RecipePhoto(source=str(photo), size_hint=(None, None),
                                    width=dp(92), height=dp(92), fit_mode='contain')
            thumbnail.bind(on_release=lambda *_: self._open_image(recipe, photos, self.image_index))
            summary.add_widget(thumbnail)
        facts = box(spacing=1)
        origin = " · ".join(item for item in (recipe["country"] or t(self.locale, "no_country"), recipe["region"], recipe["continent"]) if item)
        facts.add_widget(label(recipe['name'], 16, GOLD, 26, True))
        facts.add_widget(label(origin, 12, MUTED, 20))
        facts.add_widget(label(f"{recipe['categoryLabel']} · {recipe['dietTypeLabel']} · {recipe['difficultyLabel']}",
                               12, WHITE, 24))
        times = (f"{t(self.locale, 'prep')} {recipe['prepMinutes']} · "
                 f"{t(self.locale, 'cook')} {recipe['cookMinutes']} · "
                 f"{t(self.locale, 'total')} {recipe['totalMinutes']} {t(self.locale, 'minutes')}")
        facts.add_widget(label(times, 11, MUTED, 19))
        summary.add_widget(facts)
        self.detail_body.add_widget(summary)
        if photos:
            if len(photos) > 1:
                controls = box(False, size_hint_y=None, height=dp(32))
                controls.add_widget(button("‹", lambda: self._change_image(-1), size_hint_x=None, width=dp(46)))
                controls.add_widget(label(f"{self.image_index + 1} / {len(photos)}", 12, MUTED, 32))
                controls.add_widget(button("›", lambda: self._change_image(1), size_hint_x=None, width=dp(46)))
                self.detail_body.add_widget(controls)
            credit = attributions().get(reference)
            if not credit or credit.get('rights_status') == 'pending':
                self.detail_body.add_widget(label(t(self.locale, 'rights_pending'), 11, MUTED, 30))
            else:
                details = f"Foto: {credit['author']} · {credit['license']}"
                if credit.get('modifications'):
                    details += f" · {credit['modifications']}"
                self.detail_body.add_widget(label(details, 11, MUTED, 30))
                if credit.get('source_url'):
                    self.detail_body.add_widget(button(t(self.locale, 'image_source'),
                                                       lambda url=credit['source_url']: webbrowser.open(url), height=32))

    def _money(self, value):
        amount = format(value, '.2f')
        return f"{amount.replace('.', ',')} €" if self.locale == 'de' else f'€{amount}'

    def _update_step_progress(self, widget, progress, total):
        widget.text = t(self.locale, 'steps_progress').format(done=len(progress['steps']), total=total)

    def _change_step(self, offset):
        recipe = next((item for item in self.recipes if item['id'] == self.selected_id), None)
        if recipe is None:
            return
        steps = recipe.get('instructions') or []
        if not steps:
            return
        progress = self.cooking_progress[recipe['id']]
        progress['current_step'] = max(0, min(len(steps) - 1, progress['current_step'] + offset))
        self._render_detail()

    def _cooking_step_card(self, recipe, step, progress, progress_label, total):
        number = step['step']
        card = box(padding=8, spacing=5, color=PANEL_LIGHT, hover=True, size_hint_y=None)
        card.bind(minimum_height=card.setter('height'))
        heading = button('', height=40)
        heading.halign = 'left'
        heading.bind(width=lambda widget, width: setattr(widget, 'text_size', (width - dp(20), None)))
        def update_step():
            done = number in progress['steps']
            card.set_base_color((0.11, 0.27, 0.21, 1) if done else PANEL_LIGHT)
            heading.set_base_color(GREEN if done else PANEL)
            heading.color = BG if done else WHITE
            heading.text = (f"✓  {t(self.locale, 'instruction_step')} {number}  ·  {t(self.locale, 'step_done')}"
                            if done else f"○  {t(self.locale, 'instruction_step')} {number}")
        def toggle_step():
            completed = progress['steps']
            completed.remove(number) if number in completed else completed.add(number)
            update_step()
            self._update_step_progress(progress_label, progress, total)
        heading.bind(on_release=lambda *_: toggle_step())
        card.add_widget(heading)
        update_step()
        text = Label(text=step['text'], color=WHITE, font_size=dp(14),
                     size_hint_y=None, halign='left', valign='top')
        text.bind(width=lambda widget, width: setattr(widget, 'text_size', (width, None)))
        text.bind(texture_size=lambda widget, size: setattr(widget, 'height', max(dp(28), size[1] + dp(6))))
        card.add_widget(text)
        ingredients = {item['ingredientId']: item for item in recipe['ingredients']}
        used = [ingredients[item_id] for item_id in step.get('ingredientIds', []) if item_id in ingredients]
        if used:
            card.add_widget(label(t(self.locale, 'step_ingredients'), 12, GOLD, 25, True))
        for ingredient in used:
            item_id = ingredient['ingredientId']
            amount = f"{ingredient['amount']:g}" if isinstance(ingredient['amount'], float) else str(ingredient['amount'])
            entry = button('', height=40)
            entry.halign = 'left'
            entry.bind(width=lambda widget, width: setattr(widget, 'text_size', (width - dp(20), None)))
            entry.bind(texture_size=lambda widget, size: setattr(widget, 'height', max(dp(40), size[1] + dp(14))))
            def update_ingredient(entry=entry, item_id=item_id, ingredient=ingredient, amount=amount):
                checked = (number, item_id) in progress['ingredients']
                entry.set_base_color(GREEN if checked else PANEL)
                entry.color = BG if checked else WHITE
                entry.text = (f"{'✓' if checked else '□'}  {amount} {ingredient['unit']}  ·  "
                              f"{ingredient['name']}")
            def toggle_ingredient(item_id=item_id, update=update_ingredient):
                key = (number, item_id)
                checked = progress['ingredients']
                checked.remove(key) if key in checked else checked.add(key)
                update()
            entry.bind(on_release=lambda *_, toggle=toggle_ingredient: toggle())
            card.add_widget(entry)
            update_ingredient()
        return card

    def _ingredient_price(self, ingredient):
        key = f"{ingredient['ingredientId']}:{ingredient['unit']}"
        quote = self.reference_price_for(key) if self.reference_price_for else None
        if quote is None:
            return None
        price, basis = quote
        return price, basis, price * Decimal(str(ingredient['amount'])) / basis

    def _cost_summary(self, recipe):
        costs = [quote[2] for ingredient in recipe['ingredients']
                 if (quote := self._ingredient_price(ingredient)) is not None]
        total = self._money(sum(costs, Decimal('0')))
        text = t(self.locale, 'recipe_estimated_cost').format(
            amount=total, priced=len(costs), total=len(recipe['ingredients']))
        return label(text, 14, GOLD, 42, True)

    def _open_image(self, recipe, photos, index):
        return open_gallery(recipe, photos, index, self.locale)

    def _plan_selected(self) -> None:
        recipe = next((item for item in self.recipes if item["id"] == self.selected_id), None)
        if recipe is not None:
            self.on_plan(recipe)

    def surprise(self) -> None:
        if self.filtered:
            recipe = random.choice(self.filtered)
            self.image_index = 0
            self.selected_id = recipe["id"]
            if self.on_select:
                self.on_select(self.selected_id)
            self.page = self.filtered.index(recipe) // self.PAGE_SIZE
            self.refresh()

    def _change_image(self, offset: int) -> None:
        self.image_index += offset
        self._render_detail()


    def previous_page(self) -> None:
        if self.page > 0:
            self.page -= 1
            self.refresh()

    def next_page(self) -> None:
        if (self.page + 1) * self.PAGE_SIZE < len(self.filtered):
            self.page += 1
            self.refresh()
