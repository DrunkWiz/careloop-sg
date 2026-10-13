"""Facts and Message: what the language layer hands the engine, and what it hands back.

Facts mirror CheckIn.extracted_facts in contracts/. Message mirrors the Message object.
Until Vibu freezes contracts/ (Tue 23:00) these are the language layer's proposal;
facts.example.json is the example to copy into contracts/.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal, Optional

Lang = Literal["en", "en-SG", "zh"]
Rung = Literal["0", "1", "2", "3", "4", "R"]
Audience = Literal["senior", "family", "aac"]

# Below this, the senior app asks the senior to confirm the number. We never guess a reading.
CONFIRM_BELOW = 0.8

RED_FLAG_SYMPTOMS = ("chest_pain", "face_droop", "slurred_speech", "one_sided_weakness", "fainting")
SYMPTOM_CODES = RED_FLAG_SYMPTOMS + (
    "headache", "dizziness", "breathless", "palpitations", "swelling", "tired", "unwell",
)


@dataclass
class BP:
    systolic: int
    diastolic: int
    pulse: Optional[int] = None
    confidence: float = 1.0
    span: str = ""  # the exact words the numbers came from
    plausible: bool = True

    @property
    def needs_confirmation(self) -> bool:
        return self.confidence < CONFIRM_BELOW or not self.plausible


@dataclass
class Dose:
    taken: bool
    medicine: Optional[str] = None  # None = "my pills", unspecified
    span: str = ""


@dataclass
class Symptom:
    code: str  # one of SYMPTOM_CODES
    words: str  # the senior's own words, kept for the GP brief
    red_flag: bool = False


@dataclass
class Activity:
    kind: Literal["social", "exercise", "outing", "home"]
    words: str
    social_contact: bool = False


@dataclass
class Facts:
    lang: Lang
    bp: list[BP] = field(default_factory=list)
    pulse: Optional[int] = None  # a pulse said on its own, without a BP
    doses: list[Dose] = field(default_factory=list)
    running_out: list[str] = field(default_factory=list)  # medicine names; "unspecified" if not named
    symptoms: list[Symptom] = field(default_factory=list)
    activities: list[Activity] = field(default_factory=list)
    mood: Optional[Literal["good", "ok", "low"]] = None
    english: str = ""  # the meaning in English, for the GP brief and the family; never the numbers' source
    source: str = "rules"  # "rules" or "rules+model:<name>"

    @property
    def red_flag(self) -> bool:
        return any(s.red_flag for s in self.symptoms)

    @property
    def feeling_unwell(self) -> bool:
        return bool(self.symptoms)

    @property
    def social_contact(self) -> bool:
        return any(a.social_contact for a in self.activities)

    @property
    def needs_confirmation(self) -> list[BP]:
        return [b for b in self.bp if b.needs_confirmation]

    def numbers(self) -> set[int]:
        """Every number the senior actually said. write() may repeat these and no others."""
        out: set[int] = set()
        for b in self.bp:
            out |= {b.systolic, b.diastolic}
            if b.pulse is not None:
                out.add(b.pulse)
        if self.pulse is not None:
            out.add(self.pulse)
        return out

    def to_dict(self) -> dict:
        d = asdict(self)
        d["red_flag"] = self.red_flag
        d["feeling_unwell"] = self.feeling_unwell
        d["social_contact"] = self.social_contact
        for b, raw in zip(self.bp, d["bp"]):
            raw["needs_confirmation"] = b.needs_confirmation
        return d


@dataclass
class GuardrailResult:
    passed: bool
    reasons: list[str] = field(default_factory=list)


@dataclass
class Message:
    to: Audience
    rung: Rung
    language: Lang
    text: str
    from_template: bool
    guardrail: GuardrailResult
    model: Optional[str] = None  # which rung of the model chain wrote it, if any

    def to_dict(self) -> dict:
        return asdict(self)
