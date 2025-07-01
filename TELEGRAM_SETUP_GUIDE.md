# 🚀 Hướng dẫn sử dụng Telegram Automation Tool

## 📋 Yêu cầu hệ thống

### 1. Cài đặt Dependencies

```bash
pip install telethon PySide6
```

### 2. Lấy API Credentials từ Telegram

1. Truy cập: <https://my.telegram.org/apps>
2. Đăng nhập bằng số điện thoại Telegram
3. Tạo ứng dụng mới:
   - **App title**: Telegram Automation Tool
   - **Short name**: telegram_bot
   - **Platform**: Desktop
4. Sao chép **API ID** và **API Hash**

### 3. Cấu hình API

Mở file `telegram_config.json` và điền thông tin:

```json
{
  "api_id": "123456789",
  "api_hash": "abcdef123456789abcdef123456789abc",
  "session_folder": "sessions"
}
```

## 🎯 Cách sử dụng

### 1. Quản lý Tài khoản Telegram

#### Thêm tài khoản

1. Mở tab **"Quản lý Tài khoản Telegram"**
2. Click **"Thêm tài khoản"**
3. Nhập số điện thoại (với mã quốc gia): `+84123456789`
4. Nhập mã xác minh từ Telegram
5. Nếu có 2FA, nhập mật khẩu

#### Kiểm tra tài khoản

1. Tick chọn tài khoản cần kiểm tra
2. Click **"Kiểm tra"**
3. Xem trạng thái trong bảng

### 2. Gửi tin nhắn Telegram

#### Chuẩn bị

1. Mở tab **"Nhắn tin Telegram"**
2. **Load danh sách người nhận**:
   - Click **"Load danh sách"**
   - Chọn file `.txt` chứa username hoặc số điện thoại
   - Format: mỗi dòng 1 người nhận

   ```
   @username1
   @username2
   +84123456789
   +84987654321
   ```

#### Tạo tin nhắn

1. Click **"Thêm"** để tạo tin nhắn mới
2. Nhập nội dung tin nhắn
3. Tùy chọn: Chọn file media (ảnh/video)
4. Tick chọn tin nhắn để sử dụng

#### Cấu hình gửi

- **Số luồng**: 1-10 (tài khoản gửi đồng thời)
- **Số lỗi tối đa**: Dừng sau bao nhiêu lỗi liên tiếp
- **Số tin nhắn**: Giới hạn tin nhắn mỗi tài khoản
- **Delay**: Khoảng thời gian giữa các lần gửi (giây)

#### Bắt đầu gửi

1. Click **"Bắt đầu"**
2. Theo dõi tiến trình trong bảng
3. Click **"Dừng"** để dừng lại

## 📁 Cấu trúc file

```
telegram_config.json      # Cấu hình API
telegram_account.json     # Danh sách tài khoản
message_templates.json    # Mẫu tin nhắn
sessions/                 # Session files của Telegram
├── +84123456789.session
└── +84987654321.session
```

## ⚠️ Lưu ý quan trọng

### Bảo mật

- **KHÔNG** chia sẻ file session với ai
- **KHÔNG** public API ID/Hash lên internet
- Backup file config và session thường xuyên

### Giới hạn Telegram

- Không gửi quá 30 tin nhắn/phút/tài khoản
- Không spam hoặc gửi tin nhắn không mong muốn
- Tuân thủ Terms of Service của Telegram

### Troubleshooting

#### Lỗi "API ID invalid"

- Kiểm tra lại API ID và Hash trong `telegram_config.json`
- Đảm bảo đã tạo app trên my.telegram.org

#### Lỗi "Phone number invalid"

- Đảm bảo số điện thoại có mã quốc gia: `+84123456789`
- Số điện thoại phải đã đăng ký Telegram

#### Lỗi "Flood wait"

- Telegram giới hạn tần suất gửi tin
- Tăng delay giữa các tin nhắn
- Chờ và thử lại sau

## 🆘 Hỗ trợ

Nếu gặp vấn đề:

1. Kiểm tra log trong console
2. Đảm bảo internet ổn định  
3. Restart ứng dụng
4. Xóa file session và đăng nhập lại

## 📝 Changelog

- **v1.0**: Chuyển đổi hoàn toàn từ Instagram sang Telegram
- Hỗ trợ multi-account messaging
- Giao diện thân thiện người dùng
