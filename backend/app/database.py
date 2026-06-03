"""
Database connection pool management
"""
import aiomysql
import logging
from app.config import DB_CONFIG

logger = logging.getLogger(__name__)

pool: aiomysql.Pool = None  # type: ignore


async def create_pool():
    """Database connection pool yaratish"""
    global pool
    pool_config = {
        "host": DB_CONFIG["host"],
        "port": DB_CONFIG["port"],
        "user": DB_CONFIG["user"],
        "password": DB_CONFIG["password"],
        "db": DB_CONFIG["db"],
        "autocommit": DB_CONFIG["autocommit"],
        "minsize": DB_CONFIG["minsize"],
        "maxsize": DB_CONFIG["maxsize"],
    }
    if "ssl" in DB_CONFIG:
        pool_config["ssl"] = DB_CONFIG["ssl"]

    pool = await aiomysql.create_pool(**pool_config)
    logger.info("Database connection pool yaratildi")


async def close_pool():
    """Pool'ni yopish"""
    global pool
    if pool:
        pool.close()
        await pool.wait_closed()
        logger.info("Database connection pool yopildi")


async def get_conn():
    """Connection olish"""
    return await pool.acquire()


async def release_conn(conn):
    """Connection qaytarish"""
    pool.release(conn)
