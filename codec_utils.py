import base64
import re
import sys
import zlib

from reedsolo import RSCodec

from app_metadata import APP_VERSION

BASE36_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"
BASE36_PATTERN = re.compile(r"^[0-9a-z]+$")
LEGACY_NSYM_CANDIDATES = [10] + [value for value in range(1, 256) if value != 10]
LOWERCASE_PAYLOAD_V1 = 1
LOWERCASE_PAYLOAD_V2 = 2
LOWERCASE_FLAG_ENHANCED = 1
BASE64_PAYLOAD_V2 = b"AT2"
BASE64_FLAG_ENHANCED = 1

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)


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


def build_lowercase_payload(content, enhanced_mode=False, n_sym=10):
    compressed = zlib.compress(content, level=9)
    if enhanced_mode:
        payload = b"".join(
            [
                bytes([LOWERCASE_PAYLOAD_V2, LOWERCASE_FLAG_ENHANCED]),
                int(n_sym).to_bytes(2, byteorder="big"),
                len(content).to_bytes(4, byteorder="big"),
                RSCodec(n_sym).encode(compressed),
            ]
        )
    else:
        payload = bytes([LOWERCASE_PAYLOAD_V1]) + len(content).to_bytes(4, byteorder="big") + compressed
    return bytes_to_base36(payload)


def parse_lowercase_payload(encoded_str):
    payload = base36_to_bytes(encoded_str)
    if len(payload) < 5:
        raise ValueError("base36 数据长度不足")

    version = payload[0]
    if version == LOWERCASE_PAYLOAD_V1:
        raw_length = int.from_bytes(payload[1:5], byteorder="big")
        compressed = payload[5:]
    elif version == LOWERCASE_PAYLOAD_V2:
        if len(payload) < 8:
            raise ValueError("base36 增强数据长度不足")
        flags = payload[1]
        n_sym = int.from_bytes(payload[2:4], byteorder="big")
        raw_length = int.from_bytes(payload[4:8], byteorder="big")
        compressed = payload[8:]
        if flags & LOWERCASE_FLAG_ENHANCED:
            try:
                compressed = RSCodec(n_sym).decode(compressed)[0]
            except Exception as exc:
                raise ValueError("base36 增强模式解码失败，请检查编码内容是否完整") from exc
    else:
        raise ValueError("base36 数据头非法")

    try:
        decoded = zlib.decompress(compressed)
    except zlib.error as exc:
        raise ValueError("base36 压缩数据损坏，无法解压") from exc

    if len(decoded) != raw_length:
        raise ValueError("base36 数据长度校验失败")
    return decoded


def build_base64_payload(content, enhanced_mode=False, n_sym=10):
    compressed = zlib.compress(content, level=9)
    if enhanced_mode:
        payload = b"".join(
            [
                BASE64_PAYLOAD_V2,
                bytes([BASE64_FLAG_ENHANCED]),
                int(n_sym).to_bytes(2, byteorder="big"),
                len(content).to_bytes(4, byteorder="big"),
                RSCodec(n_sym).encode(compressed),
            ]
        )
    else:
        payload = b"".join(
            [
                BASE64_PAYLOAD_V2,
                bytes([0]),
                (0).to_bytes(2, byteorder="big"),
                len(content).to_bytes(4, byteorder="big"),
                compressed,
            ]
        )
    return base64.b64encode(payload).decode("utf-8")


def decode_plain_text_bytes(raw_bytes):
    try:
        return raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("解码后的内容不是有效的 UTF-8 文本，数据可能已损坏") from exc


def decode_legacy_enhanced_bytes(raw_bytes, n_sym):
    try:
        compressed = RSCodec(n_sym).decode(raw_bytes)[0]
        decoded = zlib.decompress(compressed)
    except Exception as exc:
        raise ValueError("增强模式解码失败，请检查纠错字符数和编码内容是否完整") from exc
    return decode_plain_text_bytes(decoded)


def decode_wrapped_base64_payload(raw_bytes):
    if len(raw_bytes) < 10 or not raw_bytes.startswith(BASE64_PAYLOAD_V2):
        raise ValueError("不是带元数据的 base64 负载")

    flags = raw_bytes[3]
    n_sym = int.from_bytes(raw_bytes[4:6], byteorder="big")
    raw_length = int.from_bytes(raw_bytes[6:10], byteorder="big")
    payload = raw_bytes[10:]

    if flags & BASE64_FLAG_ENHANCED:
        try:
            payload = RSCodec(n_sym).decode(payload)[0]
        except Exception as exc:
            raise ValueError("增强模式解码失败，请检查编码内容是否完整") from exc

    try:
        decoded = zlib.decompress(payload)
    except zlib.error as exc:
        raise ValueError("增强模式压缩数据损坏，无法解压") from exc

    if len(decoded) != raw_length:
        raise ValueError("增强模式数据长度校验失败")
    return decode_plain_text_bytes(decoded)


def auto_decode_base64_payload(raw_bytes):
    wrapped_errors = []
    if raw_bytes.startswith(BASE64_PAYLOAD_V2):
        try:
            return decode_wrapped_base64_payload(raw_bytes)
        except ValueError as exc:
            wrapped_errors.append(exc)

    try:
        return decode_plain_text_bytes(raw_bytes)
    except ValueError as plain_error:
        legacy_errors = []
        for candidate in LEGACY_NSYM_CANDIDATES:
            try:
                return decode_legacy_enhanced_bytes(raw_bytes, candidate)
            except ValueError as exc:
                legacy_errors.append(exc)

        if wrapped_errors:
            raise wrapped_errors[-1]
        if legacy_errors:
            raise legacy_errors[-1]
        raise plain_error


def encode_payload(content, lowercase_mode=False, enhanced_mode=False, n_sym=10):
    if lowercase_mode:
        return build_lowercase_payload(content, enhanced_mode=enhanced_mode, n_sym=n_sym)

    return build_base64_payload(content, enhanced_mode=enhanced_mode, n_sym=n_sym)


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

    compact_str = "".join(normalized_str.split())

    if decode_mode == "auto":
        last_error = None
        auto_modes = ("base36", "base64") if BASE36_PATTERN.fullmatch(compact_str) else ("base64", "base36")
        for mode in auto_modes:
            try:
                if mode == "base36":
                    return decode_plain_text_bytes(decode_bytes(compact_str, mode))
                raw_bytes = decode_bytes(compact_str, mode)
                return auto_decode_base64_payload(raw_bytes)
            except Exception as exc:
                last_error = exc
        else:
            raise ValueError(f"无法自动识别编码格式: {last_error}")
        raise ValueError("无法自动识别编码格式")

    if decode_mode == "base36":
        return decode_plain_text_bytes(decode_bytes(compact_str, decode_mode))

    raw_bytes = decode_bytes(compact_str, decode_mode)
    if enhanced_mode:
        try:
            return decode_wrapped_base64_payload(raw_bytes)
        except ValueError:
            return decode_legacy_enhanced_bytes(raw_bytes, n_sym)
    try:
        return decode_wrapped_base64_payload(raw_bytes)
    except ValueError:
        return decode_plain_text_bytes(raw_bytes)
