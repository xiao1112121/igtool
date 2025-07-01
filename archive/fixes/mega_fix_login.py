#!/usr/bin/env python3
"""MEGA FIX: Sửa tất cả vấn đề đăng nhập Instagram"""

import os
import shutil
from datetime import datetime

def apply_fixes():
    file_path = "src/ui/account_management.py"
    
    if not os.path.exists(file_path):
        print("❌ File không tồn tại")
        return False
    
    # Backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{file_path}.backup_mega_{timestamp}"
    shutil.copy2(file_path, backup_path)
    print(f"✅ Backup: {backup_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    fixes_applied = []
    
    # FIX 1: CAPTCHA infinite loop
    old_captcha = '''                            else:
                                print(f"[WARN] Captcha đã giải nhưng chưa thấy icons, tiếp tục chờ...")
                                continue'''
    
    new_captcha = '''                            else:
                                # ⭐ FIX CAPTCHA: Retry logic thay vì continue
                                print(f"[DEBUG] Captcha done - start retry logic...")
                                
                                max_retry = 5
                                for retry_i in range(max_retry):
                                    time.sleep(1.5)
                                    print(f"[DEBUG] Captcha retry {retry_i+1}/{max_retry}")
                                    
                                    if self.check_home_and_explore_icons(driver):
                                        print(f"[SUCCESS] ✅ Success after captcha retry {retry_i+1}")
                                        account["status"] = "🎉 Vượt captcha thành công!"
                                        self.status_updated.emit(username, account["status"])
                                        
                                        def save_and_cleanup():
                                            try:
                                                self.save_cookies(driver, username)
                                                account["status"] = "Đã đăng nhập"
                                                self.status_updated.emit(username, account["status"])
                                            except Exception as e:
                                                print(f"[WARN] Save error: {e}")
                                            finally:
                                                self.close_browser_safely(driver, username)
                                        
                                        import threading
                                        threading.Thread(target=save_and_cleanup, daemon=True).start()
                                        return "Đã đăng nhập", "OK", None
                                
                                # Timeout - break loop
                                print(f"[WARN] Captcha timeout after {max_retry} retries")
                                account["status"] = "⏰ Timeout sau captcha"
                                self.status_updated.emit(username, account["status"])
                                break'''
    
    if old_captcha in content:
        content = content.replace(old_captcha, new_captcha)
        fixes_applied.append("CAPTCHA infinite loop")
    
    # FIX 2: Tối ưu loop timing
    old_timing = '''            max_wait_time = 15  # ⚡ Tăng từ 10s lên 15s để có thời gian xử lý 2FA
            check_interval = 0.8  # ⚡ Giảm từ 1.0s xuống 0.8s để check nhanh hơn'''
    
    new_timing = '''            max_wait_time = 20  # ⚡ Đủ thời gian cho các trường hợp phức tạp
            check_interval = 0.3  # ⚡ Nhanh hơn 2.7x (0.8s -> 0.3s)'''
    
    if old_timing in content:
        content = content.replace(old_timing, new_timing)
        fixes_applied.append("Loop timing optimization")
    
    # FIX 3: Giảm debug trong loop
    old_log = '''                    print(f"[DEBUG] Vòng lặp kiểm tra - Thời gian đã trôi qua: {elapsed_time:.1f}s/{max_wait_time}s")
                    
                    time.sleep(check_interval)
                    
                    print(f"[DEBUG] Kiểm tra trạng thái đăng nhập cho {username} - URL: {driver.current_url}")'''
    
    new_log = '''                    # ⚡ TỐI ƯU: Chỉ log mỗi 2s
                    if int(elapsed_time) % 2 == 0:
                        print(f"[DEBUG] ⚡ Check {elapsed_time:.0f}s/{max_wait_time}s")
                    
                    time.sleep(check_interval)'''
    
    if old_log in content:
        content = content.replace(old_log, new_log)
        fixes_applied.append("Reduced debug logging")
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return fixes_applied

if __name__ == "__main__":
    print("🚀 MEGA FIX: Login Issues")
    print("=" * 40)
    
    fixes = apply_fixes()
    if fixes:
        print("✅ APPLIED FIXES:")
        for fix in fixes:
            print(f"   • {fix}")
        print("")
        print("📈 EXPECTED RESULTS:")
        print("   • No infinite loops")
        print("   • 3x faster detection")
        print("   • Cleaner logs")
        print("")
        print("🚀 Restart app to apply!")
    else:
        print("❌ No fixes applied")
    
    print("=" * 40) 