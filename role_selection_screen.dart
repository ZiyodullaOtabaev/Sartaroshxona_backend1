import 'package:flutter/material.dart';
import 'package:sartaroshxona/screens/register_screen.dart';
import 'package:sartaroshxona/providers/theme_provider.dart';

class RoleSelectionScreen extends StatelessWidget {
  const RoleSelectionScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AppColors>()!;

    return Scaffold(
      backgroundColor: colors.background,
      appBar: AppBar(
        backgroundColor: colors.background,
        elevation: 0,
        leading: IconButton(
          icon: Icon(Icons.arrow_back_ios_rounded, color: colors.textPrimary),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 28),
          child: Column(
            children: [
              const Spacer(flex: 1),
              Container(
                width: 80,
                height: 80,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: LinearGradient(colors: [colors.primary, colors.primaryLight]),
                  boxShadow: [
                    BoxShadow(color: colors.primary.withOpacity(0.3), blurRadius: 20, offset: const Offset(0, 8)),
                  ],
                ),
                child: const Icon(Icons.people_rounded, color: Colors.white, size: 36),
              ),
              const SizedBox(height: 24),
              Text(
                "Qaysi maqsadda foydalanasiz?",
                textAlign: TextAlign.center,
                style: TextStyle(color: colors.textPrimary, fontSize: 26, fontWeight: FontWeight.bold, height: 1.3),
              ),
              const SizedBox(height: 8),
              Text("Rolni tanlab ro'yxatdan o'ting", style: TextStyle(color: colors.textSecondary, fontSize: 14)),
              const SizedBox(height: 40),
              _RoleCard(
                colors: colors,
                title: "Mijozman",
                subtitle: "Sartarosh qidirish va navbat olish uchun",
                icon: Icons.person_rounded,
                role: "customer",
                features: const ["Sartarosh qidirish", "Online navbat olish", "To'lov qilish"],
              ),
              const SizedBox(height: 16),
              _RoleCard(
                colors: colors,
                title: "Sartaroshman",
                subtitle: "Xizmat ko'rsatish va mijozlarni boshqarish",
                icon: Icons.content_cut_rounded,
                role: "barber",
                features: const ["Mijozlar qabul qilish", "Xizmatlarni boshqarish", "Daromadni kuzatish"],
              ),
              const Spacer(flex: 2),
            ],
          ),
        ),
      ),
    );
  }
}

class _RoleCard extends StatelessWidget {
  final AppColors colors;
  final String title;
  final String subtitle;
  final IconData icon;
  final String role;
  final List<String> features;

  const _RoleCard({
    required this.colors,
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.role,
    required this.features,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => RegisterScreen(selectedRole: role))),
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: colors.surface,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: colors.border),
          boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.04), blurRadius: 12, offset: const Offset(0, 4))],
        ),
        child: Row(
          children: [
            Container(
              width: 56, height: 56,
              decoration: BoxDecoration(
                gradient: LinearGradient(colors: [colors.primary.withOpacity(0.15), colors.primaryLight.withOpacity(0.1)]),
                borderRadius: BorderRadius.circular(16),
              ),
              child: Icon(icon, color: colors.primary, size: 28),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: TextStyle(color: colors.textPrimary, fontSize: 17, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 4),
                  Text(subtitle, style: TextStyle(color: colors.textSecondary, fontSize: 12)),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 6, runSpacing: 4,
                    children: features.map((f) => Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: colors.primary.withOpacity(0.08),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(f, style: TextStyle(color: colors.primary, fontSize: 10, fontWeight: FontWeight.w500)),
                    )).toList(),
                  ),
                ],
              ),
            ),
            Icon(Icons.arrow_forward_ios_rounded, color: colors.textSecondary, size: 14),
          ],
        ),
      ),
    );
  }
}
