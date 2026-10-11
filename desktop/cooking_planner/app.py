from concurrent.futures import ThreadPoolExecutor
from configparser import ConfigParser
from datetime import date, timedelta
from pathlib import Path

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import Metrics, dp
from kivy.uix.scrollview import ScrollView

from cooking_planner.ui.dialogs import confirm_popup
from cooking_planner.plans.dialog import plan_popup
from cooking_planner.recipes.dialogs import notes_popup, picker_popup
from cooking_planner.overview.panel import OverviewPanel
from cooking_planner.recipes.browser import RecipeBrowser
from cooking_planner.recipes.admin import AdminPanel
from cooking_planner.shopping.draft import ShoppingDraft
from cooking_planner.shopping.panel import ShoppingPanel
from cooking_planner.ui.theme import BG, GOLD, MUTED, PANEL, box, button, label, spinner, tab_button
from cooking_planner.ui.strings import t
from cooking_planner.plans.week import WeekPlanner


class CookingPlannerApp(App):
    title = 'Cooking Planner'

    def __init__(self, client, startup_error=None, config_path=None, ui_scale=1.0, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.startup_error = startup_error
        self.config_path = Path(config_path) if config_path else None
        self.ui_scale = ui_scale
        self.base_density = Metrics.density
        self.worker = ThreadPoolExecutor(max_workers=2)
        self.locale = 'en'
        self.locales = ('en',)
        self.tab = 'overview'
        self.week_start = date.today() - timedelta(days=date.today().weekday())
        self.recipes = []
        self.plans = []
        self.info = {}
        self.admin_records = []
        self.admin_entry = None
        self.status_message = t(self.locale, 'ready')
        self.generation = 0
        self.selected_id = None
        self.shopping_draft = ShoppingDraft(self.config_path.parent / 'shopping.json' if self.config_path else None)
        self.window_fullscreen = False

    def build(self):
        Metrics.density = self.base_density * self.ui_scale
        Window.minimum_width, Window.minimum_height = 900, 650
        self.window_fullscreen = bool(Window.fullscreen)
        Window.clearcolor = BG
        self.root_view = self._build_shell()
        if self.startup_error:
            self._status(self.startup_error)
        else:
            Clock.schedule_once(lambda *_: self.refresh(), 0)
        return self.root_view

    def _build_shell(self):
        root = box(padding=14, spacing=10)
        header = box(spacing=5, size_hint_y=None, height=dp(104))
        self.header = header
        top_row = box(False, spacing=10, size_hint_y=None, height=dp(52))
        heading = box(spacing=0)
        heading.add_widget(label('COOKING PLANNER', 21, GOLD, 29, True))
        heading.add_widget(label(t(self.locale, 'tagline'), 12, MUTED, 19))
        top_row.add_widget(heading)
        self.admin_button = tab_button(t(self.locale, 'admin'), lambda: self.show_tab('admin'),
                                       self.tab == 'admin', size_hint_x=None, width=dp(138))
        top_row.add_widget(self.admin_button)
        header.add_widget(top_row)
        controls = box(False, spacing=8, size_hint_y=None, height=dp(42))
        self.header_controls = controls
        controls.add_widget(box())
        controls.add_widget(button(t(self.locale, 'data_notes'), self.show_notes,
                                   size_hint_x=None, width=dp(130)))
        languages = spinner(self.locale.upper(), (item.upper() for item in self.locales),
                            size_hint_x=None, width=dp(76))
        languages.bind(text=lambda _, value: self.change_locale(value.lower()))
        controls.add_widget(languages)
        scales = spinner(f'{round(self.ui_scale * 100)}%',
                         ('100%', '125%', '150%', '175%', '200%'),
                         size_hint_x=None, width=dp(84))
        scales.bind(text=lambda _, value: self.change_scale(int(value[:-1]) / 100))
        controls.add_widget(scales)
        self.window_button = button(t(self.locale, 'leave_fullscreen' if self.window_fullscreen else 'enter_fullscreen'),
                                    self.toggle_window, size_hint_x=None, width=dp(115))
        controls.add_widget(self.window_button)
        header.add_widget(controls)
        root.add_widget(header)
        nav_scroll = ScrollView(size_hint_y=None, height=dp(48), do_scroll_y=False)
        nav = box(False, spacing=8, size_hint_x=None)
        nav_scroll.bind(width=lambda _, width: setattr(nav, 'width', max(width, dp(740))))
        for tab in ('overview', 'explore', 'week', 'shopping'):
            nav.add_widget(tab_button(t(self.locale, tab),
                                      lambda selected=tab: self.show_tab(selected),
                                      tab == self.tab, height=48))
        nav_scroll.add_widget(nav)
        root.add_widget(nav_scroll)
        self.content = box(color=PANEL, padding=10)
        root.add_widget(self.content)
        footer = box(False, size_hint_y=None, height=dp(42))
        self.exit_button = button(t(self.locale, 'exit'), self.stop, 'danger',
                                  size_hint_x=None, width=dp(100))
        footer.add_widget(self.exit_button)
        root.add_widget(footer)
        self._render_tab()
        return root

    def _status(self, message):
        self.status_message = str(message)
        if self.tab == 'admin' and hasattr(self, 'admin_panel'):
            self.admin_panel.set_status(self.status_message)

    def _submit(self, work, success):
        self._status('…')
        future = self.worker.submit(work)
        def done(result):
            try:
                value = result.result()
            except Exception as error:
                message = str(error)
                Clock.schedule_once(lambda *_: self._status(message), 0)
                return
            Clock.schedule_once(lambda *_: success(value), 0)
        future.add_done_callback(done)

    def refresh(self):
        self.generation += 1
        generation = self.generation
        locale = self.locale
        start = self.week_start.isoformat()
        end = (self.week_start + timedelta(days=6)).isoformat()
        def load():
            return (self.client.locales(), self.client.recipes(locale), self.client.catalog_info(locale),
                    self.client.plans(start, end, locale))
        self._submit(load, lambda data: self._loaded(data, generation))

    def _loaded(self, data, generation):
        if generation != self.generation:
            return
        locales, self.recipes, self.info, self.plans = data
        new_locales = tuple(locales)
        if self.locales != new_locales:
            self.locales = new_locales
            self._rebuild_shell()
        else:
            self._render_tab()
        self._status(self.shopping_draft.recovery_notice or
                     f"{len(self.recipes)} {t(self.locale, 'results')} · {len(self.plans)} {t(self.locale, 'planned')}")

    def _rebuild_shell(self):
        self.root_view.clear_widgets()
        fresh = self._build_shell()
        for widget in reversed(list(fresh.children)):
            fresh.remove_widget(widget)
            self.root_view.add_widget(widget)

    def show_tab(self, tab):
        self.tab = tab
        self._rebuild_shell()
        if tab == 'admin':
            self.load_admin()

    def _render_tab(self):
        self.content.clear_widgets()
        if self.tab == 'overview':
            panel = OverviewPanel(self.recipes, self.plans, self.info, self.locale,
                                  self.show_tab, self.show_notes)
        elif self.tab == 'explore':
            panel = RecipeBrowser(self.recipes, self.locale, self.plan_recipe, self._selected_recipe)
            self.browser = panel
            if self.selected_id:
                panel.select_id(self.selected_id)
        elif self.tab == 'week':
            panel = WeekPlanner(self.week_start, self.plans, self.locale,
                                self.shift_week, self.current_week, self.pick_recipe, self.remove_plan)
        elif self.tab == 'shopping':
            panel = ShoppingPanel(self.plans, self.recipes, self.shopping_draft, self.locale,
                                  self.week_start, self._status)
        else:
            panel = AdminPanel(self.admin_records, self.locales, self.locale, self.select_admin_recipe,
                               self.save_admin_recipe, self.delete_admin_recipe, self.load_admin, self._status,
                               getattr(self, 'admin_options', {}), self.status_message)
            self.admin_panel = panel
            if self.admin_entry:
                panel.show_recipe(self.admin_entry)
        self.content.add_widget(panel.root)

    def load_admin(self):
        def load():
            return self.client.locales(), self.client.admin_recipes(), self.client.admin_options()
        def loaded(data):
            locales, records, options = data
            self.locales = tuple(locales)
            self.admin_records = records
            self.admin_options = options
            if self.tab == 'admin':
                self._render_tab()
                self._status(f"{len(records)} {t(self.locale, 'results')}")
        self._submit(load, loaded)

    def select_admin_recipe(self, recipe_id):
        def loaded(entry):
            self.admin_entry = entry
            if self.tab == 'admin':
                self.admin_panel.show_recipe(entry)
        self._submit(lambda: self.client.admin_recipe(recipe_id), loaded)

    def save_admin_recipe(self, recipe_id, source_locale, translations, create):
        def saved(entry):
            self.admin_entry = entry
            self.refresh()
            self.load_admin()
        self._submit(lambda: self.client.save_recipe(recipe_id, source_locale, translations, create), saved)

    def delete_admin_recipe(self, recipe_id):
        def delete():
            def deleted(_):
                self.admin_entry = None
                self.refresh()
                self.load_admin()
            self._submit(lambda: self.client.delete_recipe(recipe_id), deleted)
        confirm_popup(t(self.locale, 'admin_delete_question'), self.locale, delete,
                      title=t(self.locale, 'admin_delete'), confirm_label=t(self.locale, 'admin_delete'))

    def browse_recipe(self, recipe_id):
        self.selected_id = recipe_id
        self.show_tab('explore')

    def _selected_recipe(self, recipe_id):
        self.selected_id = recipe_id

    def change_locale(self, locale):
        if locale not in self.locales or locale == self.locale:
            return
        self.locale = locale
        self._rebuild_shell()
        self.refresh()

    def change_scale(self, scale):
        if scale == self.ui_scale:
            return
        self.ui_scale = scale
        Metrics.density = self.base_density * scale
        self._save_scale()
        self._rebuild_shell()
        self._status(f'{round(scale * 100)}%')

    def toggle_window(self):
        # SDL3 only enables fullscreen for the boolean True value. Its runtime
        # setter treats Kivy's older 'auto' option as False.
        Window.fullscreen = not bool(Window.fullscreen)
        self.window_fullscreen = bool(Window.fullscreen)
        self.window_button.text = t(self.locale, 'leave_fullscreen' if self.window_fullscreen else 'enter_fullscreen')

    def _save_scale(self):
        if self.config_path is None:
            return
        config = ConfigParser()
        config.read(self.config_path)
        if not config.has_section('ui'):
            config.add_section('ui')
        config.set('ui', 'scale', str(self.ui_scale))
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.config_path.with_suffix('.tmp')
        with temporary.open('w', encoding='utf-8') as file:
            config.write(file)
        temporary.replace(self.config_path)

    def shift_week(self, days):
        self.week_start += timedelta(days=days)
        self.refresh()

    def current_week(self):
        today = date.today()
        self.week_start = today - timedelta(days=today.weekday())
        self.refresh()

    def plan_recipe(self, recipe):
        plan_popup(recipe, self.locale, date.today(), 'DINNER', self.save_plan)

    def pick_recipe(self, day, meal):
        picker_popup(self.recipes, self.locale,
                     lambda recipe: plan_popup(recipe, self.locale, day, meal, self.save_plan))

    def save_plan(self, day, meal, recipe_id, servings):
        def saved(_):
            self.week_start = day - timedelta(days=day.weekday())
            self.show_tab('week')
            self.refresh()
        self._submit(lambda: self.client.save_plan(day.isoformat(), meal, recipe_id, servings), saved)

    def remove_plan(self, plan):
        confirm_popup(t(self.locale, 'remove_question'), self.locale,
                      lambda: self._submit(lambda: self.client.delete_plan(plan['id']),
                                           lambda *_: self.refresh()))

    def show_notes(self):
        notes_popup(self.info, self.locale)

    def on_stop(self):
        self.worker.shutdown(wait=False, cancel_futures=True)
