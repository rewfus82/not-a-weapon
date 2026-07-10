from resolver.contract import Tier
from resolver.items import DEFAULT_BUILDS
from resolver.prompt import SYSTEM_PROMPT, render_user_message


def test_system_prompt_is_loaded_and_jargon_free():
    assert len(SYSTEM_PROMPT) > 500
    lowered = SYSTEM_PROMPT.lower()
    for banned in ("diver", "jack-in", "jack in", "signature", "the simulation"):
        assert banned not in lowered


def test_render_user_message_includes_slots_associations_delivery_and_tier():
    build = DEFAULT_BUILDS["broom+oil"]
    msg = render_user_message(build, Tier.RARE)
    assert "delivery:" in msg and "push broom" in msg
    assert "utility:" in msg and "spilled fry oil" in msg
    assert "damage:" in msg and "empty" in msg  # unfilled slot shows "empty"
    assert "LOCKED DELIVERY FORM: SWING" in msg
    assert "TARGET TIER: RARE" in msg
    # at least one association from the delivery item is injected
    assert "bristles" in msg
