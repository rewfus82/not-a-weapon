"""LLM resolver: proposes the creative composition via structured output.

The Anthropic client is injected so the harness can use a real client at
runtime and a fake client in tests (creativity itself is not unit-testable;
this is a contract test of the wiring). This is offline/frontier generation,
never a runtime hot path.
"""
from __future__ import annotations

from resolver.clamp import fill_budget
from resolver.contract import GadgetDraft, Tier
from resolver.items import Build
from resolver.prompt import SYSTEM_PROMPT, render_user_message

# Adaptive thinking (on by default for Sonnet/Opus) shares this budget with the
# structured output; too small and thinking starves the JSON, truncating it
# mid-token and failing schema validation. Generous headroom, no streaming.
MAX_TOKENS = 8000


class LLMResolver:
    def __init__(self, client, models: list[str]) -> None:
        if not models:
            raise ValueError("LLMResolver needs at least one model")
        self.client = client
        self.models = list(models)

    def resolve(self, build: Build, tier: Tier) -> GadgetDraft:
        # Try each model in order; the first parseable draft wins. A refusal
        # (parsed_output is None) or a transport error advances to the next
        # model — retries with escalation, the way the POC did. Only when every
        # attempt fails do we raise, so the harness records a fallback slot.
        user = render_user_message(build, tier)
        last_reason: str | None = None
        for model in self.models:
            try:
                response = self.client.messages.parse(
                    model=model,
                    max_tokens=MAX_TOKENS,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": user}],
                    output_format=GadgetDraft,
                )
                draft = response.parsed_output
                if draft is not None:
                    return fill_budget(draft, tier)
                last_reason = f"no GadgetDraft (stop_reason={response.stop_reason!r})"
            except Exception as exc:  # noqa: BLE001 - retry on any transport/parse failure
                last_reason = f"{type(exc).__name__}: {exc}"
        raise RuntimeError(
            f"resolver exhausted {len(self.models)} attempt(s); last: {last_reason}"
        )
