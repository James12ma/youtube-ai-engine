"""Director control flow with a scripted fake LLM: repair loop, fail-closed, event coverage."""
import copy
import json
import unittest
from pathlib import Path

from studio.assets import gpu_request
from studio.director import DirectorFailed, direct
from studio.spec import FilmSpec

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
        llm = Scripted(ANALYSIS, broken, broken, broken)
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

    def test_long_shots_are_blocking(self):
        long = copy.deepcopy(GATE_A)
        long["shots"][1]["words"] = [5, 27]
        del long["shots"][2:4]
        with self.assertRaises(DirectorFailed) as ctx:
            direct(GATE_A["narration"]["text"], llm=Scripted(ANALYSIS, long, long, long), film_id="t", log=lambda m: None)
        self.assertTrue(any("split it" in p for p in ctx.exception.problems))

    def test_merged_beats_never_override_existing_ones(self):
        analysis = {"entities": {}, "events": [{"word": 30, "action": "presses Submit"}]}
        spec = direct(GATE_A["narration"]["text"], llm=Scripted(analysis, GATE_A), film_id="t", log=lambda m: None)
        s05 = next(s for s in spec.shots if s.id == "s05")
        self.assertEqual([b.at_word for b in s05.beats], [30, 31])  # the planner's own beats, nothing duplicated

    def test_gpu_request_orders_stills_before_clips_and_keeps_identity(self):
        req = gpu_request(FilmSpec(**GATE_A))
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
