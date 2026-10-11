from decimal import Decimal, InvalidOperation

from kivy.metrics import dp

from cooking_planner.ui.dialogs import confirm_popup, styled_popup
from cooking_planner.shopping.draft import item_key, normalize_price
from cooking_planner.ui.theme import BG, GOLD, GREEN, MUTED, PANEL, PANEL_LIGHT, RED, WHITE, box, button, field, label, scroll_view
from cooking_planner.ui.strings import t
from cooking_planner.ui.clipboard import get_clipboard


Clipboard = get_clipboard()


class ShoppingPanel:
    def __init__(self, plans, recipes, draft, locale, week_start, on_status):
        self.root = box(spacing=7)
        self.plans = plans
        self.recipes = recipes
        self.draft = draft
        self.locale = locale
        self.start = week_start.isoformat()
        self.on_status = on_status
        self.items = []
        header = box(False, spacing=8, size_hint_y=None, height=dp(42))
        header.add_widget(label(t(locale, 'shopping'), 19, GOLD, 42, True))
        header.add_widget(button(t(locale, 'copy'), self.copy, size_hint_x=None, width=dp(120)))
        self.root.add_widget(header)
        actions = box(spacing=5, size_hint_y=None, height=dp(45))
        self.actions = actions
        primary = box(False, spacing=5, size_hint_y=None, height=dp(40))
        primary.add_widget(button(t(locale, 'add_item'), self.add_item, 'primary', height=40))
        primary.add_widget(button(t(locale, 'choose_meals'), self.choose_meals, height=40))
        primary.add_widget(button(t(locale, 'add_week_short'), self.add_all, height=40))
        self.more_button = button(t(locale, 'more_actions'), self.toggle_actions, height=40)
        primary.add_widget(self.more_button)
        actions.add_widget(primary)
        secondary = box(False, spacing=5, size_hint_y=None, height=0, opacity=0, disabled=True)
        self.more_row = secondary
        secondary.add_widget(button(t(locale, 'reset_checks'), self.reset, height=40))
        secondary.add_widget(button(t(locale, 'clear_list'), self.confirm_clear, 'danger', height=40))
        actions.add_widget(secondary)
        self.root.add_widget(actions)
        summary = box(False, padding=8, spacing=8, color=PANEL,
                      size_hint_y=None, height=dp(46))
        self.summary = label('', 15, WHITE, 30, True)
        self.meal_summary = label('', 13, MUTED, 30)
        self.price_summary = label('', 13, GOLD, 30)
        summary.add_widget(self.summary)
        summary.add_widget(self.meal_summary)
        summary.add_widget(self.price_summary)
        self.root.add_widget(summary)
        scroll = scroll_view(do_scroll_x=False)
        self.scroll = scroll
        self.compact_list = False
        scroll.bind(height=self._resize_items)
        self.rows = box(spacing=5, size_hint_y=None)
        self.rows.bind(minimum_height=self.rows.setter('height'))
        scroll.add_widget(self.rows)
        self.root.add_widget(scroll)
        self._render()

    def toggle_actions(self):
        expanded = self.more_row.height == 0
        self.more_row.height = dp(40) if expanded else 0
        self.more_row.opacity = int(expanded)
        self.more_row.disabled = not expanded
        self.actions.height = dp(90 if expanded else 45)
        self.more_button.text = t(self.locale, 'less_actions' if expanded else 'more_actions')

    def _resize_items(self, _, height):
        compact = height < dp(150)
        if compact != self.compact_list:
            self.compact_list = compact
            self._render()

    @staticmethod
    def _amount(item):
        return format(Decimal(str(item['amount'])).normalize(), 'f')

    @staticmethod
    def _name_width(row_width):
        return max(dp(80), min(dp(240), row_width * 0.28, row_width - dp(381)))

    def _money(self, value):
        amount = format(value, '.2f')
        if self.locale == 'de':
            return f"{amount.replace('.', ',')} €"
        return f'€{amount}'

    def _update_price_summary(self):
        prices = [price for item in self.items
                  if (price := self.draft.price_for(self.start, item_key(item))) is not None]
        total = sum(prices, Decimal('0'))
        self.price_summary.color = GOLD
        self.price_summary.text = t(self.locale, 'shopping_prices_summary').format(
            count=len(prices), total=len(self.items), amount=self._money(total))

    def _save_price(self, key, widget):
        try:
            self.draft.set_price(self.start, key, widget.text)
        except (ValueError, RuntimeError) as error:
            widget.background_color = RED
            self.price_summary.color = RED
            self.price_summary.text = str(error) if isinstance(error, RuntimeError) else t(self.locale, 'invalid_price')
            return
        widget.background_color = PANEL
        saved = self.draft.price_for(self.start, key)
        widget.text = '' if saved is None else format(saved, '.2f').replace('.', ',' if self.locale == 'de' else '.')
        self._update_price_summary()

    def _section(self, title, count):
        heading = box(False, spacing=6, size_hint_y=None, height=dp(30))
        heading.add_widget(label(title, 15, GOLD, 30, True))
        total = label(str(count), 13, MUTED, 30, size_hint_x=None, width=dp(36))
        total.halign = 'right'
        heading.add_widget(total)
        self.rows.add_widget(heading)

    def _column_header(self):
        heading = box(False, padding=5, spacing=5, size_hint_y=None, height=dp(25))
        heading.add_widget(label('', 12, MUTED, 25, size_hint_x=None, width=dp(38)))
        name = label(t(self.locale, 'shopping_item_label'), 12, MUTED, 25,
                     size_hint_x=None, width=dp(240))
        name.text_size = (name.width, name.height)
        heading.bind(width=lambda _, width: setattr(name, 'width', self._name_width(width)))
        heading.add_widget(name)
        quantity = label(t(self.locale, 'manual_amount'), 12, MUTED, 25,
                         size_hint_x=None, width=dp(82))
        quantity.halign = 'right'
        heading.add_widget(quantity)
        heading.add_widget(box(False, size_hint_x=None, width=dp(8)))
        heading.add_widget(label(t(self.locale, 'manual_unit'), 12, MUTED, 25,
                                 size_hint_x=None, width=dp(70)))
        heading.add_widget(label(t(self.locale, 'shopping_price'), 12, MUTED, 25,
                                 size_hint_x=None, width=dp(100)))
        heading.add_widget(box(False))
        heading.add_widget(label('', 12, MUTED, 25, size_hint_x=None, width=dp(38)))
        self.rows.add_widget(heading)

    def _item_row(self, item, checked):
        key = item_key(item)
        row = box(False, padding=5, spacing=5, color=(0.09, 0.18, 0.16, 1) if checked else PANEL_LIGHT,
                  size_hint_y=None, height=dp(48))
        check = button('[x]' if checked else '[ ]', lambda: self.toggle(key),
                       height=38, size_hint_x=None, width=dp(38))
        if checked:
            check.background_color = GREEN
            check.color = BG
        row.add_widget(check)
        name = button(item['name'], lambda: self.toggle(key), height=38,
                      size_hint_x=None, width=dp(240))
        row.bind(width=lambda _, width: setattr(name, 'width', self._name_width(width)))
        name.background_color = (0, 0, 0, 0)
        name.color = MUTED if checked else WHITE
        name.halign = 'left'
        name.valign = 'middle'
        name.shorten = True
        name.text_size = (name.width - dp(8), name.height)
        name.bind(size=lambda widget, _: setattr(widget, 'text_size',
                                                (widget.width - dp(8), widget.height)))
        row.add_widget(name)
        amount = label(self._amount(item), 15, GREEN if checked else WHITE, 38, True,
                       size_hint_x=None, width=dp(82))
        amount.halign = 'right'
        row.add_widget(amount)
        row.add_widget(box(False, size_hint_x=None, width=dp(8)))
        unit = label(item['unit'], 13, MUTED, 38, size_hint_x=None, width=dp(70))
        unit.shorten = True
        row.add_widget(unit)
        saved_price = self.draft.price_for(self.start, key)
        price_text = '' if saved_price is None else format(saved_price, '.2f').replace(
            '.', ',' if self.locale == 'de' else '.')
        price = field(t(self.locale, 'shopping_price_hint'), text=price_text, height=38,
                      size_hint_x=None, width=dp(100))
        price.background_color = PANEL
        price.bind(focus=lambda widget, focused: self._save_price(key, widget) if not focused else None)
        price.bind(on_text_validate=lambda widget: self._save_price(key, widget))
        row.add_widget(price)
        row.add_widget(box(False))
        row.add_widget(button('×', lambda: self.remove(key), 'danger',
                              height=38, size_hint_x=None, width=dp(38)))
        return row

    def _render(self):
        self.items = self.draft.items(self.start, self.plans, self.recipes)
        state = self.draft.week(self.start)
        checked = set(state['checked'])
        self.rows.clear_widgets()
        remaining = sum(item_key(item) not in checked for item in self.items)
        selected = len(self.draft.selected_plan_ids(self.start, self.plans))
        self.summary.text = f"{remaining} / {len(self.items)} {t(self.locale, 'shopping_items')}"
        self.meal_summary.text = f"{selected} {t(self.locale, 'selected_meal' if selected == 1 else 'selected_meals')}"
        self._update_price_summary()
        if not self.items:
            self.rows.add_widget(label(t(self.locale, 'empty_shopping_draft'), 17, MUTED, 80))
            return
        pending = [item for item in self.items if item_key(item) not in checked]
        completed = [item for item in self.items if item_key(item) in checked]
        if pending:
            if not self.compact_list:
                self._section(t(self.locale, 'shopping_to_buy'), len(pending))
                self._column_header()
            for item in pending:
                self.rows.add_widget(self._item_row(item, False))
        if completed:
            if not self.compact_list:
                self._section(t(self.locale, 'shopping_completed'), len(completed))
                if not pending:
                    self._column_header()
            for item in completed:
                self.rows.add_widget(self._item_row(item, True))

    def _changed(self):
        self._render()

    def add_all(self):
        self.draft.add_all(self.start, self.plans)
        self._changed()

    def choose_meals(self):
        body = box(padding=12, spacing=8)
        rows = box(spacing=5, size_hint_y=None)
        rows.bind(minimum_height=rows.setter('height'))
        scroll = scroll_view(do_scroll_x=False)
        scroll.add_widget(rows)
        body.add_widget(scroll)
        dialog = styled_popup(t(self.locale, 'choose_meals'), body, 0.65, 0.75)

        def render_choices():
            rows.clear_widgets()
            selected = self.draft.selected_plan_ids(self.start, self.plans)
            for plan in self.plans:
                title = f"{'✓' if str(plan['id']) in selected else '○'}  {plan['date']} · {plan['recipeTitle']} · {plan['servings']} {t(self.locale, 'servings').lower()}"
                rows.add_widget(button(title, lambda plan_id=plan['id']: choose(plan_id), height=46))
            if not self.plans:
                rows.add_widget(label(t(self.locale, 'empty_week'), 16, MUTED, 70))

        def choose(plan_id):
            self.draft.toggle_plan(self.start, plan_id)
            dialog.dismiss()
            self._changed()

        render_choices()
        dialog.open()

    def add_item(self):
        body = box(padding=16, spacing=10)
        form = box(spacing=10, size_hint_y=None)
        form.bind(minimum_height=form.setter('height'))
        scroll = scroll_view(do_scroll_x=False)
        scroll.add_widget(form)
        body.add_widget(scroll)
        name = field(t(self.locale, 'manual_name'))
        amount = field(t(self.locale, 'manual_amount'), text='1')
        unit = field(t(self.locale, 'manual_unit'), text='pcs')
        price = field(t(self.locale, 'shopping_optional_price'))
        error = label('', 13, MUTED, 32)
        quantity = box(False, spacing=10, size_hint_y=None, height=dp(42))
        quantity.add_widget(amount)
        quantity.add_widget(unit)
        for widget in (name, quantity, price, error):
            form.add_widget(widget)
        actions = box(False, spacing=8, size_hint_y=None, height=dp(44))
        dialog = styled_popup(t(self.locale, 'add_item'), body, 0.72, 0.78)
        actions.add_widget(button(t(self.locale, 'cancel'), dialog.dismiss))

        def save(keep_open=False):
            try:
                normalize_price(price.text)
            except ValueError:
                error.text = t(self.locale, 'invalid_price')
                return
            try:
                self.draft.add_custom(self.start, name.text, amount.text, unit.text, price.text)
            except (ValueError, InvalidOperation, RuntimeError):
                error.text = t(self.locale, 'invalid_item')
                return
            if keep_open:
                name.text = ''
                amount.text = '1'
                price.text = ''
                error.text = t(self.locale, 'item_added')
                name.focus = True
            else:
                name.focus = False
                amount.focus = False
                unit.focus = False
                price.focus = False
                dialog.dismiss()
            self._changed()

        actions.add_widget(button(t(self.locale, 'add_another'), lambda: save(True)))
        actions.add_widget(button(t(self.locale, 'add_item'), save, 'primary'))
        body.add_widget(actions)
        dialog.open()

    def remove(self, key):
        try:
            self.draft.remove_item(self.start, key)
        except RuntimeError as error:
            self.on_status(str(error))
            return
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
        try:
            self.draft.clear(self.start, self.plans)
        except RuntimeError as error:
            self.on_status(str(error))
            return
        self._changed()

    def copy(self):
        checked = set(self.draft.week(self.start)['checked'])
        lines = []
        for item in self.items:
            key = item_key(item)
            if key in checked:
                continue
            line = f"{self._amount(item)} {item['unit']} {item['name']}"
            if (price := self.draft.price_for(self.start, key)) is not None:
                line += f" · {self._money(price)}"
            lines.append(line)
        try:
            Clipboard.copy('\n'.join(lines))
            self.on_status(t(self.locale, 'copied'))
        except Exception as error:
            self.on_status(str(error))
