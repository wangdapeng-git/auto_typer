import base64
import unittest
import zlib

from reedsolo import RSCodec

from codec_utils import decode_payload, encode_payload


class CodecUtilsTests(unittest.TestCase):
    def test_auto_mode_decodes_compressed_default_payload(self):
        text = ("plain base64 payload " + "中文内容 ") * 2000
        encoded = encode_payload(text.encode("utf-8"))

        decoded = decode_payload(encoded, decode_mode="auto")

        self.assertEqual(decoded, text)

    def test_default_mode_is_compressed_like_lowercase_mode(self):
        text = ("compression parity " + "中文内容 ") * 3000
        encoded_default = encode_payload(text.encode("utf-8"))
        encoded_lowercase = encode_payload(text.encode("utf-8"), lowercase_mode=True)
        legacy_plain = base64.b64encode(text.encode("utf-8")).decode("utf-8")

        self.assertLess(len(encoded_default), len(legacy_plain))
        self.assertLess(len(encoded_default), len(encoded_lowercase) * 2)

    def test_auto_mode_does_not_misclassify_lowercase_base64_text(self):
        text = "jga"
        encoded = base64.b64encode(text.encode("utf-8")).decode("utf-8").rstrip("=")

        decoded = decode_payload(encoded, decode_mode="auto")

        self.assertEqual(encoded, "amdh")
        self.assertEqual(decoded, text)

    def test_auto_mode_decodes_new_enhanced_base64_payload(self):
        text = ("长文本 mixed content 1234567890 ABC xyz\n" * 1500).strip()
        encoded = encode_payload(text.encode("utf-8"), enhanced_mode=True, n_sym=10)

        decoded = decode_payload(encoded, decode_mode="auto")

        self.assertEqual(decoded, text)

    def test_auto_mode_decodes_legacy_enhanced_base64_payload(self):
        text = ("legacy enhanced " + "中文 ") * 2500
        legacy_payload = RSCodec(10).encode(zlib.compress(text.encode("utf-8")))
        encoded = base64.b64encode(legacy_payload).decode("utf-8")

        decoded = decode_payload(encoded, decode_mode="auto")

        self.assertEqual(decoded, text)

    def test_auto_mode_decodes_legacy_plain_base64_payload(self):
        text = ("legacy plain " + "中文 ") * 1600
        encoded = base64.b64encode(text.encode("utf-8")).decode("utf-8")

        decoded = decode_payload(encoded, decode_mode="auto")

        self.assertEqual(decoded, text)

    def test_auto_mode_prefers_lowercase_mode_for_long_lowercase_payload(self):
        text = "中文测试" * 8000
        encoded = encode_payload(text.encode("utf-8"), lowercase_mode=True)

        decoded = decode_payload(encoded, decode_mode="auto")

        self.assertEqual(decoded, text)

    def test_auto_mode_decodes_lowercase_enhanced_payload(self):
        text = ("debug example " + "中文内容 ") * 4000
        encoded = encode_payload(text.encode("utf-8"), lowercase_mode=True, enhanced_mode=True, n_sym=10)

        decoded = decode_payload(encoded, decode_mode="auto")

        self.assertEqual(decoded, text)

    def test_auto_mode_accepts_pasted_whitespace(self):
        text = ("whitespace test " + "中文 ") * 500
        encoded = encode_payload(text.encode("utf-8"), enhanced_mode=True, n_sym=10)
        wrapped = "\n".join(encoded[index:index + 76] for index in range(0, len(encoded), 76))

        decoded = decode_payload(wrapped, decode_mode="auto")

        self.assertEqual(decoded, text)

    def test_explicit_base64_mode_still_supports_legacy_enhanced_payload(self):
        text = ("explicit base64 " + "中文 ") * 1200
        legacy_payload = RSCodec(10).encode(zlib.compress(text.encode("utf-8")))
        encoded = base64.b64encode(legacy_payload).decode("utf-8")

        decoded = decode_payload(encoded, decode_mode="base64", enhanced_mode=True, n_sym=10)

        self.assertEqual(decoded, text)

    def test_invalid_utf8_payload_raises_clear_error(self):
        encoded = base64.b64encode(b"\xff\xfe\xfd").decode("utf-8")

        with self.assertRaisesRegex(ValueError, "UTF-8"):
            decode_payload(encoded, decode_mode="base64")


if __name__ == "__main__":
    unittest.main()
