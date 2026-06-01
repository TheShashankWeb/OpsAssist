# api/routes/query.py
# OpsAssist FastAPI — NL2SQL Query Endpoint

from fastapi import APIRouter, Query
from pydantic import BaseModel
import pandas as pd
import sqlite3
import os
import re
from groq import Groq
from dotenv import load_dotenv
from app.nl2sql import sql_guard, enforce_limit

load_dotenv()

router = APIRouter()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

DB_PATH = "opsassist.db"

SQLITE_SCHEMA = """
Tables (SQLite):
- vendors(vendor_id, vendor_name, sector, contact_email, city, rating)
- shipments(shipment_id, tracking_number, vendor_id, origin_city,
  destination_city, status, dispatch_date, expected_delivery,
  actual_delivery, weight_kg, sector)
- inventory(inventory_id, sku_code, product_name, category, sector,
  quantity_in, quantity_out, current_stock, warehouse_location, last_updated)
- cold_storage_logs(log_id, zone_name, temperature, humidity,
  recorded_at, status, alert_triggered)
- dispatch_logs(dispatch_id, shipment_id, driver_name, vehicle_number,
  dispatch_time, delivery_time, tat_hours, delivery_status,
  failure_reason, sector)
- audit_logs(audit_id, user_name, action_type, query_text,
  result_summary, timestamp, sector)
"""

DESTRUCTIVE_INTENTS = [
    "delete", "remove all", "drop", "truncate",
    "wipe", "erase", "clear all", "destroy", "purge"
]


class QueryRequest(BaseModel):
    question: str
    sector: str = "All"
    user: str = "api_user"


class QueryResponse(BaseModel):
    question: str
    sql: str
    rows: int
    data: list
    error: str | None = None
    blocked: bool = False


@router.post("/query", response_model=QueryResponse, tags=["Query"])
def run_query(request: QueryRequest):
    """
    Convert a natural language question to SQL and execute it.
    Returns query results as JSON.
    Sector filter is applied automatically if provided.
    """
    question = request.question.strip()
    sector = request.sector
    user = request.user

    # Intent guard
    question_lower = question.lower()
    if any(word in question_lower for word in DESTRUCTIVE_INTENTS):
        return QueryResponse(
            question=question,
            sql="",
            rows=0,
            data=[],
            error="Destructive queries are not allowed.",
            blocked=True
        )

    # Generate SQL
    sector_instruction = (
        f"Filter results for sector = '{sector}'."
        if sector != "All" else ""
    )
    prompt = f"""You are a SQLite SQL expert. Given this schema:
{SQLITE_SCHEMA}
Rules:
- Return ONLY a valid SQLite SELECT query.
- No markdown, no backticks, no explanation.
- Always include LIMIT 100.
- Do not use INSERT, UPDATE, DELETE, DROP or any write operation.
{sector_instruction}
Question: {question}
SQL:"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0
    )
    sql = response.choices[0].message.content.strip()
    sql = sql.replace("```sql", "").replace("```", "").strip().rstrip(";")

    # SQL Guard
    is_safe, reason = sql_guard(sql)
    if not is_safe:
        return QueryResponse(
            question=question,
            sql=sql,
            rows=0,
            data=[],
            error=f"Query blocked: {reason}",
            blocked=True
        )

    # Enforce LIMIT
    sql = enforce_limit(sql, max_rows=100)

    # Execute
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        conn.close()
        data = [dict(row) for row in rows]
        return QueryResponse(
            question=question,
            sql=sql,
            rows=len(data),
            data=data
        )
    except Exception as e:
        return QueryResponse(
            question=question,
            sql=sql,
            rows=0,
            data=[],
            error=str(e)
        )
