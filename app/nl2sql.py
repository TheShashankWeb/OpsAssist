# app/nl2sql.py
# OpsAssist v2.0 — NL2SQL Engine with SQL Guard

import os
import re
import pandas as pd
from dotenv import load_dotenv
from groq import Groq
from app.audit_logger import get_connection, log_action

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ── Schema ──────────────────────────────────────────────────────────────────
DB_SCHEMA = """
Tables in opsassist_db (MySQL) / opsassist.db (SQLite):
1. vendors(vendor_id, vendor_name, sector, contact_email, city, rating)
2. shipments(shipment_id, tracking_number, vendor_id, origin_city,
   destination_city, status, dispatch_date, expected_delivery,
   actual_delivery, weight_kg, sector)
3. inventory(inventory_id, sku_code, product_name, category, sector,
   quantity_in, quantity_out, current_stock, warehouse_location, last_updated)
4. cold_storage_logs(log_id, zone_name, temperature, humidity,
   recorded_at, status, alert_triggered)
5. dispatch_logs(dispatch_id, shipment_id, driver_name, vehicle_number,
   dispatch_time, delivery_time, tat_hours, delivery_status,
   failure_reason, sector)
Relationships:
  shipments.vendor_id = vendors.vendor_id
  dispatch_logs.shipment_id = shipments.shipment_id
"""

# ── Dangerous keywords that must never appear in generated SQL ───────────────
BLOCKED_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER",
    "TRUNCATE", "EXEC", "EXECUTE", "CREATE", "REPLACE",
    "MERGE", "CALL", "GRANT", "REVOKE", "ATTACH"
]


# ── SQL Guard ────────────────────────────────────────────────────────────────
def sql_guard(sql: str) -> tuple[bool, str]:
    """
    Validates generated SQL before execution.
    Returns (is_safe: bool, reason: str)
    """
    if not sql or not sql.strip():
        return False, "Empty SQL generated."

    # Remove SQL comments before checking (-- comment or /* comment */)
    clean = re.sub(r"--[^\n]*", "", sql)
    clean = re.sub(r"/\*.*?\*/", "", clean, flags=re.DOTALL)
    clean_upper = clean.upper()

    # Must start with SELECT
    first_word = clean_upper.strip().split()[0] if clean_upper.strip() else ""
    if first_word != "SELECT":
        return False, f"Only SELECT queries are allowed. Got: {first_word}"

    # Block dangerous keywords
    for keyword in BLOCKED_KEYWORDS:
        pattern = r"\b" + keyword + r"\b"
        if re.search(pattern, clean_upper):
            return False, f"Blocked keyword detected: {keyword}"

    # Block semicolons followed by another statement (SQL chaining)
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    if len(statements) > 1:
        return False, "Multiple SQL statements are not allowed."

    return True, "OK"


# ── LIMIT Enforcer ───────────────────────────────────────────────────────────
def enforce_limit(sql: str, max_rows: int = 100) -> str:
    """
    Adds LIMIT clause if missing or increases it if too large.
    """
    sql_upper = sql.upper()

    if "LIMIT" not in sql_upper:
        sql = sql.rstrip(";").strip() + f" LIMIT {max_rows}"
    else:
        # Check if existing limit exceeds max
        match = re.search(r"LIMIT\s+(\d+)", sql_upper)
        if match:
            existing_limit = int(match.group(1))
            if existing_limit > max_rows:
                sql = re.sub(
                    r"LIMIT\s+\d+", f"LIMIT {max_rows}",
                    sql, flags=re.IGNORECASE
                )
    return sql


# ── SQL Generator ────────────────────────────────────────────────────────────
def generate_sql(question: str, sector: str = "All") -> str:
    sector_filter = (
        f"Add WHERE sector = '{sector}' or JOIN condition for sector = '{sector}'."
        if sector != "All" else ""
    )

    prompt = f"""You are a SQL expert. Given this database schema:
{DB_SCHEMA}

Rules:
- Return ONLY a valid SELECT SQL query.
- No markdown, no backticks, no explanation, no comments.
- Always include LIMIT 100.
- Only use tables and columns from the schema above.
- Do not use INSERT, UPDATE, DELETE, DROP, or any write operation.
{sector_filter}

Question: {question}
SQL:"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=300
    )

    sql = response.choices[0].message.content.strip()

    # Strip markdown if Groq adds it anyway
    sql = sql.replace("```sql", "").replace("```", "").strip()

    # Remove trailing semicolon for safety
    sql = sql.rstrip(";").strip()

    return sql


# ── Main Query Runner ────────────────────────────────────────────────────────
def run_query(
    question: str,
    user: str = "coordinator",
    sector: str = "All"
) -> tuple[pd.DataFrame, str | None, str]:
    """
    Full pipeline: question → SQL → guard → execute → DataFrame
    Returns: (df, error_message, sql)
    """
    sql = ""
    try:
        # Step 1: Generate SQL
        sql = generate_sql(question, sector)

        # Step 2: Run through SQL guard
        is_safe, reason = sql_guard(sql)
        if not is_safe:
            log_action(user, "BLOCKED_QUERY", question, f"BLOCKED: {reason}", sector)
            return pd.DataFrame(), f"Query blocked: {reason}", sql

        # Step 3: Enforce LIMIT
        sql = enforce_limit(sql, max_rows=100)

        # Step 4: Execute
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(sql)
        results = cursor.fetchall()
        df = pd.DataFrame(results)
        cursor.close()
        conn.close()

        # Step 5: Log successful query
        log_action(user, "NL_QUERY", question, f"Rows: {len(df)}", sector)

        return df, None, sql

    except Exception as e:
        log_action(user, "QUERY_ERROR", question, f"Error: {str(e)}", sector)
        return pd.DataFrame(), f"Error: {str(e)}", sql