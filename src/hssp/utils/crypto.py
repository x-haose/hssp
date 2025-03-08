from hashlib import md5, sha1, sha256

from Cryptodome.Cipher import AES, ARC4
from Cryptodome.Util.Padding import pad, unpad


def encrypt_aes_256_cbc(data: bytes, key: bytes, iv: bytes) -> bytes:
    """
    aes_256_cbc加密 不填充
    Args:
        data: 加密的数据
        key: key
        iv: iv

    Returns:

    """

    cipher = AES.new(key, AES.MODE_CBC, iv)
    ciphertext = cipher.encrypt(data)
    return ciphertext


def decrypt_aes_256_cbc(data: bytes, key: bytes, iv: bytes) -> bytes:
    """
    aes_256_cbc解密 不填充
    Args:
        data: 数据
        key: key
        iv: iv

    Returns:

    """
    cipher = AES.new(key, AES.MODE_CBC, iv)
    ciphertext = cipher.decrypt(data)
    return ciphertext


def encrypt_aes_256_ecb(data: bytes, key: bytes) -> bytes:
    """
    aes_256_ecb加密 不填充
    Args:
        data: 加密的数据
        key: key

    Returns:

    """

    cipher = AES.new(key, AES.MODE_ECB)
    ciphertext = cipher.encrypt(data)
    return ciphertext


def decrypt_aes_256_ecb(data: bytes, key: bytes) -> bytes:
    """
    aes_256_ecb解密 不填充
    Args:
        data: 数据
        key: key

    Returns:

    """
    cipher = AES.new(key, AES.MODE_ECB)
    ciphertext = cipher.decrypt(data)
    return ciphertext


def encrypt_aes_256_cbc_pad7(data: bytes, key: bytes, iv: bytes) -> bytes:
    """
    aes_256_cbc加密 pad7填充
    Args:
        data: 加密的数据
        key: key
        iv: iv

    Returns:

    """

    data = pad(data, 16)
    return encrypt_aes_256_cbc(data, key, iv)


def decrypt_aes_256_cbc_pad7(data: bytes, key: bytes, iv: bytes) -> bytes:
    """
    aes_256_cbc解密 pad7填充
    Args:
        data: 数据
        key: key
        iv: iv

    Returns:

    """
    data = decrypt_aes_256_cbc(data, key, iv)
    return unpad(data, AES.block_size)


def encrypt_aes_256_ecb_pad7(data: bytes, key: bytes) -> bytes:
    """
    aes_256_ecb加密 pad7填充
    Args:
        data: 加密的数据
        key: key

    Returns:

    """

    data = pad(data, 16)
    return encrypt_aes_256_ecb(data, key)


def decrypt_aes_256_ecb_pad7(data: bytes, key: bytes) -> bytes:
    """
    aes_256_ecb解密 pad7填充
    Args:
        data: 数据
        key: key

    Returns:

    """
    data = decrypt_aes_256_ecb(data, key)
    return unpad(data, AES.block_size)


def md5_hash(data: bytes | str, result_type: str = "hex"):
    """
    md5 hash
    Args:
        data: 数据，字节数据或字符串，字符串或使用utf8编码为字节
        result_type: 返回类型，默认为16进制字符串，bytes为字节

    Returns:
        返回经过md5哈希后的值
    """
    data = data if isinstance(data, bytes) else data.encode("utf-8")
    result = md5(data, usedforsecurity=False)  # type: ignore
    if result_type == "hex":
        return result.hexdigest()
    else:
        return result.digest()


def sha1_hash(data: bytes | str, result_type: str = "hex"):
    """
    sha1 hash
    Args:
        data: 数据，字节数据或字符串，字符串或使用utf8编码为字节
        result_type: 返回类型，默认为16进制字符串，bytes为字节

    Returns:
        返回经过sha256哈希后的值
    """
    data = data if isinstance(data, bytes) else data.encode("utf-8")
    result = sha1(data)  # type: ignore  # nosec
    if result_type == "hex":
        return result.hexdigest()
    else:
        return result.digest()


def sha256_hash(data: bytes | str, result_type: str = "hex"):
    """
    sha256 hash
    Args:
        data: 数据，字节数据或字符串，字符串或使用utf8编码为字节
        result_type: 返回类型，默认为16进制字符串，bytes为字节

    Returns:
        返回经过sha256哈希后的值
    """
    data = data if isinstance(data, bytes) else data.encode("utf-8")
    result = sha256(data)  # type: ignore
    if result_type == "hex":
        return result.hexdigest()
    else:
        return result.digest()


def rc4_encrypt(data: bytes, key: bytes) -> bytes:
    """
    RC4 加密
    Args:
        data: 数据
        key: key

    Returns:

    """
    rc4 = ARC4.new(key)
    return rc4.encrypt(data)


def rc4_decrypt(data: bytes, key: bytes) -> bytes:
    """
    RC4 解密
    Args:
        data: 数据
        key: key

    Returns:

    """
    rc4 = ARC4.new(key)
    return rc4.decrypt(data)
