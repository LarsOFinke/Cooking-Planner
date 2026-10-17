from concurrent.futures import ThreadPoolExecutor
from configparser import ConfigParser
from datetime import date, timedelta
from pathlib import Path

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import Metrics

from cooking_planner.AppShell import AppShell
from cooking_planner.ui.dialogs import confirm_popup
from cooking_planner.plans.dialog import plan_popup
from cooking_planner.recipes.dialogs import notes_popup, picker_popup
from cooking_planner.recipes.AdminActions import AdminActions
from cooking_planner.shopping.ShoppingDraft import ShoppingDraft
from cooking_planner.ui.theme import BG, set_tab_active
from cooking_planner.ui.strings import t


class CookingPlannerApp(AppShell, AdminActions, App):
    title = 'Cooking Planner'

    def __init__(self, client, startup_error=None, config_path=None, ui_scale=1.0, ui_locale='en', **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.startup_error = startup_error
        self.config_path = Path(config_path) if config_path else None
        self.ui_scale = ui_scale
        self.base_density = Metrics.density
        self.worker = ThreadPoolExecutor(max_workers=2)
        self.locale = ui_locale
        self.locales = (ui_locale,)
        self.tab = 'overview'
        self.week_start = date.today() - timedelta(days=date.today().weekday())
        self.recipes = []
        self._catalog_cache = {}
        self._overview_ready = False
        self._catalog_ready = False
        self._loading_error = None
        self.plans = []
        self.info = {}
        self.admin_records = []
        self._admin_loaded = False
        self.admin_entry = None
        self.admin_mode = 'recipes'
        self.ingredient_admin_entry = None
        self.status_message = t(self.locale, 'ready')
        self.generation = 0
        self._refresh_running = False
        self._refresh_pending = False
        self._stopping = False
        self.selected_id = None
        self.cooking_progress = {}
        self.shopping_draft = ShoppingDraft(self.config_path.parent / 'shopping.json' if self.config_path else None)
        self.shopping_draft.locale = self.locale
        self.shopping_draft.price_writer = self.client.save_ingredient_price if hasattr(self.client, 'save_ingredient_price') else None
        self.shopping_draft.price_clearer = self.client.clear_ingredient_prices if hasattr(self.client, 'clear_ingredient_prices') else None
        self.shopping_draft.ingredient_writer = (lambda ingredient_id, name, locale:
            self.client.register_ingredient(ingredient_id, locale, name)) if hasattr(self.client, 'register_ingredient') else None
        self.shopping_draft.pending_scheduler = self._flush_shopping_pending
        self.window_fullscreen = False

    def build(self):
        Metrics.density = self.base_density * self.ui_scale
        self.window_fullscreen = bool(Window.fullscreen)
        Window.clearcolor = BG
        self.root_view = self._build_shell()
        if self.startup_error:
            self._status(self.startup_error)
        else:
            self.shopping_draft.schedule_pending()
            Clock.schedule_once(lambda *_: self._load_overview(), 0)
        return self.root_view

    def _status(self, message):
        self.status_message = str(message)
        if hasattr(self, 'status_label'):
            self.status_label.text = self.status_message
        if self.tab == 'admin' and self.admin_panel is not None:
            self.admin_panel.set_status(self.status_message)

    def _report_error(self, message):
        self._status(message)
        if not self._catalog_ready:
            self._loading_error = message
            if (self.tab == 'overview' and not self._overview_ready) or self.tab in ('explore', 'week', 'shopping'):
                self._render_tab()
        if self.tab == 'shopping' and self.shopping_panel is not None:
            self.shopping_panel.set_status(message)

    def _submit(self, work, success, show_status=True, finished=None):
        if show_status:
            self._status('…')
        future = self.worker.submit(work)
        def done(result):
            try:
                value = result.result()
            except Exception as error:
                message = str(error)
                def report(*_):
                    try:
                        self._report_error(message)
                    finally:
                        if finished is not None:
                            finished()
                Clock.schedule_once(report, 0)
                return
            def deliver(*_):
                try:
                    success(value)
                finally:
                    if finished is not None:
                        finished()
            Clock.schedule_once(deliver, 0)
        future.add_done_callback(done)

    def _flush_shopping_pending(self, work):
        self._submit(work, lambda _: None, show_status=False)

    def _load_overview(self):
        if self._stopping or self.generation:
            return
        locale = self.locale
        start = self.week_start.isoformat()
        end = (self.week_start + timedelta(days=6)).isoformat()
        def load():
            return (self.client.locales(), self.client.catalog_info(locale),
                    self.client.plans(start, end, locale))
        def loaded(data):
            if self.generation or locale != self.locale or start != self.week_start.isoformat():
                return
            locales, self.info, self.plans = data
            self._overview_ready = True
            new_locales = tuple(locales)
            if self.locales != new_locales:
                self.locales = new_locales
                self._rebuild_shell()
            else:
                self._render_tab()
            self._status(f"{self.info.get('recipeCount', 0)} {t(self.locale, 'results')} · "
                         f"{len(self.plans)} {t(self.locale, 'planned')}")
            Clock.schedule_once(lambda *_: self.refresh(), 0)
        self._submit(load, loaded)

    def refresh(self):
        if self._stopping:
            return
        if self._loading_error:
            self._loading_error = None
            self._render_tab()
        self.generation += 1
        if self._refresh_running:
            self._refresh_pending = True
            return
        self._start_refresh()

    def _start_refresh(self):
        self._refresh_running = True
        generation = self.generation
        locale = self.locale
        start = self.week_start.isoformat()
        end = (self.week_start + timedelta(days=6)).isoformat()
        cached = self._catalog_cache.get(locale)
        def load():
            catalog = cached or (self.client.locales(), self.client.recipes(locale), self.client.catalog_info(locale))
            return (*catalog,
                    self.client.plans(start, end, locale), self.client.ingredient_prices(start),
                    self.client.reference_prices())
        self._submit(load, lambda data: self._loaded(data, generation), finished=self._finish_refresh)

    def _finish_refresh(self):
        self._refresh_running = False
        if self._refresh_pending and not self._stopping:
            self._refresh_pending = False
            self._start_refresh()

    def _loaded(self, data, generation):
        if generation != self.generation:
            return
        same_overview = self._overview_ready and self.info == data[2] and self.plans == data[3]
        first_catalog = not self._catalog_ready
        locales, self.recipes, self.info, self.plans = data[:4]
        self._catalog_cache = {self.locale: data[:3]}
        self._overview_ready = True
        self._catalog_ready = True
        if len(data) > 4:
            self.shopping_draft.use_prices(self.week_start.isoformat(), data[4])
        if len(data) > 5:
            self.shopping_draft.use_reference_prices(data[5])
        new_locales = tuple(locales)
        if self.locales != new_locales:
            self.locales = new_locales
            self._rebuild_shell()
        elif not (self.tab == 'overview' and first_catalog and same_overview):
            self._render_tab()
        self._status(self.shopping_draft.recovery_notice or
                     f"{len(self.recipes)} {t(self.locale, 'results')} · {len(self.plans)} {t(self.locale, 'planned')}")

    def show_tab(self, tab):
        changed = tab != self.tab
        if not changed:
            if tab == 'explore' and self.selected_id and self.browser is not None:
                self.browser.select_id(self.selected_id)
            elif tab == 'admin':
                self.load_admin()
            return
        self.tab = tab
        for name, control in self.nav_buttons.items():
            set_tab_active(control, t(self.locale, 'admin' if name == 'admin' else 'nav_' + name), name == tab)
        self._render_tab()
        if tab == 'admin' and not self._admin_loaded:
            self.load_admin()

    def browse_recipe(self, recipe_id):
        self.selected_id = recipe_id
        self.show_tab('explore')

    def _selected_recipe(self, recipe_id):
        self.selected_id = recipe_id

    def change_locale(self, locale):
        if locale not in self.locales or locale == self.locale:
            return
        self.locale = locale
        self.shopping_draft.locale = locale
        self._overview_ready = False
        self._catalog_ready = False
        self._save_preference('locale', locale)
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
        self._save_preference('fullscreen', 'true' if self.window_fullscreen else 'false')
        self.window_button.text = t(self.locale, 'leave_fullscreen' if self.window_fullscreen else 'enter_fullscreen')

    def _save_scale(self):
        self._save_preference('scale', str(self.ui_scale))

    def _save_preference(self, key, value):
        if self.config_path is None:
            return
        config = ConfigParser()
        config.read(self.config_path)
        if not config.has_section('ui'):
            config.add_section('ui')
        config.set('ui', key, value)
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
        self._stopping = True
        self.worker.shutdown(wait=False, cancel_futures=True)

    def on_pause(self):
        return True

    def on_resume(self):
        if not self.startup_error:
            self.refresh()
