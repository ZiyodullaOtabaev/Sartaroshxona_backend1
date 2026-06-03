-- ═══════════════════════════════════════════════════════════
-- DATABASE MIGRATION: Yetishmagan constraintlarni qo'shish
-- Bu faylni MySQL Workbench da run qiling
-- ═══════════════════════════════════════════════════════════

USE sartaroshxona_db;

-- 1. Reviews jadvaliga UNIQUE constraint (bir appointment uchun bir baho)
ALTER TABLE reviews
ADD UNIQUE KEY unique_review (appointment_id, customer_id);

-- 2. Rating validation (1-5 orasida)
-- MySQL 8.0+ uchun CHECK constraint
ALTER TABLE reviews
ADD CONSTRAINT chk_rating CHECK (rating BETWEEN 1 AND 5);

-- 3. Barbers jadvaliga index — is_online bo'yicha tez qidirish
CREATE INDEX idx_barbers_online ON barbers(is_online, rating DESC);

-- 4. Appointments jadvaliga index — status bo'yicha
CREATE INDEX idx_appointments_status ON appointments(status, appointment_time);

-- 5. Working days — UNIQUE (bir barber uchun bir kun)
ALTER TABLE barber_working_days
ADD UNIQUE KEY unique_barber_day (barber_id, day_of_week);

-- 6. Blocked slots — index
CREATE INDEX idx_blocked_slots ON barber_blocked_slots(barber_id, blocked_date);
