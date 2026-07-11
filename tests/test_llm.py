from types import SimpleNamespace

import pytest

from resolver.contract import Effect, EffectKind, GadgetDraft, Stage, Tier, Trigger
from resolver.items import DEFAULT_BUILDS
from resolver.llm import LLMResolver
from resolver.prompt import SYSTEM_PROMPT


class FakeMessages:
    """Yields one canned outcome per parse() call: a GadgetDraft (success),
    None (a refusal — parsed_output is None), or an Exception (transport error)."""

    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.models_used = []
        self.captured = None

    def parse(self, **kwargs):
        self.captured = kwargs
        self.models_used.append(kwargs["model"])
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        stop = "refusal" if outcome is None else "end_turn"
        return SimpleNamespace(parsed_output=outcome, stop_reason=stop)


class FakeClient:
    def __init__(self, outcomes):
        self.messages = FakeMessages(outcomes)


def _canned_draft():
    return GadgetDraft(
        name="Fake", description="", logic="",
        stages=[Stage(trigger=Trigger.ON_HIT, effects=[Effect(kind=EffectKind.DAMAGE, amount=1)])],
    )


def test_resolver_returns_the_parsed_draft():
    client = FakeClient([_canned_draft()])
    resolver = LLMResolver(client, models=["claude-sonnet-5"])
    out = resolver.resolve(DEFAULT_BUILDS["broom+oil"], Tier.RARE)
    assert out.name == "Fake"
    assert client.messages.models_used == ["claude-sonnet-5"]


def test_resolver_wires_the_call_correctly():
    client = FakeClient([_canned_draft()])
    resolver = LLMResolver(client, models=["claude-sonnet-5"])
    resolver.resolve(DEFAULT_BUILDS["broom+oil"], Tier.RARE)
    call = client.messages.captured
    assert call["model"] == "claude-sonnet-5"
    assert call["system"] == SYSTEM_PROMPT
    assert call["output_format"] is GadgetDraft
    assert "TARGET TIER: RARE" in call["messages"][0]["content"]
    # no sampling params — current Sonnet rejects non-default temperature/top_p/top_k
    assert "temperature" not in call and "top_p" not in call and "top_k" not in call


def test_resolver_escalates_to_next_model_on_refusal():
    # primary refuses twice, then the escalate model succeeds
    client = FakeClient([None, None, _canned_draft()])
    resolver = LLMResolver(client, models=["claude-sonnet-5", "claude-sonnet-5", "claude-opus-4-8"])
    out = resolver.resolve(DEFAULT_BUILDS["broom+oil"], Tier.LEGENDARY)
    assert out.name == "Fake"
    assert client.messages.models_used == ["claude-sonnet-5", "claude-sonnet-5", "claude-opus-4-8"]


def test_resolver_raises_when_all_attempts_refuse():
    client = FakeClient([None, None, None])
    resolver = LLMResolver(client, models=["claude-sonnet-5", "claude-sonnet-5", "claude-opus-4-8"])
    with pytest.raises(RuntimeError, match="refusal"):
        resolver.resolve(DEFAULT_BUILDS["fan+duck"], Tier.EPIC)
    assert len(client.messages.models_used) == 3


def test_resolver_retries_past_an_exception():
    client = FakeClient([RuntimeError("boom"), _canned_draft()])
    resolver = LLMResolver(client, models=["claude-sonnet-5", "claude-opus-4-8"])
    out = resolver.resolve(DEFAULT_BUILDS["broom+oil"], Tier.RARE)
    assert out.name == "Fake"
    assert client.messages.models_used == ["claude-sonnet-5", "claude-opus-4-8"]


def test_resolver_requires_at_least_one_model():
    with pytest.raises(ValueError):
        LLMResolver(FakeClient([]), models=[])
