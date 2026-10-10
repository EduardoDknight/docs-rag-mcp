"""Okapi BM25 in pure Python. Swap for embeddings via the `Retriever` protocol."""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Protocol

from .ingest import Chunk

STOP = set(
    "a an the of to in on for and or is are be by with at from your you it this that as "
    "do does what how can i my".split()
)


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOP]


class Retriever(Protocol):
    """Optional embeddings hook: any object with this method can replace BM25
    (e.g. a pgvector / sqlite-vec retriever, or a hybrid BM25 + vector scorer)."""

    def search(self, query: str, k: int = 4) -> list[tuple[Chunk, float]]: ...


class BM25:
    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75):
        self.chunks, self.k1, self.b = chunks, k1, b
        self.docs = [Counter(tokenize(c.title + " " + c.text)) for c in chunks]
        self.lens = [sum(d.values()) for d in self.docs]
        self.avg = sum(self.lens) / max(len(self.lens), 1)
        df = Counter(t for d in self.docs for t in d)
        n = len(chunks)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def search(self, query: str, k: int = 4) -> list[tuple[Chunk, float]]:
        q = tokenize(query)
        scored = []
        for c, d, ln in zip(self.chunks, self.docs, self.lens):
            s = 0.0
            for t in q:
                if t in d:
                    tf = d[t]
                    norm = tf + self.k1 * (1 - self.b + self.b * ln / self.avg)
                    s += self.idf[t] * tf * (self.k1 + 1) / norm
            if s > 0:
                scored.append((c, s))
        return sorted(scored, key=lambda x: -x[1])[:k]
