from kivy.metrics import dp
from kivy.core.window import Window
from kivy.uix.popup import Popup

from cooking_planner.ui.theme import GOLD, PANEL, WHITE, box, button, label
from cooking_planner.ui.strings import t


def styled_popup(title: str, content, width=0.64, height=0.72) -> Popup:
    return Popup(title=title, content=content, size_hint=(width, height),
                 background_color=PANEL, separator_color=GOLD, title_color=WHITE,
                 title_size=dp(20), auto_dismiss=True)


def confirm_popup(message: str, locale: str, on_confirm, title=None, confirm_label=None) -> None:
    body = box(padding=18, spacing=14)
    body.add_widget(label(message, 17, WHITE, 70))
    actions = box(False, spacing=8, size_hint_y=None, height=dp(44))
    dialog = styled_popup(title or t(locale, "remove"), body, 0.55, None)
    dialog.height = min(dp(240), Window.height * 0.88)
    actions.add_widget(button(t(locale, "cancel"), dialog.dismiss))
    def confirm() -> None:
        dialog.dismiss()
        on_confirm()
    actions.add_widget(button(confirm_label or t(locale, "remove"), confirm, "danger"))
    body.add_widget(actions)
    dialog.open()
