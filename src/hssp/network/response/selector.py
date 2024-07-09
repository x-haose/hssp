from parsel import Selector as BaseSelector

from parsel import SelectorList as BaseSelectorList


class SelectorList(BaseSelectorList):
    domain: str = ""

    def proc_result(self, value, domain, is_url):
        if is_url and domain and value.startswith("/"):
            value = domain + value
        if isinstance(value, str):
            value = value.strip()
        return value

    def getall(self, is_url=False):
        result = super(SelectorList, self).getall()
        return [self.proc_result(x, domain=self.domain, is_url=is_url) for x in result]

    def get(self, default=None, is_url=False):
        result = super(SelectorList, self).get(default=default)
        result = self.proc_result(result, self.domain, is_url)
        return result


class Selector(BaseSelector):
    selectorlist_cls = SelectorList

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def css(self, query, domain=None):
        result = super(Selector, self).css(query)
        result.domain = domain
        return result

    def xpath(self, query, namespaces=None, domain=None, **kwargs):
        result = super(Selector, self).xpath(query, namespaces=namespaces, **kwargs)
        result.domain = domain
        return result
