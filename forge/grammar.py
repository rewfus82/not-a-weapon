"""The GadgetDraft token grammar as a prefix parser, so the same rules constrain any model/tokenizer.

Token language:  (<stage> <trig:T> (<fx> <k:K> <t:TGT> <bA> <bD> <bR> <cN>)+ )+ <name> text+ <desc> text+ EOS
Guarantees, for the locked chassis of the build:
  - the output parses into the game's GadgetDraft (1-4 stages, 1-4 effects each),
  - SELF-kit legality (no ON_IMPACT/ON_TRIGGER/ON_BLOCK; ON_HIT only on protective gear; SELF targets on
    ON_USE/ON_EXPIRE/ON_KILL stages) - i.e. the game's repair() is a no-op,
  - at least one stage on a trigger the game's renderer actually fires (no dead gadgets),
  - descriptions may only reference slot tokens <iK> for items present in the build.
"""

import torch

from resolver.contract import EffectKind, Target, Trigger  # noqa: E402

MAX_STAGES, MAX_FX, MAX_COUNT, N_BUCKETS = 4, 4, 8, 11
DIRECT = {"ON_USE", "ON_HIT", "ON_IMPACT"}
FIRING = {"PLACED": {"ON_TRIGGER"}, "GUARD": {"ON_USE", "ON_BLOCK"}, "SELF": {"ON_USE", "ON_HIT"},
          "DASH": {"ON_USE", "ON_HIT"}}
SELF_ILLEGAL = {"ON_IMPACT", "ON_TRIGGER", "ON_BLOCK"}
SELF_TARGET_ONLY = {"ON_USE", "ON_EXPIRE", "ON_KILL"}
STRUCT_TOKENS = (["<stage>", "<fx>"] + [f"<trig:{t.value}>" for t in Trigger] + [f"<k:{k.value}>" for k in EffectKind]
                 + [f"<t:{t.value}>" for t in Target] + [f"<b{i}>" for i in range(N_BUCKETS)]
                 + [f"<c{i}>" for i in range(MAX_COUNT + 1)])
SLOT_TOKENS = [f"<i{k}>" for k in range(4)]
TEXT_TOKENS = ["<name>", "<desc>"]


class Grammar:
    def __init__(self, ids, eos_id, text_mask, build, max_name=12, max_desc=64):
        """ids: token string -> id for STRUCT_TOKENS + SLOT_TOKENS + TEXT_TOKENS; text_mask: bool[vocab] of
        ordinary text pieces allowed inside the name/description."""
        self.I, self.eos, self.text = ids, eos_id, text_mask
        self.vocab = text_mask.shape[0]
        self.max_name, self.max_desc = max_name, max_desc
        form = build.delivery.value
        self.is_self = form == "SELF"
        protective = "protective" in build.delivery_item.tags
        self.firing = FIRING.get(form, DIRECT)
        self.trig_ok = [t.value for t in Trigger
                        if not (self.is_self and (t.value in SELF_ILLEGAL or (t.value == "ON_HIT" and not protective)))]
        self.id2trig = {ids[f"<trig:{t.value}>"]: t.value for t in Trigger}
        self.slot_ok = [ids[f"<i{k}>"] for k, (_, it) in enumerate(build.slots()) if it is not None]
        m = self._mask
        self.m_stage, self.m_fx, self.m_name = m([ids["<stage>"]]), m([ids["<fx>"]]), m([ids["<name>"]])
        self.m_kind = m([ids[f"<k:{k.value}>"] for k in EffectKind])
        self.m_tgt_all = m([ids[f"<t:{t.value}>"] for t in Target])
        self.m_tgt_self = m([ids["<t:SELF>"]])
        self.m_bucket = m([ids[f"<b{i}>"] for i in range(N_BUCKETS)])
        self.m_count = m([ids[f"<c{i}>"] for i in range(MAX_COUNT + 1)])
        self.m_desc, self.m_eos = m([ids["<desc>"]]), m([eos_id])

    def _mask(self, toks):
        mk = torch.zeros(self.vocab, dtype=torch.bool)
        mk[toks] = True
        return mk

    def parse(self, prefix):
        I = self.I  # noqa: E741
        st = dict(state="start", n_stages=0, n_fx=0, fired=False, trig=None, n=0)
        order = {"kind": "tgt", "tgt": "amt", "amt": "dur", "dur": "rad", "rad": "cnt", "cnt": "after"}
        for tok in prefix:
            s = st["state"]
            if s in ("start", "after") and tok == I["<stage>"]:
                st.update(state="trig", n_stages=st["n_stages"] + 1, n_fx=0)
            elif s == "trig":
                st["trig"] = self.id2trig[tok]
                st["fired"] = st["fired"] or st["trig"] in self.firing
                st["state"] = "fx"
            elif s in ("fx", "after") and tok == I["<fx>"]:
                st.update(state="kind", n_fx=st["n_fx"] + 1)
            elif s in order:
                st["state"] = order[s]
            elif s == "after" and tok == I["<name>"]:
                st.update(state="name", n=0)
            elif s == "name":
                st.update(state="desc", n=0) if tok == I["<desc>"] else st.update(n=st["n"] + 1)
            elif s == "desc":
                st.update(state="done") if tok == self.eos else st.update(n=st["n"] + 1)
        return st

    def allowed(self, prefix):
        st = self.parse(prefix)
        s = st["state"]
        if s == "start":
            return self.m_stage
        if s == "trig":
            ts = [t for t in self.trig_ok if st["fired"] or st["n_stages"] < MAX_STAGES or t in self.firing]
            return self._mask([self.I[f"<trig:{t}>"] for t in ts])
        if s == "fx":
            return self.m_fx
        if s == "kind":
            return self.m_kind
        if s == "tgt":
            return self.m_tgt_self if self.is_self and st["trig"] in SELF_TARGET_ONLY else self.m_tgt_all
        if s in ("amt", "dur", "rad"):
            return self.m_bucket
        if s == "cnt":
            return self.m_count
        if s == "after":
            opts = []
            if st["n_fx"] < MAX_FX:
                opts.append(self.I["<fx>"])
            if st["n_stages"] < MAX_STAGES:
                opts.append(self.I["<stage>"])
            if st["fired"]:
                opts.append(self.I["<name>"])
            return self._mask(opts)
        if s == "name":
            if st["n"] >= self.max_name:
                return self.m_desc
            mk = self.text.clone()
            if st["n"] >= 1:
                mk[self.I["<desc>"]] = True
            return mk
        if s == "desc":
            if st["n"] >= self.max_desc:
                return self.m_eos
            mk = self.text.clone()
            mk[self.slot_ok] = True
            if st["n"] >= 4:
                mk[self.eos] = True
            return mk
        return self.m_eos  # done
