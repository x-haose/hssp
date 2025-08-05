import hashlib
from hashlib import md5, sha1, sha256

from Cryptodome.Cipher import AES, ARC4
from Cryptodome.Util.Padding import pad, unpad


def encrypt_aes_256_cbc(data: bytes, key: bytes, iv: bytes, style: str | None = "pkcs7") -> bytes:
    """
    aes_256_cbc加密
    Args:
        data: 加密的数据
        key: key
        iv: iv
        style: 填充算法。设置为None不填充

    Returns:

    """
    if style:
        data = pad(data, 16, style)

    cipher = AES.new(key, AES.MODE_CBC, iv)
    ciphertext = cipher.encrypt(data)

    return ciphertext


def decrypt_aes_256_cbc(data: bytes, key: bytes, iv: bytes, style: str | None = "pkcs7") -> bytes:
    """
    aes_256_cbc解密 不填充
    Args:
        data: 数据
        key: key
        iv: iv
        style: 填充算法。设置为None不填充

    Returns:

    """
    cipher = AES.new(key, AES.MODE_CBC, iv)
    ciphertext = cipher.decrypt(data)

    if style:
        ciphertext = unpad(ciphertext, AES.block_size)

    return ciphertext


def encrypt_aes_256_ecb(data: bytes, key: bytes, style: str | None = "pkcs7") -> bytes:
    """
    aes_256_ecb加密
    Args:
        data: 加密的数据
        key: key
        style: 填充算法。设置为None不填充

    Returns:

    """

    if style:
        data = pad(data, 16, style)

    cipher = AES.new(key, AES.MODE_ECB)
    ciphertext = cipher.encrypt(data)
    return ciphertext


def decrypt_aes_256_ecb(data: bytes, key: bytes, style: str | None = "pkcs7") -> bytes:
    """
    aes_256_ecb解密
    Args:
        data: 数据
        key: key
        style: 填充算法。设置为None不填充

    Returns:

    """
    cipher = AES.new(key, AES.MODE_ECB)
    ciphertext = cipher.decrypt(data)

    if style:
        ciphertext = unpad(ciphertext, AES.block_size)

    return ciphertext


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


def evp_bytes_to_key(
    password: str, salt: bytes, key_size: int, iv_size: int, hash_algorithm: str = "md5", iterations: int = 1
) -> tuple[bytes, bytes]:
    """
    實現 OpenSSL 的 `EVP_BytesToKey` 演算法邏輯。

    警告：此函式已過時且被認為是密碼學上的弱實作。
    它只應該用於相容依賴此演算法的舊有系統。
    對於新的應用程式，請務必使用如 PBKDF2 或 Argon2 等現代化的金鑰衍生函式（KDF）。

    參數:
        password (str): 用於衍生金鑰的密碼。
        salt (bytes): 鹽值。為了與傳統 OpenSSL 相容，此值通常為 8 個位元組。
        key_size (int): 期望的金鑰長度（單位：位元組），例如 32 代表 AES-256。
        iv_size (int): 期望的初始向量（IV）長度（單位：位元組），例如 16 代表 AES-CBC。
        hash_algorithm (str): 要使用的雜湊演算法，例如 'md5' 或 'sha256'。
        iterations (int): 雜湊的迭代次數。標準的 `EVP_BytesToKey` 預設為 1。

    返回:
        一個包含衍生出的金鑰（key）和初始向量（IV）的元組（tuple）。
    """
    if not isinstance(password, bytes):
        password = password.encode("utf-8")

    final_length = key_size + iv_size
    key_iv = b""
    block = b""

    while len(key_iv) < final_length:
        hasher = hashlib.new(hash_algorithm)
        if block:
            hasher.update(block)
        hasher.update(password)
        hasher.update(salt)
        block = hasher.digest()

        # 如果指定，執行額外的迭代
        for _ in range(1, iterations):
            block = hashlib.new(hash_algorithm, block).digest()

        key_iv += block

    key = key_iv[:key_size]
    iv = key_iv[key_size:final_length]
    return key, iv
