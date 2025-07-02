import time
import os
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from PySide6.QtWidgets import QInputDialog, QMessageBox

class TelegramLogin:
    def __init__(self, proxy=None, user_data_dir=None):
        self.proxy = proxy
        self.user_data_dir = user_data_dir
        self.driver = None
        self.wait = None
        
    def init_driver(self):
        """Khởi tạo Chrome driver với cấu hình tối ưu"""
        try:
            options = Options()
            
            # ⚡ SIÊU TỐI ƯU: Tắt các tính năng không cần thiết (NHƯNG GIỮ LẠI JS)
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-web-security')
            options.add_argument('--disable-features=VizDisplayCompositor')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-plugins')
            options.add_argument('--disable-images')
            # Không tắt JavaScript vì Telegram Web cần JS để hoạt động
            # options.add_argument('--disable-javascript')
            # options.add_argument('--disable-css')
            
            # ⚡ TỐI ƯU: Giảm memory và tăng tốc
            options.add_argument('--memory-pressure-off')
            options.add_argument('--max_old_space_size=4096')
            
            # Thêm proxy nếu có
            if self.proxy:
                options.add_argument(f'--proxy-server={self.proxy}')
            
            # Thêm user data dir nếu có
            if self.user_data_dir:
                os.makedirs(self.user_data_dir, exist_ok=True)
                options.add_argument(f'--user-data-dir={self.user_data_dir}')
            
            # ⚡ SIÊU TỐI ƯU: Khởi tạo driver với timeout ngắn
            self.driver = webdriver.Chrome(options=options)
            self.driver.set_page_load_timeout(30)
            self.driver.implicitly_wait(10)
            self.wait = WebDriverWait(self.driver, 15)
            
            print(f"[TELEGRAM] Driver initialized successfully")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to initialize driver: {e}")
            return False
    
    def login(self, phone_number, password_2fa=None, parent_widget=None):
        """Đăng nhập Telegram Web"""
        try:
            if not self.init_driver():
                return {"success": False, "error": "Failed to initialize driver"}
            
            print(f"[TELEGRAM] Starting login for {phone_number}")
            
            # Bước 1: Mở Telegram Web
            self.driver.get("https://web.telegram.org/k/")
            time.sleep(3)
            
            # Bước 2: Nhập số điện thoại
            phone_input = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='tel']"))
            )
            phone_input.clear()
            phone_input.send_keys(phone_number)
            
            # Click nút Next
            next_button = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn-primary"))
            )
            next_button.click()
            time.sleep(2)
            
            print(f"[TELEGRAM] Phone number entered: {phone_number}")
            
            # Bước 3: Xử lý OTP
            otp_result = self._handle_otp(parent_widget)
            if not otp_result["success"]:
                return otp_result
            
            # Bước 4: Xử lý 2FA nếu cần
            if password_2fa:
                fa2_result = self._handle_2fa(password_2fa, parent_widget)
                if not fa2_result["success"]:
                    return fa2_result
            
            # Bước 5: Kiểm tra đăng nhập thành công
            success = self._check_login_success()
            if success:
                # Lưu session
                session_data = self._save_session(phone_number)
                return {
                    "success": True, 
                    "message": "Đăng nhập thành công!",
                    "session": session_data
                }
            else:
                return {"success": False, "error": "Login verification failed"}
                
        except TimeoutException:
            return {"success": False, "error": "Timeout - Trang web phản hồi chậm"}
        except Exception as e:
            return {"success": False, "error": f"Lỗi đăng nhập: {str(e)}"}
        finally:
            if self.driver:
                self.driver.quit()
    
    def _handle_otp(self, parent_widget):
        """Xử lý OTP code"""
        try:
            # Chờ input OTP xuất hiện
            otp_input = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input.input-field-input"))
            )
            
            # Yêu cầu người dùng nhập OTP
            if parent_widget:
                otp_code, ok = QInputDialog.getText(
                    parent_widget, "Nhập OTP", 
                    "Nhập mã OTP từ Telegram:"
                )
                if not ok or not otp_code.strip():
                    return {"success": False, "error": "Người dùng hủy nhập OTP"}
            else:
                otp_code = input("Nhập mã OTP từ Telegram: ")
            
            # Nhập OTP
            otp_input.clear()
            otp_input.send_keys(otp_code.strip())
            time.sleep(2)
            
            print(f"[TELEGRAM] OTP entered successfully")
            return {"success": True}
            
        except Exception as e:
            return {"success": False, "error": f"Lỗi xử lý OTP: {str(e)}"}
    
    def _handle_2fa(self, password_2fa, parent_widget):
        """Xử lý 2FA password"""
        try:
            # Chờ input 2FA xuất hiện
            password_input = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password']"))
            )
            
            # Nhập mật khẩu 2FA
            password_input.clear()
            password_input.send_keys(password_2fa)
            
            # Click nút Submit
            submit_button = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn-primary"))
            )
            submit_button.click()
            time.sleep(3)
            
            print(f"[TELEGRAM] 2FA password entered successfully")
            return {"success": True}
            
        except Exception as e:
            return {"success": False, "error": f"Lỗi xử lý 2FA: {str(e)}"}
    
    def _check_login_success(self):
        """Kiểm tra đăng nhập thành công"""
        try:
            # Chờ và kiểm tra các phần tử cho thấy đăng nhập thành công
            success_indicators = [
                ".chat-list",
                ".sidebar-left",
                ".chat-input",
                ".im-page-chat-container"
            ]
            
            for indicator in success_indicators:
                try:
                    element = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, indicator))
                    )
                    if element:
                        print(f"[TELEGRAM] Login success indicator found: {indicator}")
                        return True
                except:
                    continue
            
            # Kiểm tra URL
            current_url = self.driver.current_url
            if "web.telegram.org" in current_url and "#" in current_url:
                print(f"[TELEGRAM] Login success - URL: {current_url}")
                return True
                
            return False
            
        except Exception as e:
            print(f"[ERROR] Error checking login success: {e}")
            return False
    
    def _save_session(self, phone_number):
        """Lưu session data"""
        try:
            session_dir = f"sessions/{phone_number}"
            os.makedirs(session_dir, exist_ok=True)
            
            # Lưu cookies
            cookies = self.driver.get_cookies()
            with open(f"{session_dir}/cookies.json", "w") as f:
                json.dump(cookies, f, indent=2)
            
            # Lưu local storage (nếu có thể)
            try:
                local_storage = self.driver.execute_script("return window.localStorage;")
                with open(f"{session_dir}/localStorage.json", "w") as f:
                    json.dump(local_storage, f, indent=2)
            except:
                pass
            
            # Lưu session info
            session_info = {
                "phone": phone_number,
                "login_time": datetime.now().isoformat(),
                "url": self.driver.current_url,
                "user_agent": self.driver.execute_script("return navigator.userAgent;")
            }
            
            with open(f"{session_dir}/session_info.json", "w") as f:
                json.dump(session_info, f, indent=2)
            
            print(f"[TELEGRAM] Session saved for {phone_number}")
            return session_info
            
        except Exception as e:
            print(f"[ERROR] Error saving session: {e}")
            return None
    
    def check_live(self, phone_number):
        """Kiểm tra tài khoản còn live không"""
        try:
            if not self.init_driver():
                return {"success": False, "error": "Failed to initialize driver"}
            
            # Thử load session cũ
            session_loaded = self._load_session(phone_number)
            
            # Mở Telegram Web
            self.driver.get("https://web.telegram.org/k/")
            time.sleep(5)
            
            # Kiểm tra xem đã đăng nhập chưa
            if self._check_login_success():
                return {
                    "success": True, 
                    "status": "✅ Đã đăng nhập",
                    "message": "Tài khoản còn live và đã đăng nhập"
                }
            else:
                # Kiểm tra có lỗi gì không
                error_elements = self.driver.find_elements(By.CSS_SELECTOR, ".error, .alert-danger")
                if error_elements:
                    error_text = error_elements[0].text
                    return {
                        "success": False,
                        "status": "❌ Lỗi",
                        "error": error_text
                    }
                else:
                    return {
                        "success": False,
                        "status": "⚠️ Chưa đăng nhập",
                        "message": "Cần đăng nhập lại"
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "status": "❌ Lỗi kiểm tra",
                "error": str(e)
            }
        finally:
            if self.driver:
                self.driver.quit()
    
    def _load_session(self, phone_number):
        """Load session data cũ"""
        try:
            session_dir = f"sessions/{phone_number}"
            
            # Load cookies
            cookies_file = f"{session_dir}/cookies.json"
            if os.path.exists(cookies_file):
                with open(cookies_file, "r") as f:
                    cookies = json.load(f)
                
                # Mở trang trước khi add cookies
                self.driver.get("https://web.telegram.org")
                
                # Add cookies
                for cookie in cookies:
                    try:
                        self.driver.add_cookie(cookie)
                    except:
                        pass
                
                print(f"[TELEGRAM] Session loaded for {phone_number}")
                return True
                
        except Exception as e:
            print(f"[ERROR] Error loading session: {e}")
            
        return False 