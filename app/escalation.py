# app/escalation.py
# OpsAssist — Escalation Email Drafter
# Auto-fills data from DB, drafts email via Groq, sends via smtplib

import smtplib
import pandas as pd
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from groq import Groq
from app.audit_logger import get_connection
from dotenv import load_dotenv
import os

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def _query_db(sql: str) -> pd.DataFrame:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        results = cursor.fetchall()
        df = pd.DataFrame(results)
        cursor.close()
    finally:
        conn.close()
    return df


# --- Fetch escalation context from DB ---
def _get_escalation_data(sector: str = None) -> dict:
    sector_filter = f"AND s.sector = '{sector}'" if sector else ""

    delayed_sql = f"""
        SELECT COUNT(*) AS delayed_count
        FROM shipments s
        WHERE s.status NOT IN ('Delivered', 'Cancelled')
          AND DATEDIFF(CURDATE(), s.dispatch_date) > 7
          {sector_filter}
    """

    vendor_sql = f"""
        SELECT v.vendor_name, ROUND(AVG(d.tat_hours), 1) AS avg_tat
        FROM dispatch_logs d
        JOIN shipments s ON d.shipment_id = s.shipment_id
        JOIN vendors v ON s.vendor_id = v.vendor_id
        WHERE d.tat_hours > 48
          {sector_filter}
        GROUP BY v.vendor_name
        ORDER BY avg_tat DESC
        LIMIT 3
    """

    cold_sql = """
        SELECT zone_name, COUNT(*) AS breach_count
        FROM cold_storage_logs
        WHERE alert_triggered = 1
        GROUP BY zone_name
        ORDER BY breach_count DESC
        LIMIT 3
    """

    delayed = _query_db(delayed_sql)
    vendors = _query_db(vendor_sql)
    cold = _query_db(cold_sql)

    return {
        "delayed_shipments": int(delayed["delayed_count"].iloc[0]),
        "top_breaching_vendors": vendors.to_dict(orient="records"),
        "cold_storage_breaches": cold.to_dict(orient="records"),
        "sector": sector or "All Sectors"
    }


# --- Draft escalation email using Groq ---
def draft_escalation_email(
    sector: str = None,
    recipient_name: str = "Operations Manager",
    sender_name: str = "OpsAssist System"
) -> dict:

    data = _get_escalation_data(sector)

    vendor_lines = "\n".join(
        [f"  - {v['vendor_name']}: avg TAT {v['avg_tat']} hours"
         for v in data["top_breaching_vendors"]]
    ) or "  - No vendor TAT data available"

    cold_lines = "\n".join(
        [f"  - {c['zone_name']}: {c['breach_count']} breach events"
         for c in data["cold_storage_breaches"]]
    ) or "  - No cold storage breach data available"

    prompt = f"""
You are an operations escalation assistant. Write a professional escalation email
based on this live operations data:

Sector: {data['sector']}
Delayed Shipments (>7 days): {data['delayed_shipments']}
Top Vendors with TAT Breach (>48 hrs):
{vendor_lines}
Cold Storage Breach Zones:
{cold_lines}

Write the email addressed to {recipient_name} from {sender_name}.
Include: subject line, greeting, 3-4 sentence situation summary,
bullet point issues, and a clear call to action.
Keep it professional and concise. Format as:
SUBJECT: <subject here>
BODY:
<email body here>
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
        temperature=0.5,
    )

    raw = response.choices[0].message.content.strip()

    # Parse subject and body
    subject = "Escalation: Operations Issues Require Immediate Attention"
    body = raw

    if "SUBJECT:" in raw:
        lines = raw.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("SUBJECT:"):
                subject = line.replace("SUBJECT:", "").strip()
            if line.startswith("BODY:"):
                body = "\n".join(lines[i+1:]).strip()
                break

    return {
        "subject": subject,
        "body": body,
        "data_used": data
    }


# --- Send email via smtplib ---
def send_escalation_email(
    to_email: str,
    subject: str,
    body: str
) -> bool:
    smtp_email = os.getenv("SMTP_EMAIL")
    smtp_password = os.getenv("SMTP_PASSWORD")

    if not smtp_email or not smtp_password:
        print("SMTP credentials not configured in .env")
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_email
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(smtp_email, smtp_password)
            server.sendmail(smtp_email, to_email, msg.as_string())

        print(f"Email sent to {to_email}")
        return True

    except Exception as e:
        print(f"Email send failed: {e}")
        return False


if __name__ == "__main__":
    result = draft_escalation_email(sector=None, recipient_name="Operations Manager")
    print("SUBJECT:", result["subject"])
    print()
    print("BODY:")
    print(result["body"])
    print()
    print("DATA USED:", result["data_used"])