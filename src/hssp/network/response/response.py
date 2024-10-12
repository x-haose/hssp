from furl import furl

from hssp.models.net import RequestModel
from hssp.network.response.selector import Selector


class Response:
    headers: dict
    content: bytes
    text: str
    json: dict

    def __init__(
        self,
        url: str,
        status_code: int,
        headers: dict,
        cookies: dict,
        client_cookies: dict,
        content: bytes,
        text: str,
        json: dict,
        request_data: RequestModel,
    ):
        self.request_data = request_data
        self.status_code = status_code
        self.cookies = cookies
        self.client_cookies = client_cookies
        self.headers = headers
        self.text = text
        self.content = content
        self.json = json

        self.url: str = url
        self.domain = furl(self.url).origin
        self.host = furl(self.url).host

        self.selector = Selector(self.text)

    def xpath(self, query: str):
        return self.selector.xpath(query, domain=self.domain)

    def css(self, query: str):
        return self.selector.css(query, domain=self.domain)

    def re(self, regex: str, replace_entities=True):
        return self.selector.re(regex, replace_entities=replace_entities)

    def re_first(self, regex: str, default=None, replace_entities=True):
        return self.selector.re_first(regex, default=default, replace_entities=replace_entities)
