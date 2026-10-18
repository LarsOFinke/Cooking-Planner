from cooking_planner.ui.dialogs import styled_popup
from cooking_planner.ui.strings import t
from cooking_planner.ui.theme import GOLD, MUTED, WHITE, box, button, field, label, scroll_view


def picker_popup(recipes: list[dict], locale: str, on_select) -> None:
    body = box(padding=14, spacing=10)
    search = field(t(locale, "search"))
    body.add_widget(search)
    count = label("", 13, MUTED, 28)
    body.add_widget(count)
    rows = box(spacing=5, size_hint_y=None)
    rows.bind(minimum_height=rows.setter("height"))
    scroll = scroll_view(do_scroll_x=False)
    scroll.add_widget(rows)
    body.add_widget(scroll)
    dialog = styled_popup(t(locale, "pick"), body, 0.68, 0.8)
    def choose(recipe: dict) -> None:
        dialog.dismiss()
        on_select(recipe)
    def refresh(*_args) -> None:
        rows.clear_widgets()
        query = search.text.casefold().strip()
        matches = [recipe for recipe in recipes if query in (recipe["name"] + " " + recipe["country"] + " " + recipe["categoryLabel"]).casefold()]
        count.text = f"{len(matches)} {t(locale, 'results')} · {min(40, len(matches))} {t(locale, 'shown')}"
        for recipe in matches[:40]:
            title = f"{recipe['name']}  ·  {recipe['totalMinutes']} {t(locale, 'minutes')}"
            rows.add_widget(button(title, lambda item=recipe: choose(item), height=48))
    search.bind(text=refresh)
    refresh()
    dialog.open()


def notes_popup(info: dict, locale: str) -> None:
    body = box(padding=18, spacing=10, size_hint_y=None)
    body.bind(minimum_height=body.setter("height"))
    body.add_widget(label(info.get("dataset", ""), 18, GOLD, 44, True))
    for title, key in ((t(locale, "ingredients"), "quantityNote"),
                       (t(locale, "diet"), "dietNote"), (t(locale, "origin"), "originNote")):
        body.add_widget(label(title, 17, WHITE, 32, True))
        text = info.get(key, "")
        paragraph = label(text, 14, MUTED, max(80, 26 * ((len(text) // 65) + 1)))
        paragraph.valign = "top"
        body.add_widget(paragraph)
    scroll = scroll_view(do_scroll_x=False)
    scroll.add_widget(body)
    styled_popup(t(locale, "data_notes"), scroll, 0.7, 0.8).open()
