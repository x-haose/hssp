# HSSP 爬虫框架

一个基于python asyncio开发的爬虫框架 (开发中)

## 作者

- [@昊色居士](https://github.com/x-haose)

## 特性

- 使用scrapy框架的选择器`parsel`作为内置网页选择器
- 基于tenacity的自动异常重试
- 基于fake-useragent的可选随机UA
- 可选的多种下载器: httpx、aiohttp、requests、curl-cffi等
- 请求前、响应后、重试后监听

## 计划
- 在情求过程中临时更换下载器：比如net初始化时使用的是httpx下载器，其中一个情求要临时切换至 `DrissionPage`, 其他的依旧是httpx
- 支持 `DrissionPage` 浏览器渲染的下载器
- 支持 `playwright` 浏览器渲染的下载器
- 针对 `curl-cffi` 支持更多配置项及自定义项
- 编写详细使用文档

## 安装

###

使用 pip 安装 hssp

```bash
pip install hssp
```

###

使用 rye 安装 hssp

```bash
rye add hssp
```

## 支持

如需支持，请发送电子邮件至 xhrtxh@gmail.com。

## 开发测试

项目使用`rye`管理依赖，需先安装rye

```bash
    rye sync
```
