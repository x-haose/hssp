from pathlib import Path

import orjson
import aiofiles
from pandas import DataFrame
from pandas import concat

from hssp.item import Item


class ItemMgr(object):
    def __init__(self, outputs: list):
        self.outputs = set(outputs)
        self.df = DataFrame()
        self._data_list = []

    def add_item(self, item: Item):
        item_copy = dict()
        self._data_list.append(item.copy())
        for k, v in item.copy().items():
            if type(v) == list:
                item_copy[k] = ' |$| '.join(v)
            else:
                item_copy[k] = v
        df = DataFrame(item_copy, index=[0])
        self.df = concat([self.df, df], ignore_index=True)

    async def export(self):
        for path in self.outputs:
            suffix = Path(path).suffix
            method = getattr(self, f"to_{suffix[1:]}")
            if method:
                await method(path)

    async def to_json(self, path):
        """
        导出至json文件
        Args:
            path: 文件路径

        Returns:

        """
        # 使用orjson 方式导出 aiofiles 写入文件
        async with aiofiles.open(path, mode='wt', encoding='utf-8') as f:
            await f.write(str(orjson.dumps(self._data_list), encoding='utf-8'))

        # pandas 方式导出 暂时不用
        # return self.df.to_json(path, force_ascii=False, orient='records')

    async def to_xml(self, path):
        """
        导出至xml文件
        Args:
            path: 文件路径

        Returns:

        """
        self.df.to_xml(path, index=False)

    async def to_csv(self, path):
        """
        导出至csv文件
        Args:
            path: 文件路径

        Returns:

        """
        return self.df.to_csv(path, index=False)

    async def to_xls(self, path):
        """
        导出xls格式的excel文件
        Args:
            path: 文件路径

        Returns:

        """
        self.df.to_excel(path + 'x', index=False)

    async def to_xlsx(self, path):
        """
        导出xlsx格式的excel文件
        Args:
            path: 文件路径

        Returns:

        """
        self.df.to_excel(path, index=False)

    def to_data(self):
        """
        返回原数据
        Returns:

        """
        return self._data_list
