/// Ilova konfiguratsiyasi
/// Production'da bu qiymatlarni environment variables orqali o'zgartiring
class AppConstants {
  AppConstants._();

  // ─── API CONFIG ───────────────────────────────────────────────────────────
  /// Backend server manzili
  /// Local test: "http://192.168.10.4:8000"
  /// Production: "https://your-domain.com/api"
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.58.203.122:8000',  // ← Sizning lokal IP
  );



  /// API so'rovlar uchun timeout (sekundlarda)
  static const int requestTimeoutSeconds = 15;

  // ─── APP INFO ─────────────────────────────────────────────────────────────
  static const String appName = 'Sartaroshxona';
  static const String appVersion = '3.1.0';
  static const String buildNumber = '10';

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
  static const int minPasswordLength = 8;
  static const int maxNameLength = 100;
  static const int maxBioLength = 500;

  // ─── STORAGE KEYS ─────────────────────────────────────────────────────────
  static const String tokenKey = 'auth_token';
  static const String userIdKey = 'user_id';
  static const String userRoleKey = 'user_role';
  static const String userNameKey = 'user_name';
  static const String themeKey = 'app_theme';

  // ─── CONTACT INFO ─────────────────────────────────────────────────────────
  static const String supportPhone = '+998 90 000 00 00';
  static const String supportEmail = 'support@sartaroshxona.uz';
  static const String developerName = 'Sartaroshxona Team';
}
