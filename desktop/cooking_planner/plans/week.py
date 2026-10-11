from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from kivy.metrics import dp

from cooking_planner.plans.costs import planned_costs
from cooking_planner.ui.theme import GOLD, MUTED, PANEL, PANEL_LIGHT, WHITE, box, button, label, scroll_view
from cooking_planner.ui.strings import MEALS, WEEKDAYS, t


class WeekPlanner:
    def __init__(self, week_start: date, plans: list[dict], locale: str,
                 on_shift, on_today, on_pick, on_remove, recipes=None, draft=None) -> None:
        self.root = box(spacing=7)
        ending = week_start + timedelta(days=6)
        costs = planned_costs(week_start.isoformat(), plans, recipes, draft) if draft is not None else {}
        header = box(False, padding=8, spacing=6, color=PANEL,
                     size_hint_y=None, height=dp(68))
        heading = box(spacing=0)
        heading.add_widget(label(f"{week_start:%d.%m} – {ending:%d.%m.%Y}", 18, GOLD, 28, True))
        heading.add_widget(label(f"{len(plans)} {t(locale, 'planned')} · "
                                 f"{sum(plan['servings'] for plan in plans)} {t(locale, 'week_total')}",
                                 12, MUTED, 18))
        priced = sum(summary[1] for summary in costs.values())
        possible = sum(summary[2] for summary in costs.values())
        if priced:
            total = sum((summary[0] for summary in costs.values()), Decimal('0'))
            money = self._money(total, locale)
            heading.add_widget(label(t(locale, 'week_price_estimate').format(
                amount=money, priced=priced, total=possible), 11, GOLD, 18))
        header.add_widget(heading)
        controls = box(False, spacing=5, size_hint_x=None, width=dp(160))
        controls.add_widget(button('‹', lambda: on_shift(-7), size_hint_x=None, width=dp(34)))
        controls.add_widget(button(t(locale, 'today'), on_today))
        controls.add_widget(button('›', lambda: on_shift(7), size_hint_x=None, width=dp(34)))
        header.add_widget(controls)
        self.root.add_widget(header)

        scroll = scroll_view(do_scroll_x=False)
        days = box(spacing=7, padding=1, size_hint_y=None)
        self.scroll, self.days = scroll, days
        days.bind(minimum_height=days.setter('height'))
        by_slot = {(plan['date'], plan['mealType']): plan for plan in plans}
        meals = MEALS.get(locale, MEALS['en'])
        for offset in range(7):
            day = week_start + timedelta(days=offset)
            card = box(False, padding=7, spacing=7, color=PANEL_LIGHT,
                       size_hint_y=None, height=dp(90))
            day_title = WEEKDAYS.get(locale, WEEKDAYS['en'])[day.weekday()]
            if day == date.today():
                day_title += '  •'
            day_column = box(spacing=2, size_hint_x=None, width=dp(130))
            day_heading = label(day_title, 15, GOLD if day == date.today() else WHITE, 26, True)
            day_heading.shorten = True
            day_column.add_widget(day_heading)
            day_column.add_widget(label(f'{day:%d.%m}', 12, MUTED, 20))
            if day.isoformat() in costs and costs[day.isoformat()][1]:
                amount, counted, available = costs[day.isoformat()]
                day_column.add_widget(label(t(locale, 'day_price_estimate').format(
                    amount=self._money(amount, locale), priced=counted, total=available),
                    11, MUTED, 20))
            card.add_widget(day_column)
            for meal_code, meal_name in meals.items():
                plan = by_slot.get((day.isoformat(), meal_code))
                slot = box(spacing=3)
                slot.add_widget(label(meal_name, 12, MUTED, 20))
                row = box(False, spacing=4, size_hint_y=None, height=dp(38))
                if plan:
                    name = f"{plan['recipeTitle']} · {plan['servings']}"
                    entry = button(name,
                                   lambda current_day=day, current_meal=meal_code: on_pick(current_day, current_meal),
                                   height=38)
                    entry.halign = 'left'
                    entry.shorten = True
                    entry.bind(size=lambda widget, _: setattr(widget, 'text_size',
                                                              (widget.width - dp(12), widget.height)))
                    row.add_widget(entry)
                    row.add_widget(button('×', lambda current_plan=plan: on_remove(current_plan), 'danger', 38,
                                          size_hint_x=None, width=dp(32)))
                else:
                    row.add_widget(button('+  ' + t(locale, 'pick'),
                                          lambda current_day=day, current_meal=meal_code: on_pick(current_day, current_meal),
                                          height=38))
                slot.add_widget(row)
                card.add_widget(slot)
            days.add_widget(card)
        scroll.add_widget(days)
        self.root.add_widget(scroll)

    @staticmethod
    def _money(amount, locale):
        value = format(amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP), '.2f')
        return f"{value.replace('.', ',')} €" if locale == 'de' else f'€{value}'
