"""Build the application shell and its feature-owned tab views."""

from kivy.metrics import dp

from cooking_planner.overview.OverviewPanel import OverviewPanel
from cooking_planner.plans.WeekPlanner import WeekPlanner
from cooking_planner.recipes.AdminPanel import AdminPanel
from cooking_planner.recipes.IngredientAdminPanel import IngredientAdminPanel
from cooking_planner.recipes.RecipeBrowser import RecipeBrowser
from cooking_planner.shopping.ShoppingPanel import ShoppingPanel
from cooking_planner.ui.strings import t
from cooking_planner.ui.theme import MUTED, WHITE, box, button, label, scroll_view, spinner, tab_button


class AppShell:
    def _build_shell(self):
        root = box(padding=16, spacing=10)
        header = box(False, spacing=12, size_hint_y=None, height=dp(56))
        self.header = header
        heading = box(spacing=0)
        title = label('Cooking Planner', 23, WHITE, 34, True)
        tagline = label(t(self.locale, 'tagline'), 12, MUTED, 19)
        title.shorten = tagline.shorten = True
        heading.add_widget(title)
        heading.add_widget(tagline)
        header.add_widget(heading)
        controls = box(False, spacing=6, size_hint_x=None, width=dp(261))
        self.header_controls = controls
        languages = spinner(self.locale.upper(), (item.upper() for item in self.locales),
                            size_hint_x=None, width=dp(61))
        languages.bind(text=lambda _, value: self.change_locale(value.lower()))
        controls.add_widget(languages)
        scales = spinner(f'{round(self.ui_scale * 100)}%',
                         ('100%', '125%', '150%', '175%', '200%'),
                         size_hint_x=None, width=dp(71))
        scales.bind(text=lambda _, value: self.change_scale(int(value[:-1]) / 100))
        controls.add_widget(scales)
        self.window_button = button(t(self.locale, 'leave_fullscreen' if self.window_fullscreen else 'enter_fullscreen'),
                                    self.toggle_window, size_hint_x=None, width=dp(120))
        self.window_button.font_size = dp(14)
        controls.add_widget(self.window_button)
        header.add_widget(controls)
        def layout_header(_, width):
            compact = width < dp(530)
            header.orientation = 'vertical' if compact else 'horizontal'
            header.height = dp(108 if compact else 56)
            controls.size_hint_x = 1 if compact else None
            controls.width = width if compact else dp(261)
        header.bind(width=layout_header)
        layout_header(header, header.width)
        root.add_widget(header)
        nav_scroll = scroll_view(size_hint_y=None, height=dp(44), do_scroll_y=False)
        nav = box(False, spacing=7, size_hint=(None, None), height=dp(44))
        nav_scroll.bind(width=lambda _, width: setattr(nav, 'width', max(width, dp(650))))
        self.nav_buttons = {}
        for tab in ('overview', 'explore', 'week', 'shopping', 'admin'):
            name = t(self.locale, 'admin' if tab == 'admin' else 'nav_' + tab)
            control = tab_button(name, lambda selected=tab: self.show_tab(selected),
                                 tab == self.tab, height=42)
            if tab == 'admin':
                self.admin_button = control
            self.nav_buttons[tab] = control
            nav.add_widget(control)
        nav_scroll.add_widget(nav)
        root.add_widget(nav_scroll)
        self.content = box()
        root.add_widget(self.content)
        footer = box(False, spacing=10, size_hint_y=None, height=dp(36))
        self.status_label = label(self.status_message, 12, MUTED, 36)
        self.status_label.shorten = True
        footer.add_widget(self.status_label)
        self.exit_button = button(t(self.locale, 'exit'), self.stop,
                                  size_hint_x=None, width=dp(90), height=36)
        footer.add_widget(self.exit_button)
        root.add_widget(footer)
        self._render_tab()
        return root


    def _rebuild_shell(self):
        self.root_view.clear_widgets()
        fresh = self._build_shell()
        for widget in reversed(list(fresh.children)):
            fresh.remove_widget(widget)
            self.root_view.add_widget(widget)


    def _render_tab(self):
        previous = getattr(self, '_active_panel', None)
        if previous is not None and hasattr(previous, 'cancel_pending'):
            previous.cancel_pending()
        self._active_panel = None
        self.browser = None
        self.shopping_panel = None
        self.admin_panel = None
        self.content.clear_widgets()
        if not self.startup_error and ((self.tab == 'overview' and not self._overview_ready) or
                                       (self.tab in ('explore', 'week', 'shopping') and not self._catalog_ready)):
            key = 'loading_overview' if self.tab == 'overview' else 'loading_recipes'
            loading = box(padding=18, spacing=8)
            loading.add_widget(label(self._loading_error or t(self.locale, key), 16, MUTED, 90))
            if self._loading_error:
                loading.add_widget(button(t(self.locale, 'retry'), self.refresh, height=42))
            self.content.add_widget(loading)
            return
        if self.tab == 'overview':
            panel = OverviewPanel(self.recipes, self.plans, self.info, self.locale,
                                  self.show_tab, self.show_notes)
        elif self.tab == 'explore':
            panel = RecipeBrowser(self.recipes, self.locale, self.plan_recipe, self._selected_recipe,
                                  self.shopping_draft.reference_price_for, self.cooking_progress)
            self.browser = panel
            if self.selected_id:
                panel.select_id(self.selected_id)
        elif self.tab == 'week':
            panel = WeekPlanner(self.week_start, self.plans, self.locale,
                                self.shift_week, self.current_week, self.pick_recipe, self.remove_plan,
                                self.recipes, self.shopping_draft)
        elif self.tab == 'shopping':
            panel = ShoppingPanel(self.plans, self.recipes, self.shopping_draft, self.locale,
                                  self.week_start, self._status, self.search_ingredients)
            self.shopping_panel = panel
        elif self.admin_mode == 'ingredients':
            panel = IngredientAdminPanel(self.locales, self.locale, self.show_recipe_admin,
                                         self.list_admin_ingredients, self.save_admin_ingredient,
                                         self.delete_admin_ingredient, self._status,
                                         self.ingredient_admin_entry,
                                         self.shopping_draft.reference_prices, self.save_admin_price)
            self.admin_panel = panel
        else:
            panel = AdminPanel(self.admin_records, self.locales, self.locale, self.select_admin_recipe,
                               self.save_admin_recipe, self.delete_admin_recipe, self.load_admin, self._status,
                               getattr(self, 'admin_options', {}), self.status_message, self.search_ingredients,
                               self.show_ingredient_admin)
            self.admin_panel = panel
            if self.admin_entry:
                panel.show_recipe(self.admin_entry)
        self.content.add_widget(panel.root)
        self._active_panel = panel
