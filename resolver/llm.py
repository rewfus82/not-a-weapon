"""LLM resolver: proposes the creative composition via structured output.

The Anthropic client is injected so the harness can use a real client at
runtime and a fake client in tests (creativity itself is not unit-testable;
this is a contract test of the wiring). This is offline/frontier generation,
never a runtime hot path.
"""
from __future__ import annotations

from resolver.contract import GadgetDraft, Tier
from resolver.items import Build
from resolver.prompt import SYSTEM_PROMPT, render_user_message

# Adaptive thinking (on by default for Sonnet/Opus) shares this budget with the
# structured output; too small and thinking starves the JSON, truncating it
# mid-token and failing schema validation. Generous headroom, no streaming.
MAX_TOKENS = 8000


class LLMResolver:
    def __init__(self, client, model: str) -> None:
        self.client = client
        self.model = model

    def resolve(self, build: Build, tier: Tier) -> GadgetDraft:
        response = self.client.messages.parse(
            model=self.model,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": render_user_message(build, tier)}],
            output_format=GadgetDraft,
        )
        draft = response.parsed_output
        if draft is None:
            # No parseable GadgetDraft: a refusal, or thinking consumed the
            # whole budget leaving no text block. Surface it so the harness
            # can record the failed slot instead of crashing on a None draft.
            raise RuntimeError(
                f"resolver returned no GadgetDraft (stop_reason={response.stop_reason!r})"
            )
        return draft
