import asyncio
import os
import sys
import weakref
from dataclasses import field
from datetime import datetime
from functools import reduce
from inspect import isawaitable
from pathlib import Path
from types import AsyncGeneratorType
from typing import Optional, Union, Iterable, Callable, Tuple, Coroutine

from fake_useragent import UserAgent
from httpx import AsyncClient
from loguru import logger
from pyppeteer import launch
from pyppeteer.browser import Browser

from hssp.exceptions import NotImplementedParseError, SpiderHookError, InvalidCallbackResult
from hssp.item import Item, ItemMgr
from hssp.middleware import Middleware
from hssp.request import Request
from hssp.response import Response
from hssp.settings import Setting, ReqSetting

if sys.version_info >= (3, 8) and sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

if sys.version_info >= (3, 9):
    async_all_tasks = asyncio.all_tasks
    async_current_task = asyncio.current_task
else:
    async_all_tasks = asyncio.Task.all_tasks
    async_current_task = asyncio.tasks.Task.current_task
try:
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    uvloop = None


class Spider:
    name: str = 'hssp'

    # 开始的url列表
    start_urls: list = None

    # 向第一个回调函数中传递的数据
    metadata: dict = field(default={})

    # 统计成功和失败的个数
    _success_counts: int = 0
    _failed_counts: int = 0

    # 任务队列
    _worker_tasks: list = []

    _fake_useragent: UserAgent = None

    _browser: Browser = None

    def __init__(
            self,
            setting: Setting = None,
            loop: Optional[asyncio.AbstractEventLoop] = None,
            middleware: Union[Iterable, Middleware] = None,
            **kwargs
    ):
        # 爬虫的设置类
        self._setting = setting or Setting()

        # 事件循环
        self._loop = loop

        # 中间件
        if isinstance(middleware, list):
            self._middleware = reduce(lambda x, y: x + y, middleware)
        else:
            self._middleware = middleware or Middleware()

        # 设置事件循环
        asyncio.set_event_loop(self._loop)

        # 异步队列
        self.request_queue = asyncio.Queue()

        # 信号量，用于控制并发
        self._sem = asyncio.Semaphore(self._setting.concurrency)

        # 日志
        logger.remove()
        logger.add(sys.stderr, level=self._setting.log_Level)
        self.logger = logger

        # 请求会话
        self.session = AsyncClient(proxies=self._setting.proxies, verify=False)

        # 请求的全局设置
        self.req_setting = self._setting
        self.req_setting.__class__ = ReqSetting

        # 设置假ua
        if self._setting.random_ua:
            fake_useragent_path = Path(os.path.abspath(__file__)).parent / 'res/fake_useragent_0.1.11.json'
            self._fake_useragent = UserAgent(path=str(fake_useragent_path), verify_ssl=False)

        if isinstance(self._setting.out_path, list):
            outpus = self._setting.out_path
        else:
            outpus = [self._setting.out_path]
        self.item_mgr = ItemMgr(outputs=outpus)

    async def __async_init__(self):
        """
        异步初始化方法
        :return:
        """
        self._browser = await launch(
            autoClose=False,
            handleSIGINT=False,
            handleSIGTERM=False,
            headless=False,
            ignoreHTTPSErrors=True,
            ignoreDefaultArgs=['--enable-automation'],
            userDataDir=str(Path(os.environ.get('APPDATA')) / "hssp_user_data"),
            args=[
                '--disable-infobars',
                '--no-sandbox'
            ]
        )

    async def process_failed_response(self, request, response):
        """
        响应失败的处理
        :param request: 请求
        :param response: 响应
        :return:
        """
        pass

    async def process_succeed_response(self, request, response):
        """
        响应成功的处理
        :param request: 请求
        :param response: 响应
        :return:
        """
        pass

    async def process_item(self, item: Item):
        """
        处理item
        :param item: Item
        :return:
        """
        self.item_mgr.add_item(item)
        if not self._setting.out_path:
            return
        await self.item_mgr.export()

    async def parse(self, response):
        """
        字类必须实现。用于处理start_urls的回调
        :param response: Response
        :return:
        """
        raise NotImplementedParseError("<!!! parse function is expected !!!>")

    async def _run_spider_hook(self, hook_func):
        """
        运行爬虫开始之后、结束之前的函数
        :param hook_func: aws function
        :return:
        """
        if not callable(hook_func):
            return
        try:
            aws_hook_func = hook_func(weakref.proxy(self))
            if isawaitable(aws_hook_func):
                await aws_hook_func
        except Exception as e:
            raise SpiderHookError(f"<Hook {hook_func.__name__}: {e}")

    async def process_start_urls(self):
        """
        处理开始的地址
        :return: 异步请求迭代器
        """
        for url in self.start_urls:
            yield await self.get(url=url, callback=self.parse, metadata=self.metadata)

    async def _process_response(self, request: Request, response: Response):
        """
        响应成功或失败的处理
        :param request: 请求
        :param response: 响应
        :return:
        """
        if response.ok:
            # 处理成功的响应
            self._success_counts += 1
            await self.process_succeed_response(request, response)
        else:
            # 处理失败的响应
            self._failed_counts += 1
            await self.process_failed_response(request, response)

    async def _run_request_middleware(self, request: Request):
        """
        运行请求中间件
        :param request: 请求
        :return:
        """
        if not self._middleware.request_middleware:
            return
        for middleware in self._middleware.request_middleware:
            if not callable(middleware):
                continue
            try:
                aws_middleware_func = middleware(self, request)
                if isawaitable(aws_middleware_func):
                    await aws_middleware_func
                else:
                    self.logger.error(f"<Middleware {middleware.__name__}: 必须是一个协程函数")
            except Exception as e:
                self.logger.error(f"<Middleware {middleware.__name__}: {e}")

    async def _run_response_middleware(self, request: Request, response: Response):
        """
        运行响应中间件
        :param request: 请求
        :param response: 响应
        :return:
        """
        if not self._middleware.response_middleware:
            return
        for middleware in self._middleware.response_middleware:
            if not callable(middleware):
                continue
            try:
                aws_middleware_func = middleware(self, request, response)
                if isawaitable(aws_middleware_func):
                    await aws_middleware_func
                else:
                    self.logger.error(f"<Middleware {middleware.__name__}: 必须是一个协程函数")
            except Exception as e:
                self.logger.error(f"<Middleware {middleware.__name__}: {e}")

    async def get(
            self,
            url: str,
            *,
            params: dict = None,
            headers: dict = None,
            cookies: dict = None,
            callback: Callable = None,
            metadata: dict = None,
            is_browser: bool = False,
            **kwargs
    ) -> Request:
        """
        发生一个get请求
        :param url: 请求地址
        :param params: 地址中带的参数
        :param headers: 请求头
        :param cookies: 传递的cookies
        :param callback: 请求结束之后的回调函数
        :param metadata: 向函数中传递的数据
        :param is_browser: 是否使用浏览器获取，速度会慢，但会执行网页中的js脚本
        :param kwargs: httpx 请求的其他参数
        :return:
        """
        ua = self._fake_useragent.random if self._setting.random_ua else None
        return Request(
            "GET",
            url,
            self.req_setting,
            params=params,
            user_agent=ua,
            headers=headers,
            cookies=cookies,
            callback=callback,
            metadata=metadata,
            browser=self._browser,
            is_browser=is_browser,
            kwargs=kwargs
        )

    async def post(
            self,
            url: str,
            *,
            data: dict = None,
            json: dict = None,
            params: dict = None,
            headers: dict = None,
            cookies: dict = None,
            callback: Callable = None,
            metadata: dict = None,
            **kwargs
    ) -> Request:
        """
        发送一个post请求
        :param url: 请求地址
        :param data: 传递的数据
        :param json: 传递的json
        :param params: 地址中带的参数
        :param headers: 请求头
        :param cookies: 传递的cookies
        :param callback: 请求结束之后的回调函数
        :param metadata: 向函数中传递的数据
        :param kwargs: httpx 请求的其他参数
        :return:
        """
        ua = self._fake_useragent.random if self._setting.random_ua else None
        return Request(
            "POST",
            url,
            self.req_setting,
            data=data,
            json=json,
            params=params,
            user_agent=ua,
            headers=headers,
            cookies=cookies,
            callback=callback,
            metadata=metadata,
            kwargs=kwargs
        )

    async def handle_request(self, request: Request) -> Tuple[AsyncGeneratorType, Response]:
        """
        处理请求
        :param request:
        :return:
        """
        callback_result, response = None, None
        try:
            await self._run_request_middleware(request)
            callback_result, response = await request.request(self._sem)
            await self._run_response_middleware(request, response)
            await self._process_response(request=request, response=response)
        except NotImplementedParseError as e:
            self.logger.error(e)
            await self.stop()
        except Exception as e:
            self.logger.error(f"<Callback[{request.callback.__name__}]: [{e.__class__.__name__}]{e}")
        finally:
            await request.close()

        return callback_result, response

    @classmethod
    def start(
            cls,
            setting: Setting = None,
            middleware: Union[Iterable, Middleware] = None,
            loop: Optional[asyncio.AbstractEventLoop] = None,
            after_start=None,
            before_stop=None,
            close_event_loop=True,
            **kwargs
    ):
        """
        类方法。 开始爬虫
        :param setting: 设置
        :param after_start: 处理开始之后
        :param before_stop: 处理结束之前
        :param middleware: 自定义中间件，可以的列表或单独中间件
        :param loop: 事件循环
        :param close_event_loop: 结束后是否关闭事件循环
        :return: An instance of :cls:`Spider`
        """
        loop = loop or asyncio.new_event_loop()
        spider_ins = cls(setting=setting, middleware=middleware, loop=loop, **kwargs)

        # Actually start crawling
        spider_ins._loop.run_until_complete(
            spider_ins._start(after_start=after_start, before_stop=before_stop)
        )
        spider_ins._loop.run_until_complete(spider_ins._loop.shutdown_asyncgens())
        if close_event_loop:
            spider_ins._loop.close()

        return spider_ins

    async def _start(self, after_start=None, before_stop=None):
        """
        开始爬虫的内部函数
        :param after_start: 处理开始之后
        :param before_stop: 处理结束之前
        :return:
        """
        self.logger.info(f"{self.name} Spider started!")
        # await self.__async_init__()

        start_time = datetime.now()

        # 运行爬虫开始之前的hook函数
        await self._run_spider_hook(after_start)

        # Actually run crawling
        try:
            await self.start_master()
        finally:
            # 运行爬虫结束后的hook函数
            await self._run_spider_hook(before_stop)

            await self.stop()
            # Display logs about this crawl task
            end_time = datetime.now()
            self.logger.success(f"总请求数量: {self._failed_counts + self._success_counts}")

            if self._failed_counts:
                self.logger.success(f"失败的请求: {self._failed_counts}")
            self.logger.success(f"总用时: {end_time - start_time}")
            self.logger.success("爬取完成")

    async def start_master(self):
        """
        开始爬取
        """
        async for request_ins in self.process_start_urls():
            self.request_queue.put_nowait(self.handle_request(request_ins))
        workers = [asyncio.ensure_future(self.start_worker()) for _ in range(self._setting.concurrency)]
        for worker in workers:
            self.logger.info(f"Worker started: {id(worker)}")
        await self.request_queue.join()

    async def start_worker(self):
        """
        开始爬取工作
        :return:
        """
        while True:
            request_item = await self.request_queue.get()
            self._worker_tasks.append(request_item)
            if self.request_queue.empty():
                results = await asyncio.gather(*self._worker_tasks, return_exceptions=True)
                for task_result in results:
                    if not isinstance(task_result, RuntimeError) and task_result:
                        callback_results, response = task_result
                        if isinstance(callback_results, AsyncGeneratorType):
                            await self._process_async_callback(callback_results)
                self._worker_tasks = []
            self.request_queue.task_done()

    async def _process_async_callback(self, callback_results: AsyncGeneratorType):
        try:
            async for callback_result in callback_results:
                # 处理异步
                if isinstance(callback_result, Coroutine):
                    callback_result = await callback_result

                # 处理异步生成器类型：再次调用
                if isinstance(callback_result, AsyncGeneratorType):
                    await self._process_async_callback(callback_result)

                # 处理下一个请求
                elif isinstance(callback_result, Request):
                    self.request_queue.put_nowait(self.handle_request(request=callback_result))

                # 处理item
                elif isinstance(callback_result, Item):
                    # Process target item
                    await self.process_item(callback_result)

                # 其他的就报错
                else:
                    callback_result_name = type(callback_result).__name__
                    raise InvalidCallbackResult(f"<Parse invalid callback result type: {callback_result_name}>")
        except Exception as e:
            self.logger.exception(e)

    async def stop(self):
        """
        完成正在运行的任务，取消剩余的任务
        :return:
        """
        self.logger.success(f"Stopping spider: {self.name}")
        await self.session.aclose()
        await self.cancel_all_tasks()

    @staticmethod
    async def cancel_all_tasks():
        """
        取消所有的任务
        :return:
        """
        tasks = []
        for task in async_all_tasks():
            if task is not async_current_task():
                tasks.append(task)
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
