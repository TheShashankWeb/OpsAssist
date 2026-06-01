# api/routes/alerts.py
# OpsAssist FastAPI — Alerts Endpoint

from fastapi import APIRouter
from pydantic import BaseModel
import sqlite3
import pandas as pd

router = APIRouter()
DB_PATH = "opsassist.db"


class AlertItem(BaseModel):
    type: str
    message: str
    sector: str
    detail: str = ""


class AlertsResponse(BaseModel):
    total: int
    alerts: list[AlertItem]


@router.get("/alerts", response_model=AlertsResponse, tags=["Alerts"])
def get_alerts(
    sector: str = "All",
    tat_threshold: int = 48,
    ageing_days: int = 7,
    min_stock: int = 50,
    max_qty_out: int = 10
):
    """
    Returns operational alerts with configurable thresholds.
    All parameters are optional — defaults match industry SLA standards.
    """
    alerts = []
    conn = sqlite3.connect(DB_PATH)
    sf = f"AND sector = '{sector}'" if sector != "All" else ""

    # TAT Decline
    df = pd.read_sql_query(f"""
        SELECT driver_name, ROUND(AVG(tat_hours),1) as avg_tat, sector
        FROM dispatch_logs
        WHERE tat_hours > {tat_threshold} {sf}
        GROUP BY driver_name, sector
        ORDER BY avg_tat DESC LIMIT 5
    """, conn)
    for _, r in df.iterrows():
        alerts.append(AlertItem(
            type="Vendor TAT Decline",
            message=f"Driver {r['driver_name']} avg TAT {r['avg_tat']}hrs — exceeds {tat_threshold}hr SLA.",
            sector=str(r["sector"]),
            detail=f"avg_tat={r['avg_tat']}"
        ))

    # Cold Storage
    df = pd.read_sql_query("""
        SELECT zone_name, temperature, humidity
        FROM cold_storage_logs
        WHERE alert_triggered=1
        ORDER BY rowid DESC LIMIT 5
    """, conn)
    for _, r in df.iterrows():
        alerts.append(AlertItem(
            type="Cold Storage Breach",
            message=f"Zone {r['zone_name']}: {r['temperature']}°C / {r['humidity']}% humidity.",
            sector="Cold Storage",
            detail=f"temp={r['temperature']}, humidity={r['humidity']}"
        ))

    # Shipment Ageing
    df = pd.read_sql_query(f"""
        SELECT tracking_number, origin_city, destination_city, sector,
               CAST((julianday('now') - julianday(dispatch_date)) AS INTEGER) as days
        FROM shipments
        WHERE status NOT IN ('Delivered','Cancelled')
        AND CAST((julianday('now') - julianday(dispatch_date)) AS INTEGER) > {ageing_days}
        {sf}
        ORDER BY days DESC LIMIT 5
    """, conn)
    for _, r in df.iterrows():
        alerts.append(AlertItem(
            type="Shipment Ageing",
            message=f"Shipment {r['tracking_number']} stuck {r['days']} days — {r['origin_city']} to {r['destination_city']}.",
            sector=str(r["sector"]),
            detail=f"days_in_transit={r['days']}"
        ))

    # Slow SKUs
    df = pd.read_sql_query(f"""
        SELECT sku_code, product_name, sector, current_stock, quantity_out
        FROM inventory
        WHERE current_stock > {min_stock} AND quantity_out < {max_qty_out} {sf}
        ORDER BY current_stock DESC LIMIT 5
    """, conn)
    for _, r in df.iterrows():
        alerts.append(AlertItem(
            type="Slow-Moving SKU",
            message=f"SKU {r['sku_code']} has {r['current_stock']} units — only {r['quantity_out']} moved out.",
            sector=str(r["sector"]),
            detail=f"stock={r['current_stock']}, qty_out={r['quantity_out']}"
        ))

    conn.close()
    return AlertsResponse(total=len(alerts), alerts=alerts)
