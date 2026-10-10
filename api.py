"""Tiny HTTP endpoint for non-MCP clients:  uvicorn api:app"""
from fastapi import FastAPI
from pydantic import BaseModel, Field

from rag import DocsQA

app = FastAPI(title="Docs Q&A")
qa = DocsQA()


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


@app.post("/ask")
def ask(q: Question) -> dict:
    return qa.ask(q.question).__dict__
