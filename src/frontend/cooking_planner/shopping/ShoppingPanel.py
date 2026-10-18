
from datetime import date, timedelta

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.gridlayout import GridLayout

from cooking_planner.shopping.dialogs import open_add_item_dialog
from cooking_planner.shopping.ShoppingDraft import UPCOMING, item_key
from cooking_planner.shopping.ShoppingRendering import ShoppingRendering
from cooking_planner.ui.clipboard import get_clipboard
from cooking_planner.ui.dialogs import confirm_popup, styled_popup
from cooking_planner.ui.strings import MEALS, day_label, t
from cooking_planner.ui.theme import GOLD, MUTED, PANEL, WHITE, box, button, label, scroll_view

Clipboard = get_clipboard()


class ShoppingPanel(ShoppingRendering):
    def __init__(self, plans, recipes, draft, locale, week_start, on_status, on_ingredient_search=None,
                 upcoming=False):
        self.root = box(spacing=7)
        self.plans = [plan for plan in plans if plan['date'] >= week_start.isoformat()] if upcoming else plans
        self.recipes = recipes
        self.draft = draft
        self.locale = locale
        self.start = UPCOMING if upcoming else week_start.isoformat()
        self.week_start = week_start
        if upcoming:
            monday = week_start - timedelta(days=week_start.weekday())
            if draft.use_upcoming(monday.isoformat()):
                draft.update_bought_plans(UPCOMING, self.plans, recipes)
        self.on_status = on_status
        self.on_ingredient_search = on_ingredient_search
        self.items = []
        header = box(False, spacing=8, size_hint_y=None, height=dp(42))
        header.add_widget(label(t(locale, 'shopping'), 19, GOLD, 42, True))
        header.add_widget(button(t(locale, 'copy'), self.copy, size_hint_x=None, width=dp(120)))
        self.root.add_widget(header)
        actions = GridLayout(cols=3, spacing=dp(5), size_hint_y=None,
                             row_default_height=dp(40), row_force_default=True)
        self.actions = actions
        actions.add_widget(button(t(locale, 'add_item'), self.add_item, 'primary', height=40))
        actions.add_widget(button(t(locale, 'shopping_from_plan'), self.choose_meals, height=40))
        actions.add_widget(button(t(locale, 'shopping_choose_items'), self.choose_items, height=40))
        actions.add_widget(button(t(locale, 'shopping_add_day'), self.choose_day, height=40))
        actions.add_widget(button(t(locale, 'reset_checks'), self.reset, height=40))
        actions.add_widget(button(t(locale, 'clear_all'), self.confirm_clear, 'danger', height=40))
        def layout_actions(_, width):
            actions.cols = 3 if width >= dp(600) else 2
            actions.height = dp(85 if actions.cols == 3 else 130)
        actions.bind(width=layout_actions)
        layout_actions(actions, actions.width)
        self.root.add_widget(actions)
        self.notice = label(t(locale, 'shopping_selection_help'), 13, MUTED, 30)
        self.notice.shorten = True
        self.root.add_widget(self.notice)
        summary = box(False, padding=8, spacing=8, color=PANEL, hover=True,
                      size_hint_y=None, height=dp(46))
        self.summary = label('', 15, WHITE, 30, True)
        self.meal_summary = label('', 13, MUTED, 30)
        self.price_summary = label('', 13, GOLD, 30)
        summary.add_widget(self.summary)
        summary.add_widget(self.meal_summary)
        summary.add_widget(self.price_summary)
        self.compact_summary = False
        def layout_summary(_, width):
            compact = width < dp(650)
            self.compact_summary = compact
            self.meal_summary.size_hint_x = None if compact else 1
            self.meal_summary.width = 0 if compact else width / 3
            self.meal_summary.opacity = 0 if compact else 1
            self.notice.height = dp(22 if compact else 30)
            self._render_summary()
        summary.bind(width=layout_summary)
        self.root.add_widget(summary)
        heading_scroll = scroll_view(do_scroll_x=False, do_scroll_y=False,
                                     size_hint_y=None, height=dp(25), bar_width=0)
        self.heading_scroll = heading_scroll
        heading = self._column_header()
        heading_scroll.bind(width=lambda _, width: setattr(heading, 'width', max(width, dp(530))))
        heading_scroll.add_widget(heading)
        self.root.add_widget(heading_scroll)
        scroll = scroll_view(do_scroll_x=True)
        self.scroll = scroll
        scroll.bind(scroll_x=lambda _, position: setattr(heading_scroll, 'scroll_x', position))
        self.compact_list = False
        scroll.bind(height=self._resize_items)
        self.rows = box(spacing=5, size_hint_x=None, size_hint_y=None)
        scroll.bind(width=lambda _, width: setattr(self.rows, 'width', max(width, dp(530))))
        self.rows.bind(minimum_height=self.rows.setter('height'))
        scroll.add_widget(self.rows)
        self.root.add_widget(scroll)
        self._render()

    def set_status(self, message):
        self.notice.text = str(message)

    def _resize_items(self, _, height):
        compact = height < dp(150)
        if compact != self.compact_list:
            self.compact_list = compact
            self._render()











    def _changed(self):
        self._render()

    def add_all(self):
        self.draft.add_all(self.start, self.plans)
        self._changed()
        self.notice.text = t(self.locale, 'shopping_all_meals_selected')

    def choose_day(self):
        body = box(padding=12, spacing=7)
        body.add_widget(label(t(self.locale, 'shopping_add_day_help'), 14, MUTED, 38))
        days = (sorted({date.fromisoformat(plan['date']) for plan in self.plans}) if self.start == UPCOMING else
                [self.week_start + timedelta(days=offset) for offset in range(7)])
        if self.start == UPCOMING:
            rows = box(spacing=5, size_hint_y=None)
            rows.bind(minimum_height=rows.setter('height'))
            scroll = scroll_view(do_scroll_x=False)
            scroll.add_widget(rows)
            body.add_widget(scroll)
        else:
            rows = body
        for day in days:
            count = sum(plan['date'] == day.isoformat() for plan in self.plans)
            control = button(f"{day_label(day, self.locale)} · {count} "
                             f"{t(self.locale, 'selected_meal' if count == 1 else 'selected_meals')}",
                             lambda chosen=day: select(chosen), height=42)
            control.disabled = count == 0
            rows.add_widget(control)
        dialog = styled_popup(t(self.locale, 'shopping_add_day'), body, 0.62, 0.78)

        def select(day):
            count = self.draft.add_day(self.start, self.plans, day.isoformat(), self.recipes)
            if count:
                self._changed()
                self.notice.text = t(self.locale, 'shopping_day_added').format(day=day_label(day, self.locale))
            dialog.dismiss()

        dialog.open()

    def choose_meals(self):
        body = box(padding=12, spacing=8)
        body.add_widget(label(t(self.locale, 'shopping_choose_help'), 14, MUTED, 38))
        rows = box(spacing=5, size_hint_y=None)
        rows.bind(minimum_height=rows.setter('height'))
        scroll = scroll_view(do_scroll_x=False)
        scroll.add_widget(rows)
        body.add_widget(scroll)
        actions = box(False, spacing=6, size_hint_y=None, height=dp(42))
        actions.add_widget(button(t(self.locale, 'shopping_select_all'),
                                  lambda: select_all(True)))
        actions.add_widget(button(t(self.locale, 'shopping_select_none'),
                                  lambda: select_all(False)))
        actions.add_widget(button(t(self.locale, 'close'), lambda: dialog.dismiss(), 'primary'))
        body.add_widget(actions)
        dialog = styled_popup(t(self.locale, 'choose_meals'), body, 0.65, 0.75)

        def render_choices():
            rows.clear_widgets()
            selected = self.draft.selected_plan_ids(self.start, self.plans)
            bought = self.draft.bought_plan_ids(self.start, self.plans, self.recipes)
            by_id = {recipe['id']: recipe for recipe in self.recipes}
            for plan in self.plans:
                recipe = by_id.get(plan['recipeId'])
                count = len(recipe['ingredients']) if recipe else 0
                meal = MEALS.get(self.locale, MEALS['en']).get(plan.get('mealType'), '')
                is_selected = str(plan['id']) in selected
                action = t(self.locale, 'shopping_refresh_meal' if is_selected else 'shopping_add_meal')
                status = f" · {t(self.locale, 'shopping_recipe_bought')}" if str(plan['id']) in bought else ''
                title = (f"{action} · {plan['date']} · {meal} · "
                         f"{plan['recipeTitle']} · {plan['servings']} {t(self.locale, 'servings').lower()} "
                         f"· {count} {t(self.locale, 'ingredients_count').lower()}{status}")
                row = box(False, spacing=5, size_hint_y=None, height=dp(46))
                row.add_widget(self._choice_button(title, lambda plan_id=plan['id']: choose(plan_id)))
                if is_selected:
                    row.add_widget(button(t(self.locale, 'remove'),
                                          lambda plan_id=plan['id']: remove(plan_id),
                                          'danger_outline', height=46, size_hint_x=None, width=dp(94)))
                rows.add_widget(row)
            if not self.plans:
                rows.add_widget(label(t(self.locale, 'empty_week'), 16, MUTED, 70))

        def choose(plan_id):
            self.draft.add_plan(self.start, plan_id, self.plans, self.recipes)
            self._changed()
            render_choices()
            self.notice.text = t(self.locale, 'shopping_selection_updated')

        def remove(plan_id):
            self.draft.toggle_plan(self.start, plan_id)
            self._changed()
            render_choices()
            self.notice.text = t(self.locale, 'shopping_selection_updated')

        def select_all(selected):
            self.draft.select_all_plans(self.start, self.plans, selected, self.recipes)
            self._changed()
            render_choices()
            self.notice.text = t(self.locale, 'shopping_selection_updated')

        render_choices()
        dialog.open()

    def choose_items(self):
        body = box(padding=12, spacing=8)
        body.add_widget(label(t(self.locale, 'shopping_choose_items_help'), 14, MUTED, 42))
        rows = box(spacing=5, size_hint_y=None)
        rows.bind(minimum_height=rows.setter('height'))
        scroll = scroll_view(do_scroll_x=False)
        scroll.add_widget(rows)
        body.add_widget(scroll)
        actions = box(False, spacing=6, size_hint_y=None, height=dp(42))
        actions.add_widget(button(t(self.locale, 'shopping_include_all'), lambda: include_all()))
        actions.add_widget(button(t(self.locale, 'close'), lambda: dialog.dismiss(), 'primary'))
        body.add_widget(actions)
        dialog = styled_popup(t(self.locale, 'shopping_choose_items'), body, 0.7, 0.75)

        def planned():
            return self.draft.planned_items(self.start, self.plans, self.recipes)

        def render_choices():
            rows.clear_widgets()
            excluded = set(self.draft.week(self.start)['excluded'])
            for item in planned():
                key = item_key(item)
                title = f"{'○' if key in excluded else '✓'}  {item['name']} · {self._amount(item)} {item['unit']}"
                rows.add_widget(self._choice_button(title, lambda item_key_value=key: choose(item_key_value)))
            if not rows.children:
                rows.add_widget(label(t(self.locale, 'shopping_no_selected_meals'), 14, MUTED, 70))

        def choose(key):
            included = key in self.draft.week(self.start)['excluded']
            self.draft.set_item_included(self.start, key, included)
            self._changed()
            render_choices()
            self.notice.text = t(self.locale, 'shopping_selection_updated')

        def include_all():
            self.draft.include_items(self.start, {item_key(item) for item in planned()})
            self._changed()
            render_choices()
            self.notice.text = t(self.locale, 'shopping_selection_updated')

        render_choices()
        dialog.open()

    def add_item(self):
        def added():
            self._changed()
            self.notice.text = t(self.locale, 'item_added')

        open_add_item_dialog(self.locale, self.draft, self.start, self.on_ingredient_search,
                             added, styled_popup, lambda callback, delay: Clock.schedule_once(callback, delay))

    def remove(self, key):
        try:
            self.draft.remove_item(self.start, key)
        except RuntimeError as error:
            self.set_status(str(error))
            self.on_status(str(error))
            return
        self._changed()
        self.notice.text = t(self.locale, 'shopping_item_removed')

    def toggle(self, key):
        self.draft.toggle_checked(self.start, key)
        self.draft.update_bought_plans(self.start, self.plans, self.recipes)
        self._changed()

    def reset(self):
        self.draft.reset_checks(self.start)
        self._changed()
        self.notice.text = t(self.locale, 'shopping_checks_reset')

    def confirm_clear(self):
        confirm_popup(t(self.locale, 'clear_question'), self.locale, self.clear,
                      title=t(self.locale, 'clear_all'), confirm_label=t(self.locale, 'clear_all'))

    def clear(self):
        try:
            self.draft.clear(self.start, self.plans)
        except RuntimeError as error:
            self._changed()
            self.set_status(str(error))
            self.on_status(str(error))
            return
        self._changed()
        self.notice.text = t(self.locale, 'shopping_list_cleared')

    def copy(self):
        checked = set(self.draft.week(self.start)['checked'])
        lines = []
        for item in self.items:
            key = item_key(item)
            if key in checked:
                continue
            line = f"{self._amount(item)} {item['unit']} {item['name']}"
            if (price := self.draft.price_for(self.start, key, item['amount'])) is not None:
                line += f" · {self._money(price)}"
            lines.append(line)
        try:
            Clipboard.copy('\n'.join(lines))
            self.on_status(t(self.locale, 'copied'))
        except Exception as error:
            self.set_status(str(error))
            self.on_status(str(error))
