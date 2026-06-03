import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sartaroshxona/models/barber.dart';
import 'package:sartaroshxona/utils/app_constants.dart';

/// API xizmati — backend bilan aloqa
/// JWT token bilan ishlaydi, auto-retry va xatolik boshqaruvi bilan
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
  }

  Future<void> saveUserData({required int userId, required String role, required String name}) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(AppConstants.userIdKey, userId);
    await prefs.setString(AppConstants.userRoleKey, role);
    await prefs.setString(AppConstants.userNameKey, name);
  }

  Future<int?> getSavedUserId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getInt(AppConstants.userIdKey);
  }

  Future<String?> getSavedRole() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(AppConstants.userRoleKey);
  }

  // ─── HTTP HELPERS ─────────────────────────────────────────────────────────

  Future<Map<String, String>> _headers() async {
    final token = await getToken();
    return {
      "Content-Type": "application/json",
      "Accept": "application/json",
      if (token != null) "Authorization": "Bearer $token",
    };
  }

  Future<http.Response?> _get(String endpoint) async {
    try {
      final headers = await _headers();
      return await http.get(
        Uri.parse('$baseUrl$endpoint'),
        headers: headers,
      ).timeout(_timeout);
    } catch (e) {
      _logError('GET $endpoint', e);
      return null;
    }
  }

  Future<http.Response?> _post(String endpoint, {Map<String, dynamic>? body}) async {
    try {
      final headers = await _headers();
      return await http.post(
        Uri.parse('$baseUrl$endpoint'),
        headers: headers,
        body: body != null ? jsonEncode(body) : null,
      ).timeout(_timeout);
    } catch (e) {
      _logError('POST $endpoint', e);
      return null;
    }
  }

  Future<http.Response?> _put(String endpoint, {Map<String, dynamic>? body}) async {
    try {
      final headers = await _headers();
      return await http.put(
        Uri.parse('$baseUrl$endpoint'),
        headers: headers,
        body: body != null ? jsonEncode(body) : null,
      ).timeout(_timeout);
    } catch (e) {
      _logError('PUT $endpoint', e);
      return null;
    }
  }

  Future<http.Response?> _delete(String endpoint) async {
    try {
      final headers = await _headers();
      return await http.delete(
        Uri.parse('$baseUrl$endpoint'),
        headers: headers,
      ).timeout(_timeout);
    } catch (e) {
      _logError('DELETE $endpoint', e);
      return null;
    }
  }

  void _logError(String operation, dynamic error) {
    print("[ApiService] $operation ERROR: $error");
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // AUTH
  // ═══════════════════════════════════════════════════════════════════════════

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
    if (response == null) return null;

    if (response.statusCode == 200 || response.statusCode == 201) {
      final data = jsonDecode(response.body);
      if (data['token'] != null) {
        await setToken(data['token']);
      }
      return data;
    }

    if (response.statusCode == 409) {
      return {"error": "Bu email allaqachon ro'yxatdan o'tgan"};
    }
    return {"error": "Ro'yxatdan o'tishda xatolik"};
  }

  Future<Map<String, dynamic>?> loginUser(String email, String password) async {
    final response = await _post('/login', body: {
      "email": email,
      "password": password,
    });

    if (response == null) return null;

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      if (data['token'] != null) {
        await setToken(data['token']);
      }
      final user = data['user'];
      if (user != null) {
        await saveUserData(
          userId: user['id'] ?? 0,
          role: user['role'] ?? 'customer',
          name: user['full_name'] ?? '',
        );
      }
      return data;
    }
    return null;
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
    if (response != null && response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body);
      return data.map((j) => Barber.fromJson(j)).toList();
    }
    return await fetchAllBarbers(lat, lng);
  }

  Future<List<Barber>> fetchAllBarbers(double lat, double lng) async {
    final response = await _get('/all_barbers?user_lat=$lat&user_lng=$lng');
    if (response != null && response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body);
      return data.map((j) => Barber.fromJson(j)).toList();
    }
    return [];
  }

  Future<List<Barber>> searchBarbers(String query) async {
    final response = await _get('/search_barbers?query=${Uri.encodeComponent(query)}');
    if (response != null && response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body);
      return data.map((j) => Barber.fromJson(j)).toList();
    }
    return [];
  }

  Future<Map<String, dynamic>?> getBarberDetail(int barberId) async {
    final response = await _get('/barber/$barberId');
    if (response != null && response.statusCode == 200) {
      return jsonDecode(response.body);
    }
    return null;
  }

  Future<bool> updateOnlineStatus(int barberId, bool isOnline) async {
    final response = await _put('/update_online_status/$barberId?is_online=$isOnline');
    return response != null && response.statusCode == 200;
  }

  Future<bool> updateProfile(int barberId, Map<String, dynamic> data) async {
    final response = await _put('/update_profile/$barberId', body: data);
    return response != null && response.statusCode == 200;
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
      _logError('updateWorkingDays', e);
      return false;
    }
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // SLOTS
  // ═══════════════════════════════════════════════════════════════════════════

  Future<Map<String, dynamic>?> getAvailableSlots(int barberId, String date) async {
    final response = await _get('/available_slots/$barberId?date=$date');
    if (response != null && response.statusCode == 200) {
      return jsonDecode(response.body);
    }
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
    return response != null && response.statusCode == 200;
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // SERVICES
  // ═══════════════════════════════════════════════════════════════════════════

  Future<List<dynamic>> getBarberServices(int barberId) async {
    final response = await _get('/get_services/$barberId');
    if (response != null && response.statusCode == 200) {
      return jsonDecode(response.body);
    }
    return [];
  }

  Future<bool> addService(int barberId, String name, double price,
      {int duration = 30, String description = ""}) async {
    final response = await _post(
      '/add_service?barber_id=$barberId&name=${Uri.encodeComponent(name)}'
          '&price=$price&duration=$duration&description=${Uri.encodeComponent(description)}',
    );
    return response != null && response.statusCode == 200;
  }

  Future<bool> deleteService(int serviceId) async {
    final response = await _delete('/delete_service/$serviceId');
    return response != null && response.statusCode == 200;
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

    if (response != null && response.statusCode == 200) {
      return jsonDecode(response.body);
    }
    if (response != null && response.statusCode == 409) {
      return {"error": "Bu vaqt band! Boshqa vaqt tanlang."};
    }
    return null;
  }

  Future<List<dynamic>> getCustomerAppointments(int customerId) async {
    final response = await _get('/customer_appointments/$customerId');
    if (response != null && response.statusCode == 200) {
      return jsonDecode(response.body);
    }
    return [];
  }

  Future<List<dynamic>> getBarberAppointments(int barberId) async {
    final response = await _get('/barber_appointments/$barberId');
    if (response != null && response.statusCode == 200) {
      return jsonDecode(response.body);
    }
    return [];
  }

  Future<bool> updateStatus(int appId, String status) async {
    final response = await _put('/update_appointment_status/$appId?status=$status');
    return response != null && response.statusCode == 200;
  }

  Future<bool> cancelAppointment(int appId, int customerId) async {
    final response = await _put('/cancel_appointment/$appId?customer_id=$customerId');
    return response != null && response.statusCode == 200;
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
    return response != null && response.statusCode == 200;
  }

  Future<List<dynamic>> getBarberReviews(int barberId) async {
    final response = await _get('/barber_reviews/$barberId');
    if (response != null && response.statusCode == 200) {
      return jsonDecode(response.body);
    }
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
    if (response != null && response.statusCode == 200) {
      return jsonDecode(response.body);
    }
    return null;
  }

  Future<List<dynamic>> getPaymentHistory(int customerId) async {
    final response = await _get('/payment_history/$customerId');
    if (response != null && response.statusCode == 200) {
      return jsonDecode(response.body);
    }
    return [];
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // STATISTICS
  // ═══════════════════════════════════════════════════════════════════════════

  Future<Map<String, dynamic>> getBarberStats(int barberId) async {
    final response = await _get('/barber_stats/$barberId');
    if (response != null && response.statusCode == 200) {
      return jsonDecode(response.body);
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
    if (response != null && response.statusCode == 200) {
      return jsonDecode(response.body);
    }
    return {"notifications": [], "unread_count": 0};
  }

  Future<bool> markNotificationsRead(int userId) async {
    final response = await _put('/mark_notifications_read/$userId');
    return response != null && response.statusCode == 200;
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // FAVORITES
  // ═══════════════════════════════════════════════════════════════════════════

  Future<Map<String, dynamic>?> toggleFavorite(int customerId, int barberId) async {
    final response = await _post('/toggle_favorite?customer_id=$customerId&barber_id=$barberId');
    if (response != null && response.statusCode == 200) {
      return jsonDecode(response.body);
    }
    return null;
  }

  Future<List<dynamic>> getFavorites(int customerId) async {
    final response = await _get('/favorites/$customerId');
    if (response != null && response.statusCode == 200) {
      return jsonDecode(response.body);
    }
    return [];
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // HEALTH CHECK
  // ═══════════════════════════════════════════════════════════════════════════

  Future<bool> checkHealth() async {
    final response = await _get('/health');
    return response != null && response.statusCode == 200;
  }
}
