from types import SimpleNamespace

from resolver.contract import Effect, EffectKind, GadgetDraft, Stage, Tier, Trigger
from resolver.items import DEFAULT_BUILDS
from resolver.llm import LLMResolver
from resolver.prompt import SYSTEM_PROMPT


class FakeMessages:
    def __init__(self, canned):
        self.canned = canned
        self.captured = None

    def parse(self, **kwargs):
        self.captured = kwargs
        return SimpleNamespace(parsed_output=self.canned)


class FakeClient:
    def __init__(self, canned):
        self.messages = FakeMessages(canned)


def _canned_draft():
    return GadgetDraft(
        name="Fake", description="", logic="",
        stages=[Stage(trigger=Trigger.ON_HIT, effects=[Effect(kind=EffectKind.DAMAGE, amount=1)])],
    )


def test_resolver_returns_the_parsed_draft():
    client = FakeClient(_canned_draft())
    resolver = LLMResolver(client, model="claude-sonnet-5")
    out = resolver.resolve(DEFAULT_BUILDS["broom+oil"], Tier.RARE)
    assert out.name == "Fake"


def test_resolver_wires_the_call_correctly():
    client = FakeClient(_canned_draft())
    resolver = LLMResolver(client, model="claude-sonnet-5")
    resolver.resolve(DEFAULT_BUILDS["broom+oil"], Tier.RARE)
    call = client.messages.captured
    assert call["model"] == "claude-sonnet-5"
    assert call["system"] == SYSTEM_PROMPT
    assert call["output_format"] is GadgetDraft
    assert "TARGET TIER: RARE" in call["messages"][0]["content"]
    # no sampling params — current Sonnet rejects non-default temperature/top_p/top_k
    assert "temperature" not in call and "top_p" not in call and "top_k" not in call
