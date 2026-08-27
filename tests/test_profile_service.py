import unittest

from fastapi import HTTPException

from app.services.profile_service import MAX_AVATAR_BYTES, validate_avatar


class ProfileServiceTests(unittest.TestCase):
    def test_accepts_supported_image_signatures(self):
        self.assertEqual(validate_avatar(b"\x89PNG\r\n\x1a\ncontent"), "image/png")
        self.assertEqual(validate_avatar(b"\xff\xd8\xffcontent"), "image/jpeg")
        self.assertEqual(validate_avatar(b"RIFF0000WEBPcontent"), "image/webp")

    def test_rejects_unsupported_content(self):
        with self.assertRaises(HTTPException) as context:
            validate_avatar(b"<svg></svg>")
        self.assertEqual(context.exception.status_code, 415)

    def test_rejects_oversized_images(self):
        with self.assertRaises(HTTPException) as context:
            validate_avatar(b"\x89PNG\r\n\x1a\n" + b"x" * MAX_AVATAR_BYTES)
        self.assertEqual(context.exception.status_code, 413)


if __name__ == "__main__":
    unittest.main()
