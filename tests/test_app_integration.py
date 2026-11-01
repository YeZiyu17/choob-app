"""Flask integration checks that do not download or load model weights."""
from io import BytesIO
import sys
import types
from unittest import TestCase
from unittest.mock import Mock, patch

from PIL import Image

import app as backend


def image_bytes(fmt="PNG", size=(32, 32)):
    output = BytesIO()
    Image.new("RGB", size, "orange").save(output, format=fmt)
    return output.getvalue()


class FlaskIntegrationTests(TestCase):
    def setUp(self):
        self.client = backend.app.test_client()

    def test_flask_serves_original_ui_and_status(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Every dish becomes part of", response.data)
        response.close()
        status = self.client.get("/api/status")
        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.get_json()["api"], "running")

    def test_recognize_rejects_missing_empty_and_invalid_uploads(self):
        cases = [
            {},
            {"image": (BytesIO(b""), "empty.png")},
            {"image": (BytesIO(b"not an image"), "broken.png")},
        ]
        for data in cases:
            with self.subTest(data=bool(data)):
                response = self.client.post("/api/recognize", data=data)
                self.assertEqual(response.status_code, 400)
                self.assertIn("error", response.get_json())

    def test_recognize_rejects_request_larger_than_eight_megabytes(self):
        payload = b"x" * (8 * 1024 * 1024 + 1)
        response = self.client.post(
            "/api/recognize",
            data={"image": (BytesIO(payload), "large.jpg")},
        )
        self.assertEqual(response.status_code, 413)
        self.assertIn("8 MB", response.get_json()["error"])

    def test_valid_image_reaches_recognizer_and_returns_prediction(self):
        recognizer = Mock()
        recognizer.predict.return_value = {
            "accepted": True,
            "status": "supported",
            "dish_name": "Pizza",
            "suggested_dish": "Pizza",
        }
        with patch.object(backend, "get_recognizer", return_value=recognizer):
            response = self.client.post(
                "/api/recognize",
                data={"image": (BytesIO(image_bytes()), "photo.png")},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["dish_name"], "Pizza")
        image = recognizer.predict.call_args.args[0]
        self.assertEqual(image.mode, "RGB")

    def test_model_failure_is_reported_as_service_unavailable(self):
        with (patch.object(backend, "get_recognizer", side_effect=OSError("offline")),
              patch.object(backend.app.logger, "disabled", True)):
            response = self.client.post(
                "/api/recognize",
                data={"image": (BytesIO(image_bytes()), "photo.png")},
            )
        self.assertEqual(response.status_code, 503)
        self.assertIn("backend unavailable", response.get_json()["error"].lower())

    def test_clip_uses_cache_first_then_downloads_only_on_cache_miss(self):
        calls = []

        class FakeModel:
            @classmethod
            def from_pretrained(cls, model_id, **kwargs):
                calls.append(("model", model_id, kwargs))
                if kwargs.get("local_files_only"):
                    raise OSError("cache miss")
                return Mock()

        class FakeProcessor:
            @classmethod
            def from_pretrained(cls, model_id, **kwargs):
                calls.append(("processor", model_id, kwargs))
                if kwargs.get("local_files_only"):
                    raise OSError("cache miss")
                return Mock()

        module = types.ModuleType("transformers")
        module.CLIPModel = FakeModel
        module.CLIPProcessor = FakeProcessor
        backend.get_clip.cache_clear()
        try:
            with patch.dict(sys.modules, {"transformers": module}):
                backend.get_clip()
        finally:
            backend.get_clip.cache_clear()
        self.assertEqual(
            [(kind, kwargs.get("local_files_only")) for kind, _, kwargs in calls],
            [("model", True), ("model", None), ("processor", True), ("processor", None)],
        )
