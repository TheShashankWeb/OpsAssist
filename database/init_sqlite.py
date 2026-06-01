# database/init_sqlite.py
# Creates and seeds SQLite DB for cloud deployment

import sqlite3
import os
import random
from datetime import datetime, timedelta

DB_PATH = "opsassist.db"

VENDORS = [
    ("Amazon Logistics India", "Logistics", "amazon@logistics.in", "Mumbai", 4.98),
    ("Mahindra Logistics", "Logistics", "mahindra@logistics.in", "Pune", 4.95),
    ("Delhivery", "Courier", "ops@delhivery.com", "Delhi", 4.93),
    ("Safexpress Ltd", "Logistics", "ops@safexpress.com", "Delhi", 4.87),
    ("Shreyas Shipping", "Port", "ops@shreyas.com", "Mumbai", 4.83),
    ("Blue Dart Express", "Courier", "ops@bluedart.com", "Bangalore", 4.80),
    ("JSW Steel Logistics", "Steel", "ops@jsw.com", "Mumbai", 4.75),
    ("Essar Ports", "Port", "ops@essar.com", "Surat", 4.70),
    ("Snowman Logistics", "Cold Storage", "ops@snowman.com", "Delhi", 4.65),
    ("Ekart Logistics", "Courier", "ops@ekart.com", "Bangalore", 4.60),
    ("Spoton Logistics", "Logistics", "ops@spoton.com", "Hyderabad", 4.55),
    ("ColdEx", "Cold Storage", "ops@coldex.com", "Chennai", 4.50),
    ("Frontier Warehousing", "Warehouse", "ops@frontier.com", "Pune", 4.45),
    ("Apeejay Shipping", "Port", "ops@apeejay.com", "Kolkata", 4.40),
    ("TechStartup Logistics", "Startup", "ops@techstartup.com", "Bangalore", 4.35),
]

CITIES = ["Mumbai", "Delhi", "Bangalore", "Chennai", "Hyderabad",
          "Pune", "Kolkata", "Surat", "Ahmedabad", "Jaipur"]

SECTORS = ["Logistics", "Courier", "Cold Storage", "Steel",
           "Warehouse", "Port", "Startup"]

STATUSES = ["In Transit", "Delivered", "Delayed", "Out for Delivery", "Cancelled"]

CATEGORIES = ["Electronics", "Pharma", "FMCG", "Automotive", "Textile",
              "Steel", "Perishable", "Machinery"]

ZONES = ["Zone-A", "Zone-B", "Zone-C", "Zone-D"]

DRIVERS = ["Ramesh Kumar", "Suresh Singh", "Amit Sharma", "Vijay Patel",
           "Ravi Verma", "Arjun Nair", "Deepak Gupta", "Manoj Tiwari"]


def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    if os.path.exists(DB_PATH):
        print(f"SQLite DB already exists at {DB_PATH}")
        return

    print("Creating SQLite database...")
    conn = get_conn()
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS vendors (
        vendor_id INTEGER PRIMARY KEY AUTOINCREMENT,
        vendor_name TEXT, sector TEXT, contact_email TEXT,
        city TEXT, rating REAL
    );
    CREATE TABLE IF NOT EXISTS shipments (
        shipment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        tracking_number TEXT, vendor_id INTEGER,
        origin_city TEXT, destination_city TEXT, status TEXT,
        dispatch_date TEXT, expected_delivery TEXT,
        actual_delivery TEXT, weight_kg REAL, sector TEXT
    );
    CREATE TABLE IF NOT EXISTS inventory (
        inventory_id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku_code TEXT, product_name TEXT, category TEXT,
        sector TEXT, quantity_in INTEGER, quantity_out INTEGER,
        current_stock INTEGER, warehouse_location TEXT, last_updated TEXT
    );
    CREATE TABLE IF NOT EXISTS cold_storage_logs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        zone_name TEXT, temperature REAL, humidity REAL,
        recorded_at TEXT, status TEXT, alert_triggered INTEGER
    );
    CREATE TABLE IF NOT EXISTS dispatch_logs (
        dispatch_id INTEGER PRIMARY KEY AUTOINCREMENT,
        shipment_id INTEGER, driver_name TEXT, vehicle_number TEXT,
        dispatch_time TEXT, delivery_time TEXT, tat_hours REAL,
        delivery_status TEXT, failure_reason TEXT, sector TEXT
    );
    CREATE TABLE IF NOT EXISTS audit_logs (
        audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_name TEXT, action_type TEXT, query_text TEXT,
        result_summary TEXT, timestamp TEXT, sector TEXT
    );
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL,
        full_name TEXT,
        created_at TEXT
    );
    """)

    # Seed default users
    import hashlib
    def _hash(pwd):
        return hashlib.sha256(pwd.encode()).hexdigest()

    default_users = [
        ("admin",       _hash("admin123"),  "admin",       "Admin User",        datetime.now().strftime("%Y-%m-%d")),
        ("coordinator", _hash("coord123"),  "coordinator", "Ops Coordinator",   datetime.now().strftime("%Y-%m-%d")),
        ("viewer",      _hash("view123"),   "viewer",      "Read-Only Viewer",  datetime.now().strftime("%Y-%m-%d")),
    ]
    cur.executemany(
        """INSERT OR IGNORE INTO users
           (username, password_hash, role, full_name, created_at)
           VALUES (?,?,?,?,?)""",
        default_users
    )

    # Seed vendors
    cur.executemany(
        "INSERT INTO vendors (vendor_name, sector, contact_email, city, rating) VALUES (?,?,?,?,?)",
        VENDORS
    )

    # Seed shipments (500 rows)
    random.seed(42)
    base_date = datetime.now() - timedelta(days=60)
    shipments = []
    for i in range(1, 501):
        vendor_id = random.randint(1, len(VENDORS))
        sector = VENDORS[vendor_id - 1][1]
        dispatch = base_date + timedelta(days=random.randint(0, 55))
        expected = dispatch + timedelta(days=random.randint(2, 7))
        status = random.choice(STATUSES)
        actual = expected + timedelta(days=random.randint(-1, 5)) if status == "Delivered" else None
        shipments.append((
            f"TRK{100000+i}", vendor_id,
            random.choice(CITIES), random.choice(CITIES),
            status, dispatch.strftime("%Y-%m-%d"),
            expected.strftime("%Y-%m-%d"),
            actual.strftime("%Y-%m-%d") if actual else None,
            round(random.uniform(1, 500), 1), sector
        ))
    cur.executemany(
        """INSERT INTO shipments (tracking_number, vendor_id, origin_city,
        destination_city, status, dispatch_date, expected_delivery,
        actual_delivery, weight_kg, sector) VALUES (?,?,?,?,?,?,?,?,?,?)""",
        shipments
    )

    # Seed inventory (100 rows)
    inventory = []
    for i in range(1, 101):
        qty_in = random.randint(50, 500)
        qty_out = random.randint(0, qty_in)
        inventory.append((
            f"SKU{1000+i}", f"Product {i}",
            random.choice(CATEGORIES), random.choice(SECTORS),
            qty_in, qty_out, qty_in - qty_out,
            f"Warehouse-{random.choice(['A','B','C','D'])}",
            datetime.now().strftime("%Y-%m-%d")
        ))
    cur.executemany(
        """INSERT INTO inventory (sku_code, product_name, category, sector,
        quantity_in, quantity_out, current_stock, warehouse_location, last_updated)
        VALUES (?,?,?,?,?,?,?,?,?)""",
        inventory
    )

    # Seed cold_storage_logs (300 rows)
    cold_logs = []
    for i in range(300):
        temp = round(random.uniform(-5, 15), 1)
        humidity = round(random.uniform(60, 95), 1)
        alert = 1 if temp > 8 or humidity > 90 else 0
        status = "Breach" if alert else "Normal"
        recorded = datetime.now() - timedelta(hours=random.randint(0, 720))
        cold_logs.append((
            random.choice(ZONES), temp, humidity,
            recorded.strftime("%Y-%m-%d %H:%M:%S"), status, alert
        ))
    cur.executemany(
        """INSERT INTO cold_storage_logs (zone_name, temperature, humidity,
        recorded_at, status, alert_triggered) VALUES (?,?,?,?,?,?)""",
        cold_logs
    )

    # Seed dispatch_logs (500 rows)
    dispatch_logs = []
    failure_reasons = ["Traffic", "Address Issue", "Customer Absent", None, None, None]
    for i in range(1, 501):
        sector = random.choice(SECTORS)
        tat = round(random.uniform(12, 96), 1)
        d_status = "Delivered" if tat < 60 else "Delayed"
        dispatch_time = datetime.now() - timedelta(hours=random.randint(24, 500))
        delivery_time = dispatch_time + timedelta(hours=tat)
        dispatch_logs.append((
            i, random.choice(DRIVERS),
            f"MH{random.randint(10,99)}AB{random.randint(1000,9999)}",
            dispatch_time.strftime("%Y-%m-%d %H:%M:%S"),
            delivery_time.strftime("%Y-%m-%d %H:%M:%S"),
            tat, d_status, random.choice(failure_reasons), sector
        ))
    cur.executemany(
        """INSERT INTO dispatch_logs (shipment_id, driver_name, vehicle_number,
        dispatch_time, delivery_time, tat_hours, delivery_status, failure_reason, sector)
        VALUES (?,?,?,?,?,?,?,?,?)""",
        dispatch_logs
    )

    conn.commit()
    conn.close()
    print(f"SQLite DB created successfully at {DB_PATH}")
    print("Seeded: 15 vendors, 500 shipments, 100 inventory, 300 cold logs, 500 dispatch logs")


if __name__ == "__main__":
    init_db()
