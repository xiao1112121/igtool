import time
import random
import logging
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QMetaObject
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QLineEdit, QTextEdit, QFileDialog, QMessageBox,
    QProgressBar, QComboBox, QCheckBox, QSpinBox, QGroupBox,
    QScrollArea, QFrame, QSplitter, QTabWidget, QApplication,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView, QSizePolicy, QStyledItemDelegate, QMenu, QProgressDialog, QInputDialog, QSlider)
from PySide6.QtGui import QFont, QIcon, QPixmap, QColor, QPalette, QPainter, QPen, QGuiApplication, QAction
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from seleniumwire import webdriver as wire_webdriver
from seleniumwire.utils import decode
from twocaptcha import TwoCaptcha
from src.ui.utils import random_delay, wait_for_element, wait_for_element_clickable, retry_operation
from src.ui.context_menus import AccountContextMenu
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium.webdriver.common.keys import Keys

class ImprovedLoginManager:
    """Improved login manager with better timeout handling and no-hang guarantees"""
    
    def __init__(self, parent):
        self.parent = parent
        self.active_drivers = []
        self.login_timeout = 15  # Reduced from 30 seconds
        self.max_wait_time = 3   # Max wait for elements
        
    def login_instagram_safe(self, account, window_position=None):
        """Safe login method that won't hang the application"""
        driver = None
        username = account.get("username")
        password = account.get("password")
        proxy = account.get("proxy") if getattr(self.parent, 'use_proxy', True) else None
        
        try:
            logging.info(f"Starting login for {username}")
            
            # Step 1: Initialize driver with timeout
            account["status"] = "Khởi tạo trình duyệt..."
            self._update_ui()
            
            driver = self._init_driver_with_timeout(proxy, username)
            if not driver:
                return "Lỗi khởi tạo driver", "Error", None
                
            self.active_drivers.append(driver)
            
            # Step 2: Set window position
            if window_position and len(window_position) == 4:
                try:
                    x, y, width, height = window_position
                    driver.set_window_rect(x, y, width, height)
                except Exception as e:
                    logging.warning(f"Could not set window position: {e}")
            
            # Step 3: Navigate to Instagram with timeout
            account["status"] = "Đang mở Instagram..."
            self._update_ui()
            
            if not self._navigate_to_instagram(driver):
                return "Lỗi mở Instagram", "Error", driver
            
            # Step 4: Try loading cookies first
            cookies_loaded = self._load_cookies_safe(driver, username)
            if cookies_loaded and self._check_login_status_quick(driver):
                account["status"] = "Đã đăng nhập (cookies)"
                self._save_cookies_safe(driver, username)
                self._update_ui()
                return "Đã đăng nhập", "Live", driver
            
            # Step 5: Perform manual login if cookies failed
            account["status"] = "Đang đăng nhập..."
            self._update_ui()
            
            login_result = self._perform_manual_login(driver, username, password)
            if login_result == "success":
                account["status"] = "Đã đăng nhập"
                self._save_cookies_safe(driver, username)
                self._update_ui()
                return "Đã đăng nhập", "Live", driver
            elif login_result == "checkpoint":
                account["status"] = "Cần xác minh"
                self._update_ui()
                return "Checkpoint/Captcha", "Checkpoint", driver
            else:
                account["status"] = "Đăng nhập thất bại"
                self._update_ui()
                return "Đăng nhập thất bại", "Error", driver
                
        except Exception as e:
            logging.error(f"Login error for {username}: {e}")
            account["status"] = f"Lỗi: {str(e)[:50]}"
            self._update_ui()
            return f"Lỗi: {str(e)}", "Error", driver
    
    def _init_driver_with_timeout(self, proxy, username):
        """Initialize driver with strict timeout"""
        try:
            # Use parent's init_driver method but with timeout
            return self.parent.init_driver(proxy, username)
        except Exception as e:
            logging.error(f"Driver init failed: {e}")
            return None
    
    def _navigate_to_instagram(self, driver, timeout=10):
        """Navigate to Instagram with timeout"""
        try:
            driver.set_page_load_timeout(timeout)
            driver.get("https://www.instagram.com/")
            return True
        except Exception as e:
            logging.error(f"Navigation failed: {e}")
            return False
    
    def _check_login_status_quick(self, driver):
        """Quick check if already logged in (max 3 seconds)"""
        try:
            # Wait max 3 seconds for login indicators
            wait = WebDriverWait(driver, 3)
            
            # Check for home icon (most reliable indicator)
            try:
                home_icon = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "svg[aria-label='Home']"))
                )
                if home_icon.is_displayed():
                    logging.info("Login detected via home icon")
                    return True
            except TimeoutException:
                pass
            
            # Check current URL
            current_url = driver.current_url
            if "instagram.com" in current_url and not any(x in current_url for x in ["login", "challenge", "checkpoint"]):
                # Additional check for profile elements
                try:
                    driver.find_element(By.CSS_SELECTOR, "img[alt*='profile picture']")
                    logging.info("Login detected via profile picture")
                    return True
                except:
                    pass
            
            return False
            
        except Exception as e:
            logging.error(f"Quick login check failed: {e}")
            return False
    
    def _perform_manual_login(self, driver, username, password):
        """Perform manual login with strict timeouts"""
        try:
            wait = WebDriverWait(driver, self.max_wait_time)
            
            # Find username field
            try:
                username_field = wait.until(
                    EC.element_to_be_clickable((By.NAME, "username"))
                )
            except TimeoutException:
                logging.error("Username field not found")
                return "error"
            
            # Clear and type username
            username_field.clear()
            self._type_human_like(username_field, username)
            
            # Find password field
            try:
                password_field = wait.until(
                    EC.element_to_be_clickable((By.NAME, "password"))
                )
            except TimeoutException:
                logging.error("Password field not found")
                return "error"
            
            # Clear and type password
            password_field.clear()
            self._type_human_like(password_field, password)
            
            # Submit form
            password_field.send_keys(Keys.ENTER)
            
            # Wait for navigation (max 10 seconds)
            start_time = time.time()
            while time.time() - start_time < 10:
                current_url = driver.current_url
                
                # Check for successful login
                if "instagram.com" in current_url and not any(x in current_url for x in ["login"]):
                    if self._check_login_status_quick(driver):
                        return "success"
                
                # Check for checkpoint/challenge
                if any(x in current_url for x in ["challenge", "checkpoint"]):
                    return "checkpoint"
                
                time.sleep(0.5)
            
            return "error"
            
        except Exception as e:
            logging.error(f"Manual login failed: {e}")
            return "error"
    
    def _type_human_like(self, element, text):
        """Type text with human-like delays"""
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))
    
    def _load_cookies_safe(self, driver, username):
        """Load cookies safely with error handling"""
        try:
            return self.parent.load_cookies(driver, username)
        except Exception as e:
            logging.warning(f"Cookie load failed for {username}: {e}")
            return False
    
    def _save_cookies_safe(self, driver, username):
        """Save cookies safely with error handling"""
        try:
            self.parent.save_cookies(driver, username)
        except Exception as e:
            logging.warning(f"Cookie save failed for {username}: {e}")
    
    def _update_ui(self):
        """Thread-safe UI update"""
        try:
            QMetaObject.invokeMethod(self.parent, "update_account_table", Qt.QueuedConnection)
        except Exception as e:
            logging.warning(f"UI update failed: {e}")
    
    def cleanup_drivers(self):
        """Clean up all active drivers"""
        for driver in self.active_drivers[:]:
            try:
                if driver:
                    driver.quit()
                    self.active_drivers.remove(driver)
            except Exception as e:
                logging.warning(f"Driver cleanup error: {e}")


class LoginTimeoutThread(QThread):
    """Thread for login with automatic timeout"""
    
    login_completed = Signal(str, str, str, object)  # username, status, proxy_status, driver
    
    def __init__(self, login_manager, account, window_position=None):
        super().__init__()
        self.login_manager = login_manager
        self.account = account
        self.window_position = window_position
        self.timeout_timer = QTimer()
        self.timeout_timer.timeout.connect(self.force_timeout)
        self.timeout_timer.setSingleShot(True)
        
    def run(self):
        """Run login with timeout protection"""
        try:
            # Start timeout timer (30 seconds max for entire login process)
            self.timeout_timer.start(30000)
            
            username = self.account.get("username")
            status, proxy_status, driver = self.login_manager.login_instagram_safe(
                self.account, self.window_position
            )
            
            self.timeout_timer.stop()
            self.login_completed.emit(username, status, proxy_status, driver)
            
        except Exception as e:
            self.timeout_timer.stop()
            logging.error(f"Login thread error: {e}")
            self.login_completed.emit(
                self.account.get("username", "unknown"), 
                f"Thread error: {str(e)}", 
                "Error", 
                None
            )
    
    def force_timeout(self):
        """Force timeout if login takes too long"""
        logging.warning(f"Login timeout for {self.account.get('username')}")
        self.terminate()
        self.login_completed.emit(
            self.account.get("username", "unknown"),
            "Timeout (quá lâu)",
            "Timeout", 
            None
        )


def monkey_patch_account_management(account_tab):
    """Apply improved login logic to existing AccountManagementTab"""
    
    # Create improved login manager
    account_tab.improved_login_manager = ImprovedLoginManager(account_tab)
    
    # Store original method
    account_tab.original_login_method = account_tab.login_instagram_and_get_info
    
    def improved_login_instagram_and_get_info(account, window_position=None, max_retries=3, retry_delay=5):
        """Improved login method that won't hang"""
        
        def _perform_login():
            username = account.get("username")
            
            # Use timeout thread for safety
            login_thread = LoginTimeoutThread(
                account_tab.improved_login_manager, 
                account, 
                window_position
            )
            
            # Create event loop for thread completion
            import time
            thread_completed = False
            result = None
            
            def on_login_completed(username, status, proxy_status, driver):
                nonlocal thread_completed, result
                thread_completed = True
                result = (status, proxy_status, driver)
                
                # Clean up driver if login failed
                if driver and status not in ["Đã đăng nhập", "Checkpoint/Captcha"]:
                    try:
                        driver.quit()
                    except:
                        pass
                    result = (status, proxy_status, None)
            
            login_thread.login_completed.connect(on_login_completed)
            login_thread.start()
            
            # Wait for completion with timeout
            start_time = time.time()
            while not thread_completed and time.time() - start_time < 35:  # 35 second total timeout
                QApplication.processEvents()
                time.sleep(0.1)
            
            if not thread_completed:
                # Force cleanup
                try:
                    login_thread.terminate()
                    login_thread.wait(1000)
                except:
                    pass
                account["status"] = "Timeout (bị đơ)"
                account_tab.improved_login_manager._update_ui()
                return "Timeout", "Error", None
            
            return result
        
        # Execute with retries
        for attempt in range(max_retries):
            try:
                result = _perform_login()
                if result and result[0] not in ["Timeout", "Error"]:
                    return result
                
                if attempt < max_retries - 1:
                    logging.info(f"Retry {attempt + 1} for {account.get('username')}")
                    time.sleep(retry_delay)
                    
            except Exception as e:
                logging.error(f"Login attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
        
        # All attempts failed
        account["status"] = "Đăng nhập thất bại"
        account_tab.improved_login_manager._update_ui()
        return "Đăng nhập thất bại", "Error", None
    
    # Replace the method
    account_tab.login_instagram_and_get_info = improved_login_instagram_and_get_info
    
    # Add cleanup method
    original_close_all = account_tab.close_all_drivers
    
    def improved_close_all_drivers():
        """Enhanced cleanup"""
        try:
            account_tab.improved_login_manager.cleanup_drivers()
        except:
            pass
        return original_close_all()
    
    account_tab.close_all_drivers = improved_close_all_drivers
    
    logging.info("Account management monkey-patched with improved login logic")

# Usage: Call this function after creating AccountManagementTab
# monkey_patch_account_management(account_tab_instance) 