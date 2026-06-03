"""
Legacy endpoints — eski Flutter frontend bilan moslik uchun.
Yangi API'ga redirect qiladi. Keyinchalik o'chirib tashlash mumkin.
"""
import logging
import aiomysql
from typing import List
from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File

from app.database import get_conn, release_conn
from app.middleware.auth import require_auth, get_current_user
from app.schemas.models import (
    UserRegister, UserLogin, UpdateProfile,
    AppointmentCreate as NewAppointmentCreate,
    ReviewCreate as NewReviewCreate,
    PaymentCreate as NewPaymentCreate,
)
from app.routers.auth import register as new_register, login as new_login
from app.routers.barbers import (
    get_nearby_barbers, get_all_barbers, search_barbers,
    get_barber_detail, update_barber_profile, update_online_status,
    update_working_days, upload_avatar, get_services, block_slot, get_blocked_slots,
    get_barber_stats,
)
from app.routers.appointments import (
    get_available_slots,
)
from app.services.helpers import haversine, timedelta_to_str, serialize_datetime

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Legacy (eski frontend uchun)"])


# ─── AUTH (eski yo'llar) ─────────────────────────────────────────────────────

@router.post("/register")
async def legacy_register(user: UserRegister):
    return await new_register(user)


@router.post("/login")
async def legacy_login(user: UserLogin):
    return await new_login(user)


# ─── BARBERS (eski yo'llar) ──────────────────────────────────────────────────

@router.get("/nearby_barbers")
async def legacy_nearby_barbers(user_lat: float, user_lng: float, radius_km: float = 2.0):
    """Eski format — list qaytaradi (paginated emas)"""
    conn = await get_conn()
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT id, name, district, rating, total_reviews, lat, lng, "
                "experience, specialization, phone, is_online, avatar_url, bio, "
                "working_hours_start, working_hours_end "
                "FROM barbers WHERE lat IS NOT NULL AND lng IS NOT NULL"
            )
            barbers = await cur.fetchall()
            result = []
            for b in barbers:
                dist = haversine(user_lat, user_lng, b["lat"], b["lng"])
                if dist <= radius_km:
                    d = dict(b)
                    d["distance"] = round(dist, 2)
                    d["working_hours_start"] = timedelta_to_str(d.get("working_hours_start"))
                    d["working_hours_end"] = timedelta_to_str(d.get("working_hours_end"))
                    result.append(d)
            result.sort(key=lambda x: (not x["is_online"], x["distance"]))
            return result
    finally:
        await release_conn(conn)


@router.get("/all_barbers")
async def legacy_all_barbers(user_lat: float = 41.3111, user_lng: float = 69.2797):
    conn = await get_conn()
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT id, name, district, rating, total_reviews, lat, lng, "
                "experience, specialization, phone, is_online, avatar_url, bio "
                "FROM barbers WHERE lat IS NOT NULL AND lng IS NOT NULL"
            )
            barbers = await cur.fetchall()
            result = []
            for b in barbers:
                d = dict(b)
                d["distance"] = round(haversine(user_lat, user_lng, b["lat"], b["lng"]), 2)
                result.append(d)
            return result
    finally:
        await release_conn(conn)


@router.get("/search_barbers")
async def legacy_search(query: str):
    return await search_barbers(query=query)


@router.get("/barber/{barber_id}")
async def legacy_barber_detail(barber_id: int):
    return await get_barber_detail(barber_id)


@router.put("/update_profile/{barber_id}")
async def legacy_update_profile(barber_id: int, data: UpdateProfile):
    """Eski format — auth yo'q (backward compat)"""
    conn = await get_conn()
    try:
        async with conn.cursor() as cur:
            fields, values = [], []
            if data.full_name:
                fields.append("name=%s"); values.append(data.full_name)
            if data.phone:
                fields.append("phone=%s"); values.append(data.phone)
            if data.bio is not None:
                fields.append("bio=%s"); values.append(data.bio)
            if data.specialization:
                fields.append("specialization=%s"); values.append(data.specialization)
            if data.experience:
                fields.append("experience=%s"); values.append(data.experience)
            if data.working_hours_start:
                fields.append("working_hours_start=%s"); values.append(data.working_hours_start)
            if data.working_hours_end:
                fields.append("working_hours_end=%s"); values.append(data.working_hours_end)
            if fields:
                values.append(barber_id)
                await cur.execute(f"UPDATE barbers SET {','.join(fields)} WHERE id=%s", values)
                await conn.commit()
            return {"status": "success"}
    finally:
        await release_conn(conn)


@router.put("/update_online_status/{barber_id}")
async def legacy_online_status(barber_id: int, is_online: bool):
    conn = await get_conn()
    try:
        async with conn.cursor() as cur:
            await cur.execute("UPDATE barbers SET is_online=%s WHERE id=%s", (is_online, barber_id))
            await conn.commit()
        return {"status": "success"}
    finally:
        await release_conn(conn)


@router.put("/update_working_days/{barber_id}")
async def legacy_working_days(barber_id: int, days: List[int]):
    conn = await get_conn()
    try:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM barber_working_days WHERE barber_id=%s", (barber_id,))
            for day in range(7):
                await cur.execute(
                    "INSERT INTO barber_working_days (barber_id, day_of_week, is_working) VALUES (%s,%s,%s)",
                    (barber_id, day, day in days),
                )
            await conn.commit()
            return {"status": "success"}
    finally:
        await release_conn(conn)


@router.post("/upload_avatar/{barber_id}")
async def legacy_upload_avatar(barber_id: int, file: UploadFile = File(...)):
    import os, uuid, shutil
    from app.config import SERVER_BASE_URL, ALLOWED_EXTENSIONS
    try:
        ext = os.path.splitext(file.filename)[-1].lower() if file.filename else ".jpg"
        if ext not in ALLOWED_EXTENSIONS:
            ext = ".jpg"
        filename = f"barber_{barber_id}_{uuid.uuid4().hex[:8]}{ext}"
        filepath = f"uploads/avatars/{filename}"
        os.makedirs("uploads/avatars", exist_ok=True)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        avatar_url = f"{SERVER_BASE_URL}/uploads/avatars/{filename}"
        conn = await get_conn()
        try:
            async with conn.cursor() as cur:
                await cur.execute("UPDATE barbers SET avatar_url=%s WHERE id=%s", (avatar_url, barber_id))
                await conn.commit()
        finally:
            await release_conn(conn)
        return {"status": "success", "avatar_url": avatar_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── SLOTS & SERVICES ────────────────────────────────────────────────────────

@router.get("/available_slots/{barber_id}")
async def legacy_slots(barber_id: int, date: str):
    return await get_available_slots(barber_id, date)


@router.get("/get_services/{barber_id}")
async def legacy_services(barber_id: int):
    conn = await get_conn()
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT * FROM barber_services WHERE barber_id=%s AND is_active=1 ORDER BY id", (barber_id,))
            return [dict(r) for r in await cur.fetchall()]
    finally:
        await release_conn(conn)


@router.post("/add_service")
async def legacy_add_service(barber_id: int, name: str, price: float, duration: int = 30, description: str = ""):
    conn = await get_conn()
    try:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO barber_services (barber_id, service_name, price, duration_minutes, description) VALUES (%s,%s,%s,%s,%s)",
                (barber_id, name, price, duration, description),
            )
            await conn.commit()
        return {"status": "success"}
    finally:
        await release_conn(conn)


@router.delete("/delete_service/{service_id}")
async def legacy_delete_service(service_id: int):
    conn = await get_conn()
    try:
        async with conn.cursor() as cur:
            await cur.execute("UPDATE barber_services SET is_active=0 WHERE id=%s", (service_id,))
            await conn.commit()
        return {"status": "success"}
    finally:
        await release_conn(conn)


@router.post("/block_slot")
async def legacy_block_slot(barber_id: int, blocked_date: str, start_time: str, end_time: str, reason: str = ""):
    conn = await get_conn()
    try:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO barber_blocked_slots (barber_id, blocked_date, start_time, end_time, reason) VALUES (%s,%s,%s,%s,%s)",
                (barber_id, blocked_date, start_time, end_time, reason),
            )
            await conn.commit()
        return {"status": "success"}
    finally:
        await release_conn(conn)


@router.get("/blocked_slots/{barber_id}")
async def legacy_blocked_slots(barber_id: int, date: str):
    return await get_blocked_slots(barber_id, date)


# ─── APPOINTMENTS ─────────────────────────────────────────────────────────────

from pydantic import BaseModel
from typing import Optional

class LegacyAppointmentCreate(BaseModel):
    customer_id: int
    barber_id: int
    service_id: Optional[int] = None
    appointment_time: str
    service_name: str
    price: float
    notes: Optional[str] = ""


@router.post("/book_appointment")
async def legacy_book(appt: LegacyAppointmentCreate):
    """Eski format — customer_id body'da"""
    import datetime
    conn = await get_conn()
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT id FROM barbers WHERE id=%s", (appt.barber_id,))
            if not await cur.fetchone():
                raise HTTPException(status_code=404, detail="Sartarosh topilmadi")
            duration = 30
            if appt.service_id:
                await cur.execute("SELECT duration_minutes FROM barber_services WHERE id=%s", (appt.service_id,))
                svc = await cur.fetchone()
                if svc: duration = svc["duration_minutes"]
            apt_dt = datetime.datetime.fromisoformat(appt.appointment_time)
            end_dt = apt_dt + datetime.timedelta(minutes=duration)
            await cur.execute(
                "SELECT id FROM appointments WHERE barber_id=%s AND status NOT IN ('cancelled') AND appointment_time < %s AND end_time > %s",
                (appt.barber_id, end_dt.strftime("%Y-%m-%d %H:%M:%S"), apt_dt.strftime("%Y-%m-%d %H:%M:%S")),
            )
            if await cur.fetchone():
                raise HTTPException(status_code=409, detail="Bu vaqt band! Boshqa vaqt tanlang.")
            await cur.execute(
                "INSERT INTO appointments (customer_id, barber_id, service_id, appointment_time, end_time, service_name, price, status, notes) VALUES (%s,%s,%s,%s,%s,%s,%s,'pending',%s)",
                (appt.customer_id, appt.barber_id, appt.service_id, appt.appointment_time, end_dt.strftime("%Y-%m-%d %H:%M:%S"), appt.service_name, appt.price, appt.notes),
            )
            appt_id = cur.lastrowid
            await cur.execute("SELECT full_name FROM users WHERE id=%s", (appt.customer_id,))
            customer = await cur.fetchone()
            await cur.execute("SELECT u.id FROM users u JOIN barbers b ON u.id=b.user_id WHERE b.id=%s", (appt.barber_id,))
            barber_user = await cur.fetchone()
            if barber_user:
                cust_name = customer["full_name"] if customer else "Mijoz"
                await cur.execute(
                    "INSERT INTO notifications (user_id, title, body, type) VALUES (%s,%s,%s,'appointment')",
                    (barber_user["id"], "Yangi navbat!", f"{cust_name} navbat oldi: {appt.service_name}"),
                )
            await conn.commit()
            return {"status": "success", "appointment_id": appt_id}
    except HTTPException:
        raise
    except Exception as e:
        await conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await release_conn(conn)


@router.get("/customer_appointments/{customer_id}")
async def legacy_customer_appointments(customer_id: int):
    conn = await get_conn()
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT a.*, b.name as barber_name, b.district, b.phone as barber_phone, b.avatar_url as barber_avatar, r.rating as my_rating FROM appointments a JOIN barbers b ON a.barber_id = b.id LEFT JOIN reviews r ON r.appointment_id = a.id AND r.customer_id = a.customer_id WHERE a.customer_id=%s ORDER BY a.appointment_time DESC",
                (customer_id,),
            )
            result = await cur.fetchall()
            rows = []
            for r in result:
                d = dict(r)
                d = serialize_datetime(d, ["appointment_time", "end_time", "created_at"])
                rows.append(d)
            return rows
    finally:
        await release_conn(conn)


@router.get("/barber_appointments/{barber_id}")
async def legacy_barber_appointments(barber_id: int):
    conn = await get_conn()
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT a.*, u.full_name as customer_name, u.phone as customer_phone FROM appointments a JOIN users u ON a.customer_id = u.id WHERE a.barber_id=%s ORDER BY a.appointment_time DESC",
                (barber_id,),
            )
            result = await cur.fetchall()
            rows = []
            for r in result:
                d = dict(r)
                d = serialize_datetime(d, ["appointment_time", "end_time", "created_at"])
                rows.append(d)
            return rows
    finally:
        await release_conn(conn)


@router.put("/update_appointment_status/{app_id}")
async def legacy_update_status(app_id: int, status: str):
    if status not in ("pending", "confirmed", "completed", "cancelled"):
        raise HTTPException(status_code=400, detail="Noto'g'ri status")
    conn = await get_conn()
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("UPDATE appointments SET status=%s WHERE id=%s", (status, app_id))
            await cur.execute(
                "SELECT a.customer_id, a.service_name, b.name as barber_name FROM appointments a JOIN barbers b ON a.barber_id=b.id WHERE a.id=%s",
                (app_id,),
            )
            appt = await cur.fetchone()
            if appt:
                msgs = {
                    "confirmed": ("Navbat tasdiqlandi", f"{appt['barber_name']} navbatingizni tasdiqladi"),
                    "completed": ("Xizmat yakunlandi", f"{appt['service_name']} muvaffaqiyatli yakunlandi"),
                    "cancelled": ("Navbat bekor qilindi", f"{appt['barber_name']} navbatingizni bekor qildi"),
                }
                if status in msgs:
                    title, body = msgs[status]
                    await cur.execute(
                        "INSERT INTO notifications (user_id, title, body, type) VALUES (%s,%s,%s,'appointment')",
                        (appt["customer_id"], title, body),
                    )
            await conn.commit()
            return {"status": "success"}
    finally:
        await release_conn(conn)


@router.put("/cancel_appointment/{app_id}")
async def legacy_cancel(app_id: int, customer_id: int):
    conn = await get_conn()
    try:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE appointments SET status='cancelled' WHERE id=%s AND customer_id=%s AND status='pending'",
                (app_id, customer_id),
            )
            if cur.rowcount == 0:
                raise HTTPException(status_code=400, detail="Bekor qilib bo'lmadi")
            await conn.commit()
            return {"status": "success"}
    finally:
        await release_conn(conn)


# ─── REVIEWS ──────────────────────────────────────────────────────────────────

class LegacyReviewCreate(BaseModel):
    appointment_id: int
    customer_id: int
    barber_id: int
    rating: int
    comment: Optional[str] = ""


@router.post("/add_review")
async def legacy_add_review(review: LegacyReviewCreate):
    conn = await get_conn()
    try:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id FROM reviews WHERE appointment_id=%s AND customer_id=%s", (review.appointment_id, review.customer_id))
            if await cur.fetchone():
                raise HTTPException(status_code=409, detail="Allaqachon baholangansiz")
            await cur.execute(
                "INSERT INTO reviews (appointment_id, customer_id, barber_id, rating, comment) VALUES (%s,%s,%s,%s,%s)",
                (review.appointment_id, review.customer_id, review.barber_id, review.rating, review.comment),
            )
            await cur.execute("SELECT AVG(rating) as avg_r, COUNT(*) as cnt FROM reviews WHERE barber_id=%s", (review.barber_id,))
            stats = await cur.fetchone()
            if stats and stats[0]:
                await cur.execute("UPDATE barbers SET rating=%s, total_reviews=%s WHERE id=%s", (round(float(stats[0]), 1), stats[1], review.barber_id))
            await conn.commit()
            return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        await conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await release_conn(conn)


@router.get("/barber_reviews/{barber_id}")
async def legacy_barber_reviews(barber_id: int, limit: int = 20):
    conn = await get_conn()
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT r.*, u.full_name as customer_name FROM reviews r JOIN users u ON r.customer_id=u.id WHERE r.barber_id=%s ORDER BY r.created_at DESC LIMIT %s",
                (barber_id, limit),
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


# ─── PAYMENTS ─────────────────────────────────────────────────────────────────

@router.post("/create_payment")
async def legacy_create_payment(payment: NewPaymentCreate):
    import datetime
    conn = await get_conn()
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT id, price, customer_id, payment_status FROM appointments WHERE id=%s", (payment.appointment_id,))
            appt = await cur.fetchone()
            if not appt:
                raise HTTPException(status_code=404, detail="Navbat topilmadi")
            if appt["payment_status"] == "paid":
                raise HTTPException(status_code=409, detail="Allaqachon to'langan")
            await cur.execute("INSERT INTO payments (appointment_id, amount, method, status) VALUES (%s,%s,%s,'pending')", (payment.appointment_id, payment.amount, payment.method))
            payment_id = cur.lastrowid
            if payment.method in ("click", "payme"):
                transaction_id = f"{payment.method.upper()}-{payment_id}-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
                await cur.execute("UPDATE payments SET status='completed', transaction_id=%s WHERE id=%s", (transaction_id, payment_id))
            else:
                await cur.execute("UPDATE payments SET status='completed' WHERE id=%s", (payment_id,))
            await cur.execute("UPDATE appointments SET payment_status='paid', payment_method=%s WHERE id=%s", (payment.method, payment.appointment_id))
            points = int(payment.amount // 50000)
            if points > 0:
                await cur.execute("UPDATE users SET loyalty_points = loyalty_points + %s WHERE id=%s", (points, appt["customer_id"]))
            await conn.commit()
            return {"status": "success", "payment_id": payment_id, "loyalty_points_earned": points}
    except HTTPException:
        raise
    except Exception as e:
        await conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await release_conn(conn)


@router.get("/payment_history/{customer_id}")
async def legacy_payment_history(customer_id: int):
    conn = await get_conn()
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT p.*, a.service_name, b.name as barber_name FROM payments p JOIN appointments a ON p.appointment_id = a.id JOIN barbers b ON a.barber_id = b.id WHERE a.customer_id=%s AND p.status='completed' ORDER BY p.created_at DESC",
                (customer_id,),
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


# ─── NOTIFICATIONS & FAVORITES ────────────────────────────────────────────────

@router.get("/notifications/{user_id}")
async def legacy_notifications(user_id: int):
    conn = await get_conn()
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT * FROM notifications WHERE user_id=%s ORDER BY created_at DESC LIMIT 50", (user_id,))
            result = await cur.fetchall()
            await cur.execute("SELECT COUNT(*) as cnt FROM notifications WHERE user_id=%s AND is_read=0", (user_id,))
            unread = (await cur.fetchone())["cnt"]
            rows = []
            for r in result:
                d = dict(r)
                d = serialize_datetime(d, ["created_at"])
                rows.append(d)
            return {"notifications": rows, "unread_count": unread}
    finally:
        await release_conn(conn)


@router.put("/mark_notifications_read/{user_id}")
async def legacy_mark_read(user_id: int):
    conn = await get_conn()
    try:
        async with conn.cursor() as cur:
            await cur.execute("UPDATE notifications SET is_read=1 WHERE user_id=%s", (user_id,))
            await conn.commit()
        return {"status": "success"}
    finally:
        await release_conn(conn)


@router.post("/toggle_favorite")
async def legacy_toggle_fav(customer_id: int, barber_id: int):
    conn = await get_conn()
    try:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id FROM favorites WHERE customer_id=%s AND barber_id=%s", (customer_id, barber_id))
            existing = await cur.fetchone()
            if existing:
                await cur.execute("DELETE FROM favorites WHERE customer_id=%s AND barber_id=%s", (customer_id, barber_id))
                await conn.commit()
                return {"status": "success", "is_favorite": False}
            else:
                await cur.execute("INSERT INTO favorites (customer_id, barber_id) VALUES (%s,%s)", (customer_id, barber_id))
                await conn.commit()
                return {"status": "success", "is_favorite": True}
    except Exception as e:
        try: await conn.rollback()
        except: pass
        return {"status": "error", "detail": str(e)}
    finally:
        await release_conn(conn)


@router.get("/favorites/{customer_id}")
async def legacy_favorites(customer_id: int):
    conn = await get_conn()
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT b.id, b.name, b.district, b.rating, b.specialization, b.is_online, b.avatar_url, b.lat, b.lng, b.total_reviews FROM favorites f JOIN barbers b ON f.barber_id=b.id WHERE f.customer_id=%s ORDER BY f.created_at DESC",
                (customer_id,),
            )
            return [dict(r) for r in await cur.fetchall()]
    finally:
        await release_conn(conn)


@router.get("/barber_stats/{barber_id}")
async def legacy_stats(barber_id: int):
    import datetime
    conn = await get_conn()
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            today = datetime.date.today()
            month_start = today.replace(day=1)
            await cur.execute("SELECT COUNT(*) as cnt FROM appointments WHERE barber_id=%s AND DATE(appointment_time)=%s AND status!='cancelled'", (barber_id, today))
            today_count = (await cur.fetchone())["cnt"]
            await cur.execute("SELECT COUNT(*) as cnt FROM appointments WHERE barber_id=%s AND status='completed'", (barber_id,))
            total_completed = (await cur.fetchone())["cnt"]
            await cur.execute("SELECT COALESCE(SUM(p.amount),0) as rev FROM payments p JOIN appointments a ON p.appointment_id=a.id WHERE a.barber_id=%s AND p.status='completed'", (barber_id,))
            revenue = float((await cur.fetchone())["rev"])
            await cur.execute("SELECT COALESCE(SUM(p.amount),0) as rev FROM payments p JOIN appointments a ON p.appointment_id=a.id WHERE a.barber_id=%s AND p.status='completed' AND DATE(p.created_at)>=%s", (barber_id, month_start))
            monthly_revenue = float((await cur.fetchone())["rev"])
            await cur.execute("SELECT COUNT(*) as cnt FROM appointments WHERE barber_id=%s AND status='pending'", (barber_id,))
            pending_count = (await cur.fetchone())["cnt"]
            await cur.execute("SELECT COALESCE(AVG(rating),5.0) as avg_r, COUNT(*) as cnt FROM reviews WHERE barber_id=%s", (barber_id,))
            review_stats = await cur.fetchone()
            return {"today_count": today_count, "total_completed": total_completed, "revenue": revenue, "monthly_revenue": monthly_revenue, "pending_count": pending_count, "avg_rating": round(float(review_stats["avg_r"]), 1), "total_reviews": review_stats["cnt"]}
    except Exception:
        return {"today_count": 0, "total_completed": 0, "revenue": 0, "monthly_revenue": 0, "pending_count": 0, "avg_rating": 5.0, "total_reviews": 0}
    finally:
        await release_conn(conn)
