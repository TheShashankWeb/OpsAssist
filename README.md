# 🚚 OpsAssist — AI-Powered Operations Co-pilot

> An LLM-powered operations assistant that lets logistics coordinators 
> query a unified multi-sector database in plain English, auto-generates 
> Excel MIS reports, surfaces AI decision alerts, and drafts escalation emails.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Streamlit%20Cloud-FF4B4B?style=for-the-badge&logo=streamlit)](https://opsassist-ds.streamlit.app)
[![GitHub](https://img.shields.io/badge/GitHub-OpsAssist-181717?style=for-the-badge&logo=github)](https://github.com/TheShashankWeb/OpsAssist)
[![Python](https://img.shields.io/badge/Python-3.14-3776AB?style=for-the-badge&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)

---

## 🔗 Quick Links

| Resource | Link |
|---|---|
| 🌐 Live App | https://opsassist-ds.streamlit.app |
| 📖 API Docs | Run locally → http://localhost:8000/docs |
| 💻 GitHub | https://github.com/TheShashankWeb/OpsAssist |

---

## 🎯 Problem it Solves

Operations coordinators at logistics companies spend hours:
- Writing SQL reports manually or waiting for IT teams
- Monitoring cold storage, dispatch TAT, shipment delays manually
- Drafting escalation emails with data pulled from multiple sources

**OpsAssist eliminates all of that** — coordinators type a question in plain 
English and get answers, reports, alerts, and draft emails in seconds.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 💬 **NL2SQL Query Engine** | Type any ops question in English → instant SQL + results |
| 🛡️ **SQL Injection Guard** | Blocks 15+ dangerous SQL patterns + destructive intents |
| 📊 **KPI Dashboard** | Live metrics — shipments, delays, cold breaches, avg TAT |
| 🚨 **AI Alert Feed** | 4 alert types with configurable thresholds |
| 📧 **Escalation Drafter** | AI drafts professional emails with live data injected |
| 📁 **Excel MIS Reports** | 3 formatted reports — Dispatch, Stock, Vendor Scorecard |
| 🗂️ **Audit Trail** | Every query, block, error logged with filters + CSV export |
| 🔐 **Login System** | SHA-256 hashed passwords, role-based sessions |
| ⚡ **FastAPI Backend** | REST API with auto-docs, Pydantic models, CORS |
| ⚡ **API Mode Toggle** | Switch between Direct DB and FastAPI backend live |

---

## 🏗️ Architecture

```text
User (Browser)
│
▼
Streamlit Frontend (main_cloud.py)
│
├── Direct DB Mode ──────────────────► SQLite (opsassist.db)
│
└── API Mode ──► FastAPI Backend ────► SQLite (opsassist.db)
(api/main.py)
│
├── POST /api/v1/query
└── GET  /api/v1/alerts
All SQL → SQL Guard (app/nl2sql.py)
→ Groq API LLaMA 3.3 70B
→ enforce_limit() → Execute
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---    |---         |
| Language | Python 3.14 |
| Frontend | Streamlit 1.58 |
| Backend API | FastAPI + Uvicorn |
| LLM | Groq API — LLaMA 3.3 70B (free) |
| Local DB | MySQL 9.7 |
| Cloud DB | SQLite (committed to repo) |
| Excel Reports | openpyxl |
| ORM | SQLAlchemy + PyMySQL |
| Auth | SHA-256 hashed passwords |
| Deployment | Streamlit Cloud |

---

## 📁 Project Structure

```text
OpsAssist/
├── api/                      ← FastAPI backend
│   ├── main.py               ← App entry + CORS
│   └── routes/
│       ├── query.py          ← POST /api/v1/query
│       └── alerts.py         ← GET /api/v1/alerts
├── app/
│   ├── nl2sql.py             ← NL2SQL + SQL Guard + enforce_limit
│   ├── report_builder.py     ← Excel MIS report generator
│   ├── alert_engine.py       ← Alert detection (MySQL)
│   ├── escalation.py         ← Escalation email drafter
│   └── audit_logger.py       ← MySQL audit logging
├── database/
│   ├── init_sqlite.py        ← SQLite init + seed
│   └── schema.sql            ← MySQL schema
├── main_cloud.py             ← Streamlit cloud entry point
├── main.py                   ← Streamlit local (MySQL)
├── opsassist.db              ← SQLite database (cloud)
├── requirements.txt
└── .env.example
```

---

## 🚀 Local Setup

### Prerequisites
- Python 3.10+
- MySQL 9.x (for local version)
- Groq API key (free at console.groq.com)

### Installation

```bash
# Clone the repo
git clone https://github.com/TheShashankWeb/OpsAssist.git
cd OpsAssist

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Add your GROQ_API_KEY to .env
```

### Run Streamlit App (Cloud/SQLite version)
```bash
streamlit run main_cloud.py
```

### Run FastAPI Backend (optional)
```bash
uvicorn api.main:app --reload --port 8000
# API docs at http://localhost:8000/docs
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/query` | Convert NL question to SQL and execute |
| `GET` | `/api/v1/alerts` | Get operational alerts with thresholds |
| `GET` | `/health` | Health check |
| `GET` | `/docs` | Auto-generated interactive API docs |

### Example — Query Endpoint

**Request:**
```json
POST /api/v1/query
{
  "question": "show top 5 vendors by rating",
  "sector": "All",
  "user": "coordinator"
}
```

**Response:**
```json
{
  "question": "show top 5 vendors by rating",
  "sql": "SELECT vendor_name, rating FROM vendors ORDER BY rating DESC LIMIT 5",
  "rows": 5,
  "data": [
    {"vendor_name": "Amazon Logistics India", "rating": 4.98},
    {"vendor_name": "Mahindra Logistics", "rating": 4.95}
  ],
  "error": null,
  "blocked": false
}
```

---

## 🔐 Security Features

- ✅ SQL injection protection — 15+ blocked keywords
- ✅ Destructive intent blocker — blocks "delete", "drop", "wipe" etc.
- ✅ SELECT-only enforcement — no write operations allowed
- ✅ Multi-statement SQL blocked
- ✅ LIMIT 100 enforced on all queries
- ✅ SHA-256 password hashing
- ✅ Session-based authentication
- ✅ Full audit trail with timestamps

---

## 🗃️ Database

**6 tables, 6,340+ rows of simulated operations data:**

| Table | Rows | Description |
|---|---|---|
| vendors | 40 | Vendor profiles across 7 sectors |
| shipments | 2,000 | 6-month shipment records |
| inventory | 300 | SKU stock movements |
| cold_storage_logs | 2,000 | Temperature and humidity logs |
| dispatch_logs | 2,000 | Driver TAT and delivery records |
| users | 3 | Admin, coordinator, viewer accounts |

**Default login credentials (demo):**
```text
admin       / admin123
coordinator / coord123
viewer      / view123
```

---

## 📊 What's New in v2.0

| Feature | v1.0 | v2.0 |
|---|---|---|
| SQL Guard | ❌ | ✅ 15+ patterns blocked |
| Login System | ❌ | ✅ SHA-256 + roles |
| KPI Dashboard | ❌ | ✅ 4 live metrics |
| Alert Thresholds | Hardcoded | ✅ Configurable sliders |
| Audit Trail | Basic | ✅ Filters + KPIs + CSV |
| FastAPI Backend | ❌ | ✅ Full REST API |
| API Mode Toggle | ❌ | ✅ Live switching |
| CSV Export | ❌ | ✅ Timestamped files |
| Sector Filter | Partial | ✅ Fully wired |

---

## 🏭 Target Industries

Delhivery · Safexpress · Blue Dart · Ekart · Gati KWE ·
Snowman Logistics · ColdEx · JSW Steel · Apeejay Shipping ·
Frontier Warehousing · Mahindra Logistics · VRL Logistics

---

## 👨💻 Developer

**Shashank**
GitHub: [@TheShashankWeb](https://github.com/TheShashankWeb)

---

## 📄 License

MIT License — free to use for portfolio and learning purposes.
