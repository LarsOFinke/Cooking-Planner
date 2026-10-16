"""Open the app's loopback API without inheriting system HTTP proxies."""

from urllib.parse import urlsplit
from urllib.request import ProxyHandler, Request, build_opener

from cooking_planner.api.LocalRedirectHandler import LocalRedirectHandler


_opener = build_opener(ProxyHandler({}), LocalRedirectHandler())


def open_local(request: Request, timeout: float):
    url = urlsplit(request.full_url)
    if url.scheme != 'http' or url.hostname != '127.0.0.1' or url.username or url.password:
        raise ValueError('Local API requests must target 127.0.0.1')
    return _opener.open(request, timeout=timeout)
