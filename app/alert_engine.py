# app/alert_engine.py
# OpsAssist — AI Alert Engine
# Detects: vendor TAT decline, cold storage breach, shipment ageing, slow-moving SKUs

import pandas as pd
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


def _ask_groq(prompt: str) -> str:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
        temperature=0.4,
    )
    return response.choices[0].message.content.strip()


# --- Alert 1: Vendor TAT Decline ---
def check_vendor_tat() -> list[dict]:
    sql = """
        SELECT v.vendor_name, v.sector,
               ROUND(AVG(d.tat_hours), 1) AS avg_tat
        FROM dispatch_logs d
        JOIN shipments s ON d.shipment_id = s.shipment_id
        JOIN vendors v ON s.vendor_id = v.vendor_id
        WHERE d.tat_hours IS NOT NULL
        GROUP BY v.vendor_id, v.vendor_name, v.sector
        HAVING avg_tat > 48
        ORDER BY avg_tat DESC
        LIMIT 5
    """
    df = _query_db(sql)
    alerts = []
    for _, row in df.iterrows():
        msg = _ask_groq(
            f"Vendor '{row['vendor_name']}' (sector: {row['sector']}) has average TAT of "
            f"{row['avg_tat']} hours, which exceeds the 48-hour SLA. "
            f"Write a 1-sentence ops alert for a logistics coordinator."
        )
        alerts.append({
            "type": "Vendor TAT Decline",
            "vendor": row["vendor_name"],
            "sector": row["sector"],
            "avg_tat_hours": row["avg_tat"],
            "message": msg
        })
    return alerts


# --- Alert 2: Cold Storage Breach ---
def check_cold_storage() -> list[dict]:
    sql = """
        SELECT zone_name, temperature, humidity, recorded_at, status
        FROM cold_storage_logs
        WHERE alert_triggered = 1
        ORDER BY recorded_at DESC
        LIMIT 5
    """
    df = _query_db(sql)
    alerts = []
    for _, row in df.iterrows():
        msg = _ask_groq(
            f"Cold storage zone '{row['zone_name']}' recorded temperature {row['temperature']}°C "
            f"and humidity {row['humidity']}% at {row['recorded_at']} with status '{row['status']}'. "
            f"Write a 1-sentence urgent ops alert."
        )
        alerts.append({
            "type": "Cold Storage Breach",
            "zone": row["zone_name"],
            "temperature": row["temperature"],
            "humidity": row["humidity"],
            "recorded_at": str(row["recorded_at"]),
            "message": msg
        })
    return alerts


# --- Alert 3: Shipment Ageing ---
def check_shipment_ageing() -> list[dict]:
    sql = """
        SELECT shipment_id, tracking_number, origin_city,
               destination_city, sector, dispatch_date,
               DATEDIFF(CURDATE(), dispatch_date) AS days_in_transit
        FROM shipments
        WHERE status NOT IN ('Delivered', 'Cancelled')
          AND DATEDIFF(CURDATE(), dispatch_date) > 7
        ORDER BY days_in_transit DESC
        LIMIT 5
    """
    df = _query_db(sql)
    alerts = []
    for _, row in df.iterrows():
        msg = _ask_groq(
            f"Shipment {row['tracking_number']} from {row['origin_city']} to "
            f"{row['destination_city']} (sector: {row['sector']}) has been in transit for "
            f"{row['days_in_transit']} days without delivery. Write a 1-sentence ops alert."
        )
        alerts.append({
            "type": "Shipment Ageing",
            "tracking_number": row["tracking_number"],
            "sector": row["sector"],
            "days_in_transit": int(row["days_in_transit"]),
            "message": msg
        })
    return alerts


# --- Alert 4: Slow-Moving SKUs ---
def check_slow_moving_skus() -> list[dict]:
    sql = """
        SELECT sku_code, product_name, category, sector,
               current_stock, quantity_out
        FROM inventory
        WHERE current_stock > 50
          AND quantity_out < 10
        ORDER BY current_stock DESC
        LIMIT 5
    """
    df = _query_db(sql)
    alerts = []
    for _, row in df.iterrows():
        msg = _ask_groq(
            f"SKU '{row['sku_code']}' ({row['product_name']}, {row['category']}, sector: {row['sector']}) "
            f"has {row['current_stock']} units in stock but only {row['quantity_out']} units moved out. "
            f"Write a 1-sentence inventory alert for an ops coordinator."
        )
        alerts.append({
            "type": "Slow-Moving SKU",
            "sku_code": row["sku_code"],
            "product_name": row["product_name"],
            "sector": row["sector"],
            "current_stock": int(row["current_stock"]),
            "message": msg
        })
    return alerts


# --- Run All Alerts ---
def run_all_alerts() -> list[dict]:
    all_alerts = []
    all_alerts += check_vendor_tat()
    all_alerts += check_cold_storage()
    all_alerts += check_shipment_ageing()
    all_alerts += check_slow_moving_skus()
    return all_alerts


# --- Quick test ---
if __name__ == "__main__":
    alerts = run_all_alerts()
    print(f"\nTotal alerts generated: {len(alerts)}\n")
    for a in alerts:
        print(f"[{a['type']}] {a['message']}")
        print()