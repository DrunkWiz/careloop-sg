"""The deploy: one service serves the API under /api and the built web app (web/dist) at every other path.

    cd web && VITE_API_URL=/api npm run build && cd ..
    CARELOOP_SEED=demo CARELOOP_DEMO_DAYS=11 uvicorn backend.api.serve:site --host 0.0.0.0 --port 8000

One origin, so no CORS and one HTTPS address for phones (installing the app and hold-to-talk need HTTPS).
The API sits under /api because some page paths (/care/family/health) look like API paths
(/care/family/{contact}). CARELOOP_DEMO_DAYS plays the demo forward on a fresh store, so a judge opening
the link lands on the video's day (24 Oct) instead of its start. Owner: Nathan.
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import app as api_module
from . import demo

DIST = Path(os.environ.get("CARELOOP_WEB_DIST", Path(__file__).resolve().parents[2] / "web" / "dist"))

days = int(os.environ.get("CARELOOP_DEMO_DAYS", "0") or 0)
if days and os.environ.get("CARELOOP_SEED") == "demo" and demo.today(api_module.store) == demo.DEMO_TODAY:
    demo.advance(api_module.store, days)

site = FastAPI(title="CareLoop SG (site)", docs_url=None, redoc_url=None, openapi_url=None)
site.mount("/api", api_module.app)

if (DIST / "assets").is_dir():
    site.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")  # hashed names: cached forever


@site.get("/healthz", include_in_schema=False)
def healthz():
    return {"ok": True, "today": demo.today(api_module.store).isoformat()}


@site.get("/{path:path}", include_in_schema=False)
def page(path: str):
    """A real file (sw.js, manifests, icons) if there is one, otherwise the app, which routes itself."""
    if not (DIST / "index.html").is_file():
        return JSONResponse({"detail": "web app not built: run npm run build in web/"}, status_code=503)
    f = (DIST / path).resolve()
    if path and f.is_file() and DIST.resolve() in f.parents:
        # The service worker and manifests must not be cached, or a new build never reaches phones.
        fresh = f.name == "sw.js" or f.suffix == ".webmanifest"
        return FileResponse(f, headers={"Cache-Control": "no-cache"} if fresh else None)
    return FileResponse(DIST / "index.html", headers={"Cache-Control": "no-cache"})
