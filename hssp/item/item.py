"""
Scrapy Item

See documentation in docs/topics/item.rst
"""
from abc import ABCMeta
from inspect import isawaitable
from typing import Dict, Any
from copy import deepcopy
from pprint import pformat
from dataclasses import dataclass, field
from collections.abc import MutableMapping

from parsel import Selector

from hssp import Response


@dataclass()
class Field(object):
    css_select: str = field(default_factory=str)
    xpath_select: str = field(default_factory=str)
    re_select: str = field(default_factory=str)
    default: Any = field(default=None)
    is_url: bool = field(default=False)
    many: bool = field(default=False)


class ItemMeta(ABCMeta):
    """Metaclass_ of :class:`Item` that handles field definitions.

    .. _metaclass: https://realpython.com/python-metaclasses
    """

    def __new__(mcs, class_name, bases, attrs):
        classcell = attrs.pop('__classcell__', None)
        new_bases = tuple(getattr(base, '_class') for base in bases if hasattr(base, '_class'))
        _class = super().__new__(mcs, 'x_' + class_name, new_bases, attrs)

        fields = getattr(_class, 'fields', {})
        new_attrs = {}
        for n in dir(_class):
            v = getattr(_class, n)
            if isinstance(v, Field):
                fields[n] = v
            elif n in attrs:
                new_attrs[n] = attrs[n]

        new_attrs['fields'] = fields
        new_attrs['_class'] = _class
        if classcell is not None:
            new_attrs['__classcell__'] = classcell
        return super().__new__(mcs, class_name, bases, new_attrs)


class DictItem(MutableMapping):
    fields: Dict[str, Field] = {}

    def __init__(self, *args, **kwargs):
        self._values = {}
        if args or kwargs:  # avoid creating dict for most common case
            for k, v in dict(*args, **kwargs).items():
                self[k] = v

    def __getitem__(self, key):
        return self._values.get(key)

    def __setitem__(self, key, value):
        if key in self.fields:
            self._values[key] = value
        else:
            raise KeyError(f"{self.__class__.__name__} does not support field: {key}")

    def __delitem__(self, key):
        del self._values[key]

    def __getattr__(self, name):
        if name in self.fields:
            return self.__getitem__(name)
        if name.endswith('__field'):
            name = 'url'.split('__field')[0]
            return self.fields.get(name)
        return super().__getattribute__(name)

    def __setattr__(self, name, value):
        if name in self.fields:
            self.__setitem__(name, value)
        else:
            super().__setattr__(name, value)

    def __len__(self):
        return len(self._values)

    def __iter__(self):
        return iter(self._values)

    def keys(self):
        return self._values.keys()

    def __repr__(self):
        return pformat(self.to_dict())

    def to_dict(self):
        return dict(self)

    def copy(self):
        """Return a :func:`~copy.deepcopy` of this item.
        """
        return deepcopy(self.to_dict())


class Item(DictItem, metaclass=ItemMeta):
    target_item = Field()

    @classmethod
    async def extracts(
            cls,
            *,
            response: Response = None,
            selector: Selector = None,
            domain: str = None
    ):
        if not response and not selector:
            return
        selector = selector or response.selector
        domain = domain or response.domain or ''

        items_field = cls.fields.get('target_item', None)
        if not items_field:
            raise ValueError("<Item: target_item 不存在, 请使用 extract>")

        items_field.many = True
        items_selector = await cls.extract(response=response, selector=selector, domain=domain, target=True)
        if items_selector:
            for each_selector in items_selector:
                _item = await cls.extract(response=response, selector=each_selector, domain=domain)
                yield _item
        else:
            value_error_info = "<Item: 无法获取target_item的值>"
            raise ValueError(value_error_info)

    @classmethod
    async def extract(
            cls,
            *,
            response: Response = None,
            selector: Selector = None,
            domain: str = None,
            target=False
    ):
        if not response and not selector:
            return
        selector = selector or response.selector
        domain = domain or response.domain or ''

        _item = cls()
        for key, f in _item.fields.items():
            # target_item 判断
            if target and key == "target_item":
                return _item._extract_field(f, selector, is_source=True)
            if (target and key != "target_item") or (not target and key == "target_item"):
                continue

            # 提取字段值
            value = _item._extract_field(f, selector)
            if not value:
                continue
            # 字段后处理
            clean_method = getattr(_item, f"_clean_{key}", None)
            if clean_method and callable(clean_method):
                aws_clean_func = clean_method(value)
                if isawaitable(aws_clean_func):
                    value = await aws_clean_func
                else:
                    value = clean_method(value)
            # url处理
            if f.is_url and domain and value.startswith('/'):
                value = domain + value
            if type(value) == str:
                value = value.strip()

            # 重新设置字段值
            _item.__setitem__(key, value)

        return _item

    def _extract_field(
            self,
            f: Field,
            selector: Selector,
            is_source=False,
    ):
        if not f.xpath_select and not f.css_select and not f.re_select:
            return
        if f.xpath_select and f.css_select:
            raise ValueError(f"{f.__class__.__name__} field: css、xpath选择器只可选择一个.")

        if f.css_select:
            elements = selector.css(f.css_select)
        elif f.xpath_select:
            elements = selector.xpath(f.xpath_select)
        else:
            elements = None

        if elements and is_source:
            return elements

        if elements:
            if f.many:
                results = elements.re(f.re_select) if f.re_select else elements.getall()
            else:
                results = elements.re_first(f.re_select) if f.re_select else elements.get()
        else:
            results = selector.re(f.re_select) if f.re_select else selector.re_first(f.re_select)

        null = [] if f.many else None
        return results or f.default or null


class TestItem(Item):
    a = Field(xpath_select='xxxx')
    b = Field(css_select='aaaa', re_select='ddd')
    c = 0


if __name__ == '__main__':
    item = TestItem()
    item.a = 1
    item.b = 2
    item.c = 10
    print(item)
    print(dict(item))
