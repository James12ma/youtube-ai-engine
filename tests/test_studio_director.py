"""Director control flow with a scripted fake LLM: repair loop, fail-closed, event coverage."""
import copy
import json
import unittest
from pathlib import Path

from studio.assets import gpu_request
from studio.director import DirectorFailed, direct
from studio.spec import FilmSpec, tokenize

GATE_A = json.loads((Path(__file__).resolve().parents[1] / "studio/films/gate_a/spec.json").read_text())
ANALYSIS = {"entities": {}, "events": [{"word": 30, "action": "presses Submit"}, {"word": 43, "action": "arrives"}]}


class Scripted:
    def __init__(self, *answers):
        self.answers = [json.dumps(a) for a in answers]
        self.prompts = []

    def __call__(self, system, user):
        self.prompts.append(user)
        return self.answers.pop(0)


class DirectorTests(unittest.TestCase):
    def test_valid_plan_passes_first_time(self):
        llm = Scripted(ANALYSIS, GATE_A)
        spec = direct(GATE_A["narration"]["text"], llm=llm, film_id="t", log=lambda m: None)
        self.assertEqual(len(spec.shots), len(GATE_A["shots"]))
        self.assertIn("8:she", llm.prompts[0])  # words are numbered for the model

    def test_repair_loop_feeds_back_problems(self):
        broken = copy.deepcopy(GATE_A)
        broken["shots"][4]["beats"][0]["at_word"] = 50
        llm = Scripted(ANALYSIS, broken, GATE_A)
        direct(GATE_A["narration"]["text"], llm=llm, film_id="t", log=lambda m: None)
        self.assertIn("outside its words", llm.prompts[-1])

    def test_fails_closed_after_repairs(self):
        broken = copy.deepcopy(GATE_A)
        broken["shots"][0]["technique"] = "character_animation"
        llm = Scripted(ANALYSIS, *[broken] * 5)
        with self.assertRaises(DirectorFailed) as ctx:
            direct(GATE_A["narration"]["text"], llm=llm, film_id="t", log=lambda m: None)
        self.assertTrue(any("not renderable" in p for p in ctx.exception.problems))

    def test_forgotten_events_are_merged_from_the_analysis(self):
        no_beats = copy.deepcopy(GATE_A)
        for s in no_beats["shots"]:
            s["beats"] = []
        analysis = {"entities": {}, "events": [{"word": 43, "action": "arrives at company", "object": "application"}]}
        spec = direct(GATE_A["narration"]["text"], llm=Scripted(analysis, no_beats), film_id="t", log=lambda m: None)
        beat = next(b for s in spec.shots for b in s.beats)
        self.assertEqual((beat.at_word, beat.object), (43, "application"))

    def test_list_shaped_entities_and_assets_are_keyed(self):
        listed = copy.deepcopy(GATE_A)
        listed["entities"] = [{"id": k, **v} for k, v in GATE_A["entities"].items()]
        listed["assets"] = [{"id": k, **v} for k, v in GATE_A["assets"].items()]
        spec = direct(GATE_A["narration"]["text"], llm=Scripted(ANALYSIS, listed), film_id="t", log=lambda m: None)
        self.assertEqual(set(spec.entities), set(GATE_A["entities"]))
        self.assertEqual(set(spec.assets), set(GATE_A["assets"]))

    def test_shotless_stub_never_becomes_the_repair_base(self):
        # Run 39809209470: a 134-char stub ("shots: Field required") outranked a real 20-problem plan.
        stub = {"title": "x"}
        no_names = copy.deepcopy(GATE_A)
        for e in no_names["entities"].values():
            e.pop("name"), e.pop("kind")
        analysis = {**ANALYSIS, "entities": copy.deepcopy(GATE_A["entities"])}
        llm = Scripted(analysis, stub, no_names)
        spec = direct(GATE_A["narration"]["text"], llm=llm, film_id="t", log=lambda m: None)
        self.assertEqual(llm.prompts[2], llm.prompts[1])  # re-planned from the analysis, not a repair of the stub
        self.assertEqual({k: e.kind for k, e in spec.entities.items()},
                         {k: e["kind"] for k, e in GATE_A["entities"].items()})

    def test_filler_words_lose_emphasis(self):
        plan = copy.deepcopy(GATE_A)
        words = tokenize(GATE_A["narration"]["text"])
        k, filler = next((k, i) for k, sh in enumerate(plan["shots"]) for i in range(sh["words"][0], sh["words"][1] + 1)
                         if words[i].lower() in ("the", "to", "a"))
        plan["shots"][k]["text"]["emphasis"] = [filler]
        spec = direct(GATE_A["narration"]["text"], llm=Scripted(ANALYSIS, plan), film_id="t", log=lambda m: None)
        self.assertEqual(spec.shots[k].text.emphasis, [])

    def test_malformed_shots_go_to_repair_not_crash(self):
        bad = copy.deepcopy(GATE_A)
        bad["shots"] = ["not a shot"] + bad["shots"]
        llm = Scripted(ANALYSIS, bad, GATE_A)
        spec = direct(GATE_A["narration"]["text"], llm=llm, film_id="t", log=lambda m: None)
        self.assertEqual(len(spec.shots), len(GATE_A["shots"]))
        self.assertEqual(len(llm.prompts), 3)

    def test_long_shots_are_blocking(self):
        long = copy.deepcopy(GATE_A)
        long["shots"][1]["words"] = [5, 27]
        del long["shots"][2:4]
        with self.assertRaises(DirectorFailed) as ctx:
            direct(GATE_A["narration"]["text"], llm=Scripted(ANALYSIS, *[long] * 5), film_id="t", log=lambda m: None)
        self.assertTrue(any("split it" in p for p in ctx.exception.problems))

    def test_degenerate_repair_never_replaces_a_better_plan(self):
        almost = copy.deepcopy(GATE_A)
        almost["shots"][4]["beats"][0]["at_word"] = 50   # one problem
        garbage = {"shots": [{"technique": "title"}]}      # many problems
        llm = Scripted(ANALYSIS, almost, garbage, GATE_A)
        direct(GATE_A["narration"]["text"], llm=llm, film_id="t", log=lambda m: None)
        self.assertIn("outside its words", llm.prompts[-1])  # the repair after garbage still targets the good plan
        self.assertIn('"s05"', llm.prompts[-1])

    def test_merged_beats_never_override_existing_ones(self):
        analysis = {"entities": {}, "events": [{"word": 30, "action": "presses Submit"}]}
        spec = direct(GATE_A["narration"]["text"], llm=Scripted(analysis, GATE_A), film_id="t", log=lambda m: None)
        s05 = next(s for s in spec.shots if s.id == "s05")
        self.assertEqual([b.at_word for b in s05.beats], [30, 31])  # the planner's own beats, nothing duplicated

    def test_gpu_request_orders_stills_before_clips_and_keeps_identity(self):
        raw = copy.deepcopy(GATE_A)
        raw["assets"]["clip_thumbs_typing"] = {"kind": "video", "source_image": "still_thumbs_typing", "seconds": 3.5,
                                               "prompt": "thumbs type on the phone"}
        req = gpu_request(FilmSpec(**raw))
        ids = [t["id"] for t in req["tasks"]]
        self.assertLess(ids.index("still_thumbs_typing"), ids.index("clip_thumbs_typing"))
        maya = next(t for t in req["tasks"] if t["id"] == "still_maya_night")["settings"]
        self.assertIn("curly dark hair", maya["prompt"])
        self.assertEqual(maya["seed"], 1997)
        clip = next(t for t in req["tasks"] if t["id"] == "clip_thumbs_typing")["settings"]
        self.assertEqual(clip["image_start"], "@still_thumbs_typing")
        self.assertEqual((clip["video_length"] - 1) % 4, 0)


if __name__ == "__main__":
    unittest.main()


class FreeLLMTests(unittest.TestCase):
    def test_retries_busy_providers_and_skips_dead_models(self):
        import io
        import os
        import urllib.error
        from unittest import mock

        from studio import director

        answers = iter([404, 503, 503, 503, 503, "ok"])
        seen = []

        def fake_urlopen(req, timeout=0):
            model = json.loads(req.data)["model"]
            seen.append(model)
            a = next(answers)
            if a == "ok":
                return mock.MagicMock(__enter__=lambda s: io.BytesIO(json.dumps({"choices": [{"message": {"content": "{}"}}]}).encode()),
                                      __exit__=lambda *a: False)
            raise urllib.error.HTTPError(req.full_url, a, "x", {}, io.BytesIO(b"busy"))

        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "k", "GROQ_API_KEY": "k"}, clear=False), \
             mock.patch.object(director.urllib.request, "urlopen", fake_urlopen):
            llm = director.free_llm(sleep=lambda s: None)
            self.assertEqual(llm("s", "u"), "{}")
        self.assertEqual(seen[0], "gemini-3.8-flash")
        self.assertNotIn("gemini-3.8-flash", seen[1:])  # 404 = gone, not retried
