"""CareLoop SG language layer. Owner: Mingyu.

The engine calls the model ONLY through these two functions:

    understand(text, lang) -> Facts
    write(rung, facts, lang) -> Message

Rules pick the rung. The model only understands and writes words.
"""
from .facts import BP, Activity, Dose, Facts, GuardrailResult, Message, Symptom
from .gateway import Chain, FakeGateway, describe
from .transcribe import transcribe
from .understand import understand
from .write import write

__all__ = [
    "understand", "write", "transcribe", "describe",
    "Facts", "Message", "BP", "Dose", "Symptom", "Activity", "GuardrailResult",
    "Chain", "FakeGateway",
]
