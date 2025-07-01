from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QPushButton, 
                            QTableWidget, QTableWidgetItem, QComboBox, QLabel, 
                            QLineEdit, QSpinBox, QRadioButton, QCheckBox, 
                            QGroupBox, QTextEdit, QHeaderView, QFileDialog, QMessageBox, QButtonGroup,
                            QProgressBar, QScrollArea, QFrame, QSplitter, QTabWidget, QApplication,
                            QSizePolicy, QStyledItemDelegate, QMenu, QAbstractItemView, QInputDialog)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSize, QModelIndex, QRect, QEvent, QMutex
from PySide6.QtGui import QFont, QIcon, QPixmap, QColor, QPalette, QPainter, QPen, QAction
from src.ui.context_menus import MessagingContextMenu
from src.ui.account_management import CheckboxDelegate
import json
import os
import time
import random
import threading
from typing import List, Dict, Any, Optional, Tuple

class MessageSenderThread(QThread):
    """Thread class for sending messages without blocking UI"""
    
    # Signals for communication with main thread
    progress_updated = Signal(str, str, int, str)  # username, status, success_count, detail
    finished = Signal()
    error_occurred = Signal(str, str)  # username, error_message
    
    def __init__(self, sender_accounts: List[Dict[str, Any]], usernames: List[str], 
                 selected_messages: List[Tuple[str, str]], settings: Dict[str, Any], 
                 account_tab: Any, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.sender_accounts = sender_accounts
        self.usernames = usernames
        self.selected_messages = selected_messages
        self.settings = settings
        self.account_tab = account_tab
        self.should_stop = False
        self.mutex = QMutex()
        
    def stop(self):
        """Stop the sending process"""
        self.mutex.lock()
        self.should_stop = True
        self.mutex.unlock()
        
    def is_stopped(self) -> bool:
        """Check if thread should stop"""
        self.mutex.lock()
        stopped = self.should_stop
        self.mutex.unlock()
        return stopped
        
    def run(self):
        """Main thread execution"""
        try:
            max_success = self.settings.get('max_success', 1)
            max_error = self.settings.get('max_error', 1)
            delay_min = self.settings.get('delay_min', 1)
            delay_max = self.settings.get('delay_max', 5)
            
            for acc in self.sender_accounts:
                if self.is_stopped():
                    break
                    
                username = acc.get("username", "")
                error_count = 0
                acc["success"] = 0
                acc["state"] = "Đang gửi"
                total_targets = len(self.usernames)  # Initialize early to avoid UnboundLocalError
                
                self.progress_updated.emit(username, "Đang gửi", 0, "Bắt đầu gửi tin nhắn...")
                
                # Get or create driver
                driver = self.get_driver_for_account(acc)
                if driver is None:
                    self.error_occurred.emit(username, "Không thể lấy driver")
                    continue
                
                for idx, target in enumerate(self.usernames):
                    if self.is_stopped():
                        break
                        
                    content, media = random.choice(self.selected_messages)
                    
                    self.progress_updated.emit(username, "Đang gửi", acc["success"], 
                                             f"Đang gửi tới {target} ({idx+1}/{total_targets})...")
                    
                    try:
                        # Use the thread's own method instead of parent's method
                        result = self.send_instagram_message_safe(acc, target, content, media, driver)
                        
                        if result == "success":
                            acc["success"] = acc.get("success", 0) + 1
                            error_count = 0  # Reset error count on success
                            self.progress_updated.emit(username, "Đã gửi", acc["success"], 
                                                     f"Đã gửi tới {target} | Thành công {acc['success']}/{total_targets}")
                        else:
                            error_count += 1
                            self.progress_updated.emit(username, "Lỗi gửi", acc["success"], 
                                                     f"Lỗi gửi tới {target} ({error_count}) | Thành công {acc['success']}/{total_targets}")
                            
                        # Check stop conditions
                        if acc["success"] >= max_success:
                            acc["state"] = "Thành công"
                            self.progress_updated.emit(username, "Thành công", acc["success"], 
                                                     f"Hoàn thành {acc['success']}/{total_targets}")
                            break
                            
                        if error_count >= max_error:
                            acc["state"] = "Lỗi"
                            self.progress_updated.emit(username, "Lỗi", acc["success"], 
                                                     f"Quá nhiều lỗi liên tiếp | Thành công {acc['success']}/{total_targets}")
                            break
                            
                        # Delay between messages
                        if not self.is_stopped():
                            delay = random.randint(delay_min, delay_max)
                            time.sleep(delay)
                            
                    except Exception as e:
                        error_count += 1
                        self.error_occurred.emit(username, f"Lỗi gửi tin nhắn: {str(e)}")
                        
                        if error_count >= max_error:
                            break
                
                # Final status update - FIX UnboundLocalError
                final_status = "Kết thúc"  # Default value
                if not self.is_stopped():
                    if acc["success"] >= max_success:
                        final_status = "Thành công"
                    elif error_count >= max_error:
                        final_status = "Lỗi"
                    else:
                        final_status = "Kết thúc"
                else:
                    final_status = "Đã dừng"
                        
                self.progress_updated.emit(username, final_status, acc["success"], 
                                         f"{final_status} | Thành công {acc['success']}/{total_targets}")
                                             
        except Exception as e:
            self.error_occurred.emit("Hệ thống", f"Lỗi nghiêm trọng: {str(e)}")
        finally:
            self.finished.emit()
    
    def get_driver_for_account(self, account: Dict) -> Optional[Any]:
        """Get driver for specific account"""
        username = account.get("username")
        if not self.account_tab or not hasattr(self.account_tab, "active_drivers"):
            return None
            
        # Try to find existing driver
        for drv in self.account_tab.active_drivers:
            if isinstance(drv, dict) and drv.get("username") == username:
                return drv.get("driver")
            if hasattr(drv, "insta_username") and drv.insta_username == username:
                return drv
                
        # Try to login if no driver found
        if hasattr(self.account_tab, "login_instagram_and_get_info"):
            try:
                login_result = self.account_tab.login_instagram_and_get_info(account)
                if isinstance(login_result, tuple) and login_result[0] == "Đã đăng nhập":
                    # Try to get driver again after login
                    for drv in self.account_tab.active_drivers:
                        if isinstance(drv, dict) and drv.get("username") == username:
                            return drv.get("driver")
                        if hasattr(drv, "insta_username") and drv.insta_username == username:
                            return drv
            except Exception as e:
                self.error_occurred.emit(username, f"Lỗi đăng nhập: {str(e)}")
                
        return None
    
    def send_instagram_message_safe(self, account: Dict, target: str, content: str, 
                                   media: str, driver: Any) -> str:
        """Send Instagram message with better error handling and improved selectors"""
        try:
            import time  # Import time locally to avoid conflicts
            import os
            from selenium.webdriver.common.by import By
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.common.exceptions import TimeoutException, NoSuchElementException
            
            # Navigate to direct messages
            driver.get("https://www.instagram.com/direct/inbox/")
            wait = WebDriverWait(driver, 10)  # Increased timeout
            
            # Wait for page to load
            time.sleep(3)
            
            # Find and click new message button with improved selectors
            try:
                new_msg_selectors = [
                    # More specific selectors for new message button
                    "//div[@role='button'][contains(@aria-label, 'New message')]",
                    "//div[@role='button'][contains(@aria-label, 'Tin nhắn mới')]",
                    "//button[contains(@aria-label, 'New message')]",
                    "//button[contains(@aria-label, 'Tin nhắn mới')]",
                    "//svg[@aria-label='New message']/../..",
                    "//div[contains(text(), 'Send message')]",
                    "//div[contains(text(), 'Gửi tin nhắn')]",
                    # Fallback selectors
                    "//div[contains(@aria-label, 'message')]",
                    "//button[contains(text(), 'message')]"
                ]
                
                new_msg_btn = None
                for selector in new_msg_selectors:
                    try:
                        new_msg_btn = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                        print(f"[DEBUG] Found new message button with selector: {selector}")
                        break
                    except TimeoutException:
                        continue
                        
                if new_msg_btn:
                    # Scroll to element if needed
                    driver.execute_script("arguments[0].scrollIntoView(true);", new_msg_btn)
                    time.sleep(1)
                    new_msg_btn.click()
                    time.sleep(3)
                else:
                    print("[ERROR] Cannot find new message button")
                    return 'fail'
                    
            except Exception as e:
                print(f"[ERROR] Cannot find new message button: {e}")
                return 'fail'
            
            # Enter target username with improved selectors
            try:
                input_selectors = [
                    "//input[@name='queryBox']",
                    "//input[@placeholder='Search...']",
                    "//input[@placeholder='Tìm kiếm...']",
                    "//input[contains(@placeholder, 'search')]",
                    "//input[contains(@placeholder, 'tìm')]",
                    "//textarea[@placeholder='Search...']",
                    "//div[@contenteditable='true']"
                ]
                
                to_input = None
                for selector in input_selectors:
                    try:
                        to_input = wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                        print(f"[DEBUG] Found input field with selector: {selector}")
                        break
                    except TimeoutException:
                        continue
                
                if to_input:
                    to_input.clear()
                    to_input.send_keys(target)
                    time.sleep(3)  # Wait for search results
                    
                    # Select user from dropdown with improved selectors
                    user_selectors = [
                        f"//div[contains(@role, 'button')]//span[contains(text(), '{target}')]",
                        f"//div[@role='button']//span[contains(@title, '{target}')]",
                        f"//div[contains(text(), '{target}')]",
                        f"//span[contains(text(), '{target}')]",
                        "//div[@role='button'][1]",  # First result
                        "//div[contains(@class, 'x1i10hfl')][1]"  # Instagram's button class
                    ]
                    
                    user_selected = False
                    for selector in user_selectors:
                        try:
                            user_item = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                            print(f"[DEBUG] Found user with selector: {selector}")
                            user_item.click()
                            user_selected = True
                            time.sleep(2)
                            break
                        except TimeoutException:
                            continue
                    
                    if not user_selected:
                        print("[WARN] User not found in dropdown, trying Enter key")
                        to_input.send_keys(Keys.ENTER)
                        time.sleep(2)
                else:
                    print("[ERROR] Cannot find input field")
                    return 'fail'
                    
            except Exception as e:
                print(f"[ERROR] Cannot enter target username: {e}")
                return 'fail'
            
            # Click Next button if exists
            try:
                next_selectors = [
                    "//div[text()='Next' or text()='Tiếp']",
                    "//button[text()='Next' or text()='Tiếp']",
                    "//div[@role='button'][text()='Next' or text()='Tiếp']"
                ]
                
                for selector in next_selectors:
                    try:
                        next_btn = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                        next_btn.click()
                        time.sleep(2)
                        print("[DEBUG] Clicked Next button")
                        break
                    except TimeoutException:
                        continue
            except Exception:
                print("[DEBUG] Next button not found or not needed")
            
            # Enter message content with improved selectors
            try:
                msg_selectors = [
                    "//textarea[@placeholder='Message...']",
                    "//textarea[@placeholder='Tin nhắn...']",
                    "//div[@contenteditable='true'][@role='textbox']",
                    "//div[@contenteditable='true'][contains(@aria-label, 'Message')]",
                    "//textarea[contains(@placeholder, 'message')]",
                    "//textarea[contains(@placeholder, 'tin nhắn')]",
                    "//textarea",  # Fallback
                    "//div[@contenteditable='true']"  # Fallback
                ]
                
                msg_box = None
                for selector in msg_selectors:
                    try:
                        msg_box = wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                        print(f"[DEBUG] Found message box with selector: {selector}")
                        break
                    except TimeoutException:
                        continue
                
                if msg_box:
                    msg_box.clear()
                    msg_box.send_keys(content)
                    time.sleep(2)
                else:
                    print("[ERROR] Cannot find message box")
                    return 'fail'
            except Exception as e:
                print(f"[ERROR] Cannot enter message content: {e}")
                return 'fail'
            
            # Attach media if provided
            if media and os.path.exists(media):
                try:
                    file_input = driver.find_element(By.XPATH, "//input[@type='file']")
                    file_input.send_keys(os.path.abspath(media))
                    time.sleep(3)
                    print("[DEBUG] Media attached successfully")
                except Exception as e:
                    print(f"[WARN] Cannot attach media: {e}")
            
            # Send message with improved selectors
            try:
                send_selectors = [
                    "//button[text()='Send' or text()='Gửi']",
                    "//div[@role='button'][text()='Send' or text()='Gửi']",
                    "//button[contains(@type, 'submit')]",
                    "//div[contains(@aria-label, 'Send')]",
                    "//div[contains(@aria-label, 'Gửi')]",
                    "//button[contains(text(), 'Send')]",
                    "//button[contains(text(), 'Gửi')]",
                    "//div[contains(text(), 'Send')]",
                    "//div[contains(text(), 'Gửi')]"
                ]
                
                send_btn = None
                for selector in send_selectors:
                    try:
                        send_btn = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                        print(f"[DEBUG] Found send button with selector: {selector}")
                        break
                    except TimeoutException:
                        continue
                
                if send_btn:
                    send_btn.click()
                    time.sleep(3)
                    print(f"[SUCCESS] Message sent to {target}")
                    return 'success'
                else:
                    print("[ERROR] Cannot find send button")
                    return 'fail'
                    
            except Exception as e:
                print(f"[ERROR] Cannot send message: {e}")
                return 'fail'
                
        except Exception as e:
            print(f"[ERROR] General error in send_instagram_message_safe: {e}")
            return 'fail'

class MessagingTab(QWidget):
    def __init__(self, account_tab=None):
        super().__init__()
        self.account_tab = account_tab  # Lưu instance AccountManagementTab để lấy driver/session
        
        # Initialize attributes
        self.active_drivers = []  # Add missing attribute
        self.sender_thread: Optional[MessageSenderThread] = None
        self.is_sending = False
        
        # Biến lưu trạng thái
        self.usernames = []  # Danh sách username hợp lệ đã tải lên
        self.username_file_loaded = False
        self.username_file_path = None
        self.duplicate_filtered = False
        self.username_stats_label = QLabel("Số lượng username: 0")
        self.last_username_file_error = None
        
        # Load accounts from account management tab
        self.accounts = []
        self.folder_map = {}
        if self.account_tab:
            self.accounts = self.account_tab.accounts
            self.folder_map = self.account_tab.folder_map
            # Connect signals for syncing
            if hasattr(self.account_tab, "folders_updated"):
                self.account_tab.folders_updated.connect(self.on_folders_updated)
            print(f"[DEBUG] MessagingTab loaded {len(self.accounts)} accounts from account management")
        
        # Initialize UI
        self.init_ui()
        self.load_message_templates()
        
        # Update UI with loaded data
        self.update_account_table()
        self.update_send_stats()
        
    def init_ui(self):
        layout = QHBoxLayout(self)
        
        # Panel bên trái (35%)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Thu nhỏ cỡ chữ cho panel bên trái
        left_panel.setStyleSheet("font-size: 12px;")
        
        # 1. Cấu hình tin nhắn
        config_group = QGroupBox("Cấu hình tin nhắn")
        config_layout = QVBoxLayout(config_group)
        
        # Số luồng chạy đồng thời
        thread_layout = QHBoxLayout()
        thread_layout.addWidget(QLabel("Số luồng:"))
        self.thread_spin = QSpinBox()
        self.thread_spin.setFont(QFont("Segoe UI", 9))
        self.thread_spin.setFixedSize(54, 26)
        self.thread_spin.setRange(1, 10)
        self.thread_spin.setToolTip("Số tài khoản gửi đồng thời")
        self.thread_spin.setStyleSheet("""
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
        thread_layout.addWidget(self.thread_spin)
        config_layout.addLayout(thread_layout)
        
        # Tài khoản lỗi liên tiếp
        error_layout = QHBoxLayout()
        error_layout.addWidget(QLabel("Tài khoản lỗi:"))
        self.error_spin = QSpinBox()
        self.error_spin.setFont(QFont("Segoe UI", 9))
        self.error_spin.setFixedSize(54, 26)
        self.error_spin.setRange(1, 10)
        self.error_spin.setToolTip("Số lần gửi lỗi liên tiếp cho mỗi tài khoản đích, nếu vượt quá thì bỏ qua tài khoản đích đó")
        self.error_spin.setStyleSheet("""
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
        error_layout.addWidget(self.error_spin)
        config_layout.addLayout(error_layout)
        
        # Số lượng tin nhắn thành công/tài khoản gửi
        msg_count_layout = QHBoxLayout()
        msg_count_layout.addWidget(QLabel("Số lượng tin nhắn:"))
        self.msg_count_spin = QSpinBox()
        self.msg_count_spin.setFont(QFont("Segoe UI", 9))
        self.msg_count_spin.setFixedSize(54, 26)
        self.msg_count_spin.setRange(1, 1000)
        self.msg_count_spin.setToolTip("Giới hạn số tin nhắn thành công/tài khoản gửi")
        self.msg_count_spin.setStyleSheet("""
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
        msg_count_layout.addWidget(self.msg_count_spin)
        config_layout.addLayout(msg_count_layout)
        
        # Khoảng cách gửi (giây): min/max
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("Khoảng cách (giây):"))
        self.delay_min_spin = QSpinBox()
        self.delay_min_spin.setFont(QFont("Segoe UI", 9))
        self.delay_min_spin.setFixedSize(54, 26)
        self.delay_min_spin.setRange(1, 3600)
        self.delay_min_spin.setToolTip("Khoảng cách tối thiểu giữa các lần gửi (giây)")
        self.delay_min_spin.setStyleSheet("""
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
        delay_layout.addWidget(self.delay_min_spin)
        delay_layout.addWidget(QLabel("-") )
        self.delay_max_spin = QSpinBox()
        self.delay_max_spin.setFont(QFont("Segoe UI", 9))
        self.delay_max_spin.setFixedSize(54, 26)
        self.delay_max_spin.setRange(1, 3600)
        self.delay_max_spin.setToolTip("Khoảng cách tối đa giữa các lần gửi (giây)")
        self.delay_max_spin.setStyleSheet("""
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
        delay_layout.addWidget(self.delay_max_spin)
        config_layout.addLayout(delay_layout)
        
        left_layout.addWidget(config_group)
        
        # 2. Nhắn theo danh sách
        list_group = QGroupBox("Nhắn theo danh sách")
        list_layout = QVBoxLayout(list_group)
        list_layout.setContentsMargins(8, 18, 8, 8)
        
        # Layout dọc cho radio + checkbox
        radio_col_layout = QVBoxLayout()
        radio_col_layout.setSpacing(8)
        self.username_radio = QRadioButton("Theo danh sách username")
        self.follower_radio = QRadioButton("Theo người theo dõi")
        self.following_radio = QRadioButton("Theo người đang theo dõi")
        
        # Set default selection
        self.username_radio.setChecked(True)
        radio_col_layout.addWidget(self.username_radio)
        radio_col_layout.addWidget(self.follower_radio)
        radio_col_layout.addWidget(self.following_radio)
        self.no_duplicate = QCheckBox("Không nhắn trùng username")
        radio_col_layout.addWidget(self.no_duplicate)
        radio_col_layout.addStretch(1)

        # Layout ngang cho radio + nút nhập data + nút info
        radio_row_layout = QHBoxLayout()
        radio_row_layout.setSpacing(10)
        radio_row_layout.addLayout(radio_col_layout)
        radio_row_layout.addStretch(1)
        
        # Thêm nút Load ở trên nút Nhập data
        buttons_layout = QVBoxLayout()
        self.btn_load = QPushButton("Load")
        self.btn_load.setFixedWidth(90)
        self.btn_load.setStyleSheet("""
            QPushButton { 
                background-color: #FF9800; 
                color: white; 
                border-radius: 4px; 
                font-weight: bold;
                min-height: 30px;
            } 
            QPushButton:hover { 
                background-color: #F57C00; 
            }
        """)
        self.btn_load.setToolTip("Load dữ liệu từ file usernames_data.txt")
        buttons_layout.addWidget(self.btn_load)
        
        self.btn_choose_file = QPushButton("Nhập data")
        self.btn_choose_file.setFixedWidth(90)
        buttons_layout.addWidget(self.btn_choose_file)
        
        radio_row_layout.addLayout(buttons_layout)
        self.info_btn = QPushButton("i")
        self.info_btn.setFixedSize(22, 22)
        self.info_btn.setStyleSheet("QPushButton { border-radius: 11px; background: #1976D2; color: white; font-weight: bold; font-size: 13px; } QPushButton::hover { background: #1565c0; }")
        self.info_btn.setToolTip('<div style="background:#fff; color:#1976D2; font-size:13px; padding:6px;">'
            '<ul style="margin:0; padding-left:18px;">'
            '<li><b>Nhập data</b>: Mở/tạo file usernames_data.txt để chỉnh sửa</li>'
            '<li><b>Load</b>: Load dữ liệu từ file usernames_data.txt lên ứng dụng</li>'
            '<li><b>Theo danh sách username</b>: Nhắn theo dữ liệu được tải lên (có thể là id, username,...)</li>'
            '<li><b>Theo người theo dõi</b>: Nhắn cho những người đang theo dõi chính tài khoản gửi tin nhắn</li>'
            '<li><b>Theo người đang theo dõi</b>: Nhắn cho những người mà tài khoản gửi tin nhắn đang theo dõi</li>'
            '<li><b>Không nhắn trùng username</b>: Khi tick, các tài khoản không được phép gửi trùng người nhận; bỏ tick thì được phép gửi trùng người nhận.</li>'
            '<li>Chỉ các tài khoản đã tick chọn mới được gửi tin nhắn.</li>'
            '</ul>'
        )
        radio_row_layout.addWidget(self.info_btn)
        list_layout.addLayout(radio_row_layout)
        list_layout.addWidget(self.username_stats_label)
        self.btn_choose_file.setVisible(True)
        self.no_duplicate.setVisible(True)
        self.username_stats_label.setVisible(True)
        # Ẩn/hiện nút nhập data và checkbox theo radio
        def update_input_mode():
            if self.username_radio.isChecked():
                self.btn_choose_file.setEnabled(True)
                self.no_duplicate.setEnabled(True)
            else:
                self.btn_choose_file.setEnabled(False)
                self.no_duplicate.setEnabled(False)
        self.username_radio.toggled.connect(update_input_mode)
        self.follower_radio.toggled.connect(update_input_mode)
        self.following_radio.toggled.connect(update_input_mode)
        update_input_mode()
        # Style cho checkbox khi tick
        self.no_duplicate.setStyleSheet("QCheckBox::indicator:checked { background-color: #4caf50; border: 1px solid #388e3c; } QCheckBox::indicator { width: 16px; height: 16px; }")
        # Style cho radio button khi chọn
        radio_style = """
        QRadioButton {
            background: white;
            color: #222;
            border-radius: 4px;
            padding: 2px 8px;
        }
        QRadioButton::indicator { width: 16px; height: 16px; }
        QRadioButton:checked {
            background: white;
            color: #1976D2;
        }
        """
        self.username_radio.setStyleSheet(radio_style)
        self.follower_radio.setStyleSheet(radio_style)
        self.following_radio.setStyleSheet(radio_style)
        self.btn_choose_file.setStyleSheet("QPushButton { background-color: #1976D2; color: white; border-radius: 4px; } QPushButton::hover { background-color: #1565c0; }")
        self.btn_choose_file.setMinimumSize(70, 35)
        self.btn_choose_file.setMaximumSize(90, 35)

        # Connect button signal with proper error handling
        try:
            self.btn_choose_file.blockSignals(True)
            self.btn_choose_file.clicked.connect(self.open_or_create_data_file)
            self.btn_choose_file.blockSignals(False)
        except Exception:
            # Fallback connection if the above fails
            self.btn_choose_file.clicked.connect(self.open_or_create_data_file)

        # Connect duplicate filter checkbox
        self.no_duplicate.stateChanged.connect(self.filter_duplicate_usernames)
        left_layout.addWidget(list_group)
        
        # 3. Nhắn theo nội dung
        content_group = QGroupBox("Nhắn theo nội dung")
        content_layout = QVBoxLayout(content_group)
        
        # Bảng tin nhắn có thêm cột checkbox nhỏ gọn
        self.message_table = QTableWidget()
        self.message_table.setColumnCount(3)
        self.message_table.setHorizontalHeaderLabels(["✓", "Nội dung tin nhắn", "Đường dẫn media"])
        header1 = self.message_table.horizontalHeader()
        header1.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header1.resizeSection(0, 24)
        header1.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header1.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header1.resizeSection(2, 120)  # Thu nhỏ cột Link ảnh/video
        self.message_table.verticalHeader().setVisible(False)
        header1.setStretchLastSection(True)
        self.message_table.horizontalHeader().setFixedHeight(40)
        # Menu chuột phải cho bảng nội dung tin nhắn
        self.message_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.message_table.customContextMenuRequested.connect(self.show_message_context_menu)
        self.message_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        # 🔒 LOCK TABLE - Chỉ xem, không cho phép chỉnh sửa
        self.message_table.setEditTriggers(QTableWidget.NoEditTriggers)
        # Auto-save khi checkbox thay đổi
        self.message_table.itemChanged.connect(self.on_message_item_changed)
        content_layout.addWidget(self.message_table)
        
        # Text box nhập nội dung
        message_input = QTextEdit()
        message_input.setPlaceholderText("Nhập nội dung tin nhắn...")
        message_input.setFixedHeight(50)
        content_layout.addWidget(message_input)
        
        # Nút chọn ảnh/video và lưu
        btn_layout = QHBoxLayout()
        self.btn_choose_media = QPushButton("Chọn ảnh/video")
        self.btn_save = QPushButton("Lưu tin nhắn")
        btn_layout.addWidget(self.btn_choose_media)
        btn_layout.addWidget(self.btn_save)
        content_layout.addLayout(btn_layout)
        self.selected_media_path = None
        self.btn_choose_media.clicked.connect(self.choose_media_file)
        self.btn_save.clicked.connect(self.save_message_content)
        
        left_layout.addWidget(content_group)
        
        # Panel bên phải (65%)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Thanh công cụ
        toolbar = QWidget()
        toolbar_layout = QHBoxLayout(toolbar)
        
        # ComboBox danh mục
        self.category_combo = QComboBox()
        self.load_folder_list_to_combo()
        self.category_combo.currentIndexChanged.connect(self.on_folder_changed)
        
        # Các nút điều khiển
        self.btn_start = QPushButton("Start")
        self.btn_stop = QPushButton("Stop")

        # Style cho các nút Start, Stop
        start_button_style = """
        QPushButton {
            min-width: 40px;
            max-width: 40px;
            min-height: 35px;
            max-height: 35px;
            border: 1px solid #888;
            border-radius: 4px;
            color: white;
            background-color: #4caf50;
        }
        """
        stop_button_style = """
        QPushButton {
            min-width: 40px;
            max-width: 40px;
            min-height: 35px;
            max-height: 35px;
            border: 1px solid #888;
            border-radius: 4px;
            color: white;
            background-color: #e53935;
        }
        """
        self.btn_start.setStyleSheet(start_button_style)
        self.btn_stop.setStyleSheet(stop_button_style)
        toolbar_layout.addWidget(self.category_combo)
        toolbar_layout.addWidget(self.btn_start)
        toolbar_layout.addWidget(self.btn_stop)
        right_layout.addWidget(toolbar)
        
        # Bảng dữ liệu tài khoản
        self.account_table = QTableWidget()
        self.account_table.setColumnCount(9)
        headers = ["✓", "STT", "Số điện thoại", "Mật khẩu 2FA", "Username", "ID", "Trạng thái tài khoản", "Tin nhắn gửi", "Chi tiết quá trình"]
        self.account_table.setHorizontalHeaderLabels(headers)
        header2 = self.account_table.horizontalHeader()
        header2.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header2.resizeSection(0, 32)
        header2.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header2.resizeSection(1, 40)
        header2.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header2.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header2.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header2.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.account_table.verticalHeader().setVisible(False)
        header2.setStretchLastSection(True)
        self.account_table.horizontalHeader().setFixedHeight(40)
        # Đặt delegate checkbox giống tab Quản lý Tài khoản
        self.checkbox_delegate = CheckboxDelegate(self)
        self.account_table.setItemDelegateForColumn(0, self.checkbox_delegate)
        self.checkbox_delegate.checkbox_clicked.connect(self.on_checkbox_clicked)
        
        # Footer thống kê
        stats_label = QLabel("Thành công: 0 | Thất bại: 0 | Chưa gửi: 0")
        
        # Thêm các thành phần vào layout
        right_layout.addWidget(self.account_table)
        self.stats_label = stats_label  # Store reference for update_send_stats
        right_layout.addWidget(stats_label)
        
        # Thêm các panel vào layout chính
        layout.addWidget(left_panel, 35)
        layout.addWidget(right_panel, 65) 

        self.load_accounts()  # Nạp tài khoản khi khởi tạo

        self.account_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.account_table.customContextMenuRequested.connect(self.show_context_menu)
        self.account_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        # 🔒 LOCK TABLE - Chỉ xem, không cho phép chỉnh sửa
        self.account_table.setEditTriggers(QTableWidget.NoEditTriggers)

        # Gán chức năng cho nút Load ở panel trái
        self.btn_load.clicked.connect(self.reload_usernames_data_file)

        # Gán chức năng cho nút Start và Stop
        self.btn_start.clicked.connect(self.send_message)
        self.btn_stop.clicked.connect(self.stop_sending)

        # Đọc cấu hình từ file nếu có
        self.settings_file = "messaging_settings.json"
        self.load_settings()
        # Kết nối sự kiện thay đổi để tự động lưu và validate
        self.thread_spin.valueChanged.connect(self._on_thread_spin_changed)
        self.error_spin.valueChanged.connect(self.save_settings)
        self.msg_count_spin.valueChanged.connect(self.save_settings)
        self.delay_min_spin.valueChanged.connect(self._on_delay_changed)
        self.delay_max_spin.valueChanged.connect(self._on_delay_changed)

    def open_or_create_data_file(self):
        import os
        import subprocess
        from PySide6.QtCore import QTimer
        data_file = "usernames_data.txt"
        if not os.path.exists(data_file):
            with open(data_file, "w", encoding="utf-8") as f:
                f.write("")
        # Mở file bằng notepad (Windows)
        try:
            self.notepad_proc = subprocess.Popen(["notepad.exe", data_file])
        except Exception as e:
            QMessageBox.warning(self, "Lỗi", f"Không thể mở file: {e}")
            return
        # Tạo QTimer kiểm tra notepad đã đóng chưa
        def check_notepad_closed():
            if self.notepad_proc.poll() is not None:
                # Notepad đã đóng, reload file
                self.reload_usernames_data_file()
                self.notepad_timer.stop()
        self.notepad_timer = QTimer(self)
        self.notepad_timer.timeout.connect(check_notepad_closed)
        self.notepad_timer.start(1000)  # Kiểm tra mỗi giây

    def reload_usernames_data_file(self):
        data_file = "usernames_data.txt"
        usernames = []
        errors = []
        if not os.path.exists(data_file):
            self.usernames = []
            self.username_stats_label.setText("Số lượng username: 0")
            return
        with open(data_file, 'r', encoding='utf-8') as f:
            for idx, line in enumerate(f):
                username = line.strip()
                if not username:
                    continue
                if ' ' in username or ',' in username or '\t' in username:
                    continue
                if username.count('@') > 0:
                    username = username.replace('@', '')
                if username:
                    usernames.append(username)
        self.usernames = usernames
        self.update_username_stats()
        if errors:
            QMessageBox.warning(self, "Cảnh báo file", "Một số dòng bị loại bỏ:\n" + '\n'.join(errors))

    def choose_username_file(self):
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        file_path, _ = QFileDialog.getOpenFileName(self, "Chọn file username.txt", "", "Text Files (*.txt)")
        if not file_path:
            return
        usernames = []
        errors = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for idx, line in enumerate(f):
                username = line.strip()
                if not username:
                    errors.append(f"Dòng {idx+1} trống.")
                    continue
                if ' ' in username or ',' in username or '\t' in username:
                    errors.append(f"Dòng {idx+1} chứa ký tự không hợp lệ: {username}")
                    continue
                if username.count('@') > 0:
                    username = username.replace('@', '')
                if username:
                    usernames.append(username)
        if not usernames:
            QMessageBox.warning(self, "Lỗi file", "File không có username hợp lệ!")
            self.usernames = []
            self.username_file_loaded = False
            self.username_stats_label.setText("Số lượng username: 0")
            return
        self.usernames = usernames
        self.username_file_loaded = True
        self.username_file_path = file_path
        self.last_username_file_error = errors
        self.update_username_stats()
        if errors:
            QMessageBox.warning(self, "Cảnh báo file", "Một số dòng bị loại bỏ:\n" + '\n'.join(errors))

    def update_username_stats(self):
        # Thống kê tổng số tài khoản đích hợp lệ đã tải lên
        count = len([u for u in self.usernames if u and isinstance(u, str)])
        self.username_stats_label.setText(f"Số lượng username: {count}")

    def filter_duplicate_usernames(self):
        if self.no_duplicate.isChecked() and self.usernames:
            unique_usernames = list(dict.fromkeys(self.usernames))
            self.usernames = unique_usernames
            self.duplicate_filtered = True
        else:
            self.duplicate_filtered = False
        self.update_username_stats()

    def choose_media_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Chọn ảnh hoặc video", "", "Media Files (*.png *.jpg *.jpeg *.mp4 *.mov *.avi)")
        if file_path:
            self.selected_media_path = file_path
            QMessageBox.information(self, "Đã chọn file", f"Đã chọn: {file_path}")
        else:
            self.selected_media_path = None

    def save_message_content(self):
        # Lưu nội dung vào bảng tin nhắn
        content = self.findChild(QTextEdit)
        if not content:
            return
        message = content.toPlainText().strip()
        media = self.selected_media_path or ""
        if not message and not media:
            QMessageBox.warning(self, "Thiếu nội dung", "Vui lòng nhập nội dung hoặc chọn ảnh/video!")
            return
        row = self.message_table.rowCount()
        self.message_table.insertRow(row)
        # Cột 0: checkbox nhỏ
        item_checkbox = QTableWidgetItem()
        item_checkbox.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        item_checkbox.setCheckState(Qt.Unchecked)
        self.message_table.setItem(row, 0, item_checkbox)
        self.message_table.setItem(row, 1, QTableWidgetItem(message))
        self.message_table.setItem(row, 2, QTableWidgetItem(media))
        # Reset input
        content.clear()
        self.selected_media_path = None
        self.save_message_templates()

    def closeEvent(self, event):
        self.save_settings()
        for driver in self.active_drivers:
            try:
                driver.quit()
            except:
                pass
        self.active_drivers.clear()
        super().closeEvent(event)

    def save_settings(self):
        settings = {
            "thread_spin": self.thread_spin.value(),
            "error_spin": self.error_spin.value(),
            "msg_count_spin": self.msg_count_spin.value(),
            "delay_min_spin": self.delay_min_spin.value(),
            "delay_max_spin": self.delay_max_spin.value()
        }
        try:
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(settings, f)
        except Exception as e:
            print(f"[WARN] Không thể lưu cấu hình tin nhắn: {e}")

    def load_settings(self):
        # Set default values
        self.thread_spin.setValue(1)
        self.error_spin.setValue(3)
        self.msg_count_spin.setValue(10)
        self.delay_min_spin.setValue(5)
        self.delay_max_spin.setValue(15)
        
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                    self.thread_spin.setValue(settings.get("thread_spin", 1))
                    self.error_spin.setValue(settings.get("error_spin", 3))
                    self.msg_count_spin.setValue(settings.get("msg_count_spin", 10))
                    self.delay_min_spin.setValue(settings.get("delay_min_spin", 5))
                    self.delay_max_spin.setValue(settings.get("delay_max_spin", 15))
        except Exception as e:
            print(f"[WARN] Không thể đọc cấu hình tin nhắn: {e}")
            
        # Validate settings
        self._validate_settings()

    def _validate_settings(self):
        """Validate and fix settings values"""
        # Ensure delay min is at least 3 seconds
        if self.delay_min_spin.value() < 3:
            self.delay_min_spin.setValue(3)
            
        # Ensure delay max is greater than delay min
        if self.delay_max_spin.value() <= self.delay_min_spin.value():
            self.delay_max_spin.setValue(self.delay_min_spin.value() + 5)
            
        # Ensure reasonable limits
        if self.thread_spin.value() > 5:
            self.thread_spin.setValue(5)
            QMessageBox.warning(self, "Cảnh báo", "Số luồng tối đa là 5 để tránh bị Instagram phát hiện!")
            
    def _on_thread_spin_changed(self):
        """Handle thread spin value changes"""
        if self.thread_spin.value() > 5:
            self.thread_spin.setValue(5)
            QMessageBox.warning(self, "Cảnh báo", "Số luồng tối đa là 5 để tránh bị Instagram phát hiện!")
        self.save_settings()
        
    def _on_delay_changed(self):
        """Handle delay spin value changes"""
        # Auto-adjust delay max if it's less than delay min
        if self.delay_max_spin.value() <= self.delay_min_spin.value():
            self.delay_max_spin.setValue(self.delay_min_spin.value() + 5)
        self.save_settings()

    def _validate_delay_spin(self):
        if self.delay_min_spin.value() < 3:
            QMessageBox.warning(self, "Cảnh báo", "Khoảng cách gửi tối thiểu nên là ít nhất 3 giây!")

    def show_context_menu(self, pos):
        index = self.account_table.indexAt(pos)
        context_row = index.row() if index.isValid() else None
        menu = MessagingContextMenu(self)
        menu.context_row = context_row
        menu.exec(self.account_table.viewport().mapToGlobal(pos))

    def load_folder_list_to_combo(self):
        self.category_combo.clear()
        self.category_combo.addItem("Tất cả")
        # Luôn load lại folder_map từ file để đảm bảo mới nhất
        import os, json
        folder_map_file = "data/folder_map.json"
        folder_map = {}
        if os.path.exists(folder_map_file):
            with open(folder_map_file, "r", encoding="utf-8") as f:
                try:
                    folder_map = json.load(f)
                except Exception:
                    folder_map = {}
        self.folder_map = folder_map
        if folder_map and "_FOLDER_SET_" in folder_map:
            for folder in folder_map["_FOLDER_SET_"]:
                if folder != "Tổng":
                    self.category_combo.addItem(folder)
        print(f"[DEBUG][MessagingTab] Đã tải danh sách thư mục vào combobox: {self.category_combo.count()} mục")

    def on_folder_changed(self):
        import json, os
        # Load lại dữ liệu mới nhất
        accounts = []
        folder_map = {}
        if os.path.exists("accounts.json"):
            with open("accounts.json", "r", encoding="utf-8") as f:
                try:
                    accounts = json.load(f)
                except Exception:
                    accounts = []
        if os.path.exists("data/folder_map.json"):
            with open("data/folder_map.json", "r", encoding="utf-8") as f:
                try:
                    folder_map = json.load(f)
                except Exception:
                    folder_map = {}
        self.accounts = accounts
        self.folder_map = folder_map
        selected_folder = self.category_combo.currentText()
        if selected_folder == "Tất cả":
            self.update_account_table(self.accounts)
        else:
            # Lọc username thuộc đúng thư mục
            filtered_accounts = [acc for acc in self.accounts if self.folder_map.get(acc.get("username"), "Tổng") == selected_folder]
            self.update_account_table(filtered_accounts)
        print(f"[DEBUG][MessagingTab] Đã lọc tài khoản theo thư mục: {selected_folder}")

    def on_folders_updated(self):
        """Handle when folders are updated in account management tab"""
        if self.account_tab:
            self.accounts = self.account_tab.accounts
            self.folder_map = self.account_tab.folder_map
            self.update_account_table()
            print("[DEBUG] MessagingTab synced accounts after folder update")

    def load_accounts(self):
        # Nạp toàn bộ tài khoản từ accounts.json, chỉ lấy tài khoản đã đăng nhập
        import os, json
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
            item = QTableWidgetItem()
            item.setData(CheckboxDelegate.CheckboxStateRole, acc.get("selected", False))
            self.account_table.setItem(i, 0, item)
            self.account_table.setItem(i, 1, QTableWidgetItem(str(i+1)))
            # Số điện thoại - hiển thị số điện thoại Telegram thật (cột 2)
            telegram_phone = acc.get("telegram_phone", "") or acc.get("phone_telegram", "") or acc.get("tg_phone", "") or acc.get("phone_number", "") or acc.get("phone", "")
            if not telegram_phone:
                # Fallback: nếu không có số điện thoại Telegram, hiển thị username (có thể là số điện thoại)
                telegram_phone = acc.get("username", "")
                if not telegram_phone:
                    telegram_phone = "Chưa có số điện thoại"
            self.account_table.setItem(i, 2, QTableWidgetItem(telegram_phone))
            # Mật khẩu 2FA (cột 3)
            telegram_2fa = acc.get("telegram_2fa", "") or acc.get("two_fa_password", "") or acc.get("password_2fa", "") or acc.get("twofa", "") or "Chưa có 2FA"
            self.account_table.setItem(i, 3, QTableWidgetItem(telegram_2fa))
            # Username - hiển thị username Telegram thật (cột 4)
            telegram_username = acc.get("telegram_username", "") or acc.get("username_telegram", "") or acc.get("tg_username", "") or ""
            # Đảm bảo có @ ở đầu nếu là username Telegram
            if telegram_username and not telegram_username.startswith("@"):
                telegram_username = "@" + telegram_username
            if not telegram_username:
                telegram_username = "Chưa có username"
            self.account_table.setItem(i, 4, QTableWidgetItem(telegram_username))
            # ID (cột 5)
            account_id = acc.get("telegram_id", "") or acc.get("id_telegram", "") or acc.get("tg_id", "") or acc.get("user_id", "") or "Chưa có ID"
            self.account_table.setItem(i, 5, QTableWidgetItem(account_id))
            self.account_table.setItem(i, 6, QTableWidgetItem(acc.get("status", "")))    # Trạng thái tài khoản
            self.account_table.setItem(i, 7, QTableWidgetItem(str(acc.get("success", ""))))  # Tin nhắn gửi
            self.account_table.setItem(i, 8, QTableWidgetItem(acc.get("state", "")))     # Chi tiết quá trình
            if "detail" in acc:
                # Giả sử cột "Chi tiết quá trình" là cột cuối cùng
                col = self.account_table.columnCount() - 1
                self.account_table.setItem(i, col, QTableWidgetItem(str(acc["detail"])))
        self.account_table.clearSelection()

    def on_checkbox_clicked(self, row, new_state):
        # Cập nhật trạng thái 'selected' trong dữ liệu gốc
        if 0 <= row < len(self.accounts):
            self.accounts[row]["selected"] = new_state

    def update_sender_status(self, username, state, success_count=None, detail=None):
        # Cập nhật trạng thái và số lượng thành công cho tài khoản gửi
        for row, acc in enumerate(self.accounts):
            if acc.get("username") == username:
                acc["state"] = state
                if success_count is not None:
                    acc["success"] = success_count
                if detail is not None:
                    acc["detail"] = detail
                break
        self.update_account_table()
        self.update_send_stats()

    def update_send_stats(self):
        # Thống kê tổng số tài khoản gửi: thành công, thất bại, chưa gửi
        success = sum(1 for acc in self.accounts if acc.get("success", 0) > 0)
        fail = sum(1 for acc in self.accounts if str(acc.get("state", "")).lower() in ["lỗi", "checkpoint", "die"])
        not_sent = sum(1 for acc in self.accounts if acc.get("success", 0) == 0 and str(acc.get("state", "")).lower() not in ["lỗi", "checkpoint", "die"])
        if hasattr(self, 'stats_label'):
            self.stats_label.setText(f"Thành công: {success} | Thất bại: {fail} | Chưa gửi: {not_sent}")

    def send_message(self):
        """Start sending messages using threading"""
        if self.is_sending:
            QMessageBox.warning(self, "Đang gửi", "Đang trong quá trình gửi tin nhắn. Vui lòng đợi hoặc nhấn Stop để dừng.")
            return
            
        sender_accounts = [acc for acc in self.accounts if acc.get("selected")]
        if not sender_accounts:
            QMessageBox.warning(self, "Thiếu tài khoản gửi", "Vui lòng tick chọn ít nhất một tài khoản gửi!")
            return
            
        if not self.usernames:
            QMessageBox.warning(self, "Thiếu username đích", "Vui lòng nhập danh sách username đích!")
            return
            
        selected_messages = []
        for row in range(self.message_table.rowCount()):
            item = self.message_table.item(row, 0)
            if item and item.checkState() == Qt.Checked:
                content = self.message_table.item(row, 1).text() if self.message_table.item(row, 1) else ""
                media = self.message_table.item(row, 2).text() if self.message_table.item(row, 2) else ""
                selected_messages.append((content, media))
                
        if not selected_messages:
            QMessageBox.warning(self, "Thiếu nội dung", "Vui lòng tick chọn ít nhất một nội dung tin nhắn!")
            return
        
        # Prepare settings
        settings = {
            'max_success': self.msg_count_spin.value(),
            'max_error': self.error_spin.value(),
            'delay_min': self.delay_min_spin.value(),
            'delay_max': self.delay_max_spin.value()
        }
        
        # Reset account states
        for acc in sender_accounts:
            acc["success"] = 0
            acc["state"] = "Chuẩn bị"
        
        self.update_account_table()
        self.update_send_stats()
        
        # Start sender thread
        self.sender_thread = MessageSenderThread(
            sender_accounts, self.usernames, selected_messages, 
            settings, self.account_tab, self
        )
        
        # Connect signals
        self.sender_thread.progress_updated.connect(self.on_progress_updated)
        self.sender_thread.finished.connect(self.on_sending_finished)
        self.sender_thread.error_occurred.connect(self.on_error_occurred)
        
        # Update UI state
        self.is_sending = True
        self.btn_start.setText("Đang gửi...")
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        
        # Start thread
        self.sender_thread.start()
        
    def stop_sending(self):
        """Stop the message sending process"""
        if self.sender_thread and self.sender_thread.isRunning():
            self.sender_thread.stop()
            self.sender_thread.wait(5000)  # Wait up to 5 seconds for thread to finish
            
            if self.sender_thread.isRunning():
                self.sender_thread.terminate()
                self.sender_thread.wait()
                
        self.on_sending_finished()
        QMessageBox.information(self, "Đã dừng", "Đã dừng quá trình gửi tin nhắn.")
        
    def on_progress_updated(self, username: str, status: str, success_count: int, detail: str):
        """Handle progress updates from sender thread"""
        self.update_sender_status(username, status, success_count, detail)
        
    def on_sending_finished(self):
        """Handle when sending is finished"""
        self.is_sending = False
        self.btn_start.setText("Start")
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(True)
        
        if self.sender_thread:
            self.sender_thread.deleteLater()
            self.sender_thread = None
            
        self.update_send_stats()
        
    def on_error_occurred(self, username: str, error_message: str):
        """Handle errors from sender thread"""
        print(f"[ERROR] {username}: {error_message}")
        # Could show error in status bar or log

    def load_recipients(self):
        """Load recipients list from file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Chọn file danh sách người nhận", 
            "", 
            "Text Files (*.txt);;CSV Files (*.csv);;All Files (*)"
        )
        if not file_path:
            return
            
        try:
            recipients = []
            if file_path.endswith('.csv'):
                import csv
                with open(file_path, 'r', encoding='utf-8', newline='') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if row and row[0].strip():  # Take first column as username
                            recipients.append(row[0].strip())
            else:
                # Text file
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        username = line.strip()
                        if username and not username.startswith('#'):  # Skip comments
                            # Clean username (remove @ if present)
                            if username.startswith('@'):
                                username = username[1:]
                            if username:
                                recipients.append(username)
            
            if not recipients:
                QMessageBox.warning(self, "Lỗi file", "File không có username hợp lệ!")
                return
                
            # Update usernames list
            self.usernames = recipients
            self.username_file_loaded = True
            self.username_file_path = file_path
            self.update_username_stats()
            
            QMessageBox.information(
                self, 
                "Tải thành công", 
                f"Đã tải {len(recipients)} người nhận từ file:\n{file_path}"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể đọc file:\n{str(e)}")

    def export_recipients(self):
        """Export recipients list to file"""
        import time
        if not self.usernames:
            QMessageBox.warning(self, "Không có dữ liệu", "Chưa có danh sách người nhận để xuất!")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Xuất danh sách người nhận",
            f"recipients_{time.strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt);;CSV Files (*.csv);;All Files (*)"
        )
        
        if not file_path:
            return
            
        try:
            if file_path.endswith('.csv'):
                import csv
                with open(file_path, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Username'])  # Header
                    for username in self.usernames:
                        writer.writerow([username])
            else:
                # Text file
                with open(file_path, 'w', encoding='utf-8') as f:
                    for username in self.usernames:
                        f.write(f"{username}\n")
                        
            QMessageBox.information(
                self,
                "Xuất thành công",
                f"Đã xuất {len(self.usernames)} người nhận ra file:\n{file_path}"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể ghi file:\n{str(e)}")

    def clear_recipients(self):
        """Clear recipients list"""
        if not self.usernames:
            QMessageBox.information(self, "Thông báo", "Danh sách người nhận đã trống!")
            return
            
        reply = QMessageBox.question(
            self,
            "Xác nhận xóa",
            f"Bạn có chắc muốn xóa {len(self.usernames)} người nhận?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.usernames.clear()
            self.username_file_loaded = False
            self.username_file_path = None
            self.update_username_stats()
            
            QMessageBox.information(self, "Xóa thành công", "Đã xóa danh sách người nhận!")
        
    def closeEvent(self, event):
        """Properly cleanup when closing"""
        # Stop sending thread if running
        if self.sender_thread and self.sender_thread.isRunning():
            self.sender_thread.stop()
            self.sender_thread.wait(3000)
            if self.sender_thread.isRunning():
                self.sender_thread.terminate()
                
        # Save settings
        self.save_settings()
        
        # Cleanup drivers
        for driver in self.active_drivers:
            try:
                if hasattr(driver, 'quit'):
                    driver.quit()
            except:
                pass
        self.active_drivers.clear()
        
        super().closeEvent(event)

    def show_message_context_menu(self, pos):
        index = self.message_table.indexAt(pos)
        if not index.isValid():
            return
        menu = QMenu(self)
        action_select = menu.addAction("Chọn bài viết")
        action_delete = menu.addAction("Xóa nội dung")
        action_edit = menu.addAction("Chỉnh sửa nội dung hoặc link")
        action = menu.exec(self.message_table.viewport().mapToGlobal(pos))
        selected_rows = set(idx.row() for idx in self.message_table.selectionModel().selectedRows())
        row = index.row()
        if action == action_select:
            # Tick chọn các dòng đang bôi đen
            for r in selected_rows:
                item_checkbox = self.message_table.item(r, 0)
                if item_checkbox:
                    item_checkbox.setCheckState(Qt.Checked)
            self.save_message_templates()
        elif action == action_delete:
            self.message_table.removeRow(row)
            self.save_message_templates()
        elif action == action_edit:
            old_content = self.message_table.item(row, 1).text() if self.message_table.item(row, 1) else ""
            old_link = self.message_table.item(row, 2).text() if self.message_table.item(row, 2) else ""
            new_content, ok1 = QInputDialog.getText(self, "Chỉnh sửa nội dung", "Nội dung:", QLineEdit.EchoMode.Normal, old_content)
            if not ok1:
                return
            new_link, ok2 = QInputDialog.getText(self, "Chỉnh sửa link ảnh/video", "Link ảnh/video:", QLineEdit.EchoMode.Normal, old_link)
            if not ok2:
                return
            self.message_table.setItem(row, 1, QTableWidgetItem(new_content))
            self.message_table.setItem(row, 2, QTableWidgetItem(new_link))
            self.save_message_templates()
        
    def on_message_item_changed(self, item):
        """Auto-save when message table items change (especially checkboxes)"""
        if item and item.column() == 0:  # Only save when checkbox column changes
            self.save_message_templates()

    def load_message_templates(self):
        import os
        file_path = "message_templates.json"
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    templates = json.load(f)
                except Exception:
                    templates = []
            self.message_table.setRowCount(0)
            for tpl in templates:
                row = self.message_table.rowCount()
                self.message_table.insertRow(row)
                # Cột 0: checkbox với trạng thái được lưu
                item_checkbox = QTableWidgetItem()
                item_checkbox.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                # Khôi phục trạng thái checkbox từ file
                is_selected = tpl.get("selected", False)
                item_checkbox.setCheckState(Qt.Checked if is_selected else Qt.Unchecked)
                self.message_table.setItem(row, 0, item_checkbox)
                self.message_table.setItem(row, 1, QTableWidgetItem(tpl.get("content", "")))
                self.message_table.setItem(row, 2, QTableWidgetItem(tpl.get("media", "")))
            print(f"[DEBUG] Đã tải {len(templates)} mẫu tin nhắn với trạng thái checkbox")

    def save_message_templates(self):
        templates = []
        for row in range(self.message_table.rowCount()):
            content = self.message_table.item(row, 1).text() if self.message_table.item(row, 1) else ""
            media = self.message_table.item(row, 2).text() if self.message_table.item(row, 2) else ""
            # Lưu trạng thái checkbox
            checkbox_item = self.message_table.item(row, 0)
            is_selected = checkbox_item.checkState() == Qt.Checked if checkbox_item else False
            templates.append({
                "content": content, 
                "media": media,
                "selected": is_selected
            })
        with open("message_templates.json", "w", encoding="utf-8") as f:
            json.dump(templates, f, ensure_ascii=False, indent=2)
        print(f"[DEBUG] Đã lưu {len(templates)} mẫu tin nhắn với trạng thái checkbox")

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    window = MessagingTab()
    window.show()
    sys.exit(app.exec()) 