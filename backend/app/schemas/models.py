"""
Pydantic models — API request/response validation
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional


# ═══════════════════════════════════════════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════════════════════════════════════════

class UserRegister(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    role: str = Field(..., pattern="^(customer|barber|owner)$")
    phone: str = Field(default="", max_length=30)
    experience: Optional[str] = None
    specialization: Optional[str] = None
    bio: Optional[str] = Field(None, max_length=500)
    lat: Optional[float] = None
    lng: Optional[float] = None
    # Owner ro'yxatdan o'tganda salon ma'lumotlari (ixtiyoriy)
    salon_name: Optional[str] = Field(None, max_length=150)
    salon_address: Optional[str] = Field(None, max_length=255)
    # Owner o'zi ham sartarosh bo'lib ishlashni xohlasa
    also_barber: bool = False


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class ChangePassword(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6, max_length=128)


# ═══════════════════════════════════════════════════════════════════════════════
# PROFILE
# ═══════════════════════════════════════════════════════════════════════════════

class UpdateProfile(BaseModel):
    full_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=30)
    bio: Optional[str] = Field(None, max_length=500)
    specialization: Optional[str] = Field(None, max_length=150)
    experience: Optional[str] = Field(None, max_length=100)
    working_hours_start: Optional[str] = None
    working_hours_end: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# APPOINTMENTS
# ═══════════════════════════════════════════════════════════════════════════════

class AppointmentCreate(BaseModel):
    barber_id: int
    service_id: Optional[int] = None
    appointment_time: str
    service_name: str = Field(..., max_length=100)
    price: float = Field(..., ge=0)
    notes: Optional[str] = Field("", max_length=500)


# ═══════════════════════════════════════════════════════════════════════════════
# REVIEWS
# ═══════════════════════════════════════════════════════════════════════════════

class ReviewCreate(BaseModel):
    appointment_id: int
    barber_id: int
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field("", max_length=500)


# ═══════════════════════════════════════════════════════════════════════════════
# PAYMENTS
# ═══════════════════════════════════════════════════════════════════════════════

class PaymentCreate(BaseModel):
    appointment_id: int
    amount: float = Field(..., gt=0)
    method: str = Field(..., pattern="^(cash|card|click|payme)$")


# ═══════════════════════════════════════════════════════════════════════════════
# SERVICES
# ═══════════════════════════════════════════════════════════════════════════════

class ServiceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    price: float = Field(..., gt=0)
    duration: int = Field(30, ge=5, le=480)
    description: str = Field("", max_length=255)


# ═══════════════════════════════════════════════════════════════════════════════
# BLOCKED SLOTS
# ═══════════════════════════════════════════════════════════════════════════════

class BlockedSlotCreate(BaseModel):
    blocked_date: str
    start_time: str
    end_time: str
    reason: Optional[str] = Field("", max_length=150)



# ═══════════════════════════════════════════════════════════════════════════════
# CRM — SALONS (Sartaroshxona muassasasi)
# ═══════════════════════════════════════════════════════════════════════════════

class SalonCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    description: Optional[str] = Field(None, max_length=1000)
    address: Optional[str] = Field(None, max_length=255)
    district: str = Field("Toshkent", max_length=100)
    lat: Optional[float] = None
    lng: Optional[float] = None
    phone: Optional[str] = Field(None, max_length=30)
    working_hours_start: Optional[str] = None
    working_hours_end: Optional[str] = None


class SalonUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    description: Optional[str] = Field(None, max_length=1000)
    address: Optional[str] = Field(None, max_length=255)
    district: Optional[str] = Field(None, max_length=100)
    lat: Optional[float] = None
    lng: Optional[float] = None
    phone: Optional[str] = Field(None, max_length=30)
    working_hours_start: Optional[str] = None
    working_hours_end: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# CRM — STAFF / INVITATIONS (Dinamik bog'lanish)
# ═══════════════════════════════════════════════════════════════════════════════

class StaffInvite(BaseModel):
    """Rahbar sartaroshni taklif qiladi (email yoki barber_id orqali)"""
    barber_id: Optional[int] = None
    barber_email: Optional[EmailStr] = None
    message: Optional[str] = Field("", max_length=255)


class JoinRequest(BaseModel):
    """Sartarosh salonga qo'shilishni so'raydi"""
    salon_id: int
    message: Optional[str] = Field("", max_length=255)


class InvitationResponse(BaseModel):
    """Taklif/so'rovga javob (qabul/rad)"""
    accept: bool
