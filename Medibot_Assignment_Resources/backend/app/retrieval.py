from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

from .ingestion import build_document_index
from .rbac import build_qdrant_filter, can_access_collection


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9]+", text.lower())


def _cosine_similarity(query_tokens: list[str], doc_tokens: list[str]) -> float:
    if not query_tokens or not doc_tokens:
        return 0.0
    q_counter = Counter(query_tokens)
    d_counter = Counter(doc_tokens)
    shared_terms = set(q_counter) & set(d_counter)
    numerator = sum(q_counter[t] * d_counter[t] for t in shared_terms)
    q_norm = math.sqrt(sum(v * v for v in q_counter.values()))
    d_norm = math.sqrt(sum(v * v for v in d_counter.values()))
    if q_norm == 0 or d_norm == 0:
        return 0.0
    return numerator / (q_norm * d_norm)


def _bm25_score(query: str, doc_text: str, doc_freq: dict[str, int], avgdl: float, total_docs: int) -> float:
    q_tokens = _tokenize(query)
    if not q_tokens:
        return 0.0
    doc_tokens = _tokenize(doc_text)
    if not doc_tokens:
        return 0.0
    doc_len = len(doc_tokens)
    k1 = 1.5
    b = 0.75
    score = 0.0
    for token in set(q_tokens):
        tf = doc_tokens.count(token)
        if tf == 0:
            continue
        df = doc_freq.get(token, 1)
        idf = math.log((total_docs - df + 0.5) / (df + 0.5) + 1.0)
        numerator = tf * (k1 + 1)
        denominator = tf + k1 * (1 - b + b * (doc_len / avgdl if avgdl else 1.0))
        score += idf * numerator / denominator
    return score


class HybridSearchEngine:
    def __init__(self, base_dir: Path | None = None):
        base_dir = base_dir or Path(__file__).resolve().parents[2] / "mediassist_data" / "mediassist_data"
        self.docs = build_document_index(base_dir)
        self.texts = [doc["text"] for doc in self.docs]
        self.doc_freq = {}
        for text in self.texts:
            for token in set(_tokenize(text)):
                self.doc_freq[token] = self.doc_freq.get(token, 0) + 1
        self.avgdl = sum(len(_tokenize(text)) for text in self.texts) / max(len(self.texts), 1)

    def apply_rbac_filter(self, role: str) -> list[dict[str, Any]]:
        allowed = [doc for doc in self.docs if can_access_collection(role, doc["collection"])]
        qdrant_filter = build_qdrant_filter(role)
        _ = qdrant_filter
        return allowed

    def _dense_scores(self, query: str, candidate_docs: list[dict[str, Any]]) -> list[float]:
        query_tokens = _tokenize(query)
        if not query_tokens:
            return [0.0 for _ in candidate_docs]
        return [_cosine_similarity(query_tokens, _tokenize(doc["text"])) for doc in candidate_docs]

    def _sparse_scores(self, query: str, candidate_docs: list[dict[str, Any]]) -> list[float]:
        if not candidate_docs:
            return []
        return [_bm25_score(query, doc["text"], self.doc_freq, self.avgdl, len(self.docs)) for doc in candidate_docs]

    def rerank(self, query: str, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not candidates:
            return []
        dense_scores = self._dense_scores(query, candidates)
        sparse_scores = self._sparse_scores(query, candidates)
        combined = []
        for idx, doc in enumerate(candidates):
            combined.append({
                **doc,
                "score": 0.65 * dense_scores[idx] + 0.35 * sparse_scores[idx],
            })
        combined.sort(key=lambda item: item["score"], reverse=True)
        return combined[:3]

    def search(self, query: str, role: str, top_k: int = 10) -> list[dict[str, Any]]:
        filtered_docs = self.apply_rbac_filter(role)
        if not filtered_docs:
            return []
        dense_scores = self._dense_scores(query, filtered_docs)
        sparse_scores = self._sparse_scores(query, filtered_docs)
        ranked = []
        for idx, doc in enumerate(filtered_docs):
            ranked.append({
                **doc,
                "score": 0.65 * dense_scores[idx] + 0.35 * sparse_scores[idx],
            })
        ranked.sort(key=lambda item: item["score"], reverse=True)
        return ranked[:top_k]

    def search_with_rerank(self, query: str, role: str) -> list[dict[str, Any]]:
        filtered_docs = self.apply_rbac_filter(role)
        if not filtered_docs:
            return []
        broad_hits = self.search(query, role, top_k=10)
        return self.rerank(query, broad_hits)
