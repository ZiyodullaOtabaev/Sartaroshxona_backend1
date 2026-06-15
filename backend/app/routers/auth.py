"""
Auth endpoints — Register, Login, Change Password
"""
import logging
import aiomysql
from fastapi import APIRouter, HTTPException, Depends, status
from passlib.context import CryptContext

from app.database import get_conn, release_conn
from app.middleware.auth import create_access_token, require_auth
from app.schemas.models import UserRegister, UserLogin, ChangePassword
from app.services.helpers import timedelta_to_str

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/register")
async def register(user: UserRegister):
    """Yangi foydalanuvchi ro'yxatdan o'tishi"""
    conn = await get_conn()
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # Email mavjudligini tekshirish
            await cur.execute("SELECT id FROM users WHERE email=%s", (user.email,))
            if await cur.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Bu email allaqachon ro'yxatdan o'tgan",
                )

            # Parolni hash qilish
            hashed_password = pwd_context.hash(user.password)

            # User yaratish
            await cur.execute(
                "INSERT INTO users (full_name, email, password_hash, role, phone) "
                "VALUES (%s, %s, %s, %s, %s)",
                (user.full_name, user.email, hashed_password, user.role, user.phone),
            )
            user_id = cur.lastrowid

            barber_id = None
            salon_id = None

            # Barber role uchun barbers jadvaliga yozish
            if user.role == "barber":
                await cur.execute(
                    "INSERT INTO barbers (user_id, name, experience, phone, specialization, bio, lat, lng, rating, total_reviews, district) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 5.0, 0, 'Toshkent')",
                    (
                        user_id,
                        user.full_name,
                        user.experience or "",
                        user.phone,
                        user.specialization or "",
                        user.bio or "",
                        user.lat,
                        user.lng,
                    ),
                )
                barber_id = cur.lastrowid

                # Default working days (Dushanba-Shanba)
                for day in range(1, 7):
                    await cur.execute(
                        "INSERT INTO barber_working_days (barber_id, day_of_week, is_working) VALUES (%s, %s, 1)",
                        (barber_id, day),
                    )

            # Owner role uchun salon yaratish
            elif user.role == "owner":
                salon_name = user.salon_name or f"{user.full_name} sartaroshxonasi"
                await cur.execute(
                    "INSERT INTO salons (owner_id, name, address, phone, lat, lng, description) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (
                        user_id,
                        salon_name,
                        user.salon_address or "",
                        user.phone,
                        user.lat,
                        user.lng,
                        user.bio or "",
                    ),
                )
                salon_id = cur.lastrowid

                # Owner o'zi ham sartarosh bo'lib ishlashni xohlasa
                if user.also_barber:
                    await cur.execute(
                        "INSERT INTO barbers (user_id, salon_id, name, experience, phone, specialization, bio, lat, lng, rating, total_reviews, district) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 5.0, 0, 'Toshkent')",
                        (
                            user_id, salon_id, user.full_name,
                            user.experience or "", user.phone,
                            user.specialization or "", user.bio or "",
                            user.lat, user.lng,
                        ),
                    )
                    barber_id = cur.lastrowid
                    for day in range(1, 7):
                        await cur.execute(
                            "INSERT INTO barber_working_days (barber_id, day_of_week, is_working) VALUES (%s, %s, 1)",
                            (barber_id, day),
                        )

            await conn.commit()

            # Token yaratish
            token = create_access_token({
                "user_id": user_id,
                "role": user.role,
                "email": user.email,
            })

            logger.info(f"Yangi user ro'yxatdan o'tdi: {user.email} (role={user.role})")

            return {
                "status": "success",
                "user_id": user_id,
                "barber_id": barber_id,
                "salon_id": salon_id,
                "token": token,
            }

    except HTTPException:
        raise
    except Exception as e:
        await conn.rollback()
        logger.error(f"Register xato: {e}")
        raise HTTPException(status_code=500, detail="Ro'yxatdan o'tishda xatolik")
    finally:
        await release_conn(conn)


@router.post("/login")
async def login(user: UserLogin):
    """Foydalanuvchi login"""
    conn = await get_conn()
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT u.id, u.full_name, u.email, u.password_hash, u.role, u.phone, "
                "u.loyalty_points, b.id as barber_id, b.salon_id as barber_salon_id, "
                "b.is_online, b.rating, b.specialization, b.bio, b.avatar_url, "
                "b.working_hours_start, b.working_hours_end, "
                "s.id as owned_salon_id, s.name as salon_name "
                "FROM users u "
                "LEFT JOIN barbers b ON u.id = b.user_id "
                "LEFT JOIN salons s ON u.id = s.owner_id "
                "WHERE u.email=%s",
                (user.email,),
            )
            db_user = await cur.fetchone()

            if not db_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Email yoki parol noto'g'ri",
                )

            if not pwd_context.verify(user.password, db_user["password_hash"]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Email yoki parol noto'g'ri",
                )

            # Parol hash'ni javobdan olib tashlash
            db_user.pop("password_hash", None)

            # Token yaratish
            token = create_access_token({
                "user_id": db_user["id"],
                "role": db_user["role"],
                "email": db_user["email"],
            })

            # Timedelta -> string
            if db_user.get("working_hours_start"):
                db_user["working_hours_start"] = timedelta_to_str(db_user["working_hours_start"])
            if db_user.get("working_hours_end"):
                db_user["working_hours_end"] = timedelta_to_str(db_user["working_hours_end"])

            logger.info(f"User login: {user.email}")

            return {"status": "success", "token": token, "user": db_user}

    finally:
        await release_conn(conn)


@router.post("/change-password")
async def change_password(data: ChangePassword, current_user: dict = Depends(require_auth)):
    """Parolni o'zgartirish — faqat o'z parolingizni"""
    conn = await get_conn()
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT password_hash FROM users WHERE id=%s",
                (current_user["user_id"],),
            )
            user = await cur.fetchone()
            if not user:
                raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")

            if not pwd_context.verify(data.current_password, user["password_hash"]):
                raise HTTPException(status_code=400, detail="Joriy parol noto'g'ri")

            new_hash = pwd_context.hash(data.new_password)
            await cur.execute(
                "UPDATE users SET password_hash=%s WHERE id=%s",
                (new_hash, current_user["user_id"]),
            )
            await conn.commit()

            return {"status": "success", "message": "Parol muvaffaqiyatli o'zgartirildi"}
    finally:
        await release_conn(conn)
