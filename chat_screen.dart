import 'dart:async';
import 'package:flutter/material.dart';
import 'package:sartaroshxona/providers/theme_provider.dart';

class ChatScreen extends StatefulWidget {
  final int userId;
  final int receiverId;
  final String receiverName;
  final bool isBarber;

  const ChatScreen({
    super.key,
    required this.userId,
    required this.receiverId,
    required this.receiverName,
    this.isBarber = false,
  });

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> with TickerProviderStateMixin {
  final TextEditingController _msgController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final List<_ChatMessage> _messages = [];
  bool _isSending = false;

  @override
  void initState() {
    super.initState();
    _loadSampleMessages();
  }

  @override
  void dispose() {
    _msgController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _loadSampleMessages() {
    // TODO: Backend'dan xabarlarni yuklash
    // Hozircha namuna xabarlar
    setState(() {
      _messages.addAll([
        _ChatMessage(text: "Assalomu alaykum! Bugun bo'sh vaqtingiz bormi?", isMine: true, time: "14:30"),
        _ChatMessage(text: "Vaalaykum assalom! Ha, soat 16:00 da bo'shman", isMine: false, time: "14:32"),
        _ChatMessage(text: "Juda yaxshi! Soch olish uchun kelaman", isMine: true, time: "14:33"),
        _ChatMessage(text: "Kutib turaman! Manzilni bilasizmi?", isMine: false, time: "14:34"),
      ]);
    });
  }

  void _sendMessage() {
    final text = _msgController.text.trim();
    if (text.isEmpty) return;

    setState(() {
      _messages.add(_ChatMessage(
        text: text,
        isMine: true,
        time: "${DateTime.now().hour}:${DateTime.now().minute.toString().padLeft(2, '0')}",
      ));
      _msgController.clear();
    });

    // Scroll pastga
    Future.delayed(const Duration(milliseconds: 100), () {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });

    // TODO: Backend'ga xabar yuborish
    // ApiService().sendMessage(widget.userId, widget.receiverId, text);
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AppColors>()!;

    return Scaffold(
      backgroundColor: colors.background,
      appBar: AppBar(
        backgroundColor: colors.surface,
        elevation: 0,
        leading: IconButton(
          icon: Icon(Icons.arrow_back_ios_rounded, color: colors.textPrimary),
          onPressed: () => Navigator.pop(context),
        ),
        title: Row(
          children: [
            Container(
              width: 40, height: 40,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: LinearGradient(colors: [colors.primary, colors.primaryLight]),
              ),
              child: Center(
                child: Text(
                  widget.receiverName.isNotEmpty ? widget.receiverName[0].toUpperCase() : 'S',
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
                ),
              ),
            ),
            const SizedBox(width: 12),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(widget.receiverName, style: TextStyle(color: colors.textPrimary, fontSize: 15, fontWeight: FontWeight.bold)),
                Text("Online", style: TextStyle(color: colors.success, fontSize: 11)),
              ],
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: Icon(Icons.phone_rounded, color: colors.primary),
            onPressed: () {},
          ),
        ],
      ),
      body: Column(
        children: [
          // Xabarlar ro'yxati
          Expanded(
            child: ListView.builder(
              controller: _scrollController,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              itemCount: _messages.length,
              itemBuilder: (_, i) => _buildMessage(colors, _messages[i]),
            ),
          ),

          // Xabar yozish
          Container(
            padding: const EdgeInsets.fromLTRB(16, 8, 8, 24),
            decoration: BoxDecoration(
              color: colors.surface,
              border: Border(top: BorderSide(color: colors.border)),
            ),
            child: Row(
              children: [
                Expanded(
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    decoration: BoxDecoration(
                      color: colors.surfaceVariant,
                      borderRadius: BorderRadius.circular(24),
                    ),
                    child: TextField(
                      controller: _msgController,
                      style: TextStyle(color: colors.textPrimary),
                      decoration: InputDecoration(
                        hintText: "Xabar yozing...",
                        hintStyle: TextStyle(color: colors.textTertiary),
                        border: InputBorder.none,
                        contentPadding: const EdgeInsets.symmetric(vertical: 12),
                      ),
                      onSubmitted: (_) => _sendMessage(),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                GestureDetector(
                  onTap: _sendMessage,
                  child: Container(
                    width: 44, height: 44,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(colors: [colors.primary, colors.primaryLight]),
                    ),
                    child: const Icon(Icons.send_rounded, color: Colors.white, size: 20),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMessage(AppColors colors, _ChatMessage message) {
    return Align(
      alignment: message.isMine ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.72),
        decoration: BoxDecoration(
          color: message.isMine ? colors.primary : colors.surface,
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(16),
            topRight: const Radius.circular(16),
            bottomLeft: Radius.circular(message.isMine ? 16 : 4),
            bottomRight: Radius.circular(message.isMine ? 4 : 16),
          ),
          border: message.isMine ? null : Border.all(color: colors.border),
          boxShadow: [
            BoxShadow(color: Colors.black.withOpacity(0.04), blurRadius: 4, offset: const Offset(0, 2)),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text(
              message.text,
              style: TextStyle(
                color: message.isMine ? Colors.white : colors.textPrimary,
                fontSize: 14,
                height: 1.4,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              message.time,
              style: TextStyle(
                color: message.isMine ? Colors.white70 : colors.textTertiary,
                fontSize: 10,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ChatMessage {
  final String text;
  final bool isMine;
  final String time;

  _ChatMessage({required this.text, required this.isMine, required this.time});
}
