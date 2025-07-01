#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔥 REPLACE METHOD: Thay thế method phức tạp bằng method đơn giản
"""

import shutil
import re

def replace_method():
    print("🔥 Bắt đầu thay thế method phức tạp...")
    
    # Backup file gốc
    try:
        shutil.copy('src/ui/account_management.py', 'src/ui/account_management.py.BACKUP_BEFORE_SIMPLE_FIX')
        print("✅ Đã backup file gốc")
    except Exception as e:
        print(f"❌ Lỗi backup: {e}")
        return False
    
    # Đọc file
    try:
        with open('src/ui/account_management.py', 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Lỗi đọc file: {e}")
        return False
    
    # Method đơn giản thay thế
    simple_method = '''    def login_instagram_and_get_info(self, account, window_position=None, max_retries=3, retry_delay=5):
        """🔥 SIMPLE LOGIN: Logic đơn giản, không vòng lặp phức tạp"""
        username = account.get("username", "")
        password = account.get("password", "")
        
        print(f"[DEBUG] 🔥 SIMPLE LOGIN bắt đầu cho {username}")
        
        try:
            # Khởi tạo driver
            driver = self.init_driver(account.get("proxy"), username)
            if not driver:
                print(f"[ERROR] Không thể khởi tạo driver cho {username}")
                account["status"] = "Lỗi khởi tạo driver"
                self.status_updated.emit(username, account["status"])
                return "Lỗi", "Error", None
            
            # Mở Instagram
            print(f"[DEBUG] Mở Instagram cho {username}")
            driver.get("https://www.instagram.com/")
            time.sleep(2)
            
            # Load cookies nếu có
            self.load_cookies(driver, username)
            time.sleep(1)
            
            # CHECK ĐĂNG NHẬP ĐƠN GIẢN
            print(f"[DEBUG] 🔥 CHECK ĐĂNG NHẬP ĐƠN GIẢN cho {username}")
            
            if self.check_home_and_explore_icons(driver):
                print(f"[SUCCESS] ✅ ĐÃ ĐĂNG NHẬP: {username}")
                account["status"] = "Đã đăng nhập"
                self.status_updated.emit(username, account["status"])
                self.save_cookies(driver, username)
                self.close_browser_safely(driver, username)
                return "Đã đăng nhập", "OK", None
            else:
                print(f"[INFO] ❌ CHƯA ĐĂNG NHẬP: {username}")
                account["status"] = "Cần đăng nhập thủ công"  
                self.status_updated.emit(username, account["status"])
                # Giữ browser mở để user đăng nhập thủ công
                return "Cần đăng nhập thủ công", "Manual", driver
                
        except Exception as e:
            print(f"[ERROR] Lỗi simple login: {e}")
            account["status"] = f"Lỗi: {str(e)}"
            self.status_updated.emit(username, account["status"])
            if 'driver' in locals():
                self.close_browser_safely(driver, username)
            return "Lỗi", "Error", None'''
    
    # Tìm vị trí bắt đầu method
    start_marker = "def login_instagram_and_get_info(self, account"
    start_pos = content.find(start_marker)
    
    if start_pos == -1:
        print("❌ Không tìm thấy method login_instagram_and_get_info")
        return False
    
    print(f"✅ Tìm thấy method ở vị trí: {start_pos}")
    
    # Tìm method tiếp theo để biết kết thúc
    lines = content[start_pos:].split('\n')
    method_lines = []
    found_next_method = False
    
    for i, line in enumerate(lines):
        if i == 0:
            # Dòng def đầu tiên
            method_lines.append(line)
            continue
            
        # Nếu gặp def mới ở cùng level (4 spaces indent) thì dừng
        if line.strip() and line.startswith("    def ") and not line.startswith("        "):
            print(f"✅ Tìm thấy method tiếp theo: {line.strip()}")
            found_next_method = True
            break
            
        method_lines.append(line)
    
    if not found_next_method:
        print("❌ Không tìm thấy method tiếp theo để làm boundary")
        return False
    
    # Thay thế method cũ
    old_method = '\n'.join(method_lines)
    new_content = content.replace(old_method, simple_method)
    
    # Lưu file
    try:
        with open('src/ui/account_management.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("🎉 ĐÃ THAY THẾ METHOD THÀNH CÔNG!")
        return True
    except Exception as e:
        print(f"❌ Lỗi lưu file: {e}")
        return False

if __name__ == "__main__":
    success = replace_method()
    if success:
        print("✅ HOÀN TẤT! Method đã được thay thế bằng version đơn giản.")
        print("🚀 Bây giờ restart app và test thử!")
    else:
        print("❌ THẤT BẠI! Kiểm tra lỗi ở trên.") 