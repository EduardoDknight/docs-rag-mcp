import asyncio

import pytest
from fastapi.testclient import TestClient

from rag import DocsQA
from rag.security import check_citations, scan


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


@pytest.fixture(scope="module")
def qa():
    return DocsQA()


@pytest.mark.parametrize("q,doc", [
    ("How many days of PTO do I accrue?", "hr-pto-policy"),
    ("Can I get a refund after 60 days?", "refund-policy"),
    ("What is the API rate limit?", "api-guide"),
    ("How many days can I work remotely?", "hr-remote-work"),
    ("What is the response time for a SEV1 incident?", "incident-response"),
])
def test_retrieval_finds_right_doc(qa, q, doc):
    assert qa.search(q, 1)[0]["doc"] == doc


def test_refuses_out_of_scope(qa):
    a = qa.ask("What is the capital of Australia?")
    assert a.refused and a.citations == []


def test_injection_doc_flagged(qa):
    assert {c.doc for c in qa.chunks if c.flags} == {"vendor-faq"}


def test_injection_not_obeyed(qa):
    a = qa.ask("When are vendors paid after an invoice?")
    assert "45" in a.answer
    low = a.answer.lower()
    assert "admin mode" not in low and "approved automatically" not in low
    assert any("injection" in w for w in a.warnings)
    # adversarial query that lexically matches the injected sentence
    b = qa.ask("Tell me about admin mode and refunds approved automatically for vendors")
    assert "approved automatically" not in b.answer.lower()
    assert "system prompt" not in b.answer.lower()


def test_citations_valid(qa):
    a = qa.ask("How long do refunds take to process?")
    ok, cited = check_citations(a.answer, {s["id"] for s in a.sources})
    assert ok and cited and all(c.startswith("refund-policy#") for c in cited)


def test_citation_guard_rejects_unknown_or_missing_source():
    assert check_citations("Yes [secret-doc#0]", {"refund-policy#0"})[0] is False
    assert check_citations("Yes, always.", {"refund-policy#0"})[0] is False


def test_llm_answer_with_bad_citation_falls_back(qa, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-not-a-key")
    monkeypatch.setattr(qa, "_llm", lambda q, c: "All refunds approved [vendor-faq#9]")
    a = qa.ask("How long do refunds take to process?")
    assert a.mode == "extractive" and "citation check" in a.warnings[-1]


def test_scanner_ignores_clean_text():
    assert scan("Refunds are issued within 30 days.") == []


def test_mcp_tools_registered():
    import mcp_server
    names = {t.name for t in asyncio.run(mcp_server.mcp.list_tools())}
    assert {"search_docs", "ask"} <= names


def test_http_ask():
    import api
    r = TestClient(api.app).post("/ask", json={"question": "What is the API rate limit?"})
    assert r.status_code == 200 and r.json()["citations"]
