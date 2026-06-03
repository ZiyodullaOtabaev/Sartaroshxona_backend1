import 'dart:io';

/// Ilova konfiguratsiyasi
/// Production'da bu qiymatlarni environment variables orqali o'zgartiring
class AppConstants {
  AppConstants._();

  // ─── API CONFIG ───────────────────────────────────────────────────────────
  /// Backend server manzili
  ///
  /// MUHIM: Bu yerga kompyuteringizning HAQIQIY Wi-Fi IP manzilini yozing!
  /// Qanday topish:
  ///   Windows: CMD da -> ipconfig -> Wi-Fi IPv4 Address
  ///   Mac: Terminal -> ifconfig | grep inet
  ///   Linux: Terminal -> hostname -I
  ///
  /// Emulator uchun: Android emulator -> 10.0.2.2:8000
  /// Haqiqiy telefon uchun: Kompyuter IP (masalan 192.168.1.100:8000)
  ///
  /// --dart-define=API_BASE_URL=http://your-ip:8000 bilan override qilsa bo'ladi
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://192.168.1.100:8000', // ← O'ZGARTIRING: o'z IP manzilingiz
  );

  /// API so'rovlar uchun timeout (sekundlarda)
  /// Sekin internet uchun 20 sekund — yetarli
  static const int requestTimeoutSeconds = 20;

  /// Retry urinishlar soni
  static const int maxRetryAttempts = 2;

  // ─── APP INFO ─────────────────────────────────────────────────────────────
  static const String appName = 'Sartaroshxona';
  static const String appVersion = '4.0.0';
  static const String buildNumber = '15';

  // ─── MAP CONFIG ───────────────────────────────────────────────────────────
  /// Default joylashuv (Toshkent markazi)
  static const double defaultLat = 41.3111;
  static const double defaultLng = 69.2797;

  /// Default qidiruv radiusi (km)
  static const double defaultSearchRadiusKm = 2.0;

  // ─── PAGINATION ───────────────────────────────────────────────────────────
  static const int defaultPageSize = 20;
  static const int maxPageSize = 50;

  // ─── VALIDATION ───────────────────────────────────────────────────────────
  static const int minPasswordLength = 6;
  static const int maxNameLength = 100;
  static const int maxBioLength = 500;

  // ─── STORAGE KEYS ─────────────────────────────────────────────────────────
  static const String tokenKey = 'auth_token';
  static const String userIdKey = 'user_id';
  static const String userRoleKey = 'user_role';
  static const String userNameKey = 'user_name';
  static const String barberIdKey = 'barber_id';
  static const String themeKey = 'app_theme';
  static const String onboardingKey = 'onboarding_completed';

  // ─── CONTACT INFO ─────────────────────────────────────────────────────────
  static const String supportPhone = '+998 90 000 00 00';
  static const String supportEmail = 'support@sartaroshxona.uz';
  static const String developerName = 'Sartaroshxona Team';
  static const String telegramChannel = '@sartaroshxona_uz';
}
