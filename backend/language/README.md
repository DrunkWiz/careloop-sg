# backend/language

The engine calls the model only through two functions. Rules pick the rung; this layer only understands and writes words.

```python
from backend.language import understand, write

facts = understand("I'm fine lah, BP 186/112 this morning")   # -> Facts
msg = write("R", facts, "en-SG", to="senior", context={"contact": "Wei Ling"})  # -> Message
```

Owner: Mingyu. Standard library only; Python 3.10+.

## understand(text, lang=None) -> Facts

- Rules always run first, for English, Singlish and Mandarin on every check-in (seniors code-switch). They extract BP, pulse, doses taken or missed, medicine running out, symptoms (5 red flags plus 7 others), activities and mood.
- Every BP carries a `confidence`. `needs_confirmation` is true below 0.8 or when the reading is implausible. The senior app then asks the senior to confirm the number. The layer never guesses a reading and never "fixes" a swapped one; the trust check is the engine's job.
- The model, when one answers, may only add meaning: a symptom said in a roundabout way, the mood, an English gloss. It cannot remove a rule finding. It cannot introduce a number: a model BP is kept only if both numbers appear in the text, and then at confidence 0.5.
- `lang` is `en`, `en-SG` (Singlish) or `zh`, and is detected if not given.

Shape: [facts.example.json](facts.example.json). It's proposed for `CheckIn.extracted_facts` in `contracts/`.

## write(rung, facts, lang, *, to="senior", context=None) -> Message

- The model drafts in the senior's language and tone, inside the rung the engine chose. It's given the rung's fixed template and told to keep everything it says: it changes the wording, not the content.
- **Red flags never go to the model.** Their wording is the fixed template the medical student signs off, sent at once: what to do must not be reworded each time, and an urgent message must not wait on a model call.
- The guardrail checks every draft. If it fails, or no model answers, the fixed template for that rung goes out (English and Mandarin; Singlish speakers get English).
- `context` fills template slots and informs the guardrail: `name`, `contact`, `place` (rung 2), `summary`, `psi` / `haze`.
- Rung 0 returns empty text. So does rung 1, 2 or 3 to an audience that isn't messaged at that rung.

Shape: [message.example.json](message.example.json).

## Guardrail (`guardrail.py`)

It rejects a draft that:

| Rule | Example it stops |
| --- | --- |
| `diagnosis` | "Sounds like a stroke" / 你可能是中风 |
| `dose_change` | "Take an extra pill tonight" / 多吃一粒 |
| `stop_medicine` | "No need to take medicine today" / 停药 |
| `calm_on_red_flag` | "Don't worry, just rest" on a red flag; at rung R, no call to act now |
| `haze_go_out` | "Wear a mask and go out" when PSI > 100 |
| `leads_with_number` | a senior message that opens with "186/112…" |
| `invented_number` | any number the senior didn't say and the engine didn't give (995 and 5 are always allowed) |

The red-flag templates are **PLACEHOLDER** until the medical student signs off (Thu).

## Model chain (`gateway.py`)

1. Tencent Hunyuan via its OpenAI-compatible endpoint: `HUNYUAN_API_KEY` (optional `HUNYUAN_MODEL`, default `hunyuan-turbos-latest`; `HUNYUAN_BASE_URL`).
2. Any OpenAI-compatible fallback: `LLM_FALLBACK_BASE_URL`, `LLM_FALLBACK_API_KEY`, `LLM_FALLBACK_MODEL` (optional `LLM_FALLBACK_NAME`). The hosted demo uses Gemini here (`gemini-3.8-flash` via Google's OpenAI-compatible endpoint) until a Hunyuan key is set.
   When every model fails, the server logs why (the provider's error, never the key) before falling back.
3. No model: rules and templates. Always there, so the demo survives a dead API.

`describe()` returns the chain for `GET /meta`.

## Speech to text

Decision: the senior app transcribes **in the browser** with the Web Speech API (`en-SG`, `zh-CN`; free in Chrome) and posts text to `POST /checkin`.

For audio uploads, `transcribe(audio, lang)` calls Tencent Cloud ASR when `TENCENTCLOUD_SECRET_ID` / `TENCENTCLOUD_SECRET_KEY` are set. It hasn't been tried against a live account yet. Without keys it raises `NotConfigured`, and the API should answer 501 so the app falls back to typing.

Translation needs no separate API: the model's `english` gloss inside `understand()` covers it.

## Tests

Offline, no key, no network (`tests/__init__.py` drops any keys). `FakeGateway` scripts model replies.

```
python -m unittest discover -s backend/language/tests -t .
```
