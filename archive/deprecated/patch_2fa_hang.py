#!/usr/bin/env python3
"""AUTO PATCH - Sửa lỗi bot đơ sau 2FA"""

import os
import shutil
from datetime import datetime
import time

def backup_file(file_path):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{file_path}.backup_{timestamp}"
    shutil.copy2(file_path, backup_path)
    print(f"✅ Backup: {backup_path}")
    return backup_path

def patch_2fa_hang():
    file_path = "src/ui/account_management.py"
    
    if not os.path.exists(file_path):
        print(f"❌ File không tồn tại: {file_path}")
        return False
    
    backup_file(file_path)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern tìm kiếm ngắn gọn hơn
    old_pattern = "continue  # ← ĐOẠN NÀY GÂY RA INFINITE LOOP"
    
    if old_pattern not in content:
        if "max_retry_after_2fa = 8" in content:
            print("✅ Đã được patch!")
            return True
        print("❌ Không tìm thấy pattern cần patch")
        return False
    
    # Tìm và thay thế đoạn code có vấn đề  
    old_block = '''                            else:
                                print(f"[WARN] 2FA đã nhập nhưng chưa thấy icons, tiếp tục chờ...")
                                # Tiếp tục vòng lặp để chờ thêm
                                continue'''
    
    new_block = '''                            else:
                                # ⭐ THAY ĐỔI: Không continue nữa, dùng retry logic riêng
                                print(f"[DEBUG] 2FA submitted, bắt đầu retry logic...")
                                
                                # RETRY LOGIC SAU 2FA
                                max_retry = 6
                                for i in range(max_retry):
                                    time.sleep(2)
                                    print(f"[DEBUG] Retry {i+1}/{max_retry} sau 2FA")
                                    
                                    if self.check_home_and_explore_icons(driver):
                                        print(f"[SUCCESS] ✅ Thành công retry {i+1}")
                                        account["status"] = "🎉 Vượt 2FA thành công!"
                                        self.status_updated.emit(username, account["status"])
                                        
                                        def save_and_cleanup():
                                            try:
                                                self.save_cookies(driver, username)
                                                account["status"] = "Đã đăng nhập"
                                                self.status_updated.emit(username, account["status"])
                                            except Exception as e:
                                                print(f"[WARN] Save cookies error: {e}")
                                            finally:
                                                self.close_browser_safely(driver, username)
                                        
                                        import threading
                                        threading.Thread(target=save_and_cleanup, daemon=True).start()
                                        return "Đã đăng nhập", "OK", None
                                    
                                    # Check form save login
                                    if self.check_save_login_info(driver):
                                        print(f"[INFO] Xử lý save login form")
                                        self.handle_save_login_info(driver, username)
                                        continue
                                
                                # Hết retry, break khỏi vòng lặp chính
                                print(f"[WARN] Timeout sau 2FA retry")
                                account["status"] = "⏰ Timeout sau 2FA"
                                self.status_updated.emit(username, account["status"])
                                break'''
    
    if old_block in content:
        new_content = content.replace(old_block, new_block)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print("✅ PATCH THÀNH CÔNG!")
        return True
    else:
        print("❌ Không tìm thấy block cần patch")
        return False

if __name__ == "__main__":
    print("🚨 AUTO PATCH: Fix 2FA Hang")
    print("=" * 40)
    
    if patch_2fa_hang():
        print("🎉 Đã fix lỗi bot đơ sau 2FA!")
        print("🚀 Restart ứng dụng để áp dụng!")
    else:
        print("❌ Patch thất bại")
    
    print("=" * 40) 