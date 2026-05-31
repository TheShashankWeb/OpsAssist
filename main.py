# main.py
# OpsAssist — Streamlit App Entry Point

import streamlit as st

# --- Page Config (must be first Streamlit call) ---
st.set_page_config(
    page_title="OpsAssist",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Imports ---
import pandas as pd
from app.nl2sql import run_query
from app.report_builder import (
    build_daily_dispatch_report,
    build_stock_summary_report,
    build_vendor_scorecard
)
from app.alert_engine import run_all_alerts
from app.escalation import draft_escalation_email
from app.audit_logger import log_action

# --- Session State Init ---
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

# --- Sidebar ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/truck.png", width=60)
    st.title("OpsAssist")
    st.caption("AI-Powered Operations Co-pilot")
    st.divider()

    st.session_state.user_name = st.text_input(
        "Your Name", value=st.session_state.user_name
    )

    st.session_state.sector = st.selectbox(
        "Filter by Sector",
        ["All", "Logistics", "Warehouse", "Cold Storage",
         "Steel", "Courier", "Port", "Startup"]
    )

    st.divider()
    st.markdown("**Navigation**")
    page = st.radio(
        "Go to",
        ["💬 Query Assistant", "📊 MIS Reports",
         "🚨 Alert Feed", "📧 Escalation", "🗂️ Audit Trail"],
        label_visibility="collapsed"
    )

# --- Sector filter value ---
sector_val = None if st.session_state.sector == "All" else st.session_state.sector

# ================================================================
# PAGE 1 — QUERY ASSISTANT
# ================================================================
if page == "💬 Query Assistant":
    st.title("💬 Query Assistant")
    st.caption("Ask anything about your operations in plain English.")

    # Chat history display
    for entry in st.session_state.chat_history:
        with st.chat_message("user"):
            st.write(entry["question"])
        with st.chat_message("assistant"):
            if entry["error"]:
                st.error(entry["error"])
            else:
                st.dataframe(entry["df"], use_container_width=True)
                st.code(entry["sql"], language="sql")

    # Query input
    user_query = st.chat_input("e.g. Show top 5 delayed shipments this week...")

    if user_query:
        with st.spinner("Thinking..."):
            df, error, sql = run_query(user_query)

        with st.chat_message("user"):
            st.write(user_query)

        with st.chat_message("assistant"):
            if error:
                st.error(f"Error: {error}")
            else:
                st.dataframe(df, use_container_width=True)
                st.code(sql, language="sql")

                # Show bar chart if numeric column exists
                numeric_cols = df.select_dtypes(include="number").columns.tolist()
                if len(df) > 1 and len(numeric_cols) > 0:
                    chart_col = numeric_cols[0]
                    label_col = df.columns[0]
                    if label_col != chart_col:
                        chart_df = df[[label_col, chart_col]].set_index(label_col)
                        st.bar_chart(chart_df)

        # Save to chat history
        st.session_state.chat_history.append({
            "question": user_query,
            "df": df if not error else pd.DataFrame(),
            "sql": sql or "",
            "error": error
        })

        # Log to audit
        log_action(
            user_name=st.session_state.user_name,
            action_type="NL_QUERY",
            query_text=user_query,
            result_summary=f"{len(df)} rows returned" if not error else f"Error: {error}",
            sector=st.session_state.sector
        )

    if st.session_state.chat_history:
        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_history = []
            st.rerun()

# ================================================================
# PAGE 2 — MIS REPORTS
# ================================================================
elif page == "📊 MIS Reports":
    st.title("📊 MIS Reports")
    st.caption("Auto-generated Excel reports — download instantly.")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("🚛 Daily Dispatch")
        st.write("Driver-wise delivery performance and TAT summary.")
        if st.button("Generate Report", key="dispatch"):
            with st.spinner("Building report..."):
                path = build_daily_dispatch_report()
            with open(path, "rb") as f:
                st.download_button(
                    "⬇️ Download Excel",
                    f,
                    file_name="dispatch_report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            st.success("Ready!")

    with col2:
        st.subheader("📦 Inventory")
        st.write("Stock levels, slow-moving SKUs and category breakdown.")
        if st.button("Generate Report", key="inventory"):
            with st.spinner("Building report..."):
                path = build_stock_summary_report()
            with open(path, "rb") as f:
                st.download_button(
                    "⬇️ Download Excel",
                    f,
                    file_name="inventory_report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            st.success("Ready!")

    with col3:
        st.subheader("🏆 Vendor Scorecard")
        st.write("Vendor ratings, TAT performance and sector breakdown.")
        if st.button("Generate Report", key="cold"):
            with st.spinner("Building report..."):
                path = build_vendor_scorecard()
            with open(path, "rb") as f:
                st.download_button(
                    "⬇️ Download Excel",
                    f,
                    file_name="cold_storage_report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            st.success("Ready!")

# ================================================================
# PAGE 3 — ALERT FEED
# ================================================================
elif page == "🚨 Alert Feed":
    st.title("🚨 AI Alert Feed")
    st.caption("Live operational alerts generated by AI.")

    if st.button("🔄 Refresh Alerts"):
        with st.spinner("Scanning operations data..."):
            st.session_state.alerts = run_all_alerts()

    if not st.session_state.alerts:
        st.info("Click 'Refresh Alerts' to scan for issues.")
    else:
        st.success(f"{len(st.session_state.alerts)} alerts detected.")
        st.divider()

        type_colors = {
            "Vendor TAT Decline": "🟠",
            "Cold Storage Breach": "🔴",
            "Shipment Ageing": "🟡",
            "Slow-Moving SKU": "🔵"
        }

        for alert in st.session_state.alerts:
            icon = type_colors.get(alert["type"], "⚪")
            with st.expander(f"{icon} {alert['type']} — {alert.get('vendor') or alert.get('zone') or alert.get('tracking_number') or alert.get('sku_code', '')}"):
                st.write(alert["message"])
                st.caption(f"Sector: {alert.get('sector', 'N/A')}")

# ================================================================
# PAGE 4 — ESCALATION
# ================================================================
elif page == "📧 Escalation":
    st.title("📧 Escalation Email Drafter")
    st.caption("AI drafts a data-backed escalation email from live DB.")

    recipient = st.text_input("Recipient Name", value="Operations Manager")

    if st.button("✍️ Draft Escalation Email"):
        with st.spinner("Fetching data and drafting email..."):
            st.session_state.escalation_draft = draft_escalation_email(
                sector=sector_val,
                recipient_name=recipient,
                sender_name=st.session_state.user_name
            )

    if st.session_state.escalation_draft:
        draft = st.session_state.escalation_draft
        st.subheader("📨 Draft Preview")
        st.text_input("Subject", value=draft["subject"])
        st.text_area("Body", value=draft["body"], height=350)

        st.divider()
        st.subheader("📤 Send Email")
        to_email = st.text_input("Send to (email address)")

        if st.button("🚀 Send Now"):
            if to_email:
                from app.escalation import send_escalation_email
                with st.spinner("Sending..."):
                    ok = send_escalation_email(to_email, draft["subject"], draft["body"])
                if ok:
                    st.success(f"Email sent to {to_email}!")
                else:
                    st.error("Send failed. Check SMTP credentials in .env")
            else:
                st.warning("Enter a recipient email address.")

# ================================================================
# PAGE 5 — AUDIT TRAIL
# ================================================================
elif page == "🗂️ Audit Trail":
    st.title("🗂️ Audit Trail")
    st.caption("All queries and actions logged automatically.")

    from app.audit_logger import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_name, action_type, query_text, result_summary, timestamp, sector "
        "FROM audit_logs ORDER BY timestamp DESC LIMIT 100"
    )
    df = pd.DataFrame(cursor.fetchall())
    cursor.close()
    conn.close()

    st.dataframe(df, use_container_width=True)