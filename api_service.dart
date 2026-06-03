import 'dart:convert';
import 'dart:async';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sartaroshxona/models/barber.dart';
import 'package:sartaroshxona/utils/app_constants.dart';

/// ═══════════════════════════════════════════════════════════════════════════════
/// API SERVICE — Backend bilan professional aloqa
///
/// Xususiyatlari:
/// - JWT token boshqaruvi (auto-save, auto-load)
/// - Retry logic (timeout bo'lganda qayta urinish)
/// - Aniq xato xabarlari (network, timeout, server, auth)
/// - Singleton pattern
/// ═══════════════════════════════════════════════════════════════════════════════
class ApiService {
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;
  ApiService._internal();

  static const String baseUrl = AppConstants.baseUrl;
  static const Duration _timeout = Duration(seconds: AppConstants.requestTimeoutSeconds);

  String? _token;

  // ─── TOKEN MANAGEMENT ─────────────────────────────────────────────────────

  Future<void> setToken(String token) async {
    _token = token;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(AppConstants.tokenKey, token);
  }

  Future<String?> getToken() async {
    if (_token != null) return _token;
    final prefs = await SharedPreferences.getInstance();
    _token = prefs.getString(AppConstants.tokenKey);
    return _token;
  }

  Future<void> clearToken() async {
    _token = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(AppConstants.tokenKey);
    await prefs.remove(AppConstants.userIdKey);
    await prefs.remove(AppConstants.userRoleKey);
    await prefs.remove(AppConstants.userNameKey);
    await prefs.remove(AppConstants.barberIdKey);
  }

  Future<void> saveUserData({
    required int userId,
    required String role,
    required String name,
    int? barberId,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(AppConstants.userIdKey, userId);
    await prefs.setString(AppConstants.userRoleKey, role);
    await prefs.setString(AppConstants.userNameKey, name);
    if (barberId != null) {
      await prefs.setInt(AppConstants.barberIdKey, barberId);
    }
  }

  Future<int?> getSavedUserId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getInt(AppConstants.userIdKey);
  }

  Future<String?> getSavedRole() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(AppConstants.userRoleKey);
  }

  Future<int?> getSavedBarberId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getInt(AppConstants.barberIdKey);
  }

  // ─── HTTP HELPERS (with retry & proper error handling) ────────────────────

  Future<Map<String, String>> _headers() async {
    final token = await getToken();
    return {
      "Content-Type": "application/json",
      "Accept": "application/json",
      if (token != null) "Authorization": "Bearer $token",
    };
  }

  /// GET so'rov — retry bilan
  Future<ApiResponse> _get(String endpoint) async {
    return _request('GET', endpoint);
  }

  /// POST so'rov — retry bilan
  Future<ApiResponse> _post(String endpoint, {Map<String, dynamic>? body}) async {
    return _request('POST', endpoint, body: body);
  }

  /// PUT so'rov — retry bilan
  Future<ApiResponse> _put(String endpoint, {Map<String, dynamic>? body}) async {
    return _request('PUT', endpoint, body: body);
  }

  /// DELETE so'rov — retry bilan
  Future<ApiResponse> _delete(String endpoint) async {
    return _request('DELETE', endpoint);
  }

  /// Umumiy HTTP so'rov — barcha xatolarni to'g'ri boshqaradi
  Future<ApiResponse> _request(
    String method,
    String endpoint, {
    Map<String, dynamic>? body,
    int retryCount = 0,
  }) async {
    try {
      final headers = await _headers();
      final uri = Uri.parse('$baseUrl$endpoint');
      http.Response response;

      switch (method) {
        case 'GET':
          response = await http.get(uri, headers: headers).timeout(_timeout);
          break;
        case 'POST':
          response = await http.post(uri, headers: headers, body: body != null ? jsonEncode(body) : null).timeout(_timeout);
          break;
        case 'PUT':
          response = await http.put(uri, headers: headers, body: body != null ? jsonEncode(body) : null).timeout(_timeout);
          break;
        case 'DELETE':
          response = await http.delete(uri, headers: headers).timeout(_timeout);
          break;
        default:
          return ApiResponse.error("Noto'g'ri HTTP method", ApiErrorType.unknown);
      }

      // Muvaffaqiyatli
      if (response.statusCode >= 200 && response.statusCode < 300) {
        return ApiResponse.success(response);
      }

      // Auth xato — token muddati tugagan
      if (response.statusCode == 401) {
        return ApiResponse.error(
          _extractErrorMessage(response) ?? "Avtorizatsiya muddati tugagan. Qayta login qiling.",
          ApiErrorType.unauthorized,
        );
      }

      // Forbidden
      if (response.statusCode == 403) {
        return ApiResponse.error(
          _extractErrorMessage(response) ?? "Bu amalni bajarish uchun ruxsatingiz yo'q",
          ApiErrorType.forbidden,
        );
      }

      // Not found
      if (response.statusCode == 404) {
        return ApiResponse.error(
          _extractErrorMessage(response) ?? "Ma'lumot topilmadi",
          ApiErrorType.notFound,
        );
      }

      // Conflict (duplicate)
      if (response.statusCode == 409) {
        return ApiResponse.error(
          _extractErrorMessage(response) ?? "Bu amal allaqachon bajarilgan",
          ApiErrorType.conflict,
        );
      }

      // Validation error
      if (response.statusCode == 422) {
        return ApiResponse.error(
          _extractValidationError(response) ?? "Ma'lumotlar noto'g'ri kiritilgan",
          ApiErrorType.validation,
        );
      }

      // Server error
      if (response.statusCode >= 500) {
        return ApiResponse.error(
          "Serverda xatolik yuz berdi. Keyinroq urinib ko'ring.",
          ApiErrorType.serverError,
        );
      }

      return ApiResponse.error(
        _extractErrorMessage(response) ?? "Kutilmagan xato (${response.statusCode})",
        ApiErrorType.unknown,
      );
    } on TimeoutException {
      // Retry
      if (retryCount < AppConstants.maxRetryAttempts) {
        _log('$method $endpoint TIMEOUT — qayta urinish (${retryCount + 1})');
        await Future.delayed(Duration(seconds: 1 + retryCount));
        return _request(method, endpoint, body: body, retryCount: retryCount + 1);
      }
      return ApiResponse.error(
        "Server javob bermayapti. Internet aloqangizni tekshiring.",
        ApiErrorType.timeout,
      );
    } on SocketException {
      return ApiResponse.error(
        "Server bilan aloqa yo'q. Internet yoqilganmi? Server ishlayaptimi?",
        ApiErrorType.network,
      );
    } on HandshakeException {
      return ApiResponse.error(
        "SSL/TLS xatosi. Server manzilini tekshiring.",
        ApiErrorType.network,
      );
    } catch (e) {
      _log('$method $endpoint ERROR: $e');
      // Retry for unknown errors
      if (retryCount < AppConstants.maxRetryAttempts) {
        await Future.delayed(Duration(seconds: 1));
        return _request(method, endpoint, body: body, retryCount: retryCount + 1);
      }
      return ApiResponse.error(
        "Kutilmagan xato yuz berdi: ${e.toString().length > 100 ? e.toString().substring(0, 100) : e}",
        ApiErrorType.unknown,
      );
    }
  }

  String? _extractErrorMessage(http.Response response) {
    try {
      final body = jsonDecode(response.body);
      return body['detail']?.toString();
    } catch (_) {
      return null;
    }
  }

  String? _extractValidationError(http.Response response) {
    try {
      final body = jsonDecode(response.body);
      if (body['detail'] is List) {
        final errors = (body['detail'] as List);
        if (errors.isNotEmpty) {
          final first = errors.first;
          return first['msg']?.toString() ?? "Ma'lumotlar noto'g'ri";
        }
      }
      return body['detail']?.toString();
    } catch (_) {
      return null;
    }
  }

  void _log(String message) {
    print("[ApiService] $message");
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // AUTH
  // ═══════════════════════════════════════════════════════════════════════════

  /// Login — aniq natija qaytaradi
  Future<LoginResult> loginUser(String email, String password) async {
    final response = await _post('/login', body: {
      "email": email,
      "password": password,
    });

    if (!response.isSuccess) {
      return LoginResult.failure(response.errorMessage ?? "Login xatosi");
    }

    try {
      final data = response.data!;
      if (data['token'] != null) {
        await setToken(data['token']);
      }
      final user = data['user'];
      if (user != null) {
        await saveUserData(
          userId: user['id'] ?? 0,
          role: user['role'] ?? 'customer',
          name: user['full_name'] ?? '',
          barberId: user['barber_id'] != null ? int.tryParse(user['barber_id'].toString()) : null,
        );
      }
      return LoginResult.success(data);
    } catch (e) {
      return LoginResult.failure("Javobni o'qishda xato");
    }
  }

  /// Register
  Future<Map<String, dynamic>?> registerUser(
    String name,
    String email,
    String password,
    String role, {
    String? experience,
    String? phone,
    String? specialization,
    String? bio,
    double? lat,
    double? lng,
  }) async {
    final body = {
      "full_name": name,
      "email": email,
      "password": password,
      "role": role,
      "phone": phone ?? "",
      "experience": experience ?? "",
      "specialization": specialization ?? "",
      "bio": bio ?? "",
      "lat": lat ?? AppConstants.defaultLat,
      "lng": lng ?? AppConstants.defaultLng,
    };

    final response = await _post('/register', body: body);

    if (response.isSuccess) {
      final data = response.data!;
      if (data['token'] != null) {
        await setToken(data['token']);
      }
      return data;
    }

    if (response.errorType == ApiErrorType.conflict) {
      return {"error": "Bu email allaqachon ro'yxatdan o'tgan"};
    }

    return {"error": response.errorMessage ?? "Ro'yxatdan o'tishda xatolik"};
  }

  Future<void> logout() async {
    await clearToken();
  }

  Future<bool> isLoggedIn() async {
    final token = await getToken();
    return token != null && token.isNotEmpty;
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // BARBERS
  // ═══════════════════════════════════════════════════════════════════════════

  Future<List<Barber>> fetchBarbers(double lat, double lng, {double radiusKm = 2.0}) async {
    final response = await _get('/nearby_barbers?user_lat=$lat&user_lng=$lng&radius_km=$radiusKm');
    if (response.isSuccess) {
      final List<dynamic> data = response.data is List ? response.data : [];
      return data.map((j) => Barber.fromJson(j)).toList();
    }
    return await fetchAllBarbers(lat, lng);
  }

  Future<List<Barber>> fetchAllBarbers(double lat, double lng) async {
    final response = await _get('/all_barbers?user_lat=$lat&user_lng=$lng');
    if (response.isSuccess) {
      final List<dynamic> data = response.data is List ? response.data : [];
      return data.map((j) => Barber.fromJson(j)).toList();
    }
    return [];
  }

  Future<List<Barber>> searchBarbers(String query) async {
    final response = await _get('/search_barbers?query=${Uri.encodeComponent(query)}');
    if (response.isSuccess) {
      final List<dynamic> data = response.data is List ? response.data : [];
      return data.map((j) => Barber.fromJson(j)).toList();
    }
    return [];
  }

  Future<Map<String, dynamic>?> getBarberDetail(int barberId) async {
    final response = await _get('/barber/$barberId');
    if (response.isSuccess) return response.data as Map<String, dynamic>?;
    return null;
  }

  Future<bool> updateOnlineStatus(int barberId, bool isOnline) async {
    final response = await _put('/update_online_status/$barberId?is_online=$isOnline');
    return response.isSuccess;
  }

  Future<bool> updateProfile(int barberId, Map<String, dynamic> data) async {
    final response = await _put('/update_profile/$barberId', body: data);
    return response.isSuccess;
  }

  Future<bool> updateWorkingDays(int barberId, List<int> days) async {
    try {
      final headers = await _headers();
      final response = await http.put(
        Uri.parse('$baseUrl/update_working_days/$barberId'),
        headers: headers,
        body: jsonEncode(days),
      ).timeout(_timeout);
      return response.statusCode == 200;
    } catch (e) {
      _log('updateWorkingDays ERROR: $e');
      return false;
    }
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // SLOTS
  // ═══════════════════════════════════════════════════════════════════════════

  Future<Map<String, dynamic>?> getAvailableSlots(int barberId, String date) async {
    final response = await _get('/available_slots/$barberId?date=$date');
    if (response.isSuccess) return response.data as Map<String, dynamic>?;
    return null;
  }

  Future<bool> blockSlot({
    required int barberId,
    required String date,
    required String startTime,
    required String endTime,
    String? reason,
  }) async {
    final response = await _post('/block_slot', body: {
      "barber_id": barberId,
      "blocked_date": date,
      "start_time": startTime,
      "end_time": endTime,
      "reason": reason ?? "",
    });
    return response.isSuccess;
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // SERVICES
  // ═══════════════════════════════════════════════════════════════════════════

  Future<List<dynamic>> getBarberServices(int barberId) async {
    final response = await _get('/get_services/$barberId');
    if (response.isSuccess && response.data is List) return response.data;
    return [];
  }

  Future<bool> addService(int barberId, String name, double price,
      {int duration = 30, String description = ""}) async {
    final response = await _post(
      '/add_service?barber_id=$barberId&name=${Uri.encodeComponent(name)}'
      '&price=$price&duration=$duration&description=${Uri.encodeComponent(description)}',
    );
    return response.isSuccess;
  }

  Future<bool> deleteService(int serviceId) async {
    final response = await _delete('/delete_service/$serviceId');
    return response.isSuccess;
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // APPOINTMENTS
  // ═══════════════════════════════════════════════════════════════════════════

  Future<Map<String, dynamic>?> bookAppointment({
    required int customerId,
    required int barberId,
    int? serviceId,
    required String appointmentTime,
    required String serviceName,
    double price = 0,
    String? notes,
  }) async {
    final response = await _post('/book_appointment', body: {
      "customer_id": customerId,
      "barber_id": barberId,
      "service_id": serviceId,
      "appointment_time": appointmentTime,
      "service_name": serviceName,
      "price": price,
      "notes": notes ?? "",
    });

    if (response.isSuccess) return response.data as Map<String, dynamic>?;
    if (response.errorType == ApiErrorType.conflict) {
      return {"error": "Bu vaqt band! Boshqa vaqt tanlang."};
    }
    return null;
  }

  Future<List<dynamic>> getCustomerAppointments(int customerId) async {
    final response = await _get('/customer_appointments/$customerId');
    if (response.isSuccess && response.data is List) return response.data;
    return [];
  }

  Future<List<dynamic>> getBarberAppointments(int barberId) async {
    final response = await _get('/barber_appointments/$barberId');
    if (response.isSuccess && response.data is List) return response.data;
    return [];
  }

  Future<bool> updateStatus(int appId, String status) async {
    final response = await _put('/update_appointment_status/$appId?status=$status');
    return response.isSuccess;
  }

  Future<bool> cancelAppointment(int appId, int customerId) async {
    final response = await _put('/cancel_appointment/$appId?customer_id=$customerId');
    return response.isSuccess;
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // REVIEWS
  // ═══════════════════════════════════════════════════════════════════════════

  Future<bool> addReview({
    required int appointmentId,
    required int customerId,
    required int barberId,
    required int rating,
    String? comment,
  }) async {
    final response = await _post('/add_review', body: {
      "appointment_id": appointmentId,
      "customer_id": customerId,
      "barber_id": barberId,
      "rating": rating,
      "comment": comment ?? "",
    });
    return response.isSuccess;
  }

  Future<List<dynamic>> getBarberReviews(int barberId) async {
    final response = await _get('/barber_reviews/$barberId');
    if (response.isSuccess && response.data is List) return response.data;
    return [];
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // PAYMENTS
  // ═══════════════════════════════════════════════════════════════════════════

  Future<Map<String, dynamic>?> createPayment({
    required int appointmentId,
    required double amount,
    required String method,
  }) async {
    final response = await _post('/create_payment', body: {
      "appointment_id": appointmentId,
      "amount": amount,
      "method": method,
    });
    if (response.isSuccess) return response.data as Map<String, dynamic>?;
    return null;
  }

  Future<List<dynamic>> getPaymentHistory(int customerId) async {
    final response = await _get('/payment_history/$customerId');
    if (response.isSuccess && response.data is List) return response.data;
    return [];
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // STATISTICS
  // ═══════════════════════════════════════════════════════════════════════════

  Future<Map<String, dynamic>> getBarberStats(int barberId) async {
    final response = await _get('/barber_stats/$barberId');
    if (response.isSuccess && response.data is Map) {
      return response.data as Map<String, dynamic>;
    }
    return _emptyStats;
  }

  static const Map<String, dynamic> _emptyStats = {
    "today_count": 0,
    "total_completed": 0,
    "revenue": 0,
    "monthly_revenue": 0,
    "pending_count": 0,
    "avg_rating": 5.0,
    "total_reviews": 0,
  };

  // ═══════════════════════════════════════════════════════════════════════════
  // NOTIFICATIONS
  // ═══════════════════════════════════════════════════════════════════════════

  Future<Map<String, dynamic>> getNotifications(int userId) async {
    final response = await _get('/notifications/$userId');
    if (response.isSuccess && response.data is Map) {
      return response.data as Map<String, dynamic>;
    }
    return {"notifications": [], "unread_count": 0};
  }

  Future<bool> markNotificationsRead(int userId) async {
    final response = await _put('/mark_notifications_read/$userId');
    return response.isSuccess;
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // FAVORITES
  // ═══════════════════════════════════════════════════════════════════════════

  Future<Map<String, dynamic>?> toggleFavorite(int customerId, int barberId) async {
    final response = await _post('/toggle_favorite?customer_id=$customerId&barber_id=$barberId');
    if (response.isSuccess) return response.data as Map<String, dynamic>?;
    return null;
  }

  Future<List<dynamic>> getFavorites(int customerId) async {
    final response = await _get('/favorites/$customerId');
    if (response.isSuccess && response.data is List) return response.data;
    return [];
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // HEALTH CHECK
  // ═══════════════════════════════════════════════════════════════════════════

  Future<bool> checkHealth() async {
    final response = await _get('/health');
    return response.isSuccess;
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// RESPONSE MODELS
// ═══════════════════════════════════════════════════════════════════════════════

/// API xato turlari
enum ApiErrorType {
  network,      // Internet yo'q, server topilmadi
  timeout,      // Server javob bermayapti
  unauthorized, // Token muddati tugagan (401)
  forbidden,    // Ruxsat yo'q (403)
  notFound,     // Topilmadi (404)
  conflict,     // Duplicate (409)
  validation,   // Ma'lumot noto'g'ri (422)
  serverError,  // Server xatosi (500+)
  unknown,      // Noma'lum
}

/// Umumiy API javob modeli
class ApiResponse {
  final bool isSuccess;
  final dynamic data;
  final String? errorMessage;
  final ApiErrorType? errorType;
  final int? statusCode;

  ApiResponse._({
    required this.isSuccess,
    this.data,
    this.errorMessage,
    this.errorType,
    this.statusCode,
  });

  factory ApiResponse.success(http.Response response) {
    dynamic parsedData;
    try {
      parsedData = jsonDecode(response.body);
    } catch (_) {
      parsedData = response.body;
    }
    return ApiResponse._(
      isSuccess: true,
      data: parsedData,
      statusCode: response.statusCode,
    );
  }

  factory ApiResponse.error(String message, ApiErrorType type) {
    return ApiResponse._(
      isSuccess: false,
      errorMessage: message,
      errorType: type,
    );
  }
}

/// Login natijasi — aniq success yoki failure
class LoginResult {
  final bool isSuccess;
  final Map<String, dynamic>? data;
  final String? errorMessage;

  LoginResult._({required this.isSuccess, this.data, this.errorMessage});

  factory LoginResult.success(Map<String, dynamic> data) {
    return LoginResult._(isSuccess: true, data: data);
  }

  factory LoginResult.failure(String message) {
    return LoginResult._(isSuccess: false, errorMessage: message);
  }
}
