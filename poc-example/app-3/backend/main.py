from __future__ import annotations

import asyncio
import logging
import os
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles

from backend.data import DataAccessError, backend_name, load_dashboard


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Patient Signal Workbench",
    description="Governed patient-access analytics for MedPulse analysts.",
    version="1.0.0",
)


@app.get("/api/health")
async def health_check() -> dict[str, str | bool]:
    return {
        "status": "healthy",
        "backend": backend_name(),
    }


@app.get("/api/dashboard")
async def dashboard(
    therapy: str = Query(default="Therapy A", max_length=80),
    region: str = Query(default="Northeast", max_length=80),
    payer_type: str = Query(default="Commercial", max_length=80),
    start_date: date = Query(default=date(2026, 5, 1)),
) -> dict:
    """Return the app's analyst-safe Gold data in one compact response."""
    try:
        return await asyncio.to_thread(
            load_dashboard,
            therapy=therapy,
            region=region,
            payer_type=payer_type,
            start_date=start_date,
        )
    except DataAccessError as exc:
        logger.exception("Unable to load dashboard data")
        raise HTTPException(status_code=503, detail=str(exc)) from exc


static_dir = Path(__file__).resolve().parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("DATABRICKS_APP_PORT", "8000")),
    )
