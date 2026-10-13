"""Guardrail: one test per rejection rule, each with English, Singlish and Mandarin cases.
Plus: every template passes, and write() falls back to the template when a draft fails."""
import unittest

from backend.language import understand, write
from backend.language.facts import Facts
from backend.language.gateway import Chain, FakeGateway
from backend.language.guardrail import check
from backend.language.templates import T

NO_MODEL = Chain([])
CALM = Facts(lang="en")
RED = understand("chest pain since morning", gateway=NO_MODEL)
HIGH = understand("BP 186/112", gateway=NO_MODEL)


def reasons(text, rung="1", to="senior", facts=CALM, context=None):
    return check(text, rung=rung, to=to, facts=facts, context=context).reasons


class Rules(unittest.TestCase):
    def assertRejects(self, rule, texts, **kw):
        for t in texts:
            self.assertIn(rule, reasons(t, **kw), t)

    def test_diagnosis(self):
        self.assertRejects("diagnosis", [
            "You might have hypertension, please see a doctor.",
            "Sounds like a stroke lah, go and check.",
            "This could be angina.",
            "你可能是中风了。",
            "你得了高血压。",
        ])

    def test_dose_change(self):
        self.assertRejects("dose_change", [
            "Maybe take an extra pill tonight.",
            "Try to reduce your amlodipine dose.",
            "How many tablets did you eat today?",
            "Take another tablet lah, then rest.",
            "今晚多吃一粒药。",
            "您吃几粒？",
        ])

    def test_stop_medicine(self):
        self.assertRejects("stop_medicine", [
            "You can stop taking your pills if you feel better.",
            "No need to take medicine today lah.",
            "Skip your medicine tonight.",
            "今天可以停药。",
            "不用吃药了。",
        ])

    def test_calm_on_red_flag(self):
        self.assertRejects("calm_on_red_flag", [
            "Don't worry, just rest and see how you feel.",
            "Should be fine lah, drink some water.",
            "Let's talk about it at your next appointment.",
            "不用担心，休息一下就好。",
            "没事的，明天再看。",
        ], rung="R", facts=RED)

    def test_red_flag_needs_a_call_to_act(self):
        self.assertIn("calm_on_red_flag", reasons("Please take care of yourself.", rung="R", facts=RED))

    def test_red_flag_facts_guard_any_rung(self):
        # Even if a draft is written at a lower rung, red-flag facts forbid calm words.
        self.assertIn("calm_on_red_flag", reasons("Don't worry about it.", rung="1", facts=RED))

    def test_haze_go_out(self):
        self.assertRejects("haze_go_out", [
            "Wear a mask and go out for a walk.",
            "Nice day for the park connector!",
            "Go outside lah, wear mask can already.",
            "戴口罩出去散步吧。",
            "去公园走走。",
        ], context={"psi": 140})

    def test_haze_stay_in_is_fine(self):
        self.assertNotIn("haze_go_out", reasons("Better not go outside today. The library has a talk at 3pm.", context={"psi": 140, "time": "3pm"}))
        self.assertNotIn("haze_go_out", reasons("今天不要出门，在家休息。", context={"psi": 140}))

    def test_no_haze_outdoors_fine(self):
        self.assertNotIn("haze_go_out", reasons("How about a walk in the park?", context={"psi": 40}))

    def test_leads_with_number(self):
        self.assertIn("leads_with_number", reasons("186/112 is high.", facts=HIGH))
        self.assertNotIn("leads_with_number", reasons("BP 186/112.", to="family", rung="3", facts=HIGH))

    def test_invented_number(self):
        self.assertIn("invented_number", reasons("Your reading of 150/95 is a bit high.", facts=HIGH))
        self.assertIn("invented_number", reasons("血压一百五十，有点高。", facts=HIGH))
        self.assertNotIn("invented_number", reasons("Your reading of 186/112 needs attention now, call 995.", rung="R", facts=HIGH))

    def test_clean_message_passes(self):
        self.assertEqual(reasons("Good morning! How are you feeling today?"), [])
        self.assertEqual(reasons("早上好！今天身体怎么样？"), [])


class Templates(unittest.TestCase):
    def test_every_template_passes(self):
        ctx = {"name": "Mdm Tan", "contact": "Wei Ling", "place": "Kebun Baru AAC: karaoke", "psi": 140}
        for facts in (CALM, RED, HIGH):
            for (rung, aud, lang) in T:
                to = aud.split(":")[0]
                msg = write(rung, facts, "zh" if lang == "zh" else "en", to=to, context=ctx, gateway=NO_MODEL)
                if not msg.text:
                    continue
                self.assertTrue(msg.guardrail.passed, f"{rung}/{aud}/{lang}: {msg.guardrail.reasons}: {msg.text}")

    def test_red_flag_senior_symptom_says_995(self):
        for lang in ("en", "zh"):
            m = write("R", RED, lang, to="senior", gateway=NO_MODEL)
            self.assertIn("995", m.text)


class WriteFallsBack(unittest.TestCase):
    def draft(self, text):
        return FakeGateway().reply("Rung:", text)

    def test_bad_draft_replaced_by_template(self):
        m = write("R", RED, "en", to="senior", gateway=self.draft("Don't worry lah, just rest."))
        self.assertTrue(m.from_template)
        self.assertIn("995", m.text)
        self.assertIn("draft:calm_on_red_flag", m.guardrail.reasons)

    def test_bad_mandarin_draft_replaced(self):
        m = write("1", CALM, "zh", gateway=self.draft("今晚多吃一粒药。"))
        self.assertTrue(m.from_template)
        self.assertIn("draft:dose_change", m.guardrail.reasons)

    def test_good_draft_kept(self):
        m = write("1", CALM, "en-SG", gateway=self.draft("Morning! Sleep ok or not? When free, can measure your BP?"))
        self.assertFalse(m.from_template)
        self.assertEqual(m.model, "fake")
        self.assertTrue(m.guardrail.passed)

    def test_model_down_uses_template(self):
        m = write("1", CALM, "en", gateway=FakeGateway())
        self.assertTrue(m.from_template)
        self.assertTrue(m.text)

    def test_rung_zero_says_nothing(self):
        self.assertEqual(write("0", CALM, "en", gateway=self.draft("hello")).text, "")

    def test_prompt_never_asks_model_for_rung(self):
        fake = self.draft("Morning! How are you?")
        write("1", CALM, "en", gateway=fake)
        system, user = fake.calls[0]
        self.assertIn("Rung: 1", user)
        self.assertIn("already decided", system)


if __name__ == "__main__":
    unittest.main()
