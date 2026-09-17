import importlib.util
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins" / "cell_su7" / "skills" / "cell_su7" / "scripts" / "sync_cell_no_ai.py"
SPEC = importlib.util.spec_from_file_location("sync_cell_no_ai", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def archive_payload():
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("cell_no_ai-main/SKILL.md", "---\nname: cell_no_ai\n---\n")
        archive.writestr("cell_no_ai-main/scripts/worker.py", "print('ok')\n")
        archive.writestr("cell_no_ai-main/README.md", "ignored\n")
    return output.getvalue()


class Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


class SyncCellNoAiTests(unittest.TestCase):
    def test_archive_fallback_when_git_is_unavailable(self):
        payload = archive_payload()
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "cell_no_ai"
            with mock.patch.object(MODULE, "_git_checkout", side_effect=FileNotFoundError), mock.patch.object(
                MODULE.urllib.request, "urlopen", return_value=Response(payload)
            ):
                MODULE.sync(destination)

            self.assertTrue((destination / "SKILL.md").is_file())
            self.assertTrue((destination / "scripts" / "worker.py").is_file())
            self.assertFalse((destination / "README.md").exists())
            metadata = json.loads((destination / ".upstream.json").read_text(encoding="utf-8"))
            self.assertTrue(metadata["revision"].startswith("archive-sha256:"))


if __name__ == "__main__":
    unittest.main()
