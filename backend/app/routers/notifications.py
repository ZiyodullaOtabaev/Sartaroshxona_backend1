"""
Notifications & Favorites endpoints
"""
import logging
import aiomysql
from fastapi import APIRouter, HTTPException, Depends, Query

from app.database import get_conn, release_conn
from app.middleware.auth import require_auth
from app.services.helpers import serialize_datetime
from app.config import DEFAULT_PAGE_SIZE

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Notifications & Favorites"])


# ═══════════════════════════════════════════════════════════════════════════════
# NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/notifications")
async def get_notifications(
    current_user: dict = Depends(require_auth),
    limit: int = Query(50, ge=1, le=100),
):
    """Mening bildirishnomalarim"""
    user_id = current_user["user_id"]
    conn = await get_conn()
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT * FROM notifications WHERE user_id=%s ORDER BY created_at DESC LIMIT %s",
                (user_id, limit),
            )
            result = await cur.fetchall()

            await cur.execute(
                "SELECT COUNT(*) as cnt FROM notifications WHERE user_id=%s AND is_read=0",
                (user_id,),
            )
            unread = (await cur.fetchone())["cnt"]

            rows = []
            for r in result:
                d = dict(r)
                d = serialize_datetime(d, ["created_at"])
                rows.append(d)

            return {"notifications": rows, "unread_count": unread}
    finally:
        await release_conn(conn)


@router.put("/notifications/read")
async def mark_all_read(current_user: dict = Depends(require_auth)):
    """Barcha bildirishnomalarni o'qilgan deb belgilash"""
    conn = await get_conn()
    try:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE notifications SET is_read=1 WHERE user_id=%s",
                (current_user["user_id"],),
            )
            await conn.commit()
        return {"status": "success"}
    finally:
        await release_conn(conn)


# ═══════════════════════════════════════════════════════════════════════════════
# FAVORITES
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/favorites/toggle")
async def toggle_favorite(
    barber_id: int,
    current_user: dict = Depends(require_auth),
):
    """Sevimli qo'shish/olib tashlash"""
    customer_id = current_user["user_id"]
    conn = await get_conn()
    try:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id FROM favorites WHERE customer_id=%s AND barber_id=%s",
                (customer_id, barber_id),
            )
            existing = await cur.fetchone()

            if existing:
                await cur.execute(
                    "DELETE FROM favorites WHERE customer_id=%s AND barber_id=%s",
                    (customer_id, barber_id),
                )
                await conn.commit()
                return {"status": "success", "is_favorite": False}
            else:
                await cur.execute(
                    "INSERT INTO favorites (customer_id, barber_id) VALUES (%s, %s)",
                    (customer_id, barber_id),
                )
                await conn.commit()
                return {"status": "success", "is_favorite": True}
    except Exception as e:
        await conn.rollback()
        logger.error(f"Favorite toggle xato: {e}")
        return {"status": "error", "detail": str(e)}
    finally:
        await release_conn(conn)


@router.get("/favorites")
async def get_favorites(current_user: dict = Depends(require_auth)):
    """Mening sevimlilarim"""
    conn = await get_conn()
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT b.id, b.name, b.district, b.rating, b.specialization, "
                "b.is_online, b.avatar_url, b.lat, b.lng, b.total_reviews "
                "FROM favorites f JOIN barbers b ON f.barber_id=b.id "
                "WHERE f.customer_id=%s ORDER BY f.created_at DESC",
                (current_user["user_id"],),
            )
            result = await cur.fetchall()
            return [dict(r) for r in result]
    finally:
        await release_conn(conn)
