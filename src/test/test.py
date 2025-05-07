import asyncio

from hssp import Net
from hssp.logger.log import Logger, hssp_logger
from hssp.models.net import RequestModel
from hssp.network.downloader import HttpxDownloader
from hssp.network.response import Response


def request_retry(exception):
    logger.info(f"请求报错了:{exception}。正在重试")


async def request_before(request_data: RequestModel):
    logger.info(f"请求之前打印：{request_data}")
    request_data.url_params = {"a": 1}
    return request_data


def request_before_2(request_data: RequestModel):
    logger.info(f"请求之前打印：{request_data}")
    request_data.url_params = {"a": 1, "b": 2}
    return request_data


async def response_after(response_data: Response):
    logger.info(f"响应之后打印：{response_data.request_data} {response_data}")


def response_after_2(response: Response):
    logger.info(f"响应之后打印：{response.request_data} {response}")
    response.cookies = {"aaaa": 1243}
    return response


async def main():
    net = Net(HttpxDownloader)
    net.request_retry_signal.connect(request_retry)
    net.request_before_signal.connect(request_before)
    net.request_before_signal.connect(request_before_2)
    net.response_after_signal.connect(response_after)
    net.response_after_signal.connect(response_after_2)

    async def _send():
        resp = await net.post(
            "https://httpbin.org/post",
            timeout=3,
            form_data={"aa": 111},
            retrys_count=0,
        )
        logger.info(
            "\n"
            f"情求头：{resp.request_data.headers}\n"
            f"响应body：{resp.content}\n"
            f"响应json：{resp.json}\n"
            f"响应头：{resp.headers}\n"
            f"响应cookies：{resp.cookies}\n"
            f"客户端cookies：{resp.client_cookies}\n"
            f"客户端cookies：{net.get_cookies()}"
        )

    await asyncio.gather(*[_send() for _ in range(1)])

    await net.close()


if __name__ == "__main__":
    Logger.init_logger("test-a.log", ["httpcore.http11", "httpcore.connection", "httpx###DEBUG"])
    logger = hssp_logger.getChild("test")
    asyncio.run(main())
