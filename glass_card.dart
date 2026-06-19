import 'dart:ui';
import 'package:flutter/material.dart';

/// Liquid glass (frosted) konteyner.
///
/// Orqa fonni blur qiladi, yarim-shaffof gradient va nozik yorqin chegara
/// qo'shadi. Dark/Light rejimga avtomatik moslashadi.
///
/// Ixtiyoriy:
///   - [tintColor]: aksent rang (masalan o'qilmagan bildirishnoma uchun primary)
///   - [onTap]: bosilganda chaqiriladigan funksiya
///   - [borderColor]: chegara rangini majburan o'rnatish
class GlassContainer extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry? padding;
  final EdgeInsetsGeometry? margin;
  final double borderRadius;
  final double blur;
  final VoidCallback? onTap;
  final Color? tintColor;
  final Color? borderColor;

  const GlassContainer({
    super.key,
    required this.child,
    this.padding,
    this.margin,
    this.borderRadius = 18,
    this.blur = 18,
    this.onTap,
    this.tintColor,
    this.borderColor,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final radius = BorderRadius.circular(borderRadius);

    // To'ldiruvchi gradient ranglari
    final List<Color> fillColors;
    if (tintColor != null) {
      fillColors = [
        tintColor!.withOpacity(isDark ? 0.20 : 0.22),
        tintColor!.withOpacity(isDark ? 0.06 : 0.10),
      ];
    } else {
      fillColors = isDark
          ? [Colors.white.withOpacity(0.10), Colors.white.withOpacity(0.03)]
          : [Colors.white.withOpacity(0.70), Colors.white.withOpacity(0.45)];
    }

    // Chegara rangi (nozik yorqin "shisha qirrasi" effekti)
    final Color effectiveBorder = borderColor ??
        (tintColor != null
            ? tintColor!.withOpacity(isDark ? 0.40 : 0.45)
            : Colors.white.withOpacity(isDark ? 0.14 : 0.65));

    final glass = ClipRRect(
      borderRadius: radius,
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: blur, sigmaY: blur),
        child: Container(
          padding: padding,
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: fillColors,
            ),
            borderRadius: radius,
            border: Border.all(color: effectiveBorder, width: 1),
          ),
          child: child,
        ),
      ),
    );

    Widget result = Container(
      margin: margin,
      decoration: BoxDecoration(
        borderRadius: radius,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(isDark ? 0.28 : 0.06),
            blurRadius: 18,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: glass,
    );

    if (onTap != null) {
      result = GestureDetector(onTap: onTap, child: result);
    }
    return result;
  }
}
