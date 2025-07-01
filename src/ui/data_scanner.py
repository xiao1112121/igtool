from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QPushButton, 
                            QTableWidget, QTableWidgetItem, QComboBox, QLabel, 
                            QLineEdit, QSpinBox, QRadioButton, QCheckBox, 
                            QGroupBox, QTextEdit, QFrame, QGridLayout, QStackedWidget, QFileDialog, QMessageBox, QSizePolicy, QHeaderView, QProgressBar, QScrollArea, QSplitter, QTabWidget, QApplication, QStyledItemDelegate, QMenu, QAbstractItemView)
from PySide6.QtCore import Qt, QSize, QTimer, QThread, Signal, QModelIndex, QRect, QEvent
from PySide6.QtGui import QIcon, QFont, QPixmap, QColor, QPalette, QPainter, QPen
import random
from src.ui.context_menus import DataScannerContextMenu
from src.ui.account_management import CheckboxDelegate
import os, json
import logging
from datetime import datetime
import time

# ⭐ THÊM INSTAGRAM SCANNER THẬT
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    from selenium.webdriver.chrome.service import Service
    selenium_available = True
except ImportError:
    webdriver = None
    Service = None
    selenium_available = False

class InstagramScanner:
    """⭐ INSTAGRAM SCANNER THẬT sử dụng logic từ Account Management"""
    
    def __init__(self, account_management_tab=None):    
        self.driver = None
        self.logger = logging.getLogger(__name__)
        self.account_management = account_management_tab  # Reference đến AccountManagementTab
        
        # ⭐ USER AGENTS VÀ LANGUAGES từ Account Management
        self.USER_AGENTS = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        ]
        self.LANGUAGES = [
            "en-US,en;q=0.9",
            "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        ]
        
    def init_driver_from_account_management(self, proxy=None, username=None):
        """⭐ SỬ DỤNG LOGIC INIT_DRIVER TỪ ACCOUNT MANAGEMENT"""
        if not selenium_available:
            self.logger.error("Selenium không có sẵn!")
            return False
            
        print(f"[DEBUG][Scanner] Khởi tạo driver cho {username} với proxy: {proxy}")
        
        try:
            # ⭐ SỬ DỤNG seleniumwire như Account Management
            from seleniumwire import webdriver as wire_webdriver
            from selenium.webdriver.chrome.options import Options
            
            options = Options()
            
            # ⭐ APP MODE NHỎ GỌN như Account Management
            options.add_argument("--app=https://www.instagram.com/")
            
            # ⭐ TỐI ƯU ARGS từ Account Management
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--disable-infobars")
            options.add_argument("--disable-notifications")
            options.add_argument("--disable-extensions")
            options.add_argument("--no-default-browser-check")
            options.add_argument("--no-first-run")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-background-networking")
            options.add_argument("--disable-sync")
            
            # ⭐ PREFS từ Account Management
            prefs = {
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False,
                "translate": {"enabled": False},
                "intl.accept_languages": "en,en_US",
                "profile.default_content_setting_values.notifications": 2,
                "profile.default_content_settings.popups": 0,
                "profile.default_content_setting_values.geolocation": 2,
                "session.restore_on_startup": 4,
                "profile.exit_type": "Normal",
                "profile.exited_cleanly": True,
            }
            options.add_experimental_option("prefs", prefs)
            
            # ⭐ USER AGENT RANDOM
            random_user_agent = random.choice(self.USER_AGENTS)
            options.add_argument(f"user-agent={random_user_agent}")
            random_language = random.choice(self.LANGUAGES)
            options.add_argument(f"--lang={random_language}")
            
            # ⭐ KÍCH THƯỚC CỬA SỔ NHỎ GỌN
            options.add_argument("--window-size=450,380")
            
            # ⭐ USER DATA DIR riêng cho từng tài khoản
            if username:
                profile_dir = os.path.abspath(f'sessions/{username}_profile')
                os.makedirs(profile_dir, exist_ok=True)
                options.add_argument(f'--user-data-dir={profile_dir}')
            
            # ⭐ PROXY LOGIC từ Account Management
            proxy_options = {}
            if proxy:
                proxy_parts = proxy.split(':')
                if len(proxy_parts) == 4:
                    proxy_ip_port = f"{proxy_parts[0]}:{proxy_parts[1]}"
                    proxy_user = proxy_parts[2]
                    proxy_pass = proxy_parts[3]
                    proxy_options = {
                        'proxy': {
                            'http': f'http://{proxy_user}:{proxy_pass}@{proxy_ip_port}',
                            'https': f'https://{proxy_user}:{proxy_pass}@{proxy_ip_port}',
                            'no_proxy': 'localhost,127.0.0.1' 
                        }
                    }
                elif len(proxy_parts) == 2:
                    proxy_ip_port = f"{proxy_parts[0]}:{proxy_parts[1]}"
                    proxy_options = {
                        'proxy': {
                            'http': f'http://{proxy_ip_port}',
                            'https': f'https://{proxy_ip_port}'
                        }
                    }
            
            # ⭐ KHỞI TẠO DRIVER
            self.driver = wire_webdriver.Chrome(seleniumwire_options=proxy_options, options=options)
            print(f"[SUCCESS][Scanner] Driver khởi tạo thành công cho {username}")
            return True
            
        except Exception as e:
            self.logger.error(f"Lỗi khởi tạo driver: {e}")
            return False
    
    def setup_driver(self, proxy=None, username=None):
        """⭐ WRAPPER cho init_driver_from_account_management"""
        return self.init_driver_from_account_management(proxy, username)
    
    def login_with_account_management_logic(self, account_data):
        """⭐ SỬ DỤNG LOGIC ĐĂNG NHẬP HOÀN CHỈNH TỪ ACCOUNT MANAGEMENT"""
        username = account_data.get("username")
        password = account_data.get("password")
        
        # ⭐ PROXY LOGIC từ Account Management
        if getattr(self.account_management, 'use_proxy', True):
            permanent_proxy = account_data.get("permanent_proxy", "").strip()
            if permanent_proxy:
                proxy = permanent_proxy
            else:
                proxy = account_data.get("proxy", "").strip()
                if not proxy:
                    proxy = None
        else:
            proxy = None
        
        print(f"[INFO][Scanner] Bắt đầu đăng nhập {username} với proxy: {proxy}")
        
        try:
            # ⭐ KHỞI TẠO DRIVER
            if not self.init_driver_from_account_management(proxy, username):
                return False
            
            # ⭐ TRUY CẬP INSTAGRAM
            self.driver.get("https://www.instagram.com/")
            time.sleep(1)
            
            # ⭐ LOAD COOKIES từ Account Management
            cookies_loaded = self.load_cookies_from_account_management(username)
            
            if cookies_loaded:
                self.driver.refresh()
                time.sleep(1.5)
                
                # ⭐ KIỂM TRA ĐĂNG NHẬP THÀNH CÔNG bằng 2 icon
                if self.check_login_success_with_icons():
                    print(f"[SUCCESS][Scanner] Đăng nhập thành công bằng cookies: {username}")
                    return True
                else:
                    print(f"[INFO][Scanner] Session hết hạn, cần đăng nhập lại: {username}")
            
            # ⭐ ĐĂNG NHẬP BẰNG USERNAME/PASSWORD
            try:
                # Tìm và nhập username
                username_input = self.driver.find_element(By.NAME, "username")
                username_input.clear()
                username_input.send_keys(username)
                time.sleep(0.3)
                
                # Tìm và nhập password
                password_input = self.driver.find_element(By.NAME, "password")
                password_input.clear()
                password_input.send_keys(password)
                time.sleep(0.3)
                
                # Submit form
                from selenium.webdriver.common.keys import Keys
                password_input.send_keys(Keys.ENTER)
                
                print(f"[INFO][Scanner] Đã gửi thông tin đăng nhập cho {username}")
                
                # ⭐ CHỜ VÀ KIỂM TRA KẾT QUẢ
                max_wait = 10
                start_time = time.time()
                
                while time.time() - start_time < max_wait:
                    time.sleep(1)
                    
                    # Kiểm tra đăng nhập thành công
                    if self.check_login_success_with_icons():
                        print(f"[SUCCESS][Scanner] Đăng nhập thành công: {username}")
                        self.save_cookies_from_account_management(username)
                        return True
                    
                    # Kiểm tra các trường hợp đặc biệt (có thể thêm sau)
                    if "login" not in self.driver.current_url.lower():
                        break
                
                print(f"[ERROR][Scanner] Không thể đăng nhập: {username}")
                return False
                
            except Exception as e:
                print(f"[ERROR][Scanner] Lỗi khi nhập thông tin đăng nhập: {e}")
                return False
                
        except Exception as e:
            print(f"[ERROR][Scanner] Lỗi đăng nhập: {e}")
            return False
    
    def login_with_session(self, account_data):
        """⭐ WRAPPER cho login_with_account_management_logic"""
        return self.login_with_account_management_logic(account_data)
    
    def load_cookies_from_account_management(self, username):
        """⭐ LOAD COOKIES theo logic Account Management"""
        try:
            sessions_folder = os.path.join("sessions", username)
            cookies_file = os.path.join(sessions_folder, "cookies.json")
            
            if os.path.exists(cookies_file):
                with open(cookies_file, "r", encoding="utf-8") as f:
                    cookies = json.load(f)
                
                for cookie in cookies:
                    try:
                        self.driver.add_cookie(cookie)
                    except Exception as e:
                        continue
                
                print(f"[SUCCESS][Scanner] Đã load cookies cho {username}")
                return True
            else:
                print(f"[INFO][Scanner] Không tìm thấy cookies cho {username}")
                return False
                
        except Exception as e:
            print(f"[ERROR][Scanner] Lỗi load cookies: {e}")
            return False
    
    def save_cookies_from_account_management(self, username):
        """⭐ SAVE COOKIES theo logic Account Management"""
        try:
            sessions_folder = os.path.join("sessions", username)
            os.makedirs(sessions_folder, exist_ok=True)
            cookies_file = os.path.join(sessions_folder, "cookies.json")
            
            cookies = self.driver.get_cookies()
            with open(cookies_file, "w", encoding="utf-8") as f:
                json.dump(cookies, f, indent=2)
            
            print(f"[SUCCESS][Scanner] Đã lưu cookies cho {username}")
            return True
            
        except Exception as e:
            print(f"[ERROR][Scanner] Lỗi lưu cookies: {e}")
            return False
    
    def check_login_success_with_icons(self):
        """⭐ KIỂM TRA ĐĂNG NHẬP THÀNH CÔNG bằng 2 icon Home + Explore"""
        try:
            # Tìm icon Home (ngôi nhà)
            home_icons = self.driver.find_elements(By.XPATH, "//a[@href='/']//svg[@aria-label='Home' or contains(@aria-label, 'Trang chủ')]")
            
            # Tìm icon Explore (la bàn)
            explore_icons = self.driver.find_elements(By.XPATH, "//a[@href='/explore/']//svg[@aria-label='Explore' or contains(@aria-label, 'Khám phá')]")
            
            # Cả 2 icon đều phải có mặt
            if len(home_icons) > 0 and len(explore_icons) > 0:
                print(f"[SUCCESS][Scanner] Tìm thấy cả 2 icon Home + Explore - Đăng nhập thành công!")
                return True
            else:
                print(f"[INFO][Scanner] Không tìm thấy đủ 2 icon - Home: {len(home_icons)}, Explore: {len(explore_icons)}")
                return False
                
        except Exception as e:
            print(f"[ERROR][Scanner] Lỗi check icons: {e}")
            return False
    
    def scan_followers(self, target_username, max_count=50):
        """Quét danh sách followers của một tài khoản"""
        try:
            # Truy cập trang profile
            self.driver.get(f"https://www.instagram.com/{target_username}/")
            time.sleep(3)
            
            # Kiểm tra private account
            try:
                private_text = self.driver.find_element(By.XPATH, "//*[contains(text(), 'This account is private')]")
                if private_text:
                    self.logger.warning(f"Tài khoản {target_username} là private, không thể quét")
                    return []
            except:
                pass
            
            # Click vào followers
            followers_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/followers/')]"))
            )
            followers_link.click()
            time.sleep(3)
            
            # Scroll và thu thập followers
            followers = []
            seen_usernames = set()
            scroll_count = 0
            max_scrolls = min(max_count // 12, 15)  # Mỗi lần scroll ~12 users
            
            while len(followers) < max_count and scroll_count < max_scrolls:
                # Tìm tất cả username trong modal
                user_elements = self.driver.find_elements(By.XPATH, "//div[@role='dialog']//a[contains(@href, '/') and not(contains(@href, '/p/')) and not(contains(@href, '/explore/')) and not(contains(@href, '/reel/'))]")
                
                for element in user_elements:
                    try:
                        href = element.get_attribute('href')
                        if href and href.startswith('https://www.instagram.com/'):
                            username = href.split('/')[-1] if href.endswith('/') else href.split('/')[-1]
                            
                            if username and username not in seen_usernames and len(username) > 0 and not username.startswith('#'):
                                seen_usernames.add(username)
                                
                                # Lấy display name
                                display_name = username
                                try:
                                    display_name_element = element.find_element(By.XPATH, ".//span")
                                    display_name = display_name_element.text if display_name_element.text else username
                                except:
                                    pass
                                
                                followers.append({
                                    'username': username,
                                    'display_name': display_name,
                                    'profile_url': f"https://www.instagram.com/{username}/",
                                    'source': f"followers of {target_username}",
                                    'scan_time': datetime.now().strftime("%H:%M:%S")
                                })
                                
                                if len(followers) >= max_count:
                                    break
                    except Exception as e:
                        continue
                
                # Scroll xuống để load thêm
                try:
                    dialog = self.driver.find_element(By.XPATH, "//div[@role='dialog']")
                    scrollable_div = dialog.find_element(By.XPATH, ".//div[contains(@style, 'overflow') or contains(@style, 'scroll')]")
                    self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_div)
                except:
                    # Fallback scroll method
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                
                time.sleep(2)
                scroll_count += 1
            
            self.logger.info(f"Quét được {len(followers)} followers từ {target_username}")
            return followers
            
        except TimeoutException:
            self.logger.warning(f"Timeout khi quét followers của {target_username}")
            return []
        except Exception as e:
            self.logger.error(f"Lỗi quét followers: {e}")
            return []
    
    def scan_following(self, target_username, max_count=50):
        """Quét danh sách following của một tài khoản"""
        try:
            # Truy cập trang profile
            self.driver.get(f"https://www.instagram.com/{target_username}/")
            time.sleep(3)
            
            # Click vào following
            following_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/following/')]"))
            )
            following_link.click()
            time.sleep(3)
            
            # Tương tự như scan_followers
            following = []
            seen_usernames = set()
            scroll_count = 0
            max_scrolls = min(max_count // 12, 15)
            
            while len(following) < max_count and scroll_count < max_scrolls:
                user_elements = self.driver.find_elements(By.XPATH, "//div[@role='dialog']//a[contains(@href, '/') and not(contains(@href, '/p/')) and not(contains(@href, '/explore/')) and not(contains(@href, '/reel/'))]")
                
                for element in user_elements:
                    try:
                        href = element.get_attribute('href')
                        if href and href.startswith('https://www.instagram.com/'):
                            username = href.split('/')[-1] if href.endswith('/') else href.split('/')[-1]
                            
                            if username and username not in seen_usernames and len(username) > 0 and not username.startswith('#'):
                                seen_usernames.add(username)
                                
                                display_name = username
                                try:
                                    display_name_element = element.find_element(By.XPATH, ".//span")
                                    display_name = display_name_element.text if display_name_element.text else username
                                except:
                                    pass
                                
                                following.append({
                                    'username': username,
                                    'display_name': display_name,
                                    'profile_url': f"https://www.instagram.com/{username}/",
                                    'source': f"following of {target_username}",
                                    'scan_time': datetime.now().strftime("%H:%M:%S")
                                })
                                
                                if len(following) >= max_count:
                                    break
                    except Exception as e:
                        continue
                
                try:
                    dialog = self.driver.find_element(By.XPATH, "//div[@role='dialog']")
                    scrollable_div = dialog.find_element(By.XPATH, ".//div[contains(@style, 'overflow') or contains(@style, 'scroll')]")
                    self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_div)
                except:
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                
                time.sleep(2)
                scroll_count += 1
            
            self.logger.info(f"Quét được {len(following)} following từ {target_username}")
            return following
            
        except Exception as e:
            self.logger.error(f"Lỗi quét following: {e}")
            return []
    
    def search_users_by_keyword(self, keyword, max_count=30):
        """Tìm kiếm users theo từ khóa"""
        try:
            # Truy cập trang search
            search_url = f"https://www.instagram.com/explore/search/keyword/?q={keyword.replace(' ', '%20')}"
            self.driver.get(search_url)
            time.sleep(3)
            
            # Tìm tất cả kết quả
            users = []
            seen_usernames = set()
            
            # Scroll để load thêm kết quả
            for scroll_attempt in range(5):
                user_elements = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/') and not(contains(@href, '/explore/')) and not(contains(@href, '/p/')) and not(contains(@href, '/reel/'))]")
                
                for element in user_elements:
                    try:
                        href = element.get_attribute('href')
                        if href and href.startswith('https://www.instagram.com/'):
                            username = href.split('/')[-1] if href.endswith('/') else href.split('/')[-1]
                            
                            if username and username not in seen_usernames and len(username) > 0 and not username.startswith('#'):
                                seen_usernames.add(username)
                                
                                users.append({
                                    'username': username,
                                    'display_name': username,
                                    'profile_url': f"https://www.instagram.com/{username}/",
                                    'source': f"search: {keyword}",
                                    'scan_time': datetime.now().strftime("%H:%M:%S")
                                })
                                
                                if len(users) >= max_count:
                                    break
                    except Exception as e:
                        continue
                
                if len(users) >= max_count:
                    break
                    
                # Scroll xuống
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
            
            self.logger.info(f"Tìm được {len(users)} users với keyword: {keyword}")
            return users
            
        except Exception as e:
            self.logger.error(f"Lỗi search users: {e}")
            return []
    
    def scan_post_likers(self, post_url, max_count=50):
        """Quét người like một bài viết"""
        try:
            self.driver.get(post_url)
            time.sleep(3)
            
            # Tìm và click vào số lượt like
            like_elements = self.driver.find_elements(By.XPATH, "//span[contains(text(), 'likes') or contains(text(), 'like')]")
            
            if not like_elements:
                self.logger.warning(f"Không tìm thấy thông tin like cho bài viết: {post_url}")
                return []
            
            like_elements[0].click()
            time.sleep(3)
            
            # Thu thập likers
            likers = []
            seen_usernames = set()
            scroll_count = 0
            max_scrolls = min(max_count // 12, 15)
            
            while len(likers) < max_count and scroll_count < max_scrolls:
                user_elements = self.driver.find_elements(By.XPATH, "//div[@role='dialog']//a[contains(@href, '/') and not(contains(@href, '/p/')) and not(contains(@href, '/explore/')) and not(contains(@href, '/reel/'))]")
                
                for element in user_elements:
                    try:
                        href = element.get_attribute('href')
                        if href and href.startswith('https://www.instagram.com/'):
                            username = href.split('/')[-1] if href.endswith('/') else href.split('/')[-1]
                            
                            if username and username not in seen_usernames and len(username) > 0 and not username.startswith('#'):
                                seen_usernames.add(username)
                                
                                likers.append({
                                    'username': username,
                                    'display_name': username,
                                    'profile_url': f"https://www.instagram.com/{username}/",
                                    'source': f"likers of post",
                                    'scan_time': datetime.now().strftime("%H:%M:%S")
                                })
                                
                                if len(likers) >= max_count:
                                    break
                    except Exception as e:
                        continue
                
                try:
                    dialog = self.driver.find_element(By.XPATH, "//div[@role='dialog']")
                    scrollable_div = dialog.find_element(By.XPATH, ".//div[contains(@style, 'overflow') or contains(@style, 'scroll')]")
                    self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_div)
                except:
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                
                time.sleep(2)
                scroll_count += 1
            
            self.logger.info(f"Quét được {len(likers)} likers từ bài viết")
            return likers
            
        except Exception as e:
            self.logger.error(f"Lỗi quét post likers: {e}")
            return []
    
    def close(self):
        """Đóng driver"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None

class DataScannerTab(QWidget):
    def __init__(self, account_management_tab=None):
        super().__init__()
        self.config_data = [{} for _ in range(4)]  # Lưu cấu hình từng mục
        self.username_lists = [[], [], [], []]    # Lưu danh sách username từng mục
        self.scan_running = False
        self.scan_timer = None
        self.account_data = []
        self.result_data = []
        self.accounts = []  # Lưu toàn bộ tài khoản
        
        # ⭐ KHỞI TẠO INSTAGRAM SCANNER THẬT với reference Account Management
        self.account_management_tab = account_management_tab
        self.instagram_scanner = InstagramScanner(account_management_tab)
        self.current_account_index = 0
        self.current_scanner_driver = None
        
        self.init_ui()
        
    def init_ui(self):
        # ⭐ BỐ CỤC 4 PHẦN THEO YÊU CẦU: 10% - 20% - 70%
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        main_layout.setSpacing(0)  # Remove spacing

        # ===== 1. MENU THANH BÊN TRÁI (10%) =====
        sidebar_widget = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        sidebar_layout.setSpacing(10)

        # ⭐ CẤU HÌNH MENU - STYLE ĐỒNG BỘ
        config_label = QLabel("Loại quét:")
        config_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        sidebar_layout.addWidget(config_label)
        
        # Menu buttons với style đồng bộ
        self.menu_buttons = []
        menu_titles = [
            "Quét Tài Khoản Theo Dõi",
            "Quét Tài Khoản Theo Từ Khóa", 
            "Quét Bài Viết Của Tài Khoản",
            "Quét Bài Viết Theo Từ Khóa"
        ]
        
        for i, title in enumerate(menu_titles):
            btn = QPushButton(title)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, idx=i: self.switch_config(idx))
            # ⭐ STYLE ĐỒNG BỘ với Account Management buttons
            btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 8px 12px;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    background-color: #f5f5f5;
                    font-size: 11px;
                    min-height: 32px;
                    font-weight: normal;
                }
                QPushButton:checked {
                    background-color: #e3f2fd;
                    border-color: #2196F3;
                    color: #1976D2;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #eeeeee;
                }
            """)
            self.menu_buttons.append(btn)
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()  # Push buttons to top

        # ===== 2. PHẦN CẤU HÌNH Ở GIỮA (20%) - COMPACT =====
        config_widget = QWidget()
        config_layout = QVBoxLayout(config_widget)
        config_layout.setContentsMargins(4, 4, 4, 4)  # Margins rất nhỏ
        config_layout.setSpacing(2)  # Spacing rất nhỏ
        config_widget.setStyleSheet("""
            QWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: #fafafa;
            }
        """)
        
        # ⭐ STACKED WIDGET CHO CẤU HÌNH - COMPACT
        self.stacked_config = QStackedWidget()
        # Không ghi đè config_data và username_lists đã khởi tạo trong __init__
        
        for i in range(4):
            widget = self.create_config_widget(i)
            self.stacked_config.addWidget(widget)
        
        config_layout.addWidget(self.stacked_config)

        # ===== 3. BẢNG DỮ LIỆU TÀI KHOẢN (70%) CHIA LÀM 2 PHẦN =====
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # ===== TOOLBAR FRAME - ĐỒNG BỘ VỚI ACCOUNT MANAGEMENT =====
        toolbar_frame = QFrame()
        toolbar_frame.setStyleSheet("QFrame { padding-top: 6px; padding-bottom: 6px; }")
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setSpacing(8)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)

        # ⭐ CATEGORY COMBO - CHUẨN WINDOWS STYLE
        self.category_combo = QComboBox()
        self.category_combo.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))  # Font chuẩn Windows
        self.category_combo.addItem("Tất cả")
        self.load_folder_list_to_combo()
        self.category_combo.currentIndexChanged.connect(self.on_folder_changed)
        self.category_combo.setFixedHeight(27)                                  # Chiều cao chuẩn Windows
        self.category_combo.setMinimumWidth(150)                                # Độ rộng tối thiểu
        # Không dùng stylesheet để giữ giao diện mặc định Windows
        toolbar_layout.addWidget(self.category_combo)

        # ⭐ BUTTONS - STYLE ĐỒNG BỘ VỚI ACCOUNT MANAGEMENT
        self.btn_load = QPushButton("LOAD")
        self.btn_start = QPushButton("START")
        self.btn_stop = QPushButton("STOP")
        
        # ⭐ STYLE BUTTONS ĐỒNG BỘ
        button_style = """
        QPushButton {
                min-height: 30px;
                min-width: 60px;
                padding: 4px 8px;
                border: 1px solid #ccc;
            border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }
        """
        
        self.btn_load.setStyleSheet(button_style + """
            QPushButton { background-color: #fdd835; color: #333; }
            QPushButton:hover { background-color: #fbc02d; }
        """)
        self.btn_start.setStyleSheet(button_style + """
            QPushButton { background-color: #4caf50; color: white; }
            QPushButton:hover { background-color: #45a049; }
        """)
        self.btn_stop.setStyleSheet(button_style + """
            QPushButton { background-color: #f44336; color: white; }
            QPushButton:hover { background-color: #da190b; }
        """)
        
        self.btn_load.clicked.connect(self.load_accounts)
        self.btn_start.clicked.connect(self.start_scan)
        self.btn_stop.clicked.connect(self.stop_scan)
        
        toolbar_layout.addWidget(self.btn_load)
        toolbar_layout.addWidget(self.btn_start)
        toolbar_layout.addWidget(self.btn_stop)

        # ⭐ ĐẨY CÁC WIDGET SANG PHẢI
        toolbar_layout.addStretch(1)
        
        # ⭐ EXPORT/CLEAR BUTTONS - STYLE ĐỒNG BỘ
        self.btn_export = QPushButton("Export")
        self.btn_clear = QPushButton("Clear")
        
        self.btn_export.setStyleSheet(button_style + """
            QPushButton { background-color: #2196F3; color: white; }
            QPushButton:hover { background-color: #1976D2; }
        """)
        self.btn_clear.setStyleSheet(button_style + """
            QPushButton { background-color: #FF9800; color: white; }
            QPushButton:hover { background-color: #F57C00; }
        """)
        
        self.btn_export.clicked.connect(self.export_results)
        self.btn_clear.clicked.connect(self.clear_results)
        
        toolbar_layout.addWidget(self.btn_export)
        toolbar_layout.addWidget(self.btn_clear)

        right_layout.addWidget(toolbar_frame)

        # ===== 3.1 PHẦN TRÊN: BẢNG DỮ LIỆU TÀI KHOẢN QUÉT =====
        account_frame = QFrame()
        account_frame.setStyleSheet("QFrame { border: 1px solid #ddd; border-radius: 4px; background-color: #fafafa; }")
        account_layout = QVBoxLayout(account_frame)
        account_layout.setContentsMargins(8, 8, 8, 8)
        account_layout.setSpacing(4)
        
        # Label cho bảng tài khoản
        account_label = QLabel("Danh sách tài khoản")
        account_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        account_label.setStyleSheet("color: #333; padding: 4px;")
        account_layout.addWidget(account_label)

        # ⭐ PROGRESS BAR - TỐI ƯU VỚI STYLE ĐỒNG BỘ
        self.overall_progress = QProgressBar()
        self.overall_progress.setVisible(False)
        self.overall_progress.setFixedHeight(20)
        self.overall_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
            border-radius: 4px;
                text-align: center;
                font-size: 12px;
                background-color: #f0f0f0;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            border-radius: 4px;
            }
        """)
        account_layout.addWidget(self.overall_progress)

        # ⭐ STATS LABEL CHO TÀI KHOẢN
        self.account_stats_label = QLabel("Tổng số tài khoản quét được: 0")
        self.account_stats_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.account_stats_label.setStyleSheet("font-size: 12px; font-weight: bold; padding: 4px; color: #666;")
        account_layout.addWidget(self.account_stats_label)

        # ===== ACCOUNT TABLE - ĐỒNG BỘ VỚI ACCOUNT MANAGEMENT =====
        self.account_table = QTableWidget()
        self.account_table.setColumnCount(8)
        self.account_table.setHorizontalHeaderLabels(["✓", "STT", "Số điện thoại", "Mật khẩu 2FA", "Username", "ID", "Trạng thái quét", "Số lượng quét"])
        
        # ⭐ ĐỒNG BỘ HEADER STYLING VỚI ACCOUNT MANAGEMENT
        header1 = self.account_table.horizontalHeader()
        header1.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.account_table.setColumnWidth(0, 29)
        header1.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.account_table.setColumnWidth(1, 29)
        header1.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.account_table.setColumnWidth(2, 120)  # Giảm để tiết kiệm không gian
        header1.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.account_table.setColumnWidth(3, 100)
        header1.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        
        self.account_table.verticalHeader().setDefaultSectionSize(32)  # Giảm chiều cao row
        self.account_table.horizontalHeader().setFixedHeight(32)
        self.account_table.verticalHeader().setVisible(False)
        header1.setStretchLastSection(True)
        self.account_table.horizontalHeader().setDefaultAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        
        # ⭐ DELEGATE VÀ BEHAVIOR - ĐỒNG BỘ VỚI ACCOUNT MANAGEMENT
        self.checkbox_delegate = CheckboxDelegate(self)
        self.account_table.setItemDelegateForColumn(0, self.checkbox_delegate)
        self.checkbox_delegate.checkbox_clicked.connect(self.on_checkbox_clicked)
        self.account_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        # 🔒 LOCK TABLE - Chỉ xem, không cho phép chỉnh sửa
        self.account_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        account_layout.addWidget(self.account_table)

        # ===== 3.2 PHẦN DƯỚI: BẢNG DỮ LIỆU KẾT QUẢ QUÉT =====
        result_frame = QFrame()
        result_frame.setStyleSheet("QFrame { border: 1px solid #ddd; border-radius: 4px; background-color: #fafafa; }")
        result_layout = QVBoxLayout(result_frame)
        result_layout.setContentsMargins(8, 8, 8, 8)
        result_layout.setSpacing(4)
        
        # Label cho bảng kết quả (sẽ được cập nhật trong update_result_table_header)
        self.result_label = QLabel("Thông Tin Tài Khoản Quét Được")
        self.result_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.result_label.setStyleSheet("color: #333; padding: 4px;")
        result_layout.addWidget(self.result_label)
        
        # ⭐ STATS LABEL - ĐỒNG BỘ VỚI ACCOUNT MANAGEMENT
        self.stats_label = QLabel("Tổng số username quét được: 0")
        self.stats_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.stats_label.setStyleSheet("font-size: 12px; font-weight: bold; padding: 4px; color: #666;")
        result_layout.addWidget(self.stats_label)
        


        self.result_table = QTableWidget()
        self.result_table.setColumnCount(10)  # Tăng số cột cho tab "Quét Bài Viết Theo Từ Khóa"
        self.result_table.setHorizontalHeaderLabels(["✓", "STT", "Tài khoản quét", "Từ khóa tìm", "Tên đăng bài", "Mã bài viết", "Link bài viết", "Nội dung bài", "Media link", "Loại bài"])
        
        # ⭐ ĐỒNG BỘ RESULT TABLE STYLING VỚI ACCOUNT MANAGEMENT  
        header2 = self.result_table.horizontalHeader()
        header2.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.result_table.setColumnWidth(0, 29)
        header2.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.result_table.setColumnWidth(1, 29)
        # Cấu hình width cho các cột theo tab "Quét Bài Viết Theo Từ Khóa"
        for i in range(2, 9):
            header2.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
            self.result_table.setColumnWidth(i, 100)
        header2.setSectionResizeMode(9, QHeaderView.ResizeMode.Stretch)
        
        self.result_table.verticalHeader().setDefaultSectionSize(32)
        self.result_table.horizontalHeader().setFixedHeight(32)
        self.result_table.verticalHeader().setVisible(False)
        header2.setStretchLastSection(True)
        self.result_table.horizontalHeader().setDefaultAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        
        # ⭐ CONTEXT MENU - ĐỒNG BỘ VỚI ACCOUNT MANAGEMENT
        self.result_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.result_table.customContextMenuRequested.connect(self.show_context_menu)
        # 🔒 LOCK TABLE - Chỉ xem, không cho phép chỉnh sửa
        self.result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        result_layout.addWidget(self.result_table)

        # ===== THÊM CÁC PHẦN VÀO RIGHT PANEL =====
        right_layout.addWidget(account_frame, stretch=1)  # Bảng tài khoản trên
        right_layout.addWidget(result_frame, stretch=1)   # Bảng kết quả dưới

        # ⭐ SET MINIMUM WIDTH CHO RESPONSIVE DESIGN
        sidebar_widget.setMinimumWidth(120)   # Minimum width cho menu
        sidebar_widget.setMaximumWidth(200)   # Maximum width cho menu
        config_widget.setMinimumWidth(180)    # Minimum width cho cấu hình
        config_widget.setMaximumWidth(350)    # Maximum width cho cấu hình
        right_panel.setMinimumWidth(400)      # Minimum width cho bảng dữ liệu

        # ⭐ BỐ CỤC CHÍNH: CO GIÃN ĐỀU KHI RESIZE
        main_layout.addWidget(sidebar_widget, stretch=1)     # Tỷ lệ co giãn 1
        main_layout.addWidget(config_widget, stretch=2)      # Tỷ lệ co giãn 2  
        main_layout.addWidget(right_panel, stretch=5)        # Tỷ lệ co giãn 5 (tổng 1:2:5)

        # ===== KHỞI TẠO =====
        self.menu_buttons[0].setChecked(True)  # Chọn mặc định
        self.stacked_config.setCurrentIndex(0)
        self.update_result_table_header(0)  # Khởi tạo header mặc định
        self.load_accounts()
        
    def create_config_widget(self, idx):
        # ⭐ TẠO WIDGET CẤU HÌNH COMPACT
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(2)  # Spacing rất nhỏ
        layout.setContentsMargins(4, 4, 4, 4)  # Margins rất nhỏ
        
        titles = [
            "Cấu Hình Quét Tài Khoản Theo Dõi",
            "Cấu Hình Quét User Theo Từ Khóa", 
            "Cấu Hình Quét Bài Viết Theo Tài Khoản",
            "Cấu Hình Quét Bài Viết Theo Từ Khóa"
        ]
        title = QLabel(titles[idx])
        title.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))  # Rất nhỏ để compact
        title.setWordWrap(True)
        title.setStyleSheet("color: #333; padding: 1px;")
        layout.addWidget(title)
        
        # ⭐ HELPER FUNCTION CHO MINI SPINBOX - KÍCH THƯỚC CHUẨN WINDOWS
        def create_spinbox(min_val=1, max_val=100, width=54):
            spin = QSpinBox()
            spin.setFont(QFont("Segoe UI", 9))       # Cỡ chữ nhỏ vừa đẹp, rõ nét
            spin.setFixedSize(54, 26)                # Kích thước siêu gọn như hình mẫu
            spin.setRange(min_val, max_val)
            # ⭐ STYLE: Gọn gàng chuẩn Windows
            spin.setStyleSheet("""
                QSpinBox {
                    font-size: 9px;
                    font-weight: normal;
                    border: 1px solid #ccc;
                    border-radius: 3px;
                    background-color: white;
                    padding: 2px 4px;
                    margin: 0px;
                }
                QSpinBox::up-button, QSpinBox::down-button {
                    width: 14px;
                    height: 12px;
                    border: none;
                    background-color: #f0f0f0;
                }
                QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                    background-color: #e0e0e0;
                }
                QSpinBox::up-arrow, QSpinBox::down-arrow {
                    width: 6px;
                    height: 6px;
                }
            """)
            return spin
        
        # ⭐ HELPER FUNCTION CHO COMPACT LABEL
        def create_label(text):
            label = QLabel(text)
            label.setFont(QFont("Segoe UI", 7))  # Font rất nhỏ
            label.setWordWrap(True)
            return label
        
        # ⭐ CẤU HÌNH KHÁC NHAU CHO TỪNG TAB
        if idx == 1:  # Tab "Quét Tài Khoản Theo Từ Khóa"
            # Số luồng - CHUẨN WINDOWS với giá trị mặc định khác
            row1 = QHBoxLayout()
            row1.setSpacing(2)
            row1.addWidget(create_label("Số luồng chạy đồng thời"))
            spin_thread = create_spinbox(1, 10)
            spin_thread.setValue(3)  # Mặc định 3 như hình
            row1.addWidget(spin_thread)
            row1.addWidget(create_label("luồng"))
            row1.addStretch()
            layout.addLayout(row1)
            
            # Chuyển tài khoản nếu lỗi
            row2 = QHBoxLayout() 
            row2.setSpacing(2)
            row2.addWidget(create_label("Chuyển tài khoản nếu lỗi liên tiếp"))
            spin_error = create_spinbox(1, 100)
            spin_error.setValue(1)  # Mặc định 1
            row2.addWidget(spin_error)
            row2.addWidget(create_label("lần"))
            row2.addStretch()
            layout.addLayout(row2)
            
            # Khoảng cách quét
            row3 = QHBoxLayout()
            row3.setSpacing(2)
            row3.addWidget(create_label("Khoảng cách 2 lần quét"))
            spin_delay = create_spinbox(1, 3600)
            spin_delay.setValue(1)  # Mặc định 1
            row3.addWidget(spin_delay)
            row3.addWidget(create_label("giây"))
            row3.addStretch()
            layout.addLayout(row3)
            
            # Mỗi tài khoản quét tối đa
            row4 = QHBoxLayout()
            row4.setSpacing(2)
            row4.addWidget(create_label("Mỗi tài khoản quét tối đa"))
            spin_per_account = create_spinbox(1, 1000)
            spin_per_account.setValue(1)  # Mặc định 1
            row4.addWidget(spin_per_account)
            row4.addWidget(create_label("từ khóa"))
            row4.addStretch()
            layout.addLayout(row4)
            
            # Mỗi từ khóa quét tối đa
            row5 = QHBoxLayout()
            row5.setSpacing(2)
            row5.addWidget(create_label("Mỗi từ khóa quét tối đa 50 user"))
            spin_per_keyword = create_spinbox(1, 1000)
            spin_per_keyword.setValue(50)  # Mặc định 50
            row5.addWidget(spin_per_keyword)
            row5.addWidget(create_label("user"))
            row5.addStretch()
            layout.addLayout(row5)
            
            # Text area lớn thay vì radio buttons cho tab này
            keyword_area = QTextEdit()
            keyword_area.setMaximumHeight(80)  # Chiều cao vừa phải
            keyword_area.setPlaceholderText("thời trang")  # Placeholder như hình
            keyword_area.setStyleSheet("""
                QTextEdit {
                    font-size: 8px;
                    border: 1px solid #ccc;
                    border-radius: 3px;
                    padding: 3px;
                    background-color: white;
                }
            """)
            layout.addWidget(keyword_area)
    
            # Lưu references cho tab này
            spin_user_min = spin_per_account  # Mapping
            spin_user_max = spin_per_keyword  # Mapping
            spin_uname_min = spin_delay  # Mapping
            spin_uname_max = spin_thread  # Mapping
            spin_min = spin_delay
            spin_max = spin_delay
            radio1 = None
            radio2 = None
            
        elif idx == 2:  # Tab "Quét Bài Viết Theo Tài Khoản"
            # Số luồng
            row1 = QHBoxLayout()
            row1.setSpacing(2)
            row1.addWidget(create_label("Số luồng chạy đồng thời"))
            spin_thread = create_spinbox(1, 10)
            spin_thread.setValue(1)  # Mặc định 1
            row1.addWidget(spin_thread)
            row1.addWidget(create_label("luồng"))
            row1.addStretch()
            layout.addLayout(row1)

            # Chuyển tài khoản nếu lỗi
            row2 = QHBoxLayout()
            row2.setSpacing(2)
            row2.addWidget(create_label("Chuyển tài khoản nếu lỗi liên tiếp"))
            spin_error = create_spinbox(1, 100)
            spin_error.setValue(1)  # Mặc định 1
            row2.addWidget(spin_error)
            row2.addWidget(create_label("lần"))
            row2.addStretch()
            layout.addLayout(row2)

            # Khoảng cách quét
            row3 = QHBoxLayout()
            row3.setSpacing(2)
            row3.addWidget(create_label("Khoảng cách 2 lần quét"))
            spin_min = create_spinbox(1, 3600)
            spin_min.setValue(1)  # Mặc định 1
            spin_max = create_spinbox(1, 3600)
            spin_max.setValue(1)  # Mặc định 1
            row3.addWidget(spin_min)
            row3.addWidget(create_label("-"))
            row3.addWidget(spin_max)
            row3.addWidget(create_label("giây"))
            row3.addStretch()
            layout.addLayout(row3)

            # Mỗi tài khoản quét tối đa
            row4 = QHBoxLayout()
            row4.setSpacing(2)
            row4.addWidget(create_label("Mỗi tài khoản quét tối đa (username)"))
            spin_user_min = create_spinbox(1, 1000)
            spin_user_min.setValue(1)  # Mặc định 1
            spin_user_max = create_spinbox(1, 1000)
            spin_user_max.setValue(1)  # Mặc định 1
            row4.addWidget(spin_user_min)
            row4.addWidget(create_label("-"))
            row4.addWidget(spin_user_max)
            row4.addStretch()
            layout.addLayout(row4)

            # Mỗi username quét tối đa bài viết
            row5 = QHBoxLayout()
            row5.setSpacing(2)
            row5.addWidget(create_label("Mỗi username quét tối đa"))
            spin_uname_min = create_spinbox(1, 1000)
            spin_uname_min.setValue(1)  # Mặc định 1
            spin_uname_max = create_spinbox(1, 1000)  
            spin_uname_max.setValue(1)  # Mặc định 1
            row5.addWidget(spin_uname_min)
            row5.addWidget(create_label("-"))
            row5.addWidget(spin_uname_max)
            row5.addWidget(create_label("bài viết"))
            row5.addStretch()
            layout.addLayout(row5)
            
        elif idx == 3:  # Tab "Quét Bài Viết Theo Từ Khóa"
            # Số luồng
            row1 = QHBoxLayout()
            row1.setSpacing(2)
            row1.addWidget(create_label("Số luồng chạy đồng thời"))
            spin_thread = create_spinbox(1, 10)
            spin_thread.setValue(2)  # Mặc định 2 như hình
            row1.addWidget(spin_thread)
            row1.addWidget(create_label("luồng"))
            row1.addStretch()
            layout.addLayout(row1)
            
            # Chuyển tài khoản nếu lỗi
            row2 = QHBoxLayout() 
            row2.setSpacing(2)
            row2.addWidget(create_label("Chuyển tài khoản nếu lỗi liên tiếp"))
            spin_error = create_spinbox(1, 100)
            spin_error.setValue(1)  # Mặc định 1
            row2.addWidget(spin_error)
            row2.addWidget(create_label("lần"))
            row2.addStretch()
            layout.addLayout(row2)

            # Khoảng cách quét
            row3 = QHBoxLayout()
            row3.setSpacing(2)
            row3.addWidget(create_label("Khoảng cách 2 lần quét"))
            spin_min = create_spinbox(1, 3600)
            spin_min.setValue(5)  # Mặc định 5
            spin_max = create_spinbox(1, 3600)
            spin_max.setValue(10)  # Mặc định 10
            row3.addWidget(spin_min)
            row3.addWidget(create_label("-"))
            row3.addWidget(spin_max)
            row3.addWidget(create_label("giây"))
            row3.addStretch()
            layout.addLayout(row3)
            
            # Mỗi tài khoản quét tối đa từ khóa
            row4 = QHBoxLayout()
            row4.setSpacing(2)
            row4.addWidget(create_label("Mỗi tài khoản quét tối đa"))
            spin_user_min = create_spinbox(1, 1000)
            spin_user_min.setValue(1)  # Mặc định 1
            spin_user_max = create_spinbox(1, 1000)
            spin_user_max.setValue(1)  # Mặc định 1
            row4.addWidget(spin_user_min)
            row4.addWidget(create_label("-"))
            row4.addWidget(spin_user_max)
            row4.addWidget(create_label("từ khóa"))
            row4.addStretch()
            layout.addLayout(row4)
            
            # Mỗi từ khóa quét tối đa bài viết
            row5 = QHBoxLayout()
            row5.setSpacing(2)
            row5.addWidget(create_label("Mỗi từ khóa quét tối đa"))
            spin_uname_min = create_spinbox(1, 1000)
            spin_uname_min.setValue(50)  # Mặc định 50
            spin_uname_max = create_spinbox(1, 1000)  
            spin_uname_max.setValue(100)  # Mặc định 100
            row5.addWidget(spin_uname_min)
            row5.addWidget(create_label("-"))
            row5.addWidget(spin_uname_max)
            row5.addWidget(create_label("bài viết"))
            row5.addStretch()
            layout.addLayout(row5)
            
            # Checkbox đặc biệt cho tab này
            keyword_search_checkbox = QCheckBox("Quét theo danh sách từ khóa")
            keyword_search_checkbox.setFont(QFont("Segoe UI", 6))
            keyword_search_checkbox.setStyleSheet("""
                QCheckBox { 
                    spacing: 2px; 
                    color: #333;
                    border: 1px solid #ccc;
                    border-radius: 3px;
                    padding: 2px;
                    background-color: #e3f2fd;
                }
            """)
            keyword_search_checkbox.setChecked(True)  # Mặc định tick như hình
            layout.addWidget(keyword_search_checkbox)
            
            # Text area lớn cho từ khóa với placeholder 2 dòng
            keyword_area = QTextEdit()
            keyword_area.setMaximumHeight(80)
            keyword_area.setPlaceholderText("váy\nđầm đẹp")  # 2 dòng như hình
            keyword_area.setStyleSheet("""
                QTextEdit {
                    font-size: 8px;
                    border: 1px solid #ccc;
                    border-radius: 3px;
                    padding: 3px;
                    background-color: white;
                }
            """)
            layout.addWidget(keyword_area)
            
            # Set radio1, radio2 = None cho tab này
            radio1 = None
            radio2 = None
            
        else:  # Các tab khác giữ nguyên cấu hình cũ
            # Số luồng - MINI SIZE
            row1 = QHBoxLayout()
            row1.setSpacing(2)
            row1.addWidget(create_label("Số luồng chạy đồng thời"))
            spin_thread = create_spinbox(1, 10)
            row1.addWidget(spin_thread)
            row1.addWidget(create_label("luồng"))
            row1.addStretch()
            layout.addLayout(row1)
            
            # Chuyển tài khoản nếu lỗi
            row2 = QHBoxLayout() 
            row2.setSpacing(2)
            row2.addWidget(create_label("Chuyển tài khoản nếu lỗi liên tiếp"))
            spin_error = create_spinbox(1, 100)
            row2.addWidget(spin_error)
            row2.addWidget(create_label("lần"))
            row2.addStretch()
            layout.addLayout(row2)
            
            # Khoảng cách quét
            row3 = QHBoxLayout()
            row3.setSpacing(2)
            row3.addWidget(create_label("Khoảng cách hai lần quét (giây)"))
            spin_min = create_spinbox(1, 3600)
            spin_max = create_spinbox(1, 3600)
            row3.addWidget(spin_min)
            row3.addWidget(create_label("-"))
            row3.addWidget(spin_max)
            row3.addStretch()
            layout.addLayout(row3)
            
            # Số lượng username
            row4 = QHBoxLayout()
            row4.setSpacing(2)
            row4.addWidget(create_label("Mỗi tài khoản quét tối đa (username)"))
            spin_user_min = create_spinbox(1, 1000)
            spin_user_max = create_spinbox(1, 1000)
            row4.addWidget(spin_user_min)
            row4.addWidget(create_label("-"))
            row4.addWidget(spin_user_max)
            row4.addStretch()
            layout.addLayout(row4)
            
            # Số lần quét mỗi username
            row5 = QHBoxLayout()
            row5.setSpacing(2)
            row5.addWidget(create_label("Mỗi username quét tối đa"))
            spin_uname_min = create_spinbox(1, 1000)
            spin_uname_max = create_spinbox(1, 1000)
            row5.addWidget(spin_uname_min)
            row5.addWidget(create_label("-"))
            row5.addWidget(spin_uname_max)
            row5.addStretch()
            layout.addLayout(row5)
            
            # ⭐ RADIO GROUP CHO TAB KHÁC (không phải từ khóa và không phải bài viết)
            radio_group = QGroupBox()
            radio_group.setStyleSheet("""
                QGroupBox { 
                    font-size: 6px; 
                    border: 1px solid #ccc;
                    border-radius: 3px;
                    margin-top: 2px;
                    padding: 2px;
                }
            """)
            radio_layout = QVBoxLayout(radio_group)
            radio_layout.setSpacing(1)  # Compact spacing
            radio_layout.setContentsMargins(3, 3, 3, 3)  # Compact margins
            
            radio1 = QRadioButton("Quét người theo dõi của chính tài khoản")
            radio1.setFont(QFont("Segoe UI", 6))  # Rất nhỏ
            radio1.setStyleSheet("QRadioButton { spacing: 2px; color: #333; }")
            radio2 = QRadioButton("Quét theo danh sách username")  # Đổi text để match hình
            radio2.setFont(QFont("Segoe UI", 6))  # Rất nhỏ
            radio2.setStyleSheet("QRadioButton { spacing: 2px; color: #333; }")
            radio2.setChecked(True)  # Mặc định chọn option 2 như hình
            
            radio_layout.addWidget(radio1)
            radio_layout.addWidget(radio2)
            
            # ⭐ THÊM SUB-OPTIONS như trong hình
            sub_radio_group = QWidget()
            sub_radio_layout = QVBoxLayout(sub_radio_group)
            sub_radio_layout.setSpacing(1)
            sub_radio_layout.setContentsMargins(10, 2, 2, 2)  # Indent để hiển thị sub-level
            
            sub_radio1 = QRadioButton("Quét danh sách người theo dõi")
            sub_radio1.setFont(QFont("Segoe UI", 6))
            sub_radio1.setStyleSheet("QRadioButton { spacing: 2px; color: #444; }")
            sub_radio1.setChecked(True)  # Mặc định chọn như hình
            
            sub_radio2 = QRadioButton("Quét danh sách người đang theo dõi")
            sub_radio2.setFont(QFont("Segoe UI", 6))
            sub_radio2.setStyleSheet("QRadioButton { spacing: 2px; color: #444; }")
            
            sub_radio_layout.addWidget(sub_radio1)
            sub_radio_layout.addWidget(sub_radio2)
            
            radio_layout.addWidget(sub_radio_group)
            layout.addWidget(radio_group)
        
        # ⭐ RADIO GROUPS VÀ CHECKBOX CHO CÁC TAB KHÁC
        if idx == 2:  # Tab "Quét Bài Viết Theo Tài Khoản" - có radio buttons riêng
            # Radio group riêng cho tab bài viết
            radio_group = QGroupBox()
            radio_group.setStyleSheet("""
                QGroupBox { 
                    font-size: 6px; 
                    border: 1px solid #ccc;
                    border-radius: 3px;
                    margin-top: 2px;
                    padding: 2px;
                }
            """)
            radio_layout = QVBoxLayout(radio_group)
            radio_layout.setSpacing(1)
            radio_layout.setContentsMargins(3, 3, 3, 3)
            
            radio1 = QRadioButton("Quét bài viết của chính tài khoản")
            radio1.setFont(QFont("Segoe UI", 6))
            radio1.setStyleSheet("QRadioButton { spacing: 2px; color: #333; }")
            radio2 = QRadioButton("Quét theo danh sách tài khoản")
            radio2.setFont(QFont("Segoe UI", 6))
            radio2.setStyleSheet("QRadioButton { spacing: 2px; color: #333; }")
            radio2.setChecked(True)  # Mặc định chọn như hình
            
            radio_layout.addWidget(radio1)
            radio_layout.addWidget(radio2)
            layout.addWidget(radio_group)
        elif idx == 1 or idx == 3:  # Tab từ khóa
            # Cho tab từ khóa, set radio1, radio2 = None
            radio1 = None
            radio2 = None
        
        # ⭐ CHECKBOX KHÁC NHAU CHO TỪNG TAB
        if idx == 2:  # Tab "Quét Bài Viết Theo Tài Khoản"
            public_only_checkbox = QCheckBox("Chỉ quét bài viết đang hiển thị")
        elif idx == 3:  # Tab "Quét Bài Viết Theo Từ Khóa"  
            public_only_checkbox = QCheckBox("Chỉ quét bài viết đang hiển thị")
        else:  # Các tab khác
            public_only_checkbox = QCheckBox("Chỉ quét tài khoản công khai")
            
        public_only_checkbox.setFont(QFont("Segoe UI", 6))
        public_only_checkbox.setStyleSheet("""
            QCheckBox { 
                spacing: 2px; 
                color: #333;
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 2px;
                background-color: #f9f9f9;
            }
        """)
        layout.addWidget(public_only_checkbox)
        
        # Link text - COMPACT
        link_text = QLabel("Nhập link trang cá nhân hoặc username vào đây mỗi dòng một giá trị...")
        link_text.setFont(QFont("Segoe UI", 6))  # Rất nhỏ
        link_text.setStyleSheet("color: blue; text-decoration: underline; padding: 1px;")  # Compact padding
        link_text.setWordWrap(True)  # Important cho responsive
        link_text.setCursor(Qt.CursorShape.PointingHandCursor)
        link_text.mousePressEvent = lambda event, i=idx: self.open_txt_file(i)
        layout.addWidget(link_text)
        
        layout.addStretch()
        
        # Lưu các widget cấu hình để lấy giá trị khi cần
        config_dict = {
            'spin_thread': spin_thread,
            'spin_error': spin_error,
            'spin_min': spin_min,
            'spin_max': spin_max,
            'spin_user_min': spin_user_min,
            'spin_user_max': spin_user_max,
            'spin_uname_min': spin_uname_min,
            'spin_uname_max': spin_uname_max,
            'radio1': radio1,
            'radio2': radio2,
            'link_text': link_text,
            'public_only_checkbox': public_only_checkbox
        }
        
        # ⭐ THÊM WIDGET ĐẶC BIỆT CHO TAB TỪ KHÓA
        if idx == 1:
            config_dict['keyword_area'] = keyword_area
            
        self.config_data[idx] = config_dict
        return widget
        
    def switch_config(self, idx):
        for i, btn in enumerate(self.menu_buttons):
            btn.setChecked(i == idx)
        self.stacked_config.setCurrentIndex(idx) 
        self.update_result_table_header(idx)
        
    def update_result_table_header(self, idx):
        """Cập nhật header của result table theo tab hiện tại"""
        if idx == 3:  # Tab "Quét Bài Viết Theo Từ Khóa"
            self.result_label.setText("🔍 Danh Sách Bài Viết Đã Quét")
            self.result_table.setHorizontalHeaderLabels([
                "✓", "STT", "Tài khoản quét", "Từ khóa tìm", "Tên đăng bài", 
                "Mã bài viết", "Link bài viết", "Nội dung bài", "Media link", "Loại bài"
            ])
        else:  # Các tab khác
            self.result_label.setText("👥 Danh Sách Tài Khoản Đã Quét")
            self.result_table.setHorizontalHeaderLabels([
                "✓", "STT", "Tài khoản quét", "Link Instagram", "Tên người dùng", 
                "Trạng thái", "Nguồn quét", "Thời gian", "Ghi chú", "Thao tác"
            ]) 

    def open_txt_file(self, idx):
        file_path, _ = QFileDialog.getOpenFileName(self, "Chọn file danh sách", "", "Text Files (*.txt)")
        if file_path:
            with open(file_path, "r", encoding="utf-8") as f:
                data = [line.strip() for line in f if line.strip()]
            self.username_lists[idx] = data
            QMessageBox.information(self, "Đã nhập danh sách", f"Đã nhập {len(data)} username/link.")

    def load_accounts(self):
        # Nạp toàn bộ tài khoản từ accounts.json, chỉ lấy tài khoản đã đăng nhập
        accounts_file = os.path.join("accounts.json")
        self.accounts = []
        if os.path.exists(accounts_file):
            with open(accounts_file, "r", encoding="utf-8") as f:
                all_accounts = json.load(f)
            # Chỉ lấy tài khoản đã đăng nhập
            self.accounts = [acc for acc in all_accounts if acc.get("status") in ["Đã đăng nhập", "Live"]]
        self.on_folder_changed()  # Hiển thị theo thư mục đang chọn

    def update_account_table(self, accounts_to_display=None):
        if accounts_to_display is None:
            accounts_to_display = self.accounts
        self.account_table.setRowCount(len(accounts_to_display))
        for i, acc in enumerate(accounts_to_display):
            # Cột 0: chỉ dùng delegate, không tạo QTableWidgetItem checkable nữa
            item = QTableWidgetItem()
            item.setData(CheckboxDelegate.CheckboxStateRole, acc.get("selected", False))
            self.account_table.setItem(i, 0, item)
            # Cột 1: STT
            self.account_table.setItem(i, 1, QTableWidgetItem(str(i+1)))
            # Cột 2: Số điện thoại - hiển thị số điện thoại Telegram thật
            telegram_phone = acc.get("telegram_phone", "") or acc.get("phone_telegram", "") or acc.get("tg_phone", "") or acc.get("phone_number", "") or acc.get("phone", "")
            if not telegram_phone:
                # Fallback: nếu không có số điện thoại Telegram, hiển thị username (có thể là số điện thoại)
                telegram_phone = acc.get("username", "")
                if not telegram_phone:
                    telegram_phone = "Chưa có số điện thoại"
            self.account_table.setItem(i, 2, QTableWidgetItem(telegram_phone))
            # Cột 3: Mật khẩu 2FA
            telegram_2fa = acc.get("telegram_2fa", "") or acc.get("two_fa_password", "") or acc.get("password_2fa", "") or acc.get("twofa", "") or "Chưa có 2FA"
            self.account_table.setItem(i, 3, QTableWidgetItem(telegram_2fa))
            # Cột 4: Username - hiển thị username Telegram thật
            telegram_username = acc.get("telegram_username", "") or acc.get("username_telegram", "") or acc.get("tg_username", "") or ""
            # Đảm bảo có @ ở đầu nếu là username Telegram
            if telegram_username and not telegram_username.startswith("@"):
                telegram_username = "@" + telegram_username
            if not telegram_username:
                telegram_username = "Chưa có username"
            self.account_table.setItem(i, 4, QTableWidgetItem(telegram_username))
            # Cột 5: ID
            account_id = acc.get("telegram_id", "") or acc.get("id_telegram", "") or acc.get("tg_id", "") or acc.get("user_id", "") or "Chưa có ID"
            self.account_table.setItem(i, 5, QTableWidgetItem(account_id))
            # Cột 6: Trạng thái quét
            self.account_table.setItem(i, 6, QTableWidgetItem(acc.get("status", "")))
            # Cột 7: Số lượng quét
            self.account_table.setItem(i, 7, QTableWidgetItem(str(acc.get("success", ""))))

    def start_scan(self):
        """⭐ BẮT ĐẦU QUÉT THẬT với Instagram Scanner"""
        if self.scan_running:
            QMessageBox.warning(self, "Cảnh báo", "Quét đang chạy! Vui lòng dừng trước khi bắt đầu mới.")
            return
        
        # Kiểm tra tài khoản được chọn
        selected_accounts = [acc for acc in self.accounts if acc.get('selected')]
        if not selected_accounts:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn ít nhất 1 tài khoản để quét!")
            return
        
        # ⭐ KIỂM TRA SELENIUM
        if not selenium_available:
            QMessageBox.critical(self, "Lỗi", "Selenium không có sẵn!\nVui lòng cài đặt: pip install selenium")
            return
        
        # ⭐ KIỂM TRA DANH SÁCH MỤC TIÊU
        current_idx = self.stacked_config.currentIndex()
        scan_type = self.get_current_scan_type()
        
        if current_idx in [1, 3]:  # Quét theo từ khóa
            if not self.username_lists[current_idx]:
                QMessageBox.warning(self, "Cảnh báo", "Vui lòng nhập danh sách từ khóa để quét!")
                return
        
        self.scan_running = True
        self.result_data = []
        self.result_table.setRowCount(0)
        self.account_data = selected_accounts.copy()  # Chỉ quét tài khoản đã chọn
        
        # ⭐ SCANNER ĐÃ SẴN SÀNG - Không cần setup_driver trước nữa vì sẽ setup trong login method
        
        # ⭐ Progress tracking
        self.overall_progress.setVisible(True)
        self.overall_progress.setValue(0)
        self.overall_progress.setMaximum(len(self.account_data))
        
        self.stats_label.setText("Tổng số username quét được: 0")
        
        self.scan_idx = 0
        self.completed_accounts = 0
        self.total_results = 0
        self.current_account_index = 0
        
        # ⭐ BẮT ĐẦU QUÉT THẬT
        self.scan_timer = QTimer()
        self.scan_timer.timeout.connect(self.scan_step_real)
        self.scan_timer.start(1000)  # 1 giây để xử lý quét thật

    def scan_step_real(self):
        """⭐ QUÉT THẬT từng bước với Instagram Scanner"""
        if self.scan_idx >= len(self.account_data):
            # ⭐ HOÀN THÀNH QUÉT
            self.scan_timer.stop()
            self.scan_running = False
            
            # ⭐ ĐÓNG DRIVER
            self.instagram_scanner.close()
            
            # ⭐ Final status update
            self.overall_progress.setValue(len(self.account_data))
            
            # ⭐ Show completion message
            QMessageBox.information(
                self, 
                "Hoàn thành quét", 
                f"🎉 Đã hoàn thành quét dữ liệu thật!\n\n"
                f"📊 Tài khoản đã quét: {self.completed_accounts}\n"
                f"🔍 Tổng username thu được: {self.total_results}\n"
                f"⏱️ Dữ liệu Instagram thật được quét"
            )
            return
        
        acc = self.account_data[self.scan_idx]
        current_config = self.get_current_config()
        current_idx = self.stacked_config.currentIndex()
        
        # ⭐ Cập nhật trạng thái đang quét
        acc['status'] = '🔄 Đang đăng nhập...'
        self.update_account_table()
        QApplication.processEvents()  # Cập nhật UI
        
        # ⭐ ĐĂNG NHẬP VỚI TÀI KHOẢN sử dụng logic Account Management
        if not self.instagram_scanner.login_with_account_management_logic(acc):
            acc['status'] = '❌ Lỗi đăng nhập'
            acc['success'] = 0
            self.scan_idx += 1
            return
        
        acc['status'] = '🔍 Đang quét dữ liệu...'
        self.update_account_table()
        QApplication.processEvents()
        
        # ⭐ THỰC HIỆN QUÉT THEO LOẠI
        scanned_users = []
        max_users = current_config.get('max_users', 30)
        
        try:
            if current_idx == 0:  # Quét Followers
                if current_config.get('scan_own'):  # Quét followers của chính mình
                    scanned_users = self.instagram_scanner.scan_followers(acc['username'], max_users)
                else:  # Quét theo danh sách
                    target_users = self.username_lists[current_idx]
                    for target in target_users[:3]:  # Giới hạn 3 target để không quá lâu
                        users = self.instagram_scanner.scan_followers(target, max_users // 3)
                        scanned_users.extend(users)
                        if len(scanned_users) >= max_users:
                            break
            
            elif current_idx == 1:  # Quét theo từ khóa
                keywords = self.username_lists[current_idx]
                for keyword in keywords[:2]:  # Giới hạn 2 keywords
                    users = self.instagram_scanner.search_users_by_keyword(keyword, max_users // 2)
                    scanned_users.extend(users)
                    if len(scanned_users) >= max_users:
                        break
            
            elif current_idx == 2:  # Quét bài viết
                if current_config.get('scan_own'):  # Quét following của chính mình
                    scanned_users = self.instagram_scanner.scan_following(acc['username'], max_users)
                else:  # Quét theo danh sách
                    target_users = self.username_lists[current_idx]
                    for target in target_users[:3]:
                        users = self.instagram_scanner.scan_following(target, max_users // 3)
                        scanned_users.extend(users)
                        if len(scanned_users) >= max_users:
                            break
            
            elif current_idx == 3:  # Quét bài viết theo từ khóa
                post_urls = self.username_lists[current_idx]  # Giả sử đây là danh sách post URLs
                for post_url in post_urls[:2]:
                    if 'instagram.com/p/' in post_url:
                        users = self.instagram_scanner.scan_post_likers(post_url, max_users // 2)
                        scanned_users.extend(users)
                        if len(scanned_users) >= max_users:
                            break
            
            # ⭐ LƯU KẾT QUẢ
            n_result = len(scanned_users)
            current_scan_type = self.get_current_scan_type()
            
            for user_data in scanned_users:
                self.result_data.append({
                    'scanner_account': acc['username'],
                    'target_account': user_data.get('source', ''),
                    'found_username': user_data.get('username', ''),
                    'display_name': user_data.get('display_name', ''),
                    'profile_url': user_data.get('profile_url', ''),
                    'scan_type': current_scan_type,
                    'timestamp': user_data.get('scan_time', self.get_current_timestamp())
                })
            
            # ⭐ Cập nhật trạng thái hoàn thành
            acc['status'] = f'✅ Hoàn thành ({n_result})'
            acc['success'] = n_result
            self.completed_accounts += 1
            self.total_results += n_result
            
        except Exception as e:
            print(f"[ERROR] Lỗi quét: {e}")
            acc['status'] = '❌ Lỗi quét'
            acc['success'] = 0
        
        # ⭐ Cập nhật UI
        self.update_account_table()
        self.update_result_table()
        
        # ⭐ Cập nhật progress
        self.overall_progress.setValue(self.completed_accounts)
        self.stats_label.setText(f"Tổng số username quét được: {self.total_results}")
        
        self.scan_idx += 1

    def scan_step(self):
        """⭐ FALLBACK: Quét giả lập nếu không có scanner thật"""
        if self.scan_idx >= len(self.account_data):
            # ⭐ HOÀN THÀNH QUÉT
            self.scan_timer.stop()
            self.scan_running = False
            
            # ⭐ Final status update
            self.overall_progress.setValue(len(self.account_data))
            
            # ⭐ Show completion message
            QMessageBox.information(
                self, 
                "Hoàn thành quét", 
                f"🎉 Đã hoàn thành quét dữ liệu (demo)!\n\n"
                f"📊 Tài khoản đã quét: {self.completed_accounts}\n"
                f"🔍 Tổng username thu được: {self.total_results}\n"
                f"⚠️ Chế độ demo - cài đặt Selenium để quét thật"
            )
            return
        
        acc = self.account_data[self.scan_idx]
        current_config = self.get_current_config()
        
        # ⭐ Cập nhật trạng thái đang quét
        acc['status'] = '🔄 Đang quét (demo)...'
        self.update_account_table()
        
        # ⭐ TỐI ƯU: Giả lập quét thực tế với config
        min_results = current_config.get('min_users', 5)
        max_results = current_config.get('max_users', 15)
        n_result = random.randint(min_results, max_results)
        
        # ⭐ Tạo kết quả realistic hơn
        current_scan_type = self.get_current_scan_type()
        
        for j in range(n_result):
            username = f"demo_user_{acc['username']}_{random.randint(1000, 9999)}"
            target_account = f"demo_target_{random.randint(1, 100)}"
            
            self.result_data.append({
                'scanner_account': acc['username'],
                'target_account': target_account,
                'found_username': username,
                'scan_type': current_scan_type,
                'timestamp': self.get_current_timestamp()
            })
        
        # ⭐ Cập nhật trạng thái hoàn thành
        acc['status'] = f'✅ Demo ({n_result})'
        acc['success'] = n_result
        self.completed_accounts += 1
        self.total_results += n_result
        
        # ⭐ Cập nhật UI
        self.update_account_table()
        self.update_result_table()
        
        # ⭐ Cập nhật progress
        self.overall_progress.setValue(self.completed_accounts)
        self.stats_label.setText(f"Tổng số username quét được: {self.total_results}")
        
        self.scan_idx += 1

    def stop_scan(self):
        """⭐ DỪNG QUÉT với cleanup Instagram Scanner"""
        if self.scan_timer:
            self.scan_timer.stop()
        self.scan_running = False
        
        # ⭐ ĐÓNG INSTAGRAM SCANNER
        if hasattr(self, 'instagram_scanner') and self.instagram_scanner:
            self.instagram_scanner.close()
        
        # ⭐ Update UI when stopped
        if hasattr(self, 'total_results'):
            self.stats_label.setText(f"Tổng số username quét được: {self.total_results}")
        
        # ⭐ Hiển thị thông báo dừng
        if hasattr(self, 'completed_accounts'):
            QMessageBox.information(
                self,
                "Dừng quét",
                f"⏹️ Đã dừng quét!\n\n"
                f"📊 Đã quét: {self.completed_accounts} tài khoản\n"
                f"🔍 Tổng username: {getattr(self, 'total_results', 0)}"
            )

    def update_result_table(self):
        """⭐ CẬP NHẬT BẢNG KẾT QUẢ với dữ liệu Instagram thật (6 cột)"""
        self.result_table.setRowCount(len(self.result_data))
        for i, res in enumerate(self.result_data):
            # Checkbox
            chk = QTableWidgetItem()
            chk.setCheckState(Qt.CheckState.Unchecked)
            self.result_table.setItem(i, 0, chk)
            
            # STT
            self.result_table.setItem(i, 1, QTableWidgetItem(str(i+1)))
            
            # Tài khoản quét (scanner)
            scanner_item = QTableWidgetItem(res.get('scanner_account', res.get('account', '')))
            scanner_tooltip = f"Scan type: {res.get('scan_type', 'Unknown')}\nSource: {res.get('target_account', 'Unknown')}\nTime: {res.get('timestamp', 'Unknown')}"
            scanner_item.setToolTip(scanner_tooltip)
            self.result_table.setItem(i, 2, scanner_item)
            
            # Link Trang cá nhân - ưu tiên profile_url từ Instagram scanner
            profile_url = res.get('profile_url', f"https://instagram.com/{res.get('found_username', res.get('username', ''))}")
            link_item = QTableWidgetItem(profile_url)
            link_item.setToolTip("Click để copy link Instagram")
            self.result_table.setItem(i, 3, link_item)
            
            # Tên tài khoản (username tìm được)
            username = res.get('found_username', res.get('username', ''))
            username_item = QTableWidgetItem(username)
            username_item.setToolTip(f"Username: {username}\nDisplay name: {res.get('display_name', username)}\nDouble-click để copy")
            self.result_table.setItem(i, 4, username_item)
            
            # Avatar - hiển thị trạng thái
            avatar_status = "✅ Real" if res.get('profile_url') else "🔄 Demo"
            avatar_item = QTableWidgetItem(avatar_status)
            avatar_item.setToolTip("✅ Real: Dữ liệu thật từ Instagram\n🔄 Demo: Dữ liệu demo")
            self.result_table.setItem(i, 5, avatar_item)

    def show_context_menu(self, pos):
        """Hiển thị menu chuột phải."""
        print(f"[DEBUG] show_context_menu được gọi tại vị trí: {pos}")
        menu = DataScannerContextMenu(self)
        menu.exec(self.result_table.viewport().mapToGlobal(pos))

    def load_folder_list_to_combo(self):
        self.category_combo.clear()
        self.category_combo.addItem("Tất cả")
        folder_map_file = os.path.join("data", "folder_map.json")
        if os.path.exists(folder_map_file):
            with open(folder_map_file, "r", encoding="utf-8") as f:
                folder_map = json.load(f)
            if folder_map and "_FOLDER_SET_" in folder_map:
                for folder in folder_map["_FOLDER_SET_"]:
                    if folder != "Tổng":
                        self.category_combo.addItem(folder)
        print(f"[DEBUG][DataScannerTab] Đã tải danh sách thư mục vào combobox: {self.category_combo.count()} mục")

    def on_folder_changed(self):
        selected_folder = self.category_combo.currentText()
        folder_map_file = os.path.join("data", "folder_map.json")
        folder_map = {}
        if os.path.exists(folder_map_file):
            with open(folder_map_file, "r", encoding="utf-8") as f:
                folder_map = json.load(f)
        if selected_folder == "Tất cả":
            filtered_accounts = self.accounts
        else:
            filtered_accounts = [
                acc for acc in self.accounts
                if folder_map.get(acc.get("username"), "Tổng") == selected_folder
            ]
        self.update_account_table(filtered_accounts)

    def on_folders_updated(self):
        self.load_folder_list_to_combo() 

    def on_checkbox_clicked(self, row, new_state):
        # Cập nhật trạng thái 'selected' trong dữ liệu gốc
        if 0 <= row < len(self.accounts):
            self.accounts[row]["selected"] = new_state 

    def select_selected_accounts(self):
        selected_rows = self.account_table.selectionModel().selectedRows()
        for index in selected_rows:
            row = index.row()
            if row < len(self.accounts):
                model_index = self.account_table.model().index(row, 0)
                self.account_table.model().setData(model_index, True, CheckboxDelegate.CheckboxStateRole)
                self.accounts[row]["selected"] = True
        self.update_account_table()

    def deselect_selected_accounts(self):
        selected_rows = self.account_table.selectionModel().selectedRows()
        for index in selected_rows:
            row = index.row()
            if row < len(self.accounts):
                model_index = self.account_table.model().index(row, 0)
                self.account_table.model().setData(model_index, False, CheckboxDelegate.CheckboxStateRole)
                self.accounts[row]["selected"] = False
        self.update_account_table() 

    # ⭐ HELPER METHODS TỐI ƯU
    def get_current_config(self):
        """Lấy cấu hình hiện tại từ UI"""
        current_idx = self.stacked_config.currentIndex()
        config = self.config_data[current_idx]
        
        return {
            'threads': config['spin_thread'].value(),
            'error_threshold': config['spin_error'].value(),
            'min_delay': config['spin_min'].value(),
            'max_delay': config['spin_max'].value(),
            'min_users': config['spin_user_min'].value(),
            'max_users': config['spin_user_max'].value(),
            'min_scans': config['spin_uname_min'].value(),
            'max_scans': config['spin_uname_max'].value(),
            'scan_own': config['radio1'].isChecked() if config['radio1'] else False,
            'scan_list': config['radio2'].isChecked() if config['radio2'] else True
        }

    def get_current_scan_type(self):
        """Lấy loại quét hiện tại"""
        scan_types = [
            "Quét theo dõi", 
            "Quét bài viết", 
            "Quét chi tiết", 
            "Quét follow"
        ]
        return scan_types[self.stacked_config.currentIndex()]
    
    def get_current_timestamp(self):
        """Lấy timestamp hiện tại"""
        import datetime
        return datetime.datetime.now().strftime("%H:%M:%S")
    
    # ⭐ EXPORT/IMPORT METHODS TỐI ƯU
    def export_results(self):
        """Xuất kết quả quét ra file"""
        if not self.result_data:
            QMessageBox.warning(self, "Cảnh báo", "Không có dữ liệu để xuất!")
            return
        
        # Lựa chọn loại file xuất
        file_path, file_type = QFileDialog.getSaveFileName(
            self,
            "Xuất kết quả quét",
            f"scan_results_{self.get_current_timestamp().replace(':', '')}.txt",
            "Text Files (*.txt);;CSV Files (*.csv);;All Files (*)"
        )
        
        if not file_path:
            return
        
        try:
            if file_path.endswith('.csv'):
                self.export_to_csv(file_path)
            else:
                self.export_to_txt(file_path)
                
            QMessageBox.information(
                self, 
                "Xuất thành công", 
                f"✅ Đã xuất {len(self.result_data)} kết quả ra:\n{file_path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Lỗi xuất file", f"❌ Có lỗi khi xuất file:\n{str(e)}")
    
    def export_to_txt(self, file_path):
        """Xuất ra file TXT"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("# INSTAGRAM SCAN RESULTS\n")
            f.write(f"# Exported: {self.get_current_timestamp()}\n")
            f.write(f"# Total results: {len(self.result_data)}\n")
            f.write("# Format: found_username\n\n")
            
            for res in self.result_data:
                username = res.get('found_username', res.get('username', ''))
                f.write(f"{username}\n")
    
    def export_to_csv(self, file_path):
        """Xuất ra file CSV"""
        import csv
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                'STT', 'Scanner Account', 'Target Account', 
                'Found Username', 'Scan Type', 'Timestamp'
            ])
            
            # Data
            for i, res in enumerate(self.result_data, 1):
                writer.writerow([
                    i,
                    res.get('scanner_account', res.get('account', '')),
                    res.get('target_account', res.get('target', '')),
                    res.get('found_username', res.get('username', '')),
                    res.get('scan_type', 'Unknown'),
                    res.get('timestamp', 'Unknown')
                ])
    
    def clear_results(self):
        """Xóa toàn bộ kết quả"""
        if not self.result_data:
            QMessageBox.information(self, "Thông báo", "Không có dữ liệu để xóa!")
            return
        
        reply = QMessageBox.question(
            self,
            "Xác nhận xóa",
            f"Bạn có chắc muốn xóa {len(self.result_data)} kết quả quét?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.result_data = []
            self.result_table.setRowCount(0)
            self.stats_label.setText("Tổng số username quét được: 0")
            
            QMessageBox.information(self, "Thành công", "✅ Đã xóa toàn bộ kết quả quét!")
    
    def get_selected_result_usernames(self):
        """Lấy danh sách username được chọn từ bảng kết quả"""
        selected_usernames = []
        for i in range(self.result_table.rowCount()):
            checkbox_item = self.result_table.item(i, 0)
            if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
                username_item = self.result_table.item(i, 4)
                if username_item:
                    selected_usernames.append(username_item.text())
        return selected_usernames 