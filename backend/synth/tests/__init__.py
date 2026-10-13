# Tests never hit the network: drop any model or ASR keys before the default chain is built.
import os

for key in ("HUNYUAN_API_KEY", "LLM_FALLBACK_API_KEY", "TENCENTCLOUD_SECRET_ID", "TENCENTCLOUD_SECRET_KEY"):
    os.environ.pop(key, None)
