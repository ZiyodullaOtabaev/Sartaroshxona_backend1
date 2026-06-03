"""
Sartaroshxona API — Professional Backend
Version: 4.0.0

Tuzilish:
- app/config.py — sozlamalar
- app/database.py — DB connection pool
- app/middleware/ — auth, error handling
- app/routers/ — endpoint guruhlari
- app/schemas/ — Pydantic models
- app/services/ — business logic helpers
"""
import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import CORS_ORIGINS, UPLOAD_DIR, AVATAR_DIR
from app.database import create_pool, close_pool
from app.middleware.error_handler import ErrorHandlerMiddleware

# ─── LOGGING SETUP ───────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─── LIFESPAN ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """App startup/shutdown"""
    logger.info("Sartaroshxona API ishga tushmoqda...")
    await create_pool()
    logger.info("Server tayyor!")
    yield
    await close_pool()
    logger.info("Server to'xtadi")


# ─── APP CREATION ────────────────────────────────────────────────────────────

app = FastAPI(
    title="Sartaroshxona API",
    description="Sartaroshxona — barber booking platform backend",
    version="4.0.0",
    lifespan=lifespan,
)

# ─── MIDDLEWARE ──────────────────────────────────────────────────────────────

# Error handler (barcha kutilmagan xatolarni ushlaydi)
app.add_middleware(ErrorHandlerMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── STATIC FILES ────────────────────────────────────────────────────────────

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(AVATAR_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# ─── ROUTERS ─────────────────────────────────────────────────────────────────

# Yangi API (versiyalangan, xavfsiz)
from app.routers import auth, barbers, appointments, reviews, payments, notifications
app.include_router(auth.router)
app.include_router(barbers.router)
app.include_router(appointments.router)
app.include_router(reviews.router)
app.include_router(payments.router)
app.include_router(notifications.router)

# Legacy endpoints (eski Flutter frontend bilan moslik uchun)
from app.routers import legacy
app.include_router(legacy.router)


# ─── ROOT & HEALTH ───────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "message": "Sartaroshxona API ishlayapti",
        "version": "4.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check — server va DB holatini tekshirish"""
    from app.database import get_conn, release_conn
    try:
        conn = await get_conn()
        try:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1")
        finally:
            await release_conn(conn)
        return {"status": "ok", "db": "connected", "version": "4.0.0"}
    except Exception as e:
        logger.error(f"Health check xato: {e}")
        return {"status": "error", "db": "disconnected", "detail": str(e)}


# ─── RUN ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    from app.config import SERVER_HOST, SERVER_PORT

    uvicorn.run(
        "main:app",
        host=SERVER_HOST,
        port=SERVER_PORT,
        reload=True,
        log_level="info",
    )
