from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad


def encrypt_aes_256_cbc_pad7(data: bytes, key: bytes, iv: bytes) -> bytes:
    """
    aes_256加密 pad7填充
    Args:
        data: 加密的数据
        key: key
        iv: iv

    Returns:

    """

    data = pad(data, 16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    ciphertext = cipher.encrypt(data)
    return ciphertext


def decrypt_aes_256_cbc_pad7(data: bytes, key: bytes, iv: bytes) -> bytes:
    """
    aes_256解密 pad7填充
    Args:
        data: 数据
        key: key
        iv: iv

    Returns:

    """
    data = unpad(data, 16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    ciphertext = cipher.decrypt(data)
    return ciphertext
