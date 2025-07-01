# 📁 Archive Directory Structure

## 📝 **Mục đích:**
Thư mục này chứa các files đã được tổ chức lại để dễ bảo trì và nâng cấp ứng dụng.

## 📂 **Cấu trúc:**

### `/tests/` - Files kiểm tra và testing
- `test_*.py` - Các script test chức năng
- Không ảnh hưởng đến core application

### `/fixes/` - Files fix và patch tạm thời  
- `*fix*.py`, `*FIX*.py` - Các bản fix lỗi cũ
- Không còn sử dụng trong version hiện tại

### `/docs/` - Documentation và hướng dẫn
- `*.md` files - Tài liệu, guide, summary
- Thông tin lịch sử phát triển

### `/backups/` - Scripts backup và utilities
- `auto_backup.py` - Script backup tự động
- `scheduled_backup.py` - Backup theo lịch
- `run_with_backup.py` - Chạy app với backup

### `/deprecated/` - Files không còn sử dụng
- Các script debug, optimize cũ
- Files thử nghiệm đã lỗi thời

## ⚠️ **Lưu ý:**
- **KHÔNG XÓA** thư mục này khi nâng cấp
- Có thể **AN TOÀN** xóa từng thư mục con nếu chắc chắn không cần
- Core application ở `/src/` **KHÔNG BỊ ẢNH HƯỞNG**

## ✅ **Core Application (KHÔNG ĐỘNG VÀO):**
- `/src/` - Mã nguồn chính
- `run_*.bat` - Scripts chạy ứng dụng  
- `accounts.json`, `proxy.csv` - Config files
- `requirements.txt` - Dependencies 