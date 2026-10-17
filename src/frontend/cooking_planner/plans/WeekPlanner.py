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
        controls = box(False, spacing=5, size_hint_x=None, width=dp(180))
        controls.add_widget(button('‹', lambda: on_shift(-7), 'outline',
                                   size_hint_x=None, width=dp(40)))
        controls.add_widget(button(t(locale, 'today'), on_today, 'primary'))
        controls.add_widget(button('›', lambda: on_shift(7), 'outline',
                                   size_hint_x=None, width=dp(40)))
        header.add_widget(controls)
        def layout_header(_, width):
            compact = width < dp(460)
            header.orientation = 'vertical' if compact else 'horizontal'
            header.height = dp(150 if compact else 68)
            controls.size_hint_x = 1 if compact else None
            controls.width = width if compact else dp(180)
        header.bind(width=layout_header)
        layout_header(header, header.width)
        self.root.add_widget(header)

        scroll = scroll_view(do_scroll_x=True)
        days = box(spacing=7, padding=1, size_hint_x=None, size_hint_y=None)
        self.scroll, self.days = scroll, days
        scroll.bind(width=lambda _, width: setattr(days, 'width', max(width, dp(650))))
        days.bind(minimum_height=days.setter('height'))
        by_slot = {(plan['date'], plan['mealType']): plan for plan in plans}
        meals = MEALS.get(locale, MEALS['en'])
        for offset in range(7):
            day = week_start + timedelta(days=offset)
            day_key = day.isoformat()
            day_plans = [plan for plan in plans if plan['date'] == day_key]
            card = box(padding=9, spacing=7, color=PANEL_LIGHT, hover=True,
                       size_hint_y=None, height=dp(142))
            day_header = box(False, spacing=9, size_hint_y=None, height=dp(40))
            day_title = WEEKDAYS.get(locale, WEEKDAYS['en'])[day.weekday()]
            if day == date.today():
                day_title += '  •'
            day_column = box(spacing=0, size_hint_x=None, width=dp(150))
            day_heading = label(day_title, 15, GOLD if day == date.today() else WHITE, 22, True)
            day_heading.shorten = True
            day_column.add_widget(day_heading)
            day_column.add_widget(label(f'{day:%d.%m}', 12, MUTED, 18))
            day_header.add_widget(day_column)
            if day_plans:
                amount, counted, available = costs.get(day_key, (Decimal('0'), 0, 0))
                summary = box(spacing=0)
                title = (t(locale, 'day_price_estimate').format(amount=self._money(amount, locale))
                         if counted else t(locale, 'day_price_unavailable'))
                estimate = label(title, 15, GOLD if counted else MUTED, 22, True)
                estimate.shorten = True
                summary.add_widget(estimate)
                coverage = label(t(locale, 'day_price_coverage').format(
                    priced=counted, total=available), 11, MUTED, 18)
                coverage.shorten = True
                summary.add_widget(coverage)
                day_header.add_widget(summary)
            card.add_widget(day_header)
            meal_row = box(False, spacing=7, size_hint_y=None, height=dp(68))
            for meal_code, meal_name in meals.items():
                plan = by_slot.get((day_key, meal_code))
                slot = box(padding=5, spacing=3, color=PANEL)
                slot.add_widget(label(meal_name, 12, MUTED, 16))
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
                    row.add_widget(button('×', lambda current_plan=plan: on_remove(current_plan),
                                          'danger_outline', 38, size_hint_x=None, width=dp(36)))
                else:
                    row.add_widget(button('+  ' + t(locale, 'pick'),
                                          lambda current_day=day, current_meal=meal_code: on_pick(current_day, current_meal),
                                          'outline', height=38))
                slot.add_widget(row)
                meal_row.add_widget(slot)
            card.add_widget(meal_row)
            days.add_widget(card)
        scroll.add_widget(days)
        self.root.add_widget(scroll)

    @staticmethod
    def _money(amount, locale):
        value = format(amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP), '.2f')
        return f"{value.replace('.', ',')} €" if locale == 'de' else f'€{value}'
