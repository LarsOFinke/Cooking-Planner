import math
import random
import webbrowser

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.label import Label

from cooking_planner.recipes.images import attributions, image_file
from cooking_planner.ui.dialogs import styled_popup
from cooking_planner.ui.theme import (GOLD, MUTED, PANEL, PANEL_LIGHT, WHITE, box, button, field,
                                      label, scroll_view, set_tab_active, spinner, tab_button)
from cooking_planner.ui.strings import t


class RecipeBrowser:
    PAGE_SIZE = 16

    def __init__(self, recipes: list[dict], locale: str, on_plan, on_select=None) -> None:
        self.recipes = recipes
        self.locale = locale
        self.on_plan = on_plan
        self.on_select = on_select
        self.page = 0
        self.selected_id = recipes[0]["id"] if recipes else None
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

    def _build_filters(self) -> None:
        outer = box(padding=6, spacing=4, color=PANEL, size_hint_y=None, height=dp(50))
        search_row = box(False, spacing=6, size_hint_y=None, height=dp(38))
        self.search = field(t(self.locale, "search"), height=38)
        self.search.bind(text=self._search_changed)
        search_row.add_widget(self.search)
        search_row.add_widget(button(t(self.locale, "surprise"), self.surprise, "primary",
                                     size_hint_x=None, width=dp(125), height=38))
        self.filter_toggle = button(t(self.locale, 'filters'), self.toggle_filters,
                                    size_hint_x=None, width=dp(115), height=38)
        search_row.add_widget(self.filter_toggle)
        outer.add_widget(search_row)
        self.root.add_widget(outer)

        body = box(padding=12, spacing=10, color=PANEL)
        scroll = scroll_view(do_scroll_x=False)
        grid = GridLayout(cols=2, spacing=dp(10), padding=dp(3), size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))
        scroll.bind(width=lambda _, width: setattr(grid, 'cols', 2 if width >= dp(340) else 1))
        self.filters = {}
        for key, property_name in (("category", "categoryLabel"), ("continent", "continent"),
                                   ("diet", "dietTypeLabel"), ("difficulty", "difficultyLabel")):
            group = box(spacing=4, size_hint_y=None, height=dp(72))
            group.add_widget(label(t(self.locale, key), 13, WHITE, 22, True))
            values = sorted({recipe[property_name] for recipe in self.recipes if recipe[property_name]})
            widget = spinner(t(self.locale, "all"), (t(self.locale, "all"), *values))
            widget.bind(text=lambda *_: self._filter_changed())
            self.filters[key] = (widget, property_name)
            group.add_widget(widget)
            grid.add_widget(group)
        time_group = box(spacing=4, size_hint_y=None, height=dp(72))
        time_group.add_widget(label(t(self.locale, "time"), 13, WHITE, 22, True))
        self.time_filter = spinner(t(self.locale, "all"),
                                   (t(self.locale, "all"), "≤ 30 min", "≤ 60 min", "≤ 120 min"))
        self.time_filter.bind(text=lambda *_: self._filter_changed())
        time_group.add_widget(self.time_filter)
        grid.add_widget(time_group)
        sort_group = box(spacing=4, size_hint_y=None, height=dp(72))
        sort_group.add_widget(label(t(self.locale, "sort"), 13, WHITE, 22, True))
        self.sort = spinner(t(self.locale, "name"),
                            (t(self.locale, "name"), t(self.locale, "shortest"), t(self.locale, "country")))
        self.sort.bind(text=lambda *_: self._filter_changed())
        sort_group.add_widget(self.sort)
        grid.add_widget(sort_group)
        scroll.add_widget(grid)
        body.add_widget(scroll)
        actions = box(False, spacing=8, size_hint_y=None, height=dp(40))
        actions.add_widget(button(t(self.locale, 'clear'), self.clear_filters, height=40))
        actions.add_widget(button(t(self.locale, 'close'), self.close_filters, 'primary', height=40))
        body.add_widget(actions)
        self.filter_dialog = styled_popup(t(self.locale, 'filters'), body, 0.74, 0.78)
        self.filter_dialog.bind(on_dismiss=lambda *_: setattr(self, 'filters_open', False))

    def toggle_filters(self) -> None:
        if self.filters_open:
            self.close_filters()
        else:
            self.filters_open = True
            self.filter_dialog.open()

    def close_filters(self) -> None:
        self.filter_dialog.dismiss()
        self.filters_open = False

    def _build_results(self) -> None:
        center = box(padding=7, spacing=5, color=PANEL, size_hint_x=0.36)
        self.result_count = label("", 14, WHITE, 27, True)
        center.add_widget(self.result_count)
        scroll = scroll_view(do_scroll_x=False)
        self.rows = box(spacing=6, size_hint_y=None)
        self.rows.bind(minimum_height=self.rows.setter("height"))
        scroll.add_widget(self.rows)
        center.add_widget(scroll)
        pager = box(False, spacing=6, size_hint_y=None, height=dp(36))
        pager.add_widget(button("‹", self.previous_page, size_hint_x=None, width=dp(46)))
        self.page_label = label("", 12, MUTED, 36)
        self.page_label.halign = "center"
        pager.add_widget(self.page_label)
        pager.add_widget(button("›", self.next_page, size_hint_x=None, width=dp(46)))
        center.add_widget(pager)
        self.columns.add_widget(center)

    def _build_detail(self) -> None:
        detail = box(padding=7, spacing=5, color=PANEL, size_hint_x=0.64)
        header = box(False, spacing=6, size_hint_y=None, height=dp(36))
        tabs = box(False, spacing=5)
        self.detail_tabs = {}
        for tab, key in (('overview', 'detail_overview'), ('ingredients', 'admin_ingredients'),
                         ('recipe', 'admin_recipe_tab')):
            control = tab_button(t(self.locale, key), lambda chosen=tab: self._show_detail_tab(chosen),
                                 tab == self.detail_tab, height=36)
            self.detail_tabs[tab] = control
            tabs.add_widget(control)
        header.add_widget(tabs)
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

    def _search_changed(self, *_args) -> None:
        if self._search_event is not None:
            self._search_event.cancel()
        self._search_event = Clock.schedule_once(lambda *_: self._filter_changed(), 0.18)

    def _filter_changed(self) -> None:
        self.page = 0
        active = sum(widget.text != t(self.locale, 'all') for widget, _ in self.filters.values())
        active += self.time_filter.text != t(self.locale, 'all')
        active += self.sort.text != t(self.locale, 'name')
        self.filter_toggle.text = f"{t(self.locale, 'filters')} ({active})" if active else t(self.locale, 'filters')
        self.refresh()

    def _filtered(self) -> list[dict]:
        query = self.search.text.casefold().strip()
        values = []
        for recipe in self.recipes:
            haystack = " ".join((recipe["name"], recipe["country"], recipe["region"], recipe["categoryLabel"],
                                 " ".join(item["name"] for item in recipe["ingredients"]))).casefold()
            if query and query not in haystack:
                continue
            if any(widget.text != t(self.locale, "all") and recipe[property_name] != widget.text
                   for widget, property_name in self.filters.values()):
                continue
            if self.time_filter.text != t(self.locale, "all") and recipe["totalMinutes"] > int(self.time_filter.text.split()[1]):
                continue
            values.append(recipe)
        if self.sort.text == t(self.locale, "shortest"):
            return sorted(values, key=lambda recipe: (recipe["totalMinutes"], recipe["name"].casefold()))
        if self.sort.text == t(self.locale, "country"):
            return sorted(values, key=lambda recipe: (recipe["country"].casefold(), recipe["name"].casefold()))
        return sorted(values, key=lambda recipe: recipe["name"].casefold())

    def refresh(self) -> None:
        filtered = self._filtered()
        self.filtered = filtered
        total_pages = max(1, math.ceil(len(filtered) / self.PAGE_SIZE))
        self.page = min(self.page, total_pages - 1)
        self.result_count.text = f"{len(filtered)} {t(self.locale, 'results')}"
        self.page_label.text = f"{t(self.locale, 'page')} {self.page + 1} {t(self.locale, 'of')} {total_pages}"
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
        if self.selected_id not in {recipe["id"] for recipe in filtered}:
            self.selected_id = filtered[0]["id"] if filtered else None
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
                self.detail_body.add_widget(label(f"{ingredient['name']}    {amount} {ingredient['unit']}",
                                                  14, WHITE, 30))
            return
        if self.detail_tab == 'recipe':
            self.detail_body.add_widget(label(recipe['name'], 17, GOLD, 32, True))
            steps = recipe.get('instructions') or []
            if not steps:
                self.detail_body.add_widget(label(t(self.locale, 'no_instructions'), 15, MUTED, 85))
            for step in steps:
                card = box(padding=8, spacing=3, color=PANEL_LIGHT, size_hint_y=None)
                card.bind(minimum_height=card.setter('height'))
                card.add_widget(label(f"{t(self.locale, 'instruction_step')} {step['step']}",
                                      13, GOLD, 24, True))
                text = Label(text=step['text'], color=WHITE, font_size=dp(14),
                             size_hint_y=None, halign='left', valign='top')
                text.bind(width=lambda widget, width: setattr(widget, 'text_size', (width, None)))
                text.bind(texture_size=lambda widget, size: setattr(widget, 'height', max(dp(28), size[1] + dp(6))))
                card.add_widget(text)
                self.detail_body.add_widget(card)
            return
        photos = [(reference, photo) for reference in recipe.get("images", [])
                  if (photo := image_file(recipe["id"], reference)) is not None]
        summary = box(False, spacing=7, size_hint_y=None, height=dp(92))
        if photos:
            self.image_index %= len(photos)
            reference, photo = photos[self.image_index]
            summary.add_widget(Image(source=str(photo), size_hint=(None, None),
                                     width=dp(92), height=dp(92),
                                     allow_stretch=True, keep_ratio=True))
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
            if credit:
                if credit.get('rights_status') == 'pending':
                    self.detail_body.add_widget(label(t(self.locale, 'rights_pending'), 11, MUTED, 30))
                else:
                    details = f"Foto: {credit['author']} · {credit['license']}"
                    if credit.get('modifications'):
                        details += f" · {credit['modifications']}"
                    self.detail_body.add_widget(label(details, 11, MUTED, 30))
                if credit.get('source_url'):
                    self.detail_body.add_widget(button(t(self.locale, 'image_source'),
                                                       lambda url=credit['source_url']: webbrowser.open(url), height=32))

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

    def clear_filters(self) -> None:
        self.search.text = ""
        for widget, _ in self.filters.values():
            widget.text = t(self.locale, "all")
        self.time_filter.text = t(self.locale, "all")
        self.sort.text = t(self.locale, "name")
        self._filter_changed()

    def previous_page(self) -> None:
        if self.page > 0:
            self.page -= 1
            self.refresh()

    def next_page(self) -> None:
        if (self.page + 1) * self.PAGE_SIZE < len(self.filtered):
            self.page += 1
            self.refresh()
