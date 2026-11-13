"""Forge: a local, CPU-only resolver for "This Is Not A Weapon" (no API key, no per-craft cost).

A third resolver_fn next to resolver.llm and resolver.fallback: Hybrid(...).resolve(build, tier) -> GadgetDraft.
Mechanics come from a ~10M from-scratch model, name + description from a fine-tuned flan-t5-small; both decode under
a grammar built from the capability contract, so every draft is legal for its chassis and has a trigger that fires.
Code still owns every number (fill_budget + clamp.apply). See docs/FORGE.md.

  pip install -e ".[forge]" && python -m forge.fetch      # weights -> models/forge/
  python -m forge                                         # craft in the terminal
  python -m resolver.serve --forge                        # the sidecar (game + playground) on the local model
"""


def quiet():
    """Silence load-time noise (torch's macOS 'Redirects' note, HF progress bars, the benign tied-weights warning:
    the T5 writers were trained with untied input/output embeddings and load the same way)."""
    import logging
    import os
    import warnings
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    warnings.filterwarnings("ignore")
    logging.getLogger("torch.distributed.elastic.multiprocessing.redirects").addFilter(lambda r: False)
    os.environ.setdefault("HF_HUB_VERBOSITY", "error")  # 'unauthenticated requests' note when Model2Vec loads
    logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
