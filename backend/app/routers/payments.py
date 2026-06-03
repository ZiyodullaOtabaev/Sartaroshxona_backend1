"""
Payments endpoints — to'lov tizimi
"""
import datetime
import logging
import aiomysql
from fastapi import APIRouter, HTTPException, Depends, Query

from app.database import get_conn, release_conn
from app.middleware.auth import require_auth
from app.schemas.models import PaymentCreate
from app.services.helpers import serialize_datetime
from app.config import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/")
async def create_payment(
    payment: PaymentCreate,
    current_user: dict = Depends(require_auth),
):
    """To'lov yaratish — faqat O'Z navbatim uchun"""
    conn = await get_conn()
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # Appointment tekshirish
            await cur.execute(
                "SELECT id, price, customer_id, payment_status FROM appointments WHERE id=%s",
                (payment.appointment_id,),
            )
            appt = await cur.fetchone()
            if not appt:
                raise HTTPException(status_code=404, detail="Navbat topilmadi")

            # Ownership check
            if appt["customer_id"] != current_user["user_id"]:
                raise HTTPException(status_code=403, detail="Faqat o'z navbatingiz uchun to'lashingiz mumkin")

            if appt["payment_status"] == "paid":
                raise HTTPException(status_code=409, detail="Allaqachon to'langan")

            # Payment yaratish
            await cur.execute(
                "INSERT INTO payments (appointment_id, amount, method, status) VALUES (%s, %s, %s, 'pending')",
                (payment.appointment_id, payment.amount, payment.method),
            )
            payment_id = cur.lastrowid

            # To'lovni tasdiqlash (Click/Payme simulyatsiya)
            if payment.method in ("click", "payme"):
                transaction_id = f"{payment.method.upper()}-{payment_id}-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
                await cur.execute(
                    "UPDATE payments SET status='completed', transaction_id=%s WHERE id=%s",
                    (transaction_id, payment_id),
                )
            else:
                await cur.execute(
                    "UPDATE payments SET status='completed' WHERE id=%s", (payment_id,)
                )

            # Appointment statusini yangilash
            await cur.execute(
                "UPDATE appointments SET payment_status='paid', payment_method=%s WHERE id=%s",
                (payment.method, payment.appointment_id),
            )

            # Loyalty points
            points = int(payment.amount // 50000)
            if points > 0:
                await cur.execute(
                    "UPDATE users SET loyalty_points = loyalty_points + %s WHERE id=%s",
                    (points, appt["customer_id"]),
                )

            await conn.commit()
            return {
                "status": "success",
                "payment_id": payment_id,
                "loyalty_points_earned": points,
            }

    except HTTPException:
        raise
    except Exception as e:
        await conn.rollback()
        logger.error(f"Payment xato: {e}")
        raise HTTPException(status_code=500, detail="To'lovda xatolik")
    finally:
        await release_conn(conn)


@router.get("/history")
async def get_payment_history(
    current_user: dict = Depends(require_auth),
    page: int = Query(1, ge=1),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
):
    """Mening to'lov tarixim"""
    conn = await get_conn()
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            offset = (page - 1) * limit
            await cur.execute(
                "SELECT p.*, a.service_name, b.name as barber_name "
                "FROM payments p "
                "JOIN appointments a ON p.appointment_id = a.id "
                "JOIN barbers b ON a.barber_id = b.id "
                "WHERE a.customer_id=%s AND p.status='completed' "
                "ORDER BY p.created_at DESC LIMIT %s OFFSET %s",
                (current_user["user_id"], limit, offset),
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
