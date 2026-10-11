import random

from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView

from cooking_planner.ui.theme import GOLD, MUTED, PANEL, WHITE, box, button, label
from cooking_planner.ui.strings import t


class OverviewPanel:
    def __init__(self, recipes, plans, shopping, info, locale, on_browse, on_plan, on_notes):
        self.root = box(spacing=12)
        scroll = ScrollView(do_scroll_x=False)
        content = box(spacing=14, size_hint_y=None)
        content.bind(minimum_height=content.setter('height'))
        heading = label(t(locale, 'overview'), 26, GOLD, 52, True)
        content.add_widget(heading)
        metrics = box(False, spacing=10, size_hint_y=None, height=dp(108))
        for value, caption in ((len(recipes), 'recipes_count'), (info.get('countryCount', 0), 'countries'),
                               (len(plans), 'planned'), (len(shopping), 'shopping_items')):
            tile = box(padding=14, spacing=2, color=PANEL)
            tile.add_widget(label(str(value), 29, GOLD, 45, True))
            tile.add_widget(label(t(locale, caption), 14, MUTED, 30))
            metrics.add_widget(tile)
        content.add_widget(metrics)
        featured = random.choice(recipes) if recipes else None
        if featured:
            card = box(padding=18, spacing=8, color=PANEL, size_hint_y=None, height=dp(196))
            card.add_widget(label(t(locale, 'featured'), 15, MUTED, 28, True))
            card.add_widget(label(featured['name'], 23, GOLD, 48, True))
            card.add_widget(label(f"{featured['country'] or t(locale, 'no_country')}  ·  {featured['categoryLabel']}  ·  {featured['totalMinutes']} {t(locale, 'minutes')}", 15, WHITE, 32))
            actions = box(False, spacing=8, size_hint_y=None, height=dp(42))
            actions.add_widget(button(t(locale, 'browse'), lambda: on_browse(featured['id'])))
            actions.add_widget(button(t(locale, 'plan_this'), lambda: on_plan(featured), 'primary'))
            card.add_widget(actions)
            content.add_widget(card)
        upcoming = box(padding=18, spacing=7, color=PANEL, size_hint_y=None,
                       height=dp(64 + max(1, min(len(plans), 5)) * 36))
        upcoming.add_widget(label(t(locale, 'week_at_glance'), 19, GOLD, 40, True))
        for plan in plans[:5]:
            upcoming.add_widget(label(f"{plan['date']}  ·  {plan['recipeTitle']}  ·  {plan['servings']} {t(locale, 'servings').lower()}", 15, WHITE, 32))
        if not plans:
            upcoming.add_widget(label(t(locale, 'empty_week'), 15, MUTED, 36))
        content.add_widget(upcoming)
        content.add_widget(button(t(locale, 'data_notes'), on_notes, height=46))
        scroll.add_widget(content)
        self.root.add_widget(scroll)
