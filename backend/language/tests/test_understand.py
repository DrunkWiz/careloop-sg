"""understand(): English, Singlish, Mandarin and code-switching. Offline: no model, or the fake."""
import json
import unittest

from backend.language import understand
from backend.language.gateway import Chain, FakeGateway
from backend.language.numbers import cn_to_int

NO_MODEL = Chain([])


def u(text, lang=None, gateway=NO_MODEL):
    return understand(text, lang, gateway=gateway)


class Numbers(unittest.TestCase):
    def test_mandarin_numerals(self):
        self.assertEqual(cn_to_int("一百四十五"), 145)
        self.assertEqual(cn_to_int("九十"), 90)
        self.assertEqual(cn_to_int("十二"), 12)
        self.assertEqual(cn_to_int("一四五"), 145)
        self.assertEqual(cn_to_int("一百零五"), 105)
        self.assertIsNone(cn_to_int("好"))


class BloodPressure(unittest.TestCase):
    def bp(self, text, lang=None):
        f = u(text, lang)
        self.assertEqual(len(f.bp), 1, f"{text!r} -> {f.bp}")
        return f.bp[0]

    def test_english_forms(self):
        for text in ["BP 145/90", "my blood pressure was 145 over 90", "145 by 90 this morning", "systolic 145 diastolic 90", "top 145 bottom 90"]:
            b = self.bp(text)
            self.assertEqual((b.systolic, b.diastolic), (145, 90), text)

    def test_pulse_with_reading(self):
        b = self.bp("145/90 pulse 72")
        self.assertEqual(b.pulse, 72)

    def test_mandarin_forms(self):
        for text in ["今天血压145/90", "高压145低压90", "血压一百四十五除以九十", "上面一百四十五下面九十"]:
            b = self.bp(text, "zh")
            self.assertEqual((b.systolic, b.diastolic), (145, 90), text)

    def test_singlish_red_flag_reading(self):
        b = self.bp("I'm fine lah, BP 186/112 this morning")
        self.assertEqual((b.systolic, b.diastolic), (186, 112))
        self.assertFalse(b.needs_confirmation)

    def test_bare_numbers_after_bp_are_confirmed(self):
        b = self.bp("BP today 145 90")
        self.assertTrue(b.needs_confirmation)

    def test_swapped_or_impossible_is_flagged_not_fixed(self):
        b = self.bp("BP 90 145")
        self.assertEqual((b.systolic, b.diastolic), (90, 145))  # never rewritten
        self.assertFalse(b.plausible)
        self.assertTrue(b.needs_confirmation)

    def test_dates_are_not_readings(self):
        self.assertEqual(u("went to the polyclinic on 13/10").bp, [])

    def test_no_reading(self):
        self.assertEqual(u("feeling good today").bp, [])


class Symptoms(unittest.TestCase):
    def codes(self, text, lang=None):
        return {s.code for s in u(text, lang).symptoms}

    def test_red_flags_each_language(self):
        cases = {
            "I have chest pain since morning": "chest_pain",
            "heart pain leh": "chest_pain",
            "胸口痛": "chest_pain",
            "my face is drooping on one side": "face_droop",
            "嘴歪了": "face_droop",
            "my speech is slurred": "slurred_speech",
            "说话不清楚": "slurred_speech",
            "left arm suddenly no strength": "one_sided_weakness",
            "右手没力": "one_sided_weakness",
            "almost pengsan just now": "fainting",
            "早上晕倒了": "fainting",
        }
        for text, code in cases.items():
            f = u(text)
            self.assertIn(code, {s.code for s in f.symptoms}, text)
            self.assertTrue(f.red_flag, text)

    def test_negated(self):
        self.assertNotIn("chest_pain", self.codes("no chest pain today"))
        self.assertNotIn("chest_pain", self.codes("don't have any chest pain"))
        self.assertNotIn("chest_pain", self.codes("没有胸口痛"))

    def test_not_negated_by_unrelated_words(self):
        self.assertIn("chest_pain", self.codes("don't know why chest pain since morning"))
        self.assertIn("chest_pain", self.codes("I'm fine lah, just a bit of chest pain"))

    def test_singlish_and_mandarin_non_red(self):
        self.assertEqual(self.codes("a bit giddy"), {"dizziness"})
        self.assertEqual(self.codes("有点头晕"), {"dizziness"})
        self.assertFalse(u("a bit giddy").red_flag)

    def test_chest_tightness_is_not_low_mood(self):
        f = u("胸闷")
        self.assertIn("chest_pain", {s.code for s in f.symptoms})
        self.assertNotEqual(f.mood, "low")

    def test_keeps_own_words(self):
        f = u("almost pengsan just now")
        self.assertEqual(f.symptoms[0].words.lower(), "pengsan")


class DosesAndActivity(unittest.TestCase):
    def test_taken(self):
        for text in ["took my pills", "eat medicine already", "吃了药"]:
            f = u(text)
            self.assertEqual([d.taken for d in f.doses], [True], text)

    def test_missed(self):
        for text in ["forgot to take my amlodipine", "never eat medicine today", "忘记吃药", "还没吃药"]:
            f = u(text)
            self.assertIn(False, [d.taken for d in f.doses], text)
            self.assertNotIn(True, [d.taken for d in f.doses], text)

    def test_medicine_name(self):
        self.assertEqual(u("forgot to take my amlodipine").doses[0].medicine, "amlodipine")

    def test_running_out(self):
        for text in ["medicine almost finish already", "running out of my pills", "药快吃完了"]:
            self.assertTrue(u(text).running_out, text)

    def test_mahjong_is_social_contact(self):
        self.assertTrue(u("play mahjong whole day").social_contact)
        self.assertTrue(u("今天去打麻将").social_contact)

    def test_stayed_home(self):
        self.assertIn("home", {a.kind for a in u("stayed home whole day").activities})


class Language(unittest.TestCase):
    def test_detect(self):
        self.assertEqual(u("I feel good today").lang, "en")
        self.assertEqual(u("can lah, feeling shiok").lang, "en-SG")
        self.assertEqual(u("今天很好").lang, "zh")

    def test_code_switching(self):
        f = u("今天 BP 150 over 95, 有点头晕 lah")
        self.assertEqual((f.bp[0].systolic, f.bp[0].diastolic), (150, 95))
        self.assertIn("dizziness", {s.code for s in f.symptoms})

    def test_given_lang_wins(self):
        self.assertEqual(u("ok", "zh").lang, "zh")


class WithModel(unittest.TestCase):
    def test_model_adds_meaning(self):
        fake = FakeGateway().reply("Check-in", json.dumps({
            "english": "My chest feels like something is pressing on it.",
            "symptoms": [{"code": "chest_pain", "words": "心口像有东西压着"}], "mood": "low",
        }))
        f = u("心口像有东西压着", gateway=fake)
        self.assertTrue(f.red_flag)
        self.assertEqual(f.english, "My chest feels like something is pressing on it.")
        self.assertTrue(f.source.startswith("rules+model:fake"))

    def test_model_cannot_remove_a_red_flag(self):
        fake = FakeGateway().reply("Check-in", json.dumps({"symptoms": [], "mood": "good"}))
        f = u("I'm fine lah, just chest pain a bit", gateway=fake)
        self.assertTrue(f.red_flag)

    def test_model_cannot_invent_numbers(self):
        fake = FakeGateway().reply("Check-in", json.dumps({"bp": [{"systolic": 130, "diastolic": 85}]}))
        self.assertEqual(u("feeling ok today", gateway=fake).bp, [])

    def test_model_number_from_text_needs_confirmation(self):
        fake = FakeGateway().reply("Check-in", json.dumps({"bp": [{"systolic": 145, "diastolic": 90}]}))
        f = u("the machine say 145 then the other one 90", gateway=fake)
        self.assertEqual(len(f.bp), 1)
        self.assertTrue(f.bp[0].needs_confirmation)

    def test_model_garbage_falls_back_to_rules(self):
        fake = FakeGateway().reply("Check-in", "sorry I cannot help")
        f = u("BP 145/90", gateway=fake)
        self.assertEqual(f.source, "rules")
        self.assertEqual(len(f.bp), 1)

    def test_model_down_falls_back_to_rules(self):
        f = u("chest pain", gateway=FakeGateway())  # no scripted reply = error
        self.assertTrue(f.red_flag)
        self.assertEqual(f.source, "rules")

    def test_chain_falls_to_second_rung(self):
        broken = FakeGateway(name="hunyuan")
        backup = FakeGateway(name="backup").reply("Check-in", json.dumps({"mood": "good"}))
        f = u("today ok", gateway=Chain([broken, backup]))
        self.assertEqual(f.source, "rules+model:backup")


if __name__ == "__main__":
    unittest.main()
