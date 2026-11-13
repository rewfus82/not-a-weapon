"""Text helpers shared by the mechanics model and the writer: item vectors, slot re-insertion, the BPE tokenizer.

Delexicalization: in the description every mention of build item k is a slot token <ik> ("A <i1> wedges
inside <i0>'s barrel"); real names are re-inserted after generation. The model never spells item names, can only
mention items that are actually in the build, and works for any catalog item.
"""
import re
from pathlib import Path

FEAT_DIM = 256  # Model2Vec potion-base-8M


class ItemEmbedder:
    """Pretrained item knowledge: a static Model2Vec vector per text (cached). Only needed to (re)build item vectors
    at training time and for the CLI's did-you-mean; the runtime loads a precomputed table (item_vectors.npz)."""

    def __init__(self, cache=None):
        self.table, self._m = {}, None
        if cache and Path(cache).exists():
            import numpy as np
            z = np.load(cache, allow_pickle=False)
            self.table = dict(zip(z["names"].tolist(), z["vecs"]))

    def _model(self):
        if self._m is None:
            from model2vec import StaticModel
            self._m = StaticModel.from_pretrained("minishlab/potion-base-8M")
        return self._m

    def __call__(self, names):
        import numpy as np
        missing = sorted({n for n in names if n not in self.table})
        if missing:
            self.table.update(zip(missing, self._model().encode(missing)))
        return np.stack([self.table[n] for n in names]).astype("float32")

    def save(self, path):
        import numpy as np
        names = sorted(self.table)
        np.savez(path, names=np.array(names), vecs=np.stack([self.table[n] for n in names]).astype("float32"))


def relex(text, items):
    """Re-insert item names for slot tokens <iK>, fixing a/an in front of them and the leading capital."""
    for k, name in enumerate(items):
        def art(m, name=name):
            a = "an" if name[0].lower() in "aeiou" else "a"
            return f"{a.capitalize() if m.group(1)[0].isupper() else a} {name}"
        text = re.sub(rf"\b(an?|An?) <i{k}>", art, text)
        text = text.replace(f"<i{k}>", name)
    text = re.sub(r"<i\d>", "something", text)  # slot beyond the item count (cannot happen with masking)
    return text[:1].upper() + text[1:]


def train_tokenizer(texts, vocab_size, path, specials):
    from tokenizers import Tokenizer, decoders, models, normalizers, pre_tokenizers, trainers

    tok = Tokenizer(models.BPE(unk_token="<unk>"))
    tok.normalizer = normalizers.NFKC()
    tok.pre_tokenizer = pre_tokenizers.Metaspace()
    tok.decoder = decoders.Metaspace()
    alphabet = [chr(c) for c in range(32, 127)] + list("éèñüöä’—–")
    trainer = trainers.BpeTrainer(vocab_size=vocab_size, special_tokens=specials, initial_alphabet=alphabet,
                                  min_frequency=2, show_progress=False)
    tok.train_from_iterator(texts, trainer)
    tok.save(str(path))
    return tok


def load_tokenizer(path, specials):
    from tokenizers import Tokenizer

    tok = Tokenizer.from_file(str(path))
    for i, s in enumerate(specials):
        assert tok.token_to_id(s) == i, f"special token {s} must have id {i}"
    return tok
