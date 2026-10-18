"""Choose a desktop fullscreen mode that keeps the display resolution."""


def minimum_window_size(scale):
    """Keep enough physical room for the controls as UI density increases."""
    return (round(900 + 540 * (scale - 1)),
            round(650 + 250 * (scale - 1)))


def fullscreen_mode(enabled):
    if not enabled:
        return False
    from kivy import __version__

    return 'auto' if __version__.split('.', 1)[0] == '2' else True
