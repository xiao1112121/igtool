# 🤖 Telegram AI Automation Tool

Công cụ tự động hóa Telegram với tích hợp AI mạnh mẽ, hỗ trợ quản lý nhiều tài khoản và tương tác thông minh.

## ✨ Tính năng chính

### 🔐 Quản lý tài khoản

- Quản lý 19+ tài khoản Telegram
- Đăng nhập tự động qua Telegram API (không cần browser)
- Hỗ trợ 2FA và proxy
- Phân loại tài khoản theo thư mục
- Import/Export tài khoản từ CSV/TXT

### 🤖 AI Integration

- **AI Provider**: Groq API với model `llama-3.1-8b-instant`
- **12 AI Personalities**: Hài hước, Thân thiện, Chuyên nghiệp, Sáng tạo, v.v.
- **Rate Limiting**: Bảo vệ khỏi spam API
- **Threading**: UI không bị đơ khi xử lý AI
- **Error Handling**: Xử lý lỗi thông minh

### 💬 Messaging System

- Gửi tin nhắn hàng loạt
- Template tin nhắn với biến động
- Lọc tài khoản theo thư mục
- Thống kê tin nhắn

### 🔍 Data Scanner

- Quét dữ liệu từ các group/channel
- Phân tích thành viên
- Export dữ liệu

### 🌐 Proxy Management

- Hỗ trợ HTTP/SOCKS proxy
- Kiểm tra trạng thái proxy
- Rotation proxy tự động

## 🚀 Cài đặt

### Yêu cầu hệ thống

- Python 3.13+
- Windows 10/11
- RAM: 4GB+
- Disk: 1GB free space

### Cài đặt dependencies

```bash
pip install -r src/requirements.txt
```

### Chạy ứng dụng

```bash
python src/main.py
```

## 🔧 Cấu hình

### AI Configuration

File `ai_config.json`:
```json
{
  "provider": "groq",
  "api_key": "YOUR_GROQ_API_KEY",
  "base_url": "https://api.groq.com/openai/v1",
  "model": "llama-3.1-8b-instant",
  "max_tokens": 1000,
  "temperature": 0.7
}
```

### Telegram Setup

1. Lấy API credentials từ [my.telegram.org](https://my.telegram.org)
2. Cấu hình trong tab "Quản lý tài khoản"
3. Đăng nhập từng tài khoản

## 📁 Cấu trúc dự án

```
├── src/
│   ├── main.py              # Entry point
│   ├── ai/                  # AI integration
│   │   ├── ai_client.py     # Groq AI client
│   │   └── telegram_bot.py  # Telegram bot manager
│   ├── ui/                  # GUI components
│   │   ├── account_management.py
│   │   ├── ai_management.py
│   │   ├── messaging.py
│   │   └── ...
│   └── utils/               # Utilities
├── data/                    # Data storage
├── sessions/               # Telegram sessions
└── README.md
```

## 🎯 Sử dụng

### 1. Quản lý tài khoản

- Thêm tài khoản Telegram bằng số điện thoại
- Đăng nhập tự động
- Phân loại vào thư mục

### 2. Sử dụng AI

- Chọn personality AI
- Test response trong tab "Quản lý AI"
- Tích hợp vào messaging

### 3. Gửi tin nhắn

- Tạo template tin nhắn
- Chọn tài khoản và target
- Gửi hàng loạt với AI

### 4. Quét dữ liệu

- Chọn group/channel
- Quét thành viên
- Export CSV

## 🛡️ Bảo mật

- ✅ API keys được bảo vệ trong `.gitignore`
- ✅ Sessions được mã hóa
- ✅ Rate limiting chống spam
- ✅ Error handling an toàn
- ✅ No browser automation (stealth)

## 🔄 Backup & Recovery

Tự động backup:
```bash
python archive/backups/auto_backup.py
```

## 📊 Thống kê

- 19+ tài khoản Telegram active
- 12 AI personalities
- 3+ message templates
- 4 thư mục phân loại

## 🤝 Đóng góp

1. Fork dự án
2. Tạo feature branch
3. Commit changes
4. Push và tạo Pull Request

## 📄 License

Private project - All rights reserved

## 🆘 Hỗ trợ

- 📧 Email: [your-email]
- 💬 Telegram: [your-telegram]
- 🐛 Issues: GitHub Issues

---

**⚠️ Lưu ý**: Tuân thủ Terms of Service của Telegram khi sử dụng tool này.
