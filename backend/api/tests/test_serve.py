"""The deploy's one service: the API under /api, the web app everywhere else, nothing outside web/dist."""
import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


class Serve(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        dist = Path(cls.tmp.name) / "dist"
        (dist / "assets").mkdir(parents=True)
        (dist / "index.html").write_text("<!doctype html><title>app</title>", encoding="utf-8")
        (dist / "sw.js").write_text("// sw", encoding="utf-8")
        (dist / "assets" / "a.js").write_text("// built", encoding="utf-8")
        (Path(cls.tmp.name) / "secret.txt").write_text("no", encoding="utf-8")
        os.environ["CARELOOP_WEB_DIST"] = str(dist)
        import importlib

        from backend.api import serve

        cls.serve = importlib.reload(serve)
        cls.c = TestClient(cls.serve.site)

    @classmethod
    def tearDownClass(cls):
        os.environ.pop("CARELOOP_WEB_DIST", None)
        cls.tmp.cleanup()

    def test_api_is_under_api(self):
        self.assertEqual(self.c.get("/api/meta").json()["version"], "0.1.0")

    def test_page_paths_get_the_app(self):
        for path in ("/", "/senior?senior=tan", "/care/family/health", "/care/aac/programmes"):
            with self.subTest(path):
                r = self.c.get(path)
                self.assertEqual(r.status_code, 200)
                self.assertIn("<title>app</title>", r.text)

    def test_files_and_caching(self):
        self.assertEqual(self.c.get("/assets/a.js").text, "// built")
        r = self.c.get("/sw.js")
        self.assertEqual(r.text, "// sw")
        self.assertEqual(r.headers.get("cache-control"), "no-cache")

    def test_nothing_outside_the_build(self):
        r = self.c.get("/..%2Fsecret.txt")
        self.assertNotEqual(r.text, "no")


if __name__ == "__main__":
    unittest.main()
