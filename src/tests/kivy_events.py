"""Dispatch button releases with the signature used by the installed Kivy."""

from kivy import __version__ as kivy_version


def release(widget):
    if int(kivy_version.split('.')[0]) >= 3:
        widget.dispatch('on_release', None)
    else:
        widget.dispatch('on_release')
