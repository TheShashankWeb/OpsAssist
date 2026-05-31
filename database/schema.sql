-- OpsAssist Database Schema

USE opsassist_db;

-- 1. Vendors Table
CREATE TABLE IF NOT EXISTS vendors (
    vendor_id INT AUTO_INCREMENT PRIMARY KEY,
    vendor_name VARCHAR(100) NOT NULL,
    sector VARCHAR(50) NOT NULL,
    contact_email VARCHAR(100),
    city VARCHAR(50),
    rating DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Shipments Table
CREATE TABLE IF NOT EXISTS shipments (
    shipment_id INT AUTO_INCREMENT PRIMARY KEY,
    tracking_number VARCHAR(50) UNIQUE NOT NULL,
    vendor_id INT,
    origin_city VARCHAR(50),
    destination_city VARCHAR(50),
    status VARCHAR(30),
    dispatch_date DATE,
    expected_delivery DATE,
    actual_delivery DATE,
    weight_kg DECIMAL(8,2),
    sector VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vendor_id) REFERENCES vendors(vendor_id)
);

-- 3. Inventory Table
CREATE TABLE IF NOT EXISTS inventory (
    inventory_id INT AUTO_INCREMENT PRIMARY KEY,
    sku_code VARCHAR(50) NOT NULL,
    product_name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    sector VARCHAR(50),
    quantity_in INT DEFAULT 0,
    quantity_out INT DEFAULT 0,
    current_stock INT DEFAULT 0,
    warehouse_location VARCHAR(50),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Cold Storage Table
CREATE TABLE IF NOT EXISTS cold_storage_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    zone_name VARCHAR(50) NOT NULL,
    temperature DECIMAL(5,2),
    humidity DECIMAL(5,2),
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20),
    alert_triggered BOOLEAN DEFAULT FALSE
);

-- 5. Dispatch Log Table
CREATE TABLE IF NOT EXISTS dispatch_logs (
    dispatch_id INT AUTO_INCREMENT PRIMARY KEY,
    shipment_id INT,
    driver_name VARCHAR(100),
    vehicle_number VARCHAR(20),
    dispatch_time TIMESTAMP,
    delivery_time TIMESTAMP,
    tat_hours DECIMAL(6,2),
    delivery_status VARCHAR(30),
    failure_reason VARCHAR(200),
    sector VARCHAR(50),
    FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id)
);

-- 6. Audit Log Table
CREATE TABLE IF NOT EXISTS audit_logs (
    audit_id INT AUTO_INCREMENT PRIMARY KEY,
    user_name VARCHAR(100),
    action_type VARCHAR(50),
    query_text TEXT,
    result_summary VARCHAR(500),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sector VARCHAR(50)
);