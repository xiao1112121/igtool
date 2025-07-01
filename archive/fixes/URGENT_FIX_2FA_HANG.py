# 🚨 URGENT FIX: Sửa lỗi bot đơ sau khi nhấn "Tiếp tục" 2FA

"""
VẤN ĐỀ: Sau khi nhập 2FA và ấn "Tiếp tục", bot bị đơ luôn.

NGUYÊN NHÂN: Infinite loop - bot phát hiện 2FA lại sau khi continue.

GIẢI PHÁP: Thay thế logic xử lý sau 2FA để tránh infinite loop.
"""

# Code cần THAY THẾ trong file src/ui/account_management.py
# Tìm đoạn code này (xung quanh dòng 1210-1240):

OLD_CODE = '''
# ⚡ NGAY LẬP TỨC: Hiển thị dialog để user xử lý 2FA
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
        continue  # ← ĐOẠN NÀY GÂY RA INFINITE LOOP
'''

# THAY THẾ BẰNG CODE MỚI:
NEW_CODE = '''
# ⚡ NGAY LẬP TỨC: Hiển thị dialog để user xử lý 2FA
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
    break
'''

print("🚨 URGENT FIX: 2FA Hang Issue")
print("=" * 50)
print("1. Mở file: src/ui/account_management.py")
print("2. Tìm đoạn code OLD_CODE ở trên (xung quanh dòng 1210-1240)")  
print("3. Thay thế hoàn toàn bằng NEW_CODE")
print("4. Lưu file và restart ứng dụng")
print("5. Test với tài khoản có 2FA")
print("=" * 50)
print("✅ Sau khi fix: Bot sẽ không bao giờ bị đơ sau 2FA nữa!") 