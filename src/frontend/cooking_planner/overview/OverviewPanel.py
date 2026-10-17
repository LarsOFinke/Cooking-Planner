"""App orientation and weekly summary without an unsolicited recipe selection."""

from kivy.metrics import dp
from kivy.uix.gridlayout import GridLayout

from cooking_planner.ui.theme import MUTED, PANEL, PANEL_LIGHT, WHITE, box, button, label, scroll_view
from cooking_planner.ui.strings import t


class OverviewPanel:
    def __init__(self, recipes, plans, info, locale, on_navigate, on_notes):
        self.root = box()
        scroll = scroll_view(do_scroll_x=False)
        self.scroll = scroll
        content = box(spacing=16, size_hint_y=None)
        content.bind(minimum_height=content.setter('height'))

        hero = box(padding=20, spacing=4, color=PANEL,
                   size_hint_y=None, height=dp(116))
        hero.add_widget(label(t(locale, 'overview_welcome'), 25, WHITE, 40, True))
        hero.add_widget(label(t(locale, 'overview_intro'), 14, MUTED, 36))
        content.add_widget(hero)

        metrics = GridLayout(cols=4, spacing=dp(10), row_default_height=dp(90),
                             row_force_default=True, size_hint_y=None, height=dp(90))
        self.metrics = metrics
        def layout_metrics(_, width):
            metrics.cols = 4 if width >= dp(750) else 2 if width >= dp(400) else 1
            rows = 4 // metrics.cols
            metrics.height = dp(90 * rows) + dp(10 * (rows - 1))
        metrics.bind(width=layout_metrics)
        categories = len({recipe.get('categoryLabel') for recipe in recipes if recipe.get('categoryLabel')})
        for value, caption in ((len(recipes) or info.get('recipeCount', 0), 'recipes_count'),
                               (categories or info.get('categoryCount', 0), 'categories_count'),
                               (info.get('countryCount', 0), 'countries'), (len(plans), 'planned')):
            tile = box(padding=14, spacing=0, color=PANEL_LIGHT)
            tile.add_widget(label(str(value), 27, WHITE, 42, True))
            tile.add_widget(label(t(locale, caption), 12, MUTED, 24))
            metrics.add_widget(tile)
        content.add_widget(metrics)

        if not plans:
            guide = box(padding=16, spacing=3, color=PANEL,
                        size_hint_y=None, height=dp(148))
            guide.add_widget(label(t(locale, 'overview_start'), 17, WHITE, 30, True))
            for key in ('overview_step_explore', 'overview_step_plan', 'overview_step_shop'):
                guide.add_widget(label(t(locale, key), 13, WHITE, 25))
            content.add_widget(guide)

        content.add_widget(label(t(locale, 'overview_modules'), 18, WHITE, 32, True))
        modules = GridLayout(cols=1, spacing=dp(10), row_default_height=dp(100),
                             row_force_default=True, size_hint_y=None)
        self.modules = modules
        modules.bind(minimum_height=modules.setter('height'))
        modules.bind(width=lambda _, width: setattr(modules, 'cols',
                                                    3 if width >= dp(900) else 2 if width >= dp(600) else 1))
        for tab, description in (('explore', 'overview_explore_help'), ('week', 'overview_week_help'),
                                 ('shopping', 'overview_shopping_help')):
            card = box(False, padding=14, spacing=8, color=PANEL_LIGHT, hover=True,
                       size_hint_y=None, height=dp(100))
            copy = box(spacing=2)
            copy.add_widget(label(t(locale, tab), 16, WHITE, 28, True))
            copy.add_widget(label(t(locale, description), 12, MUTED, 42))
            card.add_widget(copy)
            card.add_widget(button(t(locale, 'open'), lambda selected=tab: on_navigate(selected),
                                   size_hint_x=None, width=dp(72), height=38))
            modules.add_widget(card)
        content.add_widget(modules)

        notes = box(False, padding=16, spacing=10, color=PANEL,
                    size_hint_y=None, height=dp(100))
        copy = box(spacing=2)
        copy.add_widget(label(t(locale, 'overview_good_to_know'), 16, WHITE, 28, True))
        copy.add_widget(label(t(locale, 'overview_catalog_note'), 13, WHITE, 42))
        notes.add_widget(copy)
        notes_action = button(t(locale, 'data_notes'), on_notes,
                              size_hint_x=None, width=dp(130), height=38)
        notes.add_widget(notes_action)
        def layout_notes(_, width):
            compact = width < dp(480)
            notes.orientation = 'vertical' if compact else 'horizontal'
            notes.height = dp(154 if compact else 100)
            notes_action.size_hint_x = 1 if compact else None
            notes_action.width = width if compact else dp(130)
        notes.bind(width=layout_notes)
        layout_notes(notes, notes.width)
        content.add_widget(notes)

        scroll.add_widget(content)
        self.root.add_widget(scroll)
