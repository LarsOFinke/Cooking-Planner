from datetime import date, timedelta

from kivy.metrics import dp
from kivy.uix.gridlayout import GridLayout

from cooking_planner.ui.theme import GOLD, MUTED, PANEL, PANEL_LIGHT, WHITE, box, button, label, scroll_view
from cooking_planner.ui.strings import MEALS, day_label, t


class WeekPlanner:
    def __init__(self, week_start: date, plans: list[dict], locale: str,
                 on_shift, on_today, on_pick, on_remove) -> None:
        self.root = box(spacing=7)
        ending = week_start + timedelta(days=6)
        header = box(False, padding=8, spacing=6, color=PANEL,
                     size_hint_y=None, height=dp(54))
        heading = box(spacing=0)
        heading.add_widget(label(f"{week_start:%d.%m} – {ending:%d.%m.%Y}", 18, GOLD, 28, True))
        heading.add_widget(label(f"{len(plans)} {t(locale, 'planned')} · "
                                 f"{sum(plan['servings'] for plan in plans)} {t(locale, 'week_total')}",
                                 12, MUTED, 20))
        header.add_widget(heading)
        controls = box(False, spacing=5, size_hint_x=None, width=dp(160))
        controls.add_widget(button('‹', lambda: on_shift(-7), size_hint_x=None, width=dp(34)))
        controls.add_widget(button(t(locale, 'today'), on_today))
        controls.add_widget(button('›', lambda: on_shift(7), size_hint_x=None, width=dp(34)))
        header.add_widget(controls)
        self.root.add_widget(header)

        scroll = scroll_view(do_scroll_x=False)
        days = GridLayout(cols=1, spacing=dp(7), padding=dp(1), size_hint_y=None)
        self.scroll, self.days = scroll, days
        days.bind(minimum_height=days.setter('height'))
        scroll.bind(width=lambda _, width: setattr(days, 'cols',
                                                   3 if width >= dp(900) else 2 if width >= dp(500) else 1))
        by_slot = {(plan['date'], plan['mealType']): plan for plan in plans}
        meals = MEALS.get(locale, MEALS['en'])
        for offset in range(7):
            day = week_start + timedelta(days=offset)
            card = box(padding=7, spacing=3, color=PANEL_LIGHT, size_hint_y=None, height=dp(155))
            day_title = day_label(day, locale)
            if day == date.today():
                day_title += '  •  ' + t(locale, 'today')
            card.add_widget(label(day_title, 16, GOLD if day == date.today() else WHITE, 28, True))
            for meal_code, meal_name in meals.items():
                plan = by_slot.get((day.isoformat(), meal_code))
                row = box(False, spacing=5, size_hint_y=None, height=dp(34))
                row.add_widget(label(meal_name, 12, MUTED, 34,
                                     size_hint_x=None, width=dp(78)))
                if plan:
                    name = f"{plan['recipeTitle']} · {plan['servings']}"
                    entry = button(name,
                                   lambda current_day=day, current_meal=meal_code: on_pick(current_day, current_meal),
                                   height=34)
                    entry.halign = 'left'
                    entry.shorten = True
                    entry.bind(size=lambda widget, _: setattr(widget, 'text_size',
                                                              (widget.width - dp(12), widget.height)))
                    row.add_widget(entry)
                    row.add_widget(button('×', lambda current_plan=plan: on_remove(current_plan), 'danger', 34,
                                          size_hint_x=None, width=dp(34)))
                else:
                    row.add_widget(button('+  ' + t(locale, 'pick'),
                                          lambda current_day=day, current_meal=meal_code: on_pick(current_day, current_meal),
                                          height=34))
                card.add_widget(row)
            days.add_widget(card)
        scroll.add_widget(days)
        self.root.add_widget(scroll)
