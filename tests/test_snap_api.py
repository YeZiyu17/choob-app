"""Upload and recognition route checks that do not download model weights."""
from io import BytesIO
from pathlib import Path
import gc
import unittest
from unittest.mock import patch
import warnings

from PIL import Image, ImageFilter

import app as backend


ROOT = Path(__file__).resolve().parents[1]


def png_bytes(size=(32, 24)):
    output = BytesIO()
    Image.new("RGB", size, "orange").save(output, format="PNG")
    return output.getvalue()


class SnapRecognitionApiTests(unittest.TestCase):
    def setUp(self):
        self.client = backend.app.test_client()

    def post_image(self, content, filename="meal.png", content_type="image/png"):
        stream = BytesIO(content)
        try:
            response = self.client.post(
                "/api/recognize",
                data={"image": (stream, filename, content_type)},
                content_type="multipart/form-data",
            )
            response.get_data()
            response.close()
            return response
        finally:
            stream.close()

    def test_single_dish_sample_reaches_recognition_as_rgb(self):
        observed = {}

        def recognize(_recognizer, image):
            observed.update(mode=image.mode, size=image.size)
            return {"accepted": True, "dish_name": "Pizza", "dishes": [{"dish_name": "Pizza"}]}

        with patch.object(backend, "get_recognizer", return_value=object()), \
                patch.object(backend, "recognize_meal", side_effect=recognize):
            response = self.post_image((ROOT / "examples/snap/pizza.jpg").read_bytes(), "pizza.jpg", "image/jpeg")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["dishes"], [{"dish_name": "Pizza"}])
        self.assertEqual(observed["mode"], "RGB")
        self.assertGreater(observed["size"][0] * observed["size"][1], 0)

    def test_multiple_dishes_are_returned_together_without_route_rewriting(self):
        result = {
            "accepted": True,
            "recognition_mode": "multi",
            "dishes": [{"dish_name": "Pizza"}, {"dish_name": "Sushi"}],
        }
        with patch.object(backend, "get_recognizer", return_value=object()), \
                patch.object(backend, "recognize_meal", return_value=result):
            response = self.post_image(png_bytes())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), result)

    def test_blurred_or_ambiguous_photo_can_abstain(self):
        with Image.open(ROOT / "examples/snap/sushi.jpg") as source:
            sample = source.convert("RGB").filter(ImageFilter.GaussianBlur(24))
        content = BytesIO()
        sample.save(content, format="JPEG")
        uncertain = {
            "accepted": False,
            "status": "uncertain",
            "dish_name": "Unknown",
            "suggested_dish": "Sushi",
            "dishes": [],
            "needs_user_confirmation": True,
        }
        with patch.object(backend, "get_recognizer", return_value=object()), \
                patch.object(backend, "recognize_meal", return_value=uncertain):
            response = self.post_image(content.getvalue(), "blurred.jpg", "image/jpeg")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.get_json()["accepted"])
        self.assertEqual(response.get_json()["dishes"], [])

    def test_missing_empty_corrupt_and_non_food_files_are_rejected(self):
        self.assertEqual(self.client.post("/api/recognize").status_code, 400)
        self.assertEqual(self.post_image(b"").status_code, 400)
        self.assertEqual(self.post_image(b"not an image", "broken.png").status_code, 400)
        self.assertEqual(self.post_image(b"plain text", "notes.txt", "text/plain").status_code, 400)

    def test_images_over_pixel_and_upload_limits_are_rejected(self):
        self.assertEqual(self.post_image(png_bytes((4001, 4000)), "huge.png").status_code, 400)
        # Werkzeug may spool an over-limit multipart body to a temporary file.
        # Force its cleanup inside the warning scope on older macOS Python builds.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ResourceWarning)
            response = self.post_image(b"x" * (8 * 1024 * 1024 + 1), "oversize.jpg", "image/jpeg")
            gc.collect()
        self.assertEqual(response.status_code, 413)
        self.assertIn("8 MB", response.get_json()["error"])

    def test_recognition_failure_returns_recoverable_service_error(self):
        with patch.object(backend, "get_recognizer", return_value=object()), \
                patch.object(backend, "recognize_meal", side_effect=RuntimeError("offline")), \
                patch.object(backend.app.logger, "exception"):
            response = self.post_image(png_bytes())

        self.assertEqual(response.status_code, 503)
        self.assertIn("Recognition backend unavailable", response.get_json()["error"])


if __name__ == "__main__":
    unittest.main()
