"""Speech to text for POST /checkin with audio.

Decision (Tue): the senior app transcribes in the browser with the Web Speech API
(free; en-SG and zh-CN in Chrome on Android), and posts TEXT. This server-side path is
for audio uploads only: Tencent Cloud ASR one-sentence recognition (<= 60 s), if
TENCENTCLOUD_SECRET_ID / TENCENTCLOUD_SECRET_KEY are set. Otherwise it raises
NotConfigured and the API should answer 501 so the app falls back to typing.

UNVERIFIED against a live account: try one real clip with real keys before relying on it.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

from .facts import Lang

HOST = "asr.tencentcloudapi.com"
# Engine per language. Override with TENCENT_ASR_ENGINE_EN / _ZH if the account has others.
ENGINES = {"en": "16k_en", "en-SG": "16k_en", "zh": "16k_zh"}


class NotConfigured(Exception):
    pass


class TranscribeError(Exception):
    pass


def transcribe(audio: bytes, lang: Lang, *, fmt: str = "wav", env: dict | None = None) -> str:
    env = os.environ if env is None else env
    sid, skey = env.get("TENCENTCLOUD_SECRET_ID"), env.get("TENCENTCLOUD_SECRET_KEY")
    if not sid or not skey:
        raise NotConfigured("server-side speech-to-text is off; the senior app transcribes in the browser")
    engine = env.get("TENCENT_ASR_ENGINE_ZH" if lang == "zh" else "TENCENT_ASR_ENGINE_EN") or ENGINES[lang]
    payload = json.dumps({
        "EngSerViceType": engine, "SourceType": 1, "VoiceFormat": fmt,
        "Data": base64.b64encode(audio).decode(), "DataLen": len(audio),
    })
    headers = _tc3_headers(sid, skey, "SentenceRecognition", "2019-06-14", payload, env.get("TENCENTCLOUD_REGION", "ap-singapore"))
    req = urllib.request.Request(f"https://{HOST}", data=payload.encode(), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.load(resp)["Response"]
    except (urllib.error.URLError, TimeoutError, KeyError, ValueError) as e:
        raise TranscribeError(str(e)) from e
    if "Error" in data:
        raise TranscribeError(data["Error"].get("Message", "ASR error"))
    return data.get("Result", "")


def _tc3_headers(sid: str, skey: str, action: str, version: str, payload: str, region: str) -> dict:
    """Tencent Cloud API v3 (TC3-HMAC-SHA256) signature."""
    ts = int(time.time())
    date = datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")
    service = HOST.split(".")[0]
    ct = "application/json; charset=utf-8"
    canonical = "\n".join([
        "POST", "/", "", f"content-type:{ct}\nhost:{HOST}\n", "content-type;host",
        hashlib.sha256(payload.encode()).hexdigest(),
    ])
    scope = f"{date}/{service}/tc3_request"
    to_sign = "\n".join(["TC3-HMAC-SHA256", str(ts), scope, hashlib.sha256(canonical.encode()).hexdigest()])

    def h(key: bytes, msg: str) -> bytes:
        return hmac.new(key, msg.encode(), hashlib.sha256).digest()

    k = h(h(h(("TC3" + skey).encode(), date), service), "tc3_request")
    sig = hmac.new(k, to_sign.encode(), hashlib.sha256).hexdigest()
    return {
        "Authorization": f"TC3-HMAC-SHA256 Credential={sid}/{scope}, SignedHeaders=content-type;host, Signature={sig}",
        "Content-Type": ct, "Host": HOST, "X-TC-Action": action, "X-TC-Timestamp": str(ts),
        "X-TC-Version": version, "X-TC-Region": region,
    }
