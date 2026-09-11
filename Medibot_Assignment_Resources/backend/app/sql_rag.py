from __future__ import annotations

import json
import os
import re
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "mediassist_data" / "mediassist_data" / "db" / "mediassist.db"


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


def _generate_text(prompt: str) -> str:
    client = _get_llm_client()
    if client is None:
        return ""

    model_name = "llama-3.1-8b-instant" if os.getenv("GROQ_API_KEY") else "gpt-4o-mini"
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        return response.choices[0].message.content or ""
    except Exception:
        return ""


def _extract_sql(raw_sql: str) -> str:
    text = raw_sql.strip()
    text = text.replace("```sql", "").replace("```", "")
    if "SELECT" in text.upper():
        match = re.search(r"SELECT.*;?", text, re.I | re.S)
        if match:
            return match.group(0).strip("; ") + ";"
    return text.strip("; ") + ";"


def _rule_based_sql(question: str) -> str:
    q = question.lower()
    if "open maintenance" in q or "maintenance tickets" in q or "category" in q or "most open" in q:
        return (
            "SELECT category, COUNT(*) AS ticket_count FROM maintenance_tickets "
            "WHERE status = 'Open' GROUP BY category ORDER BY ticket_count DESC LIMIT 1;"
        )
    if "escalated" in q or "claim" in q or "last month" in q:
        return (
            "SELECT COUNT(*) AS escalated_claims FROM claims "
            "WHERE status = 'Escalated' AND claim_date >= date('now', '-1 month');"
        )
    if "department" in q or "status" in q:
        return "SELECT department, COUNT(*) AS total_claims FROM claims GROUP BY department ORDER BY total_claims DESC LIMIT 5;"
    return "SELECT COUNT(*) AS total_claims FROM claims;"


def sql_rag_chain(question: str) -> str:
    """Translate the question to SQL, extract only the SQL, run it, and answer in English."""
    translation_prompt = (
        "Convert this user question into a single SQLite SQL statement. Return only SQL.\n"
        f"Question: {question}\n"
        "Use the tables claims and maintenance_tickets."
    )
    raw_sql = _generate_text(translation_prompt) or _rule_based_sql(question)
    sql_query = _extract_sql(raw_sql)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(sql_query).fetchall()
    finally:
        conn.close()

    result_json = json.dumps([dict(row) for row in rows], default=str)
    summary_prompt = (
        "Answer the user's question in plain English using this SQL result.\n"
        f"Question: {question}\n"
        f"SQL result: {result_json}"
    )
    answer = _generate_text(summary_prompt)
    if answer:
        return answer

    if not rows:
        return "There are no matching records for that analytical question."
    if len(rows) == 1:
        first = dict(rows[0])
        value = next(iter(first.values()))
        return f"The analysis shows {value}."
    return f"The database result is: {result_json}"
