"""Prompt-injection defenses: scan chunks, fence them as data, verify citations."""
from __future__ import annotations

import re

from .ingest import Chunk

PATTERNS = {
    "override": r"\b(ignore|disregard|forget)\b.{0,40}\b(previous|prior|above|all)\b.{0,20}\b(instructions?|rules?|prompts?)",
    "role_hijack": r"\byou are now\b|\bact as\b|\b(admin|developer|god) mode\b",
    "exfiltration": r"\b(reveal|print|show|leak)\b.{0,30}\b(system prompt|instructions|api key|secret)",
    "fake_delimiter": r"</?(system|assistant|untrusted_document)>|\[/?INST\]",
}


def scan(text: str) -> list[str]:
    """Return the names of instruction-like patterns found in a chunk."""
    return [name for name, rx in PATTERNS.items() if re.search(rx, text, re.I | re.S)]


def flag_chunks(chunks: list[Chunk]) -> list[Chunk]:
    for c in chunks:
        c.flags = scan(c.text)
    return chunks


def strip_injection(text: str) -> str:
    """Drop sentences that match a pattern; keep the legitimate facts around them."""
    return " ".join(s for s in re.split(r"(?<=[.!?])\s+", text) if not scan(s))


def fence(chunks: list[Chunk]) -> str:
    """Wrap retrieved text as untrusted data, with the ids the model must cite."""
    parts = []
    for c in chunks:
        body = c.text.replace("<", "&lt;")  # a document cannot close the fence
        warn = f' flagged="{",".join(c.flags)}"' if c.flags else ""
        parts.append(f'<untrusted_document id="{c.id}"{warn}>\n{body}\n</untrusted_document>')
    return "\n".join(parts)


CITE_RX = re.compile(r"\[([a-z0-9\-]+#\d+)\]")


def check_citations(answer: str, allowed_ids: set[str]) -> tuple[bool, list[str]]:
    """The answer must cite at least one source, and only sources that were retrieved."""
    cited = CITE_RX.findall(answer)
    return bool(cited) and all(c in allowed_ids for c in cited), cited
