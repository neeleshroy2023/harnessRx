"""RAG Q&A feature: question + doc corpus -> answer with citations.

Tiny in-memory corpus loaded from datasets/rag_corpus/*.txt.
Keyword retrieval (no embeddings) — corpus is small and demo-focused.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from app.llm.anthropic_client import FEATURE_MODEL, acomplete

CORPUS_DIR = Path(__file__).resolve().parents[3] / "datasets" / "rag_corpus"

SYSTEM = """You are a careful question-answering assistant.
Answer using ONLY the provided documents. If the answer is not in the documents, reply exactly: I don't know.

Format:
- 1-3 sentence answer.
- After the answer, on a new line, list the cited doc ids you used:
  CITATIONS: doc1, doc2

Do not invent citations. Do not cite docs you did not use.
"""


def _tokenize(s: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", s.lower())


def load_corpus() -> dict[str, str]:
    if not CORPUS_DIR.exists():
        return {}
    return {p.stem: p.read_text(encoding="utf-8") for p in sorted(CORPUS_DIR.glob("*.txt"))}


def retrieve(question: str, corpus: dict[str, str], k: int = 3) -> list[tuple[str, str]]:
    q_tokens = Counter(_tokenize(question))
    scores: list[tuple[float, str]] = []
    for doc_id, text in corpus.items():
        d_tokens = Counter(_tokenize(text))
        overlap = sum(min(q_tokens[t], d_tokens[t]) for t in q_tokens)
        scores.append((overlap, doc_id))
    scores.sort(reverse=True)
    return [(doc_id, corpus[doc_id]) for score, doc_id in scores[:k] if score > 0]


def _parse_response(raw: str) -> tuple[str, list[str]]:
    lines = raw.strip().splitlines()
    citations: list[str] = []
    answer_lines: list[str] = []
    for line in lines:
        if line.strip().upper().startswith("CITATIONS:"):
            cites_str = line.split(":", 1)[1]
            citations = [c.strip() for c in cites_str.split(",") if c.strip()]
        else:
            answer_lines.append(line)
    return "\n".join(answer_lines).strip(), citations


async def invoke(payload: dict) -> dict:
    question = payload["question"]
    corpus = load_corpus()
    if "doc_ids" in payload:
        corpus = {k: v for k, v in corpus.items() if k in payload["doc_ids"]}
    retrieved = retrieve(question, corpus, k=payload.get("k", 3))
    if not retrieved:
        return {"answer": "I don't know.", "citations": [], "retrieved": []}

    context_blocks = "\n\n".join(
        f"[doc:{doc_id}]\n{text}" for doc_id, text in retrieved
    )
    user_prompt = f"Documents:\n{context_blocks}\n\nQuestion: {question}"
    raw = await acomplete(
        model=FEATURE_MODEL,
        system=SYSTEM,
        user=user_prompt,
        max_tokens=400,
    )
    answer, citations = _parse_response(raw)
    return {
        "answer": answer,
        "citations": citations,
        "retrieved": [doc_id for doc_id, _ in retrieved],
    }
