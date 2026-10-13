"""Full-window recipe photo viewer and its clickable thumbnails."""

from kivy.metrics import dp
from kivy.uix.image import Image
from kivy.uix.popup import Popup

from cooking_planner.recipes.images import attributions
from cooking_planner.recipes.photo import RecipePhoto
from cooking_planner.ui.strings import t
from cooking_planner.ui.theme import MUTED, WHITE, box, button, label, scroll_view


def open_gallery(recipe, photos, index, locale):
    gallery = box(padding=dp(12), spacing=dp(8), color=(0.035, 0.045, 0.055, 1))
    header = box(False, spacing=8, size_hint_y=None, height=dp(44))
    header.add_widget(label(recipe['name'], 17, WHITE, 42, True))
    counter = label('', 14, MUTED, 42, size_hint_x=None, width=dp(90))
    header.add_widget(counter)
    close = button(t(locale, 'close'), lambda: popup.dismiss(),
                   size_hint_x=None, width=dp(105), height=42)
    header.add_widget(close)
    gallery.add_widget(header)
    viewer = box(False, spacing=8)
    previous = button('‹', lambda: select(index_state['value'] - 1),
                      size_hint_x=None, width=dp(52))
    viewer.add_widget(previous)
    image = Image(fit_mode='contain')
    viewer.add_widget(image)
    following = button('›', lambda: select(index_state['value'] + 1),
                       size_hint_x=None, width=dp(52))
    viewer.add_widget(following)
    gallery.add_widget(viewer)
    strip = scroll_view(do_scroll_y=False, size_hint_y=None, height=dp(96))
    thumbnails = box(False, spacing=dp(8), size_hint_x=None)
    thumbnails.width = max(dp(98) * len(photos), dp(98))
    strip.add_widget(thumbnails)
    gallery.add_widget(strip)
    credit_text = label('', 12, MUTED, 32)
    gallery.add_widget(credit_text)
    popup = Popup(title='', content=gallery, size_hint=(1, 1), auto_dismiss=True,
                  separator_height=0, title_size=0)
    index_state = {'value': index}

    def select(value):
        index_state['value'] = value % len(photos)
        reference, photo = photos[index_state['value']]
        image.source = str(photo)
        counter.text = f"{index_state['value'] + 1} / {len(photos)}"
        credit = attributions().get(reference, {})
        credit_text.text = (t(locale, 'rights_pending') if credit.get('rights_status') == 'pending'
                            else f"{credit.get('author', '')} · {credit.get('license', '')}" if credit else '')

    for number, (_, photo) in enumerate(photos):
        thumb = RecipePhoto(source=str(photo), size_hint=(None, None),
                            width=dp(90), height=dp(90), fit_mode='contain')
        thumb.bind(on_release=lambda *_, chosen=number: select(chosen))
        thumbnails.add_widget(thumb)
    select(index)
    popup.open()
    return popup
