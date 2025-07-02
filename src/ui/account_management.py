import os
import sys

# Apply blinker patch before importing selenium-wire
try:
    # Add project root to path if needed
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    import blinker_patch
except Exception as e:
    print(f"[WARN] Could not apply blinker patch in account_management: {e}")

import time
import random
import json
import threading
import queue
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Union
import traceback  # Thêm import này
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QLineEdit, QTextEdit, QFileDialog, QMessageBox,
    QProgressBar, QComboBox, QCheckBox, QSpinBox, QGroupBox,
    QScrollArea, QFrame, QSplitter, QTabWidget, QApplication,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView, QSizePolicy, QStyledItemDelegate, QMenu, QProgressDialog, QInputDialog, QSlider, QDialog)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSize, QModelIndex, QRect, QEvent, QMetaObject, Slot
from PySide6.QtGui import QFont, QIcon, QPixmap, QColor, QPalette, QPainter, QPen, QGuiApplication, QAction
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from seleniumwire import webdriver as wire_webdriver
from seleniumwire.utils import decode
from twocaptcha import TwoCaptcha
from src.ui.utils import random_delay, wait_for_element, wait_for_element_clickable, retry_operation
from src.ui.context_menus import AccountContextMenu
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium.webdriver.common.keys import Keys

class CheckboxDelegate(QStyledItemDelegate):
    # Sử dụng một UserRole tùy chỉnh để tránh xung đột với Qt.CheckStateRole mặc định
    CheckboxStateRole = Qt.UserRole + 1
    checkbox_clicked = Signal(int, bool)  # Thêm tín hiệu mới: row, new_state

    def paint(self, painter: QPainter, option, index: QModelIndex):
        super().paint(painter, option, index)  # Gọi phương thức paint của lớp cha để vẽ nền mặc định (bao gồm cả màu chọn)
        # Lấy trạng thái checkbox từ model bằng UserRole tùy chỉnh
        check_state_data = index.data(self.CheckboxStateRole)
        is_checked = bool(check_state_data)  # Convert to boolean

        # Tính toán vị trí và kích thước cho checkbox 15x15px, căn giữa trong ô
        checkbox_size = 14 
        rect = option.rect
        x = rect.x() + (rect.width() - checkbox_size) // 2
        y = rect.y() + (rect.height() - checkbox_size) // 2
        checkbox_rect = QRect(x, y, checkbox_size, checkbox_size)

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        # Vẽ nền và viền của checkbox
        if is_checked:
            painter.setBrush(QColor("#1976D2"))  # Màu xanh lam khi chọn
            painter.setPen(QColor("#1976D2"))
        else:
            painter.setBrush(Qt.white)  # Nền trắng khi không chọn
            painter.setPen(QColor("#CCCCCC"))  # Viền xám khi không chọn

        painter.drawRoundedRect(checkbox_rect, 2, 2)  # Vẽ hình vuông bo góc

        # Vẽ dấu tích nếu đã chọn
        if is_checked:
            # Vẽ dấu tích trắng đơn giản
            painter.setPen(QPen(Qt.white, 2))  # Bút màu trắng, độ dày 2
            # Đường chéo thứ nhất của dấu tích (từ dưới lên)
            painter.drawLine(x + 3, y + 7, x + 6, y + 10)
            # Đường chéo thứ hai của dấu tích (từ điểm giữa lên trên)
            painter.drawLine(x + 6, y + 10, x + 12, y + 4)

        painter.restore()

    def editorEvent(self, event, model, option, index: QModelIndex):
        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            # Lấy trạng thái hiện tại từ UserRole tùy chỉnh
            current_state = index.data(self.CheckboxStateRole)
            new_state = not bool(current_state)

            # Cập nhật trạng thái trong model bằng UserRole tùy chỉnh
            model.setData(index, new_state, self.CheckboxStateRole)

            # Phát tín hiệu khi checkbox được click
            self.checkbox_clicked.emit(index.row(), new_state)
            
            # Force repaint để cập nhật giao diện ngay lập tức
            if hasattr(model, 'parent') and hasattr(model.parent(), 'viewport'):
                model.parent().viewport().update()
            
            return True  # Đã xử lý sự kiện
        return super().editorEvent(event, model, option, index)  # Quan trọng: Gọi super() thay vì return False

class CheckableHeaderView(QHeaderView):
    toggleAllCheckboxes = Signal(bool)  # Tín hiệu để thông báo khi checkbox trong header được toggle

    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self._checked = False  # Trạng thái của checkbox trong header
        self.setSectionsClickable(True)

    def paintSection(self, painter, rect, logicalIndex):
        # Luôn vẽ nền/viền 3D mặc định trước
        super().paintSection(painter, rect, logicalIndex)
        if logicalIndex == 0:  # Cột đầu tiên là cột checkbox
            checkbox_size = 14  # Kích thước của checkbox
            x = rect.x() + (rect.width() - checkbox_size) // 2
            y = rect.y() + (rect.height() - checkbox_size) // 2
            checkbox_rect = QRect(x, y, checkbox_size, checkbox_size)

            painter.save()
            painter.setRenderHint(QPainter.Antialiasing)
            # Vẽ nền và viền của checkbox
            if self._checked:
                painter.setBrush(QColor("#1976D2"))
                painter.setPen(QColor("#1976D2"))
            else:
                painter.setBrush(Qt.white)
                painter.setPen(QColor("#CCCCCC"))
            painter.drawRoundedRect(checkbox_rect, 2, 2)
            # Vẽ dấu tích nếu đã chọn
            if self._checked:
                painter.setPen(QPen(Qt.white, 2))
                painter.drawLine(x + 3, y + 7, x + 6, y + 10)
                painter.drawLine(x + 6, y + 10, x + 12, y + 4)
            painter.restore()
        else:
            # Gọi phương thức gốc để vẽ phần còn lại của header cho các cột khác
            super().paintSection(painter, rect, logicalIndex)

    def mousePressEvent(self, event):
        if self.logicalIndexAt(event.pos()) == 0 and event.button() == Qt.LeftButton:  # Chỉ xử lý click trên cột đầu tiên
            self._checked = not self._checked
            self.toggleAllCheckboxes.emit(self._checked)
            self.viewport().update()  # Cập nhật lại giao diện header để hiển thị trạng thái checkbox mới
            event.accept()  # Chấp nhận sự kiện để ngăn xử lý mặc định
        else:
            super().mousePressEvent(event)


class AccountManagementTab(QWidget):
    # Định nghĩa tín hiệu để thông báo khi dữ liệu proxy được cập nhật
    proxy_updated = Signal()
    # Thêm signal để cập nhật trạng thái từ thread
    status_updated = Signal(str, str)  # username, status
    # ⭐ THÊM TÍN HIỆU ĐỒNG BỘ FOLDERS
    folders_updated = Signal()

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ]

    LANGUAGES = [
        "en-US,en;q=0.9",  # English (United States), English
        "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",  # Vietnamese, English
        "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",  # French, English
        "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",  # German, English
        "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7"  # Japanese, English
    ]

    PROXY_USAGE_THRESHOLD = 5  # Ngưỡng sử dụng proxy trước khi xoay vòng
    RECAPTCHA_RETRY_COUNT = 3  # Số lần thử lại khi gặp reCAPTCHA
    RECAPTCHA_WAIT_TIME = 10  # Thời gian chờ giữa các lần thử (giây)

    def __init__(self, proxy_tab_instance=None, parent=None):
        super().__init__(parent)
        self.proxy_tab = proxy_tab_instance
        self.accounts_file = os.path.join(os.getcwd(), "accounts.json")
        self.folder_map_file = os.path.join(os.getcwd(), "data", "folder_map.json")
        
        # Initialize empty lists/dicts
        self.accounts = []
        self.folder_map = {}
        self.active_drivers = []
        
        # Load data
        self.accounts = self.load_accounts()
        self.folder_map = self.load_folder_map()
        
        # Initialize UI
        self.init_ui()
        
        # Update UI with loaded data
        self.update_account_table()
        self.update_stats()
        
        print(f"[DEBUG] AccountManagementTab initialized with {len(self.accounts)} accounts")
        
        # Đọc trạng thái sử dụng proxy từ file (nếu có)
        self.settings_file = "account_settings.json"
        self.use_proxy = True
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                    self.use_proxy = settings.get("use_proxy", True)
        except Exception as e:
            print(f"[WARN] Không thể đọc trạng thái sử dụng proxy: {e}")
        # Thay thế checkbox bằng drag switch (QSlider)
        self.proxy_switch_layout = QHBoxLayout()
        self.proxy_switch_label = QLabel("Proxy: OFF")
        self.proxy_switch_slider = QSlider(Qt.Horizontal)
        self.proxy_switch_slider.setMinimum(0)
        self.proxy_switch_slider.setMaximum(1)
        self.proxy_switch_slider.setSingleStep(1)
        self.proxy_switch_slider.setFixedWidth(80)
        self.proxy_switch_slider.setValue(1 if self.use_proxy else 0)
        self.proxy_switch_layout.addWidget(self.proxy_switch_label)
        self.proxy_switch_layout.addWidget(self.proxy_switch_slider)
        self.sidebar_layout.addLayout(self.proxy_switch_layout)
        self.proxy_switch_slider.valueChanged.connect(self.on_proxy_switch_changed)
        self.update_proxy_switch_label()
        # Kết nối signal status_updated để cập nhật từ thread
        self.status_updated.connect(self.on_status_updated)

    def init_driver(self, proxy=None, username=None):
        """⚡ SIÊU TỐI ƯU: Khởi tạo Chrome driver với tốc độ cao nhất"""
        try:
            options = webdriver.ChromeOptions()
            
            # ⚡ TỐI ƯU: Các argument cơ bản cho tốc độ cao
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-notifications')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-gpu')  # Tắt GPU acceleration để nhanh hơn
            options.add_argument('--disable-web-security')
            options.add_argument('--disable-features=VizDisplayCompositor')
            options.add_argument('--disable-background-timer-throttling')
            options.add_argument('--disable-renderer-backgrounding')
            options.add_argument('--disable-backgrounding-occluded-windows')
            options.add_argument('--disable-ipc-flooding-protection')
            
            # ⚡ TỐI ƯU: Giảm memory và tăng tốc
            options.add_argument('--memory-pressure-off')
            options.add_argument('--max_old_space_size=4096')
            
            # Thêm proxy nếu có
            if proxy: 
                options.add_argument(f'--proxy-server={proxy}')
            
            # Thêm user data dir nếu có username
            if username:
                user_data_dir = os.path.join("sessions", username)
                os.makedirs(user_data_dir, exist_ok=True)
                options.add_argument(f'--user-data-dir={user_data_dir}')
            
            # ⚡ SIÊU TỐI ƯU: Khởi tạo driver với timeout ngắn
            driver = webdriver.Chrome(options=options)
            
            # ⚡ TỐI ƯU: Thiết lập timeout ngắn hơn cho tốc độ
            driver.set_page_load_timeout(15)  # Giảm từ 30s xuống 15s
            driver.implicitly_wait(5)  # Giảm từ 10s xuống 5s
            
            return driver
            
        except Exception as e:
            print(f"[ERROR] Không thể khởi tạo driver: {e}")
            return None

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        main_layout.setSpacing(0)  # Remove spacing

        # Sidebar on the left (15%)
        sidebar_widget = QWidget()
        self.sidebar_layout = QVBoxLayout(sidebar_widget)
        self.sidebar_layout.setContentsMargins(10, 10, 10, 10)
        self.sidebar_layout.setSpacing(10)

        # Functions
        btn_add_account = QPushButton("Thêm tài khoản")
        btn_add_account.clicked.connect(self.login_telegram)
        self.sidebar_layout.addWidget(btn_add_account)

        btn_load_sessions = QPushButton("LOAD SESSION")
        btn_load_sessions.clicked.connect(self.load_sessions)
        self.sidebar_layout.addWidget(btn_load_sessions)

        btn_add_folder = QPushButton("Quản lý thư mục")
        btn_add_folder.clicked.connect(self.open_folder_manager)
        self.sidebar_layout.addWidget(btn_add_folder)

        self.sidebar_layout.addStretch()  # Add stretch to push buttons to top

        main_layout.addWidget(sidebar_widget, stretch=15)

        # Right panel (85%)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        right_layout.setSpacing(0)  # Remove spacing

        # Toolbar placed in QFrame for alignment
        toolbar_frame = QFrame()
        toolbar_frame.setStyleSheet("QFrame { padding-top: 6px; padding-bottom: 6px; }\n")
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setSpacing(8)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)

        # ComboBox for Category
        self.category_combo = QComboBox()
        self.category_combo.addItem("Tất cả")
        self.load_folder_list_to_combo()  # Load folders into combobox
        self.category_combo.currentIndexChanged.connect(self.on_folder_changed)
        self.category_combo.setFixedSize(200, 30)  # Kích thước 200x35px
        toolbar_layout.addWidget(self.category_combo)

        # Đẩy các widget trước sang trái
        toolbar_layout.addStretch(1)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Tìm kiếm tài khoản...")
        self.search_input.textChanged.connect(self.filter_accounts)
        self.search_input.setFixedWidth(180)
        self.search_input.setFixedHeight(35)
        toolbar_layout.addWidget(self.search_input)

        btn_search = QPushButton("🔍")
        btn_search.clicked.connect(lambda: self.filter_accounts(self.search_input.text()))
        btn_search.setFixedSize(50, 35)
        btn_search.setProperty("role", "main")
        btn_search.setProperty("color", "blue")
        toolbar_layout.addWidget(btn_search)

        right_layout.addWidget(toolbar_frame)

        # Account table
        self.account_table = QTableWidget()
        self.account_table.setColumnCount(12)  # ⭐ Tăng lên 12 cột để thêm Username column
        self.account_table.setHorizontalHeaderLabels([
            "", "STT", "Số điện thoại", "Mật khẩu 2FA", "Username", "Trạng thái", 
            "Proxy", "Proxy VV", "Trạng thái Proxy", "Follower", "Following", "Hành động cuối"
        ])

        # Thiết lập delegate cho cột "Chọn"
        self.checkbox_delegate = CheckboxDelegate(self)
        self.account_table.setItemDelegateForColumn(0, self.checkbox_delegate)
        # Kết nối tín hiệu checkbox_clicked từ delegate
        self.checkbox_delegate.checkbox_clicked.connect(self.on_checkbox_clicked)

        # Thay thế QHeaderView mặc định bằng CheckableHeaderView
        self.header_checkbox = CheckableHeaderView(Qt.Horizontal, self.account_table)
        self.account_table.setHorizontalHeader(self.header_checkbox)
        header = self.header_checkbox  # Gán lại biến header để các dòng code sau vẫn sử dụng được

        header.setSectionResizeMode(0, QHeaderView.Fixed)  # Cột "Chọn"
        self.account_table.setColumnWidth(0, 29)
        header.setSectionResizeMode(1, QHeaderView.Fixed)  # Cột "STT"
        self.account_table.setColumnWidth(1, 29)  # Đặt chiều rộng cột STT thành 29px
        header.setSectionResizeMode(2, QHeaderView.Fixed)  # Cột "Số điện thoại" - Chuyển về Fixed
        self.account_table.setColumnWidth(2, 130)  # Đặt chiều rộng cố định (giảm để có chỗ cho Username)
        header.setSectionResizeMode(3, QHeaderView.Fixed)  # Cột "Mật khẩu 2FA" - Chuyển về Fixed
        self.account_table.setColumnWidth(3, 100)  # Đặt chiều rộng cố định (giảm để có chỗ cho Username)
        header.setSectionResizeMode(4, QHeaderView.Fixed)  # Cột "Username" - NEW
        self.account_table.setColumnWidth(4, 120)  # Username column width
        header.setSectionResizeMode(5, QHeaderView.Fixed)  # Cột "Trạng thái"
        self.account_table.setColumnWidth(5, 120)  # Giữ nguyên chiều rộng
        header.setSectionResizeMode(6, QHeaderView.Fixed)  # Cột "Proxy" - Chuyển về Fixed
        self.account_table.setColumnWidth(6, 130)  # Đặt chiều rộng cố định
        header.setSectionResizeMode(7, QHeaderView.Fixed)  # ⭐ Cột "Permanent Proxy"
        self.account_table.setColumnWidth(7, 100)  # Proxy VV - chiều rộng giảm
        header.setSectionResizeMode(8, QHeaderView.Fixed)  # Cột "Trạng thái Proxy"
        self.account_table.setColumnWidth(8, 100)  # Giảm chiều rộng
        header.setSectionResizeMode(9, QHeaderView.Fixed)  # Cột "Follower"
        self.account_table.setColumnWidth(9, 70)  # Giảm chiều rộng
        header.setSectionResizeMode(10, QHeaderView.Fixed)  # Cột "Following"
        self.account_table.setColumnWidth(10, 70)  # Giảm chiều rộng
        header.setSectionResizeMode(11, QHeaderView.Stretch)  # Cột "Hành động cuối" - Giữ nguyên Stretch
        self.account_table.verticalHeader().setDefaultSectionSize(40)
        self.account_table.horizontalHeader().setFixedHeight(40)

        # Đảm bảo cột cuối cùng kéo giãn để hiển thị đầy đủ nội dung
        header.setStretchLastSection(True)

        # Thiết lập căn lề cho các tiêu đề cột
        self.account_table.horizontalHeader().setDefaultAlignment(Qt.AlignHCenter | Qt.AlignVCenter)

        self.account_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        # 🔒 LOCK TABLE - Chỉ xem, không cho phép chỉnh sửa
        self.account_table.setEditTriggers(QTableWidget.NoEditTriggers)  # Disable editing
        self.account_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.account_table.customContextMenuRequested.connect(self.show_context_menu)
        self.account_table.itemChanged.connect(self.handle_item_changed)  # Connect itemChanged signal
        self.account_table.verticalHeader().setVisible(False)  # Ẩn cột số thứ tự bên trái
        self.account_table.itemDoubleClicked.connect(self.on_table_item_double_clicked)  # Connect double click signal

        right_layout.addWidget(self.account_table)
        # Thêm label thống kê dưới bảng tài khoản (tách riêng)
        self.stats_label = QLabel()
        self.stats_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.stats_label.setStyleSheet("font-size: 15px; font-weight: bold; padding: 8px 12px;")
        right_layout.addWidget(self.stats_label)
        main_layout.addWidget(right_panel, stretch=85)

        # Kết nối tín hiệu toggleAllCheckboxes từ CheckableHeaderView
        self.header_checkbox.toggleAllCheckboxes.connect(self.toggle_all_accounts_selection)

    def load_accounts(self):
        if os.path.exists(self.accounts_file):
            try:
                with open(self.accounts_file, 'r', encoding='utf-8') as f:
                    accounts_data = json.load(f)
                    # ⭐ MIGRATION: Đảm bảo mỗi tài khoản có các trường mới
                    updated = False
                    for account in accounts_data:
                        # Legacy field: proxy_status
                        if "proxy_status" not in account:
                            account["proxy_status"] = "Chưa kiểm tra"
                            updated = True
                        # ⭐ NEW FIELD: permanent_proxy 
                        if "permanent_proxy" not in account:
                            account["permanent_proxy"] = ""
                            updated = True
                        # ⭐ NEW FIELD: phone (fallback to username)
                        if "phone" not in account:
                            account["phone"] = account.get("username", "")
                            updated = True
                        # ⭐ NEW FIELD: two_fa_password
                        if "two_fa_password" not in account:
                            account["two_fa_password"] = ""
                            updated = True
                        # ⭐ NEW FIELD: telegram_username
                        if "telegram_username" not in account:
                            account["telegram_username"] = ""
                            updated = True
                        # ⭐ ENSURE: selected field exists
                        if "selected" not in account:
                            account["selected"] = False
                            updated = True
                        
                        if updated:
                            print(f"[DEBUG] Migrated account {account.get('username', 'Unknown')} with new fields")
                    
                    # Lưu lại nếu có migration
                    if updated:
                        print(f"[DEBUG] Migration completed for {len(accounts_data)} accounts")
                        # Lưu ngay lập tức với data mới
                        try:
                            with open(self.accounts_file, 'w', encoding='utf-8') as f:
                                json.dump(accounts_data, f, indent=4, ensure_ascii=False)
                            print("[INFO] Migrated accounts data saved successfully.")
                        except Exception as e:
                            print(f"[ERROR] Failed to save migrated accounts: {e}")
                    
                    return accounts_data
            except json.JSONDecodeError:
                print("[ERROR] Lỗi đọc file accounts.json. File có thể bị hỏng.")
                return []
        return []

    def load_folder_map(self):
        """Load folder mapping data from file"""
        if os.path.exists(self.folder_map_file):
            try:
                with open(self.folder_map_file, 'r', encoding='utf-8') as f:
                    folder_data = json.load(f)
                    print(f"[DEBUG] Loaded folder map with {len(folder_data)} entries")
                    return folder_data
            except json.JSONDecodeError:
                print("[ERROR] Lỗi đọc file folder_map.json. File có thể bị hỏng.")
                return {}
            except Exception as e:
                print(f"[ERROR] Lỗi khi đọc folder map: {e}")
                return {}
        else:
            print("[DEBUG] Folder map file không tồn tại, tạo mới")
            # Tạo folder map mặc định
            default_folder_map = {
                "_FOLDER_SET_": ["Tổng"]
            }
            try:
                # Tạo thư mục data nếu chưa có
                os.makedirs(os.path.dirname(self.folder_map_file), exist_ok=True)
                with open(self.folder_map_file, 'w', encoding='utf-8') as f:
                    json.dump(default_folder_map, f, indent=4, ensure_ascii=False)
                print("[INFO] Đã tạo folder map mặc định")
            except Exception as e:
                print(f"[ERROR] Không thể tạo folder map mặc định: {e}")
            return default_folder_map

    def save_accounts(self):
        if hasattr(self, 'accounts_file') and self.accounts_file:
            try:
                # Đảm bảo thư mục tồn tại
                accounts_dir = os.path.dirname(self.accounts_file)
                if accounts_dir and not os.path.exists(accounts_dir):
                    os.makedirs(accounts_dir, exist_ok=True)
                
                with open(self.accounts_file, 'w', encoding='utf-8') as f:
                    json.dump(self.accounts, f, indent=4, ensure_ascii=False)
                print(f"[INFO] Accounts đã được lưu vào: {self.accounts_file}")
            except Exception as e:
                print(f"[ERROR] Lỗi khi lưu accounts vào {self.accounts_file}: {e}")
                # Fallback: lưu vào file backup
                try:
                    backup_file = "accounts_backup.json"
                    with open(backup_file, 'w', encoding='utf-8') as f:
                        json.dump(self.accounts, f, indent=4, ensure_ascii=False)
                    print(f"[INFO] Đã lưu backup vào: {backup_file}")
                except Exception as backup_error:
                    print(f"[ERROR] Không thể lưu backup: {backup_error}")

    def save_folder_map(self):
        if hasattr(self, 'folder_map_file'):
            try:
                # Tạo thư mục data nếu chưa có
                os.makedirs(os.path.dirname(self.folder_map_file), exist_ok=True)
                with open(self.folder_map_file, 'w', encoding='utf-8') as f:
                    json.dump(self.folder_map, f, indent=4, ensure_ascii=False)
                print("[INFO] Folder map đã được lưu.")
            except Exception as e:
                print(f"[ERROR] Lỗi khi lưu folder map: {e}")

    def load_folder_list_to_combo(self):
        """Load folder list to combo box"""
        self.category_combo.clear()
        self.category_combo.addItem("Tất cả")
        
        if hasattr(self, 'folder_map') and self.folder_map:
            folder_set = self.folder_map.get("_FOLDER_SET_", ["Tổng"])
            for folder in folder_set:
                if folder != "Tổng":
                    self.category_combo.addItem(folder)
        print(f"[DEBUG] Đã tải {self.category_combo.count()} folders vào combo box")

    def on_folder_changed(self):
        """Handle folder selection change"""
        selected_folder = self.category_combo.currentText()
        if selected_folder == "Tất cả":
            self.update_account_table(self.accounts)
        else:
            # Filter accounts by folder
            filtered_accounts = []
            for acc in self.accounts:
                username = acc.get("username", "")
                account_folder = self.folder_map.get(username, "Tổng")
                if account_folder == selected_folder:
                    filtered_accounts.append(acc)
            self.update_account_table(filtered_accounts)
        print(f"[DEBUG] Filtered accounts by folder: {selected_folder}")

    def load_sessions(self):
        """Load file .session với validation - chỉ load session hợp lệ"""
        try:
            sessions_dir = "sessions"
            if not os.path.exists(sessions_dir):
                QMessageBox.warning(
                    self, "Cảnh báo", 
                    f"Thư mục '{sessions_dir}' không tồn tại!\n\nVui lòng tạo thư mục và đặt các file .session vào đó."
                )
                return
            
            # Tìm tất cả file .session
            session_files = []
            for file in os.listdir(sessions_dir):
                if file.endswith('.session'):
                    session_files.append(file)
            
            if not session_files:
                QMessageBox.information(
                    self, "Thông báo", 
                    f"Không tìm thấy file .session nào trong thư mục '{sessions_dir}'!"
                )
                return
            
            # Tạo progress dialog
            progress = QProgressDialog("Đang kiểm tra và load session files...", "Hủy", 0, len(session_files), self)
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            
            # Tạo danh sách tài khoản từ session files HỢP LỆ
            loaded_accounts = []
            existing_usernames = {acc.get('username', '') for acc in self.accounts}
            
            valid_sessions = 0
            invalid_sessions = 0
            skipped_existing = 0
            
            for i, session_file in enumerate(session_files):
                if progress.wasCanceled():
                    break
                    
                progress.setLabelText(f"Kiểm tra: {session_file}")
                progress.setValue(i)
                QApplication.processEvents()  # Cập nhật UI
                
                # Lấy username từ tên file (bỏ .session)
                username = session_file.replace('.session', '')
                
                # Thêm dấu + nếu là số điện thoại
                if username.isdigit():
                    username = f"+{username}"
                
                # Kiểm tra đã tồn tại chưa
                if username in existing_usernames:
                    skipped_existing += 1
                    print(f"[INFO] Bỏ qua {username} - đã tồn tại trong danh sách")
                    continue
                
                # ⭐ KIỂM TRA SESSION HỢP LỆ TRƯỚC KHI LOAD
                print(f"[INFO] Đang validate session cho {username}...")
                is_valid = self.validate_telegram_session(username)
                
                if is_valid:
                    # Session hợp lệ - load vào danh sách và lấy username
                    telegram_username = self.get_telegram_username_from_session(username)
                    
                    new_account = {
                                        "selected": False,
                                        "username": username,
                        "phone": username,  # Số điện thoại
                        "password": "",  # Không cần password khi có session
                        "two_fa_password": "",  # Mật khẩu 2FA (có thể để trống ban đầu)
                        "telegram_username": telegram_username,  # Username Telegram lấy từ session
                                        "proxy": "",
                        "permanent_proxy": "",
                        "status": "✅ Session hợp lệ",
                                        "followers": "",
                                        "following": "",
                        "last_action": "Load session hợp lệ",
                        "proxy_status": "Chưa kiểm tra"
                    }
                    loaded_accounts.append(new_account)
                    existing_usernames.add(username)
                    valid_sessions += 1
                    if telegram_username:
                        print(f"[SUCCESS] Đã load session hợp lệ: {username} (@{telegram_username})")
                    else:
                        print(f"[SUCCESS] Đã load session hợp lệ: {username}")
                else:
                    # Session không hợp lệ - xóa file
                    invalid_sessions += 1
                    session_file_path = f"{sessions_dir}/{session_file}"
                    try:
                        os.remove(session_file_path)
                        print(f"[INFO] Đã xóa session file không hợp lệ: {session_file_path}")
                    except Exception as e:
                        print(f"[WARN] Không thể xóa session file: {e}")
                    print(f"[WARN] Session không hợp lệ, đã bỏ qua: {username}")
            
            progress.setValue(len(session_files))
            progress.close()
            
            # Thêm tài khoản hợp lệ vào danh sách
            if loaded_accounts:
                self.accounts.extend(loaded_accounts)
                self.save_accounts()
                self.update_account_table()
            
            # Hiển thị kết quả chi tiết
            result_message = f"📊 KẾT QUẢ LOAD SESSION:\n\n"
            result_message += f"✅ Session hợp lệ được load: {valid_sessions}\n"
            result_message += f"❌ Session không hợp lệ (đã xóa): {invalid_sessions}\n"
            result_message += f"⏭️ Đã tồn tại (bỏ qua): {skipped_existing}\n"
            result_message += f"📋 Tổng session files: {len(session_files)}\n\n"
            
            if valid_sessions > 0:
                result_message += f"🎉 Đã thêm {valid_sessions} tài khoản mới với session hợp lệ!"
            elif invalid_sessions > 0:
                result_message += "⚠️ Tất cả session files đều không hợp lệ hoặc đã tồn tại."
            else:
                result_message += "📝 Không có session files mới để xử lý."
            
            if invalid_sessions > 0:
                result_message += f"\n\n💡 {invalid_sessions} session files không hợp lệ đã được xóa tự động."
            
            QMessageBox.information(self, "Kết quả Load Session", result_message)
                
        except Exception as e:
            QMessageBox.critical(self, "Lỗi load session", f"Không thể load session files:\n{str(e)}")
            print(f"[ERROR] Load sessions error: {e}")

    def open_folder_manager(self):
        """Open folder manager dialog"""
        try:
            from src.ui.folder_manager import FolderManagerDialog
            dialog = FolderManagerDialog(self.accounts, self.folder_map, parent=self)
            dialog.folders_updated.connect(self.on_folders_updated)
            dialog.exec()
        except ImportError:
            QMessageBox.information(self, "Thông báo", "Folder manager chưa được implement")

    def on_proxy_switch_changed(self, value):
        """Handle proxy switch changes"""
        self.use_proxy = bool(value)
        self.update_proxy_switch_label()
        
        # Save to settings file
        try:
            settings = {"use_proxy": self.use_proxy}
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(settings, f)
            print(f"[DEBUG] Proxy switch changed to: {self.use_proxy}")
        except Exception as e:
            print(f"[ERROR] Cannot save proxy settings: {e}")

    def update_proxy_switch_label(self):
        """Update proxy switch label"""
        if self.use_proxy:
            self.proxy_switch_label.setText("Proxy: ON")
            self.proxy_switch_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.proxy_switch_label.setText("Proxy: OFF")
            self.proxy_switch_label.setStyleSheet("color: red; font-weight: bold;")

    def on_status_updated(self, username: str, status: str):
        """Handle status updates from threads"""
        try:
            # Find and update account in table
            for row in range(self.account_table.rowCount()):
                username_item = self.account_table.item(row, 2)  # Username column
                if username_item and username_item.text() == username:
                    status_item = self.account_table.item(row, 4)  # Status column
                    if status_item:
                        status_item.setText(status)
                        # Update color based on status
                        if "thành công" in status.lower() or "đã đăng nhập" in status.lower():
                            status_item.setForeground(QColor("green"))
                        elif "lỗi" in status.lower() or "thất bại" in status.lower():
                            status_item.setForeground(QColor("red"))
                        else:
                            status_item.setForeground(QColor("black"))
                    break
            
            # Update stats
            self.update_stats()
            
        except Exception as e:
            print(f"[ERROR] Error updating status for {username}: {e}")

    def toggle_all_accounts_selection(self, checked: bool):
        """Toggle all accounts selection"""
        try:
            for account in self.accounts:
                account["selected"] = checked
            
            # Update table display
            for row in range(self.account_table.rowCount()):
                item = self.account_table.item(row, 0)
                if item:
                    item.setData(CheckboxDelegate.CheckboxStateRole, checked)
            
            self.save_accounts()
            self.update_stats()
            print(f"[DEBUG] Toggled all accounts to: {checked}")
            
        except Exception as e:
            print(f"[ERROR] Error toggling all accounts: {e}")

    def show_context_menu(self, pos):
        """Show context menu"""
        try:
            from src.ui.context_menus import AccountContextMenu
            menu = AccountContextMenu(self)
            menu.show_account_context_menu(pos)
        except ImportError:
            print("[DEBUG] Context menu not available")

    def on_table_item_double_clicked(self, index):
        """Handle double click on table item
        Lưu ý: QTableWidget.itemDoubleClicked truyền vào QTableWidgetItem, không phải QModelIndex
        """
        if not index:
            return

        try:
            # index ở đây là QTableWidgetItem
            row = index.row()
        except AttributeError:
            # Phòng trường hợp tham số là QModelIndex
            row = index.row() if hasattr(index, "row") else -1

        if row < 0 or row >= len(self.accounts):
            return

        account = self.accounts[row]
        QMessageBox.information(
            self, "Chi tiết tài khoản",
            f"Số điện thoại: {account.get('phone', 'N/A')}\n"
            f"Username: {account.get('username', 'N/A')}\n"
            f"Telegram Username: {account.get('telegram_username', 'N/A')}\n"
            f"Mật khẩu 2FA: {account.get('two_fa_password', 'N/A')}\n"
            f"Status: {account.get('status', 'N/A')}\n"
            f"Proxy: {account.get('proxy', 'N/A')}\n"
            f"Permanent Proxy: {account.get('permanent_proxy', 'N/A')}"
        )
    
    def login_telegram(self):
        """Đăng nhập tài khoản Telegram mới"""
        # Hiển thị dialog nhập thông tin
        dialog = QInputDialog(self)
        dialog.setWindowTitle("Thêm tài khoản Telegram")
        dialog.setLabelText("Nhập số điện thoại (bắt đầu bằng +84):")
        dialog.setTextValue("+84")
        
        if dialog.exec() == QDialog.Accepted:
            phone = dialog.textValue().strip()
            if not phone.startswith("+84"):
                QMessageBox.warning(self, "Lỗi", "Số điện thoại phải bắt đầu bằng +84!")
                return
            
            # Thêm tài khoản mới
            new_account = {
                "selected": False,
                "username": phone,
                "phone": phone,
                "password": "",
                "two_fa_password": "",  # Mật khẩu 2FA
                "telegram_username": "",  # Username Telegram
                "status": "Chưa đăng nhập",
                "proxy": "",
                "permanent_proxy": "",  # ⭐ NEW: Thêm trường permanent_proxy
                "proxy_status": "Chưa kiểm tra",
                "followers": "",
                "following": "",
                "last_action": ""
            }
            
            self.accounts.append(new_account)
            self.save_accounts()
            self.update_account_table()
            
            QMessageBox.information(self, "Thành công", f"Đã thêm tài khoản {phone}!")

    def login_selected_accounts(self):
        """Đăng nhập thật các tài khoản đã chọn"""
        # Lấy tài khoản đã chọn từ checkbox trên bảng (thay vì từ biến selected)
        selected_accounts = []
        for row in range(self.account_table.rowCount()):
            checkbox_item = self.account_table.item(row, 0)
            if checkbox_item and checkbox_item.data(CheckboxDelegate.CheckboxStateRole):
                if row < len(self.accounts):
                    selected_accounts.append(self.accounts[row])
        
        if not selected_accounts:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn ít nhất một tài khoản!")
            return

        # Hiển thị dialog xác nhận
        reply = QMessageBox.question(
            self,
            "Xác nhận đăng nhập",
            f"Bạn có muốn đăng nhập {len(selected_accounts)} tài khoản đã chọn?\n"
            f"Quá trình này có thể mất vài phút...",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Tạo progress dialog
            progress = QProgressDialog("Đang đăng nhập tài khoản...", "Hủy", 0, len(selected_accounts), self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.show()

            # Đăng nhập từng tài khoản
            for i, account in enumerate(selected_accounts):
                if progress.wasCanceled():
                    break

                username = account.get('username', '')
                password = account.get('password', '')
                proxy = account.get('proxy', '') if self.use_proxy else None

                if username:
                    progress.setLabelText(f"Đang đăng nhập: {username}")
                    progress.setValue(i)
                    QApplication.processEvents()  # Cập nhật UI

                    # Thực hiện đăng nhập thật
                    self.perform_real_login(username, password, proxy)

            progress.setValue(len(selected_accounts))
            progress.close()
            QMessageBox.information(self, "Hoàn tất", f"Đã hoàn tất đăng nhập {len(selected_accounts)} tài khoản!")

    def check_live_selected_accounts(self):
        """Check live thật 100% các tài khoản đã chọn - buộc phải đăng nhập"""
        # Lấy tài khoản đã chọn từ checkbox trên bảng
        selected_accounts = []
        for row in range(self.account_table.rowCount()):
            checkbox_item = self.account_table.item(row, 0)
            if checkbox_item and checkbox_item.data(CheckboxDelegate.CheckboxStateRole):
                if row < len(self.accounts):
                    selected_accounts.append(self.accounts[row])
        
        if not selected_accounts:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn ít nhất một tài khoản!")
            return

        # Hiển thị dialog xác nhận
        reply = QMessageBox.question(
            self,
            "Xác nhận Check Live",
            f"🔍 CHECK LIVE THẬT 100%\n\n"
            f"Sẽ đăng nhập thật vào {len(selected_accounts)} tài khoản để kiểm tra trạng thái live/die.\n"
            f"⚠️ Quá trình này sẽ bỏ qua session có sẵn và đăng nhập từ đầu.\n\n"
            f"Bạn có muốn tiếp tục?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Tạo progress dialog
            progress = QProgressDialog("Đang check live tài khoản...", "Hủy", 0, len(selected_accounts), self)
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            
            live_count = 0
            die_count = 0
            error_count = 0
            
            # Check live từng tài khoản
            for i, account in enumerate(selected_accounts):
                if progress.wasCanceled():
                    break
                    
                username = account.get('phone', account.get('username', ''))
                two_fa_password = account.get('two_fa_password', account.get('password', ''))
                
                if username:
                    progress.setLabelText(f"Check live: {username}")
                    progress.setValue(i)
                    QApplication.processEvents()
                    
                    # Thực hiện check live thật
                    result = self.perform_real_check_live(username, two_fa_password)
                    if result == "LIVE":
                        live_count += 1
                    elif result == "DIE":
                        die_count += 1
                    else:
                        error_count += 1
                    
            progress.setValue(len(selected_accounts))
            progress.close()
            
            # Hiển thị kết quả
            QMessageBox.information(
                self, "Kết quả Check Live", 
                f"📊 KẾT QUẢ CHECK LIVE:\n\n"
                f"✅ Tài khoản LIVE: {live_count}\n"
                f"❌ Tài khoản DIE: {die_count}\n"
                f"⚠️ Lỗi/Không check được: {error_count}\n"
                f"📋 Tổng cộng: {len(selected_accounts)}"
            )

    def perform_real_login(self, username, password, proxy=None):
        """Đăng nhập thật bằng Telegram API với kiểm tra session validation"""
        try:
            self.update_account_status(username, "Đang kiểm tra session...")
            
            # Kiểm tra session file có tồn tại không
            session_file = f"sessions/{username.replace('+', '')}.session"
            
            if os.path.exists(session_file):
                # KHÔNG NGAY LẬP TỨC BẢO "ĐÃ ĐĂNG NHẬP" - PHẢI VALIDATE SESSION TRƯỚC
                self.update_account_status(username, "🔍 Đang xác thực session...")
                
                # Kiểm tra session có còn hoạt động không
                session_valid = self.validate_telegram_session(username)
                if session_valid:
                    self.update_account_status(username, "✅ Session hợp lệ - Đã đăng nhập!")
                    return
                else:
                    self.update_account_status(username, "⚠️ Session hết hạn - Cần đăng nhập lại...")
                    # Xóa session file cũ
                    try:
                        os.remove(session_file)
                        print(f"[INFO] Đã xóa session file hết hạn: {session_file}")
                    except Exception as e:
                        print(f"[WARN] Không thể xóa session file: {e}")
                    # Tiếp tục với quá trình đăng nhập mới bên dưới
            
            # Nếu chưa có session, thực hiện đăng nhập thật
            self.update_account_status(username, "🚀 Bắt đầu đăng nhập thật...")
            
            # Import telethon với error handling tốt hơn
            try:
                from telethon.sync import TelegramClient
                from telethon.errors import (
                    PhoneCodeInvalidError, 
                    PhoneNumberInvalidError,
                    SessionPasswordNeededError
                )
                print(f"[INFO] Đã import thành công telethon cho {username}")
            except ImportError as import_error:
                self.update_account_status(username, "❌ Chưa cài đặt telethon")
                QMessageBox.warning(self, "Lỗi", "Cần cài đặt thư viện telethon:\npip install telethon")
                print(f"[ERROR] Import telethon failed: {import_error}")
                return
            
            try:
                # API credentials (cần có từ my.telegram.org)
                api_id = 29836061  # Thay bằng API ID thật của bạn
                api_hash = 'b2f56fe3fb8af3dd1ddb80c85b72f1e4'  # Thay bằng API Hash thật
                
                session_name = f"sessions/{username.replace('+', '')}"
                
                # Tạo thư mục sessions nếu chưa có
                os.makedirs("sessions", exist_ok=True)

                # Khởi tạo client
                client = TelegramClient(session_name, api_id, api_hash)
                
                self.update_account_status(username, "Đang kết nối Telegram...")
                client.connect()

                # Kiểm tra đã đăng nhập chưa
                if client.is_user_authorized():
                    self.update_account_status(username, "✅ Đã đăng nhập thành công!")
                    client.disconnect()
                    return
                
                # Gửi mã xác thực
                self.update_account_status(username, "Đang gửi mã xác thực...")
                phone = username if username.startswith('+') else f'+{username}'
                
                try:
                    sent_code = client.send_code_request(phone)
                    print(f"[INFO] Đã gửi mã xác thực đến {phone}")
                except PhoneNumberInvalidError:
                    self.update_account_status(username, "❌ Số điện thoại không hợp lệ")
                    client.disconnect()
                    return
                except Exception as send_error:
                    self.update_account_status(username, f"❌ Lỗi gửi mã: {str(send_error)}")
                    client.disconnect()
                    return
                
                # Hiển thị dialog nhập mã
                self.update_account_status(username, "📱 Nhập mã xác thực...")
                from PySide6.QtWidgets import QInputDialog
                
                code, ok = QInputDialog.getText(
                    self, 
                    "Mã xác thực Telegram", 
                    f"Nhập mã xác thực gửi đến {phone}:"
                )
                
                if ok and code:
                    self.update_account_status(username, "Đang xác thực...")
                    
                    try:
                        client.sign_in(phone, code)
                        
                        # ⭐ SAU KHI ĐĂNG NHẬP THÀNH CÔNG - LẤY THÔNG TIN USER
                        try:
                            me = client.get_me()
                            if me:
                                # Cập nhật username Telegram vào dữ liệu
                                if me.username:
                                    for account in self.accounts:
                                        if account.get('phone') == username or account.get('username') == username:
                                            account['telegram_username'] = me.username
                                            print(f"[SUCCESS] Đã cập nhật username Telegram: @{me.username} cho {username}")
                                            break
                                    
                                    # Lưu dữ liệu ngay lập tức
                                    self.save_accounts()
                                    self.update_account_table()
                                    
                                    self.update_account_status(username, f"✅ Đăng nhập thành công - @{me.username}")
                                else:
                                    self.update_account_status(username, "✅ Đăng nhập thành công - Chưa có username")
                            else:
                                self.update_account_status(username, "✅ Đăng nhập thành công!")
                        except Exception as user_info_error:
                            print(f"[WARN] Không thể lấy thông tin user sau đăng nhập: {user_info_error}")
                            self.update_account_status(username, "✅ Đăng nhập thành công!")
                        
                    except PhoneCodeInvalidError:
                        self.update_account_status(username, "❌ Mã xác thực sai")
                        
                    except SessionPasswordNeededError:
                        self.update_account_status(username, "⚠️ Cần mật khẩu 2FA")
                        # Hiển thị dialog nhập 2FA password
                        two_fa_password, ok_2fa = QInputDialog.getText(
                            self, 
                            "Mật khẩu 2FA", 
                            f"Nhập mật khẩu 2FA cho {phone}:",
                            QInputDialog.Password
                        )
                        
                        if ok_2fa and two_fa_password:
                            try:
                                client.sign_in(password=two_fa_password)
                                self.update_account_status(username, "✅ Đăng nhập thành công với 2FA!")
                                
                                # Lưu 2FA password vào account
                                for account in self.accounts:
                                    if account.get('phone') == username or account.get('username') == username:
                                        account['two_fa_password'] = two_fa_password
                                        break
                                self.save_accounts()
                                
                            except Exception as two_fa_error:
                                self.update_account_status(username, f"❌ Lỗi 2FA: {str(two_fa_error)}")
                        else:
                            self.update_account_status(username, "❌ Đã hủy nhập 2FA")
                        
                    except Exception as sign_error:
                        self.update_account_status(username, f"❌ Lỗi đăng nhập: {str(sign_error)}")
                        print(f"[ERROR] Sign in error for {username}: {sign_error}")
                else:
                    self.update_account_status(username, "❌ Đã hủy đăng nhập")
                
                client.disconnect()
                
            except Exception as telegram_error:
                self.update_account_status(username, f"❌ Lỗi Telegram: {str(telegram_error)}")
                print(f"[ERROR] Telegram error for {username}: {telegram_error}")
                
        except Exception as e:
            self.update_account_status(username, f"❌ Lỗi: {str(e)}")
            print(f"[ERROR] Login error: {e}")

    def validate_telegram_session(self, username):
        """Kiểm tra session Telegram có còn hoạt động hay không"""
        try:
            from telethon.sync import TelegramClient
            from telethon.errors import AuthKeyUnregisteredError, UnauthorizedError
            
            # API credentials
            api_id = 29836061
            api_hash = 'b2f56fe3fb8af3dd1ddb80c85b72f1e4'
            
            session_name = f"sessions/{username.replace('+', '')}"
            
            # Tạo client và kiểm tra
            client = TelegramClient(session_name, api_id, api_hash)
            
            try:
                client.connect()
                
                # Kiểm tra xem user có còn được authorize không
                if client.is_user_authorized():
                    # Thử thực hiện một thao tác đơn giản để chắc chắn session còn hoạt động
                    try:
                        me = client.get_me()
                        if me:
                            print(f"[SUCCESS] Session hợp lệ cho {username} - User: @{me.username or 'N/A'}")
                            
                            # ⭐ CẬP NHẬT USERNAME KHI VALIDATE SESSION
                            if me.username:
                                for account in self.accounts:
                                    if account.get('phone') == username or account.get('username') == username:
                                        if account.get('telegram_username') != me.username:
                                            account['telegram_username'] = me.username
                                            print(f"[INFO] Đã cập nhật username từ session: @{me.username} cho {username}")
                                            # Lưu dữ liệu và cập nhật UI
                                            self.save_accounts()
                                            self.update_account_table()
                                        break
                            
                            client.disconnect()
                            return True
                    except Exception as api_error:
                        print(f"[ERROR] API call failed for {username}: {api_error}")
                        client.disconnect()
                        return False
                else:
                    print(f"[WARN] Session không được authorize cho {username}")
                    client.disconnect()
                    return False
                    
            except (AuthKeyUnregisteredError, UnauthorizedError) as auth_error:
                print(f"[ERROR] Session không hợp lệ cho {username}: {auth_error}")
                client.disconnect()
                return False
                
            except Exception as conn_error:
                print(f"[ERROR] Không thể kết nối session cho {username}: {conn_error}")
                if client:
                    client.disconnect()
                return False
                
        except ImportError:
            print(f"[ERROR] Chưa cài đặt telethon - không thể validate session")
            return False  # Không thể kiểm tra, coi như session invalid
            
        except Exception as e:
            print(f"[ERROR] Lỗi validate session cho {username}: {e}")
            return False

    def perform_real_check_live(self, username, two_fa_password):
        """Check live thật 100% bằng cách đăng nhập thật vào Telegram"""
        try:
            self.update_account_status(username, "🔍 Đang check live...")
            
            # XÓA SESSION CŨ TRƯỚC KHI CHECK LIVE
            session_file = f"sessions/{username.replace('+', '')}.session"
            if os.path.exists(session_file):
                try:
                    os.remove(session_file)
                    print(f"[INFO] Đã xóa session cũ để check live: {session_file}")
                except Exception as e:
                    print(f"[WARN] Không thể xóa session cũ: {e}")
            
            try:
                from telethon.sync import TelegramClient
                from telethon.errors import (
                    PhoneCodeInvalidError, 
                    PhoneNumberInvalidError,
                    SessionPasswordNeededError,
                    FloodWaitError,
                    PhoneNumberBannedError,
                    AuthKeyUnregisteredError,
                    UserDeactivatedError,
                    UserDeactivatedBanError
                )
                
                # API credentials
                api_id = 29836061
                api_hash = 'b2f56fe3fb8af3dd1ddb80c85b72f1e4'
                
                session_name = f"sessions/{username.replace('+', '')}_temp"
                
                # Tạo thư mục sessions nếu chưa có
                os.makedirs("sessions", exist_ok=True)
                
                # Khởi tạo client
                client = TelegramClient(session_name, api_id, api_hash)
                
                self.update_account_status(username, "🚀 Đăng nhập để check live...")
                client.connect()
                
                # Kiểm tra xem đã đăng nhập chưa (không nên có với session temp mới)
                if client.is_user_authorized():
                    # Nếu đã authorize, check thông tin user
                    try:
                        me = client.get_me()
                        if me:
                            self.update_account_status(username, "✅ LIVE - Tài khoản hoạt động")
                            client.disconnect()
                            # Xóa temp session
                            try:
                                os.remove(f"{session_name}.session")
                            except:
                                pass
                            return "LIVE"
                    except Exception as api_error:
                        print(f"[ERROR] API call failed cho {username}: {api_error}")
                        self.update_account_status(username, "❌ DIE - Không thể truy cập")
                        client.disconnect()
                        return "DIE"
                
                # Gửi mã xác thực
                self.update_account_status(username, "📱 Gửi mã xác thực...")
                phone = username if username.startswith('+') else f'+{username}'
                
                try:
                    sent_code = client.send_code_request(phone)
                except PhoneNumberBannedError:
                    self.update_account_status(username, "❌ DIE - Số điện thoại bị cấm")
                    client.disconnect()
                    return "DIE"
                except PhoneNumberInvalidError:
                    self.update_account_status(username, "❌ DIE - Số điện thoại không hợp lệ")
                    client.disconnect()
                    return "DIE"
                except FloodWaitError as e:
                    self.update_account_status(username, f"⏳ Cần chờ {e.seconds}s - FloodWait")
                    client.disconnect()
                    return "ERROR"
                
                # Hiển thị dialog nhập mã
                self.update_account_status(username, "🔢 Nhập mã OTP...")
                from PySide6.QtWidgets import QInputDialog
                
                code, ok = QInputDialog.getText(
                        self, 
                    f"Mã OTP cho {username}",
                    f"Nhập mã OTP gửi đến {phone}:\n(Để check live tài khoản)"
                )

                if ok and code:
                    self.update_account_status(username, "🔐 Đăng nhập với OTP...")

                    try:
                        # Thử đăng nhập với OTP
                        client.sign_in(phone, code)

                        # Nếu cần 2FA
                        if two_fa_password:
                            self.update_account_status(username, "🔐 Nhập mật khẩu 2FA...")
                            try:
                                client.sign_in(password=two_fa_password)
                            except Exception as two_fa_error:
                                self.update_account_status(username, "❌ DIE - Mật khẩu 2FA sai")
                                client.disconnect()
                                return "DIE"
                        else:
                            self.update_account_status(username, "⚠️ Cần mật khẩu 2FA")
                            client.disconnect()
                            return "ERROR"

                    except PhoneCodeInvalidError:
                        self.update_account_status(username, "❌ DIE - Mã OTP sai")
                        client.disconnect()
                        return "DIE"

                    except (UserDeactivatedError, UserDeactivatedBanError):
                        self.update_account_status(username, "❌ DIE - Tài khoản bị vô hiệu hóa")
                        client.disconnect()
                        return "DIE"

                    except AuthKeyUnregisteredError:
                        self.update_account_status(username, "❌ DIE - Auth key không hợp lệ")
                        client.disconnect()
                        return "DIE"

                    except Exception as sign_error:
                        self.update_account_status(username, f"❌ DIE - Lỗi đăng nhập: {str(sign_error)}")
                        client.disconnect()
                        return "DIE"

                    # Kiểm tra thông tin sau khi đăng nhập thành công
                    try:
                        me = client.get_me()
                        if me:
                            self.update_account_status(username, f"✅ LIVE - @{me.username or 'N/A'}")
                            
                            # Lưu username Telegram nếu có
                            if me.username:
                                for account in self.accounts:
                                    if account.get('phone') == username or account.get('username') == username:
                                        account['telegram_username'] = me.username
                                        break
                            
                            client.disconnect()
                            # Xóa temp session
                            try:
                                os.remove(f"{session_name}.session")
                            except:
                                pass
                            return "LIVE"
                        else:
                            self.update_account_status(username, "❌ DIE - Không lấy được thông tin user")
                            client.disconnect()
                            return "DIE"
                    except Exception as api_error:
                        self.update_account_status(username, f"❌ DIE - API error: {str(api_error)}")
                        client.disconnect()
                        return "DIE"
                        
                else:
                    self.update_account_status(username, "⏹️ Đã hủy check live")
                    client.disconnect()
                    return "ERROR"
                    
            except ImportError:
                self.update_account_status(username, "❌ Chưa cài đặt telethon")
                return "ERROR"

            except Exception as e:
                self.update_account_status(username, f"❌ Lỗi check live: {str(e)}")
                print(f"[ERROR] Check live error cho {username}: {e}")
                return "ERROR"

            finally:
                # Cleanup temp session file
                try:
                    temp_session = f"sessions/{username.replace('+', '')}_temp.session"
                    if os.path.exists(temp_session):
                        os.remove(temp_session)
                except:
                    pass
                    
        except Exception as outer_error:
            self.update_account_status(username, f"❌ Lỗi tổng quát: {str(outer_error)}")
            return "ERROR"
        
        return "ERROR"  # Đảm bảo hàm perform_real_check_live kết thúc đúng

    def get_telegram_username_from_session(self, username):
        """Lấy username Telegram từ session có sẵn"""
        client = None
        try:
            from telethon.sync import TelegramClient
            
            # API credentials
            api_id = 29836061
            api_hash = 'b2f56fe3fb8af3dd1ddb80c85b72f1e4'
            
            session_name = f"sessions/{username.replace('+', '')}"
            
            # Tạo client và lấy thông tin
            client = TelegramClient(session_name, api_id, api_hash)
            client.connect()
            
            if client.is_user_authorized():
                me = client.get_me()
                if me and me.username:
                    return me.username
            
            return ""
            
        except ImportError:
            print("[ERROR] Chưa cài đặt telethon")
            return ""
        except Exception as e:
            print(f"[ERROR] Lỗi lấy username từ session: {e}")
            return ""
        finally:
            if client:
                try:
                    client.disconnect()
                except Exception as e:
                    print(f"[ERROR] Lỗi khi ngắt kết nối client: {e}")

    def select_selected_accounts(self):
        """Chọn các tài khoản đang được chọn trong bảng"""
        selected_rows = []
        for row in range(self.account_table.rowCount()):
            if self.account_table.item(row, 0).checkState() == Qt.Checked:
                selected_rows.append(row)

        if not selected_rows:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn ít nhất một tài khoản!")
            return

        for row in selected_rows:
            self.accounts[row]['selected'] = True

        self.save_accounts()
        self.update_account_table()

    def deselect_selected_accounts(self):
        """Bỏ chọn các tài khoản đang được chọn trong bảng"""
        selected_rows = []
        for row in range(self.account_table.rowCount()):
            if self.account_table.item(row, 0).checkState() == Qt.Checked:
                selected_rows.append(row)

        if not selected_rows:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn ít nhất một tài khoản!")
            return

        for row in selected_rows:
            self.accounts[row]['selected'] = False

        self.save_accounts()
        self.update_account_table()

    def deselect_all_accounts(self):
        """Bỏ chọn tất cả tài khoản"""
        for account in self.accounts:
            account['selected'] = False

        self.save_accounts()
        self.update_account_table()

    def delete_selected_accounts(self):
        """Xóa các tài khoản đã chọn"""
        # Lấy tài khoản đã chọn từ checkbox trên bảng
        selected_accounts = []
        selected_indices = []
        for row in range(self.account_table.rowCount()):
            checkbox_item = self.account_table.item(row, 0)
            if checkbox_item and checkbox_item.data(CheckboxDelegate.CheckboxStateRole):
                if row < len(self.accounts):
                    selected_accounts.append(self.accounts[row])
                    selected_indices.append(row)
        
        if not selected_accounts:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn ít nhất một tài khoản!")
            return

        reply = QMessageBox.question(
            self, 
            "Xác nhận xóa", 
            f"Bạn có chắc muốn xóa {len(selected_accounts)} tài khoản đã chọn?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Xóa tài khoản theo indices (từ cuối lên đầu để không bị lệch index)
            for index in sorted(selected_indices, reverse=True):
                del self.accounts[index]
            self.save_accounts()
            self.update_account_table()
            QMessageBox.information(self, "Thành công", f"Đã xóa {len(selected_accounts)} tài khoản!")

    def delete_all_accounts(self):
        """Xóa tất cả tài khoản"""
        if not self.accounts:
            QMessageBox.warning(self, "Cảnh báo", "Không có tài khoản nào để xóa!")
            return

        reply = QMessageBox.question(
            self, 
            "Xác nhận xóa", 
            f"Bạn có chắc muốn xóa TẤT CẢ {len(self.accounts)} tài khoản?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.accounts.clear()
            self.save_accounts()
            self.update_account_table()
            QMessageBox.information(self, "Thành công", "Đã xóa tất cả tài khoản!")

    def add_selected_to_folder(self, folder_name):
        """Thêm các tài khoản đã chọn vào thư mục"""
        # Lấy tài khoản đã chọn từ checkbox trên bảng
        selected_accounts = []
        for row in range(self.account_table.rowCount()):
            checkbox_item = self.account_table.item(row, 0)
            if checkbox_item and checkbox_item.data(CheckboxDelegate.CheckboxStateRole):
                if row < len(self.accounts):
                    selected_accounts.append(self.accounts[row])
        
        if not selected_accounts:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn ít nhất một tài khoản!")
            return

        # Thêm vào thư mục
        for account in selected_accounts:
            username = account.get('username', '')
            if username:
                self.folder_map[username] = folder_name

        self.save_folder_map()
        self.update_account_table()
        # Emit signal để thông báo folders đã được cập nhật
        self.folders_updated.emit()

        QMessageBox.information(
            self, 
            "Thành công", 
            f"Đã thêm {len(selected_accounts)} tài khoản vào thư mục '{folder_name}'!"
        )

    def remove_selected_from_folder(self):
        """Xóa các tài khoản đã chọn khỏi thư mục hiện tại"""
        # Lấy tài khoản đã chọn từ checkbox trên bảng
        selected_accounts = []
        for row in range(self.account_table.rowCount()):
            checkbox_item = self.account_table.item(row, 0)
            if checkbox_item and checkbox_item.data(CheckboxDelegate.CheckboxStateRole):
                if row < len(self.accounts):
                    selected_accounts.append(self.accounts[row])
        
        if not selected_accounts:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn ít nhất một tài khoản!")
            return

        # Xóa khỏi thư mục
        for account in selected_accounts:
            username = account.get('username', '')
            if username in self.folder_map:
                del self.folder_map[username]

        self.save_folder_map()
        self.update_account_table()
        # Emit signal để thông báo folders đã được cập nhật
        self.folders_updated.emit()

        QMessageBox.information(
            self, 
            "Thành công", 
            f"Đã xóa {len(selected_accounts)} tài khoản khỏi thư mục!"
        )

    def delete_selected_folder(self):
        """Xóa thư mục đang chọn"""
        current_folder = self.category_combo.currentText()
        if current_folder == "Tất cả":
            QMessageBox.warning(self, "Cảnh báo", "Không thể xóa thư mục 'Tất cả'!")
            return

        reply = QMessageBox.question(
            self, 
            "Xác nhận xóa", 
            f"Bạn có chắc muốn xóa thư mục '{current_folder}'?\nCác tài khoản trong thư mục sẽ được chuyển về 'Tổng'.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Xóa thư mục khỏi _FOLDER_SET_
            if '_FOLDER_SET_' in self.folder_map:
                folders = self.folder_map['_FOLDER_SET_']
                if current_folder in folders:
                    folders.remove(current_folder)
                self.folder_map['_FOLDER_SET_'] = folders

            # Chuyển tài khoản về Tổng
            for username, folder in list(self.folder_map.items()):
                if folder == current_folder:
                    self.folder_map[username] = "Tổng"

            self.save_folder_map()
            self.load_folder_list_to_combo()
            self.update_account_table()
            # Emit signal để thông báo folders đã được cập nhật
            self.folders_updated.emit()

            QMessageBox.information(self, "Thành công", f"Đã xóa thư mục '{current_folder}'!")

    def set_account_status_selected(self, status):
        """Đặt trạng thái cho các tài khoản đã chọn"""
        # Lấy tài khoản đã chọn từ checkbox trên bảng
        selected_accounts = []
        for row in range(self.account_table.rowCount()):
            checkbox_item = self.account_table.item(row, 0)
            if checkbox_item and checkbox_item.data(CheckboxDelegate.CheckboxStateRole):
                if row < len(self.accounts):
                    selected_accounts.append(self.accounts[row])
        
        if not selected_accounts:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn ít nhất một tài khoản!")
            return

        # Cập nhật trạng thái
        for account in selected_accounts:
            account['status'] = status

        self.save_accounts()
        self.update_account_table()
        QMessageBox.information(
            self, 
            "Thành công", 
            f"Đã chuyển {len(selected_accounts)} tài khoản sang trạng thái '{status}'!"
        )

    def toggle_stealth_mode(self):
        """Bật/tắt chế độ ẩn danh cho các tài khoản đã chọn"""
        # Lấy tài khoản đã chọn từ checkbox trên bảng
        selected_accounts = []
        for row in range(self.account_table.rowCount()):
            checkbox_item = self.account_table.item(row, 0)
            if checkbox_item and checkbox_item.data(CheckboxDelegate.CheckboxStateRole):
                if row < len(self.accounts):
                    selected_accounts.append(self.accounts[row])
        
        if not selected_accounts:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn ít nhất một tài khoản!")
            return

        # Toggle stealth mode
        for account in selected_accounts:
            account['stealth_mode'] = not account.get('stealth_mode', False)

        self.save_accounts()
        self.update_account_table()
        QMessageBox.information(
            self, 
            "Thành công", 
            f"Đã thay đổi chế độ ẩn danh cho {len(selected_accounts)} tài khoản!"
        )

    def export_accounts(self):
        """Xuất tài khoản ra file"""
        # Lấy tài khoản đã chọn từ checkbox trên bảng
        selected_accounts = []
        for row in range(self.account_table.rowCount()):
            checkbox_item = self.account_table.item(row, 0)
            if checkbox_item and checkbox_item.data(CheckboxDelegate.CheckboxStateRole):
                if row < len(self.accounts):
                    selected_accounts.append(self.accounts[row])
        
        if not selected_accounts:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn ít nhất một tài khoản!")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Xuất tài khoản",
            "accounts_export.json",
            "JSON Files (*.json);;Text Files (*.txt);;CSV Files (*.csv);;All Files (*)"
        )

        if not file_path:
            return

        try:
            if file_path.endswith('.json'):
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(selected_accounts, f, indent=4, ensure_ascii=False)
            elif file_path.endswith('.txt'):
                with open(file_path, 'w', encoding='utf-8') as f:
                    for acc in selected_accounts:
                        f.write(f"{acc.get('username', '')}\t{acc.get('password', '')}\t{acc.get('proxy', '')}\n")
            elif file_path.endswith('.csv'):
                import csv
                with open(file_path, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Username', 'Password', 'Proxy', 'Status', 'Followers', 'Following'])
                    for acc in selected_accounts:
                        writer.writerow([
                            acc.get('username', ''),
                            acc.get('password', ''),
                            acc.get('proxy', ''),
                            acc.get('status', ''),
                            acc.get('followers', ''),
                            acc.get('following', '')
                        ])

            QMessageBox.information(
                self,
                "Thành công",
                f"Đã xuất {len(selected_accounts)} tài khoản ra file:\n{file_path}"
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Lỗi",
                f"Không thể xuất tài khoản:\n{str(e)}"
            )

    def update_selected_proxy_info(self):
        """Cập nhật thông tin proxy cho các tài khoản đã chọn"""
        # Lấy tài khoản đã chọn từ checkbox trên bảng
        selected_accounts = []
        for row in range(self.account_table.rowCount()):
            checkbox_item = self.account_table.item(row, 0)
            if checkbox_item and checkbox_item.data(CheckboxDelegate.CheckboxStateRole):
                if row < len(self.accounts):
                    selected_accounts.append(self.accounts[row])
        
        if not selected_accounts:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn ít nhất một tài khoản!")
            return

        proxy_text, ok = QInputDialog.getText(
            self,
            "Cập nhật Proxy",
            f"Nhập proxy cho {len(selected_accounts)} tài khoản:\n(Format: ip:port:user:pass hoặc ip:port)"
        )

        if ok and proxy_text.strip():
            proxy_text = proxy_text.strip()
            # Cập nhật proxy cho các tài khoản đã chọn
            for account in selected_accounts:
                account['proxy'] = proxy_text
                account['proxy_status'] = 'Chưa kiểm tra'

            self.save_accounts()
            self.update_account_table()
            QMessageBox.information(
                self,
                "Thành công",
                f"Đã cập nhật proxy cho {len(selected_accounts)} tài khoản!"
            )

    def handle_item_changed(self, item):
        """Handle item change events"""
        if item.column() == 0:  # Checkbox column
            row = item.row()
            if row < len(self.accounts):
                self.accounts[row]['selected'] = item.checkState() == Qt.Checked
                self.update_stats()

    def update_account_table(self, accounts_to_display=None):
        """Update account table display"""
        if accounts_to_display is None:
            accounts_to_display = self.accounts

        self.account_table.setRowCount(len(accounts_to_display))
        
        for row, account in enumerate(accounts_to_display):
            # Checkbox column
            checkbox_item = QTableWidgetItem()
            checkbox_item.setData(CheckboxDelegate.CheckboxStateRole, account.get('selected', False))
            checkbox_item.setTextAlignment(Qt.AlignCenter)
            self.account_table.setItem(row, 0, checkbox_item)
            
            # STT
            stt_item = QTableWidgetItem(str(row + 1))
            stt_item.setTextAlignment(Qt.AlignCenter)
            self.account_table.setItem(row, 1, stt_item)
            
            # Số điện thoại (ưu tiên phone, fallback username)
            phone_number = account.get('phone', account.get('username', ''))
            phone_item = QTableWidgetItem(phone_number)
            self.account_table.setItem(row, 2, phone_item)
            
            # Mật khẩu 2FA (ưu tiên two_fa_password, fallback password)
            two_fa_password = account.get('two_fa_password', account.get('password', ''))
            password_item = QTableWidgetItem(two_fa_password)
            self.account_table.setItem(row, 3, password_item)
            
            # Username Telegram (hiển thị @username thực từ Telegram)
            telegram_username = account.get('telegram_username', '')
            if telegram_username and not telegram_username.startswith('@'):
                telegram_username = f"@{telegram_username}"
            username_item = QTableWidgetItem(telegram_username)
            self.account_table.setItem(row, 4, username_item)
            
            # Status (moved to column 5)
            status_item = QTableWidgetItem(account.get('status', 'Chưa đăng nhập'))
            self.account_table.setItem(row, 5, status_item)

            # Proxy (moved to column 6)
            proxy_item = QTableWidgetItem(account.get('proxy', ''))
            self.account_table.setItem(row, 6, proxy_item)
            
            # Permanent Proxy (moved to column 7)
            permanent_proxy_item = QTableWidgetItem(account.get('permanent_proxy', ''))
            self.account_table.setItem(row, 7, permanent_proxy_item)
            
            # Proxy Status (moved to column 8)
            proxy_status_item = QTableWidgetItem(account.get('proxy_status', 'Chưa kiểm tra'))
            self.account_table.setItem(row, 8, proxy_status_item)
            
            # Followers (moved to column 9)
            followers_item = QTableWidgetItem(str(account.get('followers', '')))
            self.account_table.setItem(row, 9, followers_item)

            # Following (moved to column 10)
            following_item = QTableWidgetItem(str(account.get('following', '')))
            self.account_table.setItem(row, 10, following_item)
            
            # Last Action (moved to column 11)
            last_action_item = QTableWidgetItem(account.get('last_action', ''))
            self.account_table.setItem(row, 11, last_action_item)
        
        self.update_stats(accounts_to_display)

    def update_stats(self, accounts_to_display=None):
        """Update statistics display"""
        if accounts_to_display is None:
            accounts_to_display = self.accounts
        
        total = len(accounts_to_display)
        selected = sum(1 for acc in accounts_to_display if acc.get('selected', False))
        logged_in = sum(1 for acc in accounts_to_display if 'đăng nhập' in acc.get('status', '').lower())
        
        stats_text = f"📊 Tổng: {total} tài khoản | ✅ Đã chọn: {selected} | 🔐 Đã đăng nhập: {logged_in}"
        self.stats_label.setText(stats_text)

    def on_checkbox_clicked(self, row, new_state):
        """Handle checkbox click events"""
        if row < len(self.accounts):
            self.accounts[row]['selected'] = new_state
            self.save_accounts()
        self.update_stats()

    def filter_accounts(self, text):
        """Filter accounts by search text"""
        if not text:
            self.update_account_table()
            return
        
        text = text.lower()
        filtered_accounts = []
        
        for account in self.accounts:
            if (text in account.get('username', '').lower() or 
                text in account.get('status', '').lower()):
                filtered_accounts.append(account)
        
        self.update_account_table(filtered_accounts)

    def update_account_status(self, username: str, status: str):
        """Cập nhật trạng thái tài khoản trong bảng"""
        try:
            # Tìm và cập nhật account trong danh sách
            for account in self.accounts:
                if account.get('username') == username:
                    account['status'] = status
                    break
            
            # Cập nhật trong bảng
            for row in range(self.account_table.rowCount()):
                phone_item = self.account_table.item(row, 2)  # Số điện thoại column
                if phone_item and phone_item.text() == username:
                    status_item = self.account_table.item(row, 5)  # Status column (moved to column 5)
                    if status_item:
                        status_item.setText(status)
                        # Update color based on status
                        if "thành công" in status.lower() or "đã đăng nhập" in status.lower():
                            status_item.setForeground(QColor("green"))
                        elif "lỗi" in status.lower() or "thất bại" in status.lower():
                            status_item.setForeground(QColor("red"))
                        else:
                            status_item.setForeground(QColor("black"))
                    break
            
            # Lưu và cập nhật stats
            self.save_accounts()
            self.update_stats()
            
        except Exception as e:
            print(f"[ERROR] Error updating status for {username}: {e}")

