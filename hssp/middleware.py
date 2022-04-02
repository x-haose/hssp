from collections import deque
from functools import wraps


class Middleware:
    """
    Define a middleware to customize the crawler request or response
    eg: middleware = Middleware()
    """

    def __init__(self):
        # request middleware
        self.request_middleware = deque()
        # response middleware
        self.response_middleware = deque()

    def request(self, req_middleware):
        """
        Define a Decorate to be called before a request.
        eg: @middleware.request
        """

        @wraps(req_middleware)
        def register_middleware():
            self.request_middleware.append(req_middleware)
            return req_middleware

        return register_middleware()

    def response(self, resp_middleware):
        """
        Define a Decorate to be called after a response.
        eg: @middleware.response
        """

        @wraps(resp_middleware)
        def register_middleware():
            self.response_middleware.appendleft(resp_middleware)
            return resp_middleware

        return register_middleware()

    def __add__(self, other):
        """
        自定义累加器
        :param other:
        :return:
        """
        # 新的中间件对象
        new_middleware = Middleware()

        # 追加自身的请求、响应中间件
        new_middleware.request_middleware.extend(self.request_middleware)
        new_middleware.request_middleware.extend(other.request_middleware)

        # 追加另一个的请求、响应中间件
        new_middleware.response_middleware.extend(other.response_middleware)
        new_middleware.response_middleware.extend(self.response_middleware)

        # 返回新的中间件对象
        return new_middleware


middleware = Middleware()
