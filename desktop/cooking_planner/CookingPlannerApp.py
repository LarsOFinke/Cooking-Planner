import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

from cooking_planner.ApiClient import ApiClient
from cooking_planner.RecipeLocale import locale_from_filename

BG = (0.055, 0.095, 0.14, 1)
PANEL = (0.09, 0.15, 0.21, 1)
GOLD = (0.79, 0.65, 0.36, 1)
WHITE = (0.93, 0.95, 0.96, 1)


def label(text: str, height: int = 36, size: int = 16) -> Label:
    return Label(text=text, color=WHITE, font_size=dp(size), size_hint_y=None, height=dp(height), halign="left", valign="middle")


def button(text: str, callback, accent: bool = False) -> Button:
    widget = Button(text=text, size_hint_y=None, height=dp(42), background_normal="", background_color=GOLD if accent else PANEL, color=BG if accent else WHITE)
    widget.bind(on_release=lambda *_: callback())
    return widget


class CookingPlannerApp(App):
    title = "Cooking Planner"

    def __init__(self, client: ApiClient, startup_error: str | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.client = client
        self.startup_error = startup_error
        self.worker = ThreadPoolExecutor(max_workers=1)
        self.recipes: list[dict] = []
        self.selected: dict | None = None
        self.refresh_generation = 0

    def build(self) -> BoxLayout:
        Window.size = (1100, 720)
        Window.clearcolor = BG
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        title = label("COOKING PLANNER  /  Recipes & meals", 44, 23)
        title.color = GOLD
        root.add_widget(title)
        content = BoxLayout(spacing=dp(14))
        self.left = BoxLayout(orientation="vertical", size_hint_x=0.36, spacing=dp(8))
        self.right = BoxLayout(orientation="vertical", spacing=dp(8))
        content.add_widget(self.left)
        content.add_widget(self.right)
        root.add_widget(content)
        self.status = label(self.startup_error or "Loading…", 52, 13)
        root.add_widget(self.status)
        self._build_left()
        self._build_right()
        if not self.startup_error:
            Clock.schedule_once(lambda *_: self.refresh(), 0)
        return root

    def _build_left(self) -> None:
        self.left.add_widget(label("RECIPE LIBRARY", 34, 18))
        self.language = Spinner(text="en", values=("en",), size_hint_y=None, height=dp(42))
        self.language.bind(text=lambda *_: self._language_changed())
        self.left.add_widget(self.language)
        self.search = TextInput(hint_text="Search recipes or categories", multiline=False, size_hint_y=None, height=dp(42))
        self.search.bind(text=lambda *_: self._render_recipes())
        self.left.add_widget(self.search)
        scroll = ScrollView()
        self.recipe_rows = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(5))
        self.recipe_rows.bind(minimum_height=self.recipe_rows.setter("height"))
        scroll.add_widget(self.recipe_rows)
        self.left.add_widget(scroll)
        self.left.add_widget(button("+ New recipe", self.new_recipe, True))
        self.import_path = TextInput(hint_text="Path to recipes_en.json", multiline=False, size_hint_y=None, height=dp(42))
        self.left.add_widget(self.import_path)
        self.left.add_widget(button("Import JSON", self.import_json))

    def _build_right(self) -> None:
        self.right.add_widget(label("RECIPE DETAILS", 34, 18))
        self.detail = Label(text="Select a recipe or create one.", color=WHITE, halign="left", valign="top")
        self.detail.bind(size=lambda widget, _: setattr(widget, "text_size", widget.size))
        self.right.add_widget(self.detail)
        self.right.add_widget(button("Edit selected recipe", self.edit_recipe))
        self.right.add_widget(label("PLAN A MEAL", 34, 18))
        row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        self.plan_date = TextInput(text=date.today().isoformat(), multiline=False, hint_text="YYYY-MM-DD")
        self.meal_type = Spinner(text="DINNER", values=("BREAKFAST", "LUNCH", "DINNER"))
        row.add_widget(self.plan_date)
        row.add_widget(self.meal_type)
        self.right.add_widget(row)
        self.right.add_widget(button("Plan selected recipe", self.save_plan, True))
        self.plans_label = label("This week", 30)
        self.right.add_widget(self.plans_label)
        self.plans = Label(text="", color=WHITE, halign="left", valign="top", size_hint_y=None, height=dp(150))
        self.plans.bind(size=lambda widget, _: setattr(widget, "text_size", widget.size))
        self.right.add_widget(self.plans)
        self.right.add_widget(button("Refresh", self.refresh))

    def _submit(self, work, success) -> None:
        self.status.text = "Working…"
        future = self.worker.submit(work)
        def done(result) -> None:
            try:
                value = result.result()
            except Exception as error:
                message = str(error)
                Clock.schedule_once(lambda *_: setattr(self.status, "text", message), 0)
                return
            Clock.schedule_once(lambda *_: success(value), 0)
        future.add_done_callback(done)

    def refresh(self) -> None:
        self.refresh_generation += 1
        generation = self.refresh_generation
        locale = self.language.text
        try:
            focus = date.fromisoformat(self.plan_date.text)
        except ValueError:
            focus = date.today()
        start = focus - timedelta(days=focus.weekday())
        end = start + timedelta(days=6)
        self._submit(lambda: (self.client.locales(), self.client.recipes(locale), self.client.plans(start.isoformat(), end.isoformat())),
            lambda data: self._loaded(data, generation))

    def _loaded(self, data, generation: int) -> None:
        if generation != self.refresh_generation:
            return
        locales, self.recipes, plans = data
        self.language.values = tuple(locales)
        self._render_recipes()
        self.plans.text = "\n".join(f"{p['date']}  {p['mealType'].title()}: {p['recipeTitle']}" for p in plans) or "No meals planned this week."
        if self.selected:
            self.selected = next((r for r in self.recipes if r["id"] == self.selected["id"]), None)
            self._show_selected()
        self.status.text = f"{len(self.recipes)} recipes loaded"

    def _language_changed(self) -> None:
        self.selected = None
        if hasattr(self, "detail"):
            self._show_selected()
            self.refresh()

    def _render_recipes(self) -> None:
        self.recipe_rows.clear_widgets()
        query = self.search.text.casefold().strip()
        for recipe in self.recipes:
            if query and query not in (recipe["title"] + " " + recipe["category"]).casefold():
                continue
            row = button(f"{recipe['category']}  /  {recipe['title']}", lambda item=recipe: self.select(item))
            self.recipe_rows.add_widget(row)

    def select(self, recipe: dict) -> None:
        self.selected = recipe
        self._show_selected()

    def _show_selected(self) -> None:
        if not self.selected:
            self.detail.text = "Select a recipe or create one."
            return
        recipe = self.selected
        ingredients = "\n".join("• " + item for item in recipe["ingredients"])
        self.detail.text = f"{recipe['title']}  ·  {recipe['category']}  ·  {recipe['prepMinutes']} min\n\n{ingredients}\n\n{recipe['instructions']}"

    def new_recipe(self) -> None:
        self._editor(None)

    def edit_recipe(self) -> None:
        if self.selected:
            self._editor(self.selected)
        else:
            self.status.text = "Select a recipe first."

    def _editor(self, recipe: dict | None) -> None:
        from kivy.uix.popup import Popup
        body = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(7))
        fields = {}
        for name, hint, value, height in (
            ("title", "Title", recipe["title"] if recipe else "", 42),
            ("category", "Category", recipe["category"] if recipe else "", 42),
            ("prepMinutes", "Preparation minutes", str(recipe["prepMinutes"]) if recipe else "", 42),
            ("ingredients", "Ingredients, one per line", "\n".join(recipe["ingredients"]) if recipe else "", 110),
            ("instructions", "Instructions", recipe["instructions"] if recipe else "", 160),
        ):
            widget = TextInput(text=value, hint_text=hint, multiline=height > 42, size_hint_y=None, height=dp(height))
            body.add_widget(widget)
            fields[name] = widget
        popup = Popup(title="Edit recipe" if recipe else "New recipe", content=body, size_hint=(0.7, 0.88))
        def save() -> None:
            try:
                payload = {"title": fields["title"].text.strip(), "category": fields["category"].text.strip(),
                    "prepMinutes": int(fields["prepMinutes"].text),
                    "ingredients": [part.strip() for part in fields["ingredients"].text.splitlines() if part.strip()],
                    "instructions": fields["instructions"].text.strip()}
            except ValueError:
                self.status.text = "Preparation minutes must be a number."
                return
            locale = self.language.text
            self._submit(lambda: self.client.save_recipe(payload, locale, recipe["id"] if recipe else None), lambda result: self._saved(result, popup))
        body.add_widget(button("Save recipe", save, True))
        popup.open()

    def _saved(self, recipe: dict, popup) -> None:
        popup.dismiss()
        self.selected = recipe
        self.refresh()

    def import_json(self) -> None:
        path = Path(self.import_path.text).expanduser()
        try:
            locale = locale_from_filename(path)
        except ValueError as error:
            self.status.text = str(error)
            return
        def load_and_import():
            if path.stat().st_size > 2_000_000:
                raise ValueError("JSON file must be smaller than 2 MB")
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                raise ValueError("Expected a JSON array of recipes")
            return self.client.import_recipes(data, locale)
        self._submit(load_and_import, lambda _: self._imported(locale))

    def _imported(self, locale: str) -> None:
        if self.language.text == locale:
            self.refresh()
        else:
            self.language.text = locale

    def save_plan(self) -> None:
        if not self.selected:
            self.status.text = "Select a recipe first."
            return
        try:
            plan_date = date.fromisoformat(self.plan_date.text).isoformat()
        except ValueError:
            self.status.text = "Use a date like 2026-10-10."
            return
        recipe_id = self.selected["id"]
        meal_type = self.meal_type.text
        self._submit(lambda: self.client.save_plan(plan_date, meal_type, recipe_id), lambda _: self.refresh())

    def on_stop(self) -> None:
        self.worker.shutdown(wait=False, cancel_futures=True)
