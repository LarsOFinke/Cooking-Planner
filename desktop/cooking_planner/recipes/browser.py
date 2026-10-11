import math
import random
import webbrowser

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.image import Image
from kivy.uix.scrollview import ScrollView

from cooking_planner.recipes.images import attributions, image_file
from cooking_planner.ui.theme import GOLD, MUTED, PANEL, WHITE, box, button, field, label, spinner
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
        self._search_event = None
        self.root = box(spacing=10)
        self.results_scroll = ScrollView(do_scroll_y=False)
        self.columns = box(False, spacing=12, size_hint_x=None, width=dp(1050))
        self.results_scroll.add_widget(self.columns)
        self._build_filters()
        self._build_results()
        self._build_detail()
        self.root.add_widget(self.results_scroll)
        self.refresh()

    def _build_filters(self) -> None:
        outer = box(padding=10, spacing=8, color=PANEL, size_hint_y=None, height=dp(150))
        search_row = box(False, spacing=8, size_hint_y=None, height=dp(46))
        self.search = field(t(self.locale, "search"), height=46)
        self.search.bind(text=self._search_changed)
        search_row.add_widget(self.search)
        search_row.add_widget(button(t(self.locale, "surprise"), self.surprise, "primary",
                                     size_hint_x=None, width=dp(160), height=46))
        search_row.add_widget(button(t(self.locale, "clear"), self.clear_filters,
                                     size_hint_x=None, width=dp(175), height=46))
        outer.add_widget(search_row)
        scroll = ScrollView(do_scroll_y=False)
        row = box(False, spacing=10, size_hint_x=None, width=dp(960))
        self.filters = {}
        for key, property_name in (("category", "categoryLabel"), ("continent", "continent"),
                                   ("diet", "dietTypeLabel"), ("difficulty", "difficultyLabel")):
            group = box(spacing=4, size_hint_x=None, width=dp(150))
            group.add_widget(label(t(self.locale, key), 13, MUTED, 26))
            values = sorted({recipe[property_name] for recipe in self.recipes if recipe[property_name]})
            widget = spinner(t(self.locale, "all"), (t(self.locale, "all"), *values))
            widget.bind(text=lambda *_: self._filter_changed())
            self.filters[key] = (widget, property_name)
            group.add_widget(widget)
            row.add_widget(group)
        time_group = box(spacing=4, size_hint_x=None, width=dp(130))
        time_group.add_widget(label(t(self.locale, "time"), 13, MUTED, 26))
        self.time_filter = spinner(t(self.locale, "all"),
                                   (t(self.locale, "all"), "≤ 30 min", "≤ 60 min", "≤ 120 min"))
        self.time_filter.bind(text=lambda *_: self._filter_changed())
        time_group.add_widget(self.time_filter)
        row.add_widget(time_group)
        sort_group = box(spacing=4, size_hint_x=None, width=dp(140))
        sort_group.add_widget(label(t(self.locale, "sort"), 13, MUTED, 26))
        self.sort = spinner(t(self.locale, "name"),
                            (t(self.locale, "name"), t(self.locale, "shortest"), t(self.locale, "country")))
        self.sort.bind(text=lambda *_: self._filter_changed())
        sort_group.add_widget(self.sort)
        row.add_widget(sort_group)
        scroll.add_widget(row)
        outer.add_widget(scroll)
        self.root.add_widget(outer)

    def _build_results(self) -> None:
        center = box(padding=12, spacing=8, color=PANEL, size_hint_x=0.43)
        self.result_count = label("", 17, WHITE, 38, True)
        center.add_widget(self.result_count)
        scroll = ScrollView(do_scroll_x=False)
        self.rows = box(spacing=6, size_hint_y=None)
        self.rows.bind(minimum_height=self.rows.setter("height"))
        scroll.add_widget(self.rows)
        center.add_widget(scroll)
        pager = box(False, spacing=6, size_hint_y=None, height=dp(42))
        pager.add_widget(button("‹", self.previous_page, size_hint_x=None, width=dp(46)))
        self.page_label = label("", 13, MUTED, 42)
        self.page_label.halign = "center"
        pager.add_widget(self.page_label)
        pager.add_widget(button("›", self.next_page, size_hint_x=None, width=dp(46)))
        center.add_widget(pager)
        self.columns.add_widget(center)

    def _build_detail(self) -> None:
        detail = box(padding=14, spacing=8, color=PANEL, size_hint_x=0.57)
        scroll = ScrollView(do_scroll_x=False)
        self.detail_body = box(spacing=7, size_hint_y=None)
        self.detail_body.bind(minimum_height=self.detail_body.setter("height"))
        scroll.add_widget(self.detail_body)
        detail.add_widget(scroll)
        detail.add_widget(button(t(self.locale, "plan_this"), self._plan_selected, "primary", height=50))
        self.columns.add_widget(detail)

    def _search_changed(self, *_args) -> None:
        if self._search_event is not None:
            self._search_event.cancel()
        self._search_event = Clock.schedule_once(lambda *_: self._filter_changed(), 0.18)

    def _filter_changed(self) -> None:
        self.page = 0
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
                         "primary" if selected else "secondary", height=70)
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
        if self.on_select:
            self.on_select(self.selected_id)
        self.refresh()

    def select_id(self, recipe_id: str) -> None:
        self.clear_filters()
        self.selected_id = recipe_id
        filtered = self._filtered()
        index = next((i for i, recipe in enumerate(filtered) if recipe["id"] == recipe_id), 0)
        self.page = index // self.PAGE_SIZE
        self.refresh()

    def _render_detail(self) -> None:
        self.detail_body.clear_widgets()
        recipe = next((item for item in self.recipes if item["id"] == self.selected_id), None)
        if recipe is None:
            self.detail_body.add_widget(label(t(self.locale, "no_results"), 16, MUTED, 90))
            return
        photos = [(reference, photo) for reference in recipe.get("images", [])
                  if (photo := image_file(recipe["id"], reference)) is not None]
        if photos:
            self.image_index %= len(photos)
            reference, photo = photos[self.image_index]
            self.detail_body.add_widget(Image(source=str(photo), size_hint_y=None, height=dp(240),
                                              allow_stretch=True, keep_ratio=True))
            if len(photos) > 1:
                controls = box(False, size_hint_y=None, height=dp(38))
                controls.add_widget(button("‹", lambda: self._change_image(-1), size_hint_x=None, width=dp(46)))
                controls.add_widget(label(f"{self.image_index + 1} / {len(photos)}", 13, MUTED, 38))
                controls.add_widget(button("›", lambda: self._change_image(1), size_hint_x=None, width=dp(46)))
                self.detail_body.add_widget(controls)
            credit = attributions().get(reference)
            if credit:
                if credit.get('rights_status') == 'pending':
                    self.detail_body.add_widget(label(t(self.locale, 'rights_pending'), 11, MUTED, 36))
                else:
                    details = f"Foto: {credit['author']} · {credit['license']}"
                    if credit.get('modifications'):
                        details += f" · {credit['modifications']}"
                    self.detail_body.add_widget(label(details, 11, MUTED, 36))
                if credit.get('source_url'):
                    self.detail_body.add_widget(button(t(self.locale, 'image_source'),
                                                       lambda url=credit['source_url']: webbrowser.open(url), height=38))
        self.detail_body.add_widget(label(recipe["name"], 24, GOLD, 72, True))
        origin = " · ".join(item for item in (recipe["country"] or t(self.locale, "no_country"), recipe["region"], recipe["continent"]) if item)
        self.detail_body.add_widget(label(origin, 14, MUTED, 36))
        self.detail_body.add_widget(label(f"{recipe['categoryLabel']}   •   {recipe['dietTypeLabel']}   •   {recipe['difficultyLabel']}", 15, WHITE, 40))
        times = f"{t(self.locale, 'prep')} {recipe['prepMinutes']}  ·  {t(self.locale, 'cook')} {recipe['cookMinutes']}  ·  {t(self.locale, 'total')} {recipe['totalMinutes']} {t(self.locale, 'minutes')}"
        self.detail_body.add_widget(label(times, 14, MUTED, 42))
        self.detail_body.add_widget(label(t(self.locale, "ingredients"), 18, WHITE, 42, True))
        for ingredient in recipe["ingredients"]:
            amount = f"{ingredient['amount']:g}" if isinstance(ingredient["amount"], float) else str(ingredient["amount"])
            self.detail_body.add_widget(label(f"  {ingredient['name']}    {amount} {ingredient['unit']}", 15, WHITE, 32))
        self.detail_body.add_widget(label("", height=14))
        self.detail_body.add_widget(label(t(self.locale, "no_instructions"), 14, MUTED, 75))
        self.detail_body.add_widget(label(t(self.locale, "estimate") + " · " + recipe["dataSourceLabel"], 13, MUTED, 30))

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
