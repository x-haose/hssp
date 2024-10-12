import secrets
import string


def rand_str(length: int, style: str | None = None) -> str:
    """
    获取固定长度的随机字符串
    Args:
        length: 随机字符串的长度
        style: 随机字符的格式，默认为大写字母+小写字母+数字

    Returns:
        生成的随机字符串
    """
    style = style if style else string.digits + string.ascii_letters
    return "".join(secrets.choice(style) for _ in range(length))


def random_1():
    """
    返回0-1之间的随机数
    Returns:

    """
    return secrets.randbelow(10**6) / 10**6
