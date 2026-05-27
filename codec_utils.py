import base64
import zlib

from reedsolo import RSCodec


APP_VERSION = "V1.1"
BASE36_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"


def bytes_to_base36(data):
    if not data:
        return "0"

    int_value = int.from_bytes(data, byteorder="big")
    encoded_chars = []
    while int_value > 0:
        int_value, remainder = divmod(int_value, 36)
        encoded_chars.append(BASE36_ALPHABET[remainder])

    return "".join(reversed(encoded_chars))


def base36_to_bytes(encoded_str):
    normalized_str = "".join(encoded_str.split()).lower()
    if not normalized_str:
        raise ValueError("输入内容不能为空")
    if normalized_str == "0":
        return b""

    try:
        int_value = int(normalized_str, 36)
    except ValueError as exc:
        raise ValueError("base36 内容非法，仅允许 0-9 和 a-z") from exc

    byte_length = max(1, (int_value.bit_length() + 7) // 8)
    return int_value.to_bytes(byte_length, byteorder="big")


def build_lowercase_payload(content):
    compressed = zlib.compress(content, level=9)
    payload = b"\x01" + len(content).to_bytes(4, byteorder="big") + compressed
    return bytes_to_base36(payload)


def parse_lowercase_payload(encoded_str):
    payload = base36_to_bytes(encoded_str)
    if len(payload) < 5:
        raise ValueError("base36 数据长度不足")
    if payload[0] != 1:
        raise ValueError("base36 数据头非法")

    raw_length = int.from_bytes(payload[1:5], byteorder="big")
    decoded = zlib.decompress(payload[5:])
    if len(decoded) != raw_length:
        raise ValueError("base36 数据长度校验失败")
    return decoded


def encode_payload(content, lowercase_mode=False, enhanced_mode=False, n_sym=10):
    if lowercase_mode:
        return build_lowercase_payload(content)

    if enhanced_mode:
        content = RSCodec(n_sym).encode(zlib.compress(content))

    return base64.b64encode(content).decode("utf-8")


def decode_bytes(encoded_str, decode_mode):
    normalized_str = "".join(encoded_str.split())
    if decode_mode == "base36":
        return parse_lowercase_payload(normalized_str)
    if decode_mode == "base64":
        return base64.b64decode(normalized_str, validate=True)
    raise ValueError(f"不支持的解码模式: {decode_mode}")


def decode_payload(encoded_str, decode_mode="base64", enhanced_mode=False, n_sym=10):
    normalized_str = encoded_str.strip()
    if not normalized_str:
        raise ValueError("输入内容不能为空")

    if decode_mode == "auto":
        last_error = None
        for mode in ("base64", "base36"):
            try:
                raw_bytes = decode_bytes(normalized_str, mode)
                break
            except Exception as exc:
                last_error = exc
        else:
            raise ValueError(f"无法自动识别编码格式: {last_error}")
    else:
        raw_bytes = decode_bytes(normalized_str, decode_mode)

    if decode_mode != "base36" and enhanced_mode:
        raw_bytes = zlib.decompress(RSCodec(n_sym).decode(raw_bytes)[0])

    try:
        return raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return raw_bytes.decode("utf-8", errors="replace")
