#!/usr/bin/env python3
"""
Script tự động backup code lên GitHub
Sử dụng: python auto_backup.py [commit_message]
"""

import os
import sys
import subprocess
import datetime
from pathlib import Path

# Cấu hình GitHub
GITHUB_REPO_URL = "https://github.com/xiao1112121/ig19062025.git"
GITHUB_BRANCH = "master"

def run_command(command, check=True):
    """Chạy lệnh shell và trả về kết quả"""
    print(f"[CMD] {command}")
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            check=check, 
            capture_output=True, 
            text=True,
            encoding='utf-8'
        )
        if result.stdout:
            print(f"[OUT] {result.stdout.strip()}")
        return result
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Command failed: {e}")
        if e.stderr:
            print(f"[STDERR] {e.stderr}")
        return None

def check_git_config():
    """Kiểm tra cấu hình Git"""
    print("🔧 Kiểm tra cấu hình Git...")
    
    # Kiểm tra user.name
    result = run_command("git config user.name", check=False)
    if not result or not result.stdout.strip():
        print("⚠️  Chưa cấu hình user.name")
        name = input("Nhập tên của bạn: ")
        run_command(f'git config user.name "{name}"')
    
    # Kiểm tra user.email
    result = run_command("git config user.email", check=False)
    if not result or not result.stdout.strip():
        print("⚠️  Chưa cấu hình user.email")
        email = input("Nhập email của bạn: ")
        run_command(f'git config user.email "{email}"')

def setup_remote():
    """Thiết lập remote repository"""
    print("🔗 Thiết lập remote repository...")
    
    # Kiểm tra remote origin
    result = run_command("git remote get-url origin", check=False)
    if not result:
        print("➕ Thêm remote origin...")
        run_command(f"git remote add origin {GITHUB_REPO_URL}")
    else:
        print("✅ Remote origin đã tồn tại")

def create_gitignore_if_not_exists():
    """Tạo .gitignore nếu chưa có"""
    gitignore_path = Path(".gitignore")
    if not gitignore_path.exists():
        print("📝 Tạo file .gitignore...")
        gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual Environment
venv/
env/
ENV/

# Logs
*.log
application.log

# Browser profiles and sessions (chứa thông tin nhạy cảm)
sessions/*/
!sessions/.gitkeep

# Chrome cache và temp files
chromedriver-win64/
*.tmp
*.temp

# Cookies và session data (chứa thông tin đăng nhập)
*_cookies.json
*_session.json
*.session

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Selenium wire temp files
.seleniumwire/

# Test files
test_*.py
debug_*.py
fix_*.py
"""
        with open(gitignore_path, 'w', encoding='utf-8') as f:
            f.write(gitignore_content)
        print("✅ Đã tạo .gitignore")

def backup_to_github(commit_message=None):
    """Backup code lên GitHub"""
    print("🚀 Bắt đầu backup lên GitHub...")
    
    # Tạo commit message mặc định nếu không có
    if not commit_message:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        commit_message = f"Auto backup - {timestamp}"
    
    # Kiểm tra trạng thái Git
    result = run_command("git status --porcelain")
    if not result or not result.stdout.strip():
        print("✅ Không có thay đổi nào để commit")
        return True
    
    # Add tất cả files (trừ những file trong .gitignore)
    print("📦 Thêm files vào staging area...")
    run_command("git add .")
    
    # Commit
    print("💾 Tạo commit...")
    run_command(f'git commit -m "{commit_message}"')
    
    # Push lên GitHub
    print("⬆️  Push lên GitHub...")
    result = run_command(f"git push origin {GITHUB_BRANCH}", check=False)
    
    if not result:
        print("⚠️  Push thất bại, thử force push...")
        result = run_command(f"git push -f origin {GITHUB_BRANCH}", check=False)
        
        if not result:
            print("❌ Không thể push lên GitHub. Kiểm tra:")
            print("   1. Kết nối internet")
            print("   2. Quyền truy cập repository")
            print("   3. GitHub token/credentials")
            return False
    
    print("✅ Backup thành công!")
    return True

def main():
    """Hàm main"""
    print("🔄 Instagram Tool - Auto Backup Script")
    print("=" * 50)
    
    # Kiểm tra xem đang ở thư mục Git không
    if not Path(".git").exists():
        print("❌ Không phải thư mục Git repository")
        print("Khởi tạo Git repository...")
        run_command("git init")
        print("✅ Đã khởi tạo Git repository")
    
    # Thiết lập cấu hình
    check_git_config()
    setup_remote()
    create_gitignore_if_not_exists()
    
    # Lấy commit message từ argument
    commit_message = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else None
    
    # Thực hiện backup
    success = backup_to_github(commit_message)
    
    if success:
        print("\n🎉 Backup hoàn tất!")
        print(f"🔗 Repository: {GITHUB_REPO_URL}")
    else:
        print("\n❌ Backup thất bại!")
        sys.exit(1)

if __name__ == "__main__":
    main() 