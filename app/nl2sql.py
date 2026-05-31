import os
import pandas as pd
from dotenv import load_dotenv
from groq import Groq
from app.audit_logger import get_connection, log_action

load_dotenv()
client = Groq(api_key=os.getenv('GROQ_API_KEY'))

DB_SCHEMA = """
Tables in opsassist_db:
1. vendors(vendor_id, vendor_name, sector, contact_email, city, rating)
2. shipments(shipment_id, tracking_number, vendor_id, origin_city, destination_city, status, dispatch_date, expected_delivery, actual_delivery, weight_kg, sector)
3. inventory(inventory_id, sku_code, product_name, category, sector, quantity_in, quantity_out, current_stock, warehouse_location, last_updated)
4. cold_storage_logs(log_id, zone_name, temperature, humidity, recorded_at, status, alert_triggered)
5. dispatch_logs(dispatch_id, shipment_id, driver_name, vehicle_number, dispatch_time, delivery_time, tat_hours, delivery_status, failure_reason, sector)
Relationships: shipments.vendor_id=vendors.vendor_id, dispatch_logs.shipment_id=shipments.shipment_id
"""

def generate_sql(q, sector="All"):
    sf = f"Filter for sector={sector}." if sector != "All" else ""
    prompt = f"""You are a MySQL expert. Given this schema:
{DB_SCHEMA}
Return ONLY a valid MySQL SELECT query. No markdown. No explanation. LIMIT 100. {sf}
Question: {q}
SQL:"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    sql = response.choices[0].message.content.strip()
    sql = sql.replace("```sql", "").replace("```", "").strip()
    return sql

def run_query(q, user="coordinator", sector="All"):
    try:
        sql = generate_sql(q, sector)
        if any(w in sql.upper() for w in ["INSERT","UPDATE","DELETE","DROP","ALTER"]):
            return None, "Query blocked.", sql
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(sql)
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        df = pd.DataFrame(results)
        log_action(user, "NL_QUERY", q, f"SQL:{sql}|Rows:{len(df)}", sector)
        return df, None, sql
    except Exception as e:
        return None, str(e), ""