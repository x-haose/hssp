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
        """
        基于parsel的xpath解析
        Args:
            query: 查询条件

        Returns:

        """
        return self.selector.xpath(query, domain=self.domain)

    def css(self, query: str):
        """
        基于parsel的css解析
        Args:
            query: 查询条件

        Returns:

        """
        return self.selector.css(query, domain=self.domain)

    def re(self, regex: str, replace_entities=True):
        """
        基于parsel的re解析
        Args:
            regex: 正则表达式
            replace_entities: 默认情况下，字符实体引用会被替换为其对应的字符（“&amp;” 和 “&lt;” 除外）。
                                设置为“False” 会关闭这些替换。

        Returns:
            返回解析结果列表
        """
        return self.selector.re(regex, replace_entities=replace_entities)

    def re_first(self, regex: str, default=None, replace_entities=True):
        """
        基于parsel的re解析
        Args:
            regex: 正则表达式
            replace_entities: 默认情况下，字符实体引用会被替换为其对应的字符（“&amp;” 和 “&lt;” 除外）。
                                设置为“False” 会关闭这些替换。
            default: 取不到时的默认值

        Returns:
            返回解析结果的第一个
        """
        return self.selector.re_first(regex, default=default, replace_entities=replace_entities)

    def to_url(self, urls: list[str] | str):
        """
        获取绝对路径的url地址
        Args:
            urls: url或url列表

        Returns:
            返回转换后的url列表
        """
        urls = urls if type(urls) is list else [urls]
        urls = [furl(self.url).join(url).url for url in urls if not url.startswith("http")]
        return urls
