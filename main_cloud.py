# main_cloud.py
# OpsAssist — Cloud Entry Point (SQLite version)

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

# Init SQLite DB on first run
from database.init_sqlite import init_db, DB_PATH
init_db()

# Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Session state
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


def db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def run_nl_query(question):
    schema = """
    Tables:
    - vendors(vendor_id, vendor_name, sector, contact_email, city, rating)
    - shipments(shipment_id, tracking_number, vendor_id, origin_city, destination_city, status, dispatch_date, expected_delivery, actual_delivery, weight_kg, sector)
    - inventory(inventory_id, sku_code, product_name, category, sector, quantity_in, quantity_out, current_stock, warehouse_location, last_updated)
    - cold_storage_logs(log_id, zone_name, temperature, humidity, recorded_at, status, alert_triggered)
    - dispatch_logs(dispatch_id, shipment_id, driver_name, vehicle_number, dispatch_time, delivery_time, tat_hours, delivery_status, failure_reason, sector)
    - audit_logs(audit_id, user_name, action_type, query_text, result_summary, timestamp, sector)
    Database: SQLite
    """
    prompt = f"""You are a SQL expert. Convert this question to a valid SQLite SQL query.
Question: {question}
{schema}
Return ONLY the SQL query, nothing else. No explanation, no markdown, no backticks."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0.1
    )
    sql = response.choices[0].message.content.strip()
    sql = sql.replace("```sql", "").replace("```", "").strip()

    try:
        conn = db()
        df = pd.read_sql_query(sql, conn)
        conn.close()
        return df, None, sql
    except Exception as e:
        return pd.DataFrame(), str(e), sql


def get_alerts():
    alerts = []
    conn = db()

    # Vendor TAT
    df = pd.read_sql_query("""
        SELECT driver_name, ROUND(AVG(tat_hours),1) as avg_tat, sector
        FROM dispatch_logs WHERE tat_hours > 48
        GROUP BY driver_name, sector ORDER BY avg_tat DESC LIMIT 5
    """, conn)
    for _, r in df.iterrows():
        alerts.append({
            "type": "Vendor TAT Decline", "vendor": r["driver_name"],
            "sector": r["sector"],
            "message": f"Driver {r['driver_name']} averaging {r['avg_tat']} hrs TAT — exceeds 48hr SLA."
        })

    # Cold storage
    df = pd.read_sql_query("""
        SELECT zone_name, temperature, humidity, recorded_at
        FROM cold_storage_logs WHERE alert_triggered=1
        ORDER BY recorded_at DESC LIMIT 5
    """, conn)
    for _, r in df.iterrows():
        alerts.append({
            "type": "Cold Storage Breach", "zone": r["zone_name"],
            "sector": "Cold Storage",
            "message": f"Zone {r['zone_name']} breached: {r['temperature']}°C / {r['humidity']}% humidity."
        })

    # Shipment ageing
    df = pd.read_sql_query("""
        SELECT tracking_number, origin_city, destination_city, sector, dispatch_date,
        CAST((julianday('now') - julianday(dispatch_date)) AS INTEGER) as days_in_transit
        FROM shipments WHERE status NOT IN ('Delivered','Cancelled')
        AND days_in_transit > 7 ORDER BY days_in_transit DESC LIMIT 5
    """, conn)
    for _, r in df.iterrows():
        alerts.append({
            "type": "Shipment Ageing", "tracking_number": r["tracking_number"],
            "sector": r["sector"],
            "message": f"Shipment {r['tracking_number']} stuck {r['days_in_transit']} days — {r['origin_city']} to {r['destination_city']}."
        })

    # Slow SKUs
    df = pd.read_sql_query("""
        SELECT sku_code, product_name, sector, current_stock, quantity_out
        FROM inventory WHERE current_stock > 50 AND quantity_out < 10
        ORDER BY current_stock DESC LIMIT 5
    """, conn)
    for _, r in df.iterrows():
        alerts.append({
            "type": "Slow-Moving SKU", "sku_code": r["sku_code"],
            "sector": r["sector"],
            "message": f"SKU {r['sku_code']} has {r['current_stock']} units with only {r['quantity_out']} moved out."
        })

    conn.close()
    return alerts


def draft_email(recipient="Operations Manager", sender="OpsAssist"):
    conn = db()
    delayed = pd.read_sql_query(
        "SELECT COUNT(*) as c FROM shipments WHERE status NOT IN ('Delivered','Cancelled')", conn
    ).iloc[0]["c"]
    top_vendors = pd.read_sql_query(
        "SELECT driver_name, ROUND(AVG(tat_hours),1) as avg_tat FROM dispatch_logs WHERE tat_hours>48 GROUP BY driver_name ORDER BY avg_tat DESC LIMIT 3", conn
    )
    cold = pd.read_sql_query(
        "SELECT zone_name, COUNT(*) as cnt FROM cold_storage_logs WHERE alert_triggered=1 GROUP BY zone_name ORDER BY cnt DESC LIMIT 3", conn
    )
    conn.close()

    vendor_lines = "\n".join([f"  - {r['driver_name']}: {r['avg_tat']} hrs" for _, r in top_vendors.iterrows()])
    cold_lines = "\n".join([f"  - {r['zone_name']}: {r['cnt']} breaches" for _, r in cold.iterrows()])

    prompt = f"""Write a professional escalation email.
To: {recipient}
From: {sender}
Data:
- Undelivered shipments: {delayed}
- TAT breaches: {vendor_lines}
- Cold storage breaches: {cold_lines}
Format: SUBJECT: <subject>
BODY:
<body>"""

    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500, temperature=0.5
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


# ── Sidebar ──
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/truck.png", width=60)
    st.title("OpsAssist")
    st.caption("AI-Powered Operations Co-pilot")
    st.divider()
    st.session_state.user_name = st.text_input("Your Name", value=st.session_state.user_name)
    st.session_state.sector = st.selectbox("Filter by Sector",
        ["All","Logistics","Warehouse","Cold Storage","Steel","Courier","Port","Startup"])
    st.divider()
    page = st.radio("Go to", ["💬 Query Assistant","🚨 Alert Feed","📧 Escalation","🗂️ Audit Trail"],
                    label_visibility="collapsed")

# ── Pages ──
if page == "💬 Query Assistant":
    st.title("💬 Query Assistant")
    st.caption("Ask anything about your operations in plain English.")

    for entry in st.session_state.chat_history:
        with st.chat_message("user"):
            st.write(entry["question"])
        with st.chat_message("assistant"):
            if entry["error"]:
                st.error(entry["error"])
            else:
                st.dataframe(entry["df"], use_container_width=True)
                st.code(entry["sql"], language="sql")

    user_query = st.chat_input("e.g. Show top 5 delayed shipments...")
    if user_query:
        with st.spinner("Thinking..."):
            df, error, sql = run_nl_query(user_query)
        with st.chat_message("user"):
            st.write(user_query)
        with st.chat_message("assistant"):
            if error:
                st.error(f"Error: {error}")
            else:
                st.dataframe(df, use_container_width=True)
                st.code(sql, language="sql")
                numeric_cols = df.select_dtypes(include="number").columns.tolist()
                if len(df) > 1 and len(numeric_cols) > 0 and df.columns[0] != numeric_cols[0]:
                    st.bar_chart(df[[df.columns[0], numeric_cols[0]]].set_index(df.columns[0]))
        st.session_state.chat_history.append({"question": user_query, "df": df, "sql": sql or "", "error": error})

        # Log to audit
        conn = db()
        conn.execute(
            "INSERT INTO audit_logs (user_name, action_type, query_text, result_summary, timestamp, sector) VALUES (?,?,?,?,?,?)",
            (st.session_state.user_name, "NL_QUERY", user_query,
             f"{len(df)} rows" if not error else f"Error: {error}",
             pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"), st.session_state.sector)
        )
        conn.commit()
        conn.close()

    if st.session_state.chat_history:
        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_history = []
            st.rerun()

elif page == "🚨 Alert Feed":
    st.title("🚨 AI Alert Feed")
    st.caption("Live operational alerts from your data.")
    if st.button("🔄 Refresh Alerts"):
        with st.spinner("Scanning..."):
            st.session_state.alerts = get_alerts()
    if not st.session_state.alerts:
        st.info("Click 'Refresh Alerts' to scan for issues.")
    else:
        st.success(f"{len(st.session_state.alerts)} alerts detected.")
        colors = {"Vendor TAT Decline":"🟠","Cold Storage Breach":"🔴","Shipment Ageing":"🟡","Slow-Moving SKU":"🔵"}
        for a in st.session_state.alerts:
            icon = colors.get(a["type"], "⚪")
            label = a.get("vendor") or a.get("zone") or a.get("tracking_number") or a.get("sku_code","")
            with st.expander(f"{icon} {a['type']} — {label}"):
                st.write(a["message"])
                st.caption(f"Sector: {a.get('sector','N/A')}")

elif page == "📧 Escalation":
    st.title("📧 Escalation Email Drafter")
    recipient = st.text_input("Recipient Name", value="Operations Manager")
    if st.button("✍️ Draft Escalation Email"):
        with st.spinner("Drafting..."):
            st.session_state.escalation_draft = draft_email(recipient, st.session_state.user_name)
    if st.session_state.escalation_draft:
        d = st.session_state.escalation_draft
        st.subheader("📨 Draft Preview")
        st.text_input("Subject", value=d["subject"])
        st.text_area("Body", value=d["body"], height=350)

elif page == "🗂️ Audit Trail":
    st.title("🗂️ Audit Trail")
    conn = db()
    df = pd.read_sql_query(
        "SELECT user_name, action_type, query_text, result_summary, timestamp, sector FROM audit_logs ORDER BY timestamp DESC LIMIT 100",
        conn
    )
    conn.close()
    st.dataframe(df, use_container_width=True)
