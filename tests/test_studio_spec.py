"""The production spec must block the failure modes the owner saw, not paper over them."""
import copy
import json
import unittest
from pathlib import Path

from studio.capabilities import REGISTRY, catalog_for_director
from studio.spec import FilmSpec, SpecError, tokenize, validate

GATE_A = json.loads((Path(__file__).resolve().parents[1] / "studio/films/gate_a/spec.json").read_text())


def problems(mutate):
    raw = copy.deepcopy(GATE_A)
    mutate(raw)
    try:
        validate(FilmSpec(**raw))
    except SpecError as e:
        return e.problems
    return []


class SpecTests(unittest.TestCase):
    def test_gate_a_spec_is_valid(self):
        self.assertEqual(problems(lambda r: None), [])

    def test_every_word_covered_in_order(self):
        def gap(r):
            r["shots"][2]["words"] = [11, 17]
        self.assertTrue(any("expected 10" in p for p in problems(gap)))

    def test_trailing_words_uncovered(self):
        self.assertTrue(any("not covered" in p for p in problems(lambda r: r["shots"].pop())))

    def test_beat_must_happen_inside_its_words(self):
        def late(r):
            r["shots"][4]["beats"][0]["at_word"] = 40
        self.assertTrue(any("outside its words" in p for p in problems(late)))

    def test_object_state_chain_cannot_skip(self):
        def skip(r):  # receiving before sending
            r["shots"][6]["beats"][0]["state_before"] = "draft"
        self.assertTrue(any("expects 'draft'" in p for p in problems(skip)))

    def test_unknown_technique_and_unavailable_capability_block(self):
        def unknown(r):
            r["shots"][0]["technique"] = "pretty_background"
        def unavailable(r):
            r["shots"][0]["technique"] = "character_animation"
        self.assertTrue(any("unknown technique" in p for p in problems(unknown)))
        self.assertTrue(any("not renderable yet" in p for p in problems(unavailable)))

    def test_bad_params_and_wrong_world(self):
        def bad(r):
            r["shots"][0]["params"] = {"image": "x", "colour": "blue"}
        def world(r):
            r["shots"][5]["world"] = "story"  # data_transfer is an explain/map technique
        self.assertTrue(any("bad params" in p for p in problems(bad)))
        self.assertTrue(any("does not render the 'story' world" in p for p in problems(world)))

    def test_capability_gap_blocks_rendering(self):
        self.assertTrue(any("capability gap" in p for p in problems(
            lambda r: r.__setitem__("capability_gaps", ["needs aerial footage of Haiti"]))))

    def test_unknown_entity(self):
        def ghost(r):
            r["shots"][0]["entities"].append("ghost")
        self.assertTrue(any("unknown entity 'ghost'" in p for p in problems(ghost)))

    def test_timing_required_for_render(self):
        spec = FilmSpec(**GATE_A)
        with self.assertRaises(SpecError):
            validate(spec, require_timing=True)
        n = len(spec.tokens)
        spec.narration.word_times = [(i * 0.35, i * 0.35 + 0.3) for i in range(n)]
        self.assertEqual(validate(spec, require_timing=True), [])

    def test_tokenizer_keeps_abbreviations_and_possessives(self):
        self.assertEqual(tokenize("At two a.m., the company's line."), ["At", "two", "a.m", "the", "company's", "line"])

    def test_director_catalog_lists_unavailable_capabilities(self):
        names = {c["technique"]: c["available"] for c in catalog_for_director()}
        self.assertTrue(names["ui_flow"])
        self.assertFalse(names["character_animation"])
        self.assertEqual(set(names), set(REGISTRY))


if __name__ == "__main__":
    unittest.main()
