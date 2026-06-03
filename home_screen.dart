import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:location/location.dart';
import 'package:sartaroshxona/models/barber.dart';
import 'package:sartaroshxona/providers/theme_provider.dart';
import 'package:sartaroshxona/services/api_service.dart';
import 'package:sartaroshxona/screens/barber_details_screen.dart';
import 'package:sartaroshxona/screens/customer_appointments_screen.dart';
import 'package:sartaroshxona/screens/login_screen.dart';
import 'package:sartaroshxona/screens/notifications_screen.dart';
import 'package:sartaroshxona/screens/favorites_screen.dart';
import 'package:sartaroshxona/screens/payment_history_screen.dart';
import 'package:sartaroshxona/widgets/shimmer_loading.dart';
import 'package:sartaroshxona/widgets/filter_bottom_sheet.dart';
import 'package:sartaroshxona/utils/page_transitions.dart';

class HomeScreen extends StatefulWidget {
  final String userName;
  final int userId;

  const HomeScreen({super.key, required this.userName, required this.userId});

  @override
  _HomeScreenState createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  Future<List<Barber>> futureBarbers = Future.value([]);
  final TextEditingController _searchController = TextEditingController();
  bool _isSearching = false;
  final GlobalKey<ScaffoldState> _scaffoldKey = GlobalKey<ScaffoldState>();

  double _userLat = 41.3111;
  double _userLng = 69.2797;
  FilterOptions _filter = const FilterOptions();

  @override
  void initState() {
    super.initState();
    _loadLocationAndBarbers();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadLocationAndBarbers() async {
    Location location = Location();

    bool serviceEnabled = await location.serviceEnabled();
    if (!serviceEnabled) serviceEnabled = await location.requestService();

    PermissionStatus permissionGranted = await location.hasPermission();
    if (permissionGranted == PermissionStatus.denied) {
      permissionGranted = await location.requestPermission();
    }

    if (permissionGranted == PermissionStatus.granted && serviceEnabled) {
      try {
        LocationData locationData = await location.getLocation();
        if (locationData.latitude != null && locationData.longitude != null) {
          _userLat = locationData.latitude!;
          _userLng = locationData.longitude!;
        }
      } catch (e) {
        debugPrint("GPS xatolik: $e");
      }
    }

    setState(() {
      futureBarbers = ApiService()
          .fetchBarbers(_userLat, _userLng, radiusKm: _filter.maxDistance)
          .then((barbers) {
        var filtered = barbers;
        if (_filter.onlyOnline) {
          filtered = filtered.where((b) => b.isOnline).toList();
        }
        switch (_filter.sortBy) {
          case 'rating':
            filtered.sort((a, b) => b.rating.compareTo(a.rating));
            break;
          case 'name':
            filtered.sort((a, b) => a.name.compareTo(b.name));
            break;
          default:
            filtered.sort((a, b) => (a.distance ?? 999).compareTo(b.distance ?? 999));
        }
        return filtered;
      });
    });
  }

  void _onSearch(String query) {
    if (query.trim().isEmpty) {
      setState(() {
        _isSearching = false;
        _loadLocationAndBarbers();
      });
    } else {
      setState(() {
        _isSearching = true;
        futureBarbers = ApiService().searchBarbers(query.trim());
      });
    }
  }

  void _showFilter() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => FilterBottomSheet(
        currentFilter: _filter,
        onApply: (newFilter) {
          setState(() => _filter = newFilter);
          _loadLocationAndBarbers();
        },
      ),
    );
  }

  void _logout() {
    final colors = Theme.of(context).extension<AppColors>()!;
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: colors.surface,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Text('Chiqish', style: TextStyle(color: colors.textPrimary)),
        content: Text('Tizimdan chiqmoqchimisiz?', style: TextStyle(color: colors.textSecondary)),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('Bekor', style: TextStyle(color: colors.textSecondary)),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: colors.error),
            onPressed: () => Navigator.pushAndRemoveUntil(
              context,
              MaterialPageRoute(builder: (_) => const LoginScreen()),
                  (route) => false,
            ),
            child: const Text('Chiqish'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AppColors>()!;
    final themeProvider = context.watch<ThemeProvider>();

    return Scaffold(
      key: _scaffoldKey,
      backgroundColor: colors.background,
      drawer: _buildDrawer(colors, themeProvider),
      appBar: AppBar(
        backgroundColor: colors.background,
        elevation: 0,
        leading: IconButton(
          icon: Icon(Icons.menu_rounded, color: colors.textPrimary),
          onPressed: () => _scaffoldKey.currentState?.openDrawer(),
        ),
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text("Xayrli kun!", style: TextStyle(color: colors.textSecondary, fontSize: 13)),
            Text(widget.userName, style: TextStyle(color: colors.textPrimary, fontSize: 18, fontWeight: FontWeight.bold)),
          ],
        ),
        actions: [
          Stack(
            children: [
              IconButton(
                icon: Icon(Icons.notifications_outlined, color: colors.textPrimary),
                onPressed: () => Navigator.push(context, FadeScalePageRoute(page: NotificationsScreen(userId: widget.userId))),
                tooltip: "Bildirishnomalar",
              ),
              Positioned(
                right: 8,
                top: 8,
                child: Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(shape: BoxShape.circle, color: colors.error),
                ),
              ),
            ],
          ),
          IconButton(
            icon: Icon(Icons.tune_rounded, color: colors.textPrimary),
            onPressed: _showFilter,
            tooltip: "Filtr",
          ),
          IconButton(
            icon: Icon(Icons.my_location_rounded, color: colors.primary),
            onPressed: _loadLocationAndBarbers,
            tooltip: "Joylashuvni yangilash",
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 12),
            TextField(
              controller: _searchController,
              onChanged: _onSearch,
              style: TextStyle(color: colors.textPrimary),
              decoration: InputDecoration(
                hintText: "Sartarosh yoki joy qidirish...",
                hintStyle: TextStyle(color: colors.textSecondary),
                prefixIcon: Icon(Icons.search_rounded, color: colors.textSecondary),
                suffixIcon: _searchController.text.isNotEmpty
                    ? IconButton(
                  icon: Icon(Icons.clear_rounded, color: colors.textSecondary),
                  onPressed: () { _searchController.clear(); _onSearch(''); },
                )
                    : null,
                filled: true,
                fillColor: colors.surface,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(14),
                  borderSide: BorderSide(color: colors.primary, width: 1.5),
                ),
              ),
            ),
            const SizedBox(height: 20),
            Text(
              _isSearching ? "Qidiruv natijalari" : "Yaqin atrofdagi sartaroshlar",
              style: TextStyle(color: colors.textPrimary, fontSize: 17, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            Expanded(
              child: FutureBuilder<List<Barber>>(
                future: futureBarbers,
                builder: (context, snapshot) {
                  if (snapshot.connectionState == ConnectionState.waiting) {
                    return const BarberListShimmer();
                  }
                  if (snapshot.hasError) {
                    return Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.wifi_off_rounded, size: 60, color: colors.textSecondary.withOpacity(0.5)),
                          const SizedBox(height: 12),
                          Text("Server bilan aloqa yo'q", style: TextStyle(color: colors.textSecondary)),
                          const SizedBox(height: 12),
                          ElevatedButton(onPressed: _loadLocationAndBarbers, child: const Text("Qayta urinish")),
                        ],
                      ),
                    );
                  }
                  if (!snapshot.hasData || snapshot.data!.isEmpty) {
                    return Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.person_search_rounded, size: 64, color: colors.textSecondary.withOpacity(0.4)),
                          const SizedBox(height: 12),
                          Text(
                            _isSearching ? "Natija topilmadi" : "Hozircha sartaroshlar yo'q",
                            style: TextStyle(color: colors.textSecondary),
                          ),
                        ],
                      ),
                    );
                  }
                  return RefreshIndicator(
                    onRefresh: _loadLocationAndBarbers,
                    child: ListView.builder(
                      itemCount: snapshot.data!.length,
                      itemBuilder: (context, index) => _buildBarberCard(snapshot.data![index], colors),
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDrawer(AppColors colors, ThemeProvider themeProvider) {
    return Drawer(
      backgroundColor: colors.surface,
      child: Column(
        children: [
          Container(
            width: double.infinity,
            padding: const EdgeInsets.fromLTRB(20, 60, 20, 24),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [colors.primary, colors.primaryLight],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                CircleAvatar(
                  radius: 32,
                  backgroundColor: Colors.white.withOpacity(0.2),
                  child: Text(
                    widget.userName.isNotEmpty ? widget.userName[0].toUpperCase() : 'M',
                    style: const TextStyle(color: Colors.white, fontSize: 26, fontWeight: FontWeight.bold),
                  ),
                ),
                const SizedBox(height: 12),
                Text(widget.userName, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 18)),
                const Text('Mijoz', style: TextStyle(color: Colors.white70, fontSize: 13)),
              ],
            ),
          ),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.symmetric(vertical: 8),
              children: [
                _drawerItem(colors, Icons.home_rounded, "Asosiy sahifa", () => Navigator.pop(context)),
                _drawerItem(colors, Icons.calendar_month_rounded, "Mening navbatlarim", () {
                  Navigator.pop(context);
                  Navigator.push(context, FadeScalePageRoute(page: CustomerAppointmentsScreen(userId: widget.userId)));
                }),
                _drawerItem(colors, Icons.favorite_rounded, "Sevimlilar", () {
                  Navigator.pop(context);
                  Navigator.push(context, FadeScalePageRoute(page: FavoritesScreen(userId: widget.userId)));
                }),
                _drawerItem(colors, Icons.receipt_long_rounded, "To'lov tarixi", () {
                  Navigator.pop(context);
                  Navigator.push(context, FadeScalePageRoute(page: PaymentHistoryScreen(userId: widget.userId)));
                }),
                const Divider(),
                ListTile(
                  leading: Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(color: colors.primary.withOpacity(0.1), borderRadius: BorderRadius.circular(10)),
                    child: Icon(themeProvider.isDark ? Icons.wb_sunny_rounded : Icons.nights_stay_rounded, color: colors.primary, size: 20),
                  ),
                  title: Text("Tungi rejim", style: TextStyle(color: colors.textPrimary)),
                  subtitle: Text(themeProvider.isDark ? "Yoqilgan" : "O'chirilgan", style: TextStyle(color: colors.textSecondary, fontSize: 12)),
                  trailing: Switch(value: themeProvider.isDark, onChanged: (_) => themeProvider.toggleTheme(), activeColor: colors.primary),
                ),
                _drawerItem(colors, Icons.settings_rounded, "Sozlamalar", () { Navigator.pop(context); }),
                _drawerItem(colors, Icons.help_outline_rounded, "Yordam markazi", () { Navigator.pop(context); }),
                const Divider(),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text("Ilova haqida", style: TextStyle(color: colors.textSecondary, fontSize: 12, fontWeight: FontWeight.bold)),
                      const SizedBox(height: 8),
                      _infoRow(colors, "Versiya", "v3.1.0"),
                      _infoRow(colors, "Ishlab chiquvchi", "Sartaroshxona Team"),
                      _infoRow(colors, "Aloqa", "+998 90 000 00 00"),
                    ],
                  ),
                ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
            child: SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: () { Navigator.pop(context); _logout(); },
                style: OutlinedButton.styleFrom(
                  foregroundColor: colors.error,
                  side: BorderSide(color: colors.error.withOpacity(0.5)),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                icon: const Icon(Icons.logout_rounded),
                label: const Text("Tizimdan chiqish"),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _drawerItem(AppColors colors, IconData icon, String title, VoidCallback onTap) {
    return ListTile(
      onTap: onTap,
      leading: Container(
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(color: colors.primary.withOpacity(0.1), borderRadius: BorderRadius.circular(10)),
        child: Icon(icon, color: colors.primary, size: 20),
      ),
      title: Text(title, style: TextStyle(color: colors.textPrimary)),
      trailing: Icon(Icons.arrow_forward_ios_rounded, color: colors.textSecondary, size: 12),
    );
  }

  Widget _infoRow(AppColors colors, String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        children: [
          Text("$label: ", style: TextStyle(color: colors.textSecondary, fontSize: 12)),
          Text(value, style: TextStyle(color: colors.textPrimary, fontSize: 12, fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }

  Widget _buildBarberCard(Barber barber, AppColors colors) {
    return GestureDetector(
      onTap: () => Navigator.push(context, SlidePageRoute(page: BarberDetailsScreen(barber: barber, userId: widget.userId))),
      child: Container(
        margin: const EdgeInsets.only(bottom: 14),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: colors.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: colors.border),
          boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.04), blurRadius: 8, offset: const Offset(0, 3))],
        ),
        child: Row(
          children: [
            Container(
              width: 62, height: 62,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(14),
                gradient: LinearGradient(colors: [colors.primary.withOpacity(0.8), colors.primaryLight]),
              ),
              child: Center(
                child: Text(barber.name.isNotEmpty ? barber.name[0].toUpperCase() : 'S',
                    style: const TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.bold)),
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(child: Text(barber.name, style: TextStyle(color: colors.textPrimary, fontSize: 15, fontWeight: FontWeight.bold))),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                        decoration: BoxDecoration(
                          color: (barber.isOnline ? colors.success : colors.textSecondary).withOpacity(0.15),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Row(
                          children: [
                            Container(width: 6, height: 6, decoration: BoxDecoration(shape: BoxShape.circle, color: barber.isOnline ? colors.success : colors.textSecondary)),
                            const SizedBox(width: 4),
                            Text(barber.isOnline ? 'Online' : 'Offline', style: TextStyle(color: barber.isOnline ? colors.success : colors.textSecondary, fontSize: 10, fontWeight: FontWeight.bold)),
                          ],
                        ),
                      ),
                    ],
                  ),
                  if (barber.specialization != null && barber.specialization!.isNotEmpty)
                    Text(barber.specialization!, style: TextStyle(color: colors.primary, fontSize: 12)),
                  Text(barber.district, style: TextStyle(color: colors.textSecondary, fontSize: 12)),
                  const SizedBox(height: 6),
                  Row(
                    children: [
                      const Icon(Icons.star_rounded, color: Colors.amber, size: 15),
                      Text(" ${barber.rating}", style: TextStyle(color: colors.textPrimary, fontSize: 13, fontWeight: FontWeight.bold)),
                      Text(" (${barber.totalReviews})", style: TextStyle(color: colors.textSecondary, fontSize: 12)),
                      const SizedBox(width: 10),
                      Icon(Icons.location_on_rounded, color: colors.primary, size: 14),
                      Text(" ${barber.distance?.toStringAsFixed(1) ?? '0.0'} km", style: TextStyle(color: colors.textSecondary, fontSize: 12)),
                    ],
                  ),
                ],
              ),
            ),
            Icon(Icons.arrow_forward_ios_rounded, color: colors.textSecondary, size: 13),
          ],
        ),
      ),
    );
  }
}
