"""Render shopping totals and rows from the current draft."""

from decimal import Decimal

from kivy.clock import Clock
from kivy.metrics import dp

from cooking_planner.shopping.ShoppingDraft import item_key
from cooking_planner.ui.strings import t
from cooking_planner.ui.theme import BG, GOLD, GREEN, MUTED, PANEL_LIGHT, WHITE, box, button, label


class ShoppingRendering:
    def cancel_pending(self):
        if getattr(self, '_row_event', None) is not None:
            self._row_event.cancel()
            self._row_event = None

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
                  if (price := self.draft.price_for(self.start, item_key(item), item['amount'])) is not None]
        total = sum(prices, Decimal('0'))
        self.price_summary.color = GOLD
        key = 'shopping_prices_compact' if self.compact_summary else 'shopping_prices_summary'
        self.price_summary.text = t(self.locale, key).format(
            count=len(prices), total=len(self.items), amount=self._money(total))

    def _render_summary(self):
        state = self.draft.week(self.start)
        checked = set(state['checked'])
        remaining = sum(item_key(item) not in checked for item in self.items)
        selected = len(self.draft.selected_plan_ids(self.start, self.plans))
        if self.compact_summary:
            self.summary.text = t(self.locale, 'shopping_items_compact').format(
                remaining=remaining, total=len(self.items))
        else:
            self.summary.text = f"{remaining} / {len(self.items)} {t(self.locale, 'shopping_items')}"
        self.meal_summary.text = f"{selected} {t(self.locale, 'selected_meal' if selected == 1 else 'selected_meals')}"
        self._update_price_summary()

    def _section(self, title, count):
        heading = box(False, spacing=6, size_hint_y=None, height=dp(30))
        heading.add_widget(label(title, 15, GOLD, 30, True))
        total = label(str(count), 13, MUTED, 30, size_hint_x=None, width=dp(36))
        total.halign = 'right'
        heading.add_widget(total)
        self.rows.add_widget(heading)

    @staticmethod
    def _choice_button(text, callback):
        control = button(text, callback, height=46)
        control.halign = 'left'
        control.shorten = True
        control.bind(size=lambda widget, _: setattr(widget, 'text_size',
                                                   (widget.width - dp(16), widget.height)))
        return control

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
        heading.add_widget(label(t(self.locale, 'shopping_estimated_price'), 12, MUTED, 25,
                                 size_hint_x=None, width=dp(100)))
        heading.add_widget(box(False))
        heading.add_widget(label('', 12, MUTED, 25, size_hint_x=None, width=dp(38)))
        self.rows.add_widget(heading)

    def _item_row(self, item, checked):
        key = item_key(item)
        row = box(False, padding=5, spacing=5, color=(0.09, 0.18, 0.16, 1) if checked else PANEL_LIGHT,
                  hover=True,
                  size_hint_y=None, height=dp(48))
        check = button('[x]' if checked else '[ ]', lambda: self.toggle(key),
                       height=38, size_hint_x=None, width=dp(38))
        if checked:
            check.set_base_color(GREEN)
            check.color = BG
        row.add_widget(check)
        name = button(item['name'], lambda: self.toggle(key), height=38,
                      size_hint_x=None, width=dp(240))
        row.bind(width=lambda _, width: setattr(name, 'width', self._name_width(width)))
        name.set_base_color((0, 0, 0, 0))
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
        estimated = self.draft.price_for(self.start, key, item['amount'])
        price_text = self._money(estimated) if estimated is not None else '—'
        row.add_widget(label(price_text, 13, GOLD if estimated is not None else MUTED, 38,
                             size_hint_x=None, width=dp(100)))
        row.add_widget(box(False))
        row.add_widget(button('×', lambda: self.remove(key), 'danger',
                              height=38, size_hint_x=None, width=dp(38)))
        return row

    def _render(self):
        if getattr(self, '_row_event', None) is not None:
            self._row_event.cancel()
            self._row_event = None
        self.items = self.draft.items(self.start, self.plans, self.recipes)
        state = self.draft.week(self.start)
        checked = set(state['checked'])
        self.rows.clear_widgets()
        self._render_summary()
        if not self.items:
            self.rows.add_widget(label(t(self.locale, 'empty_shopping_draft'), 17, MUTED, 80))
            return
        pending = [item for item in self.items if item_key(item) not in checked]
        completed = [item for item in self.items if item_key(item) in checked]
        entries = []
        if pending:
            if not self.compact_list:
                entries.extend((('section', (t(self.locale, 'shopping_to_buy'), len(pending))),
                                ('header', None)))
            for item in pending:
                entries.append(('item', (item, False)))
        if completed:
            if not self.compact_list:
                entries.append(('section', (t(self.locale, 'shopping_completed'), len(completed))))
                if not pending:
                    entries.append(('header', None))
            for item in completed:
                entries.append(('item', (item, True)))

        def append_batch(_):
            for kind, payload in entries[:12]:
                if kind == 'section':
                    self._section(*payload)
                elif kind == 'header':
                    self._column_header()
                else:
                    self.rows.add_widget(self._item_row(*payload))
            del entries[:12]
            self._row_event = Clock.schedule_once(append_batch, 0) if entries else None

        append_batch(0)
