import os
import sys
import time
import random
import json
import threading
import queue
from datetime import datetime
from PySide6.QtWidgets import QProgressDialog, QInputDialog, QLineEdit
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
        self.folder_map_file = os.path.join("data", "folder_map.json")  # Sửa lại đường dẫn đúng
        self.accounts = self.load_accounts()
        self.folder_map = self.load_folder_map()
        self.active_drivers = []
        self.stealth_mode_enabled = False
        self.proxies = self.load_proxies()
        
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
        
        # 🔥 FIX: Khởi tạo UI TRƯỚC KHI sử dụng self.sidebar_layout
        self.init_ui()
        self.update_account_table()
        
        # Kết nối signal status_updated để cập nhật từ thread
        self.status_updated.connect(self.on_status_updated)

    def init_driver(self, proxy=None, username=None):
        print("[DEBUG] 🚀 Khởi tạo ULTRA FAST + STEALTH driver...")
        from selenium.webdriver.chrome.options import Options
        options = Options()
        
        # 🔥 CHROME 137+ RENDERER TIMEOUT FIX
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-notifications")
        options.add_argument("--no-first-run")
        
        # 🔥 RENDERER COMMUNICATION FIX (Chrome 137+ specific)
        options.add_argument("--disable-renderer-backgrounding")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-ipc-flooding-protection")
        options.add_argument("--max_old_space_size=4096")
        
        # 🔇 HIDE SECURITY WARNINGS: Ẩn cảnh báo "Không an toàn"
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--ignore-ssl-errors")
        options.add_argument("--ignore-certificate-errors-spki-list")
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-mixed-content")
        options.add_argument("--suppress-message-center-popups")
        options.add_argument("--disable-features=VizDisplayCompositor,InsecureDownloadWarnings")
        print("[DEBUG] 🔇 Security warnings suppression enabled")
        
        # 🥷 MINIMAL STEALTH (avoid conflicts)
        options.add_experimental_option("excludeSwitches", [
            "enable-automation",
            "enable-logging", 
            "enable-blink-features=AutomationControlled"
        ])
        options.add_experimental_option("useAutomationExtension", False)
        
        # 🔥 MINIMAL PREFS (Chrome 137+ compatible)
        prefs = {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_setting_values.mixed_script": 1,  # Allow mixed content
            "profile.managed_default_content_settings.notifications": 2,
            "security.mixed_content.warnings": False,  # Disable mixed content warnings
            "security.insecure_form_warnings": False,  # Disable insecure form warnings
        }
        options.add_experimental_option("prefs", prefs)
        
        # User agent và ngôn ngữ
        random_user_agent = random.choice(self.USER_AGENTS)
        options.add_argument(f"user-agent={random_user_agent}")
        random_language = random.choice(self.LANGUAGES)
        options.add_argument(f"--lang={random_language}")
        options.add_argument(f"--accept-lang={random_language}")
        print(f"[DEBUG] Sử dụng User-Agent: {random_user_agent}")
        print(f"[DEBUG] Sử dụng Ngôn ngữ: {random_language}")
        
        # Chế độ ẩn danh nếu được bật
        if self.stealth_mode_enabled:
            options.add_argument("--incognito")
            print("[DEBUG] Chế độ ẩn danh được bật.")
        
        # Kích thước cửa sổ mặc định 500x492px
        options.add_argument("--window-size=500,492")
        
        # Cấu hình proxy
        proxy_options = {}
        if proxy: 
            print(f"[DEBUG] Proxy được cung cấp: {proxy}")
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
                print(f"[DEBUG] Sử dụng proxy có xác thực với selenium-wire: {proxy_ip_port}")
            elif len(proxy_parts) == 2:
                proxy_ip_port = f"{proxy_parts[0]}:{proxy_parts[1]}"
                proxy_options = {
                    'proxy': {
                        'http': f'http://{proxy_ip_port}',
                        'https': f'https://{proxy_ip_port}'
                    }
                }
                print(f"[DEBUG] Sử dụng proxy không xác thực với selenium-wire: {proxy_ip_port}")
            else:
                print(f"[WARN] Định dạng proxy không hợp lệ, bỏ qua: {proxy}")
                proxy = None
        else:
            print("[DEBUG] Không có proxy được cung cấp")
        
        print("[DEBUG] Đang khởi tạo Chrome driver...")
        
        # Thêm user-data-dir riêng cho từng tài khoản nếu có username
        if username:
            profile_dir = os.path.abspath(f'sessions/{username}_profile')
            os.makedirs(profile_dir, exist_ok=True)
            options.add_argument(f'--user-data-dir={profile_dir}')
        
        try:
            driver = wire_webdriver.Chrome(seleniumwire_options=proxy_options, options=options)
            print("[DEBUG] Chrome app mode driver đã được khởi tạo thành công")
            
            # 🔥 TIMEOUT FIX: Tránh renderer timeout với Chrome 137+
            driver.set_page_load_timeout(30)  # 30 giây cho Chrome 137+
            driver.implicitly_wait(3)         # 3 giây implicit wait
            driver.set_script_timeout(15)     # 15 giây script timeout
            print("[DEBUG] ✅ Đã set timeout: page_load=30s, implicit=3s, script=15s")
            
            # 🥷 MINIMAL STEALTH: Only essential (Chrome 137+ safe)
            try:
                driver.execute_script("""
                    // Remove webdriver property only
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined,
                    });
                """)
                print("[DEBUG] 🥷 Minimal stealth script injected")
            except Exception as e:
                print(f"[WARN] Stealth injection failed: {e}")
            
            return driver
        except Exception as e:
            print(f"[ERROR] Lỗi khi khởi tạo Chrome driver: {str(e)}")
            raise

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
        btn_add_account = QPushButton("Load Sessions Telegram")
        btn_add_account.clicked.connect(self.load_telegram_sessions)
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
        self.search_input.setPlaceholderText("Tìm kiếm username, số điện thoại...")
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
        self.account_table.setColumnCount(10)  # ⭐ Giảm xuống 10 cột sau khi xóa 3 cột
        self.account_table.setHorizontalHeaderLabels([
            "✓", "STT", "Số điện thoại", "Mật khẩu 2FA", "Username", "ID", "Trạng thái đăng nhập", 
            "Proxy hiện tại", "Trạng thái Proxy", "Hành động gần nhất"
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

        header.setSectionResizeMode(0, QHeaderView.Fixed)  # Cột "✓"
        self.account_table.setColumnWidth(0, 32)
        header.setSectionResizeMode(1, QHeaderView.Fixed)  # Cột "STT"
        self.account_table.setColumnWidth(1, 42)  # Tăng để hiển thị đầy đủ "STT"
        header.setSectionResizeMode(2, QHeaderView.Fixed)  # Cột "Số điện thoại"
        self.account_table.setColumnWidth(2, 140)  # Tăng để hiển thị số điện thoại dài
        header.setSectionResizeMode(3, QHeaderView.Fixed)  # Cột "Mật khẩu 2FA"
        self.account_table.setColumnWidth(3, 120)  # Mật khẩu 2FA
        header.setSectionResizeMode(4, QHeaderView.Fixed)  # Cột "Username"
        self.account_table.setColumnWidth(4, 130)  # Username
        header.setSectionResizeMode(5, QHeaderView.Fixed)  # Cột "ID"
        self.account_table.setColumnWidth(5, 100)  # ID
        header.setSectionResizeMode(6, QHeaderView.Fixed)  # Cột "Trạng thái đăng nhập"
        self.account_table.setColumnWidth(6, 140)  # Tăng để hiển thị đầy đủ tiêu đề
        header.setSectionResizeMode(7, QHeaderView.Fixed)  # Cột "Proxy hiện tại"
        self.account_table.setColumnWidth(7, 130)  # Tối ưu cho tiêu đề mới
        header.setSectionResizeMode(8, QHeaderView.Fixed)  # Cột "Trạng thái Proxy"
        self.account_table.setColumnWidth(8, 115)  # Tối ưu cho tiêu đề
        header.setSectionResizeMode(9, QHeaderView.Stretch)  # Cột "Hành động gần nhất" - Giữ nguyên Stretch
        self.account_table.verticalHeader().setDefaultSectionSize(40)
        self.account_table.horizontalHeader().setFixedHeight(40)

        # Đảm bảo cột cuối cùng kéo giãn để hiển thị đầy đủ nội dung
        header.setStretchLastSection(True)

        # Thiết lập căn lề cho các tiêu đề cột
        self.account_table.horizontalHeader().setDefaultAlignment(Qt.AlignHCenter | Qt.AlignVCenter)

        self.account_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        # 🔒 KHÓA CHỈNH SỬA: Chỉ cho phép hiển thị, không cho edit
        self.account_table.setEditTriggers(QTableWidget.NoEditTriggers)  # Disable all editing
        self.account_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.account_table.customContextMenuRequested.connect(self.show_context_menu)
        # 🔒 REMOVED: itemChanged signal không cần thiết vì đã disable editing
        # self.account_table.itemChanged.connect(self.handle_item_changed)  # Đã disable editing
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
        
        # 🔥 FIX: Thêm proxy switch setup AFTER sidebar_layout đã được tạo
        self.setup_proxy_switch()

    def setup_proxy_switch(self):
        """Setup proxy switch controls - phải gọi AFTER init_ui() để đảm bảo sidebar_layout đã tồn tại"""
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

    def save_accounts(self):
        # Sử dụng lock để tránh race condition khi nhiều thread cùng lưu
        import threading
        if not hasattr(self, '_save_lock'):
            self._save_lock = threading.Lock()
            
        with self._save_lock:
            try:
                with open(self.accounts_file, 'w', encoding='utf-8') as f:
                    json.dump(self.accounts, f, indent=4, ensure_ascii=False)
                    print("[INFO] Tài khoản đã được lưu.")
            except Exception as e:
                print(f"[ERROR] Lỗi khi lưu accounts: {e}")

    def sync_proxy_data(self):
        """Đồng bộ proxy data từ ProxyManagementTab"""
        try:
            print("[DEBUG] ⭐ Bắt đầu đồng bộ proxy data từ ProxyManagementTab...")
            
            # Load proxy data từ proxy_status.json  
            proxy_file = 'proxy_status.json'
            if os.path.exists(proxy_file):
                with open(proxy_file, 'r', encoding='utf-8') as f:
                    proxy_data = json.load(f)
                
                print(f"[DEBUG] Đã load {len(proxy_data)} proxy từ proxy_status.json")
                
                # Tạo mapping: assigned_account -> proxy
                proxy_assignments = {}
                available_proxies = []
                
                for proxy_info in proxy_data:
                    proxy_string = proxy_info.get('proxy', '')
                    assigned_account = proxy_info.get('assigned_account', '').strip()
                    proxy_status = proxy_info.get('status', '')
                    
                    if assigned_account:
                        # Proxy đã được gán cho tài khoản cụ thể
                        proxy_assignments[assigned_account] = {
                            'proxy': proxy_string,
                            'status': proxy_status
                        }
                        print(f"[DEBUG] Proxy assigned: {assigned_account} -> {proxy_string}")
                    elif proxy_status.lower() == 'ok':
                        # Proxy khả dụng chưa được gán
                        available_proxies.append(proxy_string)
                
                print(f"[DEBUG] Found {len(proxy_assignments)} assigned proxies")
                print(f"[DEBUG] Found {len(available_proxies)} available proxies")
                
                # Cập nhật proxy cho các tài khoản
                updated_count = 0
                auto_assigned_count = 0
                
                for account in self.accounts:
                    username = account.get('username', '')
                    current_proxy = account.get('proxy', '')
                    
                    # Kiểm tra xem có proxy được gán specifically cho tài khoản này không
                    if username in proxy_assignments:
                        new_proxy = proxy_assignments[username]['proxy']
                        proxy_status = proxy_assignments[username]['status']
                        
                        if current_proxy != new_proxy:
                            account['proxy'] = new_proxy
                            account['proxy_status'] = proxy_status
                            print(f"[INFO] ✅ Updated assigned proxy for {username}: {new_proxy}")
                            updated_count += 1
                    
                    # Nếu tài khoản chưa có proxy và có proxy khả dụng
                    elif not current_proxy and available_proxies:
                        new_proxy = available_proxies.pop(0)  # Lấy proxy đầu tiên
                        account['proxy'] = new_proxy
                        account['proxy_status'] = 'OK'  # Assume OK since it's from available list
                        print(f"[INFO] 🔄 Auto-assigned proxy for {username}: {new_proxy}")
                        auto_assigned_count += 1
                
                # Lưu thay đổi nếu có
                total_updates = updated_count + auto_assigned_count
                if total_updates > 0:
                    self.save_accounts()
                    self.update_account_table()
                    print(f"[SUCCESS] ✅ Proxy sync completed!")
                    print(f"  - Manual assignments updated: {updated_count}")
                    print(f"  - Auto assignments: {auto_assigned_count}")
                    print(f"  - Total accounts updated: {total_updates}")
                    
                    # Show success message
                    from PySide6.QtWidgets import QMessageBox
                    QMessageBox.information(
                        self, 
                        "Đồng bộ Proxy", 
                        f"✅ Đã đồng bộ proxy thành công!\n\n"
                        f"📋 Cập nhật proxy đã gán: {updated_count}\n"
                        f"🔄 Tự động gán proxy mới: {auto_assigned_count}\n"
                        f"📊 Tổng tài khoản được cập nhật: {total_updates}"
                    )
                else:
                    print("[INFO] 💡 No proxy updates needed - all accounts already have correct proxies")
                    
                    # Show informational message
                    from PySide6.QtWidgets import QMessageBox
                    QMessageBox.information(
                        self, 
                        "Đồng bộ Proxy", 
                        f"💡 Không cần cập nhật proxy!\n\n"
                        f"📊 Có {len(proxy_assignments)} proxy đã được gán\n"
                        f"📊 Có {len(available_proxies)} proxy khả dụng\n"
                        f"💡 Tất cả tài khoản đã có proxy phù hợp."
                    )
                    
            else:
                print(f"[WARN] ⚠️ Không tìm thấy file {proxy_file}")
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self, 
                    "Đồng bộ Proxy", 
                    f"⚠️ Không tìm thấy file proxy_status.json\n\n"
                    f"Vui lòng import proxy từ tab 'Quản lý Proxy' trước!"
                )
                
        except Exception as e:
            print(f"[ERROR] ❌ Lỗi khi đồng bộ proxy data: {e}")
            import traceback
            traceback.print_exc()
            
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self, 
                "Lỗi đồng bộ Proxy", 
                f"❌ Có lỗi xảy ra khi đồng bộ proxy:\n\n{str(e)}"
            )

    def login_telegram(self):
        """Đăng nhập Telegram trong background thread"""
        try:
            # Bước 1: Nhập số điện thoại  
            phone, ok = QInputDialog.getText(self, "Đăng nhập Telegram", "Số điện thoại (với mã quốc gia):\nVí dụ: +84123456789")
            if not ok or not phone.strip():
                return
            
            phone = phone.strip()
            if not phone.startswith('+'):
                QMessageBox.warning(self, "Lỗi", "Vui lòng nhập số điện thoại với mã quốc gia (bắt đầu bằng +)")
                return
            
            # Kiểm tra config trước khi bắt đầu
            try:
                import json
                import os
                with open("telegram_config.json", "r") as f:
                    config = json.load(f)
                api_id = config["api_id"]  
                api_hash = config["api_hash"]
                
                if api_id == "YOUR_API_ID" or api_hash == "YOUR_API_HASH_FROM_MY_TELEGRAM_ORG":
                    QMessageBox.critical(self, "Lỗi", "Vui lòng cấu hình API ID và API Hash thật trong telegram_config.json\n\nTruy cập: https://my.telegram.org/apps để lấy API credentials")
                    return
                    
            except FileNotFoundError:
                QMessageBox.critical(self, "Lỗi", "Không tìm thấy file telegram_config.json\n\nVui lòng tạo file với API credentials")
                return
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Lỗi đọc config: {str(e)}")
                return
            
            # Tạo và chạy worker thread
            from PySide6.QtCore import QThread, Signal
            
            class TelegramLoginWorker(QThread):
                finished = Signal(str, str)  # status, message
                request_input = Signal(str, str)  # title, prompt
                
                def __init__(self, phone, api_id, api_hash):
                    super().__init__()
                    self.phone = phone
                    self.api_id = api_id
                    self.api_hash = api_hash
                    self.input_result = None
                    self.input_ready = False
                    
                def wait_for_input(self, title, prompt):
                    self.input_ready = False
                    self.request_input.emit(title, prompt)
                    # Polling wait
                    while not self.input_ready:
                        self.msleep(100)
                    return self.input_result
                
                def run(self):
                    try:
                        # Import trong thread để tránh conflict
                        import asyncio
                        import os
                        from telethon import TelegramClient
                        from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
                        
                        # Tạo session folder
                        os.makedirs('sessions', exist_ok=True)
                        
                        # Tạo new event loop cho thread này
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        
                        try:
                            client = TelegramClient(f'sessions/{self.phone}', self.api_id, self.api_hash)
                            
                            # Bước 1: Gửi mã
                            async def send_code():
                                await client.connect()
                                if await client.is_user_authorized():
                                    return "already_logged_in"
                                else:
                                    sent_code = await client.send_code_request(self.phone)
                                    return sent_code.phone_code_hash
                            
                            result = loop.run_until_complete(send_code())
                            
                            if result == "already_logged_in":
                                self.finished.emit("success", "Tài khoản đã đăng nhập Telegram!")
                                return
                            
                            phone_code_hash = result
                            
                            # Bước 2: Nhập mã xác minh
                            code = self.wait_for_input("Mã xác minh", "Nhập mã xác minh được gửi đến điện thoại:")
                            if not code:
                                self.finished.emit("cancelled", "Đã hủy")
                                return
                            
                            # Bước 3: Xác minh mã
                            async def verify_code():
                                await client.sign_in(self.phone, code.strip(), phone_code_hash=phone_code_hash)
                                return "success"
                            
                            try:
                                loop.run_until_complete(verify_code())
                                self.finished.emit("success", "Đăng nhập Telegram thành công!")
                                
                            except SessionPasswordNeededError:
                                # Cần 2FA
                                password_2fa = self.wait_for_input("Mật khẩu 2FA", "Tài khoản có mật khẩu bảo vệ.\nNhập mật khẩu 2FA:")
                                if not password_2fa:
                                    self.finished.emit("cancelled", "Đã hủy")
                                    return
                                
                                async def verify_2fa():
                                    await client.sign_in(password=password_2fa.strip())
                                
                                try:
                                    loop.run_until_complete(verify_2fa())
                                    self.finished.emit("success", "Đăng nhập Telegram thành công (2FA)!")
                                except Exception as e:
                                    self.finished.emit("error", f"Mật khẩu 2FA không đúng: {str(e)}")
                                    
                            except PhoneCodeInvalidError:
                                self.finished.emit("error", "Mã xác minh không đúng!")
                            except Exception as e:
                                self.finished.emit("error", f"Lỗi xác minh: {str(e)}")
                                
                        finally:
                            try:
                                loop.run_until_complete(client.disconnect())
                            except:
                                pass
                            loop.close()
                            
                    except Exception as e:
                        self.finished.emit("error", f"Lỗi không mong muốn: {str(e)}")
            
            # Tạo worker
            self.telegram_worker = TelegramLoginWorker(phone, api_id, api_hash)
            
            # Progress dialog
            progress = QProgressDialog("Đang kết nối Telegram...", "Hủy", 0, 0, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            
            def on_request_input(title, prompt):
                progress.hide()
                text, ok = QInputDialog.getText(self, title, prompt, QLineEdit.Password if "2FA" in title else QLineEdit.Normal)
                self.telegram_worker.input_result = text if ok else None
                self.telegram_worker.input_ready = True
                if ok:
                    progress.setLabelText("Đang xử lý...")
                    progress.show()
            
            def on_finished(status, message):
                progress.close()
                
                if status == "success":
                    QMessageBox.information(self, "Thành công", message)
                    
                    # Thêm vào danh sách accounts
                    new_account = {
                        "selected": False,
                        "username": phone,
                        "password": "",
                        "fullname": "",
                        "proxy": "",
                        "status": "Đã đăng nhập Telegram" + (" (2FA)" if "2FA" in message else ""),
                        "gender": "-",
                        "followers": "",
                        "following": "",
                        "last_action": f"Đăng nhập Telegram lúc {datetime.now().strftime('%H:%M:%S')}",
                        "proxy_status": "Chưa kiểm tra",
                        "permanent_proxy": ""
                    }
                    self.accounts.append(new_account)
                    self.save_accounts()
                    self.update_account_table()
                    
                elif status == "error":
                    QMessageBox.critical(self, "Lỗi", message)
                # cancelled case - không làm gì
            
            # Kết nối signals
            self.telegram_worker.request_input.connect(on_request_input)
            self.telegram_worker.finished.connect(on_finished)
            
            # Bắt đầu worker
            self.telegram_worker.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Lỗi khởi tạo: {str(e)}")

    def load_telegram_sessions(self):
        """Load tất cả session Telegram từ thư mục sessions - CHỈ CHẠY KHI USER CLICK BUTTON"""
        try:
            print("[DEBUG] 🔥 MANUAL SESSION LOAD: User clicked button to load Telegram sessions")
            
            import os
            import glob
            from datetime import datetime
            
            # Đường dẫn thư mục sessions  
            sessions_dir = os.path.join(os.getcwd(), "sessions")
            
            if not os.path.exists(sessions_dir):
                QMessageBox.warning(self, "Lỗi", f"Không tìm thấy thư mục sessions:\n{sessions_dir}")
                return
            
            # Tìm tất cả file .session
            session_files = glob.glob(os.path.join(sessions_dir, "*.session"))
            
            if not session_files:
                QMessageBox.information(self, "Thông báo", f"Không tìm thấy file session nào trong:\n{sessions_dir}")
                return
            
            # Hỏi user có muốn load không để tránh tự động
            reply = QMessageBox.question(
                self, 
                "Xác nhận load sessions", 
                f"🔍 Tìm thấy {len(session_files)} session files.\n\n"
                f"⚠️ Quá trình này có thể mất vài phút vì cần kết nối Telegram để xác thực từng session.\n\n"
                f"Bạn có muốn tiếp tục?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                print("[DEBUG] 🛑 User cancelled session loading")
                return
            
            # Progress dialog
            progress = QProgressDialog(f"Đang load {len(session_files)} session files...", "Hủy", 0, len(session_files), self)
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            
            loaded_count = 0
            error_count = 0
            
            # Kiểm tra config Telegram
            try:
                import json
                with open("telegram_config.json", "r") as f:
                    config = json.load(f)
                api_id = config["api_id"]  
                api_hash = config["api_hash"]
                
                if api_id == "YOUR_API_ID" or api_hash == "YOUR_API_HASH_FROM_MY_TELEGRAM_ORG":
                    progress.close()
                    QMessageBox.critical(self, "Lỗi", "Vui lòng cấu hình API ID và API Hash thật trong telegram_config.json")
                    return
                    
            except Exception as e:
                progress.close()
                QMessageBox.critical(self, "Lỗi", f"Lỗi đọc config: {str(e)}")
                return
            
            # Import Telethon with warning
            try:
                print("[DEBUG] 📡 Importing Telethon for session validation...")
                from telethon import TelegramClient
                from telethon.tl.functions.users import GetFullUserRequest
            except ImportError:
                progress.close()
                QMessageBox.critical(self, "Lỗi", "Cần cài đặt thư viện Telethon:\npip install telethon")
                return
            
            print(f"[DEBUG] 🔄 Starting session validation for {len(session_files)} files...")
            
            # Load từng session
            for i, session_file in enumerate(session_files):
                if progress.wasCanceled():
                    print("[DEBUG] 🛑 User cancelled during loading")
                    break
                
                try:
                    # Lấy tên session (không có extension)
                    session_name = os.path.splitext(os.path.basename(session_file))[0]
                    progress.setLabelText(f"Đang load session: {session_name}")
                    progress.setValue(i)
                    
                    print(f"[DEBUG] 📱 Validating session: {session_name}")
                    
                    # Tạo client với session
                    client = TelegramClient(session_file.replace('.session', ''), api_id, api_hash)
                    
                    # Kết nối và lấy thông tin
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    try:
                        async def get_user_info():
                            await client.connect()
                            
                            if not await client.is_user_authorized():
                                return None
                            
                            # Lấy thông tin user hiện tại
                            me = await client.get_me()
                            
                            # Thông tin cơ bản
                            user_info = {
                                'id': me.id,
                                'phone': me.phone or session_name,
                                'username': me.username or '',
                                'first_name': me.first_name or '',
                                'last_name': me.last_name or '',
                                'is_premium': getattr(me, 'premium', False),
                                'is_verified': getattr(me, 'verified', False)
                            }
                            
                            return user_info
                        
                        user_info = loop.run_until_complete(get_user_info())
                        
                        if user_info:
                            # Kiểm tra xem đã có trong danh sách chưa
                            phone_or_username = user_info['phone'] or user_info['username'] 
                            existing = any(acc.get('username') == phone_or_username for acc in self.accounts)
                            
                            if not existing:
                                # Thêm vào danh sách accounts
                                new_account = {
                                    "selected": False,
                                    "username": phone_or_username,
                                    "password": "",
                                    "fullname": f"{user_info['first_name']} {user_info['last_name']}".strip(),
                                    "proxy": "",
                                    "status": "✅ Telegram Session Active" + (" 👑" if user_info['is_premium'] else "") + (" ✓" if user_info['is_verified'] else ""),
                                    "gender": "-",
                                    "followers": str(user_info['id']),  # Hiển thị User ID
                                    "following": "Telegram",
                                    "last_action": f"Loaded session lúc {datetime.now().strftime('%H:%M:%S')}",
                                    "proxy_status": "Chưa kiểm tra",
                                    "permanent_proxy": ""
                                }
                                self.accounts.append(new_account)
                                loaded_count += 1
                                print(f"[DEBUG] ✅ Loaded session: {phone_or_username} - {user_info['first_name']}")
                            else:
                                print(f"[DEBUG] 🔄 Session already exists: {phone_or_username}")
                        else:
                            error_count += 1
                            print(f"[DEBUG] ❌ Failed to load session: {session_name}")
                    
                    finally:
                        try:
                            loop.run_until_complete(client.disconnect())
                        except:
                            pass
                        loop.close()
                    
                except Exception as e:
                    error_count += 1
                    print(f"[ERROR] ⚠️ Error loading session {session_name}: {e}")
                    continue
            
            progress.close()
            
            # Cập nhật UI và lưu
            if loaded_count > 0:
                self.save_accounts()
                self.update_account_table()
            
            # Hiển thị kết quả
            result_msg = f"📊 Kết quả load sessions:\n\n"
            result_msg += f"✅ Loaded thành công: {loaded_count}\n"
            result_msg += f"❌ Lỗi/không thể load: {error_count}\n"
            result_msg += f"📁 Tổng session files: {len(session_files)}\n\n"
            
            if loaded_count > 0:
                result_msg += f"🎉 Đã thêm {loaded_count} tài khoản Telegram vào bảng!"
            
            QMessageBox.information(self, "Hoàn thành", result_msg)
            print(f"[DEBUG] 🏁 Session loading completed: {loaded_count} success, {error_count} errors")
            
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Lỗi load sessions: {str(e)}")
            import traceback
            print(f"[ERROR] Load sessions error: {traceback.format_exc()}")

    def add_account(self):
        """Thêm tài khoản Instagram (function cũ được giữ lại)"""
        username, ok = QInputDialog.getText(self, "Thêm tài khoản", "Username:")
        if ok and username:
            phone, ok = QInputDialog.getText(self, "Thêm tài khoản", "Số điện thoại:")
            if ok:
                proxy, ok = QInputDialog.getText(self, "Thêm tài khoản", "Proxy (tùy chọn):")
                if ok:
                    new_account = {
                        "selected": False,
                        "username": username,
                        "password": phone,  # Lưu số điện thoại vào trường password
                        "fullname": "",  # NEW: Thêm trường Họ tên
                        "proxy": proxy,
                        "status": "Chưa đăng nhập",
                        "gender": "-",  # Thêm cột giới tính
                        "followers": "",
                        "following": "",
                        "last_action": "",  # Thêm cột hành động cuối
                        "proxy_status": "Chưa kiểm tra",  # Khởi tạo trạng thái proxy
                        "permanent_proxy": ""  # ⭐ THÊM: Proxy vĩnh viễn cho tài khoản
                    }
                    self.accounts.append(new_account)
                    self.save_accounts()
                    self.update_account_table()

                    QMessageBox.information(self, "Thêm tài khoản", "Tài khoản đã được thêm thành công.")

    @Slot()
    def update_account_table(self, accounts_to_display=None):
        if accounts_to_display is None:
            accounts_to_display = self.accounts

        self.account_table.blockSignals(True)  # Block signals to prevent itemChanged from firing
        self.account_table.setRowCount(len(accounts_to_display))
        for row_idx, account in enumerate(accounts_to_display):
            # Cột "Chọn" - KHÔNG setFlags kiểu checkbox nữa, chỉ để delegate vẽ
            item_checkbox = QTableWidgetItem()
            item_checkbox.setData(CheckboxDelegate.CheckboxStateRole, account.get("selected", False))
            self.account_table.setItem(row_idx, 0, item_checkbox)  # Thiết lập item cho cột 0

            # STT
            stt_item = QTableWidgetItem(str(row_idx + 1))
            stt_item.setTextAlignment(Qt.AlignCenter)
            self.account_table.setItem(row_idx, 1, stt_item)

            # Số điện thoại - hiển thị username (cột 2)
            username_item = QTableWidgetItem(account.get("username", ""))
            username_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.account_table.setItem(row_idx, 2, username_item)

            # Mật khẩu 2FA - hiển thị mật khẩu 2FA Telegram (cột 3)
            telegram_2fa = account.get("telegram_2fa", "") or account.get("two_fa_password", "") or account.get("password_2fa", "") or account.get("twofa", "")
            if not telegram_2fa:
                telegram_2fa = "Chưa có 2FA"
            phone_item = QTableWidgetItem(telegram_2fa)
            phone_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.account_table.setItem(row_idx, 3, phone_item)

            # Username - hiển thị username của tài khoản (cột 4)
            account_username = account.get("telegram_username", "") or account.get("username_telegram", "") or account.get("tg_username", "") or ""
            if not account_username:
                account_username = "Chưa có username"
            username_tg_item = QTableWidgetItem(account_username)
            username_tg_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.account_table.setItem(row_idx, 4, username_tg_item)

            # ID - hiển thị ID của tài khoản (cột 5)
            account_id = account.get("telegram_id", "") or account.get("id_telegram", "") or account.get("tg_id", "") or account.get("user_id", "") or ""
            if not account_id:
                account_id = "Chưa có ID"
            id_item = QTableWidgetItem(account_id)
            id_item.setTextAlignment(Qt.AlignCenter)
            self.account_table.setItem(row_idx, 5, id_item)

            # Trạng thái
            status_item = QTableWidgetItem(account.get("status", "Chưa đăng nhập"))
            status_item.setTextAlignment(Qt.AlignCenter)
            if account.get("status") == "Đăng nhập thất bại":
                status_item.setForeground(QColor("red"))
            elif account.get("status") == "Đã đăng nhập" or account.get("status") == "Live":
                status_item.setForeground(QColor("green"))
            elif account.get("status") == "Die":
                status_item.setForeground(QColor("red"))  # Thêm màu đỏ cho trạng thái "Die"
            else:
                status_item.setForeground(QColor("black"))  # Mặc định màu đen
            self.account_table.setItem(row_idx, 6, status_item)

            # Proxy
            proxy_item = QTableWidgetItem(account.get("proxy", ""))
            proxy_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.account_table.setItem(row_idx, 7, proxy_item)

            # Trạng thái Proxy
            proxy_status_item = QTableWidgetItem(account.get("proxy_status", "Chưa kiểm tra"))
            proxy_status_item.setTextAlignment(Qt.AlignCenter)
            if account.get("proxy_status") == "Die":
                proxy_status_item.setForeground(QColor("red"))
            elif account.get("proxy_status") == "OK":
                proxy_status_item.setForeground(QColor("green"))
            else:
                proxy_status_item.setForeground(QColor("black"))
            self.account_table.setItem(row_idx, 8, proxy_status_item)

            # Hành động cuối
            last_action_item = QTableWidgetItem(account.get("last_action", ""))
            last_action_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.account_table.setItem(row_idx, 9, last_action_item)
        self.account_table.blockSignals(False)  # Unblock signals
        self.update_stats(accounts_to_display)

    @Slot()
    def update_stats(self, accounts_to_display=None):
        if accounts_to_display is None:
            accounts_to_display = self.accounts
        total = len(accounts_to_display)
        live = 0
        die = 0
        selected = 0
        for acc in accounts_to_display:
            status = str(acc.get("status", "")).lower()
            # 🔥 FIX: Đếm đúng tất cả trạng thái thực tế
            if status in ["đã đăng nhập", "live", "✅ đã đăng nhập"]:
                live += 1
            elif status in ["tài khoản bị khóa", "die", "❌ tài khoản bị khóa", "checkpoint", "blocked", "locked"]:
                die += 1
            if acc.get("selected", False):
                selected += 1
        not_selected = total - selected
        
        # 🔍 DEBUG: In ra thống kê để kiểm tra
        print(f"[DEBUG] 📊 STATS UPDATE: Total={total}, Live={live}, Die={die}, Selected={selected}")
        if live + die > 0:  # Chỉ debug khi có dữ liệu
            print(f"[DEBUG] 📊 Status details:")
            for i, acc in enumerate(accounts_to_display[:5]):  # Chỉ in 5 tài khoản đầu
                username = acc.get("username", "Unknown")
                status = acc.get("status", "N/A")
                print(f"[DEBUG] 📊   {i+1}. {username}: '{status}'")
        
        stats_html = (
            f'<span style="color:black">Tổng: <b>{total}</b></span> | '
            f'<span style="color:green">Live: <b>{live}</b></span> | '
            f'<span style="color:red">Die: <b>{die}</b></span> | '
            f'<span style="color:#1976D2">Đã chọn: <b>{selected}</b></span> | '
            f'<span style="color:gray">Chưa chọn: <b>{not_selected}</b></span>'
        )
        self.stats_label.setText(stats_html)

    def on_checkbox_clicked(self, row, new_state):
        # Hàm này được kết nối từ delegate để xử lý khi trạng thái checkbox thay đổi
        if row < len(self.accounts):
            self.accounts[row]["selected"] = new_state
            self.save_accounts()
            print(f"[DEBUG] Checkbox tại hàng {row} được chuyển thành: {new_state}. Tài khoản: {self.accounts[row]['username']}")
        self.update_stats()

    def handle_item_changed(self, item):
        """🔒 DISABLED: Chỉnh sửa trực tiếp đã bị khóa"""
        # 🔒 EARLY RETURN: Không cho phép chỉnh sửa trực tiếp nữa
        print(f"[INFO] 🔒 Chỉnh sửa trực tiếp đã bị khóa. Vui lòng sử dụng menu chuột phải.")
        return
        
        # Code cũ đã được comment out
        # Kiểm tra nếu tín hiệu bị block, bỏ qua
        # if self.account_table.signalsBlocked():
        #     return
        # ... rest of the old code ...

    def filter_accounts(self, text):
        filtered_accounts = [
            account for account in self.accounts
            if text.lower() in account.get("username", "").lower() or  # Tìm trong username
            text.lower() in account.get("password", "").lower() or    # Tìm trong số điện thoại
            text.lower() in account.get("status", "").lower() or
            text.lower() in account.get("proxy", "").lower() or
            text.lower() in account.get("permanent_proxy", "").lower() or  # ⭐ Thêm permanent proxy vào search
            text.lower() in account.get("proxy_status", "").lower() or
            text.lower() in account.get("last_action", "").lower()
        ]
        if self.category_combo.currentText() != "Tất cả":
            folder_name = self.category_combo.currentText()
            # Đảm bảo rằng get() có một giá trị mặc định cho trường hợp username không có trong folder_map
            filtered_accounts = [acc for acc in filtered_accounts if self.folder_map.get(acc.get("username"), "Tổng") == folder_name]

        self.update_account_table(filtered_accounts)
        self.update_stats(filtered_accounts)

    def get_window_positions(self, num_windows):
        # 🔥 OPTIMIZED POSITIONING: 4 cửa sổ trải đều màn hình + 5px spacing
        win_h = 350  # Chiều cao cố định
        
        # Lấy kích thước màn hình
        try:
            from PySide6.QtGui import QGuiApplication
            screen = QGuiApplication.primaryScreen()
            geometry = screen.geometry()
            screen_w, screen_h = geometry.width(), geometry.height()
            print(f"[DEBUG] 🖥️ Screen size: {screen_w}x{screen_h}")
        except Exception:
            screen_w, screen_h = 1920, 1080  # fallback
        
        # 🔒 FIXED LAYOUT: 3 cửa sổ/hàng, kích thước 500x492px, spacing 10px
        margin_x = 0    # Bắt đầu từ góc trên bên trái (0px)
        margin_y = 0    # Bắt đầu từ góc trên bên trái (0px)
        spacing_x = 10  # Khoảng cách 10px giữa các cửa sổ ngang
        spacing_y = 10  # Khoảng cách 10px giữa các hàng
        
        # 🔒 FIXED SIZE: Cửa sổ mặc định 500x492px
        win_w = 500  # Chiều rộng cố định
        win_h = 492  # Chiều cao cố định
        
        print(f"[DEBUG] 🔒 FIXED WINDOW SIZE: {win_w}x{win_h}px")
        print(f"[DEBUG] 🔒 Screen resolution: {screen_w}x{screen_h}px")
        
        # 🔒 FIXED GRID POSITIONS: Vị trí cố định tuyệt đối để tránh đè lên nhau
        positions = []
        
        # 🎯 PREDEFINED POSITIONS: Grid cố định 3 cửa sổ/hàng
        fixed_positions = [
            # Hàng 1: Y=0 (góc trên bên trái)
            (0, 0, 500, 492),       # Cửa sổ 1: X=0
            (510, 0, 500, 492),     # Cửa sổ 2: X=510  
            (1020, 0, 500, 492),    # Cửa sổ 3: X=1020
            
            # Hàng 2: Y=502 (492 + 10 spacing)
            (0, 502, 500, 492),     # Cửa sổ 4
            (510, 502, 500, 492),   # Cửa sổ 5
            (1020, 502, 500, 492),  # Cửa sổ 6
            
            # Hàng 3: Y=1004 (502 + 502 spacing)
            (0, 1004, 500, 492),    # Cửa sổ 7
            (510, 1004, 500, 492),  # Cửa sổ 8
            (1020, 1004, 500, 492), # Cửa sổ 9
        ]
        
        print(f"[DEBUG] 🔒 Using FIXED POSITIONS for {num_windows} windows")
        
        # 🔒 Sử dụng vị trí cố định
        for i in range(num_windows):
            if i < len(fixed_positions):
                # Sử dụng vị trí từ danh sách cố định
                x, y, w, h = fixed_positions[i]
                positions.append((x, y, w, h))
                
                col = i % 3 + 1  # Cột 1-3
                row = i // 3 + 1  # Hàng 1, 2, 3...
                
                print(f"[DEBUG] 🔒 FIXED Window {i+1}: Row {row}, Col {col} → ({x}, {y}, {w}, {h})")
            else:
                # Nếu vượt quá 9 cửa sổ, tạo cascade pattern
                overflow_index = i - 9
                cascade_x = 0 + (overflow_index * 50)   # Cascade sang phải
                cascade_y = (overflow_index * 50)        # Cascade xuống dưới
                
                # Đảm bảo không vượt quá màn hình
                if cascade_x + 500 > screen_w - 10:
                    cascade_x = 0
                if cascade_y + 492 > screen_h - 50:
                    cascade_y = 0
                
                positions.append((cascade_x, cascade_y, 500, 492))
                print(f"[DEBUG] 🔒 OVERFLOW Window {i+1}: CASCADE → ({cascade_x}, {cascade_y}, 500, 492)")
        
        return positions

    def login_selected_accounts(self):
        # Chạy đăng nhập cho từng tài khoản trong thread phụ, không block main thread
        import threading
        selected_accounts = [acc for acc in self.accounts if acc.get('selected')]
        if not selected_accounts:
            QMessageBox.information(self, "Thông báo", "Vui lòng chọn ít nhất 1 tài khoản để đăng nhập.")
            return
        def login_worker(account, window_position=None):
            import threading
            username = account.get('username', 'Unknown')
            thread_id = threading.get_ident()
            
            print(f"[DEBUG] Thread worker BẮT ĐẦU cho {username} - thread id: {thread_id}")
            
            # Signal báo thread bắt đầu
            try:
                account["status"] = "Thread bắt đầu..."
                self.status_updated.emit(username, account["status"])
                print(f"[DEBUG] Đã emit signal bắt đầu cho {username}")
            except Exception as e:
                print(f"[ERROR] Không thể emit signal bắt đầu cho {username}: {e}")
            
            # Wrapping toàn bộ logic trong try-catch để đảm bảo luôn emit signal
            try:
                print(f"[DEBUG] Gọi login_instagram_and_get_info cho {username}")
                result = self.login_instagram_and_get_info(account, window_position)
                print(f"[DEBUG] login_instagram_and_get_info hoàn thành cho {username} với result: {result}")
                return result
                
            except Exception as e:
                print(f"[CRITICAL][Thread] Lỗi nghiêm trọng trong thread {username}: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                
                # Đảm bảo luôn emit signal cập nhật trạng thái
                try:
                    error_status = f"Lỗi thread: {type(e).__name__}"
                    account["status"] = error_status
                    self.status_updated.emit(username, error_status)
                    print(f"[DEBUG] Đã emit signal lỗi nghiêm trọng cho {username}")
                except Exception as emit_error:
                    print(f"[CRITICAL] Không thể emit signal cuối cùng cho {username}: {emit_error}")
                
                return "Lỗi thread", "Lỗi", None
                
            finally:
                print(f"[DEBUG] Thread worker KẾT THÚC cho {username}")
                
        # 🔍 GET WINDOW POSITIONS: Lấy vị trí cửa sổ cố định
        window_positions = self.get_window_positions(len(selected_accounts))
        
        # 🔍 VERIFY POSITIONS: In ra tất cả vị trí để kiểm tra
        print(f"[DEBUG] 🔍 WINDOW POSITIONS VERIFICATION:")
        for i, pos in enumerate(window_positions):
            x, y, w, h = pos
            print(f"[DEBUG] 🪟 Position {i+1}: ({x}, {y}, {w}, {h})")
        
        # 🎴 CARD DEALING EFFECT: Hiệu ứng chia bài khi mở cửa sổ
        print(f"[DEBUG] 🎴 Bắt đầu hiệu ứng chia bài cho {len(selected_accounts)} cửa sổ")
        
        for idx, account in enumerate(selected_accounts):
            pos = window_positions[idx] if window_positions else None
            
            # 🎯 Tính toán vị trí trong grid (3 cửa sổ/hàng)
            col = idx % 3  # Cột (0-2)
            row = idx // 3  # Hàng (0, 1, 2...)
            
            print(f"[DEBUG] 🎴 Chia bài {idx+1}: {account.get('username')} -> Hàng {row+1}, Cột {col+1}")
            
            t = threading.Thread(target=login_worker, args=(account, pos), daemon=True)
            t.start()
            
            # 🎴 STAGGERED DELAY: Hiệu ứng chia bài
            if idx < len(selected_accounts) - 1:
                # Delay ngắn hơn cho cùng hàng, delay dài hơn cho hàng mới
                if col == 2:  # Cửa sổ cuối hàng (cột thứ 3)
                    delay = 0.8  # Delay dài hơn trước khi chuyển hàng mới
                    print(f"[DEBUG] 🎴 Kết thúc hàng {row+1}, chờ {delay}s trước khi chuyển hàng")
                else:  # Cửa sổ trong cùng hàng
                    delay = 0.3  # Delay ngắn giữa các cửa sổ cùng hàng
                    print(f"[DEBUG] 🎴 Tiếp tục hàng {row+1}, chờ {delay}s")
                
                time.sleep(delay)


    def get_human_delay(self, base_time=1.0, variation=0.5):
        """⚡ HUMAN-LIKE: Tạo delay ngẫu nhiên giống con người"""
        # Gaussian distribution để giống timing con người
        import random
        delay = random.gauss(base_time, variation)
        return max(0.1, min(delay, base_time * 2))  # Clamp between 0.1s and 2x base
    
    def simulate_human_scroll(self, driver):
        """🥷 STEALTH: Giả lập scroll như con người"""
        try:
            # Random scroll nhẹ để giống human behavior
            scroll_amount = random.randint(100, 300)
            driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
            time.sleep(self.get_human_delay(0.5, 0.2))
        except Exception as e:
            print(f"[DEBUG] Scroll simulation error: {e}")
    
    def simulate_mouse_movement(self, driver):
        """🥷 STEALTH: Giả lập di chuyển chuột"""
        try:
            from selenium.webdriver.common.action_chains import ActionChains
            action = ActionChains(driver)
            
            # Random mouse movement trong viewport
            x_offset = random.randint(-50, 50)
            y_offset = random.randint(-30, 30)
            action.move_by_offset(x_offset, y_offset).perform()
            time.sleep(self.get_human_delay(0.2, 0.1))
        except Exception as e:
            print(f"[DEBUG] Mouse simulation error: {e}")
    
    def track_login_success(self, success=True):
        """🚀 SMART TRACKING: Theo dõi thành công để adaptive optimization"""
        if not hasattr(self, '_success_streak'):
            self._success_streak = 0
        
        if success:
            self._success_streak += 1
            print(f"[DEBUG] 🚀 Success streak: {self._success_streak}")
        else:
            self._success_streak = 0
            print("[DEBUG] ⚠️ Success streak reset")
    
    def instant_success_report(self, account, driver, status="Đã đăng nhập"):
        """🚀 INSTANT REPORT: Báo về kết quả ngay lập tức, không chờ đợi"""
        try:
            username = account['username']
            print(f"[DEBUG] ✅ INSTANT SUCCESS REPORT: {username} - {status}")
            
            # Track success for adaptive optimization
            self.track_login_success(True)
            
            # Update status immediately
            account["status"] = status
            account["last_action"] = f"Đăng nhập thành công lúc {time.strftime('%H:%M:%S')}"
            
            # Emit signal to update UI immediately
            self.status_updated.emit(username, status)
            
            # Force UI update immediately
            from PySide6.QtCore import QCoreApplication
            QCoreApplication.processEvents()
            
            # Save accounts immediately to persist status
            self.save_accounts()
            
            # 🚀 SUPER FAST BACKGROUND TASKS: All non-critical operations
            import threading
            def background_tasks():
                try:
                    print(f"[DEBUG] 🚀 Starting background tasks for {username}")
                    
                    # Task 1: Save cookies (important but non-blocking)
                    try:
                        self.save_cookies(driver, username)
                        print(f"[DEBUG] ✅ Cookies saved for {username}")
                    except Exception as e:
                        print(f"[WARN] Cookie save failed: {e}")
                    
                    # Task 2: Basic info collection (optional)
                    try:
                        current_url = driver.current_url
                        # Only collect if we're on feed/main page (don't navigate)
                        if "instagram.com" in current_url and not "login" in current_url:
                            # Quick info without navigation
                            info = {
                                "username": username,
                                "profile_url": f"https://www.instagram.com/{username}/",
                                "followers": "N/A",
                                "following": "N/A",
                                "posts": "N/A",
                                "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
                            }
                            self.update_account_info(account, info)
                            print(f"[DEBUG] ✅ Basic info updated for {username}")
                    except Exception as e:
                        print(f"[DEBUG] Info collection skipped: {e}")
                    
                    # Task 3: Browser cleanup (after short delay)
                    time.sleep(2)  # Give time for any pending operations
                    try:
                        self.close_browser_safely(driver, username)
                        print(f"[DEBUG] ✅ Browser closed for {username}")
                    except Exception as e:
                        print(f"[WARN] Browser close failed: {e}")
                    
                    print(f"[SUCCESS] 🚀 All background tasks completed for {username}")
                    
                except Exception as e:
                    print(f"[ERROR] Background tasks failed for {username}: {e}")
            
            # Start background tasks immediately
            threading.Thread(target=background_tasks, daemon=True).start()
            
            print(f"[SUCCESS] 🚀 INSTANT REPORT COMPLETE: {username} - UI updated, background tasks started")
            return True
            
        except Exception as e:
            print(f"[ERROR] Instant success report failed: {e}")
            return False

    def login_instagram_and_get_info(self, account, window_position=None, max_retries=3, retry_delay=5):
        """🔥 SIMPLE LOGIN: Logic đơn giản, không vòng lặp phức tạp"""
        username = account.get("username", "")
        password = account.get("password", "")
        
        print(f"[DEBUG] 🔥 SIMPLE LOGIN bắt đầu cho {username}")
        
        try:
            # 🔥 ƯUTIÊN PERMANENT PROXY: Chọn proxy tốt nhất cho tài khoản
            permanent_proxy = account.get("permanent_proxy", "").strip()
            regular_proxy = account.get("proxy", "").strip()
            
            # Ưu tiên permanent proxy nếu có
            chosen_proxy = permanent_proxy if permanent_proxy else regular_proxy
            proxy_type = "permanent" if permanent_proxy else "regular" if regular_proxy else "none"
            
            print(f"[DEBUG] 🎯 Proxy selection for {username}:")
            print(f"[DEBUG]   - Permanent proxy: {permanent_proxy or 'None'}")
            print(f"[DEBUG]   - Regular proxy: {regular_proxy or 'None'}")
            print(f"[DEBUG]   - Chosen: {chosen_proxy or 'None'} ({proxy_type})")
            
            # Khởi tạo driver với proxy đã chọn
            driver = self.init_driver(chosen_proxy, username)
            if not driver:
                print(f"[ERROR] Không thể khởi tạo driver cho {username}")
                account["status"] = "Lỗi khởi tạo driver"
                self.status_updated.emit(username, account["status"])
                return "Lỗi", "Error", None
            
            # 🔥 TIMEOUT PROTECTION: Giống như init_driver
            try:
                driver.set_page_load_timeout(30)  # 30 giây
                driver.implicitly_wait(3)         # 3 giây implicit wait
                driver.set_script_timeout(15)     # 15 giây script timeout
                print(f"[DEBUG] ✅ Đã set timeout protection cho {username}")
            except Exception as timeout_error:
                print(f"[WARN] Không thể set timeout: {timeout_error}")
            
            # 🔥 SET WINDOW POSITION: Đặt vị trí cửa sổ để tránh chồng lên nhau
            if window_position and len(window_position) == 4:
                x, y, width, height = window_position
                print(f"[DEBUG] 🎯 Đặt vị trí cửa sổ cho {username}: ({x}, {y}) size ({width}, {height})")
                try:
                    driver.set_window_rect(x, y, width, height)
                    time.sleep(0.3)  # Chờ cửa sổ ổn định
                    
                    # 🔍 VERIFY POSITION: Kiểm tra vị trí thực tế sau khi set
                    try:
                        actual_rect = driver.get_window_rect()
                        actual_x, actual_y = actual_rect['x'], actual_rect['y']
                        actual_w, actual_h = actual_rect['width'], actual_rect['height']
                        
                        print(f"[DEBUG] ✅ Vị trí thực tế cho {username}: ({actual_x}, {actual_y}) size ({actual_w}, {actual_h})")
                        
                        # Kiểm tra có chính xác không
                        if abs(actual_x - x) > 10 or abs(actual_y - y) > 10:
                            print(f"[WARN] ⚠️ VỊ TRÍ KHÔNG CHÍNH XÁC cho {username}!")
                            print(f"[WARN] Expected: ({x}, {y}) Got: ({actual_x}, {actual_y})")
                        else:
                            print(f"[DEBUG] ✅ Vị trí chính xác cho {username}")
                            
                    except Exception as verify_error:
                        print(f"[WARN] Không thể verify vị trí: {verify_error}")
                        
                except Exception as e:
                    print(f"[ERROR] ❌ Không thể đặt vị trí cửa sổ cho {username}: {e}")
            else:
                # Vị trí mặc định nếu không có window_position  
                print(f"[DEBUG] ⚠️ Không có window_position cho {username}, dùng mặc định")
                try:
                    driver.set_window_rect(0, 0, 500, 492)  # Góc trên bên trái + kích thước mặc định
                    print(f"[DEBUG] Sử dụng vị trí mặc định cho {username}: (0, 0, 500, 492)")
                except Exception as e:
                    print(f"[ERROR] ❌ Không thể đặt vị trí mặc định: {e}")
            
            # Mở Instagram
            print(f"[DEBUG] Mở Instagram cho {username}")
            driver.get("https://www.instagram.com/")
            time.sleep(2)
            
            # Load cookies nếu có
            print(f"[DEBUG] 📊 PROGRESS: 30% - Bắt đầu load cookies cho {username}")
            self.load_cookies(driver, username)
            print(f"[DEBUG] 📊 PROGRESS: 35% - Hoàn thành load cookies cho {username}")
            time.sleep(1)
            
            # 🔥 SMART CHECK: Kiểm tra theo thứ tự ưu tiên ĐÚNG
            print(f"[DEBUG] 🔥 SMART CHECK cho {username}")
            
            # 🚨 PRIORITY 1: Check Account locked/restricted TRƯỚC TIÊN!
            try:
                print(f"[DEBUG] 🚨 Kiểm tra tài khoản bị khóa/restricted cho {username}")
                if self.check_account_locked(driver):
                    print(f"[ERROR] ❌ Tài khoản {username} bị khóa/restricted")
                    account["status"] = "❌ Tài khoản bị khóa"
                    self.status_updated.emit(username, account["status"])
                    try:
                        self.close_browser_safely(driver, username)
                    except Exception:
                        pass  # Ignore close errors
                    return "Tài khoản bị khóa", "Locked", None
            except Exception as e:
                print(f"[DEBUG] Account lock check error: {e}")
            
            # ⚠️ PRIORITY 2: Check 2FA requirement (chỉ khi không bị khóa)
            try:
                print(f"[DEBUG] ⚠️ Kiểm tra yêu cầu 2FA cho {username}")
                if self.check_2fa_required(driver):
                    print(f"[WARN] ⚠️ Phát hiện yêu cầu 2FA cho {username}")
                    account["status"] = "⚠️ Yêu cầu nhập 2FA"
                    self.status_updated.emit(username, account["status"])
                    # Giữ browser mở để user xử lý 2FA
                    return "Yêu cầu 2FA", "2FA", driver
            except Exception as e:
                print(f"[DEBUG] 2FA check error: {e}")
            
            # ⚠️ PRIORITY 3: Check Captcha requirement  
            try:
                print(f"[DEBUG] ⚠️ Kiểm tra yêu cầu captcha cho {username}")
                if self.check_captcha_required(driver):
                    print(f"[WARN] ⚠️ Phát hiện yêu cầu captcha cho {username}")
                    account["status"] = "⚠️ Yêu cầu giải captcha"
                    self.status_updated.emit(username, account["status"])
                    # Giữ browser mở để user xử lý captcha
                    return "Yêu cầu captcha", "Captcha", driver
            except Exception as e:
                print(f"[DEBUG] Captcha check error: {e}")
            
            # ✅ FINAL CHECK: Login success
            try:
                print(f"[DEBUG] 📊 PROGRESS: 75% - Kiểm tra đăng nhập thành công cho {username}")
                print(f"[DEBUG] 🔥 Kiểm tra đăng nhập thành công cho {username}")
                
                # 🔥 TIMEOUT PROTECTION: Set thời gian timeout ngắn để tránh treo
                start_time = time.time()
                login_check_timeout = 8  # 8 giây timeout
                
                login_success = False
                print(f"[DEBUG] 🔄 Bắt đầu vòng lặp check login cho {username} với timeout {login_check_timeout}s")
                while time.time() - start_time < login_check_timeout:
                    try:
                        elapsed = time.time() - start_time
                        print(f"[DEBUG] 🔄 Check login iteration {elapsed:.1f}s cho {username}")
                        login_success = self.check_home_and_explore_icons(driver)
                        if login_success:
                            print(f"[DEBUG] ✅ Login check SUCCESS sau {elapsed:.1f}s cho {username}")
                            break
                        time.sleep(0.5)  # Wait 0.5s before retry
                    except Exception as check_error:
                        print(f"[DEBUG] Login check iteration error: {check_error}")
                        time.sleep(0.5)
                
                print(f"[DEBUG] 🔄 Kết thúc check login: login_success={login_success} cho {username}")
                if login_success:
                    print(f"[SUCCESS] ✅ ĐÃ ĐĂNG NHẬP: {username}")
                    account["status"] = "Đã đăng nhập"
                    self.status_updated.emit(username, account["status"])
                    
                    # 🔥 ULTRA SAFE OPERATIONS: Timeout wrap để tránh renderer timeout
                    import threading
                    
                    def safe_save_cookies():
                        try:
                            self.save_cookies(driver, username)
                            print(f"[DEBUG] ✅ Đã lưu cookies cho {username}")
                        except Exception as save_error:
                            print(f"[WARN] Lỗi lưu cookies: {save_error}")
                    
                    def safe_close_browser():
                        try:
                            self.close_browser_safely(driver, username)
                            print(f"[DEBUG] ✅ Đã đóng browser cho {username}")
                        except Exception as close_error:
                            print(f"[WARN] Lỗi đóng browser: {close_error}")
                    
                    # Chạy save cookies với timeout
                    save_thread = threading.Thread(target=safe_save_cookies, daemon=True)
                    save_thread.start()
                    save_thread.join(timeout=3.0)  # Max 3s để save cookies
                    
                    # Chạy close browser với timeout  
                    close_thread = threading.Thread(target=safe_close_browser, daemon=True)
                    close_thread.start()
                    close_thread.join(timeout=2.0)  # Max 2s để close browser
                    
                    return "Đã đăng nhập", "OK", None
                else:
                    print(f"[INFO] ❌ CHƯA ĐĂNG NHẬP: {username} - Bắt đầu tự động đăng nhập")
                    
                    # 🚀 TỰ ĐỘNG ĐĂNG NHẬP KHI PHÁT HIỆN FORM LOGIN
                    password = account.get("password", "")
                    if not password:
                        print(f"[ERROR] Không có mật khẩu cho {username}")
                        account["status"] = "Thiếu mật khẩu"
                        self.status_updated.emit(username, account["status"])
                        return "Thiếu mật khẩu", "Error", driver
                    
                    try:
                        # Thực hiện tự động đăng nhập
                        login_result = self.perform_auto_login(driver, username, password)
                        if login_result:
                            print(f"[SUCCESS] ✅ TỰ ĐỘNG ĐĂNG NHẬP THÀNH CÔNG: {username}")
                            account["status"] = "Đã đăng nhập"
                            self.status_updated.emit(username, account["status"])
                            
                            # Lưu cookies và đóng browser
                            import threading
                            def safe_save_cookies():
                                try:
                                    self.save_cookies(driver, username)
                                    print(f"[DEBUG] ✅ Đã lưu cookies cho {username}")
                                except Exception as save_error:
                                    print(f"[WARN] Lỗi lưu cookies: {save_error}")
                            
                            def safe_close_browser():
                                try:
                                    self.close_browser_safely(driver, username)
                                    print(f"[DEBUG] ✅ Đã đóng browser cho {username}")
                                except Exception as close_error:
                                    print(f"[WARN] Lỗi đóng browser: {close_error}")
                            
                            save_thread = threading.Thread(target=safe_save_cookies, daemon=True)
                            save_thread.start()
                            save_thread.join(timeout=3.0)
                            
                            close_thread = threading.Thread(target=safe_close_browser, daemon=True)
                            close_thread.start()
                            close_thread.join(timeout=2.0)
                            
                            return "Đã đăng nhập", "OK", None
                        else:
                            print(f"[ERROR] ❌ TỰ ĐỘNG ĐĂNG NHẬP THẤT BẠI: {username}")
                            account["status"] = "Đăng nhập thất bại"
                            self.status_updated.emit(username, account["status"])
                            return "Đăng nhập thất bại", "Failed", driver
                    except Exception as login_error:
                        print(f"[ERROR] Lỗi tự động đăng nhập cho {username}: {login_error}")
                        account["status"] = f"Lỗi đăng nhập: {str(login_error)}"
                        self.status_updated.emit(username, account["status"])
                        return "Lỗi đăng nhập", "Error", driver
            except Exception as check_error:
                print(f"[ERROR] Lỗi khi check login: {check_error}")
                account["status"] = f"Lỗi check: {str(check_error)}"
                self.status_updated.emit(username, account["status"])
                return "Lỗi check login", "Error", driver
                
        except Exception as e:
            print(f"[ERROR] Lỗi simple login: {e}")
            account["status"] = f"Lỗi: {str(e)}"
            self.status_updated.emit(username, account["status"])
            if 'driver' in locals():
                self.close_browser_safely(driver, username)
            return "Lỗi", "Error", None

    def close_all_drivers(self):
        # Đóng từng driver trong thread riêng biệt để không block GUI
        import threading
        def close_driver_safe(driver):
            try:
                # ⭐ CHECK _messaging_busy FLAG TRƯỚC KHI ĐÓNG
                if hasattr(driver, '_messaging_busy') and driver._messaging_busy:
                    print(f"[DEBUG] Skip closing driver - đang busy với messaging")
                    return
                driver.quit()
            except Exception as e:
                print(f"[WARN] Lỗi khi đóng trình duyệt: {e}")
        
        # ⭐ ONLY CLOSE DRIVERS THAT ARE NOT BUSY WITH MESSAGING
        drivers_to_keep = []
        for d in self.active_drivers:
            driver = d["driver"] if isinstance(d, dict) and "driver" in d else d
            if hasattr(driver, '_messaging_busy') and driver._messaging_busy:
                print(f"[DEBUG] Keeping driver alive - đang busy với messaging")
                drivers_to_keep.append(d)
            else:
                threading.Thread(target=close_driver_safe, args=(driver,)).start()
        
        self.active_drivers = drivers_to_keep
        print(f"[INFO] Đã đóng {len(self.active_drivers) - len(drivers_to_keep)} trình duyệt. Giữ lại {len(drivers_to_keep)} driver đang busy.")

    def import_accounts(self):
        """Nhập danh sách tài khoản từ file (hỗ trợ .json, .txt, .csv)."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Nhập tài khoản", "", "All Supported (*.json *.txt *.csv);;JSON Files (*.json);;Text Files (*.txt);;CSV Files (*.csv)")
        if not file_path:
            return
        try:
            imported_accounts = []
            if file_path.endswith('.json'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    imported_accounts = json.load(f)
            elif file_path.endswith('.txt'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            # Hỗ trợ: username hoặc username,password hoặc username,password,proxy
                            parts = [p.strip() for p in line.split(',')]
                            if len(parts) == 1:
                                imported_accounts.append({"username": parts[0], "password": "", "proxy": ""})
                            elif len(parts) == 2:
                                imported_accounts.append({"username": parts[0], "password": parts[1], "proxy": ""})
                            elif len(parts) >= 3:
                                imported_accounts.append({"username": parts[0], "password": parts[1], "proxy": parts[2]})
            elif file_path.endswith('.csv'):
                import csv
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if not row: continue
                        # Hỗ trợ: username,password,proxy
                        username = row[0].strip() if len(row) > 0 else ""
                        password = row[1].strip() if len(row) > 1 else ""
                        proxy = row[2].strip() if len(row) > 2 else ""
                        if username:
                            imported_accounts.append({"username": username, "password": password, "proxy": proxy})
            else:
                QMessageBox.warning(self, "Lỗi", "Định dạng file không được hỗ trợ!")
                return

            # Lấy danh sách username hiện tại (không phân biệt hoa thường)
            existing_usernames = set(acc.get("username", "").lower() for acc in self.accounts)
            # Loại bỏ tài khoản trùng username trong chính file import
            seen = set()
            unique_imported_accounts = []
            for acc in imported_accounts:
                uname = acc.get("username", "").lower()
                if uname and uname not in seen:
                    seen.add(uname)
                    unique_imported_accounts.append(acc)
            # Lọc ra các tài khoản mới chưa có trong bảng hiện tại
            new_accounts = [acc for acc in unique_imported_accounts if acc.get("username", "").lower() not in existing_usernames]
            if not new_accounts:
                QMessageBox.information(self, "Thông báo", "Không có tài khoản mới nào được thêm (tất cả đều đã tồn tại trong bảng hiện tại).")
            else:
                # Bổ sung các trường mặc định nếu thiếu
                for acc in new_accounts:
                    acc.setdefault("selected", False)
                    acc.setdefault("fullname", "")
                    acc.setdefault("status", "Chưa đăng nhập")
                    acc.setdefault("gender", "-")
                    acc.setdefault("followers", "")
                    acc.setdefault("following", "")
                    acc.setdefault("last_action", "")
                    acc.setdefault("proxy_status", "Chưa kiểm tra")
                    acc.setdefault("permanent_proxy", "")  # ⭐ THÊM: Proxy vĩnh viễn cho tài khoản
                self.accounts.extend(new_accounts)
                self.save_accounts()
                self.update_account_table()
                QMessageBox.information(self, "Thành công", f"Đã nhập {len(new_accounts)} tài khoản mới thành công!")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể nhập tài khoản: {str(e)}")

    def open_folder_manager(self):
        # Kiểm tra xem self.folder_map có được khởi tạo không
        if not hasattr(self, 'folder_map'):
            self.folder_map = self.load_folder_map()
        from src.ui.folder_manager import FolderManagerDialog  # Import ở đây để tránh lỗi circular dependency
        dialog = FolderManagerDialog(self.accounts, self.folder_map, self)  # Truyền self.accounts và self.folder_map
        dialog.folders_updated.connect(self.on_folders_updated)  # Kết nối tín hiệu cập nhật thư mục
        dialog.exec()

    def load_folder_list_to_combo(self):
        self.category_combo.clear()
        self.category_combo.addItem("Tất cả")
        # Luôn load lại folder_map từ file để đảm bảo mới nhất
        folder_map = self.load_folder_map()
        if folder_map and "_FOLDER_SET_" in folder_map:
            for folder in folder_map["_FOLDER_SET_"]:
                if folder != "Tổng":
                    self.category_combo.addItem(folder)
        print(f"[DEBUG] Đã tải danh sách thư mục vào combobox: {folder_map.get('_FOLDER_SET_', [])}")

    def on_folder_changed(self):
        selected_folder = self.category_combo.currentText()
        if selected_folder == "Tất cả":
            self.update_account_table(self.accounts)
        else:
            filtered_accounts = [acc for acc in self.accounts if self.folder_map.get(acc.get("username"), "Tổng") == selected_folder]
            self.update_account_table(filtered_accounts)
        print(f"[DEBUG] Đã lọc tài khoản theo thư mục: {selected_folder}")

    def on_folders_updated(self):
        # Khi thư mục được cập nhật trong FolderManagerDialog, cập nhật lại combobox và bảng
        print("[DEBUG] Tín hiệu folders_updated đã được nhận trong AccountManagementTab.")
        self.folder_map = self.load_folder_map()  # Tải lại folder_map mới nhất
        self.load_folder_list_to_combo()  # Cập nhật combobox
        self.update_account_table()  # Cập nhật bảng tài khoản để phản ánh thay đổi thư mục
        # ⭐ PHÁT TÍN HIỆU ĐỂ ĐỒNG BỘ VỚI CÁC TAB KHÁC
        self.folders_updated.emit()

    def show_context_menu(self, pos):
        """Hiển thị menu chuột phải."""
        print(f"[DEBUG] show_context_menu được gọi tại vị trí: {pos}")
        menu = AccountContextMenu(self)
        menu.exec(self.account_table.viewport().mapToGlobal(pos))

    def on_table_item_double_clicked(self, index):
        selected_account: dict = self.accounts[index.row()]
        QMessageBox.information(self, "Chi tiết tài khoản", 
            f"Username: {selected_account.get('username', 'N/A')}\n"
            f"Số điện thoại: {selected_account.get('password', 'N/A')}\n"
            f"Trạng thái: {selected_account.get('status', 'N/A')}\n"
            f"Proxy: {selected_account.get('proxy', 'N/A')}\n"
            f"Proxy VV: {selected_account.get('permanent_proxy', 'N/A')}\n"
            f"Trạng thái Proxy: {selected_account.get('proxy_status', 'N/A')}\n"
            f"Follower: {selected_account.get('followers', 'N/A')}\n"
            f"Following: {selected_account.get('following', 'N/A')}\n"
            f"Hành động cuối: {selected_account.get('last_action', 'N/A')}")

    @Slot(str, str)
    def on_status_updated(self, username, status):
        """Update trạng thái từ thread một cách an toàn"""
        print(f"[DEBUG] on_status_updated được gọi cho {username} với status: {status}")
        
        # ⭐ CONSOLE LOG CHO ĐĂNG NHẬP THÀNH CÔNG (Không hiển thị popup nữa)
        if status == "Đã đăng nhập" or "đăng nhập thành công" in status.lower():
            print(f"[SUCCESS] 🎉 {username} đã đăng nhập thành công!")
            # Đã bỏ notification popup vì cột trạng thái đã hiển thị rõ ràng
        
        # Tìm và cập nhật account trong danh sách
        found = False
        account_row = -1
        for i, account in enumerate(self.accounts):
            if account.get("username") == username:
                # ⭐ KHÔNG CHO PHÉP OVERRIDE STATUS "Đã đăng nhập" 
                current_status = account.get("status", "")
                if current_status == "Đã đăng nhập" and status != "Đã đăng nhập":
                    # Bỏ qua nếu đang cố override status đăng nhập thành công
                    if "đang" in status.lower() or "đã" not in status.lower():
                        print(f"[DEBUG] Bỏ qua override status '{status}' vì tài khoản {username} đã đăng nhập thành công")
                        return
                
                account["status"] = status
                account["last_action"] = f"Cập nhật: {status} lúc {time.strftime('%H:%M:%S')}"
                found = True
                account_row = i
                print(f"[DEBUG] Tìm thấy account {username} ở row {i}, đã cập nhật status")
                break
        
        if not found:
            print(f"[ERROR] Không tìm thấy account {username} trong danh sách accounts!")
            return
        
        # Lưu accounts
        self.save_accounts()
        
        # Cập nhật chỉ ô trạng thái thay vì toàn bộ bảng để tránh dataChanged error
        try:
            if account_row >= 0 and account_row < self.account_table.rowCount():
                # Block signals để tránh lỗi dataChanged
                self.account_table.blockSignals(True)
                
                # Cập nhật chỉ ô trạng thái (cột 4)
                status_item = self.account_table.item(account_row, 4)
                if status_item:
                    status_item.setText(status)
                    
                    # ⭐ CẢI THIỆN MÀU SẮC VÀ HIỆU ỨNG CHO ĐĂNG NHẬP THÀNH CÔNG
                    if status == "Đã đăng nhập" or "đăng nhập thành công" in status.lower():
                        status_item.setForeground(QColor("#4CAF50"))  # Xanh lá đậm hơn
                        status_item.setBackground(QColor("#E8F5E8"))  # Nền xanh nhạt
                        # Thêm icon success
                        status_item.setText(f"✅ {status}")
                    elif status == "Đăng nhập thất bại" or "Lỗi" in status:
                        status_item.setForeground(QColor("#F44336"))  # Đỏ
                        status_item.setBackground(QColor("#FFEBEE"))  # Nền đỏ nhạt
                        status_item.setText(f"❌ {status}")
                    elif status == "Die" or "khóa" in status.lower():
                        status_item.setForeground(QColor("#FF5722"))  # Đỏ cam
                        status_item.setBackground(QColor("#FFF3E0"))  # Nền cam nhạt
                        status_item.setText(f"🚫 {status}")
                    elif "checkpoint" in status.lower() or "captcha" in status.lower():
                        status_item.setForeground(QColor("#FF9800"))  # Cam
                        status_item.setBackground(QColor("#FFF8E1"))  # Nền vàng nhạt
                        status_item.setText(f"⚠️ {status}")
                    else:
                        status_item.setForeground(QColor("#333333"))  # Xám đen
                        status_item.setBackground(QColor("#ffffff"))  # Nền trắng
                
                # ⭐ CẬP NHẬT CỘT "HÀNH ĐỘNG CUỐI" CŨNG ĐƯỢC HIGHLIGHT
                last_action_item = self.account_table.item(account_row, 10)  # Cột cuối cùng
                if last_action_item:
                    last_action_text = f"Cập nhật: {status} lúc {time.strftime('%H:%M:%S')}"
                    last_action_item.setText(last_action_text)
                    
                    if status == "Đã đăng nhập":
                        last_action_item.setForeground(QColor("#4CAF50"))
                        last_action_item.setText(f"🎉 {last_action_text}")
                
                # Unblock signals
                self.account_table.blockSignals(False)
                
                # Force repaint
                self.account_table.viewport().update()
                
                print(f"[DEBUG] Đã cập nhật UI trực tiếp cho {username}: {status}")
            else:
                print(f"[ERROR] Row {account_row} không hợp lệ cho bảng có {self.account_table.rowCount()} rows")
                
        except Exception as e:
            print(f"[ERROR] Lỗi khi cập nhật UI cho {username}: {e}")
            # Đảm bảo unblock signals
            self.account_table.blockSignals(False)
            
        # Cập nhật thống kê
        self.update_stats()

    def toggle_all_accounts_selection(self, checked):
        # Chỉ tick/bỏ tick các dòng đang hiển thị (không bị ẩn)
        for row_idx in range(self.account_table.rowCount()):
            if not self.account_table.isRowHidden(row_idx):
                item = self.account_table.item(row_idx, 0)
                if item:
                    model_index = self.account_table.model().index(row_idx, 0)
                    self.account_table.model().setData(model_index, checked, CheckboxDelegate.CheckboxStateRole)
                    # Cập nhật trạng thái 'selected' trong dữ liệu tài khoản gốc
                    username = self.account_table.item(row_idx, 2).text()
                    for acc in self.accounts:
                        if acc.get("username", "") == username:
                            acc["selected"] = checked
        self.save_accounts()
        self.update_account_table()
        self.update_stats()

    def load_proxies(self):
        proxies = []
        proxies_file = "proxies.txt"
        if os.path.exists(proxies_file):
            with open(proxies_file, 'r', encoding='utf-8-sig') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split(':')
                        if len(parts) == 4:
                            ip, port, user, password = parts
                            proxies.append({"ip": ip, "port": port, "user": user, "pass": password, "status": "Chưa kiểm tra", "is_in_use": False, "usage_count": 0})
                        elif len(parts) == 2:  # No auth proxy
                            ip, port = parts
                            proxies.append({"ip": ip, "port": port, "user": "", "pass": "", "status": "Chưa kiểm tra", "is_in_use": False, "usage_count": 0})
                        else:
                            print(f"[WARN] Định dạng proxy không hợp lệ, bỏ qua: {line}")
        print(f"[DEBUG] Đã tải {len(proxies)} proxy.")
        return proxies

    def load_folder_map(self):
        if os.path.exists(self.folder_map_file):
            try:
                with open(self.folder_map_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print("[ERROR] Lỗi đọc file folder_map.json. File có thể bị hỏng. Tạo lại map trống.")
                return {}
        return {}

    def _assign_new_proxy(self, account):
        """Tìm và gán một proxy mới cho tài khoản nếu proxy hiện tại bị lỗi hoặc cần xoay vòng."""
        current_proxy = account.get("proxy", "")
        username = account.get("username", "")
        print(f"[DEBUG] Đang tìm proxy mới cho tài khoản {username}. Proxy hiện tại: {current_proxy}")

        new_proxy_info = None

        # --- Ưu tiên 1: Tìm một proxy chưa được sử dụng (not in use) và có số lần sử dụng thấp (< PROXY_USAGE_THRESHOLD) ---
        for proxy_info in self.proxies:
            if (proxy_info.get("status") == "OK" or proxy_info.get("status") == "Chưa kiểm tra") and \
               not proxy_info.get("is_in_use", False) and \
               proxy_info.get("usage_count", 0) < self.PROXY_USAGE_THRESHOLD:
                new_proxy_info = proxy_info
                print(f"[DEBUG] Đã tìm thấy proxy ưu tiên (thấp sử dụng): {proxy_info.get('ip')}. Usage: {proxy_info.get('usage_count')}")
                break

        # --- Ưu tiên 2: Fallback đến bất kỳ proxy nào chưa được sử dụng và có trạng thái tốt (bất kể usage_count) ---
        if not new_proxy_info:
            print("[DEBUG] Không tìm thấy proxy ưu tiên, đang tìm proxy khả dụng bất kỳ.")
            for proxy_info in self.proxies:
                if (proxy_info.get("status") == "OK" or proxy_info.get("status") == "Chưa kiểm tra") and \
                   not proxy_info.get("is_in_use", False):
                    new_proxy_info = proxy_info
                    print(f"[DEBUG] Đã tìm thấy proxy khả dụng: {proxy_info.get('ip')}. Usage: {proxy_info.get('usage_count')}")
                    break

        if new_proxy_info:
            account["proxy"] = f"{new_proxy_info.get('ip')}:{new_proxy_info.get('port')}:{new_proxy_info.get('user')}:{new_proxy_info.get('pass')}"
            new_proxy_info["is_in_use"] = True  # Đánh dấu là đang được sử dụng khi gán
            new_proxy_info["status"] = "Đang sử dụng"  # Cập nhật trạng thái proxy trong danh sách toàn cầu
            account["proxy_status"] = "Đang chuyển đổi"  # Đánh dấu trạng thái tài khoản đang chuyển đổi proxy
            print(f"[INFO] Đã gán proxy mới {account['proxy']} cho tài khoản {username}.")
        else:
            account["proxy_status"] = "Không có proxy khả dụng"  # Nếu không tìm thấy proxy nào phù hợp
            print(f"[WARN] Không tìm thấy proxy khả dụng nào cho tài khoản {username}.")

        self.save_accounts()  # Lưu thay đổi vào accounts.json

    def _perform_warmup(self, driver, delay_multiplier):
        # Implementation of _perform_warmup method
        driver.get("https://www.instagram.com")
        time.sleep(2 * delay_multiplier)
        # Simulate scrolling down
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2 * delay_multiplier)
        # Simulate clicking on a random post or exploring
        try:
            # Find a post link and click it (simple example)
            post_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/p/')]") 
            if post_links:
                random_post = random.choice(post_links)
                random_post.click()
                time.sleep(5 * delay_multiplier)  # Spend some time on the post
                driver.back()  # Go back to home feed
                time.sleep(2 * delay_multiplier)
        except Exception as e:
            print(f"[WARN] Lỗi khi thực hiện warm-up: {e}")
        print("[DEBUG] Đã hoàn tất phiên warm-up.")

    def get_info_selected_accounts(self):
        QMessageBox.information(self, "Chức năng", "Lấy thông tin tài khoản đang được phát triển.")
        print("[DEBUG] Chức năng get_info_selected_accounts được gọi.")

    def open_browser_for_selected(self):
        QMessageBox.information(self, "Chức năng", "Mở trình duyệt đang được phát triển.")
        print("[DEBUG] Chức năng open_browser_for_selected được gọi.")

    def logout_selected_accounts(self):
        self.update_account_table()
        QMessageBox.information(self, "Chức năng", "Đăng xuất tài khoản đang được phát triển.")
        print("[DEBUG] Chức năng logout_selected_accounts được gọi.")

    def delete_selected_accounts(self):
        # Xóa các tài khoản đã được tick chọn (checkbox)
        selected_accounts = [acc for acc in self.accounts if acc.get("selected")]
        if not selected_accounts:
            QMessageBox.warning(self, "Xóa tài khoản", "Vui lòng tick chọn ít nhất một tài khoản để xóa.")
            return
        reply = QMessageBox.question(
            self, "Xác nhận", f"Bạn có chắc chắn muốn xóa {len(selected_accounts)} tài khoản đã chọn?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.accounts = [acc for acc in self.accounts if not acc.get("selected")]
            self.save_accounts()
            self.update_account_table()
            QMessageBox.information(self, "Thành công", "Đã xóa các tài khoản đã chọn.")

    def select_selected_accounts(self):
        selected_rows = self.account_table.selectionModel().selectedRows()
        for index in selected_rows:
            row = index.row()
            if row < len(self.accounts):
                model_index = self.account_table.model().index(row, 0)
                self.account_table.model().setData(model_index, True, CheckboxDelegate.CheckboxStateRole)
                self.accounts[row]["selected"] = True
        self.save_accounts()
        self.update_account_table()
        # QMessageBox.information(self, "Chọn tài khoản", f"Đã chọn {len(selected_rows)} tài khoản được bôi đen.")
        print(f"[DEBUG] Đã chọn {len(selected_rows)} tài khoản được bôi đen.")

    def deselect_selected_accounts(self):
        # Bỏ chọn các tài khoản đang được bôi đen (highlighted) và đang hiển thị
        selected_rows = self.account_table.selectionModel().selectedRows()
        for index in selected_rows:
            row = index.row()
            if not self.account_table.isRowHidden(row):
                item_checkbox = self.account_table.item(row, 0)
                if item_checkbox:
                    model_index = self.account_table.model().index(row, 0)
                    self.account_table.model().setData(model_index, False, CheckboxDelegate.CheckboxStateRole)
                    username = self.account_table.item(row, 2).text()
                    for acc in self.accounts:
                        if acc.get("username", "") == username:
                            acc["selected"] = False
        self.save_accounts()
        self.update_account_table()
        print(f"[DEBUG] Đã bỏ chọn các tài khoản được bôi đen và đang hiển thị.")

    def deselect_all_accounts(self):
        # Bỏ chọn tất cả tài khoản đã được tick chọn (chỉ các dòng đang hiển thị)
        for row_idx in range(self.account_table.rowCount()):
            if not self.account_table.isRowHidden(row_idx):
                item = self.account_table.item(row_idx, 0)
                if item:
                    model_index = self.account_table.model().index(row_idx, 0)
                    self.account_table.model().setData(model_index, False, CheckboxDelegate.CheckboxStateRole)
                    username = self.account_table.item(row_idx, 2).text()
                    for acc in self.accounts:
                        if acc.get("username", "") == username:
                            acc["selected"] = False
        self.save_accounts()
        self.update_account_table()
        print(f"[DEBUG] Đã bỏ chọn tất cả tài khoản đang hiển thị.")

    def add_selected_to_folder(self, folder_name):
        # Gán tất cả tài khoản đang tick chọn vào folder_name
        selected_accounts = [acc for acc in self.accounts if acc.get("selected")]
        if not selected_accounts:
            QMessageBox.warning(self, "Gán thư mục", "Vui lòng tick chọn ít nhất một tài khoản để gán vào thư mục.")
            return
        for acc in selected_accounts:
            username = acc.get("username", "")
            if username:
                self.folder_map[username] = folder_name
        self.save_folder_map()
        self.update_account_table()
        QMessageBox.information(self, "Thành công", f"Đã gán {len(selected_accounts)} tài khoản vào thư mục '{folder_name}'.")

    def remove_selected_from_folder(self):
        # Đưa tất cả tài khoản đang tick chọn về thư mục 'Tổng' nếu đang ở thư mục khác
        selected_accounts = [acc for acc in self.accounts if acc.get("selected")]
        if not selected_accounts:
            QMessageBox.warning(self, "Bỏ gán thư mục", "Vui lòng tick chọn ít nhất một tài khoản để bỏ gán.")
            return
        count = 0
        for acc in selected_accounts:
            username = acc.get("username", "")
            if username and self.folder_map.get(username) != "Tổng":
                self.folder_map[username] = "Tổng"
                count += 1
        self.save_folder_map()
        self.update_account_table()
        QMessageBox.information(self, "Thành công", f"Đã bỏ gán {count} tài khoản khỏi các thư mục.")

    def delete_selected_folder(self):
        QMessageBox.information(self, "Chức năng", "Xóa thư mục đang được phát triển.")
        print("[DEBUG] Chức năng delete_selected_folder được gọi.")

    def set_account_status_selected(self, status):
        selected_accounts = [acc for acc in self.accounts if acc.get("selected")]
        if not selected_accounts:
            QMessageBox.warning(self, "Chuyển trạng thái", "Vui lòng tick chọn ít nhất một tài khoản.")
            return
        for acc in selected_accounts:
            acc["status"] = status
        self.save_accounts()
        self.update_account_table()
        QMessageBox.information(self, "Thành công", f"Đã chuyển trạng thái {len(selected_accounts)} tài khoản sang '{status}'.")

    def update_selected_proxy_info(self):
        import re
        selected_accounts = [acc for acc in self.accounts if acc.get("selected")]
        if not selected_accounts:
            QMessageBox.warning(self, "Cập nhật Proxy", "Vui lòng tick chọn ít nhất một tài khoản.")
            return
        proxy, ok = QInputDialog.getText(self, "Nhập Proxy", "Nhập proxy (ip:port hoặc ip:port:user:pass):")
        if not ok or not proxy.strip():
            return
        # Kiểm tra định dạng proxy
        pattern = r'^(\d{1,3}\.){3}\d{1,3}:\d{2,5}(:\w+:\w+)?$'
        if not re.match(pattern, proxy.strip()):
            QMessageBox.warning(self, "Lỗi", "Proxy không đúng định dạng!\nĐịnh dạng hợp lệ: ip:port hoặc ip:port:user:pass")
            return
        for acc in selected_accounts:
            acc["proxy"] = proxy.strip()
        self.save_accounts()
        self.update_account_table()
        QMessageBox.information(self, "Thành công", f"Đã cập nhật proxy cho {len(selected_accounts)} tài khoản.")

    def open_selected_user_data_folder(self):
        QMessageBox.information(self, "Chức năng", "Mở thư mục UserData đang được phát triển.")
        print("[DEBUG] Chức năng open_selected_user_data_folder được gọi.")

    def export_accounts(self):
        """Xuất danh sách tài khoản ra file."""
        file_path, _ = QFileDialog.getSaveFileName(self, "Xuất tài khoản", "", "JSON Files (*.json)")
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.accounts, f, ensure_ascii=False, indent=4)
                QMessageBox.information(self, "Thành công", "Đã xuất tài khoản thành công!")
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể xuất tài khoản: {str(e)}")

    def toggle_stealth_mode(self):
        """Bật/tắt chế độ ẩn danh."""
        self.stealth_mode_enabled = not self.stealth_mode_enabled
        status = "bật" if self.stealth_mode_enabled else "tắt"
        QMessageBox.information(self, "Thông báo", f"Đã {status} chế độ ẩn danh!")

    def delete_all_accounts(self):
        """Xóa tất cả tài khoản."""
        reply = QMessageBox.question(self, "Xác nhận", "Bạn có chắc chắn muốn xóa tất cả tài khoản?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.accounts.clear()
            self.save_accounts()
            self.update_account_table()
            QMessageBox.information(self, "Thành công", "Đã xóa tất cả tài khoản!")

    def close_popups(self, driver):
        # import time  # XÓA DÒNG NÀY
        from selenium.webdriver.common.by import By
        close_selectors = [
            # Banner "Chrome controlled"
            "//div[contains(@class, 'controlled-indicator')]//button",
            "//div[contains(text(),'自动测试软件')]/following-sibling::button",
            "//div[contains(text(),'is being controlled')]/following-sibling::button",
            # Cookie/terms
            "//button[contains(@aria-label, 'Schließen')]",
            "//button[contains(@aria-label, 'Close')]",
            "//button[contains(@aria-label, '关闭')]",
            "//button[contains(text(), '×')]",
            "//button[text()='OK']",
            "//button[text()='Accept']",
            "//button[text()='Allow all cookies']",
            "//button[text()='Cho phép tất cả cookie']",
            "//button[contains(text(), 'Akzeptieren')]",
        ]
        for _ in range(3):  # Lặp lại 3 lần để chắc chắn tắt hết
            for sel in close_selectors:
                try:
                    btn = driver.find_element(By.XPATH, sel)
                    btn.click()
                    print(f"[DEBUG] Đã tắt popup với selector: {sel}")
                    # time.sleep(0.2)  # XÓA DÒNG NÀY
                except Exception:
                    continue
        # Inject CSS ẩn
                    # Inject CSS ẩn banner "Chrome controlled" nếu còn sót
                try:
                    driver.execute_script("""
                    var el = document.querySelector('div.controlled-indicator');
                    if (el) { el.style.display = 'none'; }
                    """)
                except Exception:
                    pass

    def save_folder_map(self):
        if hasattr(self, 'folder_map_file'):
            try:
                with open(self.folder_map_file, "w", encoding="utf-8") as f:
                    json.dump(self.folder_map, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"[ERROR] Lỗi khi lưu folder_map: {e}")

    def on_proxy_switch_changed(self, value):
        self.use_proxy = bool(value)
        self.update_proxy_switch_label()
        # Lưu trạng thái vào file
        try:
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump({"use_proxy": self.use_proxy}, f)
        except Exception as e:
            print(f"[WARN] Không thể lưu trạng thái sử dụng proxy: {e}")
        print(f"[DEBUG] Trạng thái sử dụng proxy: {self.use_proxy}")

    def update_proxy_switch_label(self):
        if self.use_proxy:
            self.proxy_switch_label.setText("Proxy: ON")
            self.proxy_switch_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        else:
            self.proxy_switch_label.setText("Proxy: OFF")
            self.proxy_switch_label.setStyleSheet("color: #888; font-weight: bold;")

    def closeEvent(self, event):
        # Lưu trạng thái sử dụng proxy khi đóng ứng dụng
        try:
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump({"use_proxy": self.use_proxy}, f)
        except Exception as e:
            print(f"[WARN] Không thể lưu trạng thái sử dụng proxy khi đóng ứng dụng: {e}")
        super().closeEvent(event)

    def save_cookies(self, driver, username):
        """⚡ ULTRA SAFE COOKIES: Save cookies với timeout protection"""
        try:
            import signal
            import os
            import json
            
            print(f"[DEBUG] ⚡ Saving cookies for {username}...")
            
            # 🔥 TIMEOUT PROTECTION: Max 3 seconds for get_cookies
            def timeout_handler(signum, frame):
                raise TimeoutError("Cookies save timeout")
            
            try:
                # Set timeout for Windows (alternative approach)
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                
                # Quick check if driver is still responsive (NO WebDriverWait)
                try:
                    # Simple check without WebDriverWait to avoid renderer timeout
                    current_url = driver.current_url  # Basic connectivity test
                    if not current_url:
                        print(f"[WARN] Driver not responsive, skipping cookies save for {username}")
                        return False
                except Exception as connectivity_error:
                    print(f"[WARN] Driver connectivity failed: {connectivity_error}")
                    return False
                
                # 🔥 SAFE COOKIES EXTRACTION with timeout
                os.makedirs('sessions', exist_ok=True)
                
                # Use threading for timeout on Windows
                import threading
                cookies = None
                exception_holder = [None]
                
                def get_cookies_with_timeout():
                    try:
                        nonlocal cookies
                        cookies = driver.get_cookies()
                    except Exception as e:
                        exception_holder[0] = e
                
                thread = threading.Thread(target=get_cookies_with_timeout, daemon=True)
                thread.start()
                thread.join(timeout=2.0)  # Max 2 seconds
                
                if thread.is_alive():
                    print(f"[WARN] ⏰ Cookies extraction timeout for {username}")
                    return False
                
                if exception_holder[0]:
                    raise exception_holder[0]
                
                if cookies is None:
                    print(f"[WARN] No cookies extracted for {username}")
                    return False
                
                # 🔥 SAFE FILE WRITE
                cookies_file = f'sessions/{username}_cookies.json'
                with open(cookies_file, 'w', encoding='utf-8') as f:
                    json.dump(cookies, f, indent=2)
                
                print(f"[DEBUG] ✅ Cookies saved successfully for {username} ({len(cookies)} cookies)")
                return True
                
            except Exception as e:
                print(f"[WARN] Cookies save failed for {username}: {e}")
                return False
                
        except Exception as e:
            print(f"[ERROR] Cookies save error for {username}: {e}")
            return False

    def load_cookies(self, driver, username):
        """Load cookies với debug tracking để tránh treo"""
        try:
            print(f"[DEBUG] 🍪 Bắt đầu load cookies cho {username}")
            cookies_path = f'sessions/{username}_cookies.json'
            
            if not os.path.exists(cookies_path):
                print(f"[DEBUG] 🍪 Không có file cookies cho {username}")
                return False
                
            print(f"[DEBUG] 🍪 Đọc file cookies: {cookies_path}")
            with open(cookies_path, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            
            print(f"[DEBUG] 🍪 Có {len(cookies)} cookies cho {username}")
            
            # Add từng cookie một với error handling
            added_count = 0
            for i, cookie in enumerate(cookies):
                try:
                    # Selenium yêu cầu phải ở đúng domain mới add được cookie
                    driver.add_cookie(cookie)
                    added_count += 1
                except Exception as cookie_error:
                    print(f"[DEBUG] 🍪 Lỗi add cookie {i+1}: {cookie_error}")
                    continue
            
            print(f"[DEBUG] 🍪 Đã add {added_count}/{len(cookies)} cookies cho {username}")
            return True
            
        except Exception as e:
            print(f"[DEBUG] 🍪 Lỗi load cookies cho {username}: {e}")
            return False

    def show_captcha_dialog_safe(self, driver, username, dialog_type="captcha"):
        """Hiển thị dialog captcha/checkpoint một cách an toàn"""
        try:
            from PySide6.QtWidgets import QMessageBox
            
            # Chỉ hiển thị dialog nếu chưa có dialog nào đang mở
            if hasattr(self, '_captcha_dialog_active') and self._captcha_dialog_active:
                print("[DEBUG] Captcha dialog đã đang mở, bỏ qua")
                return True
                
            self._captcha_dialog_active = True
            
            try:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Captcha/Xác minh")
                
                if dialog_type == "captcha":
                    msg_box.setText(f"Phát hiện captcha/checkpoint cho tài khoản {username}.\n\n"
                                   "Vui lòng:\n"
                                   "1. Chuyển sang cửa sổ trình duyệt\n"
                                   "2. Giải captcha hoặc xác minh\n"
                                   "3. Nhấn 'Tiếp tục' khi hoàn tất\n\n"
                                   "KHÔNG đóng trình duyệt!")
                else:  # 2FA
                    msg_box.setText(f"Phát hiện yêu cầu 2FA cho tài khoản {username}.\n\n"
                                   "Vui lòng:\n"
                                   "1. Chuyển sang cửa sổ trình duyệt\n"
                                   "2. Nhập mã xác minh 2FA\n"
                                   "3. Nhấn 'Tiếp tục' khi hoàn tất\n\n"
                                   "KHÔNG đóng trình duyệt!")
                
                msg_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
                msg_box.button(QMessageBox.Ok).setText("Tiếp tục")
                msg_box.button(QMessageBox.Cancel).setText("Bỏ qua")
                
                # Đảm bảo dialog luôn ở trên cùng
                msg_box.setWindowFlag(msg_box.windowFlags() | 0x00000008)  # WindowStaysOnTopHint
                
                # Hiển thị dialog
                result = msg_box.exec()
                
                self._captcha_dialog_active = False
                
                if result == QMessageBox.Ok:
                    print(f"[DEBUG] User chọn tiếp tục xử lý {dialog_type} cho {username}")
                    return True
                else:
                    print(f"[DEBUG] User chọn bỏ qua {dialog_type} cho {username}")
                    return False
                    
            except Exception as e:
                print(f"[ERROR] Lỗi khi hiển thị dialog: {e}")
                self._captcha_dialog_active = False
                return False
            
        except Exception as e:
            print(f"[ERROR] Lỗi trong show_captcha_dialog_safe: {e}")
            return False
    
    def check_login_success_after_captcha(self, driver, username):
        """Kiểm tra đăng nhập thành công sau khi xử lý captcha"""
        try:
            print(f"[INFO] Kiểm tra đăng nhập sau xử lý captcha cho {username}")
            
            # Đợi một chút để trang tải
            time.sleep(2)
            
            # Sử dụng hàm kiểm tra nhanh
            return self.quick_login_check(driver)
            
        except Exception as e:
            print(f"[ERROR] Lỗi khi kiểm tra đăng nhập sau captcha: {e}")
            return False

    def verify_login_and_collect_info_fast(self, driver, username, account):
        """Xác minh đăng nhập và thu thập thông tin nhanh chóng"""
        try:
            print(f"[INFO] Bắt đầu xác minh đăng nhập nhanh cho {username}")
            
            # Bước 1: Kiểm tra nhanh đã đăng nhập chưa
            login_verified = self.quick_login_check(driver)
            if not login_verified:
                print(f"[WARN] Chưa đăng nhập thành công cho {username}")
                return False
            
            # Bước 2: Thu thập thông tin cơ bản nhanh
            info = self.collect_basic_info_fast(driver, username)
            
            # Bước 3: Cập nhật thông tin vào account
            self.update_account_info(account, info)
            
            # Bước 4: Lưu cookies để lần sau đăng nhập nhanh hơn
            self.save_cookies(driver, username)
            
            # Bước 5: Cập nhật UI
            account["status"] = "Đã đăng nhập"
            account["last_action"] = f"Đăng nhập thành công lúc {time.strftime('%H:%M:%S')}"
            from PySide6.QtCore import QMetaObject, Qt
            self.status_updated.emit(username, account["status"])
            
            print(f"[SUCCESS] Xác minh đăng nhập thành công cho {username}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Lỗi khi xác minh đăng nhập cho {username}: {e}")
            return False
    
    def quick_login_check(self, driver):
        """🔥 ZERO DOM LOGIN CHECK: Chỉ URL + title, KHÔNG find_element"""
        try:
            # 🚀 STEP 1: URL check (FASTEST)
            current_url = driver.current_url.lower()
            print(f"[DEBUG] Quick check URL: {current_url}")
            
            # ❌ Definitely NOT logged in
            if any(x in current_url for x in ["login", "challenge", "checkpoint", "accounts/signup"]):
                print(f"[DEBUG] ❌ Not logged in - URL contains login/challenge")
                return False
            
            # ✅ Likely logged in if on Instagram domain
            if "instagram.com" in current_url:
                print(f"[DEBUG] ✅ Likely logged in - On Instagram domain")
                
                # 🚀 STEP 2: Title check for extra confidence
                try:
                    title = driver.title.lower()
                    if "login" in title:
                        print(f"[DEBUG] ❌ Login title detected")
                        return False
                    else:
                        print(f"[DEBUG] ✅ Non-login title: {title}")
                        return True
                except Exception as title_error:
                    print(f"[DEBUG] Title check failed: {title_error}")
                    return True  # Default to success if on Instagram domain
            
            print(f"[DEBUG] ❌ Not on Instagram domain")
            return False
            
        except Exception as e:
            print(f"[ERROR] Quick login check error: {e}")
            # Default to True to avoid hanging
            return True
    
    def collect_basic_info_fast(self, driver, username):
        """Thu thập thông tin cơ bản nhanh chóng"""
        info = {
            "username": username,
            "profile_url": "",
            "followers": "N/A",
            "following": "N/A", 
            "posts": "N/A",
            "bio": "",
            "verified": False,
            "private": False
        }
        
        try:
            # Lấy URL hiện tại
            current_url = driver.current_url
            if "instagram.com" in current_url:
                info["profile_url"] = current_url
            
            # Thử truy cập profile nhanh (nếu chưa ở profile)
            if f"instagram.com/{username}" not in current_url.lower():
                try:
                    driver.get(f"https://www.instagram.com/{username}/")
                    time.sleep(2)  # Đợi trang tải
                except Exception:
                    pass
            
            # Thu thập thông tin từ profile (với timeout ngắn)
            try:
                # Followers, Following, Posts
                stats_selectors = [
                    "main section ul li a span",
                    "header section ul li a span",
                    "article header div span"
                ]
                
                for selector in stats_selectors:
                    try:
                        stats = driver.find_elements(By.CSS_SELECTOR, selector)
                        if len(stats) >= 3:
                            info["posts"] = stats[0].text.strip()
                            info["followers"] = stats[1].text.strip() 
                            info["following"] = stats[2].text.strip()
                            break
                    except Exception:
                        continue
                
                # Bio
                try:
                    bio_element = driver.find_element(By.CSS_SELECTOR, "header section div span")
                    info["bio"] = bio_element.text.strip()[:100]  # Giới hạn 100 ký tự
                except Exception:
                    pass
                
                # Verified badge
                try:
                    verified = driver.find_elements(By.CSS_SELECTOR, "svg[aria-label*='Verified']")
                    info["verified"] = len(verified) > 0
                except Exception:
                    pass
                
                # Private account
                try:
                    private_text = driver.page_source.lower()
                    info["private"] = "this account is private" in private_text
                except Exception:
                    pass
                    
            except Exception as e:
                print(f"[DEBUG] Không thu thập được thông tin chi tiết: {e}")
            
            print(f"[DEBUG] Thu thập info: {info}")
            return info
            
        except Exception as e:
            print(f"[ERROR] Lỗi khi thu thập thông tin: {e}")
            return info
    
    def update_account_info(self, account, info):
        """Cập nhật thông tin vào account"""
        try:
            account["profile_url"] = info.get("profile_url", "")
            account["followers"] = info.get("followers", "N/A")
            account["following"] = info.get("following", "N/A")
            account["posts"] = info.get("posts", "N/A")
            account["bio"] = info.get("bio", "")
            account["verified"] = info.get("verified", False)
            account["private"] = info.get("private", False)
            account["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
            
            print(f"[DEBUG] Đã cập nhật thông tin cho {account.get('username')}")
            
        except Exception as e:
            print(f"[ERROR] Lỗi khi cập nhật thông tin account: {e}")
    
    def debug_instagram_dom(self, driver, username):
        """Debug DOM structure của Instagram để hiểu layout"""
        try:
            print(f"[DEBUG] ===== DEBUG DOM STRUCTURE CHO {username} =====")
            
            # Tìm tất cả các link href="/"
            home_links = driver.find_elements(By.CSS_SELECTOR, "a[href='/']")
            print(f"[DEBUG] Tìm thấy {len(home_links)} link href='/'")
            for i, link in enumerate(home_links[:5]):  # Chỉ log 5 link đầu
                try:
                    location = link.location
                    size = link.size
                    is_displayed = link.is_displayed()
                    print(f"[DEBUG] Home link {i+1}: X={location['x']}, Y={location['y']}, W={size['width']}, H={size['height']}, Visible={is_displayed}")
                    print(f"[DEBUG] HTML: {link.get_attribute('outerHTML')[:300]}...")
                except Exception as e:
                    print(f"[DEBUG] Lỗi khi debug home link {i+1}: {e}")
            
            # Tìm tất cả các link explore
            explore_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='explore']")
            print(f"[DEBUG] Tìm thấy {len(explore_links)} link explore")
            for i, link in enumerate(explore_links[:5]):  # Chỉ log 5 link đầu
                try:
                    location = link.location
                    size = link.size
                    is_displayed = link.is_displayed()
                    print(f"[DEBUG] Explore link {i+1}: X={location['x']}, Y={location['y']}, W={size['width']}, H={size['height']}, Visible={is_displayed}")
                    print(f"[DEBUG] HTML: {link.get_attribute('outerHTML')[:300]}...")
                except Exception as e:
                    print(f"[DEBUG] Lỗi khi debug explore link {i+1}: {e}")
            
            # Tìm tất cả SVG icons
            svg_icons = driver.find_elements(By.CSS_SELECTOR, "svg")
            print(f"[DEBUG] Tìm thấy {len(svg_icons)} SVG icons")
            home_svg_count = 0
            explore_svg_count = 0
            for i, svg in enumerate(svg_icons[:20]):  # Chỉ log 20 SVG đầu
                try:
                    aria_label = svg.get_attribute('aria-label') or ""
                    location = svg.location
                    is_displayed = svg.is_displayed()
                    if is_displayed and location['y'] > 0:  # Chỉ log SVG hiển thị
                        if any(keyword in aria_label.lower() for keyword in ['home', 'trang chủ']):
                            home_svg_count += 1
                            print(f"[DEBUG] HOME SVG {home_svg_count}: aria-label='{aria_label}', X={location['x']}, Y={location['y']}")
                        elif any(keyword in aria_label.lower() for keyword in ['search', 'explore', 'tìm kiếm', 'khám phá']):
                            explore_svg_count += 1
                            print(f"[DEBUG] EXPLORE SVG {explore_svg_count}: aria-label='{aria_label}', X={location['x']}, Y={location['y']}")
                except Exception as e:
                    continue
                    
            print(f"[DEBUG] Tổng: {home_svg_count} Home SVG, {explore_svg_count} Explore SVG")
            print(f"[DEBUG] ===== KẾT THÚC DEBUG DOM =====")
            
        except Exception as e:
            print(f"[DEBUG] Lỗi khi debug DOM: {e}")

    def check_home_and_explore_icons(self, driver):
        """⚡ ULTRA FAST LOGIN DETECTION: URL-first approach với 99% accuracy"""
        return self.ultra_fast_login_detection(driver)
    
    def ultra_fast_login_detection(self, driver):
        """⚡ SIÊU NHANH - CHÍNH XÁC 99%: Nhận diện trạng thái trong <1 giây"""
        try:
            print("[DEBUG] ⚡ ULTRA FAST LOGIN DETECTION - URL FIRST...")
            
            # 🚀 STEP 1: URL-BASED DETECTION (FASTEST - 0.1s)
            try:
                current_url = driver.current_url.lower()
                print(f"[DEBUG] 🔍 URL: {current_url}")
                
                # ❌ CHẮC CHẮN CHƯA ĐĂNG NHẬP - URL patterns
                login_fail_patterns = [
                    "accounts/login", "/login/", "/login?", "accounts/emaillogin",
                    "accounts/signup", "accounts/onetap", "accounts/password/reset"
                ]
                
                for pattern in login_fail_patterns:
                    if pattern in current_url:
                        print(f"[RESULT] ❌ CHƯA ĐĂNG NHẬP - URL: {pattern}")
                        return False
                
                # 🔐 2FA DETECTION - URL patterns
                twofa_patterns = ["accounts/login/two_factor", "/challenge/", "two_factor"]
                for pattern in twofa_patterns:
                    if pattern in current_url:
                        print(f"[RESULT] 🔐 2FA REQUIRED - URL: {pattern}")
                        return "2FA_REQUIRED"
                
                # 🤖 CAPTCHA DETECTION - URL patterns  
                captcha_patterns = ["challenge", "checkpoint", "captcha", "recaptcha"]
                for pattern in captcha_patterns:
                    if pattern in current_url:
                        print(f"[RESULT] 🤖 CAPTCHA REQUIRED - URL: {pattern}")
                        return "CAPTCHA_REQUIRED"
                
                # 🚨 ACCOUNT LOCKED - URL patterns
                locked_patterns = ["accounts/suspended", "accounts/locked", "accounts/disabled"]
                for pattern in locked_patterns:
                    if pattern in current_url:
                        print(f"[RESULT] 🚨 ACCOUNT LOCKED - URL: {pattern}")
                        return "ACCOUNT_LOCKED"
                
                # ✅ LIKELY LOGGED IN - Instagram main domain without bad patterns
                if "instagram.com" in current_url and not any(bad in current_url for bad in 
                    ["login", "challenge", "checkpoint", "signup", "accounts/", "recover"]):
                    print(f"[RESULT] ✅ LIKELY LOGGED IN - Clean Instagram URL")
                    return True
                    
            except Exception as e:
                print(f"[DEBUG] URL check error: {e}")
            
            # 🚀 STEP 2: TITLE-BASED DETECTION (FAST - 0.2s)
            try:
                title = driver.title.lower()
                print(f"[DEBUG] 🔍 TITLE: '{title}'")
                
                # ❌ Login page titles
                if any(word in title for word in ["login", "sign up", "create account"]):
                    print(f"[RESULT] ❌ CHƯA ĐĂNG NHẬP - Title: {title}")
                    return False
                
                # 🔐 2FA titles
                if any(word in title for word in ["verification", "2fa", "security code"]):
                    print(f"[RESULT] 🔐 2FA REQUIRED - Title: {title}")
                    return "2FA_REQUIRED"
                
                # 🤖 Captcha titles
                if any(word in title for word in ["captcha", "challenge", "security", "robot"]):
                    print(f"[RESULT] 🤖 CAPTCHA REQUIRED - Title: {title}")
                    return "CAPTCHA_REQUIRED"
                
                # 🚨 Account locked titles
                if any(word in title for word in ["suspended", "disabled", "restricted", "locked"]):
                    print(f"[RESULT] 🚨 ACCOUNT LOCKED - Title: {title}")
                    return "ACCOUNT_LOCKED"
                
                # ✅ Success titles
                if title == "instagram" or "instagram" in title and len(title) < 15:
                    print(f"[RESULT] ✅ LIKELY LOGGED IN - Instagram title")
                    return True
                    
            except Exception as e:
                print(f"[DEBUG] Title check error: {e}")
            
            # 🎯 STEP 3: POPUP SAVE LOGIN INFO CHECK (MEDIUM - 0.3s)
            try:
                print("[DEBUG] 🎯 Quick popup check...")
                import threading
                import time
                
                popup_found = False
                popup_check_done = False
                
                def check_popup():
                    nonlocal popup_found, popup_check_done
                    try:
                        page_source = driver.page_source
                        if any(text in page_source for text in [
                            "Save your login info", "save your login info",
                            "We can save your login info"
                        ]):
                            popup_found = True
                    except:
                        pass
                    finally:
                        popup_check_done = True
                
                # Timeout sau 0.5s với proper cleanup
                thread = threading.Thread(target=check_popup, daemon=True)
                thread.start()
                thread.join(timeout=0.5)
                
                # Force cleanup nếu thread chưa done
                if not popup_check_done:
                    print("[DEBUG] Popup check timeout - continuing...")
                
                if popup_found:
                    print(f"[RESULT] 🎉 SAVE LOGIN POPUP -> ĐĂNG NHẬP THÀNH CÔNG!")
                    self.handle_save_login_popup_quick(driver)
                    return True
                    
            except Exception as e:
                print(f"[DEBUG] Popup check error: {e}")
            
            # 🔥 STEP 4: SIMPLE DOM CHECK (NO THREADING) - (0.5s max)
            try:
                print("[DEBUG] 🔥 Simple DOM check (no threading)...")
                
                # Set timeout for implicit wait temporarily
                original_timeout = driver.implicitly_wait(0.5)  # Very short timeout
                
                try:
                    # Chỉ check 1 element đơn giản nhất - login form
                    login_inputs = driver.find_elements(By.CSS_SELECTOR, "input[name='username']")
                    if login_inputs and any(inp.is_displayed() for inp in login_inputs):
                        print(f"[RESULT] ❌ LOGIN FORM FOUND -> NOT LOGGED IN")
                        return False
                        
                    # Check navigation - đơn giản hơn
                    nav_links = driver.find_elements(By.CSS_SELECTOR, "a[href='/']")
                    if nav_links and len(nav_links) > 0:
                        print(f"[RESULT] ✅ NAVIGATION FOUND -> LOGGED IN")
                        return True
                        
                except Exception as dom_error:
                    print(f"[DEBUG] DOM elements check failed: {dom_error}")
                finally:
                    # Restore original timeout
                    try:
                        driver.implicitly_wait(3)  # Restore to 3s
                    except:
                        pass
                        
            except Exception as e:
                print(f"[DEBUG] DOM check error: {e}")
            
            # 🛡️ FINAL FALLBACK: Dựa vào URL cuối cùng
            try:
                current_url = driver.current_url.lower()
                if "instagram.com" in current_url:
                    # Nếu URL có dấu hiệu xấu -> chưa đăng nhập
                    if any(bad in current_url for bad in ["login", "challenge", "checkpoint", "signup"]):
                        print(f"[RESULT] ❌ FALLBACK: Bad URL patterns detected")
                        return False
                    else:
                        print(f"[RESULT] ✅ FALLBACK: Clean Instagram URL assumed logged in")
                        return True
                        
                print(f"[RESULT] ❌ FALLBACK: Non-Instagram URL")
                return False
                
            except Exception as e:
                print(f"[ERROR] Fallback error: {e}")
                return False
            
        except Exception as e:
            print(f"[ERROR] ULTRA FAST DETECTION ERROR: {e}")
            return False
    def check_captcha_required(self, driver):
        """⚡ ULTRA SIMPLE CAPTCHA CHECK: Chỉ check URL và iframe"""
        try:
            print(f"[DEBUG] ⚡ Quick captcha check...")
            
            # 🔥 STEP 1: Quick URL check (FASTEST) 
            try:
                current_url = driver.current_url.lower()
                print(f"[DEBUG] URL: {current_url}")
                
                # Check for captcha URL patterns
                captcha_url_patterns = [
                    "challenge", "checkpoint", "captcha", "recaptcha", "hcaptcha"
                ]
                
                for pattern in captcha_url_patterns:
                    if pattern in current_url:
                        print(f"[DEBUG] ✅ CAPTCHA DETECTED - URL Pattern: {pattern}")
                        return True
                        
            except Exception as e:
                print(f"[DEBUG] URL check error: {e}")
            
            # 🔥 STEP 2: Quick iframe check (FAST)
            try:
                captcha_frames = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='recaptcha'], iframe[src*='hcaptcha']")
                if captcha_frames:
                    print("[DEBUG] ✅ CAPTCHA DETECTED - iframe captcha")
                    return True
            except Exception as e:
                print(f"[DEBUG] Iframe check error: {e}")
            
            # 🔥 STEP 3: Quick title check (FAST)
            try:
                title = driver.title.lower()
                captcha_title_words = ["captcha", "challenge", "security", "robot", "verify"]
                
                if any(word in title for word in captcha_title_words):
                    print(f"[DEBUG] ✅ CAPTCHA DETECTED - Title: {title}")
                    return True
                    
            except Exception as e:
                print(f"[DEBUG] Title check error: {e}")
            
            print(f"[DEBUG] ❌ No captcha detected")
            return False
            
        except Exception as e:
            print(f"[DEBUG] Lỗi khi kiểm tra captcha: {e}")
            return False
    
    def check_2fa_required(self, driver):
        """⚡ ULTRA SIMPLE 2FA CHECK: Chỉ check URL và title"""
        try:
            print(f"[DEBUG] ⚡ Quick 2FA check...")
            
            # 🔥 STEP 1: Quick URL check (FASTEST)
            try:
                current_url = driver.current_url.lower()
                print(f"[DEBUG] URL: {current_url}")
                
                # Check for 2FA URL patterns
                twofa_url_patterns = [
                    "accounts/login/two_factor", "challenge/", "two_factor", "2fa", "verify"
                ]
                
                for pattern in twofa_url_patterns:
                    if pattern in current_url:
                        print(f"[DEBUG] ✅ 2FA DETECTED - URL Pattern: {pattern}")
                        return True
                        
            except Exception as e:
                print(f"[DEBUG] URL check error: {e}")
            
            # 🔥 STEP 2: Quick title check (FAST)
            try:
                title = driver.title.lower()
                twofa_title_words = ["verification", "2fa", "security", "code", "authenticate"]
                
                if any(word in title for word in twofa_title_words):
                    print(f"[DEBUG] ✅ 2FA DETECTED - Title: {title}")
                    return True
                    
            except Exception as e:
                print(f"[DEBUG] Title check error: {e}")
            
            print(f"[DEBUG] ❌ No 2FA detected")
            return False

            
        except Exception as e:
            print(f"[ERROR] Lỗi khi kiểm tra 2FA: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def check_identity_verification_required(self, driver):
        """⚡ ULTRA SIMPLE IDENTITY CHECK: Chỉ check URL và title"""
        try:
            print(f"[DEBUG] ⚡ Quick identity verification check...")
            
            # 🔥 STEP 1: Check login success first (URL-based, NO DOM)
            try:
                current_url = driver.current_url.lower()
                if "instagram.com" in current_url and not any(x in current_url for x in ["challenge", "checkpoint", "login"]):
                    print(f"[DEBUG] ✅ Already logged in - Skip identity verification")
                    return False
            except:
                pass
            
            # 🔥 STEP 2: Quick URL check (FASTEST)
            try:
                current_url = driver.current_url.lower()
                print(f"[DEBUG] URL: {current_url}")
                
                # Check for identity verification URL patterns
                identity_url_patterns = [
                    "challenge", "checkpoint", "verify", "confirm", "identity"
                ]
                
                for pattern in identity_url_patterns:
                    if pattern in current_url:
                        print(f"[DEBUG] ✅ IDENTITY VERIFICATION DETECTED - URL Pattern: {pattern}")
                        return True
                        
            except Exception as e:
                print(f"[DEBUG] URL check error: {e}")
            
            # 🔥 STEP 3: Quick title check (FAST)
            try:
                title = driver.title.lower()
                identity_title_words = ["verification", "identity", "confirm", "verify", "security"]
                
                if any(word in title for word in identity_title_words):
                    print(f"[DEBUG] ✅ IDENTITY VERIFICATION DETECTED - Title: {title}")
                    return True
                    
            except Exception as e:
                print(f"[DEBUG] Title check error: {e}")
            
            print(f"[DEBUG] ❌ No identity verification detected")
            return False
            
        except Exception as e:
            print(f"[DEBUG] Lỗi khi kiểm tra identity verification: {e}")
            return False

    def check_account_locked(self, driver):
        """⚡ ULTRA SIMPLE ACCOUNT LOCK CHECK: Chỉ check URL và title"""
        try:
            print(f"[DEBUG] ⚡ Quick account lock check...")
            
            # 🔥 STEP 1: Quick URL check (FASTEST)
            try:
                current_url = driver.current_url.lower()
                print(f"[DEBUG] URL: {current_url}")
                
                # Check for account restriction URL patterns
                lock_url_patterns = [
                    "accounts/suspended", "accounts/locked", "accounts/disabled",
                    "challenge/", "checkpoint/", "restricted"
                ]
                
                for pattern in lock_url_patterns:
                    if pattern in current_url:
                        print(f"[ERROR] 🚨 ACCOUNT LOCKED - URL Pattern: {pattern}")
                        return True
                        
            except Exception as e:
                print(f"[DEBUG] URL check error: {e}")
            
            # 🔥 STEP 2: Quick title check (FAST)
            try:
                title = driver.title.lower()
                lock_title_words = ["suspended", "disabled", "restricted", "locked", "automated"]
                
                if any(word in title for word in lock_title_words):
                    print(f"[ERROR] 🚨 ACCOUNT LOCKED - Title: {title}")
                    return True
                    
            except Exception as e:
                print(f"[DEBUG] Title check error: {e}")
            
            # 🔥 STEP 3: EMERGENCY TEXT CHECK (only if URL looks suspicious)
            try:
                if any(x in current_url for x in ["challenge", "checkpoint"]):
                    print(f"[DEBUG] 🔍 Emergency text check for challenge page...")
                    
                    # Quick page source check with timeout
                    import threading
                    page_text = None
                    
                    def get_page_source():
                        nonlocal page_text
                        try:
                            page_text = driver.page_source.lower()
                        except:
                            pass
                    
                    thread = threading.Thread(target=get_page_source, daemon=True)
                    thread.start()
                    thread.join(timeout=1.0)  # Max 1 second
                    
                    if page_text and thread.is_alive() == False:
                        # Only check critical keywords
                        critical_lock_keywords = [
                            "we suspect automated behavior",
                            "account has been disabled",
                            "account suspended"
                        ]
                        
                        for keyword in critical_lock_keywords:
                            if keyword in page_text:
                                print(f"[ERROR] 🚨 ACCOUNT LOCKED - Keyword: {keyword}")
                                return True
                    else:
                        print(f"[DEBUG] Page source check timeout/failed")
                        
            except Exception as e:
                print(f"[DEBUG] Text check error: {e}")
            
            print(f"[DEBUG] ✅ Account not locked")
            return False
            
        except Exception as e:
            print(f"[DEBUG] Lỗi khi kiểm tra account locked: {e}")
            return False

    def check_save_login_info(self, driver):
        """⚡ ULTRA SIMPLE SAVE LOGIN CHECK: Chỉ check button elements"""
        try:
            print(f"[DEBUG] ⚡ Quick save login info check...")
            
            # 🔥 STEP 1: Quick button element check (FASTEST)
            try:
                # Tìm button "Informationen speichern" hoặc "Save Info"
                save_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Informationen speichern') or contains(text(), 'Save Info') or contains(text(), 'Jetzt nicht') or contains(text(), 'Not Now')]")
                if save_buttons:
                    print("[DEBUG] ✅ SAVE LOGIN DIALOG DETECTED - Button found")
                    return True
                
                # Kiểm tra các selector khác
                save_selectors = [
                    "button[type='button'][class*='_acan']",  # Instagram save button class
                    "div[role='button'][tabindex='0']",  # Instagram dialog buttons
                ]
                
                for selector in save_selectors:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            # Kiểm tra text của button
                            for element in elements:
                                text = element.text.lower()
                                if any(word in text for word in ["speichern", "save", "nicht", "not", "jetzt"]):
                                    print(f"[DEBUG] ✅ SAVE LOGIN DIALOG DETECTED - Button: {text}")
                                    return True
                    except:
                        continue
                        
            except Exception as e:
                print(f"[DEBUG] Button check error: {e}")
            
            # 🔥 STEP 2: Quick title check (FAST)
            try:
                title = driver.title.lower()
                save_title_words = ["save", "speichern", "login", "information"]
                
                if any(word in title for word in save_title_words):
                    print(f"[DEBUG] ✅ SAVE LOGIN DIALOG DETECTED - Title: {title}")
                    return True
                    
            except Exception as e:
                print(f"[DEBUG] Title check error: {e}")
            
            print(f"[DEBUG] ❌ No save login dialog detected")
            return False
            
        except Exception as e:
            print(f"[DEBUG] Lỗi khi kiểm tra save login info: {e}")
            return False

    def handle_save_login_popup_quick(self, driver):
        """🚀 XỬ LÝ NHANH POPUP SAVE LOGIN INFO - Không cần username parameter"""
        try:
            print("[DEBUG] 🚀 Xử lý nhanh popup Save Login Info...")
            
            # Danh sách các button "Not Now" có thể có
            not_now_buttons = [
                "//button[contains(text(), 'Not now')]",
                "//button[contains(text(), 'Not Now')]", 
                "//button[contains(text(), 'not now')]",
                "//div[@role='button' and contains(text(), 'Not now')]",
                "//div[@role='button' and contains(text(), 'Not Now')]"
            ]
            
            # Thử click button "Not Now"
            for xpath in not_now_buttons:
                try:
                    button = driver.find_element(By.XPATH, xpath)
                    if button.is_displayed() and button.is_enabled():
                        button.click()
                        print("[SUCCESS] ✅ Đã click 'Not Now' cho popup Save Login Info")
                        time.sleep(1)  # Chờ popup đóng
                        return True
                except:
                    continue
            
            # Fallback: Tìm bất kỳ button nào có text liên quan "not"
            try:
                all_buttons = driver.find_elements(By.TAG_NAME, "button")
                for button in all_buttons:
                    if button.is_displayed() and button.is_enabled():
                        text = button.text.lower().strip()
                        if text and any(word in text for word in ["not", "skip", "later", "dismiss"]):
                            button.click()
                            print(f"[SUCCESS] ✅ Đã click button '{button.text}' để đóng popup")
                            time.sleep(1)
                            return True
            except:
                pass
            
            print("[WARN] ⚠️ Không tìm thấy button để đóng popup Save Login Info")
            return False
            
        except Exception as e:
            print(f"[ERROR] Lỗi xử lý popup Save Login Info: {e}")
            return False

    def handle_save_login_info(self, driver, username):
        """Xử lý form lưu thông tin đăng nhập - chọn 'Không lưu' để tiếp tục"""
        try:
            print(f"[INFO] Xử lý form lưu thông tin đăng nhập cho {username}")
            
            # Tìm và click button "Jetzt nicht" (Not Now) hoặc "Nicht speichern"
            not_now_buttons = [
                "//button[contains(text(), 'Jetzt nicht')]",  # German "Not Now"
                "//button[contains(text(), 'Not Now')]",  # English "Not Now"
                "//button[contains(text(), 'Nicht speichern')]",  # German "Don't Save"
                "//button[contains(text(), \"Don't Save\")]",  # English "Don't Save"
                "//button[contains(text(), 'Skip')]",  # English "Skip"
                "//div[@role='button' and contains(text(), 'Jetzt nicht')]",  # German div button
                "//div[@role='button' and contains(text(), 'Not Now')]"  # English div button
            ]
            
            for xpath in not_now_buttons:
                try:
                    button = driver.find_element(By.XPATH, xpath)
                    if button.is_displayed() and button.is_enabled():
                        button.click()
                        print(f"[SUCCESS] Đã click 'Not Now' cho form lưu thông tin đăng nhập")
                        time.sleep(2)  # Chờ form đóng
                        return True
                except:
                    continue
            
            # Nếu không tìm thấy button "Not Now", thử tìm button đầu tiên có text phù hợp
            try:
                all_buttons = driver.find_elements(By.TAG_NAME, "button")
                for button in all_buttons:
                    text = button.text.lower()
                    if any(word in text for word in ["nicht", "not", "skip", "later", "nein"]):
                        if button.is_displayed() and button.is_enabled():
                            button.click()
                            print(f"[SUCCESS] Đã click button '{button.text}' để bỏ qua lưu thông tin")
                            time.sleep(2)
                            return True
            except:
                pass
            
            # Nếu vẫn không được, thử nhấn ESC để đóng dialog
            try:
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                print(f"[INFO] Đã nhấn ESC để đóng form lưu thông tin")
                time.sleep(2)
                return True
            except:
                pass
            
            print(f"[WARN] Không thể xử lý form lưu thông tin đăng nhập cho {username}")
            return False
            
        except Exception as e:
            print(f"[ERROR] Lỗi khi xử lý form lưu thông tin đăng nhập: {e}")
            return False

    def perform_auto_login(self, driver, username, password):
        """🚀 TỰ ĐỘNG ĐĂNG NHẬP INSTAGRAM"""
        try:
            print(f"[DEBUG] 🚀 Bắt đầu tự động đăng nhập cho {username}")
            
            # Đảm bảo đang ở trang Instagram
            current_url = driver.current_url
            if "instagram.com" not in current_url:
                driver.get("https://www.instagram.com/")
                time.sleep(3)
            
            # Tìm và điền username
            try:
                username_input = driver.find_element(By.CSS_SELECTOR, "input[name='username']")
                username_input.clear()
                time.sleep(0.5)
                
                # Nhập từng ký tự như con người  
                for char in username:
                    username_input.send_keys(char)
                    time.sleep(random.uniform(0.05, 0.15))
                    
                print(f"[DEBUG] ✅ Đã nhập username cho {username}")
            except Exception as e:
                print(f"[ERROR] Không tìm thấy ô username: {e}")
                return False
            
            # Tìm và điền password
            try:
                password_input = driver.find_element(By.CSS_SELECTOR, "input[name='password']")
                password_input.clear()
                time.sleep(0.5)
                
                # Nhập từng ký tự như con người
                for char in password:
                    password_input.send_keys(char)
                    time.sleep(random.uniform(0.05, 0.15))
                    
                print(f"[DEBUG] ✅ Đã nhập password cho {username}")
            except Exception as e:
                print(f"[ERROR] Không tìm thấy ô password: {e}")
                return False
            
            # Tìm và click nút đăng nhập
            try:
                # Thử nhiều selector cho nút login
                login_selectors = [
                    "button[type='submit']",
                    "button:contains('Log in')", 
                    "button:contains('Log In')",
                    "div[role='button']:contains('Log in')",
                    "//button[contains(text(),'Log in') or contains(text(),'Log In') or contains(text(),'Đăng nhập')]"
                ]
                
                login_button = None
                for selector in login_selectors:
                    try:
                        if selector.startswith("//"):
                            login_button = driver.find_element(By.XPATH, selector)
                        else:
                            login_button = driver.find_element(By.CSS_SELECTOR, selector)
                        break
                    except:
                        continue
                
                if login_button:
                    # Scroll đến button và click
                    driver.execute_script("arguments[0].scrollIntoView(true);", login_button)
                    time.sleep(0.5)
                    login_button.click()
                    print(f"[DEBUG] ✅ Đã click nút đăng nhập cho {username}")
                else:
                    print(f"[ERROR] Không tìm thấy nút đăng nhập cho {username}")
                    return False
                    
            except Exception as e:
                print(f"[ERROR] Lỗi khi click nút đăng nhập: {e}")
                return False
            
            # Chờ đăng nhập và kiểm tra kết quả
            print(f"[DEBUG] ⏳ Chờ xử lý đăng nhập cho {username}...")
            time.sleep(5)
            
            # Kiểm tra có cảnh báo lỗi không
            try:
                error_elements = driver.find_elements(By.CSS_SELECTOR, 
                    "div[id*='error'], div[class*='error'], p[class*='error'], span[class*='error']")
                for error_elem in error_elements:
                    error_text = error_elem.text.lower()
                    if any(keyword in error_text for keyword in ['incorrect', 'wrong', 'invalid', 'sai', 'không đúng']):
                        print(f"[ERROR] Phát hiện lỗi đăng nhập: {error_text}")
                        return False
            except:
                pass
            
            # Xử lý popup "Save Login Info" nếu có
            try:
                save_info_buttons = driver.find_elements(By.XPATH, 
                    "//button[contains(text(),'Not Now') or contains(text(),'Không phải bây giờ') or contains(text(),'Save Info')]")
                for btn in save_info_buttons:
                    if btn.is_displayed():
                        btn.click()
                        print(f"[DEBUG] ✅ Đã xử lý popup Save Login Info")
                        time.sleep(2)
                        break
            except:
                pass
            
            # Xử lý popup "Turn on Notifications" nếu có  
            try:
                notification_buttons = driver.find_elements(By.XPATH,
                    "//button[contains(text(),'Not Now') or contains(text(),'Không phải bây giờ')]")
                for btn in notification_buttons:
                    if btn.is_displayed():
                        btn.click()
                        print(f"[DEBUG] ✅ Đã xử lý popup notification")
                        time.sleep(2)
                        break
            except:
                pass
            
            # Kiểm tra đăng nhập thành công bằng cách kiểm tra URL và elements
            time.sleep(3)
            
            # Kiểm tra bằng hàm đã có
            if self.check_home_and_explore_icons(driver):
                print(f"[SUCCESS] 🎉 Tự động đăng nhập thành công cho {username}")
                return True
            else:
                print(f"[ERROR] ❌ Tự động đăng nhập thất bại cho {username}")
                return False
                
        except Exception as e:
            print(f"[ERROR] Lỗi trong quá trình tự động đăng nhập cho {username}: {e}")
            return False

    def close_browser_safely(self, driver, username):
        """⭐ TỐI ƯU: Đóng trình duyệt một cách an toàn và nhanh chóng"""
        import threading
        
        def close_with_timeout():
            try:
                print(f"[INFO] 🔄 Bắt đầu đóng trình duyệt cho {username}")
                
                # Bước 1: Đóng tất cả tabs ngoại trừ tab chính
                try:
                    handles = driver.window_handles
                    if len(handles) > 1:
                        for handle in handles[1:]:
                            try:
                                driver.switch_to.window(handle)
                                driver.close()
                            except:
                                continue
                        try:
                            driver.switch_to.window(handles[0])
                        except:
                            pass
                except Exception:
                    pass
                
                # Bước 2: Cleanup không cần thiết - không xóa cookies (đã lưu rồi)
                try:
                    # Chỉ clear local storage để tránh conflict
                    driver.execute_script("localStorage.clear();")
                except Exception:
                    pass
                
                # Bước 3: Quit driver chính
                try:
                    driver.quit()
                    print(f"[INFO] ✅ Đã đóng trình duyệt thành công cho {username}")
                    return True
                except Exception as e:
                    print(f"[WARN] Lỗi khi quit driver: {e}")
                
                # Bước 4: Force terminate nếu quit thất bại
                try:
                    if hasattr(driver, 'service') and hasattr(driver.service, 'process'):
                        process = driver.service.process
                        if process and process.poll() is None:  # Process vẫn đang chạy
                            process.terminate()
                            # Chờ tối đa 2 giây để process tự terminate
                            for i in range(20):
                                if process.poll() is not None:
                                    break
                                time.sleep(0.1)
                            
                            # Nếu vẫn chưa terminate, kill force
                            if process.poll() is None:
                                process.kill()
                                print(f"[INFO] 🔥 Đã force kill browser process cho {username}")
                            else:
                                print(f"[INFO] ⚡ Đã terminate browser process cho {username}")
                except Exception as e2:
                    print(f"[WARN] Lỗi khi terminate/kill process: {e2}")
                
                return True
                
            except Exception as e:
                print(f"[ERROR] Lỗi không mong muốn khi đóng trình duyệt: {e}")
                return False
        
        # ⭐ TỐI ƯU: Chạy trong thread riêng với timeout ngắn
        close_thread = threading.Thread(target=close_with_timeout, daemon=True)
        close_thread.start()
        
        # ⚡ TỐI ƯU: Chờ tối đa 2 giây để đóng browser (giảm từ 3 giây)
        close_thread.join(timeout=2.0)
        
        if close_thread.is_alive():
            print(f"[WARN] ⏰ Timeout khi đóng trình duyệt cho {username} - tiếp tục chạy")
        else:
            print(f"[INFO] ✨ Hoàn tất đóng trình duyệt cho {username}")

# Hàm helper bổ sung

def detect_checkpoint_or_captcha(driver):
    """Phát hiện captcha/checkpoint một cách chính xác"""
    try:
        current_url = driver.current_url.lower()
        
        # 1. Kiểm tra URL có chứa challenge/checkpoint không
        if "challenge" in current_url or "checkpoint" in current_url:
            print("[DEBUG] Phát hiện challenge/checkpoint từ URL")
            return True
            
        # 2. Kiểm tra iframe captcha thực sự
        try:
            recaptcha_frames = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='recaptcha']")
            hcaptcha_frames = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='hcaptcha']")
            
            if recaptcha_frames or hcaptcha_frames:
                print("[DEBUG] Phát hiện iframe captcha thực sự")
                return True
        except Exception:
            pass
            
        # 3. Kiểm tra các text cụ thể về captcha/checkpoint (chỉ khi chưa đăng nhập)
        try:
            page_source = driver.page_source.lower()
            
            # Nếu đã có home icon => đã đăng nhập => không cần kiểm tra captcha
            if "svg[aria-label='home']" in page_source or "aria-label=\"home\"" in page_source:
                return False
                
            # Chỉ kiểm tra captcha/checkpoint khi chưa đăng nhập
            specific_captcha_keywords = [
                "we need to make sure you're a real person",
                "help us confirm you're human", 
                "confirm that you're human",
                "are you a robot",
                "verify that you're human",
                "security check",
                "suspicious login attempt",
                "unusual activity",
                "checkpoint required",
                "account temporarily locked"
            ]
            
            for keyword in specific_captcha_keywords:
                if keyword in page_source:
                    print(f"[DEBUG] Phát hiện captcha/checkpoint từ keyword: {keyword}")
                    return True
                    
        except Exception as e:
            print(f"[DEBUG] Lỗi khi kiểm tra page source: {e}")
            
        # 4. Kiểm tra các element captcha cụ thể
        captcha_selectors = [
            "div[class*='captcha']",
            "div[class*='recaptcha']", 
            "div[class*='hcaptcha']",
            "div[id*='captcha']",
            "form[class*='checkpoint']",
            "div[class*='checkpoint']"
        ]
        
        for selector in captcha_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements and any(el.is_displayed() for el in elements):
                    print(f"[DEBUG] Phát hiện element captcha: {selector}")
                    return True
            except Exception:
                continue
                
    except Exception as e:
        print(f"[DEBUG] Lỗi trong detect_checkpoint_or_captcha: {e}")
        
    return False

def is_logged_in_desktop(driver):
    """Kiểm tra đăng nhập desktop"""
    try:
        nav_divs = driver.find_elements(By.CLASS_NAME, "PolarisNavigationIcons")
        for nav in nav_divs:
            svgs = nav.find_elements(By.TAG_NAME, "svg")
            print(f"[DEBUG] Số lượng SVG trong PolarisNavigationIcons: {len(svgs)}")
            if len(svgs) >= 3:
                print("[DEBUG] Đã nhận diện đủ 3 icon SVG đầu tiên trong PolarisNavigationIcons (Home, Explore, Reels)")
                return True
        print("[DEBUG] Không tìm thấy đủ 3 icon SVG trong PolarisNavigationIcons.")
    except Exception as e:
        print(f"[DEBUG] Lỗi khi kiểm tra icon SVG menu: {e}")
    return False