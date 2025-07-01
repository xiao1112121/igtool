#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔥 SIMPLE LOGIN FIX: Thay thế method phức tạp bằng logic đơn giản
❌ Vấn đề: Method login_instagram_and_get_info quá phức tạp và bị hang
✅ Giải pháp: Method đơn giản chỉ check login và return ngay
"""

def simple_login_method():
    """
    Method login đơn giản thay thế cho method phức tạp
    """
    return '''
    def login_instagram_and_get_info(self, account, window_position=None, max_retries=3, retry_delay=5):
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
            return "Lỗi", "Error", None
    '''

if __name__ == "__main__":
    print("🔥 SIMPLE LOGIN FIX được tạo thành công!")
    print("Sao chép method trên và thay thế vào file account_management.py") 