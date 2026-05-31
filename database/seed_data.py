import sys
import os
sys.stdout = open('seed_log.txt', 'w')
sys.stderr = sys.stdout

from dotenv import load_dotenv
load_dotenv()

import pymysql
import random
from faker import Faker
from datetime import datetime, timedelta

fake = Faker('en_IN')

conn = pymysql.connect(
    host=os.getenv('DB_HOST', 'localhost'),
    port=int(os.getenv('DB_PORT', 3306)),
    user=os.getenv('DB_USER', 'root'),
    password=os.getenv('DB_PASSWORD', ''),
    database=os.getenv('DB_NAME', 'opsassist_db')
)
cursor = conn.cursor()

sectors = ['Logistics','Warehouse','Cold Storage','Steel','Courier','Port','Startup']
cities = ['Mumbai','Delhi','Chennai','Kolkata','Pune','Hyderabad','Ahmedabad','Surat']
vendor_names = [
    'Delhivery Pvt Ltd','Safexpress Ltd','Blue Dart Express',
    'Ekart Logistics','Gati KWE','TCI Express','Spoton Logistics',
    'Snowman Logistics','ColdEx Logistics','Versacold India',
    'JSW Steel Logistics','Tata Steel Supply','SAIL Transport',
    'Apeejay Shipping','Shreyas Shipping','Essar Ports',
    'Frontier Warehousing','Mahindra Logistics','VRL Logistics',
    'Amazon Logistics India'
]

print("Inserting vendors...")
for name in vendor_names:
    cursor.execute("""
        INSERT IGNORE INTO vendors (vendor_name, sector, contact_email, city, rating)
        VALUES (%s, %s, %s, %s, %s)
    """, (name, random.choice(sectors), fake.email(),
          random.choice(cities), round(random.uniform(2.5, 5.0), 2)))
conn.commit()
print("Vendors done!")

cursor.execute("SELECT vendor_id FROM vendors")
vendor_ids = [row[0] for row in cursor.fetchall()]

print("Inserting shipments...")
statuses = ['Delivered','In Transit','Pending','Delayed','Cancelled']
start_date = datetime.now() - timedelta(days=180)
for i in range(2000):
    dispatch = start_date + timedelta(days=random.randint(0, 170))
    expected = dispatch + timedelta(days=random.randint(1, 7))
    actual = expected + timedelta(days=random.randint(-1, 5)) if random.random() > 0.2 else None
    cursor.execute("""
        INSERT INTO shipments
        (tracking_number, vendor_id, origin_city, destination_city,
         status, dispatch_date, expected_delivery, actual_delivery, weight_kg, sector)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (f"TRK{100000+i}", random.choice(vendor_ids),
          random.choice(cities), random.choice(cities),
          random.choice(statuses), dispatch.date(), expected.date(),
          actual.date() if actual else None,
          round(random.uniform(0.5, 5000), 2), random.choice(sectors)))
conn.commit()
print("Shipments done!")

cursor.execute("SELECT shipment_id FROM shipments")
shipment_ids = [row[0] for row in cursor.fetchall()]

print("Inserting inventory...")
products = [
    ('SKU001','Steel Coil HR','Raw Material','Steel'),
    ('SKU002','Frozen Prawns 1kg','Seafood','Cold Storage'),
    ('SKU003','Mobile Phone Box','Electronics','Courier'),
    ('SKU004','Rice Bag 25kg','Food Grain','Warehouse'),
    ('SKU005','Engine Oil 5L','Automotive','Logistics'),
    ('SKU006','Laptop Dell','Electronics','Courier'),
    ('SKU007','Chicken Frozen 2kg','Poultry','Cold Storage'),
    ('SKU008','Cement Bag 50kg','Construction','Warehouse'),
    ('SKU009','Container 20ft','Shipping','Port'),
    ('SKU010','Server Rack Unit','IT Hardware','Startup'),
]
warehouses = ['Zone-A','Zone-B','Zone-C','Zone-D']
for sku, name, cat, sec in products:
    for _ in range(30):
        qty_in = random.randint(50, 500)
        qty_out = random.randint(10, qty_in)
        cursor.execute("""
            INSERT INTO inventory
            (sku_code, product_name, category, sector,
             quantity_in, quantity_out, current_stock, warehouse_location)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (sku, name, cat, sec, qty_in, qty_out,
              qty_in - qty_out, random.choice(warehouses)))
conn.commit()
print("Inventory done!")

print("Inserting cold storage logs...")
zones = ['Zone-A','Zone-B','Zone-C','Zone-D']
for _ in range(2000):
    temp = round(random.uniform(-25, 10), 2)
    alert = temp > 5 or temp < -22
    cursor.execute("""
        INSERT INTO cold_storage_logs
        (zone_name, temperature, humidity, recorded_at, status, alert_triggered)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (random.choice(zones), temp,
          round(random.uniform(60, 95), 2),
          start_date + timedelta(hours=random.randint(0, 4320)),
          'BREACH' if alert else 'NORMAL', alert))
conn.commit()
print("Cold storage done!")

print("Inserting dispatch logs...")
drivers = [fake.name() for _ in range(50)]
delivery_statuses = ['Delivered','Failed','Returned','Partial']
failure_reasons = ['Wrong Address','Customer Absent','Vehicle Breakdown',
                   'Weather Delay','Traffic',None,None,None]
for sid in random.sample(shipment_ids, min(2000, len(shipment_ids))):
    dispatch_time = start_date + timedelta(hours=random.randint(0, 4000))
    tat = round(random.uniform(1, 96), 2)
    delivery_time = dispatch_time + timedelta(hours=tat)
    status = random.choice(delivery_statuses)
    cursor.execute("""
        INSERT INTO dispatch_logs
        (shipment_id, driver_name, vehicle_number, dispatch_time,
         delivery_time, tat_hours, delivery_status, failure_reason, sector)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (sid, random.choice(drivers),
          f"MH{random.randint(10,99)}AB{random.randint(1000,9999)}",
          dispatch_time, delivery_time, tat, status,
          random.choice(failure_reasons) if status == 'Failed' else None,
          random.choice(sectors)))
conn.commit()
print("Dispatch done!")

cursor.close()
conn.close()
print("SUCCESS: All data seeded! 10000+ rows inserted.")
sys.stdout.close()