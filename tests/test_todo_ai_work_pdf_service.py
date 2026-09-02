import unittest

from app.services.todo_ai_work_pdf_service import build_todo_work_pdf


class TodoAIWorkPdfServiceTests(unittest.TestCase):
    def test_generates_unicode_pdf_with_optional_signature_area(self):
        pdf = build_todo_work_pdf(
            "Kündigung der Mitgliedschaft",
            "Sehr geehrte Damen und Herren,\n\nhiermit kündige ich meine Mitgliedschaft.\n\nMit freundlichen Grüßen",
            include_signature=True,
        )

        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 1000)


if __name__ == "__main__":
    unittest.main()
