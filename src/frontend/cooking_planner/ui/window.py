"""Choose a desktop fullscreen mode that keeps the display resolution."""


def fullscreen_mode(enabled):
    if not enabled:
        return False
    from kivy import __version__

    return 'auto' if __version__.split('.', 1)[0] == '2' else True
