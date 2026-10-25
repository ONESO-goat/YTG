"""The classifier's handling of model answers, using a fake engine instead of a real AI."""

from conftest import random_png

from agent.bot import ScreenClassifier
from agent.engine import parse_json
from agent.frames import frame_fingerprint, is_same_frame


class FakeEngine:
    backend = "fake"

    def __init__(self, summary, verdict):
        self.summary, self.verdict = summary, verdict
        self.judged = None

    def describe_image(self, image_bytes, system_prompt):
        return self.summary

    def judge(self, text, system_prompt):
        self.judged = (text, system_prompt)
        return self.verdict


def classifier_with(summary, verdict) -> ScreenClassifier:
    c = ScreenClassifier("stub")
    c.engine = FakeEngine(summary, verdict)  # type: ignore[assignment]
    return c


def analyze(c: ScreenClassifier, restrictions=("gore",)):
    return c.analyze(b"png", user_id="u", guardian_settings=None, restrictions=list(restrictions))


def test_parse_json_handles_fences_and_garbage():
    assert parse_json('```json\n{"flagged": true}\n```') == {"flagged": True}
    assert parse_json('{"a": 1}') == {"a": 1}
    assert parse_json("not json") is None
    assert parse_json("[1, 2]") is None
    assert parse_json(None) is None


def test_flagged_verdict():
    c = classifier_with({"summary": "a gory scene"}, {"flagged": True, "category": "gore", "confidence": 0.8})
    a = analyze(c)
    assert a.flagged and a.category == "gore" and not a.failed
    assert "gore" in c.engine.judged[1]  # the restrictions reach the prompt


def test_unknown_categories_are_not_trusted():
    c = classifier_with({"summary": "x"}, {"flagged": True, "category": "made up", "confidence": "high"})
    a = analyze(c)
    assert a.flagged and a.category == "restricted content" and a.confidence == 0.0


def test_unusable_answers_fail_safely():
    assert analyze(classifier_with(None, None)).failed
    assert analyze(classifier_with({"summary": ""}, None)).failed
    assert analyze(classifier_with({"summary": "ok"}, {"description": "no flagged key"})).failed
    assert analyze(classifier_with({"summary": "ok"}, {"flagged": "yes"})).failed


def test_frame_fingerprints():
    a, b = frame_fingerprint(random_png(1)), frame_fingerprint(random_png(2))
    assert a and b
    assert is_same_frame(a, frame_fingerprint(random_png(1)))
    assert not is_same_frame(a, b)
    assert frame_fingerprint(b"garbage") is None
