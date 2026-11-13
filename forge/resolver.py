"""ForgeResolver: the local model as a drop-in resolver_fn for resolver.serve (and anything else that takes one).

    from forge.resolver import ForgeResolver
    resolve = ForgeResolver()            # loads models/forge (~2 s, ~500 MB RAM), CPU only, 1 thread
    draft = resolve(build, Tier.RARE)    # GadgetDraft with fill_budget applied, like LLMResolver.resolve

Each call samples a fresh seed, so repeated crafts of the same combo give different readings - the same contract as
the live LLM path ("acquisition is random"; the drawn instance is what gets frozen). deterministic=True makes a
combo + tier always return the same reading (handy for tests and for pre-baking a library).
Calls are serialized: the models run single-threaded, so concurrent rolls would only contend for the same core.
"""
import random
import threading

from resolver.contract import Tier


class ForgeResolver:
    source = "forge"  # what serve.py reports as the gadget's source

    def __init__(self, models=None, n=8, deterministic=False):
        from forge import quiet
        quiet()
        from forge.writer import load_resolver
        self.model = load_resolver(models)
        self.n, self.deterministic = n, deterministic
        self._lock = threading.Lock()

    def __call__(self, build, tier):
        seed = None if self.deterministic else random.randrange(1 << 30)
        with self._lock:
            return self.model.resolve(build, Tier(tier).value, seed=seed, n=self.n)

    resolve = __call__

    @property
    def label(self):
        return f"FORGE (local model, epoch {self.model.ck['epoch']})"
