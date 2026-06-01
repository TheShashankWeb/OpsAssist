# main_cloud.py
# OpsAssist v2.0 — Cloud Entry Point (SQLite + SQL Guard)

import streamlit as st

st.set_page_config(
    page_title="OpsAssist",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded"
)

import pandas as pd
import sqlite3
from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()

# ── Init SQLite DB ───────────────────────────────────────────────────────────
from database.init_sqlite import init_db, DB_PATH
init_db()

# ── Import guarded NL2SQL engine ─────────────────────────────────────────────
# This replaces the old duplicate run_nl_query() that had no SQL guard
from app.nl2sql import sql_guard, enforce_limit

# ── Groq client ──────────────────────────────────────────────────────────────
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ── DB helper ────────────────────────────────────────────────────────────────
def db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

# ── Schema (SQLite version) ──────────────────────────────────────────────────
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

# ── NL2SQL with SQL Guard (cloud version using SQLite) ───────────────────────
def run_nl_query(question: str, sector: str = "All"):
    """
    Generates SQL via Groq, runs through SQL guard, executes on SQLite.
    Sector filter is now properly wired into the prompt.
    """
    # ── Intent Guard — block destructive user intent ─────────────────────
    DESTRUCTIVE_INTENTS = [
        "delete", "remove all", "drop", "truncate", "wipe",
        "erase", "clear all", "destroy", "purge"
    ]
    question_lower = question.lower()
    if any(word in question_lower for word in DESTRUCTIVE_INTENTS):
        return (
            pd.DataFrame(),
            "⚠️ This query was blocked. OpsAssist only supports read operations.",
            ""
        )

    sector_instruction = (
        f"Filter results for sector = '{sector}' using WHERE or JOIN as appropriate."
        if sector != "All" else ""
    )

    prompt = f"""You are a SQLite SQL expert. Given this schema:
{SQLITE_SCHEMA}

Rules:
- Return ONLY a valid SQLite SELECT query.
- No markdown, no backticks, no explanation, no comments.
- Always include LIMIT 100.
- Only use tables and columns from the schema above.
- Do not use INSERT, UPDATE, DELETE, DROP, or any write operation.
- Use julianday() for date differences in SQLite, not DATEDIFF().
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
    sql = sql.replace("```sql", "").replace("```", "").strip()
    sql = sql.rstrip(";").strip()

    # ── SQL Guard ────────────────────────────────────────────────────────────
    is_safe, reason = sql_guard(sql)
    if not is_safe:
        _log_audit(st.session_state.user_name, "BLOCKED_QUERY", question,
                   f"BLOCKED: {reason}", sector)
        return pd.DataFrame(), f"Query blocked: {reason}", sql

    # ── Enforce LIMIT ────────────────────────────────────────────────────────
    sql = enforce_limit(sql, max_rows=100)

    # ── Execute ──────────────────────────────────────────────────────────────
    try:
        conn = db()
        df = pd.read_sql_query(sql, conn)
        conn.close()
        _log_audit(st.session_state.user_name, "NL_QUERY", question,
                   f"{len(df)} rows", sector)
        return df, None, sql
    except Exception as e:
        _log_audit(st.session_state.user_name, "QUERY_ERROR", question,
                   f"Error: {str(e)}", sector)
        return pd.DataFrame(), f"Error: {str(e)}", sql


# ── Audit Logger (SQLite version) ────────────────────────────────────────────
def _log_audit(user, action, query, result, sector):
    try:
        conn = db()
        conn.execute(
            """INSERT INTO audit_logs
               (user_name, action_type, query_text, result_summary, timestamp, sector)
               VALUES (?,?,?,?,?,?)""",
            (user, action, query, str(result)[:500],
             pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"), sector)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Audit log error: {e}")


# ── Alert Engine (SQLite version) ────────────────────────────────────────────
def get_alerts(sector: str = "All"):
    alerts = []
    conn = db()

    sector_filter = f"AND sector = '{sector}'" if sector != "All" else ""

    # Vendor TAT Decline
    df = pd.read_sql_query(f"""
        SELECT driver_name, ROUND(AVG(tat_hours),1) as avg_tat, sector
        FROM dispatch_logs
        WHERE tat_hours > 48 {sector_filter}
        GROUP BY driver_name, sector
        ORDER BY avg_tat DESC LIMIT 5
    """, conn)
    for _, r in df.iterrows():
        alerts.append({
            "type": "Vendor TAT Decline",
            "vendor": r["driver_name"],
            "sector": r["sector"],
            "message": f"Driver {r['driver_name']} averaging {r['avg_tat']} hrs TAT — exceeds 48hr SLA."
        })

    # Cold Storage Breach
    df = pd.read_sql_query("""
        SELECT zone_name, temperature, humidity, recorded_at
        FROM cold_storage_logs
        WHERE alert_triggered = 1
        ORDER BY recorded_at DESC LIMIT 5
    """, conn)
    for _, r in df.iterrows():
        alerts.append({
            "type": "Cold Storage Breach",
            "zone": r["zone_name"],
            "sector": "Cold Storage",
            "message": f"Zone {r['zone_name']} breached: {r['temperature']}°C / {r['humidity']}% humidity."
        })

    # Shipment Ageing
    df = pd.read_sql_query(f"""
        SELECT tracking_number, origin_city, destination_city, sector,
               CAST((julianday('now') - julianday(dispatch_date)) AS INTEGER) as days_in_transit
        FROM shipments
        WHERE status NOT IN ('Delivered','Cancelled')
        AND CAST((julianday('now') - julianday(dispatch_date)) AS INTEGER) > 7
        {sector_filter}
        ORDER BY days_in_transit DESC LIMIT 5
    """, conn)
    for _, r in df.iterrows():
        alerts.append({
            "type": "Shipment Ageing",
            "tracking_number": r["tracking_number"],
            "sector": r["sector"],
            "message": f"Shipment {r['tracking_number']} stuck {r['days_in_transit']} days — {r['origin_city']} to {r['destination_city']}."
        })

    # Slow-Moving SKUs
    df = pd.read_sql_query(f"""
        SELECT sku_code, product_name, sector, current_stock, quantity_out
        FROM inventory
        WHERE current_stock > 50 AND quantity_out < 10 {sector_filter}
        ORDER BY current_stock DESC LIMIT 5
    """, conn)
    for _, r in df.iterrows():
        alerts.append({
            "type": "Slow-Moving SKU",
            "sku_code": r["sku_code"],
            "sector": r["sector"],
            "message": f"SKU {r['sku_code']} has {r['current_stock']} units — only {r['quantity_out']} moved out."
        })

    conn.close()
    return alerts


# ── Escalation Email Drafter ─────────────────────────────────────────────────
def draft_email(recipient="Operations Manager", sender="OpsAssist", sector="All"):
    conn = db()
    sector_filter = f"AND sector = '{sector}'" if sector != "All" else ""

    delayed = pd.read_sql_query(
        f"SELECT COUNT(*) as c FROM shipments WHERE status NOT IN ('Delivered','Cancelled') {sector_filter}",
        conn
    ).iloc[0]["c"]

    top_drivers = pd.read_sql_query(
        f"""SELECT driver_name, ROUND(AVG(tat_hours),1) as avg_tat
            FROM dispatch_logs WHERE tat_hours > 48 {sector_filter}
            GROUP BY driver_name ORDER BY avg_tat DESC LIMIT 3""",
        conn
    )

    cold = pd.read_sql_query(
        """SELECT zone_name, COUNT(*) as cnt FROM cold_storage_logs
           WHERE alert_triggered=1 GROUP BY zone_name
           ORDER BY cnt DESC LIMIT 3""",
        conn
    )
    conn.close()

    driver_lines = "\n".join(
        [f"  - {r['driver_name']}: {r['avg_tat']} hrs" for _, r in top_drivers.iterrows()]
    ) or "  - No TAT breach data"

    cold_lines = "\n".join(
        [f"  - {r['zone_name']}: {r['cnt']} breaches" for _, r in cold.iterrows()]
    ) or "  - No cold storage breach data"

    sector_label = f"Sector: {sector}" if sector != "All" else "All Sectors"

    prompt = f"""Write a professional operations escalation email.
To: {recipient}
From: {sender}
Scope: {sector_label}
Live Data:
- Undelivered/delayed shipments: {delayed}
- Top TAT breach drivers: {driver_lines}
- Cold storage breach zones: {cold_lines}

Format exactly as:
SUBJECT: <subject line>
BODY:
<email body>"""

    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
        temperature=0.4
    )
    raw = resp.choices[0].message.content.strip()
    subject = "Escalation: Immediate Attention Required"
    body = raw

    if "SUBJECT:" in raw:
        lines = raw.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("SUBJECT:"):
                subject = line.replace("SUBJECT:", "").strip()
            if line.startswith("BODY:"):
                body = "\n".join(lines[i+1:]).strip()
                break

    return {"subject": subject, "body": body}


# ── Session State ─────────────────────────────────────────────────────────────
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "alerts" not in st.session_state:
    st.session_state.alerts = []
if "escalation_draft" not in st.session_state:
    st.session_state.escalation_draft = None
if "user_name" not in st.session_state:
    st.session_state.user_name = "Coordinator"
if "sector" not in st.session_state:
    st.session_state.sector = "All"
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "login_user" not in st.session_state:
    st.session_state.login_user = None


# ── Login Gate ────────────────────────────────────────────────────────────────
import hashlib

def verify_login(username: str, password: str) -> dict | None:
    """Check credentials against users table. Returns user dict or None."""
    pwd_hash = hashlib.sha256(password.encode()).hexdigest()
    conn = db()
    cur = conn.cursor()
    cur.execute(
        "SELECT username, role, full_name FROM users WHERE username=? AND password_hash=?",
        (username, pwd_hash)
    )
    row = cur.fetchone()
    conn.close()
    if row:
        return {"username": row[0], "role": row[1], "full_name": row[2]}
    return None


def show_login_page():
    """Renders the login screen."""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("https://img.icons8.com/fluency/96/truck.png", width=80)
        st.title("OpsAssist")
        st.caption("AI-Powered Operations Co-pilot v2.0")
        st.divider()
        st.subheader("🔐 Login")

        username = st.text_input("Username", placeholder="Enter username")
        password = st.text_input("Password", type="password", placeholder="Enter password")

        if st.button("Login", use_container_width=True, type="primary"):
            if not username or not password:
                st.warning("Please enter both username and password.")
            else:
                user = verify_login(username.strip(), password.strip())
                if user:
                    st.session_state.logged_in = True
                    st.session_state.login_user = user["username"]
                    st.session_state.user_name = user["full_name"]
                    st.session_state.user_role = user["role"]
                    _log_audit(user["username"], "LOGIN", "User logged in", "Success", "All")
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
                    _log_audit(username, "LOGIN_FAILED", "Failed login attempt", "Failed", "All")

        st.divider()
        st.caption("Default credentials for demo:")
        st.code("admin / admin123\ncoordinator / coord123\nviewer / view123")


# Show login page if not authenticated
if not st.session_state.logged_in:
    show_login_page()
    st.stop()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/truck.png", width=60)
    st.title("OpsAssist")
    st.caption("AI-Powered Operations Co-pilot v2.0")
    st.divider()
    st.session_state.user_name = st.text_input(
        "Your Name", value=st.session_state.user_name
    )
    st.session_state.sector = st.selectbox(
        "🏭 Filter by Sector",
        ["All", "Logistics", "Warehouse", "Cold Storage",
         "Steel", "Courier", "Port", "Startup"]
    )
    st.divider()
    page = st.radio(
        "Go to",
        ["💬 Query Assistant", "🚨 Alert Feed",
         "📧 Escalation", "🗂️ Audit Trail"],
        label_visibility="collapsed"
    )
    st.divider()
    st.divider()
    st.caption(f"👤 **{st.session_state.user_name}**")
    st.caption(f"Role: `{st.session_state.user_role}`")
    st.caption(f"Sector: **{st.session_state.sector}**")
    st.caption("v2.0 — SQL Guard Active 🛡️")
    st.divider()
    if st.button("🚪 Logout", use_container_width=True):
        _log_audit(st.session_state.login_user, "LOGOUT", "User logged out", "Success", "All")
        for key in ["logged_in", "login_user", "user_name", "user_role",
                    "chat_history", "alerts", "escalation_draft"]:
            st.session_state[key] = None if key not in ["logged_in"] else False
        st.rerun()


# ── Page: Query Assistant ─────────────────────────────────────────────────────
if page == "💬 Query Assistant":
    st.title("💬 Query Assistant")
    st.caption(
        f"Ask anything in plain English. "
        f"Sector filter: **{st.session_state.sector}** | "
        f"SQL Guard: 🛡️ Active"
    )

    for entry in st.session_state.chat_history:
        with st.chat_message("user"):
            st.write(entry["question"])
        with st.chat_message("assistant"):
            if entry["error"]:
                st.error(entry["error"])
            else:
                st.dataframe(entry["df"], use_container_width=True)
                st.code(entry["sql"], language="sql")

    user_query = st.chat_input("e.g. Show top 5 delayed shipments in Logistics sector...")
    if user_query:
        with st.spinner("Thinking..."):
            df, error, sql = run_nl_query(
                user_query,
                sector=st.session_state.sector   # ← Sector now wired
            )
        with st.chat_message("user"):
            st.write(user_query)
        with st.chat_message("assistant"):
            if error:
                st.error(f"{error}")
            else:
                st.dataframe(df, use_container_width=True)
                st.code(sql, language="sql")

                # ── CSV Export ───────────────────────────────────────────
                csv_data = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="⬇️ Download CSV",
                    data=csv_data,
                    file_name=f"opsassist_result_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    key=f"csv_{pd.Timestamp.now().strftime('%H%M%S%f')}"
                )

                # ── Bar Chart ────────────────────────────────────────────
                numeric_cols = df.select_dtypes(include="number").columns.tolist()
                if len(df) > 1 and len(numeric_cols) > 0 and df.columns[0] != numeric_cols[0]:
                    st.bar_chart(
                        df[[df.columns[0], numeric_cols[0]]].set_index(df.columns[0])
                    )
        st.session_state.chat_history.append({
            "question": user_query,
            "df": df,
            "sql": sql or "",
            "error": error
        })

    if st.session_state.chat_history:
        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_history = []
            st.rerun()


# ── Page: Alert Feed ──────────────────────────────────────────────────────────
elif page == "🚨 Alert Feed":
    st.title("🚨 AI Alert Feed")
    st.caption(
        f"Live operational alerts. "
        f"Sector filter: **{st.session_state.sector}**"
    )

    if st.button("🔄 Refresh Alerts"):
        with st.spinner("Scanning operations data..."):
            st.session_state.alerts = get_alerts(
                sector=st.session_state.sector  # ← Sector now wired
            )

    if not st.session_state.alerts:
        st.info("Click 'Refresh Alerts' to scan for issues.")
    else:
        st.success(f"{len(st.session_state.alerts)} alerts detected.")
        st.divider()
        colors = {
            "Vendor TAT Decline": "🟠",
            "Cold Storage Breach": "🔴",
            "Shipment Ageing": "🟡",
            "Slow-Moving SKU": "🔵"
        }
        for a in st.session_state.alerts:
            icon = colors.get(a["type"], "⚪")
            label = (a.get("vendor") or a.get("zone") or
                     a.get("tracking_number") or a.get("sku_code", ""))
            with st.expander(f"{icon} {a['type']} — {label}"):
                st.write(a["message"])
                st.caption(f"Sector: {a.get('sector', 'N/A')}")


# ── Page: Escalation ──────────────────────────────────────────────────────────
elif page == "📧 Escalation":
    st.title("📧 Escalation Email Drafter")
    st.caption(f"Drafting for sector: **{st.session_state.sector}**")

    recipient = st.text_input("Recipient Name", value="Operations Manager")

    if st.button("✍️ Draft Escalation Email"):
        with st.spinner("Fetching live data and drafting..."):
            st.session_state.escalation_draft = draft_email(
                recipient=recipient,
                sender=st.session_state.user_name,
                sector=st.session_state.sector   # ← Sector now wired
            )

    if st.session_state.escalation_draft:
        d = st.session_state.escalation_draft
        st.subheader("📨 Draft Preview")
        st.text_input("Subject", value=d["subject"])
        st.text_area("Body", value=d["body"], height=350)


# ── Page: Audit Trail ─────────────────────────────────────────────────────────
elif page == "🗂️ Audit Trail":
    st.title("🗂️ Audit Trail")
    st.caption("All queries, blocks and errors logged automatically.")

    conn = db()
    df = pd.read_sql_query(
        """SELECT user_name, action_type, query_text,
                  result_summary, timestamp, sector
           FROM audit_logs
           ORDER BY timestamp DESC LIMIT 100""",
        conn
    )
    conn.close()

    if df.empty:
        st.info("No audit logs yet. Use the Query Assistant to generate logs.")
    else:
        st.dataframe(df, use_container_width=True)