#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⚡ ULTRA FAST STEALTH LOGIN OPTIMIZATION
Tối ưu hóa siêu nhanh cho quy trình đăng nhập Instagram

Mục tiêu tốc độ:
- Session login: 3-5 giây
- Manual login: 8-12 giây
- Driver init: 2-3 giây
"""

import time
import random
import json
import os
from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class UltraFastChromeDriver:
    """⚡ Siêu tối ưu ChromeDriver để khởi tạo nhanh nhất có thể"""
    
    def __init__(self):
        self.driver_cache = {}  # Cache driver instances
        self.session_cache = {}  # Cache session cookies
        
    def create_ultra_fast_driver(self, proxy=None, username=None) -> webdriver.Chrome:
        """⚡ Tạo ChromeDriver siêu nhanh với tối ưu tối đa"""
        try:
            start_time = time.time()
            
            # ⚡ Chrome options siêu tối ưu
        options = Options()
        
            # ⚡ Tắt tất cả tính năng không cần thiết để tăng tốc
            options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-plugins")
            options.add_argument("--disable-images")  # Không tải ảnh để tăng tốc
            options.add_argument("--disable-javascript")  # Tắt JS không cần thiết
            options.add_argument("--disable-css")  # Tắt CSS để tăng tốc
            options.add_argument("--disable-web-security")
            options.add_argument("--disable-features=VizDisplayCompositor")
            options.add_argument("--disable-ipc-flooding-protection")
            options.add_argument("--disable-renderer-backgrounding")
            options.add_argument("--disable-backgrounding-occluded-windows")
            options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-background-networking")
            options.add_argument("--disable-default-apps")
        options.add_argument("--disable-sync")
            options.add_argument("--disable-translate")
            options.add_argument("--hide-scrollbars")
            options.add_argument("--mute-audio")
            options.add_argument("--no-first-run")
            options.add_argument("--no-default-browser-check")
            options.add_argument("--disable-logging")
            options.add_argument("--disable-log-file")
            options.add_argument("--log-level=3")
            options.add_argument("--silent")
            
            # ⚡ Tối ưu bộ nhớ và CPU
            options.add_argument("--memory-pressure-off")
            options.add_argument("--max_old_space_size=4096")
        options.add_argument("--aggressive-cache-discard")
            
            # ⚡ Tối ưu network
            options.add_argument("--disable-background-networking")
            options.add_argument("--disable-background-downloads")
            options.add_argument("--disable-preconnect")
            
            # ⚡ User Agent ngẫu nhiên nhưng cố định cho session
            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            ]
            options.add_argument(f"--user-agent={random.choice(user_agents)}")
            
            # ⚡ Proxy setup nếu có
            if proxy:
                options.add_argument(f"--proxy-server={proxy}")
                print(f"[⚡ PROXY] Sử dụng proxy: {proxy}")
            
            # ⚡ Profile riêng cho mỗi username để tăng tốc
            if username:
                profile_path = f"./chrome_profiles/{username}"
                os.makedirs(profile_path, exist_ok=True)
                options.add_argument(f"--user-data-dir={profile_path}")
                
            # ⚡ Tắt automation indicators
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # ⚡ Prefs siêu tối ưu
            prefs = {
                "profile.default_content_setting_values": {
                    "notifications": 2,  # Block notifications
                    "media_stream": 2,   # Block media
                    "geolocation": 2,    # Block location
                    "images": 2,         # Block images để tăng tốc
                    "plugins": 2,        # Block plugins
                    "popups": 2,         # Block popups
                    "mixed_script": 2,   # Block mixed content
                },
                "profile.managed_default_content_settings": {
                    "images": 2,         # Block images
                    "javascript": 1,     # Allow minimal JS
                },
                "profile.default_content_settings": {
                    "images": 2,
                    "plugins": 2,
                    "popups": 2,
                    "geolocation": 2,
                    "notifications": 2,
                    "media_stream": 2,
                },
                # ⚡ Tắt password manager để tăng tốc
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False,
                # ⚡ Tắt safe browsing
                "safebrowsing.enabled": False,
                "safebrowsing.disable_download_protection": True,
                # ⚡ Tắt các service không cần thiết
                "translate_enabled": False,
                "spellcheck.dictionaries": [],
                "spellcheck.use_spelling_service": False,
            }
            options.add_experimental_option("prefs", prefs)
            
            # ⚡ Service với timeout ngắn
            service = Service()
            service.creation_flags = 0x08000000  # CREATE_NO_WINDOW flag
            
            # ⚡ Tạo driver với timeout siêu ngắn
            driver = webdriver.Chrome(service=service, options=options)
            
            # ⚡ Cấu hình timeout siêu ngắn
            driver.set_page_load_timeout(8)  # Chỉ 8 giây
            driver.implicitly_wait(1)        # Chỉ 1 giây
            
            # ⚡ Inject stealth scripts ngay sau khi tạo
            self._inject_stealth_scripts(driver)
            
            # ⚡ Set window size nhỏ để tăng tốc render
            driver.set_window_size(1024, 768)
            
            elapsed = time.time() - start_time
            print(f"[⚡ DRIVER] ChromeDriver khởi tạo trong {elapsed:.1f}s")
            
            return driver
            
        except Exception as e:
            print(f"[⚡ ERROR] Lỗi khởi tạo driver: {e}")
            return None
    
    def _inject_stealth_scripts(self, driver):
        """⚡ Inject các script stealth siêu nhanh"""
        try:
            # ⚡ Script tối ưu để ẩn automation
            stealth_script = """
            // Hide webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // Override plugins length
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            // Override languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
            
            // Override chrome property
            window.chrome = {
                runtime: {},
            };
            
            // Remove automation indicators
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
            """
            
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': stealth_script
            })
            
            print("[⚡ STEALTH] Stealth scripts injected")
            
        except Exception as e:
            print(f"[⚡ WARN] Stealth injection warning: {e}")

class UltraFastLoginManager:
    """⚡ Quản lý đăng nhập siêu nhanh"""
    
    def __init__(self):
        self.driver_factory = UltraFastChromeDriver()
        self.session_cache = {}
        
    def ultra_fast_session_login(self, username: str, driver) -> bool:
        """⚡ Đăng nhập từ session siêu nhanh - mục tiêu 3-5 giây"""
        try:
            start_time = time.time()
            print(f"[⚡ SESSION] Bắt đầu session login cho {username}")
            
            # ⚡ Load cookies nhanh
            cookies_loaded = self._load_cookies_ultra_fast(driver, username)
            if not cookies_loaded:
                print(f"[⚡ SESSION] Không có cookies cho {username}")
                return False
            
            # ⚡ Navigate với timeout ngắn
            try:
                driver.get("https://www.instagram.com/")
            except Exception as e:
                print(f"[⚡ WARN] Timeout navigate, tiếp tục: {e}")
            
            # ⚡ Chờ tối thiểu
            time.sleep(1)
            
            # ⚡ Kiểm tra login siêu nhanh
            login_success = self._check_login_ultra_fast(driver)
            
            elapsed = time.time() - start_time
            if login_success:
                print(f"[⚡ SUCCESS] Session login thành công trong {elapsed:.1f}s")
                return True
else:
                print(f"[⚡ FAIL] Session login thất bại sau {elapsed:.1f}s")
                return False
                
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"[⚡ ERROR] Session login error sau {elapsed:.1f}s: {e}")
            return False
    
    def ultra_fast_manual_login(self, username: str, password: str, driver) -> bool:
        """⚡ Đăng nhập thủ công siêu nhanh - mục tiêu 8-12 giây"""
        try:
            start_time = time.time()
            print(f"[⚡ MANUAL] Bắt đầu manual login cho {username}")
            
            # ⚡ Tìm và điền form siêu nhanh
            login_success = self._fill_login_form_ultra_fast(driver, username, password)
            
            if login_success:
                # ⚡ Lưu cookies ngay
                self._save_cookies_ultra_fast(driver, username)
                
                elapsed = time.time() - start_time
                print(f"[⚡ SUCCESS] Manual login thành công trong {elapsed:.1f}s")
                return True
            else:
                elapsed = time.time() - start_time
                print(f"[⚡ FAIL] Manual login thất bại sau {elapsed:.1f}s")
                return False
                
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"[⚡ ERROR] Manual login error sau {elapsed:.1f}s: {e}")
            return False
    
    def _load_cookies_ultra_fast(self, driver, username: str) -> bool:
        """⚡ Load cookies siêu nhanh"""
        try:
            cookies_file = f"sessions/{username}/cookies.json"
            if not os.path.exists(cookies_file):
                return False
                
            with open(cookies_file, "r", encoding="utf-8") as f:
                cookies = json.load(f)
            
            # ⚡ Add cookies nhanh nhất có thể
            for cookie in cookies:
                try:
                    driver.add_cookie(cookie)
                except:
                    continue
            
            return True
            
        except Exception as e:
            print(f"[⚡ WARN] Load cookies error: {e}")
            return False
    
    def _save_cookies_ultra_fast(self, driver, username: str):
        """⚡ Lưu cookies siêu nhanh"""
        try:
            sessions_dir = f"sessions/{username}"
            os.makedirs(sessions_dir, exist_ok=True)
            
            cookies = driver.get_cookies()
            cookies_file = f"{sessions_dir}/cookies.json"
            
            with open(cookies_file, "w", encoding="utf-8") as f:
                json.dump(cookies, f)
                
            print(f"[⚡ COOKIES] Saved cookies for {username}")
            
        except Exception as e:
            print(f"[⚡ WARN] Save cookies error: {e}")
    
    def _check_login_ultra_fast(self, driver) -> bool:
        """⚡ Kiểm tra login siêu nhanh - chỉ 2 giây"""
        try:
            wait = WebDriverWait(driver, 2)
            
            # ⚡ Kiểm tra home icon trước (nhanh nhất)
            try:
                home_icon = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "svg[aria-label='Home']"))
                )
                if home_icon.is_displayed():
                    return True
            except TimeoutException:
                pass
            
            # ⚡ Kiểm tra URL pattern
            current_url = driver.current_url.lower()
            if "instagram.com" in current_url and "login" not in current_url:
                # ⚡ Quick element check
                try:
                    profile_elements = [
                        "img[alt*='profile picture']",
                        "svg[aria-label='Direct']",
                        "[data-testid='user-avatar']"
                    ]
                    
                    for selector in profile_elements:
                        try:
                            element = driver.find_element(By.CSS_SELECTOR, selector)
                            if element.is_displayed():
                                return True
                        except:
                            continue
                except:
                    pass
            
            return False
            
        except Exception as e:
            print(f"[⚡ WARN] Login check error: {e}")
            return False
    
    def _fill_login_form_ultra_fast(self, driver, username: str, password: str) -> bool:
        """⚡ Điền form login siêu nhanh"""
        try:
            wait = WebDriverWait(driver, 3)
            
            # ⚡ Tìm username field
            username_input = None
            username_selectors = [
                "input[name='username']",
                "input[aria-label*='username']"
            ]
            
            for selector in username_selectors:
                try:
                    username_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    break
                except TimeoutException:
                    continue
            
            if not username_input:
                return False
            
            # ⚡ Điền username
            username_input.clear()
            username_input.send_keys(username)
            
            # ⚡ Tìm password field
            password_input = driver.find_element(By.CSS_SELECTOR, "input[name='password']")
            password_input.clear()
            password_input.send_keys(password)
            
            # ⚡ Submit bằng Enter
            from selenium.webdriver.common.keys import Keys
            password_input.send_keys(Keys.ENTER)
            
            # ⚡ Chờ và kiểm tra kết quả
            max_wait = 5
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                time.sleep(0.5)
                
                if self._check_login_ultra_fast(driver):
                    return True
                
                # Check URL change
                if "login" not in driver.current_url.lower():
                    time.sleep(1)
                    if self._check_login_ultra_fast(driver):
                        return True
                    break
            
            return False
            
        except Exception as e:
            print(f"[⚡ ERROR] Fill form error: {e}")
            return False

# ⚡ Factory function cho việc sử dụng dễ dàng
def create_ultra_fast_driver(proxy=None, username=None):
    """⚡ Tạo driver siêu nhanh - wrapper function"""
    factory = UltraFastChromeDriver()
    return factory.create_ultra_fast_driver(proxy, username)

def ultra_fast_login(username: str, password: str, proxy=None) -> tuple:
    """
    ⚡ Hàm đăng nhập siêu nhanh hoàn chỉnh
    Trả về: (success: bool, driver: webdriver, elapsed_time: float, method: str)
    """
    total_start = time.time()
    
    try:
        # ⚡ Tạo driver
        driver = create_ultra_fast_driver(proxy, username)
        if not driver:
            return False, None, 0, "driver_error"
        
        # ⚡ Thử session login trước
        login_manager = UltraFastLoginManager()
        
        session_success = login_manager.ultra_fast_session_login(username, driver)
        if session_success:
            elapsed = time.time() - total_start
            return True, driver, elapsed, "session"
        
        # ⚡ Thử manual login
        manual_success = login_manager.ultra_fast_manual_login(username, password, driver)
        elapsed = time.time() - total_start
        
        if manual_success:
            return True, driver, elapsed, "manual"
else:
            return False, driver, elapsed, "failed"
            
    except Exception as e:
        elapsed = time.time() - total_start
        print(f"[⚡ ERROR] Ultra fast login error: {e}")
        return False, None, elapsed, "error"

if __name__ == "__main__":
    # ⚡ Test siêu nhanh
    print("⚡ ULTRA FAST STEALTH LOGIN TEST")
    
    # Test tạo driver
    start = time.time()
    driver = create_ultra_fast_driver()
    if driver:
        elapsed = time.time() - start
        print(f"✅ Driver created in {elapsed:.1f}s")
        driver.quit()
    else:
        print("❌ Driver creation failed") 