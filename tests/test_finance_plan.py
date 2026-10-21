"""Offline finance planner validation. No live providers or rendering."""
import pytest
from pydantic import ValidationError

from orchestrator.finance_planner import (
    ChartPoint, FinancePlan, FinanceScene, plan, to_premium_script,
)


def example(kind="data", **overrides):
    opts = {
        "kind": kind,
        "narration": "Prices sometimes rise faster than income, shrinking what an ordinary household can buy.",
        "on_screen": "Illustrative household price comparison" if kind == "data" else "How purchasing power changes",
        "data": [{"label": "Before", "value": 10}, {"label": "After", "value": 12}] if kind == "data" else [],
        "facts": ["ILLUSTRATIVE: example prices, not measured CPI"] if kind == "data" else [],
        "excerpt": "A hypothetical example document" if kind == "document" else "",
        "source_label": "Illustrative example" if kind == "document" else "",
    }
    opts.update(overrides)
    return FinanceScene(**opts)


def test_data_requires_points():
    with pytest.raises(ValidationError, match="actual numeric"):
        example(data=[])


def test_data_requires_explicit_illustrative_facts():
    with pytest.raises(ValidationError, match="ILLUSTRATIVE"):
        example(facts=["source: https://example.com"])


def test_data_requires_visible_disclosure():
    with pytest.raises(ValidationError, match="labeled visibly"):
        example(on_screen="Historical CPI")


def test_finite_chart_numbers():
    with pytest.raises(ValidationError):
        ChartPoint(label="bad", value=float("nan"))


def test_max_six_numeric_points():
    with pytest.raises(ValidationError):
        example(data=[{"label": str(i), "value": i} for i in range(7)])


def test_document_requires_excerpt():
    with pytest.raises(ValidationError, match="excerpt"):
        example("document", excerpt="")


def test_document_requires_illustrative_attribution():
    with pytest.raises(ValidationError, match="Illustrative example"):
        example("document", source_label="Federal Reserve")


def test_map_requires_geographic_narration():
    with pytest.raises(ValidationError, match="geographic"):
        example("map", narration="Prices are rising at the store.")


def test_map_accepts_geographic_narration():
    assert example("map", narration="Inflation can differ across countries.").kind == "map"


def test_plan_needs_three_kinds():
    with pytest.raises(ValidationError, match="three"):
        FinancePlan(title="Finance explainer", scenes=[example() for _ in range(6)])


def test_plan_max_two_hero():
    scenes = [example("hero") for _ in range(3)] + [example() for _ in range(3)]
    with pytest.raises(ValidationError, match="two hero"):
        FinancePlan(title="Finance explainer", scenes=scenes)


def test_valid_payload_is_json_without_bang_prefix():
    import json
    scenes = [example("hero"), example(), example("document"), example("map",
         narration="Inflation varies around the world."), example(), example()]
    obj = FinancePlan(title="Financial literacy", scenes=scenes)
    payload = to_premium_script(obj)
    assert payload.startswith("{")
    raw = json.loads(payload)
    assert len(raw["scenes"]) == 6
    assert raw["scenes"][1]["kind"] == "data"
    assert raw["scenes"][1]["visual_notes"].startswith("Illustrative")


class FakeRouter:
    def __init__(self, value):
        self.value = value
        self.calls = []

    def execute(self, task_type, input_data, request, schema):
        self.calls.append((task_type, input_data, schema))
        return self.value


def test_planner_rejects_rewritten_owner_narration():
    scenes = [example("hero"), example(), example("document"),
              example("map", narration="Across countries, prices may vary."),
              example(), example()]
    router = FakeRouter(FinancePlan(title="Finance explainer", scenes=scenes))
    with pytest.raises(ValueError, match="changed owner narration"):
        plan("A user's original script about inflation that should not be modified or reordered by a planning model in any way.", router)
    assert router.calls[0][0] == "finance_visual_plan"


def test_planner_rejects_short_owner_script_before_api():
    router = FakeRouter(None)
    with pytest.raises(ValueError, match="20\+ words"):
        plan("Too short", router)
    assert not router.calls


def test_existing_premium_make_plan_accepts_finance_json(tmp_path):
    """Real interface check, without a narrator, model or browser."""
    from tiktok_motion.premium_job import make_plan
    scenes = [
        example("hero"), example(), example("document"),
        example("map", narration="Inflation affects the world in different ways."),
        example(), example()
    ]
    fplan = FinancePlan(title="Finance visual contract", scenes=scenes)
    request = {
        "script": to_premium_script(fplan),
        "profile": "premium", "visual_mode": "premium",
        "language": "en", "voice": "af_heart"
    }
    premium_plan = make_plan(request, tmp_path)
    assert len(premium_plan["scenes"]) == 6
    assert premium_plan["scenes"][1]["kind"] == "data"
    assert len(premium_plan["scenes"][1]["data"]) == 2
    assert premium_plan["auto_publish"] is False
    assert premium_plan["narration_rewritten"] is False
