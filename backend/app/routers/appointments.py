"""
Appointments endpoints — navbatlar boshqaruvi
Booking, cancel, status update, available slots
"""
import datetime
import logging
import aiomysql
from fastapi import APIRouter, HTTPException, Depends, Query

from app.database import get_conn, release_conn
from app.middleware.auth import require_auth
from app.schemas.models import AppointmentCreate
from app.services.helpers import serialize_datetime, timedelta_to_str
from app.config import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.post("/book")
async def book_appointment(
    appt: AppointmentCreate,
    current_user: dict = Depends(require_auth),
):
    """Navbat olish — faqat O'ZIM uchun"""
    customer_id = current_user["user_id"]
    conn = await get_conn()
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # Barber mavjudligini tekshirish
            await cur.execute("SELECT id FROM barbers WHERE id=%s", (appt.barber_id,))
            if not await cur.fetchone():
                raise HTTPException(status_code=404, detail="Sartarosh topilmadi")

            # Duration hisoblash
            duration = 30
            if appt.service_id:
                await cur.execute(
                    "SELECT duration_minutes FROM barber_services WHERE id=%s",
                    (appt.service_id,),
                )
                svc = await cur.fetchone()
                if svc:
                    duration = svc["duration_minutes"]

            apt_dt = datetime.datetime.fromisoformat(appt.appointment_time)
            end_dt = apt_dt + datetime.timedelta(minutes=duration)

            # Conflict tekshirish
            await cur.execute(
                "SELECT id FROM appointments "
                "WHERE barber_id=%s AND status NOT IN ('cancelled') "
                "AND appointment_time < %s AND end_time > %s",
                (appt.barber_id, end_dt.strftime("%Y-%m-%d %H:%M:%S"), apt_dt.strftime("%Y-%m-%d %H:%M:%S")),
            )
            if await cur.fetchone():
                raise HTTPException(status_code=409, detail="Bu vaqt band! Boshqa vaqt tanlang.")

            # Navbat yaratish
            await cur.execute(
                "INSERT INTO appointments (customer_id, barber_id, service_id, appointment_time, end_time, service_name, price, status, notes) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending', %s)",
                (
                    customer_id, appt.barber_id, appt.service_id,
                    appt.appointment_time, end_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    appt.service_name, appt.price, appt.notes,
                ),
            )
            appt_id = cur.lastrowid

            # Notification barber'ga
            await cur.execute("SELECT full_name FROM users WHERE id=%s", (customer_id,))
            customer = await cur.fetchone()
            await cur.execute(
                "SELECT u.id FROM users u JOIN barbers b ON u.id=b.user_id WHERE b.id=%s",
                (appt.barber_id,),
            )
            barber_user = await cur.fetchone()

            if barber_user:
                cust_name = customer["full_name"] if customer else "Mijoz"
                await cur.execute(
                    "INSERT INTO notifications (user_id, title, body, type) VALUES (%s, %s, %s, 'appointment')",
                    (barber_user["id"], "Yangi navbat!", f"{cust_name} navbat oldi: {appt.service_name}"),
                )

            await conn.commit()
            return {"status": "success", "appointment_id": appt_id}

    except HTTPException:
        raise
    except Exception as e:
        await conn.rollback()
        logger.error(f"Booking xato: {e}")
        raise HTTPException(status_code=500, detail="Navbat olishda xatolik")
    finally:
        await release_conn(conn)


@router.get("/my")
async def get_my_appointments(
    current_user: dict = Depends(require_auth),
    page: int = Query(1, ge=1),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
):
    """Mening navbatlarim (customer sifatida)"""
    conn = await get_conn()
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            offset = (page - 1) * limit
            await cur.execute(
                "SELECT a.*, b.name as barber_name, b.district, b.phone as barber_phone, "
                "b.avatar_url as barber_avatar, r.rating as my_rating "
                "FROM appointments a "
                "JOIN barbers b ON a.barber_id = b.id "
                "LEFT JOIN reviews r ON r.appointment_id = a.id AND r.customer_id = a.customer_id "
                "WHERE a.customer_id=%s "
                "ORDER BY a.appointment_time DESC LIMIT %s OFFSET %s",
                (current_user["user_id"], limit, offset),
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


@router.get("/barber/{barber_id}")
async def get_barber_appointments(
    barber_id: int,
    current_user: dict = Depends(require_auth),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
):
    """Barber navbatlari — faqat O'Z navbatlaringiz"""
    conn = await get_conn()
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # Ownership check
            await cur.execute("SELECT user_id FROM barbers WHERE id=%s", (barber_id,))
            barber = await cur.fetchone()
            if not barber or barber["user_id"] != current_user["user_id"]:
                raise HTTPException(status_code=403, detail="Ruxsat yo'q")

            offset = (page - 1) * limit
            await cur.execute(
                "SELECT a.*, u.full_name as customer_name, u.phone as customer_phone "
                "FROM appointments a JOIN users u ON a.customer_id = u.id "
                "WHERE a.barber_id=%s ORDER BY a.appointment_time DESC "
                "LIMIT %s OFFSET %s",
                (barber_id, limit, offset),
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


@router.put("/{app_id}/status")
async def update_appointment_status(
    app_id: int,
    status_val: str = Query(..., alias="status", pattern="^(pending|confirmed|completed|cancelled)$"),
    current_user: dict = Depends(require_auth),
):
    """Status yangilash — barber faqat o'z navbatlarini"""
    conn = await get_conn()
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # Appointment topish va tekshirish
            await cur.execute(
                "SELECT a.barber_id, a.customer_id, a.service_name, b.user_id as barber_user_id, b.name as barber_name "
                "FROM appointments a JOIN barbers b ON a.barber_id=b.id WHERE a.id=%s",
                (app_id,),
            )
            appt = await cur.fetchone()
            if not appt:
                raise HTTPException(status_code=404, detail="Navbat topilmadi")

            # Barber yoki customer o'zi bo'lishi kerak
            if current_user["user_id"] not in (appt["barber_user_id"], appt["customer_id"]):
                raise HTTPException(status_code=403, detail="Ruxsat yo'q")

            await cur.execute(
                "UPDATE appointments SET status=%s WHERE id=%s", (status_val, app_id)
            )

            # Notification
            msgs = {
                "confirmed": ("Navbat tasdiqlandi", f"{appt['barber_name']} navbatingizni tasdiqladi"),
                "completed": ("Xizmat yakunlandi", f"{appt['service_name']} muvaffaqiyatli yakunlandi"),
                "cancelled": ("Navbat bekor qilindi", f"Navbat bekor qilindi"),
            }
            if status_val in msgs:
                title, body = msgs[status_val]
                await cur.execute(
                    "INSERT INTO notifications (user_id, title, body, type) VALUES (%s, %s, %s, 'appointment')",
                    (appt["customer_id"], title, body),
                )

            await conn.commit()
            return {"status": "success"}
    finally:
        await release_conn(conn)


@router.put("/{app_id}/cancel")
async def cancel_appointment(
    app_id: int,
    current_user: dict = Depends(require_auth),
):
    """Navbatni bekor qilish — faqat o'zim"""
    conn = await get_conn()
    try:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE appointments SET status='cancelled' "
                "WHERE id=%s AND customer_id=%s AND status='pending'",
                (app_id, current_user["user_id"]),
            )
            if cur.rowcount == 0:
                raise HTTPException(status_code=400, detail="Bekor qilib bo'lmadi")
            await conn.commit()
            return {"status": "success"}
    finally:
        await release_conn(conn)


@router.get("/available-slots/{barber_id}")
async def get_available_slots(barber_id: int, date: str):
    """Mavjud vaqtlar (public)"""
    conn = await get_conn()
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT working_hours_start, working_hours_end, slot_duration_minutes "
                "FROM barbers WHERE id=%s",
                (barber_id,),
            )
            barber = await cur.fetchone()
            if not barber:
                raise HTTPException(status_code=404, detail="Barber topilmadi")

            target_date = datetime.date.fromisoformat(date)
            day_of_week = target_date.isoweekday() % 7

            await cur.execute(
                "SELECT is_working FROM barber_working_days WHERE barber_id=%s AND day_of_week=%s",
                (barber_id, day_of_week),
            )
            wd = await cur.fetchone()
            if wd and not wd["is_working"]:
                return {"date": date, "slots": [], "message": "Dam olish kuni"}

            # Booked slots
            await cur.execute(
                "SELECT appointment_time, end_time FROM appointments "
                "WHERE barber_id=%s AND DATE(appointment_time)=%s AND status NOT IN ('cancelled')",
                (barber_id, date),
            )
            booked = await cur.fetchall()

            # Blocked slots
            await cur.execute(
                "SELECT start_time, end_time FROM barber_blocked_slots "
                "WHERE barber_id=%s AND blocked_date=%s",
                (barber_id, date),
            )
            blocked = await cur.fetchall()

            def td_to_minutes(td):
                if isinstance(td, datetime.timedelta):
                    return int(td.total_seconds()) // 60
                if isinstance(td, (datetime.datetime, datetime.time)):
                    return td.hour * 60 + td.minute
                if isinstance(td, str) and ":" in td:
                    h, m = map(int, td.split(":")[:2])
                    return h * 60 + m
                return 0

            start_min = td_to_minutes(barber["working_hours_start"])
            end_min = td_to_minutes(barber["working_hours_end"])
            slot_dur = barber["slot_duration_minutes"] or 30

            booked_ranges = []
            for b in booked:
                s_td = b["appointment_time"]
                e_td = b["end_time"]
                if hasattr(s_td, "hour"):
                    s = s_td.hour * 60 + s_td.minute
                elif hasattr(s_td, "strftime"):
                    t = s_td.strftime("%H:%M")
                    h, m = map(int, t.split(":"))
                    s = h * 60 + m
                else:
                    s = td_to_minutes(s_td)
                if e_td and hasattr(e_td, "hour"):
                    e = e_td.hour * 60 + e_td.minute
                elif e_td and hasattr(e_td, "strftime"):
                    t = e_td.strftime("%H:%M")
                    h, m = map(int, t.split(":"))
                    e = h * 60 + m
                else:
                    e = s + slot_dur
                booked_ranges.append((s, e))

            for bl in blocked:
                s = td_to_minutes(bl["start_time"])
                e = td_to_minutes(bl["end_time"])
                booked_ranges.append((s, e))

            now = datetime.datetime.now()
            current_min = now.hour * 60 + now.minute if target_date == now.date() else 0

            slots = []
            t = start_min
            while t + slot_dur <= end_min:
                if t > current_min:
                    is_free = all(not (t < be and t + slot_dur > bs) for bs, be in booked_ranges)
                    h, m = t // 60, t % 60
                    slots.append({"time": f"{h:02d}:{m:02d}", "is_available": is_free})
                t += slot_dur

            return {"date": date, "slots": slots}
    finally:
        await release_conn(conn)
