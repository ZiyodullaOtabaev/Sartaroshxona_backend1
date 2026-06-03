"""
Reviews endpoints — baholash tizimi
"""
import logging
import aiomysql
from fastapi import APIRouter, HTTPException, Depends, Query

from app.database import get_conn, release_conn
from app.middleware.auth import require_auth
from app.schemas.models import ReviewCreate
from app.services.helpers import serialize_datetime
from app.config import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.post("/")
async def add_review(
    review: ReviewCreate,
    current_user: dict = Depends(require_auth),
):
    """Baholash qo'shish — faqat O'Z appointmentingiz uchun"""
    customer_id = current_user["user_id"]
    conn = await get_conn()
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # Appointment ownership tekshirish
            await cur.execute(
                "SELECT id, customer_id, status FROM appointments WHERE id=%s",
                (review.appointment_id,),
            )
            appt = await cur.fetchone()
            if not appt:
                raise HTTPException(status_code=404, detail="Navbat topilmadi")
            if appt["customer_id"] != customer_id:
                raise HTTPException(status_code=403, detail="Faqat o'z navbatingizni baholashingiz mumkin")
            if appt["status"] != "completed":
                raise HTTPException(status_code=400, detail="Faqat yakunlangan navbatni baholash mumkin")

            # Duplicate check
            await cur.execute(
                "SELECT id FROM reviews WHERE appointment_id=%s AND customer_id=%s",
                (review.appointment_id, customer_id),
            )
            if await cur.fetchone():
                raise HTTPException(status_code=409, detail="Allaqachon baholangansiz")

            # Review yaratish
            await cur.execute(
                "INSERT INTO reviews (appointment_id, customer_id, barber_id, rating, comment) "
                "VALUES (%s, %s, %s, %s, %s)",
                (review.appointment_id, customer_id, review.barber_id, review.rating, review.comment),
            )

            # Rating yangilash
            await cur.execute(
                "SELECT AVG(rating) as avg_r, COUNT(*) as cnt FROM reviews WHERE barber_id=%s",
                (review.barber_id,),
            )
            stats = await cur.fetchone()
            if stats and stats["avg_r"]:
                await cur.execute(
                    "UPDATE barbers SET rating=%s, total_reviews=%s WHERE id=%s",
                    (round(float(stats["avg_r"]), 1), stats["cnt"], review.barber_id),
                )

            await conn.commit()
            return {"status": "success"}

    except HTTPException:
        raise
    except Exception as e:
        await conn.rollback()
        logger.error(f"Review xato: {e}")
        raise HTTPException(status_code=500, detail="Baholashda xatolik")
    finally:
        await release_conn(conn)


@router.get("/barber/{barber_id}")
async def get_barber_reviews(
    barber_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
):
    """Barber baholari"""
    conn = await get_conn()
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            offset = (page - 1) * limit
            await cur.execute(
                "SELECT r.*, u.full_name as customer_name "
                "FROM reviews r JOIN users u ON r.customer_id=u.id "
                "WHERE r.barber_id=%s ORDER BY r.created_at DESC "
                "LIMIT %s OFFSET %s",
                (barber_id, limit, offset),
            )
            result = await cur.fetchall()
            rows = []
            for r in result:
                d = dict(r)
                d = serialize_datetime(d, ["created_at"])
                rows.append(d)
            return rows
    finally:
        await release_conn(conn)
