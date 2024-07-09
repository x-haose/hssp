class RequestException(Exception):
    """
    请求发生异常
    """

    def __init__(self, exception_type: str, exception_msg: list):
        self.exception_type = exception_type
        self.exception_msg = exception_msg


class RequestStateException(Exception):
    """
    请求状态发生异常
    """

    def __init__(self, code):
        self.code = code
