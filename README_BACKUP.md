# 🔄 Hệ thống Auto Backup cho Instagram Tool

Hệ thống tự động backup code lên GitHub trước mỗi lần chỉnh sửa hoặc chạy ứng dụng.

## 📋 Các file trong hệ thống

- `auto_backup.py` - Script chính để backup code lên GitHub
- `run_with_backup.py` - Wrapper script tự động backup trước khi chạy ứng dụng
- `run_with_backup.bat` - File batch cho Windows
- `.gitignore` - Loại bỏ các file không cần thiết khỏi Git

## 🚀 Cách sử dụng

### Phương pháp 1: Chạy với auto backup (Khuyến nghị)
```bash
# Trên Windows
run_with_backup.bat

# Hoặc trực tiếp với Python
python run_with_backup.py
```

### Phương pháp 2: Backup thủ công
```bash
# Backup với message tự động
python auto_backup.py

# Backup với message tùy chỉnh
python auto_backup.py "Cập nhật tính năng login"
```

### Phương pháp 3: Chạy ứng dụng thông thường (không backup)
```bash
python src/main.py
```

## ⚙️ Thiết lập lần đầu

### 1. Cấu hình Git (nếu chưa có)
Script sẽ tự động hỏi thông tin nếu chưa cấu hình:
- Tên người dùng
- Email

### 2. Xác thực GitHub
Bạn cần xác thực với GitHub một trong các cách sau:

#### Cách 1: GitHub CLI (Khuyến nghị)
```bash
# Cài đặt GitHub CLI
# https://cli.github.com/

# Đăng nhập
gh auth login
```

#### Cách 2: Personal Access Token
1. Tạo Personal Access Token tại: https://github.com/settings/tokens
2. Cấp quyền `repo` cho token
3. Khi push lần đầu, nhập:
   - Username: `username_github_của_bạn`
   - Password: `personal_access_token`

#### Cách 3: SSH Key
```bash
# Tạo SSH key
ssh-keygen -t ed25519 -C "your_email@example.com"

# Thêm SSH key vào GitHub
# https://github.com/settings/keys

# Thay đổi remote URL sang SSH
git remote set-url origin git@github.com:xiao1112121/ig19062025.git
```

## 📁 Cấu trúc backup

### Files được backup:
- ✅ Tất cả source code (`.py`)
- ✅ Configuration files (`.json`, `.qss`)
- ✅ README và documentation
- ✅ Requirements và setup files

### Files KHÔNG được backup (trong .gitignore):
- ❌ Session data và cookies (`*_cookies.json`, `*_session.json`)
- ❌ Browser profiles (`sessions/*/`)
- ❌ Log files (`*.log`)
- ❌ Cache và temp files
- ❌ Virtual environment (`venv/`)
- ❌ Python cache (`__pycache__/`)

## 🔧 Tùy chỉnh

### Thay đổi repository URL
Chỉnh sửa trong `auto_backup.py`:
```python
GITHUB_REPO_URL = "https://github.com/your_username/your_repo.git"
```

### Thay đổi branch
```python
GITHUB_BRANCH = "main"  # hoặc "master"
```

### Thêm files vào .gitignore
Chỉnh sửa file `.gitignore` để loại bỏ thêm files không cần thiết.

## 🐛 Xử lý lỗi thường gặp

### Lỗi: "Permission denied"
- Kiểm tra xác thực GitHub
- Đảm bảo có quyền push vào repository

### Lỗi: "Repository not found"
- Kiểm tra URL repository
- Đảm bảo repository tồn tại và public/có quyền truy cập

### Lỗi: "Git not configured"
- Chạy script, nó sẽ tự động hỏi thông tin cấu hình

### Lỗi: "Nothing to commit"
- Không có gì để backup, đây là trạng thái bình thường

## 📊 Workflow tự động

1. **Trước khi chạy ứng dụng:**
   - Kiểm tra thay đổi code
   - Tự động commit với timestamp
   - Push lên GitHub
   - Chạy ứng dụng

2. **Backup thủ công:**
   - Chạy `python auto_backup.py`
   - Nhập commit message (tùy chọn)

3. **Khôi phục code:**
   - Clone từ GitHub: `git clone https://github.com/xiao1112121/ig19062025.git`
   - Hoặc pull changes: `git pull origin main`

## 🔒 Bảo mật

- ⚠️ **Quan trọng:** Session data và cookies KHÔNG được backup để bảo vệ thông tin đăng nhập
- ✅ Chỉ source code và configuration được backup
- ✅ Repository có thể để public vì không chứa thông tin nhạy cảm

## 📞 Hỗ trợ

Nếu gặp vấn đề, kiểm tra:
1. Kết nối internet
2. Quyền truy cập GitHub repository
3. Cấu hình Git local
4. GitHub authentication

---

**Lưu ý:** Luôn backup code trước khi thực hiện thay đổi lớn! 