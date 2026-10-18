"""Three previewable recipe image slots with a local file chooser."""

import hashlib
from pathlib import Path
from uuid import uuid4

from kivy.metrics import dp
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.image import Image

from cooking_planner.recipes.images import PHOTO_NAME, image_file
from cooking_planner.ui.dialogs import styled_popup
from cooking_planner.ui.strings import t
from cooking_planner.ui.theme import GOLD, MUTED, PANEL, PANEL_LIGHT, RED, box, button, label

EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp'}
MAX_IMAGE_BYTES = 8_000_000


class RecipeImageEditor:
    def __init__(self, locale, recipe_id, references, user_data_dir=None):
        self.locale = locale
        self.recipe_id = recipe_id
        self.user_data_dir = user_data_dir
        self.slots = {number: None for number in range(1, 4)}
        for reference in references:
            name = reference.rsplit('/', 1)[-1]
            if match := PHOTO_NAME.fullmatch(name):
                self.slots[int(match.group(1))] = {'reference': reference}
        self.root = box(spacing=7, size_hint_y=None)
        self.root.bind(minimum_height=self.root.setter('height'))
        self.root.add_widget(label(t(locale, 'admin_images'), 16, GOLD, 28, True))
        self.context = label('', 13, GOLD, 28)
        self.root.add_widget(self.context)
        self.notice = label('', 13, RED, 26)
        self.root.add_widget(self.notice)
        self.cards = {}
        for number in self.slots:
            card = box(False, padding=10, spacing=10, color=PANEL_LIGHT,
                       size_hint_y=None, height=dp(132))
            self.cards[number] = card
            self.root.add_widget(card)
        self.render()

    def _file(self, entry):
        if entry is None:
            return None
        if 'path' in entry:
            return Path(entry['path'])
        return image_file(self.recipe_id, entry['reference'], self.user_data_dir)

    @staticmethod
    def _digest(path):
        with Path(path).open('rb') as stream:
            return hashlib.file_digest(stream, 'sha256').digest()

    def render(self):
        for number, card in self.cards.items():
            card.clear_widgets()
            entry = self.slots[number]
            path = self._file(entry)
            preview = box(padding=4, color=PANEL, size_hint_x=None, width=dp(112))
            if path is not None and path.is_file():
                preview.add_widget(Image(source=str(path), fit_mode='contain'))
            else:
                preview.add_widget(label(t(self.locale, 'admin_no_preview'), 12, MUTED, 98))
            card.add_widget(preview)
            details = box(spacing=4)
            details.add_widget(label(f"{t(self.locale, 'admin_image_slot')} {number}", 14, GOLD, 28, True))
            filename = label(path.name if path is not None else t(self.locale, 'admin_no_image'),
                             12, MUTED, 28)
            filename.shorten = True
            filename.shorten_from = 'right'
            details.add_widget(filename)
            controls = box(False, spacing=8, size_hint_y=None, height=dp(44))
            controls.add_widget(button(t(self.locale, 'admin_replace_image' if entry else 'admin_add_image'),
                                       lambda slot=number: self.choose(slot), 'outline', height=44))
            remove = button(t(self.locale, 'remove'), lambda slot=number: self.remove(slot),
                            'danger_outline', height=44)
            remove.disabled = entry is None
            controls.add_widget(remove)
            details.add_widget(controls)
            card.add_widget(details)

    def remove(self, number):
        self.slots[number] = None
        self.notice.text = ''
        self.render()

    def select(self, number, path):
        candidate = Path(path)
        if (not candidate.is_file() or candidate.suffix.lower() not in EXTENSIONS or
                candidate.stat().st_size > MAX_IMAGE_BYTES):
            self.notice.text = t(self.locale, 'admin_invalid_image')
            return False
        digest = self._digest(candidate)
        for slot, entry in self.slots.items():
            other = self._file(entry)
            if slot != number and other is not None and other.is_file() and self._digest(other) == digest:
                self.notice.text = t(self.locale, 'admin_duplicate_image')
                return False
        self.slots[number] = {'path': str(candidate), 'token': uuid4().hex[:12]}
        self.notice.text = ''
        self.render()
        return True

    def choose(self, number):
        home = Path.home()
        start = home / 'Pictures' if (home / 'Pictures').is_dir() else home
        content = box(padding=8, spacing=8)
        chooser = FileChooserListView(path=str(start), filters=['*.png', '*.jpg', '*.jpeg', '*.webp',
                                                               '*.PNG', '*.JPG', '*.JPEG', '*.WEBP'],
                                      multiselect=False, dirselect=False)
        content.add_widget(chooser)
        preview = Image(fit_mode='contain', size_hint_y=None, height=dp(140))
        content.add_widget(preview)
        picker_notice = label('', 13, RED, 26)
        content.add_widget(picker_notice)
        controls = box(False, spacing=8, size_hint_y=None, height=dp(40))
        dialog = styled_popup(t(self.locale, 'admin_choose_image'), content, 0.85, 0.86)
        selected = button(t(self.locale, 'admin_use_image'), kind='primary', height=40)
        selected.disabled = True

        def update(*_):
            path = Path(chooser.selection[0]) if chooser.selection else None
            valid = path is not None and path.is_file() and path.suffix.lower() in EXTENSIONS
            preview.source = str(path) if valid else ''
            selected.disabled = not valid
            picker_notice.text = ''

        def accept():
            if chooser.selection and self.select(number, chooser.selection[0]):
                dialog.dismiss()
            else:
                picker_notice.text = self.notice.text

        chooser.bind(selection=update)
        selected.bind(on_release=lambda *_: accept())
        controls.add_widget(button(t(self.locale, 'cancel'), dialog.dismiss, height=40))
        controls.add_widget(selected)
        content.add_widget(controls)
        dialog.open()
        return dialog

    def values(self, recipe_id):
        references, uploads = [], []
        for number, entry in self.slots.items():
            if entry is None:
                continue
            if 'path' in entry:
                extension = Path(entry['path']).suffix.lower().lstrip('.')
                reference = f"recipe_images/{recipe_id}/image_0{number}-{entry['token']}.{extension}"
                uploads.append({'reference': reference, 'path': entry['path']})
            else:
                reference = entry['reference']
            references.append(reference)
        return references, uploads
