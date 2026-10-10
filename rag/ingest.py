"""Load markdown docs and split them into overlapping, citable chunks."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Chunk:
    id: str          # stable citation id, e.g. "refund-policy#2"
    doc: str         # source file stem
    title: str       # document title (first heading)
    text: str
    flags: list[str] = field(default_factory=list)  # filled by the injection scanner


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [p.strip() for p in parts if p.strip() and not p.strip().startswith("#")]


def chunk_doc(doc: str, text: str, max_words: int = 60, overlap_sentences: int = 1) -> list[Chunk]:
    """Group sentences into ~max_words chunks; repeat the last N sentences in the next chunk."""
    title = next((ln.lstrip("# ").strip() for ln in text.splitlines() if ln.startswith("#")), doc)
    sents = _sentences(text)
    chunks: list[Chunk] = []
    cur: list[str] = []
    i = 0
    while i < len(sents):
        cur.append(sents[i])
        i += 1
        if sum(len(s.split()) for s in cur) >= max_words or i == len(sents):
            chunks.append(Chunk(f"{doc}#{len(chunks)}", doc, title, " ".join(cur)))
            cur = cur[-overlap_sentences:] if i < len(sents) and overlap_sentences else []
    return chunks


def load_corpus(path: str | Path, **kw) -> list[Chunk]:
    out: list[Chunk] = []
    for f in sorted(Path(path).glob("*.md")):
        out.extend(chunk_doc(f.stem, f.read_text(encoding="utf-8"), **kw))
    return out
