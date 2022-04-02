import cgi
import codecs
import typing
from dataclasses import dataclass, field

from parsel import Selector, SelectorList
from furl import furl


def is_known_encoding(encoding: str) -> bool:
    """
    Return `True` if `encoding` is a known codec.
    """
    try:
        codecs.lookup(encoding)
    except LookupError:
        return False
    return True


class TextDecoder:
    """
    Handles incrementally decoding bytes into text
    """

    def __init__(self, encoding: typing.Optional[str] = None):
        self.decoder: typing.Optional[codecs.IncrementalDecoder] = None
        if encoding is not None:
            self.decoder = codecs.getincrementaldecoder(encoding)(errors="replace")

    def decode(self, data: bytes) -> str:
        if self.decoder is None:
            # If this is the first decode pass then we need to determine which
            # encoding to use by attempting UTF-8 and raising any decode errors.
            attempt_utf_8 = codecs.getincrementaldecoder("utf-8")(errors="strict")
            try:
                attempt_utf_8.decode(data)
            except UnicodeDecodeError:
                # Could not decode as UTF-8. Use Windows 1252.
                self.decoder = codecs.getincrementaldecoder("cp1252")(errors="replace")
            else:
                # Can decode as UTF-8. Use UTF-8 with lenient error settings.
                self.decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")

        return self.decoder.decode(data)

    def flush(self) -> str:
        if self.decoder is None:
            return ""
        return self.decoder.decode(b"", True)


class MySelector(Selector):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.selectorlist_cls = MySelectorList

    def css(self, query, domain=None):
        result = super(MySelector, self).css(query)
        result.domain = domain
        return result

    def xpath(self, query, namespaces=None, domain=None, **kwargs):
        result = super(MySelector, self).xpath(query, namespaces=namespaces, **kwargs)
        result.domain = domain
        return result


class MySelectorList(SelectorList):
    domain: str = ''

    def proc_result(self, value, domain, is_url):
        if is_url and domain and value.startswith('/'):
            value = domain + value
        if type(value) == str:
            value = value.strip()
        return value

    def getall(self, is_url=False):
        result = super(MySelectorList, self).getall()
        return [self.proc_result(x, domain=self.domain, is_url=is_url) for x in result]

    def get(self, default=None, is_url=False):
        result = super(MySelectorList, self).get(default=default)
        result = self.proc_result(result, self.domain, is_url)
        return result


@dataclass
class Response(object):
    ok: bool = field(default=False)

    url: str = field(default_factory=str)
    metadata: dict = field(default_factory=dict)
    content: bytes = field(default_factory=bytes)
    status_code: int = field(default_factory=int)
    history: list = field(default_factory=list)
    headers: dict = field(default_factory=dict)
    cookies: dict = field(default_factory=dict)

    selector: MySelector = field(default=None, init=False)
    domain: str = field(default_factory=str, init=False)
    host: str = field(default_factory=str, init=False)
    _text: str = field(default_factory=str, init=False)
    _encoding: str = field(default=None, init=False)

    def __post_init__(self):
        self.selector = MySelector(self.text)
        self.domain = furl(self.url).origin
        self.host = furl(self.url).host

    @property
    def charset_encoding(self) -> typing.Optional[str]:
        """
        Return the encoding, as specified by the Content-Type header.
        """
        content_type = self.headers.get("Content-Type")
        if content_type is None:
            return None

        _, params = cgi.parse_header(content_type)
        if "charset" not in params:
            return None

        return params["charset"].strip("'\"")

    @property
    def encoding(self) -> typing.Optional[str]:
        """
        Return the encoding, which may have been set explicitly, or may have
        been specified by the Content-Type header.
        """
        if not self._encoding:
            encoding = self.charset_encoding
            if encoding is None or not is_known_encoding(encoding):
                self._encoding = "utf-8"
            else:
                self._encoding = encoding
        return self._encoding

    @encoding.setter
    def encoding(self, value: str) -> None:
        self._encoding = value

    @property
    def text(self) -> str:
        if not self._text:
            content = self.content
            if not content:
                self._text = ""
            else:
                decoder = TextDecoder(encoding=self.encoding)
                self._text = "".join([decoder.decode(self.content), decoder.flush()])
        return self._text

    def json(self, **kwargs):
        pass

    def xpath(self, query):
        return self.selector.xpath(query, domain=self.domain)

    def css(self, query):
        return self.selector.css(query, domain=self.domain)

    def re(self, regex, replace_entities=True):
        return self.selector.re(regex, replace_entities=replace_entities)

    def re_first(self, regex, default=None, replace_entities=True):
        return self.selector.re_first(regex, default=default, replace_entities=replace_entities)
