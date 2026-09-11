from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.rbac import ROLE_COLLECTIONS, get_rbac_refusal, get_role_access
from app.retrieval import HybridSearchEngine
from app.sql_rag import sql_rag_chain


def _get_llm_client():
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            from openai import OpenAI

            return OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1")
        except Exception:
            return None

    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        try:
            from openai import OpenAI

            return OpenAI(api_key=openai_key)
        except Exception:
            return None

    return None


app = FastAPI(title="MediBot", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
engine = HybridSearchEngine()

DEMO_USERS = {
    "dr.mehta": {"password": "doctor", "role": "doctor"},
    "nurse.priya": {"password": "nurse", "role": "nurse"},
    "billing.ravi": {"password": "billing_executive", "role": "billing_executive"},
    "tech.anand": {"password": "technician", "role": "technician"},
    "admin.sys": {"password": "admin", "role": "admin"},
}


class LoginRequest(BaseModel):
    username: str
    password: str


class ChatRequest(BaseModel):
    question: str
    role: str


def _generate_answer(question: str, context: str) -> str:
    client = _get_llm_client()
    if client is None:
        if not context.strip():
            return "I couldn't find relevant evidence in your authorised documents for that question."
        return (
            "Based on the authorised MediAssist documents, the most relevant guidance is: "
            f"{context[:1200]}"
        )

    model_name = "llama-3.1-8b-instant" if os.getenv("GROQ_API_KEY") else "gpt-4o-mini"
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": "You are MediBot, a healthcare internal assistant. Base your answer only on the provided source excerpts and cite them clearly.",
                },
                {"role": "user", "content": f"Question: {question}\n\nSource context:\n{context}"},
            ],
            temperature=0,
        )
        return response.choices[0].message.content or "No answer generated."
    except Exception:
        return "I could not reach the inference API, so I am returning the best grounded summary available from the retrieved evidence."


def _is_analytical_question(question: str) -> bool:
    q = question.lower()
    analytical_terms = [
        "how many",
        "count",
        "which category",
        "what is the total",
        "last month",
        "escalated",
        "open maintenance",
        "most open",
        "billing claims",
        "claims",
        "maintenance tickets",
        "department",
    ]
    return any(term in q for term in analytical_terms)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/login")
def login(payload: LoginRequest) -> dict[str, Any]:
    user = DEMO_USERS.get(payload.username)
    if not user or user["password"] != payload.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {
        "token": f"{payload.username}:{user['role']}",
        "role": user["role"],
    }


@app.get("/collections/{role}")
def collections_for_role(role: str) -> dict[str, Any]:
    if role not in ROLE_COLLECTIONS:
        raise HTTPException(status_code=404, detail="Unknown role")
    return {"role": role, "collections": get_role_access(role)}


@app.post("/chat")
def chat(payload: ChatRequest) -> dict[str, Any]:
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    role = payload.role.strip()
    if role not in ROLE_COLLECTIONS:
        raise HTTPException(status_code=400, detail="Unknown role")

    analytical = _is_analytical_question(question)
    if analytical and role not in {"billing_executive", "admin"}:
        answer = get_rbac_refusal(role)
        return {
            "answer": answer,
            "sources": [],
            "retrieval_type": "hybrid_rag",
            "role": role,
        }

    if analytical and role in {"billing_executive", "admin"}:
        answer = sql_rag_chain(question)
        return {
            "answer": answer,
            "sources": [{"source_document": "mediassist.db", "section_title": "SQL Analytics", "collection": "billing"}],
            "retrieval_type": "sql_rag",
            "role": role,
        }

    hits = engine.search_with_rerank(question, role)
    if not hits:
        answer = get_rbac_refusal(role)
        return {
            "answer": answer,
            "sources": [],
            "retrieval_type": "hybrid_rag",
            "role": role,
        }

    context = "\n\n".join(
        f"Section: {doc['section_title']}\nCollection: {doc['collection']}\n{doc['text']}"
        for doc in hits
    )
    answer = _generate_answer(question, context)
    sources = [
        {
            "source_document": doc["source_document"],
            "section_title": doc["section_title"],
            "collection": doc["collection"],
        }
        for doc in hits
    ]
    return {
        "answer": answer,
        "sources": sources,
        "retrieval_type": "hybrid_rag",
        "role": role,
    }
