"""Load Kivy's clipboard without logging failed optional X11 probes."""

import shutil
import sys
from functools import cache

from kivy import Logger


@cache
def get_clipboard():
    # SDL clipboard is usable without xclip or xsel. Kivy also probes the
    # optional X11 Cutbuffer and otherwise logs a misleading critical error.
    no_x11_cutbuffer = sys.platform == 'linux' and not (shutil.which('xclip') or shutil.which('xsel'))
    if no_x11_cutbuffer:
        def message_filter(record):
            return not record.getMessage().startswith('Cutbuffer: Unable to find any valuable Cutbuffer provider')

        Logger.addFilter(message_filter)
    try:
        from kivy.core.clipboard import Clipboard
    finally:
        if no_x11_cutbuffer:
            Logger.removeFilter(message_filter)
    if Clipboard.__class__.__name__ == 'ClipboardDummy':
        Logger.warning('Clipboard: no system clipboard provider is available')
    return Clipboard
