import random
import string


def rand_str(length: int, style: str | None = None):
    """
    获取固定长度的随机字符串
    Args:
        style: 格式：默认为大写字母+小写字母+数字
        length: 长度

    Returns:

    """
    if not style:
        style = string.digits + string.ascii_letters
    max_length = len(style)
    if length <= max_length:
        return "".join(random.sample(style, length))

    text = ""
    count = length // max_length
    remainder = length % max_length
    for _ in range(count):
        text += rand_str(max_length)
    if remainder > 0:
        text += rand_str(remainder)
    return text


def random_1():
    """
    返回0-1之间的随机数
    Returns:

    """
    return random.random()
