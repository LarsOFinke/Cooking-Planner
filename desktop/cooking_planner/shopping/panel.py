from decimal import Decimal, InvalidOperation

from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView

from cooking_planner.ui.dialogs import confirm_popup, styled_popup
from cooking_planner.shopping.draft import item_key
from cooking_planner.ui.theme import GOLD, MUTED, box, button, field, label
from cooking_planner.ui.strings import t
from cooking_planner.ui.clipboard import get_clipboard


Clipboard = get_clipboard()


class ShoppingPanel:
    def __init__(self, plans, recipes, draft, locale, week_start, on_status, on_change):
        self.root = box(spacing=10)
        self.plans = plans
        self.recipes = recipes
        self.draft = draft
        self.locale = locale
        self.start = week_start.isoformat()
        self.on_status = on_status
        self.on_change = on_change
        self.items = []
        header = box(False, spacing=8, size_hint_y=None, height=dp(48))
        header.add_widget(label(t(locale, 'shopping'), 23, GOLD, 48, True))
        header.add_widget(button(t(locale, 'copy'), self.copy, size_hint_x=None, width=dp(150)))
        self.root.add_widget(header)
        actions_scroll = ScrollView(size_hint_y=None, height=dp(48), do_scroll_y=False)
        actions = box(False, spacing=8, size_hint_x=None, width=dp(850))
        actions.add_widget(button(t(locale, 'add_week'), self.add_all, 'primary', size_hint_x=None, width=dp(210)))
        actions.add_widget(button(t(locale, 'choose_meals'), self.choose_meals, size_hint_x=None, width=dp(160)))
        actions.add_widget(button(t(locale, 'add_item'), self.add_item, size_hint_x=None, width=dp(170)))
        actions.add_widget(button(t(locale, 'reset_checks'), self.reset, size_hint_x=None, width=dp(130)))
        actions.add_widget(button(t(locale, 'clear_list'), self.confirm_clear, 'danger', size_hint_x=None, width=dp(140)))
        actions_scroll.add_widget(actions)
        self.root.add_widget(actions_scroll)
        self.summary = label('', 15, MUTED, 36)
        self.root.add_widget(self.summary)
        scroll = ScrollView(do_scroll_x=False)
        self.rows = box(spacing=7, size_hint_y=None)
        self.rows.bind(minimum_height=self.rows.setter('height'))
        scroll.add_widget(self.rows)
        self.root.add_widget(scroll)
        self._render()

    @staticmethod
    def _amount(item):
        return format(Decimal(str(item['amount'])).normalize(), 'f')

    def _render(self):
        self.items = self.draft.items(self.start, self.plans, self.recipes)
        state = self.draft.week(self.start)
        checked = set(state['checked'])
        self.rows.clear_widgets()
        remaining = sum(item_key(item) not in checked for item in self.items)
        selected = sum(str(plan['id']) in state['plans'] for plan in self.plans)
        self.summary.text = (f"{remaining} / {len(self.items)} {t(self.locale, 'shopping_items')}"
                             f" · {selected} {t(self.locale, 'selected_meals')}")
        if not self.items:
            self.rows.add_widget(label(t(self.locale, 'empty_shopping_draft'), 17, MUTED, 80))
        for item in self.items:
            key = item_key(item)
            line = f"{item['name']}    {self._amount(item)} {item['unit']}"
            row = box(False, spacing=6, size_hint_y=None, height=dp(51))
            entry = button(('✓  ' if key in checked else '○  ') + line,
                           lambda selected_key=key: self.toggle(selected_key), height=51)
            entry.halign = 'left'
            entry.bind(size=lambda widget, _: setattr(widget, 'text_size', (widget.width - dp(24), widget.height)))
            row.add_widget(entry)
            row.add_widget(button('×', lambda selected_key=key: self.remove(selected_key), 'danger',
                                  height=51, size_hint_x=None, width=dp(48)))
            self.rows.add_widget(row)

    def _changed(self):
        self._render()
        self.on_change()

    def add_all(self):
        self.draft.add_all(self.start, self.plans)
        self._changed()

    def choose_meals(self):
        body = box(padding=12, spacing=8)
        rows = box(spacing=5, size_hint_y=None)
        rows.bind(minimum_height=rows.setter('height'))
        scroll = ScrollView(do_scroll_x=False)
        scroll.add_widget(rows)
        body.add_widget(scroll)
        dialog = styled_popup(t(self.locale, 'choose_meals'), body, 0.65, 0.75)

        def render_choices():
            rows.clear_widgets()
            selected = set(self.draft.week(self.start)['plans'])
            for plan in self.plans:
                title = f"{'✓' if str(plan['id']) in selected else '○'}  {plan['date']} · {plan['recipeTitle']} · {plan['servings']} {t(self.locale, 'servings').lower()}"
                rows.add_widget(button(title, lambda plan_id=plan['id']: choose(plan_id), height=46))
            if not self.plans:
                rows.add_widget(label(t(self.locale, 'empty_week'), 16, MUTED, 70))

        def choose(plan_id):
            self.draft.toggle_plan(self.start, plan_id)
            self._changed()
            render_choices()

        render_choices()
        dialog.open()

    def add_item(self):
        body = box(padding=16, spacing=10)
        name = field(t(self.locale, 'manual_name'))
        amount = field(t(self.locale, 'manual_amount'), text='1')
        unit = field(t(self.locale, 'manual_unit'))
        error = label('', 13, MUTED, 32)
        for widget in (name, amount, unit, error):
            body.add_widget(widget)
        actions = box(False, spacing=8, size_hint_y=None, height=dp(44))
        dialog = styled_popup(t(self.locale, 'add_item'), body, 0.48, 0.48)
        actions.add_widget(button(t(self.locale, 'cancel'), dialog.dismiss))

        def save():
            try:
                self.draft.add_custom(self.start, name.text, amount.text, unit.text)
            except (ValueError, InvalidOperation):
                error.text = t(self.locale, 'invalid_item')
                return
            dialog.dismiss()
            self._changed()

        actions.add_widget(button(t(self.locale, 'add_item'), save, 'primary'))
        body.add_widget(actions)
        dialog.open()

    def remove(self, key):
        self.draft.remove_item(self.start, key)
        self._changed()

    def toggle(self, key):
        self.draft.toggle_checked(self.start, key)
        self._changed()

    def reset(self):
        self.draft.reset_checks(self.start)
        self._changed()

    def confirm_clear(self):
        confirm_popup(t(self.locale, 'clear_question'), self.locale, self.clear,
                      title=t(self.locale, 'clear_list'), confirm_label=t(self.locale, 'clear_list'))

    def clear(self):
        self.draft.clear(self.start)
        self._changed()

    def copy(self):
        checked = set(self.draft.week(self.start)['checked'])
        lines = [f"{self._amount(item)} {item['unit']} {item['name']}"
                 for item in self.items if item_key(item) not in checked]
        try:
            Clipboard.copy('\n'.join(lines))
            self.on_status(t(self.locale, 'copied'))
        except Exception as error:
            self.on_status(str(error))
