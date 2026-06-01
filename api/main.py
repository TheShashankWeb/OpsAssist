# api/main.py
# OpsAssist — FastAPI Backend Entry Point

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import query, alerts

app = FastAPI(
    title="OpsAssist API",
    description="""
## OpsAssist — AI-Powered Operations Co-pilot API

This API powers the OpsAssist backend with the following capabilities:

- **Natural Language Queries** — Convert plain English to SQL and execute
- **Operational Alerts** — Detect TAT breaches, cold storage issues, shipment ageing, slow SKUs
- **SQL Guard** — All queries validated before execution

### Authentication
This is a demo API. In production, JWT-based authentication would be added.

### Tech Stack
- FastAPI + Uvicorn
- SQLite (cloud) / MySQL (local)
- Groq API (LLaMA 3.3 70B)
    """,
    version="2.0.0",
    contact={
        "name": "Shashank",
        "url": "https://github.com/TheShashankWeb/OpsAssist"
    }
)

# CORS — allows Streamlit to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "https://opsassist-ds.streamlit.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(query.router, prefix="/api/v1")
app.include_router(alerts.router, prefix="/api/v1")


@app.get("/", tags=["Health"])
def root():
    return {
        "app": "OpsAssist API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
        "endpoints": [
            "POST /api/v1/query",
            "GET  /api/v1/alerts"
        ]
    }


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}
