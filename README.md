# HSSP 爬虫框架

一个基于python asyncio开发的爬虫框架

## 作者

- [@昊色居士](https://github.com/x-haose)

## 特性

- 使用scrapy框架的选择器`parsel`作为内置网页选择器
- 使用python async异步爬取
- 基于tenacity的自动异常重试
- 基于fake-useragent的可选随机UA
- 支持爬取结束自动导出至json、xml、csv、xls文件
- 内置`pyppeteer`框架支持动态爬取
- 支持以`Item`方式爬取

## 安装

使用 pip 安装 hssp

```bash
  pip install hssp
```

## 路线图

- 完善使用pyppeteer对网页内容进行下载（实现部分功能，但存在问题）

- 增加基于apscheduler进行定时爬取

- 爬取结束自动导出至数据库

- 完善使用文档

- 增加更多示例

## 支持

如需支持，请发送电子邮件至 xhrtxh@gmail.com。

## 开发测试

项目使用`pdm`管理依赖，需先安装pdm

```bash
    pip install pdm
    pdm sync
```

## 技术栈

- 异步网络请求 httpx
- 网页选择器 parsel
- 日志打印 loguru
- 异常重试 tenacity
- 随机UA fake-useragent>
- 动态爬取 pyppeteer
- 数据处理 pandas、orjson、aiofiles

## 致谢

- [基于asyncio和aiohttp的异步爬虫框架](https://github.com/howie6879/ruia)
- [scrapy爬虫框架](https://github.com/scrapy/scrapy)

