import unittest

from fastapi import HTTPException

from app.services.branding_service import MAX_LOGO_BYTES, validate_logo, validate_signature


class BrandingServiceTests(unittest.TestCase):
    def test_accepts_supported_logo_formats(self):
        self.assertEqual(validate_logo(b"\x89PNG\r\n\x1a\ncontent"), "image/png")
        self.assertEqual(validate_logo(b"\xff\xd8\xffcontent"), "image/jpeg")
        self.assertEqual(validate_logo(b"RIFF0000WEBPcontent"), "image/webp")

    def test_rejects_svg_logo(self):
        with self.assertRaises(HTTPException) as raised:
            validate_logo(b"<svg></svg>")
        self.assertEqual(raised.exception.status_code, 415)

    def test_rejects_oversized_logo(self):
        with self.assertRaises(HTTPException) as raised:
            validate_logo(b"\x89PNG\r\n\x1a\n" + b"x" * MAX_LOGO_BYTES)
        self.assertEqual(raised.exception.status_code, 413)

    def test_accepts_png_signature(self):
        self.assertEqual(validate_signature(b"\x89PNG\r\n\x1a\ncontent"), "image/png")


if __name__ == "__main__":
    unittest.main()
