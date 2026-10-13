"""Filter controls and search behavior for the recipe browser."""

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.gridlayout import GridLayout

from cooking_planner.ui.dialogs import styled_popup
from cooking_planner.ui.strings import t
from cooking_planner.ui.theme import PANEL, WHITE, box, button, field, label, scroll_view, spinner


class RecipeFilters:
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

    def clear_filters(self) -> None:
        self.search.text = ""
        for widget, _ in self.filters.values():
            widget.text = t(self.locale, "all")
        self.time_filter.text = t(self.locale, "all")
        self.sort.text = t(self.locale, "name")
        self._filter_changed()
