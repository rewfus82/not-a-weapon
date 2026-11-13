"""Forge model: pre-LN Transformer encoder-decoder with tied embeddings (deep encoder, shallow decoder)."""
import torch
import torch.nn as nn
import torch.nn.functional as F


class Attention(nn.Module):
    def __init__(self, d, h, dropout, cross=False):
        super().__init__()
        self.h, self.dropout, self.cross = h, dropout, cross
        if cross:
            self.q, self.kv = nn.Linear(d, d), nn.Linear(d, 2 * d)
        else:
            self.qkv = nn.Linear(d, 3 * d)
        self.o = nn.Linear(d, d)

    def forward(self, x, mem=None, mask=None, causal=False):
        B, T, D = x.shape
        hd = D // self.h
        if self.cross:
            q = self.q(x).view(B, T, self.h, hd).transpose(1, 2)
            k, v = self.kv(mem).view(B, mem.shape[1], 2, self.h, hd).permute(2, 0, 3, 1, 4)
        else:
            q, k, v = self.qkv(x).view(B, T, 3, self.h, hd).permute(2, 0, 3, 1, 4)
        a = F.scaled_dot_product_attention(q, k, v, attn_mask=mask, is_causal=causal and mask is None,
                                           dropout_p=self.dropout if self.training else 0.0)
        return self.o(a.transpose(1, 2).reshape(B, T, D))


class FFN(nn.Module):
    def __init__(self, d, ff, dropout):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(d, ff), nn.GELU(), nn.Dropout(dropout), nn.Linear(ff, d))

    def forward(self, x):
        return self.net(x)


class EncBlock(nn.Module):
    def __init__(self, d, h, ff, dropout):
        super().__init__()
        self.ln1, self.att, self.ln2, self.ffn = nn.LayerNorm(d), Attention(d, h, dropout), nn.LayerNorm(d), FFN(d, ff, dropout)
        self.drop = nn.Dropout(dropout)

    def forward(self, x, mask):
        x = x + self.drop(self.att(self.ln1(x), mask=mask))
        return x + self.drop(self.ffn(self.ln2(x)))


class DecBlock(nn.Module):
    def __init__(self, d, h, ff, dropout):
        super().__init__()
        self.ln1, self.self_att = nn.LayerNorm(d), Attention(d, h, dropout)
        self.ln2, self.cross_att = nn.LayerNorm(d), Attention(d, h, dropout, cross=True)
        self.ln3, self.ffn = nn.LayerNorm(d), FFN(d, ff, dropout)
        self.drop = nn.Dropout(dropout)

    def forward(self, x, mem, mem_mask):
        x = x + self.drop(self.self_att(self.ln1(x), causal=True))
        x = x + self.drop(self.cross_att(self.ln2(x), mem=mem, mask=mem_mask))
        return x + self.drop(self.ffn(self.ln3(x)))


class Forge(nn.Module):
    def __init__(self, vocab, d=256, heads=4, enc_layers=4, dec_layers=3, ff_mult=4, max_pos=128, dropout=0.1,
                 pad_id=0, feat_dim=0):
        super().__init__()
        self.config = dict(vocab=vocab, d=d, heads=heads, enc_layers=enc_layers, dec_layers=dec_layers,
                           ff_mult=ff_mult, max_pos=max_pos, dropout=dropout, pad_id=pad_id, feat_dim=feat_dim)
        self.pad_id = pad_id
        self.emb = nn.Embedding(vocab, d)
        # optional pretrained item knowledge: a feature vector per source token, projected into the encoder
        self.item_proj = nn.Sequential(nn.Linear(feat_dim, d), nn.GELU(), nn.Linear(d, d)) if feat_dim else None
        self.pos_enc, self.pos_dec = nn.Embedding(max_pos, d), nn.Embedding(max_pos, d)
        self.enc = nn.ModuleList(EncBlock(d, heads, ff_mult * d, dropout) for _ in range(enc_layers))
        self.dec = nn.ModuleList(DecBlock(d, heads, ff_mult * d, dropout) for _ in range(dec_layers))
        self.enc_ln, self.dec_ln = nn.LayerNorm(d), nn.LayerNorm(d)
        self.drop = nn.Dropout(dropout)
        self.apply(self._init)

    @staticmethod
    def _init(m):
        if isinstance(m, (nn.Linear, nn.Embedding)):
            nn.init.normal_(m.weight, std=0.02)
        if isinstance(m, nn.Linear) and m.bias is not None:
            nn.init.zeros_(m.bias)

    def mem_mask(self, src):
        return (src != self.pad_id)[:, None, None, :]  # True = attend

    def encode(self, src, feat=None):
        mask = self.mem_mask(src)
        x = self.emb(src) + self.pos_enc.weight[: src.shape[1]]
        if self.item_proj is not None and feat is not None:
            x = x + self.item_proj(feat)
        x = self.drop(x)
        for blk in self.enc:
            x = blk(x, mask)
        return self.enc_ln(x), mask

    def decode(self, tgt_in, mem, mem_mask):
        x = self.drop(self.emb(tgt_in) + self.pos_dec.weight[: tgt_in.shape[1]])
        for blk in self.dec:
            x = blk(x, mem, mem_mask)
        return self.dec_ln(x) @ self.emb.weight.T  # tied output projection

    def forward(self, src, tgt_in, feat=None):
        mem, mask = self.encode(src, feat)
        return self.decode(tgt_in, mem, mask)


def n_params(model):
    return sum(p.numel() for p in model.parameters())
