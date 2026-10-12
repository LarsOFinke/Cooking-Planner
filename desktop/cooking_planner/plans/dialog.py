from datetime import date, timedelta

from kivy.metrics import dp

from cooking_planner.ui.dialogs import styled_popup
from cooking_planner.ui.theme import GOLD, MUTED, box, button, field, label, scroll_view, spinner
from cooking_planner.ui.strings import MEALS, t


def plan_popup(recipe: dict, locale: str, initial_day: date, initial_meal: str,
               on_save) -> None:
    content = box(padding=12, spacing=8)
    scroll = scroll_view(do_scroll_x=False)
    body = box(padding=12, spacing=10, size_hint_y=None)
    body.bind(minimum_height=body.setter('height'))
    body.add_widget(label(recipe["name"], 21, GOLD, 48, True))
    body.add_widget(label(f"{recipe['categoryLabel']}  ·  {recipe['totalMinutes']} {t(locale, 'minutes')}", 14, MUTED, 32))
    body.add_widget(label(t(locale, "select_day"), 14, MUTED, 28))
    date_row = box(False, spacing=8, size_hint_y=None, height=dp(44))
    date_input = field(text=initial_day.isoformat())
    date_row.add_widget(button("‹", lambda: shift(-1), height=42, size_hint_x=None, width=dp(42)))
    date_row.add_widget(date_input)
    date_row.add_widget(button("›", lambda: shift(1), height=42, size_hint_x=None, width=dp(42)))
    body.add_widget(date_row)
    def shift(days: int) -> None:
        try:
            current = date.fromisoformat(date_input.text)
        except ValueError:
            current = date.today()
        date_input.text = (current + timedelta(days=days)).isoformat()
    body.add_widget(label(t(locale, "select_meal"), 14, MUTED, 28))
    meal_labels = MEALS.get(locale, MEALS["en"])
    selected_meal = spinner(meal_labels[initial_meal], meal_labels.values())
    body.add_widget(selected_meal)
    body.add_widget(label(t(locale, "servings"), 14, MUTED, 28))
    serving_row = box(False, spacing=8, size_hint_y=None, height=dp(44))
    servings = spinner("1", (str(number) for number in range(1, 21)))
    serving_row.add_widget(servings)
    body.add_widget(serving_row)
    error = label("", 13, MUTED, 34)
    body.add_widget(error)
    scroll.add_widget(body)
    content.add_widget(scroll)
    actions = box(False, spacing=8, size_hint_y=None, height=dp(44))
    dialog = styled_popup(t(locale, "plan_this"), content, 0.7, 0.88)
    actions.add_widget(button(t(locale, "cancel"), dialog.dismiss))
    def save() -> None:
        try:
            selected_day = date.fromisoformat(date_input.text)
        except ValueError:
            error.text = "YYYY-MM-DD"
            return
        meal = next(code for code, name in meal_labels.items() if name == selected_meal.text)
        dialog.dismiss()
        on_save(selected_day, meal, recipe["id"], int(servings.text))
    actions.add_widget(button(t(locale, "save"), save, kind="primary"))
    content.add_widget(actions)
    dialog.open()
