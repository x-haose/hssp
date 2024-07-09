# HSSP 爬虫框架

一个基于python asyncio开发的爬虫框架 (开发中)

## 作者

- [@昊色居士](https://github.com/x-haose)

## 特性

- 使用scrapy框架的选择器`parsel`作为内置网页选择器
- 基于tenacity的自动异常重试
- 基于fake-useragent的可选随机UA
- 可选的多种下载器: httpx、aiohttp、requests等
- 请求前、响应后、重试后监听

## 安装（后续支持）

使用 pip 安装 hssp

```bash

```

## 路线图

## 支持

如需支持，请发送电子邮件至 xhrtxh@gmail.com。

## 开发测试

项目使用`rye`管理依赖，需先安装rye

```bash
    rye sync
```
