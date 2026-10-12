"""Shopping item entry dialog and saved-ingredient suggestions."""

from decimal import InvalidOperation

from kivy.metrics import dp

from cooking_planner.ui.strings import t
from cooking_planner.ui.theme import MUTED, box, button, field, label, scroll_view, spinner


def open_add_item_dialog(locale, draft, start, on_ingredient_search, on_added,
                         popup_factory, schedule_search):
    body = box(padding=16, spacing=10)
    form = box(spacing=10, size_hint_y=None)
    form.bind(minimum_height=form.setter('height'))
    scroll = scroll_view(do_scroll_x=False)
    scroll.add_widget(form)
    body.add_widget(scroll)
    form.add_widget(label(t(locale, 'shopping_item_label'), 13, MUTED, 24))
    name = field(t(locale, 'manual_name'))
    form.add_widget(name)
    suggestions = box(spacing=4, size_hint_y=None, height=0)
    form.add_widget(suggestions)
    selection = {'id': None, 'name': None, 'generation': 0, 'event': None}

    def show_matches(matches, generation):
        if generation != selection['generation']:
            return
        suggestions.clear_widgets()
        for match in matches[:5]:
            suggestions.add_widget(button(f"{match['name']} · {match['id']}",
                                          lambda item=match: choose_ingredient(item), height=38))
        suggestions.height = dp(42 * min(len(matches), 5))

    def choose_ingredient(match):
        selection['id'], selection['name'] = match['id'], match['name']
        name.text = match['name']
        suggestions.clear_widgets()
        suggestions.height = 0
        error.text = t(locale, 'shopping_saved_ingredient')

    def search_name(*_):
        if selection['name'] is not None and name.text != selection['name']:
            selection['id'], selection['name'] = None, None
        selection['generation'] += 1
        if selection['event'] is not None:
            selection['event'].cancel()
        suggestions.clear_widgets()
        suggestions.height = 0
        query = name.text.strip()
        if len(query) >= 2 and on_ingredient_search is not None and selection['id'] is None:
            generation = selection['generation']
            selection['event'] = schedule_search(
                lambda *_: on_ingredient_search(locale, query,
                    lambda matches: show_matches(matches, generation)), 0.25)

    name.bind(text=search_name)
    form.add_widget(label(t(locale, 'shopping_quantity_unit'), 13, MUTED, 24))
    amount = field(t(locale, 'manual_amount'), text='1')
    unit = spinner('pcs', ('pcs', 'g', 'kg', 'ml', 'l', 'pack'))
    error = label('', 13, MUTED, 32)
    quantity = box(False, spacing=10, size_hint_y=None, height=dp(42))
    quantity.add_widget(amount)
    quantity.add_widget(unit)
    form.add_widget(quantity)
    form.add_widget(error)
    actions = box(False, spacing=8, size_hint_y=None, height=dp(44))
    dialog = popup_factory(t(locale, 'add_item'), body, 0.72, 0.78)
    actions.add_widget(button(t(locale, 'cancel'), dialog.dismiss))

    def save(keep_open=False):
        try:
            draft.add_custom(start, name.text, amount.text, unit.text, ingredient_id=selection['id'])
        except (ValueError, InvalidOperation, RuntimeError) as failure:
            error.text = str(failure) if isinstance(failure, RuntimeError) else t(locale, 'invalid_item')
            return
        if keep_open:
            name.text = ''
            amount.text = '1'
            selection['id'], selection['name'] = None, None
            error.text = t(locale, 'item_added')
            name.focus = True
        else:
            name.focus = False
            amount.focus = False
            dialog.dismiss()
        on_added()

    actions.add_widget(button(t(locale, 'add_another'), lambda: save(True)))
    actions.add_widget(button(t(locale, 'add_item'), save, 'primary'))
    body.add_widget(actions)
    dialog.open()
