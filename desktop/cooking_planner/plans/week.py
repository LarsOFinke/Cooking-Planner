from datetime import date, timedelta

from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView

from cooking_planner.ui.theme import GOLD, MUTED, PANEL, WHITE, box, button, label
from cooking_planner.ui.strings import MEALS, day_label, t


class WeekPlanner:
    def __init__(self, week_start: date, plans: list[dict], locale: str,
                 on_shift, on_today, on_pick, on_remove) -> None:
        self.root = box(spacing=12)
        header = box(False, spacing=8, size_hint_y=None, height=dp(48))
        header.add_widget(label(t(locale, "week_at_glance"), 23, GOLD, 48, True))
        header.add_widget(button("‹", lambda: on_shift(-7), size_hint_x=None, width=dp(48)))
        header.add_widget(button(t(locale, "today"), on_today, size_hint_x=None, width=dp(110)))
        header.add_widget(button("›", lambda: on_shift(7), size_hint_x=None, width=dp(48)))
        self.root.add_widget(header)
        ending = week_start + timedelta(days=6)
        summary = box(False, padding=12, spacing=16, color=PANEL,
                      size_hint_y=None, height=dp(72))
        summary.add_widget(label(f"{week_start:%d.%m} – {ending:%d.%m.%Y}", 17, WHITE, 45, True))
        summary.add_widget(label(f"{len(plans)} {t(locale, 'planned')}", 16, GOLD, 45))
        summary.add_widget(label(f"{sum(plan['servings'] for plan in plans)} {t(locale, 'week_total')}", 15, MUTED, 45))
        self.root.add_widget(summary)
        scroll = ScrollView(do_scroll_x=False)
        days = box(spacing=10, size_hint_y=None)
        days.bind(minimum_height=days.setter("height"))
        by_slot = {(plan["date"], plan["mealType"]): plan for plan in plans}
        meals = MEALS.get(locale, MEALS["en"])
        for offset in range(7):
            day = week_start + timedelta(days=offset)
            card = box(padding=12, spacing=5, color=PANEL, size_hint_y=None, height=dp(190))
            day_title = day_label(day, locale)
            if day == date.today():
                day_title += "  •  " + t(locale, "today")
            card.add_widget(label(day_title, 17, GOLD if day == date.today() else WHITE, 34, True))
            for meal_code, meal_name in meals.items():
                plan = by_slot.get((day.isoformat(), meal_code))
                row = box(False, spacing=7, size_hint_y=None, height=dp(38))
                row.add_widget(label(meal_name, 13, MUTED, 38, size_hint_x=None, width=dp(115)))
                if plan:
                    name = f"{plan['recipeTitle']}   ·   {plan['servings']} {t(locale, 'servings').lower()}"
                    row.add_widget(button(name, lambda current_day=day, current_meal=meal_code: on_pick(current_day, current_meal), height=38))
                    row.add_widget(button("×", lambda current_plan=plan: on_remove(current_plan), "danger", 38,
                                          size_hint_x=None, width=dp(40)))
                else:
                    row.add_widget(button("+  " + t(locale, "pick"),
                                          lambda current_day=day, current_meal=meal_code: on_pick(current_day, current_meal), height=38))
                card.add_widget(row)
            days.add_widget(card)
        scroll.add_widget(days)
        self.root.add_widget(scroll)
