class IgnoreThisItem(Exception):
    """
    忽略这个Item
    """
    pass


class InvalidCallbackResult(Exception):
    """
    回调结果无效
    """
    pass


class NotImplementedParseError(Exception):
    """
    一个解析函数都没有
    """
    pass


class SpiderHookError(Exception):
    """
    在爬虫执行Hook的时候发生异常
    """
    pass


class BrowerError(Exception):
    """
    使用浏览器请求时发生异常
    """
