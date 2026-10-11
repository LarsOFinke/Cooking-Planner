"""App orientation and weekly summary without an unsolicited recipe selection."""

from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView

from cooking_planner.ui.theme import GOLD, MUTED, PANEL, WHITE, box, button, label
from cooking_planner.ui.strings import t


class OverviewPanel:
    def __init__(self, recipes, plans, info, locale, on_navigate, on_notes):
        self.root = box(spacing=10)
        scroll = ScrollView(do_scroll_x=False)
        content = box(spacing=12, size_hint_y=None)
        content.bind(minimum_height=content.setter('height'))
        content.add_widget(label(t(locale, 'overview_welcome'), 25, GOLD, 46, True))
        content.add_widget(label(t(locale, 'overview_intro'), 15, MUTED, 50))

        metrics = box(False, spacing=8, size_hint_y=None, height=dp(88))
        categories = len({recipe.get('categoryLabel') for recipe in recipes if recipe.get('categoryLabel')})
        for value, caption in ((len(recipes), 'recipes_count'), (categories, 'categories_count'),
                               (info.get('countryCount', 0), 'countries'), (len(plans), 'planned')):
            tile = box(padding=10, spacing=1, color=PANEL)
            tile.add_widget(label(str(value), 23, GOLD, 34, True))
            tile.add_widget(label(t(locale, caption), 13, MUTED, 26))
            metrics.add_widget(tile)
        content.add_widget(metrics)

        if not plans:
            guide = box(padding=14, spacing=5, color=PANEL, size_hint_y=None, height=dp(170))
            guide.add_widget(label(t(locale, 'overview_start'), 18, GOLD, 32, True))
            for key in ('overview_step_explore', 'overview_step_plan', 'overview_step_shop'):
                guide.add_widget(label(t(locale, key), 14, WHITE, 30))
            content.add_widget(guide)

        content.add_widget(label(t(locale, 'overview_modules'), 19, GOLD, 34, True))
        for tab, description in (('explore', 'overview_explore_help'), ('week', 'overview_week_help'),
                                 ('shopping', 'overview_shopping_help')):
            row = box(False, padding=10, spacing=10, color=PANEL,
                      size_hint_y=None, height=dp(84))
            copy = box(spacing=0)
            copy.add_widget(label(t(locale, tab), 17, WHITE, 29, True))
            copy.add_widget(label(t(locale, description), 13, MUTED, 32))
            row.add_widget(copy)
            row.add_widget(button(t(locale, 'open'), lambda selected=tab: on_navigate(selected),
                                  size_hint_x=None, width=dp(105)))
            content.add_widget(row)

        notes = box(padding=14, spacing=5, color=PANEL, size_hint_y=None, height=dp(170))
        notes.add_widget(label(t(locale, 'overview_good_to_know'), 18, GOLD, 30, True))
        notes.add_widget(label(t(locale, 'overview_catalog_note'), 14, WHITE, 56))
        notes.add_widget(button(t(locale, 'data_notes'), on_notes, size_hint_x=None, width=dp(175)))
        content.add_widget(notes)
        scroll.add_widget(content)
        self.root.add_widget(scroll)
