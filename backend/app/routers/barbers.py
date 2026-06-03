"""
Barbers endpoints — sartaroshlar bilan ishlash
Public: ro'yxat, qidiruv, detail
Protected: profil yangilash, online status
"""
import os
import uuid
import shutil
import logging
import aiomysql
from typing import List
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Query

from app.database import get_conn, release_conn
from app.middleware.auth import require_auth, require_barber
from app.schemas.models import UpdateProfile, ServiceCreate, BlockedSlotCreate
from app.services.helpers import haversine, timedelta_to_str, serialize_datetime
from app.config import SERVER_BASE_URL, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, ALLOWED_EXTENSIONS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/barbers", tags=["Barbers"])


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/nearby")
async def get_nearby_barbers(
    user_lat: float,
    user_lng: float,
    radius_km: float = Query(2.0, ge=0.1, le=50.0),
    page: int = Query(1, ge=1),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
):
    """Yaqin atrofdagi sartaroshlar (masofa bo'yicha tartiblangan)"""
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

            # Online + masofa bo'yicha sort
            result.sort(key=lambda x: (not x["is_online"], x["distance"]))

            # Pagination
            total = len(result)
            start = (page - 1) * limit
            paginated = result[start : start + limit]

            return {
                "items": paginated,
                "total": total,
                "page": page,
                "limit": limit,
                "has_more": start + limit < total,
            }
    finally:
        await release_conn(conn)


@router.get("/all")
async def get_all_barbers(
    user_lat: float = 41.3111,
    user_lng: float = 69.2797,
    page: int = Query(1, ge=1),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
):
    """Barcha sartaroshlar"""
    conn = await get_conn()
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # Total count
            await cur.execute("SELECT COUNT(*) as cnt FROM barbers WHERE lat IS NOT NULL AND lng IS NOT NULL")
            total = (await cur.fetchone())["cnt"]

            offset = (page - 1) * limit
            await cur.execute(
                "SELECT id, name, district, rating, total_reviews, lat, lng, "
                "experience, specialization, phone, is_online, avatar_url, bio "
                "FROM barbers WHERE lat IS NOT NULL AND lng IS NOT NULL "
                "ORDER BY is_online DESC, rating DESC "
                "LIMIT %s OFFSET %s",
                (limit, offset),
            )
            barbers = await cur.fetchall()

            result = []
            for b in barbers:
                d = dict(b)
                d["distance"] = round(haversine(user_lat, user_lng, b["lat"], b["lng"]), 2)
                result.append(d)

            return {
                "items": result,
                "total": total,
                "page": page,
                "limit": limit,
                "has_more": offset + limit < total,
            }
    finally:
        await release_conn(conn)


@router.get("/search")
async def search_barbers(
    query: str = Query(..., min_length=1, max_length=100),
    page: int = Query(1, ge=1),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
):
    """Sartaroshlarni qidirish"""
    conn = await get_conn()
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            like = f"%{query}%"
            await cur.execute(
                "SELECT id, name, district, rating, total_reviews, lat, lng, "
                "experience, specialization, phone, is_online, avatar_url, bio "
                "FROM barbers "
                "WHERE name LIKE %s OR district LIKE %s OR specialization LIKE %s "
                "ORDER BY rating DESC "
                "LIMIT %s OFFSET %s",
                (like, like, like, limit, (page - 1) * limit),
            )
            result = await cur.fetchall()
            return [dict(b) for b in result]
    finally:
        await release_conn(conn)


@router.get("/{barber_id}")
async def get_barber_detail(barber_id: int):
    """Sartarosh to'liq ma'lumotlari (services, reviews, working_days bilan)"""
    conn = await get_conn()
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT b.*, u.email FROM barbers b "
                "JOIN users u ON b.user_id = u.id WHERE b.id=%s",
                (barber_id,),
            )
            barber = await cur.fetchone()
            if not barber:
                raise HTTPException(status_code=404, detail="Sartarosh topilmadi")

            # Working days
            await cur.execute(
                "SELECT day_of_week, is_working FROM barber_working_days "
                "WHERE barber_id=%s ORDER BY day_of_week",
                (barber_id,),
            )
            working_days = await cur.fetchall()

            # Services
            await cur.execute(
                "SELECT * FROM barber_services WHERE barber_id=%s AND is_active=1",
                (barber_id,),
            )
            services = await cur.fetchall()

            # Reviews (oxirgi 10 ta)
            await cur.execute(
                "SELECT r.*, u.full_name as customer_name "
                "FROM reviews r JOIN users u ON r.customer_id=u.id "
                "WHERE r.barber_id=%s ORDER BY r.created_at DESC LIMIT 10",
                (barber_id,),
            )
            reviews = await cur.fetchall()

            result = dict(barber)
            result["working_hours_start"] = timedelta_to_str(result.get("working_hours_start"))
            result["working_hours_end"] = timedelta_to_str(result.get("working_hours_end"))
            result["working_days"] = [dict(d) for d in working_days]
            result["services"] = [dict(s) for s in services]

            revs = []
            for r in reviews:
                rv = dict(r)
                rv = serialize_datetime(rv, ["created_at"])
                revs.append(rv)
            result["reviews"] = revs

            return result
    finally:
        await release_conn(conn)


# ═══════════════════════════════════════════════════════════════════════════════
# PROTECTED ENDPOINTS (Faqat o'z profilingiz uchun)
# ═══════════════════════════════════════════════════════════════════════════════


@router.put("/{barber_id}/profile")
async def update_barber_profile(
    barber_id: int,
    data: UpdateProfile,
    current_user: dict = Depends(require_auth),
):
    """Profil yangilash — faqat O'Z profilingiz"""
    conn = await get_conn()
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # Ownership check
            await cur.execute(
                "SELECT user_id FROM barbers WHERE id=%s", (barber_id,)
            )
            barber = await cur.fetchone()
            if not barber:
                raise HTTPException(status_code=404, detail="Sartarosh topilmadi")
            if barber["user_id"] != current_user["user_id"]:
                raise HTTPException(
                    status_code=403,
                    detail="Faqat o'z profilingizni o'zgartira olasiz",
                )

            fields, values = [], []
            if data.full_name:
                fields.append("name=%s")
                values.append(data.full_name)
            if data.phone:
                fields.append("phone=%s")
                values.append(data.phone)
            if data.bio is not None:
                fields.append("bio=%s")
                values.append(data.bio)
            if data.specialization:
                fields.append("specialization=%s")
                values.append(data.specialization)
            if data.experience:
                fields.append("experience=%s")
                values.append(data.experience)
            if data.working_hours_start:
                fields.append("working_hours_start=%s")
                values.append(data.working_hours_start)
            if data.working_hours_end:
                fields.append("working_hours_end=%s")
                values.append(data.working_hours_end)

            if fields:
                values.append(barber_id)
                await cur.execute(
                    f"UPDATE barbers SET {','.join(fields)} WHERE id=%s", values
                )
                await conn.commit()

            return {"status": "success"}
    finally:
        await release_conn(conn)


@router.put("/{barber_id}/online-status")
async def update_online_status(
    barber_id: int,
    is_online: bool,
    current_user: dict = Depends(require_auth),
):
    """Online statusni o'zgartirish"""
    conn = await get_conn()
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # Ownership check
            await cur.execute("SELECT user_id FROM barbers WHERE id=%s", (barber_id,))
            barber = await cur.fetchone()
            if not barber or barber["user_id"] != current_user["user_id"]:
                raise HTTPException(status_code=403, detail="Ruxsat yo'q")

            await cur.execute(
                "UPDATE barbers SET is_online=%s WHERE id=%s", (is_online, barber_id)
            )
            await conn.commit()
        return {"status": "success"}
    finally:
        await release_conn(conn)


@router.put("/{barber_id}/working-days")
async def update_working_days(
    barber_id: int,
    days: List[int],
    current_user: dict = Depends(require_auth),
):
    """Ish kunlarini yangilash"""
    conn = await get_conn()
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # Ownership check
            await cur.execute("SELECT user_id FROM barbers WHERE id=%s", (barber_id,))
            barber = await cur.fetchone()
            if not barber or barber["user_id"] != current_user["user_id"]:
                raise HTTPException(status_code=403, detail="Ruxsat yo'q")

            await cur.execute(
                "DELETE FROM barber_working_days WHERE barber_id=%s", (barber_id,)
            )
            for day in range(7):
                await cur.execute(
                    "INSERT INTO barber_working_days (barber_id, day_of_week, is_working) VALUES (%s, %s, %s)",
                    (barber_id, day, day in days),
                )
            await conn.commit()
            return {"status": "success"}
    finally:
        await release_conn(conn)


@router.post("/{barber_id}/avatar")
async def upload_avatar(
    barber_id: int,
    file: UploadFile = File(...),
    current_user: dict = Depends(require_auth),
):
    """Avatar yuklash"""
    conn = await get_conn()
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # Ownership check
            await cur.execute("SELECT user_id FROM barbers WHERE id=%s", (barber_id,))
            barber = await cur.fetchone()
            if not barber or barber["user_id"] != current_user["user_id"]:
                raise HTTPException(status_code=403, detail="Ruxsat yo'q")

        ext = os.path.splitext(file.filename)[-1].lower() if file.filename else ".jpg"
        if ext not in ALLOWED_EXTENSIONS:
            ext = ".jpg"

        filename = f"barber_{barber_id}_{uuid.uuid4().hex[:8]}{ext}"
        filepath = f"uploads/avatars/{filename}"

        os.makedirs("uploads/avatars", exist_ok=True)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        avatar_url = f"{SERVER_BASE_URL}/uploads/avatars/{filename}"

        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE barbers SET avatar_url=%s WHERE id=%s", (avatar_url, barber_id)
            )
            await conn.commit()

        return {"status": "success", "avatar_url": avatar_url}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Avatar upload xato: {e}")
        raise HTTPException(status_code=500, detail="Rasm yuklashda xato")
    finally:
        await release_conn(conn)


# ═══════════════════════════════════════════════════════════════════════════════
# SERVICES (Barber xizmatlari)
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/{barber_id}/services")
async def get_services(barber_id: int):
    """Barber xizmatlari ro'yxati"""
    conn = await get_conn()
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT * FROM barber_services WHERE barber_id=%s AND is_active=1 ORDER BY id",
                (barber_id,),
            )
            result = await cur.fetchall()
            return [dict(r) for r in result]
    finally:
        await release_conn(conn)


@router.post("/{barber_id}/services")
async def add_service(
    barber_id: int,
    service: ServiceCreate,
    current_user: dict = Depends(require_auth),
):
    """Yangi xizmat qo'shish"""
    conn = await get_conn()
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # Ownership check
            await cur.execute("SELECT user_id FROM barbers WHERE id=%s", (barber_id,))
            barber = await cur.fetchone()
            if not barber or barber["user_id"] != current_user["user_id"]:
                raise HTTPException(status_code=403, detail="Ruxsat yo'q")

            await cur.execute(
                "INSERT INTO barber_services (barber_id, service_name, price, duration_minutes, description) "
                "VALUES (%s, %s, %s, %s, %s)",
                (barber_id, service.name, service.price, service.duration, service.description),
            )
            await conn.commit()
        return {"status": "success", "service_id": cur.lastrowid}
    finally:
        await release_conn(conn)


@router.delete("/{barber_id}/services/{service_id}")
async def delete_service(
    barber_id: int,
    service_id: int,
    current_user: dict = Depends(require_auth),
):
    """Xizmatni o'chirish (soft delete)"""
    conn = await get_conn()
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # Ownership check
            await cur.execute("SELECT user_id FROM barbers WHERE id=%s", (barber_id,))
            barber = await cur.fetchone()
            if not barber or barber["user_id"] != current_user["user_id"]:
                raise HTTPException(status_code=403, detail="Ruxsat yo'q")

            await cur.execute(
                "UPDATE barber_services SET is_active=0 WHERE id=%s AND barber_id=%s",
                (service_id, barber_id),
            )
            await conn.commit()
        return {"status": "success"}
    finally:
        await release_conn(conn)


# ═══════════════════════════════════════════════════════════════════════════════
# BLOCKED SLOTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/{barber_id}/blocked-slots")
async def block_slot(
    barber_id: int,
    slot: BlockedSlotCreate,
    current_user: dict = Depends(require_auth),
):
    """Vaqt bloklash"""
    conn = await get_conn()
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT user_id FROM barbers WHERE id=%s", (barber_id,))
            barber = await cur.fetchone()
            if not barber or barber["user_id"] != current_user["user_id"]:
                raise HTTPException(status_code=403, detail="Ruxsat yo'q")

            await cur.execute(
                "INSERT INTO barber_blocked_slots (barber_id, blocked_date, start_time, end_time, reason) "
                "VALUES (%s, %s, %s, %s, %s)",
                (barber_id, slot.blocked_date, slot.start_time, slot.end_time, slot.reason),
            )
            await conn.commit()
        return {"status": "success"}
    finally:
        await release_conn(conn)


@router.get("/{barber_id}/blocked-slots")
async def get_blocked_slots(barber_id: int, date: str):
    """Bloklangan vaqtlar"""
    conn = await get_conn()
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT * FROM barber_blocked_slots WHERE barber_id=%s AND blocked_date=%s",
                (barber_id, date),
            )
            result = await cur.fetchall()
            return [dict(r) for r in result]
    finally:
        await release_conn(conn)


# ═══════════════════════════════════════════════════════════════════════════════
# STATISTICS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/{barber_id}/stats")
async def get_barber_stats(
    barber_id: int,
    current_user: dict = Depends(require_auth),
):
    """Barber statistikasi"""
    import datetime

    conn = await get_conn()
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            today = datetime.date.today()
            month_start = today.replace(day=1)

            await cur.execute(
                "SELECT COUNT(*) as cnt FROM appointments WHERE barber_id=%s AND DATE(appointment_time)=%s AND status!='cancelled'",
                (barber_id, today),
            )
            today_count = (await cur.fetchone())["cnt"]

            await cur.execute(
                "SELECT COUNT(*) as cnt FROM appointments WHERE barber_id=%s AND status='completed'",
                (barber_id,),
            )
            total_completed = (await cur.fetchone())["cnt"]

            await cur.execute(
                "SELECT COALESCE(SUM(p.amount),0) as rev FROM payments p "
                "JOIN appointments a ON p.appointment_id=a.id "
                "WHERE a.barber_id=%s AND p.status='completed'",
                (barber_id,),
            )
            revenue = float((await cur.fetchone())["rev"])

            await cur.execute(
                "SELECT COALESCE(SUM(p.amount),0) as rev FROM payments p "
                "JOIN appointments a ON p.appointment_id=a.id "
                "WHERE a.barber_id=%s AND p.status='completed' AND DATE(p.created_at)>=%s",
                (barber_id, month_start),
            )
            monthly_revenue = float((await cur.fetchone())["rev"])

            await cur.execute(
                "SELECT COUNT(*) as cnt FROM appointments WHERE barber_id=%s AND status='pending'",
                (barber_id,),
            )
            pending_count = (await cur.fetchone())["cnt"]

            await cur.execute(
                "SELECT COALESCE(AVG(rating),5.0) as avg_r, COUNT(*) as cnt FROM reviews WHERE barber_id=%s",
                (barber_id,),
            )
            review_stats = await cur.fetchone()

            return {
                "today_count": today_count,
                "total_completed": total_completed,
                "revenue": revenue,
                "monthly_revenue": monthly_revenue,
                "pending_count": pending_count,
                "avg_rating": round(float(review_stats["avg_r"]), 1),
                "total_reviews": review_stats["cnt"],
            }
    except Exception:
        return {
            "today_count": 0, "total_completed": 0, "revenue": 0,
            "monthly_revenue": 0, "pending_count": 0, "avg_rating": 5.0, "total_reviews": 0,
        }
    finally:
        await release_conn(conn)
