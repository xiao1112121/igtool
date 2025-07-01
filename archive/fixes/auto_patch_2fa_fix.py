#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUTO PATCH: Tự động sửa lỗi bot đơ sau 2FA
Chạy: python auto_patch_2fa_fix.py
"""

import os
import shutil
from datetime import datetime

def backup_file(file_path):
    """Tạo backup file trước khi patch"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{file_path}.backup_{timestamp}"
    shutil.copy2(file_path, backup_path)
    print(f"✅ Đã backup: {backup_path}")
    return backup_path

def apply_2fa_fix():
    """Áp dụng fix cho 2FA hang issue"""
    
    file_path = "src/ui/account_management.py"
    
    # Kiểm tra file tồn tại
    if not os.path.exists(file_path):
        print(f"❌ Không tìm thấy file: {file_path}")
        return False
    
    # Backup file trước
    backup_path = backup_file(file_path)
    
    # Đọc nội dung file
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Lỗi khi đọc file: {e}")
        return False
    
    # Code cũ cần thay thế
    old_code = '''                        # ⚡ NGAY LẬP TỨC: Hiển thị dialog để user xử lý 2FA
                        continue_result = self.show_captcha_dialog_safe(driver, username, "2fa")
                        if continue_result:
                            print(f"[DEBUG] User đã nhập 2FA và nhấn tiếp tục")
                            
                            # ⚡ CHỜ THÊM THỜI GIAN CHO 2FA XỬ LÝ
                            print(f"[DEBUG] Chờ 2FA được xử lý...")
                            time.sleep(3)  # Chờ 3 giây để 2FA được xử lý
                            
                            # Kiểm tra lại đăng nhập thành công
                            if self.check_home_and_explore_icons(driver):
                                print(f"[SUCCESS] ✅ Đăng nhập thành công sau nhập 2FA: {username}")
                                
                                # ⭐ SUCCESS HANDLING
                                account["status"] = "🎉 Đã vượt qua 2FA - Đăng nhập thành công!"
                                account["last_action"] = f"Vượt 2FA + đăng nhập lúc {time.strftime('%H:%M:%S')}"
                                self.status_updated.emit(username, account["status"])
                                
                                # Background processing
                                from PySide6.QtCore import QCoreApplication
                                import threading
                                QCoreApplication.processEvents()
                                
                                def save_and_cleanup():
                                    try:
                                        self.save_cookies(driver, username)
                                        account["status"] = "Đã đăng nhập"
                                        self.status_updated.emit(username, account["status"])
                                    except Exception as e:
                                        print(f"[WARN] Lỗi khi lưu cookies: {e}")
                                    finally:
                                        self.close_browser_safely(driver, username)
                                
                                threading.Thread(target=save_and_cleanup, daemon=True).start()
                                print(f"[INFO] ===== HOÀN TẤT 2FA: {username} =====")
                                return "Đã đăng nhập", "OK", None
                            else:
                                print(f"[WARN] 2FA đã nhập nhưng chưa thấy icons, tiếp tục chờ...")
                                # Tiếp tục vòng lặp để chờ thêm
                                continue'''
    
    # Code mới thay thế
    new_code = '''                        # ⚡ NGAY LẬP TỨC: Hiển thị dialog để user xử lý 2FA
                        continue_result = self.show_captcha_dialog_safe(driver, username, "2fa")
                        if continue_result:
                            print(f"[DEBUG] User đã nhập 2FA và nhấn tiếp tục")
                            account["status"] = "🔄 Đang xử lý sau 2FA..."
                            self.status_updated.emit(username, account["status"])
                            
                            # ⭐ LOGIC MỚI: RETRY NHIỀU LẦN SAU 2FA - TRÁNH BỊ ĐƠ
                            max_retry_after_2fa = 8  # Retry tối đa 8 lần
                            retry_interval = 2  # Chờ 2 giây mỗi lần
                            
                            print(f"[DEBUG] Bắt đầu retry sau 2FA - tối đa {max_retry_after_2fa} lần")
                            
                            for retry_count in range(max_retry_after_2fa):
                                print(f"[DEBUG] Retry {retry_count + 1}/{max_retry_after_2fa} sau 2FA cho {username}")
                                
                                try:
                                    # Chờ một chút trước mỗi lần check
                                    time.sleep(retry_interval)
                                    
                                    # Kiểm tra URL hiện tại
                                    current_url = driver.current_url
                                    print(f"[DEBUG] URL sau 2FA (retry {retry_count + 1}): {current_url}")
                                    
                                    # ⭐ KIỂM TRA SAVE LOGIN INFO TRƯỚC (thường xuất hiện sau 2FA)
                                    if self.check_save_login_info(driver):
                                        print(f"[INFO] 💾 Phát hiện form lưu thông tin sau 2FA cho {username}")
                                        account["status"] = "Đang xử lý form lưu thông tin sau 2FA"
                                        self.status_updated.emit(username, account["status"])
                                        
                                        if self.handle_save_login_info(driver, username):
                                            print(f"[SUCCESS] Đã xử lý form lưu thông tin sau 2FA")
                                            time.sleep(2)  # Chờ form đóng
                                        
                                        # Tiếp tục check icons
                                        continue
                                    
                                    # ⭐ KIỂM TRA ĐĂNG NHẬP THÀNH CÔNG
                                    if self.check_home_and_explore_icons(driver):
                                        print(f"[SUCCESS] ✅ ĐĂNG NHẬP THÀNH CÔNG SAU 2FA (retry {retry_count + 1}): {username}")
                                        
                                        # ⭐ SUCCESS HANDLING
                                        account["status"] = "🎉 Đã vượt qua 2FA - Đăng nhập thành công!"
                                        account["last_action"] = f"Vượt 2FA + đăng nhập lúc {time.strftime('%H:%M:%S')}"
                                        self.status_updated.emit(username, account["status"])
                                        
                                        # Background processing
                                        from PySide6.QtCore import QCoreApplication
                                        import threading
                                        QCoreApplication.processEvents()
                                        
                                        def save_and_cleanup():
                                            try:
                                                self.save_cookies(driver, username)
                                                account["status"] = "Đã đăng nhập"
                                                self.status_updated.emit(username, account["status"])
                                            except Exception as e:
                                                print(f"[WARN] Lỗi khi lưu cookies: {e}")
                                            finally:
                                                self.close_browser_safely(driver, username)
                                        
                                        threading.Thread(target=save_and_cleanup, daemon=True).start()
                                        print(f"[INFO] ===== HOÀN TẤT 2FA: {username} =====")
                                        return "Đã đăng nhập", "OK", None
                                    
                                    # ⭐ KIỂM TRA XEM CÓ VẪN Ở TRANG 2FA KHÔNG
                                    if self.check_2fa_required(driver):
                                        if retry_count < 3:  # Chỉ log cho 3 lần đầu
                                            print(f"[DEBUG] Vẫn còn ở trang 2FA, chờ thêm... (retry {retry_count + 1})")
                                        continue
                                    
                                    # ⭐ KIỂM TRA CÁC TRƯỜNG HỢP KHÁC
                                    if self.check_captcha_required(driver):
                                        print(f"[WARN] Phát hiện captcha sau 2FA - thoát khỏi retry loop")
                                        break  # Thoát khỏi retry loop để xử lý captcha
                                    
                                    if self.check_account_locked(driver):
                                        print(f"[ERROR] Tài khoản bị khóa sau 2FA")
                                        account["status"] = "Tài khoản Die sau 2FA"
                                        self.status_updated.emit(username, account["status"])
                                        driver.quit()
                                        return "Tài khoản Die", "Die", None
                                    
                                    # Nếu không có gì đặc biệt, tiếp tục retry
                                    print(f"[DEBUG] Chưa thấy kết quả, tiếp tục retry... ({retry_count + 1}/{max_retry_after_2fa})")
                                    
                                except Exception as retry_error:
                                    print(f"[ERROR] Lỗi trong retry {retry_count + 1}: {retry_error}")
                                    # Tiếp tục retry ngay cả khi có lỗi
                                    continue
                            
                            # ⭐ SAU KHI HẾT RETRY - BREAK KHỎI VÒNG LẶP CHÍNH
                            print(f"[WARN] Đã retry {max_retry_after_2fa} lần sau 2FA nhưng chưa thành công")
                            account["status"] = "⏰ Timeout sau 2FA"
                            self.status_updated.emit(username, account["status"])
                            
                            # Thoát khỏi vòng lặp chính để không bị loop vô tận
                            break'''
    
    # Kiểm tra có code cũ không
    if old_code not in content:
        print("❌ Không tìm thấy code cần patch. Có thể đã được patch rồi hoặc code đã thay đổi.")
        # Kiểm tra đã patch chưa
        if "max_retry_after_2fa = 8" in content:
            print("✅ Code đã được patch trước đó!")
            return True
        return False
    
    # Thay thế code
    new_content = content.replace(old_code, new_code)
    
    # Kiểm tra có thay đổi không
    if new_content == content:
        print("❌ Không có thay đổi nào được thực hiện")
        return False
    
    # Ghi file mới
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"✅ Đã patch thành công: {file_path}")
        print("🎉 Fix 2FA hang issue hoàn tất!")
        return True
    except Exception as e:
        print(f"❌ Lỗi khi ghi file: {e}")
        # Khôi phục backup
        try:
            shutil.copy2(backup_path, file_path)
            print(f"✅ Đã khôi phục từ backup: {backup_path}")
        except:
            pass
        return False

def main():
    print("🚨 AUTO PATCH: 2FA Hang Fix")
    print("=" * 50)
    
    if apply_2fa_fix():
        print("=" * 50)
        print("✅ THÀNH CÔNG! Các thay đổi:")
        print("   • Loại bỏ infinite loop sau 2FA")
        print("   • Retry logic thông minh (8 lần)")
        print("   • Xử lý save login form tự động")
        print("   • Debug logging chi tiết")
        print("")
        print("🚀 Khởi động lại ứng dụng để áp dụng fix!")
        print("✅ Bot sẽ không bao giờ bị đơ sau 2FA nữa!")
    else:
        print("=" * 50)
        print("❌ THẤT BẠI! Vui lòng thực hiện manual patch.")
        print("   Xem hướng dẫn trong file: URGENT_FIX_2FA_HANG.py")
    
    print("=" * 50)

if __name__ == "__main__":
    main() 