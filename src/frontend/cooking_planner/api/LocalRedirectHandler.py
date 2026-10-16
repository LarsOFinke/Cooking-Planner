"""Keep local API responses from redirecting requests or their token."""

from urllib.request import HTTPRedirectHandler


class LocalRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None
