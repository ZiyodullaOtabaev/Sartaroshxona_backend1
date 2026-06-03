"""
Sartaroshxona Backend - Configuration
Barcha sozlamalar shu yerda markazlashtirilgan
"""
import os
import ssl


# ─── SECRET KEY ──────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "sartaroshxona-dev-key-change-in-production!")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# ─── SERVER ──────────────────────────────────────────────────────────────────
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))
SERVER_BASE_URL = os.getenv("SERVER_BASE_URL", f"http://{SERVER_HOST}:{SERVER_PORT}")

# ─── DATABASE ────────────────────────────────────────────────────────────────
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "0000"),
    "db": os.getenv("DB_NAME", "sartaroshxona_db"),
    "autocommit": False,
    "minsize": 2,
    "maxsize": 10,
}

# Aiven SSL support
if os.getenv("DB_HOST") and "aiven" in os.getenv("DB_HOST", ""):
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    DB_CONFIG["ssl"] = ssl_ctx

# ─── CORS ────────────────────────────────────────────────────────────────────
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# ─── PAGINATION ──────────────────────────────────────────────────────────────
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# ─── UPLOAD ──────────────────────────────────────────────────────────────────
UPLOAD_DIR = "uploads"
AVATAR_DIR = "uploads/avatars"
ALLOWED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
