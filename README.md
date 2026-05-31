# 🚚 OpsAssist — AI-Powered Operations Co-pilot

An LLM-powered operations co-pilot that lets logistics coordinators query a unified multi-sector operations database in plain English, auto-generates formatted Excel MIS reports, surfaces proactive AI decision alerts, and drafts data-backed escalation emails.

---

## 🎯 Key Features

- 💬 **Natural Language Queries** — Ask anything in plain English, get SQL results instantly
- 📊 **Excel MIS Reports** — Auto-generate dispatch, inventory and vendor scorecard reports
- 🚨 **AI Alert Feed** — Detects vendor TAT decline, cold storage breaches, shipment ageing, slow SKUs
- 📧 **Escalation Email Drafter** — AI drafts professional emails from live DB data
- 🗂️ **Audit Trail** — Every query and action logged automatically

---

## 🏭 Target Industries

| Industry | Companies |
|----------|-----------|
| Logistics & Transport | Delhivery, Safexpress |
| Warehouse | Frontier Warehousing |
| Cold Storage | Snowman, ColdEx |
| Steel / Manufacturing | JSW Steel |
| Courier / E-commerce | Ekart, Blue Dart |
| Port / Shipping | Apeejay Shipping |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.14 |
| Database | MySQL 9.7 |
| LLM | Groq API — LLaMA 3.3 70B |
| Frontend | Streamlit |
| Excel | openpyxl |
| ORM | SQLAlchemy + PyMySQL |
| Data | pandas |
| Deployment | Streamlit Cloud |

---

## 🗄️ Database Schema

- **vendors** — 40 rows (vendor profiles, ratings, sectors)
- **shipments** — 2,000 rows (tracking, status, origin/destination)
- **inventory** — 300 rows (SKUs, stock levels, warehouse locations)
- **cold_storage_logs** — 2,000 rows (temperature, humidity, breach alerts)
- **dispatch_logs** — 2,000 rows (driver, TAT, delivery status)
- **audit_logs** — grows with usage

---

## 🚀 Local Setup

```bash
# 1. Clone the repository
git clone https://github.com/TheShashankWeb/OpsAssist.git
cd OpsAssist

# 2. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
# Create .env file with:
# GROQ_API_KEY=your_groq_api_key
# DB_HOST=localhost
# DB_PORT=3306
# DB_NAME=opsassist_db
# DB_USER=root
# DB_PASSWORD=your_mysql_password
# SMTP_EMAIL=your_gmail
# SMTP_PASSWORD=your_gmail_app_password

# 5. Setup MySQL database
mysql -u root -p < database/schema.sql
python database/seed_data.py

# 6. Run the app
streamlit run main.py
```

---

## 📁 Project Structure
OpsAssist/
├── app/
│   ├── nl2sql.py          # NL to SQL using Groq API
│   ├── report_builder.py  # Excel MIS report generator
│   ├── alert_engine.py    # AI-powered alert detection
│   ├── escalation.py      # Escalation email drafter
│   └── audit_logger.py    # DB connection + audit logging
├── database/
│   ├── schema.sql         # All 6 table definitions
│   └── seed_data.py       # 6,340+ rows of realistic data
├── reports/               # Generated Excel files
├── main.py                # Streamlit app entry point
└── requirements.txt

---

## 💡 Sample Queries

- *"Show top 5 vendors by rating"*
- *"List all delayed shipments older than 7 days"*
- *"Which cold storage zones had breaches this week?"*
- *"Show slow moving SKUs with stock above 100"*
- *"Average TAT by sector"*

---

## 👨‍💻 Developer

**Shashank** — [GitHub](https://github.com/TheShashankWeb)

---

*Built as a portfolio project demonstrating LLM integration, SQL automation, and real-world operations use cases.*
