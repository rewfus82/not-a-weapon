"""Seeding and constrained sampling shared by both models."""
import hashlib

import torch


def combo_seed(parts, salt=0):
    """Stable 32-bit seed for a combo (+ depth/tier/...), identical on every machine and Python version."""
    key = "|".join(parts) + f"#{salt}"
    return int(hashlib.md5(key.encode()).hexdigest()[:8], 16)


def pick(logits, allowed, gen, temperature, min_p):
    """Next token under a grammar mask: greedy when gen is None, else min-p sampling at the given temperature."""
    logits = logits.masked_fill(~allowed, float("-inf"))
    if gen is None:
        return int(logits.argmax())
    probs = torch.softmax(logits / temperature, -1)
    probs = probs.masked_fill(probs < min_p * probs.max(), 0.0)
    return int(torch.multinomial(probs / probs.sum(), 1, generator=gen))
