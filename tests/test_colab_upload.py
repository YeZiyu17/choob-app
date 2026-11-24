"""Exercise the real Colab upload cell without Colab, private data or inference."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
from types import ModuleType
import unittest
from unittest.mock import patch


NOTEBOOK = Path(__file__).resolve().parents[1] / "Choob_Recommendation_Pipeline.ipynb"


class ColabUploadTests(unittest.TestCase):
    def upload_source(self):
        notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
        matches = ["".join(cell.get("source", [])) for cell in notebook["cells"]
                   if cell["cell_type"] == "code"
                   and "uploaded = files.upload()" in "".join(cell.get("source", []))]
        self.assertEqual(len(matches), 1, "The notebook must have one build-input upload step")
        return matches[0]

    def execute_upload(self, uploads, input_directory):
        # Only redirect Colab's fixed input directory; all file-writing logic is
        # executed from the actual notebook cell under test.
        real_path = Path

        def notebook_path(value):
            return input_directory if value == "/content/choob-input" else real_path(value)

        google = ModuleType("google")
        colab = ModuleType("google.colab")
        files = ModuleType("google.colab.files")
        files.upload = lambda: dict(uploads)
        google.colab = colab
        colab.files = files
        source = self.upload_source()
        modules = {"google": google, "google.colab": colab, "google.colab.files": files}
        with patch.dict("sys.modules", modules), patch("pathlib.Path", notebook_path):
            with redirect_stdout(io.StringIO()):
                exec(compile(source, str(NOTEBOOK) + ":upload", "exec"), {})

    def complete_inputs(self):
        return {
            "choob_reviews_sample.csv": b"review_id,text\nfixture,synthetic review\n",
            "choob_restaurants.csv": b"business_id,name\nfixture,Synthetic Restaurant\n",
            "choob_annotations.jsonl": b'{"review_id":"fixture","dishes":[]}\n',
            "annotation_provenance.json": b'{"synthetic_test_fixture":true}\n',
        }

    def test_all_four_build_inputs_survive_upload_and_unrelated_files_are_ignored(self):
        expected = self.complete_inputs()
        uploads = {**expected, "notes.txt": b"not a build input",
                   "other.json": b"{}", "other_annotations.jsonl": b"{}\n",
                   "other_reviews.csv": b"not,an,input\n"}
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "colab-input"
            self.execute_upload(uploads, destination)
            actual = {path.name: path.read_bytes() for path in destination.iterdir()}
            self.assertEqual(actual, expected)

    def test_missing_required_inputs_fail_at_upload_instead_of_later_export(self):
        for missing in self.complete_inputs():
            with self.subTest(missing=missing), tempfile.TemporaryDirectory() as directory:
                uploads = self.complete_inputs()
                del uploads[missing]
                with self.assertRaisesRegex(AssertionError, missing):
                    self.execute_upload(uploads, Path(directory) / "colab-input")


if __name__ == "__main__":
    unittest.main()
