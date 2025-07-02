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
    QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView, QSizePolicy, QStyledItemDelegate, QMenu, QProgressDialog, QInputDialog, QSlider)
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
            return True  # Đã xử lý sự kiện
        return False  # Quan trọng: Trả về False để các sự kiện không phải click được xử lý mặc định

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
        self.accounts_file = "accounts.json"
        self.folder_map_file = "data/folder_map.json"
        
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

        btn_import_accounts = QPushButton("Import .txt/.csv")
        btn_import_accounts.clicked.connect(self.import_accounts)
        self.sidebar_layout.addWidget(btn_import_accounts)

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
        self.account_table.setColumnCount(11)  # ⭐ Tăng lên 11 cột để thêm Permanent Proxy
        self.account_table.setHorizontalHeaderLabels([
            "", "STT", "Tên đăng nhập", "Mật khẩu", "Trạng thái", 
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
        header.setSectionResizeMode(2, QHeaderView.Fixed)  # Cột "Tên đăng nhập" - Chuyển về Fixed
        self.account_table.setColumnWidth(2, 150)  # Đặt chiều rộng cố định
        header.setSectionResizeMode(3, QHeaderView.Fixed)  # Cột "Mật khẩu" - Chuyển về Fixed
        self.account_table.setColumnWidth(3, 150)  # Đặt chiều rộng cố định
        header.setSectionResizeMode(4, QHeaderView.Fixed)  # Cột "Trạng thái"
        self.account_table.setColumnWidth(4, 120)  # Giữ nguyên chiều rộng
        header.setSectionResizeMode(5, QHeaderView.Fixed)  # Cột "Proxy" - Chuyển về Fixed
        self.account_table.setColumnWidth(5, 150)  # Đặt chiều rộng cố định (giảm để có chỗ cho Permanent Proxy)
        header.setSectionResizeMode(6, QHeaderView.Fixed)  # ⭐ Cột "Permanent Proxy"
        self.account_table.setColumnWidth(6, 120)  # Proxy VV - chiều rộng vừa phải
        header.setSectionResizeMode(7, QHeaderView.Fixed)  # Cột "Trạng thái Proxy"
        self.account_table.setColumnWidth(7, 120)  # Giảm chiều rộng
        header.setSectionResizeMode(8, QHeaderView.Fixed)  # Cột "Follower"
        self.account_table.setColumnWidth(8, 79)
        header.setSectionResizeMode(9, QHeaderView.Fixed)  # Cột "Following"
        self.account_table.setColumnWidth(9, 79)
        header.setSectionResizeMode(10, QHeaderView.Stretch)  # Cột "Hành động cuối" - Giữ nguyên Stretch
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
                            print(f"[DEBUG] Migrated account {account.get('username', 'Unknown')} with permanent_proxy field")
                    
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
        if hasattr(self, 'accounts_file'):
            try:
                # Tạo thư mục data nếu chưa có
                os.makedirs(os.path.dirname(self.accounts_file), exist_ok=True)
                with open(self.accounts_file, 'w', encoding='utf-8') as f:
                    json.dump(self.accounts, f, indent=4, ensure_ascii=False)
                print("[INFO] Accounts đã được lưu.")
            except Exception as e:
                print(f"[ERROR] Lỗi khi lưu accounts: {e}")

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

    def import_accounts(self):
        """Import accounts from file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import tài khoản", "", "Text Files (*.txt);;CSV Files (*.csv);;All Files (*)"
        )
        if file_path:
            try:
                imported_accounts = []
                if file_path.endswith('.csv'):
                    import csv
                    with open(file_path, 'r', encoding='utf-8', newline='') as f:
                        reader = csv.reader(f)
                        for row in reader:
                            if len(row) >= 2:
                                username = row[0].strip()
                                password = row[1].strip()
                                proxy = row[2].strip() if len(row) > 2 else ""
                                if username and password:
                                    imported_accounts.append({
                                        "selected": False,
                                        "username": username,
                                        "password": password,
                                        "proxy": proxy,
                                        "status": "Chưa đăng nhập",
                                        "followers": "",
                                        "following": "",
                                        "last_action": "",
                                        "proxy_status": "Chưa kiểm tra",
                                        "permanent_proxy": ""
                                    })
                else:
                    # Text file
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if ':' in line:
                                parts = line.split(':')
                                username = parts[0].strip()
                                password = parts[1].strip()
                                if username and password:
                                    imported_accounts.append({
                                        "selected": False,
                                        "username": username,
                                        "password": password,
                                        "proxy": "",
                                        "status": "Chưa đăng nhập",
                                        "followers": "",
                                        "following": "",
                                        "last_action": "",
                                        "proxy_status": "Chưa kiểm tra",
                                        "permanent_proxy": ""
                                    })
                
                if imported_accounts:
                    self.accounts.extend(imported_accounts)
                    self.save_accounts()
                    self.update_account_table()
                    QMessageBox.information(
                        self, "Import thành công", 
                        f"Đã import {len(imported_accounts)} tài khoản!"
                    )
                else:
                    QMessageBox.warning(self, "Import thất bại", "Không tìm thấy tài khoản hợp lệ trong file!")
                
            except Exception as e:
                QMessageBox.critical(self, "Lỗi import", f"Không thể import file:\n{str(e)}")

    def open_folder_manager(self):
        """Open folder manager dialog"""
        try:
            from src.ui.folder_manager import FolderManagerDialog
            dialog = FolderManagerDialog(self.folder_map, parent=self)
            if dialog.exec() == QDialog.Accepted: # type: ignore
                self.folder_map = dialog.get_folder_map()
                self.save_folder_map()
                self.load_folder_list_to_combo()
                self.update_account_table()
                # Emit signal for other tabs
                if hasattr(self, 'folders_updated'):
                    self.folders_updated.emit()
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
            menu.exec(self.account_table.viewport().mapToGlobal(pos))
        except ImportError:
            print("[DEBUG] Context menu not available")

    def on_table_item_double_clicked(self, index):
        """Handle double click on table item"""
        if index.isValid() and index.row() < len(self.accounts):
            account = self.accounts[index.row()]
            QMessageBox.information(
                self, "Chi tiết tài khoản",
                f"Username: {account.get('username', 'N/A')}\n"
                f"Password: {account.get('password', 'N/A')}\n"
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
                "username": phone,
                "phone": phone,
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
        """Đăng nhập các tài khoản đã chọn"""
        selected_accounts = [acc for acc in self.accounts if acc.get('selected')]
        if not selected_accounts:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn ít nhất một tài khoản!")
            return

        # Tạo progress dialog
        progress = QProgressDialog("Đang đăng nhập tài khoản...", "Hủy", 0, len(selected_accounts), self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setWindowTitle("Đăng nhập tài khoản")
        progress.setAutoClose(True)
        progress.setAutoReset(True)

        # Đăng nhập từng tài khoản
        for i, account in enumerate(selected_accounts):
            if progress.wasCanceled():
                break

            username = account.get('username', '')
            progress.setLabelText(f"Đang đăng nhập {username}...")
            progress.setValue(i)

            try:
                # Khởi tạo driver với proxy nếu có
                proxy = None
                if self.use_proxy:
                    permanent_proxy = account.get('permanent_proxy', '').strip()
                    if permanent_proxy:
                        proxy = permanent_proxy
                    else:
                        proxy = account.get('proxy', '').strip()

                driver = self.init_driver(proxy=proxy, username=username)
                if not driver:
                    account['status'] = "Lỗi khởi tạo driver"
                    continue

                # Thêm vào danh sách active drivers
                self.active_drivers.append(driver)

                # Đăng nhập
                driver.get("https://web.telegram.org/k/")
                time.sleep(5)  # Chờ trang load

                # Kiểm tra đã đăng nhập chưa
                if "web.telegram.org/k/" in driver.current_url:
                    account['status'] = "Đã đăng nhập"
                else:
                    # Nhập số điện thoại
                    phone_input = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.NAME, "phone"))
                    )
                    phone_input.clear()
                    phone_input.send_keys(username)
                    time.sleep(1)

                    # Click nút Next/Submit
                    next_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
                    )
                    next_button.click()

                    # Đợi code OTP từ user
                    code, ok = QInputDialog.getText(
                        self, 
                        "Nhập mã OTP", 
                        f"Nhập mã OTP cho {username}:"
                    )
                    if ok and code:
                        # Nhập code OTP
                        code_input = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.NAME, "code"))
                        )
                        code_input.clear()
                        code_input.send_keys(code)
                        time.sleep(1)

                        # Kiểm tra kết quả đăng nhập
                        if "web.telegram.org/k/" in driver.current_url:
                            account['status'] = "Đã đăng nhập"
                        else:
                            account['status'] = "Đăng nhập thất bại"
                    else:
                        account['status'] = "Đã hủy đăng nhập"

            except Exception as e:
                print(f"[ERROR] Lỗi đăng nhập {username}: {e}")
                account['status'] = f"Lỗi: {str(e)[:50]}"

            finally:
                # Cập nhật UI
                self.save_accounts()
                self.update_account_table()

        progress.setValue(len(selected_accounts))
        QMessageBox.information(self, "Hoàn tất", "Đã hoàn tất quá trình đăng nhập!")

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
        selected_accounts = [acc for acc in self.accounts if acc.get('selected')]
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
            # Xóa tài khoản
            self.accounts = [acc for acc in self.accounts if not acc.get('selected')]
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
        selected_accounts = [acc for acc in self.accounts if acc.get('selected')]
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
        selected_accounts = [acc for acc in self.accounts if acc.get('selected')]
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
        selected_accounts = [acc for acc in self.accounts if acc.get('selected')]
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
        selected_accounts = [acc for acc in self.accounts if acc.get('selected')]
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
        selected_accounts = [acc for acc in self.accounts if acc.get('selected')]
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
        selected_accounts = [acc for acc in self.accounts if acc.get('selected')]
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
            
            # Username
            username_item = QTableWidgetItem(account.get('username', ''))
            self.account_table.setItem(row, 2, username_item)
            
            # Password
            password_item = QTableWidgetItem(account.get('password', ''))
            self.account_table.setItem(row, 3, password_item)
            
            # Status
            status_item = QTableWidgetItem(account.get('status', 'Chưa đăng nhập'))
            self.account_table.setItem(row, 4, status_item)

            # Proxy
            proxy_item = QTableWidgetItem(account.get('proxy', ''))
            self.account_table.setItem(row, 5, proxy_item)
            
            # Permanent Proxy
            permanent_proxy_item = QTableWidgetItem(account.get('permanent_proxy', ''))
            self.account_table.setItem(row, 6, permanent_proxy_item)
            
            # Proxy Status
            proxy_status_item = QTableWidgetItem(account.get('proxy_status', 'Chưa kiểm tra'))
            self.account_table.setItem(row, 7, proxy_status_item)
            
            # Followers
            followers_item = QTableWidgetItem(str(account.get('followers', '')))
            self.account_table.setItem(row, 8, followers_item)

            # Following
            following_item = QTableWidgetItem(str(account.get('following', '')))
            self.account_table.setItem(row, 9, following_item)
            
            # Last Action
            last_action_item = QTableWidgetItem(account.get('last_action', ''))
            self.account_table.setItem(row, 10, last_action_item)
        
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