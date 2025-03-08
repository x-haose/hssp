import time


def timestamp_13() -> int:
    """
    获取 13 位 时间戳

    Returns:
        int: 13 位 时间戳
    """

    return int(time.time() * 1000)
