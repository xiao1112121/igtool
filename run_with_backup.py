#!/usr/bin/env python3
"""
Wrapper script để tự động backup code trước khi chạy ứng dụng
Sử dụng: python run_with_backup.py
"""

import os
import sys
import subprocess
import datetime
from pathlib import Path

def run_backup():
    """Chạy script backup"""
    print("🔄 Tự động backup code trước khi chạy ứng dụng...")
    
    try:
        # Tạo commit message với timestamp
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        commit_message = f"Auto backup before run - {timestamp}"
        
        # Chạy script backup
        result = subprocess.run([
            sys.executable, 
            "auto_backup.py", 
            commit_message
        ], check=False)
        
        if result.returncode == 0:
            print("✅ Backup thành công!")
        else:
            print("⚠️  Backup thất bại, nhưng vẫn tiếp tục chạy ứng dụng...")
            
    except Exception as e:
        print(f"❌ Lỗi khi backup: {e}")
        print("⚠️  Vẫn tiếp tục chạy ứng dụng...")

def run_application():
    """Chạy ứng dụng chính"""
    print("\n🚀 Khởi động ứng dụng Instagram Tool...")
    
    try:
        # Chạy ứng dụng chính
        subprocess.run([sys.executable, "src/main.py"], check=True)
    except KeyboardInterrupt:
        print("\n⏹️  Ứng dụng bị dừng bởi người dùng")
    except Exception as e:
        print(f"❌ Lỗi khi chạy ứng dụng: {e}")
        sys.exit(1)

def main():
    """Hàm main"""
    print("🔄 Instagram Tool - Auto Backup & Run")
    print("=" * 50)
    
    # Kiểm tra xem file main.py có tồn tại không
    if not Path("src/main.py").exists():
        print("❌ Không tìm thấy src/main.py")
        print("Đảm bảo bạn đang chạy script từ thư mục gốc của dự án")
        sys.exit(1)
    
    # Chạy backup trước
    run_backup()
    
    # Chạy ứng dụng
    run_application()

if __name__ == "__main__":
    main() 