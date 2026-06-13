-- ═══════════════════════════════════════════════════════════════════════════
-- MIGRATION 002: CRM Tizimi — Sartaroshxona (Salon) boshqaruvi
--
-- Yangiliklar:
--   1. 'owner' (sartaroshxona egasi) roli
--   2. salons jadvali — sartaroshxona muassasasi
--   3. barbers.salon_id — sartarosh qaysi salonda ishlaydi (faqat bitta)
--   4. salon_invitations — dinamik taklif/so'rov tizimi
--
-- Ishlatish: MySQL Workbench'da BIR MARTA run qiling.
-- ═══════════════════════════════════════════════════════════════════════════

USE sartaroshxona_db;

-- ─── 1. users.role enum'ga 'owner' qo'shish ─────────────────────────────────
ALTER TABLE users
    MODIFY COLUMN role ENUM('customer', 'barber', 'owner') NOT NULL DEFAULT 'customer';


-- ─── 2. SALONS — Sartaroshxona muassasasi ───────────────────────────────────
CREATE TABLE IF NOT EXISTS salons (
    id INT AUTO_INCREMENT PRIMARY KEY,

    owner_id INT NOT NULL,                          -- egasi (users.id)

    name VARCHAR(150) NOT NULL,                     -- sartaroshxona nomi
    description TEXT,                                -- tavsif
    address VARCHAR(255),                           -- to'liq manzil
    district VARCHAR(100) DEFAULT 'Toshkent',       -- tuman/shahar

    lat DOUBLE,                                      -- joylashuv
    lng DOUBLE,

    phone VARCHAR(30),                               -- aloqa raqami
    avatar_url VARCHAR(255),                         -- logo
    cover_url VARCHAR(255),                          -- muqova rasmi

    working_hours_start TIME DEFAULT '09:00:00',
    working_hours_end TIME DEFAULT '20:00:00',

    rating FLOAT DEFAULT 5.0,
    total_reviews INT DEFAULT 0,

    is_active BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
);


-- ─── 3. barbers jadvaliga salon bog'lanishi ─────────────────────────────────
-- salon_id NULL bo'lsa => mustaqil sartarosh
-- salon_id to'ldirilgan bo'lsa => shu salonda ishlaydi (faqat bitta)
ALTER TABLE barbers
    ADD COLUMN salon_id INT NULL AFTER user_id;

ALTER TABLE barbers
    ADD COLUMN is_accepting_bookings BOOLEAN DEFAULT TRUE AFTER is_online;

ALTER TABLE barbers
    ADD CONSTRAINT fk_barber_salon
    FOREIGN KEY (salon_id) REFERENCES salons(id) ON DELETE SET NULL;

CREATE INDEX idx_barbers_salon ON barbers(salon_id);


-- ─── 4. SALON_INVITATIONS — dinamik taklif/so'rov ──────────────────────────
-- initiated_by = 'owner'  => rahbar sartaroshni taklif qildi
-- initiated_by = 'barber' => sartarosh salonga qo'shilishni so'radi
CREATE TABLE IF NOT EXISTS salon_invitations (
    id INT AUTO_INCREMENT PRIMARY KEY,

    salon_id INT NOT NULL,
    barber_id INT NOT NULL,

    initiated_by ENUM('owner', 'barber') NOT NULL,

    status ENUM('pending', 'accepted', 'rejected', 'cancelled') DEFAULT 'pending',

    message VARCHAR(255),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    responded_at TIMESTAMP NULL,

    FOREIGN KEY (salon_id) REFERENCES salons(id) ON DELETE CASCADE,
    FOREIGN KEY (barber_id) REFERENCES barbers(id) ON DELETE CASCADE,

    INDEX idx_invitation_salon (salon_id, status),
    INDEX idx_invitation_barber (barber_id, status)
);


-- ─── 5. Daromad analitikasi uchun indexlar ──────────────────────────────────
-- Owner dashboard: salon bo'yicha to'lovlarni tez yig'ish
CREATE INDEX idx_payments_status_date ON payments(status, created_at);
