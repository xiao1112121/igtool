import os
import sys
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
        self.init_ui()
        self.update_account_table()
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
        print("[DEBUG] Bắt đầu khởi tạo driver...")
        from selenium.webdriver.chrome.options import Options
        options = Options()
        
        # ẨN THANH ĐỊA CHỈ - SỬ DỤNG APP MODE VỚI KÍCH THƯỚC NHỎ
        options.add_argument("--app=https://www.instagram.com/")
        
        # Tắt các thông báo hệ thống của Chrome
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-save-password-bubble")
        options.add_argument("--disable-translate")
        options.add_argument("--disable-features=TranslateUI")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-extensions")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--no-first-run")
        
        # Tắt popup lưu mật khẩu, dịch, cookie, v.v.
        prefs = {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "translate": {"enabled": False},
            "intl.accept_languages": "en,en_US",
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_setting_values.automatic_downloads": 1,
            "profile.default_content_setting_values.popups": 2,
            "profile.default_content_setting_values.geolocation": 2,
            # Tắt popup khôi phục trang và session restore
            "session.restore_on_startup": 4,  # 4 = không khôi phục
            "profile.exit_type": "Normal",
            "profile.exited_cleanly": True,
            "browser.show_home_button": False,
            "browser.startup_page": 1,  # 1 = blank page
        }
        options.add_experimental_option("prefs", prefs)
        
        # Tắt các popup và khôi phục session
        options.add_argument("--disable-session-crashed-bubble")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-restore-session-state")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-renderer-backgrounding")
        options.add_argument("--disable-features=TranslateUI,VizDisplayCompositor")
        
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
        
        # Đảm bảo hiển thị giao diện desktop Instagram (không mobile)
        options.add_argument("--disable-mobile-emulation")
        options.add_argument("--force-device-scale-factor=1")
        
        # Kích thước cửa sổ nhỏ gọn 450x380px
        options.add_argument("--window-size=450,380")
        
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
        btn_add_account = QPushButton("Thêm tài khoản")
        btn_add_account.clicked.connect(self.add_account)
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
        self.account_table.setColumnCount(8)  # Tăng lên 10 cột
        self.account_table.setHorizontalHeaderLabels([
            "", "STT", "Tên đăng nhập", "Mật khẩu", "Trạng thái", 
            "Proxy", "Trạng thái Proxy", "Hành động cuối"
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
        self.account_table.setColumnWidth(5, 200)  # Đặt chiều rộng cố định
        header.setSectionResizeMode(6, QHeaderView.Fixed)  # Cột "Trạng thái Proxy"
        self.account_table.setColumnWidth(6, 150)  # Tăng chiều rộng cố định
        header.setSectionResizeMode(7, QHeaderView.Fixed)  # Cột "Follower"
        self.account_table.setColumnWidth(7, 79)
        header.setSectionResizeMode(8, QHeaderView.Fixed)  # Cột "Following"
        self.account_table.setColumnWidth(8, 79)
        header.setSectionResizeMode(9, QHeaderView.Stretch)  # Cột "Hành động cuối" - Giữ nguyên Stretch
        self.account_table.verticalHeader().setDefaultSectionSize(40)
        self.account_table.horizontalHeader().setFixedHeight(40)

        # Đảm bảo cột cuối cùng kéo giãn để hiển thị đầy đủ nội dung
        header.setStretchLastSection(True)

        # Thiết lập căn lề cho các tiêu đề cột
        self.account_table.horizontalHeader().setDefaultAlignment(Qt.AlignHCenter | Qt.AlignVCenter)

        self.account_table.setSelectionBehavior(QAbstractItemView.SelectRows)
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
                    # Đảm bảo mỗi tài khoản có trường 'proxy_status'
                    for account in accounts_data:
                        if "proxy_status" not in account:
                            account["proxy_status"] = "Chưa kiểm tra"
                    return accounts_data
            except json.JSONDecodeError:
                print("[ERROR] Lỗi đọc file accounts.json. File có thể bị hỏng.")
                return []
        return []

    def save_accounts(self):
        with open(self.accounts_file, 'w', encoding='utf-8') as f:
            json.dump(self.accounts, f, indent=4, ensure_ascii=False)
            print("[INFO] Tài khoản đã được lưu.")

    def add_account(self):
        username, ok = QInputDialog.getText(self, "Thêm tài khoản", "Tên người dùng:")
        if ok and username:
            password, ok = QInputDialog.getText(self, "Thêm tài khoản", "Mật khẩu:", QLineEdit.Password)
            if ok:
                proxy, ok = QInputDialog.getText(self, "Thêm tài khoản", "Proxy (tùy chọn):")
                if ok:
                    new_account = {
                        "selected": False,
                        "username": username,
                        "password": password,
                        "fullname": "",  # NEW: Thêm trường Họ tên
                        "proxy": proxy,
                        "status": "Chưa đăng nhập",
                        "gender": "-",  # Thêm cột giới tính
                        "followers": "",
                        "following": "",
                        "last_action": "",  # Thêm cột hành động cuối
                        "proxy_status": "Chưa kiểm tra"  # Khởi tạo trạng thái proxy
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

            # Tên đăng nhập
            username_item = QTableWidgetItem(account.get("username", ""))
            username_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.account_table.setItem(row_idx, 2, username_item)

            # Mật khẩu
            password_item = QTableWidgetItem(account.get("password", ""))
            password_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.account_table.setItem(row_idx, 3, password_item)

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
            self.account_table.setItem(row_idx, 4, status_item)

            # Proxy
            proxy_item = QTableWidgetItem(account.get("proxy", ""))
            proxy_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.account_table.setItem(row_idx, 5, proxy_item)

            # Trạng thái Proxy
            proxy_status_item = QTableWidgetItem(account.get("proxy_status", "Chưa kiểm tra"))
            proxy_status_item.setTextAlignment(Qt.AlignCenter)
            if account.get("proxy_status") == "Die":
                proxy_status_item.setForeground(QColor("red"))
            elif account.get("proxy_status") == "OK":
                proxy_status_item.setForeground(QColor("green"))
            else:
                proxy_status_item.setForeground(QColor("black"))
            self.account_table.setItem(row_idx, 6, proxy_status_item)

            # Follower
            follower_item = QTableWidgetItem(account.get("followers", ""))
            follower_item.setTextAlignment(Qt.AlignCenter)
            self.account_table.setItem(row_idx, 7, follower_item)

            # Following
            following_item = QTableWidgetItem(account.get("following", ""))
            following_item.setTextAlignment(Qt.AlignCenter)
            self.account_table.setItem(row_idx, 8, following_item)

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
            if status == "live":
                live += 1
            elif status == "die":
                die += 1
            if acc.get("selected", False):
                selected += 1
        not_selected = total - selected
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
        # Kiểm tra nếu tín hiệu bị block, bỏ qua
        if self.account_table.signalsBlocked():
            return

        row = item.row()
        col = item.column()

        if col == 0:  # Cột checkbox, đã được xử lý bởi on_checkbox_clicked
            return

        # Chỉ xử lý các cột có thể chỉnh sửa: Tên đăng nhập, Mật khẩu, Proxy
        if col == 2:  # Tên đăng nhập
            self.accounts[row]["username"] = item.text()
        elif col == 3:  # Mật khẩu
            self.accounts[row]["password"] = item.text()
        elif col == 5:  # Proxy
            self.accounts[row]["proxy"] = item.text()
        else:
            return  # Không xử lý các cột khác

        self.save_accounts()
        self.update_stats()

    def filter_accounts(self, text):
        filtered_accounts = [
            account for account in self.accounts
            if text.lower() in account.get("username", "").lower() or
            text.lower() in account.get("status", "").lower() or
            text.lower() in account.get("proxy", "").lower() or
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
        # Kích thước mỗi cửa sổ theo yêu cầu
        win_w, win_h = 450, 380
        
        # Lấy kích thước màn hình
        try:
            from PySide6.QtGui import QGuiApplication
            screen = QGuiApplication.primaryScreen()
            geometry = screen.geometry()
            screen_w, screen_h = geometry.width(), geometry.height()
            print(f"[DEBUG] Kích thước màn hình: {screen_w}x{screen_h}")
        except Exception:
            screen_w, screen_h = 1920, 1080  # fallback nếu không lấy được
        
        # Tính toán lưới xếp cửa sổ
        margin = 10  # Khoảng cách nhỏ giữa các cửa sổ
        effective_win_w = win_w + margin
        effective_win_h = win_h + margin
        
        # Số cột tối đa có thể xếp trên màn hình
        max_cols = max(1, (screen_w - margin) // effective_win_w)
        print(f"[DEBUG] Số cột tối đa: {max_cols}")
        
        positions = []
        for i in range(num_windows):
            # Tính vị trí trong lưới: từ trái sang phải, từ trên xuống dưới
            col = i % max_cols
            row = i // max_cols
            
            # Tính toán vị trí pixel
            x = margin + col * effective_win_w
            y = margin + row * effective_win_h
            
            # Đảm bảo không vượt quá màn hình
            if x + win_w > screen_w:
                x = screen_w - win_w - margin
            if y + win_h > screen_h:
                y = screen_h - win_h - margin
            
            positions.append((x, y, win_w, win_h))
            print(f"[DEBUG] Cửa sổ {i+1}: Hàng {row+1}, Cột {col+1} → Vị trí ({x}, {y})")
        
        return positions

    def login_selected_accounts(self):
        # Chạy đăng nhập cho từng tài khoản trong thread phụ, không block main thread
        import threading
        selected_accounts = [acc for acc in self.accounts if acc.get('selected')]
        if not selected_accounts:
            QMessageBox.information(self, "Thông báo", "Vui lòng chọn ít nhất 1 tài khoản để đăng nhập.")
            return
        def login_worker(account, window_position=None):
            try:
                self.login_instagram_and_get_info(account, window_position)
            except Exception as e:
                print(f"[ERROR][Thread] Lỗi khi đăng nhập tài khoản {account.get('username')}: {e}")
        window_positions = self.get_window_positions(len(selected_accounts))
        for idx, account in enumerate(selected_accounts):
            pos = window_positions[idx] if window_positions else None
            t = threading.Thread(target=login_worker, args=(account, pos), daemon=True)
            t.start()

    def login_instagram_and_get_info(self, account, window_position=None, max_retries=3, retry_delay=5):
        """Đăng nhập Instagram theo logic yêu cầu của user"""
        driver = None
        username = account.get("username")
        password = account.get("password")
        proxy = account.get("proxy") if getattr(self, 'use_proxy', True) else None
        
        print(f"[INFO] ===== BẮT ĐẦU ĐĂNG NHẬP: {username} =====")
        
        try:
            from PySide6.QtCore import QMetaObject, Qt
            
            # BƯỚC 1: MỞ CHROME DRIVER TIẾN HÀNH ĐĂNG NHẬP
            print(f"[1] Mở Chrome driver cho {username}")
            account["status"] = "Đang mở Chrome driver..."
            self.status_updated.emit(username, "Đang mở Chrome driver...")
            
            driver = self.init_driver(proxy, username=username)
            
            # Đặt vị trí cửa sổ ngay sau khi tạo để tránh đè lên nhau
            if window_position and len(window_position) == 4:
                x, y, width, height = window_position
                print(f"[DEBUG] Đặt vị trí cửa sổ cho {username}: ({x}, {y}) size ({width}, {height})")
                try:
                    driver.set_window_rect(x, y, width, height)
                    time.sleep(0.3)  # Chờ cửa sổ ổn định
                except Exception as e:
                    print(f"[WARN] Không thể đặt vị trí cửa sổ: {e}")
            else:
                # Vị trí mặc định nếu không có window_position
                try:
                    driver.set_window_rect(100, 100, 450, 380)
                except Exception as e:
                    print(f"[WARN] Không thể đặt vị trí mặc định: {e}")
            
            # Truy cập Instagram
            print(f"[DEBUG] Truy cập Instagram cho {username}")
            driver.get("https://www.instagram.com/")
            time.sleep(3)
            
            # BƯỚC 2: LOAD SESSION COOKIES
            print(f"[2] Load session cookies cho {username}")
            account["status"] = "Đang load session cookies..."
            self.status_updated.emit(username, "Đang load session cookies...")
            
            cookies_loaded = self.load_cookies(driver, username)
            print(f"[DEBUG] Kết quả load cookies cho {username}: {cookies_loaded}")
            
            if cookies_loaded:
                print(f"[DEBUG] Đã load cookies cho {username} - Refresh trang...")
                driver.refresh()
                time.sleep(3)
                print(f"[DEBUG] Sau refresh - URL: {driver.current_url}")
                
                # Debug DOM trước khi kiểm tra session
                print(f"[DEBUG] ===== KIỂM TRA SESSION BẰNG COOKIES CHO {username} =====")
                self.debug_instagram_dom(driver, username)
                
                # Kiểm tra session còn hạn không bằng cách check 2 icon
                print(f"[DEBUG] Gọi check_home_and_explore_icons để kiểm tra session cho {username}")
                session_valid = self.check_home_and_explore_icons(driver)
                print(f"[DEBUG] Kết quả kiểm tra session: {session_valid}")
                
                if session_valid:
                    print(f"[SUCCESS] ✅ Session còn hạn - Đăng nhập thành công bằng cookies: {username}")
                    # Lưu cookies và báo về app
                    self.save_cookies(driver, username)
                    account["status"] = "Đã đăng nhập"
                    self.status_updated.emit(username, account["status"])
                    # Đóng trình duyệt
                    driver.quit()
                    print(f"[INFO] Đã đóng trình duyệt cho {username}")
                    print(f"[INFO] ===== HOÀN TẤT: {username} =====")
                    return "Đã đăng nhập", "OK", None
                else:
                    print(f"[WARN] Session quá hạn cho {username} - Cần đăng nhập lại")
                    print(f"[DEBUG] URL hiện tại: {driver.current_url}")
                    try:
                        title = driver.title
                        print(f"[DEBUG] Title hiện tại: {title}")
                    except Exception as e:
                        print(f"[DEBUG] Lỗi khi lấy title: {e}")
                    
                    # Kiểm tra xem có phải đang ở trang login không
                    if "login" in driver.current_url.lower() or "accounts/login" in driver.current_url.lower():
                        print(f"[DEBUG] Đang ở trang login - session thật sự hết hạn")
                    else:
                        print(f"[DEBUG] Không ở trang login - có thể vẫn đang load hoặc có lỗi khác")
                        
                        # Kiểm tra xem có phải bị captcha/checkpoint không
                        if self.check_captcha_required(driver):
                            print(f"[WARN] ⚠️ Phát hiện captcha khi load cookies cho {username}")
                            account["status"] = "Checkpoint/Captcha: Cần thao tác thủ công"
                            self.status_updated.emit(username, account["status"])
                            # Giữ cửa sổ mở để user xử lý
                            continue_result = self.show_captcha_dialog_safe(driver, username, "captcha")
                            if continue_result:
                                # Sau khi user xử lý, check lại
                                if self.check_home_and_explore_icons(driver):
                                    print(f"[SUCCESS] ✅ Đăng nhập thành công sau xử lý captcha: {username}")
                                    self.save_cookies(driver, username)
                                    account["status"] = "Đã đăng nhập"
                                    self.status_updated.emit(username, account["status"])
                                    driver.quit()
                                    return "Đã đăng nhập", "OK", None
                            else:
                                driver.quit()
                                return "Đã bỏ qua", "Bỏ qua", None
            else:
                print(f"[DEBUG] Không có cookies hoặc không load được cookies cho {username}")
            
            # BƯỚC 3: SESSION QUÁ HẠN - YÊU CẦU NHẬP TÀI KHOẢN MẬT KHẨU
            print(f"[3] Session quá hạn - Nhập tài khoản mật khẩu cho {username}")
            account["status"] = "Session quá hạn - Đang nhập tài khoản mật khẩu..."
            self.status_updated.emit(username, account["status"])
            
            # Tìm và nhập username
            try:
                username_input = driver.find_element(By.NAME, "username")
                username_input.clear()
                username_input.send_keys(username)
                time.sleep(1)
                
                # Tìm và nhập password  
                password_input = driver.find_element(By.NAME, "password")
                password_input.clear()
                password_input.send_keys(password)
                time.sleep(1)
                
                # Nhấn Enter để đăng nhập
                password_input.send_keys(Keys.ENTER)
                print(f"[DEBUG] Đã gửi thông tin đăng nhập cho {username}")
                
            except Exception as e:
                print(f"[ERROR] Không thể nhập thông tin đăng nhập: {e}")
                account["status"] = "Lỗi nhập thông tin đăng nhập"
                self.status_updated.emit(username, account["status"])
                driver.quit()
                return "Lỗi nhập thông tin", "Lỗi", None
            
            # BƯỚC 4: SAU KHI ĐĂNG NHẬP - CHECK THEO LOGIC YÊU CẦU
            print(f"[4] Kiểm tra kết quả đăng nhập cho {username}")
            account["status"] = "Đang kiểm tra kết quả đăng nhập..."
            self.status_updated.emit(username, account["status"])
            
            # Chờ tối đa 15 giây để kiểm tra
            max_wait_time = 15
            check_interval = 2
            start_time = time.time()
            
            print(f"[DEBUG] ===== BẮT ĐẦU VÒNG LẶP KIỂM TRA CHO {username} =====")
            
            while time.time() - start_time < max_wait_time:
                try:
                    elapsed_time = time.time() - start_time
                    print(f"[DEBUG] Vòng lặp kiểm tra - Thời gian đã trôi qua: {elapsed_time:.1f}s/{max_wait_time}s")
                    
                    time.sleep(check_interval)
                    
                    print(f"[DEBUG] Kiểm tra trạng thái đăng nhập cho {username} - URL: {driver.current_url}")
                    
                    # KIỂM TRA THEO THỨ TỰ YÊU CẦU:
                    print(f"[DEBUG] ===== KIỂM TRA TRẠNG THÁI ĐĂNG NHẬP CHO {username} =====")
                    print(f"[DEBUG] URL hiện tại: {driver.current_url}")
                    
                    try:
                        title = driver.title
                        print(f"[DEBUG] Title hiện tại: {title}")
                    except Exception as e:
                        print(f"[DEBUG] Lỗi khi lấy title: {e}")
                    
                    # THỨ NHẤT: Check icon ngôi nhà ở góc dưới bên trái
                    # THỨ HAI: Check icon la bàn bên cạnh icon ngôi nhà (bên phải)
                    print(f"[DEBUG] Bước 1: Kiểm tra 2 icon Home + Explore cho {username}")
                    
                    # Debug DOM structure để hiểu layout
                    try:
                        self.debug_instagram_dom(driver, username)
                    except Exception as e:
                        print(f"[ERROR] Lỗi khi debug DOM: {e}")
                    
                    print(f"[DEBUG] Gọi hàm check_home_and_explore_icons cho {username}")
                    try:
                        icons_found = self.check_home_and_explore_icons(driver)
                        print(f"[DEBUG] Kết quả check_home_and_explore_icons: {icons_found}")
                        if icons_found:
                            print(f"[SUCCESS] ✅ ĐĂNG NHẬP THÀNH CÔNG - Tìm thấy cả 2 icon: {username}")
                            print(f"[SUCCESS] URL khi thành công: {driver.current_url}")
                            
                            # Lưu session cookies cho lần sau
                            print(f"[DEBUG] Đang lưu cookies cho {username}")
                            self.save_cookies(driver, username)
                            
                            # Báo về app đăng nhập thành công
                            print(f"[DEBUG] Đang cập nhật trạng thái về app cho {username}")
                            account["status"] = "Đã đăng nhập"
                            self.status_updated.emit(username, account["status"])
                            
                            # Đóng trình duyệt
                            print(f"[DEBUG] Đang đóng trình duyệt cho {username}")
                            driver.quit()
                            print(f"[INFO] Đã đóng trình duyệt cho {username}")
                            print(f"[SUCCESS] ===== HOÀN TẤT THÀNH CÔNG: {username} =====")
                            return "Đã đăng nhập", "OK", None
                    except Exception as e:
                        print(f"[ERROR] Lỗi khi check icons: {e}")
                        import traceback
                        traceback.print_exc()
                    
                    # KIỂM TRA FORM LỮU THÔNG TIN ĐĂNG NHẬP (SAVE LOGIN INFO)
                    if self.check_save_login_info(driver):
                        print(f"[INFO] 💾 Phát hiện form lưu thông tin đăng nhập cho {username}")
                        account["status"] = "Đang xử lý form lưu thông tin đăng nhập"
                        self.status_updated.emit(username, account["status"])
                        
                        # Xử lý form - chọn "Not Now" để tiếp tục
                        if self.handle_save_login_info(driver, username):
                            print(f"[SUCCESS] Đã xử lý form lưu thông tin đăng nhập cho {username}")
                            # Sau khi xử lý form, tiếp tục check 2 icon để xác nhận đăng nhập
                            time.sleep(2)  # Chờ một chút để trang load
                            if self.check_home_and_explore_icons(driver):
                                print(f"[SUCCESS] ✅ Đăng nhập thành công sau xử lý form lưu thông tin: {username}")
                                self.save_cookies(driver, username)
                                account["status"] = "Đã đăng nhập"
                                self.status_updated.emit(username, account["status"])
                                driver.quit()
                                print(f"[INFO] Đã đóng trình duyệt cho {username}")
                                print(f"[INFO] ===== HOÀN TẤT: {username} =====")
                                return "Đã đăng nhập", "OK", None
                        else:
                            print(f"[WARN] Không thể xử lý form lưu thông tin đăng nhập cho {username}")
                            # Vẫn tiếp tục logic, có thể form tự đóng
                    
                    # KIỂM TRA CAPTCHA
                    if self.check_captcha_required(driver):
                        print(f"[WARN] ⚠️ Phát hiện yêu cầu giải captcha cho {username}")
                        print(f"[DEBUG] URL khi phát hiện captcha: {driver.current_url}")
                        account["status"] = "Phát hiện yêu cầu giải captcha"
                        self.status_updated.emit(username, account["status"])
                        
                        # Giữ cửa sổ bật + hiển thị nút tiếp tục
                        continue_result = self.show_captcha_dialog_safe(driver, username, "captcha")
                        if continue_result:
                            print(f"[DEBUG] User đã giải captcha và nhấn tiếp tục")
                            # Tiếp tục chạy theo logic - check lại 2 icon
                            if self.check_home_and_explore_icons(driver):
                                print(f"[SUCCESS] ✅ Đăng nhập thành công sau giải captcha: {username}")
                                self.save_cookies(driver, username)
                                account["status"] = "Đã đăng nhập"
                                self.status_updated.emit(username, account["status"])
                                driver.quit()
                                print(f"[INFO] Đã đóng trình duyệt cho {username}")
                                print(f"[INFO] ===== HOÀN TẤT: {username} =====")
                                return "Đã đăng nhập", "OK", None
                        else:
                            print(f"[INFO] User chọn bỏ qua captcha")
                            account["status"] = "Đã bỏ qua captcha"
                            self.status_updated.emit(username, account["status"])
                            driver.quit()
                            return "Đã bỏ qua", "Bỏ qua", None
                    
                    # KIỂM TRA 2FA
                    if self.check_2fa_required(driver):
                        print(f"[WARN] ⚠️ Phát hiện yêu cầu nhập 2FA cho {username}")
                        account["status"] = "Phát hiện yêu cầu nhập 2FA"
                        self.status_updated.emit(username, account["status"])
                        
                        # Giữ cửa sổ trình duyệt + hiển thị nút tiếp tục
                        continue_result = self.show_captcha_dialog_safe(driver, username, "2fa")
                        if continue_result:
                            print(f"[DEBUG] User đã nhập 2FA và nhấn tiếp tục")
                            # Chạy theo logic đăng nhập thành công - check 2 icon
                            if self.check_home_and_explore_icons(driver):
                                print(f"[SUCCESS] ✅ Đăng nhập thành công sau nhập 2FA: {username}")
                                self.save_cookies(driver, username)
                                account["status"] = "Đã đăng nhập"
                                self.status_updated.emit(username, account["status"])
                                driver.quit()
                                print(f"[INFO] Đã đóng trình duyệt cho {username}")
                                print(f"[INFO] ===== HOÀN TẤT: {username} =====")
                                return "Đã đăng nhập", "OK", None
                        else:
                            print(f"[INFO] User chọn bỏ qua 2FA")
                            account["status"] = "Đã bỏ qua 2FA"
                            self.status_updated.emit(username, account["status"])
                            driver.quit()
                            return "Đã bỏ qua", "Bỏ qua", None
                    
                    # KIỂM TRA TÀI KHOẢN BỊ KHÓA
                    if self.check_account_locked(driver):
                        print(f"[ERROR] ❌ Tài khoản {username} bị khóa")
                        account["status"] = "Tài khoản Die"
                        self.status_updated.emit(username, account["status"])
                        # Đóng trình duyệt
                        driver.quit()
                        print(f"[INFO] Đã đóng trình duyệt cho {username}")
                        print(f"[INFO] ===== HOÀN TẤT: {username} =====")
                        return "Tài khoản Die", "Die", None
                    
                    else:
                        print(f"[DEBUG] Chưa xác định được trạng thái cho {username} - tiếp tục chờ...")
                    
                except Exception as e:
                    print(f"[ERROR] Lỗi khi kiểm tra trạng thái: {e}")
                    continue
            
            # TIMEOUT - KHÔNG XÁC ĐỊNH ĐƯỢC TRẠNG THÁI
            print(f"[WARN] ⏰ Timeout khi đăng nhập {username}")
            account["status"] = "Timeout đăng nhập"
            self.status_updated.emit(username, account["status"])
            driver.quit()
            return "Timeout", "Timeout", None
            
        except Exception as e:
            print(f"[ERROR] ❌ Lỗi không mong muốn khi đăng nhập {username}: {e}")
            account["status"] = f"Lỗi: {str(e)}"
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            return "Lỗi không mong muốn", "Lỗi", None

    def close_all_drivers(self):
        # Đóng từng driver trong thread riêng biệt để không block GUI
        import threading
        def close_driver_safe(driver):
            try:
                driver.quit()
            except Exception as e:
                print(f"[WARN] Lỗi khi đóng trình duyệt: {e}")
        for d in self.active_drivers:
            threading.Thread(target=close_driver_safe, args=(d["driver"] if isinstance(d, dict) and "driver" in d else d,)).start()
        self.active_drivers = []
        print("[INFO] Đã đóng tất cả các trình duyệt.")

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

    def show_context_menu(self, pos):
        """Hiển thị menu chuột phải."""
        print(f"[DEBUG] show_context_menu được gọi tại vị trí: {pos}")
        menu = AccountContextMenu(self)
        menu.exec(self.account_table.viewport().mapToGlobal(pos))

    def on_table_item_double_clicked(self, index):
        selected_account: dict = self.accounts[index.row()]
        QMessageBox.information(self, "Chi tiết tài khoản", 
            f"Tên đăng nhập: {selected_account.get('username', 'N/A')}\n"
            f"Mật khẩu: {selected_account.get('password', 'N/A')}\n"
            f"Trạng thái: {selected_account.get('status', 'N/A')}\n"
            f"Proxy: {selected_account.get('proxy', 'N/A')}\n"
            f"Trạng thái Proxy: {selected_account.get('proxy_status', 'N/A')}\n"
            f"Follower: {selected_account.get('followers', 'N/A')}\n"
            f"Following: {selected_account.get('following', 'N/A')}\n"
            f"Hành động cuối: {selected_account.get('last_action', 'N/A')}")

    @Slot(str, str)
    def on_status_updated(self, username, status):
        """Update trạng thái từ thread một cách an toàn"""
        # Tìm và cập nhật account trong danh sách
        for account in self.accounts:
            if account.get("username") == username:
                account["status"] = status
                break
        # Lưu và cập nhật UI
        self.save_accounts()
        self.update_account_table()
        print(f"[DEBUG] Đã cập nhật trạng thái cho {username}: {status}")

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
        os.makedirs('sessions', exist_ok=True)
        cookies = driver.get_cookies()
        with open(f'sessions/{username}_cookies.json', 'w', encoding='utf-8') as f:
            json.dump(cookies, f)

    def load_cookies(self, driver, username):
        cookies_path = f'sessions/{username}_cookies.json'
        if os.path.exists(cookies_path):
            with open(cookies_path, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            for cookie in cookies:
                # Selenium yêu cầu phải ở đúng domain mới add được cookie
                driver.add_cookie(cookie)
            return True
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
        """Kiểm tra nhanh đã đăng nhập thành công chưa"""
        try:
            # Kiểm tra URL trước
            current_url = driver.current_url.lower()
            if any(x in current_url for x in ["login", "challenge", "checkpoint"]):
                return False
            
            # Kiểm tra các dấu hiệu đăng nhập thành công (theo thứ tự ưu tiên)
            login_indicators = [
                # 1. Home icon (nhanh nhất)
                ("svg[aria-label='Home']", "Home icon"),
                ("svg[aria-label='Trang chủ']", "Home icon (VI)"),
                
                # 2. Navigation bar
                ("nav[role='navigation']", "Navigation bar"),
                
                # 3. User avatar
                ("img[alt*='profile']", "Profile avatar"),
                ("span[data-testid='user-avatar']", "User avatar"),
                
                # 4. Story tray
                ("div[role='button'][tabindex='0']", "Story tray"),
            ]
            
            for selector, description in login_indicators:
                try:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                    if element.is_displayed():
                        print(f"[DEBUG] Đăng nhập xác nhận qua {description}")
                        return True
                except Exception:
                    continue
            
            return False
            
        except Exception as e:
            print(f"[ERROR] Lỗi khi kiểm tra đăng nhập nhanh: {e}")
            return False
    
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
        """Kiểm tra icon ngôi nhà và la bàn ở Instagram (app mode + desktop mode)"""
        try:
            print("[DEBUG] Đang kiểm tra icon ngôi nhà và la bàn ở Instagram...")
            print(f"[DEBUG] URL hiện tại: {driver.current_url}")
            
            # Thêm debug về page source
            try:
                page_source = driver.page_source
                print(f"[DEBUG] Page source length: {len(page_source)}")
                if "instagram.com" in page_source.lower():
                    print("[DEBUG] ✅ Trang Instagram đã load")
                else:
                    print("[DEBUG] ❌ Trang Instagram chưa load đúng")
            except:
                pass
            
            # THỨ NHẤT: Check icon Home (ngôi nhà) - mở rộng cho app mode
            home_icon_selectors = [
                # Instagram app mode và desktop mode
                "a[href='/'] svg",
                "a[href='/'][role='link'] svg",
                "a[href='/'][aria-label*='Home'] svg",
                "a[href='/'][aria-label*='Trang chủ'] svg",
                # Aria labels cho home icon
                "svg[aria-label='Home']",
                "svg[aria-label='Trang chủ']",
                "svg[aria-label*='Home']",
                "svg[aria-label*='Trang chủ']",
                # Bottom navigation bar
                "div[role='tablist'] a[href='/'] svg",
                "div[role='tablist'] svg[aria-label='Home']",
                "div[role='tablist'] svg[aria-label='Trang chủ']",
                "nav a[href='/'] svg", 
                "nav svg[aria-label='Home']",
                # Navigation containers
                "nav[role='navigation'] a[href='/'] svg",
                "div[class*='nav'] a[href='/'] svg",
                "div[class*='bottom'] a[href='/'] svg",
                # Mobile/app mode specific
                "div[class*='mobile'] a[href='/'] svg",
                "section a[href='/'] svg",
                # Generic navigation
                "[role='navigation'] a[href='/'] svg",
                "[role='tablist'] a[href='/'] svg"
            ]
            
            home_found = False
            home_location = None
            
            for selector in home_icon_selectors:
                try:
                    home_icons = driver.find_elements(By.CSS_SELECTOR, selector)
                    for icon in home_icons:
                        if icon.is_displayed():
                            location = icon.location
                            print(f"[DEBUG] Tìm thấy Home icon tại vị trí X={location['x']}, Y={location['y']}")
                            home_found = True
                            home_location = location
                            break
                except Exception as e:
                    print(f"[DEBUG] Lỗi khi tìm home icon với selector {selector}: {e}")
                    continue
                if home_found:
                    break
            
            if not home_found:
                print("[DEBUG] ❌ Không tìm thấy Home icon")
                # Debug thêm về DOM structure
                try:
                    all_links = driver.find_elements(By.CSS_SELECTOR, "a[href='/']")
                    print(f"[DEBUG] Tìm thấy {len(all_links)} link href='/'")
                    for i, link in enumerate(all_links[:3]):  # Chỉ log 3 link đầu
                        print(f"[DEBUG] Link {i+1}: {link.get_attribute('outerHTML')[:200]}...")
                except:
                    pass
                return False
            
            # THỨ HAI: Check icon Explore/Search (la bàn) - mở rộng cho app mode
            explore_icon_selectors = [
                # Instagram app mode và desktop mode
                "a[href='/explore/'] svg",
                "a[href*='explore'] svg",
                "a[href='/explore/'][role='link'] svg",
                "a[href*='explore'][role='link'] svg",
                # Aria labels cho explore icon
                "svg[aria-label='Search and Explore']",
                "svg[aria-label='Search']",
                "svg[aria-label='Explore']", 
                "svg[aria-label='Tìm kiếm']",
                "svg[aria-label='Khám phá']",
                "svg[aria-label*='Search']",
                "svg[aria-label*='Explore']",
                "svg[aria-label*='Tìm kiếm']",
                # Bottom navigation explore
                "div[role='tablist'] a[href='/explore/'] svg",
                "div[role='tablist'] a[href*='explore'] svg",
                "div[role='tablist'] svg[aria-label='Search']",
                "div[role='tablist'] svg[aria-label='Explore']",
                "div[role='tablist'] svg[aria-label='Search and Explore']",
                "nav a[href='/explore/'] svg",
                "nav a[href*='explore'] svg",
                "nav svg[aria-label='Search']",
                "nav svg[aria-label='Explore']",
                # Navigation containers
                "nav[role='navigation'] a[href*='explore'] svg",
                "div[class*='nav'] a[href*='explore'] svg",
                "div[class*='bottom'] a[href*='explore'] svg",
                # Mobile/app mode specific
                "div[class*='mobile'] a[href*='explore'] svg",
                "section a[href*='explore'] svg",
                # Generic navigation
                "[role='navigation'] a[href*='explore'] svg",
                "[role='tablist'] a[href*='explore'] svg"
            ]
            
            explore_found = False
            
            for selector in explore_icon_selectors:
                try:
                    explore_icons = driver.find_elements(By.CSS_SELECTOR, selector)
                    for icon in explore_icons:
                        if icon.is_displayed():
                            location = icon.location
                            print(f"[DEBUG] Tìm thấy Explore icon tại vị trí X={location['x']}, Y={location['y']}")
                            # Kiểm tra icon có gần home icon không (cùng vùng navigation)
                            if home_location:
                                x_diff = abs(location['x'] - home_location['x'])
                                y_diff = abs(location['y'] - home_location['y'])
                                print(f"[DEBUG] Khoảng cách với Home icon: X={x_diff}, Y={y_diff}")
                                # Cho phép linh hoạt hơn về vị trí
                                if y_diff < 100:  # Cùng hàng ngang (trong vòng 100px)
                                    print(f"[DEBUG] ✅ Explore icon ở cùng vùng với Home icon")
                                    explore_found = True
                                    break
                            else:
                                # Nếu không có home_location, chấp nhận explore icon
                                explore_found = True
                                break
                except Exception as e:
                    print(f"[DEBUG] Lỗi khi tìm explore icon với selector {selector}: {e}")
                    continue
                if explore_found:
                    break
            
            if not explore_found:
                print("[DEBUG] ❌ Không tìm thấy Explore icon")
                # Debug thêm về DOM structure
                try:
                    all_explore_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='explore']")
                    print(f"[DEBUG] Tìm thấy {len(all_explore_links)} link explore")
                    for i, link in enumerate(all_explore_links[:3]):  # Chỉ log 3 link đầu
                        print(f"[DEBUG] Explore link {i+1}: {link.get_attribute('outerHTML')[:200]}...")
                except:
                    pass
                return False
            
            print("[DEBUG] ✅ Tìm thấy cả 2 icon: Home + Explore ở Instagram")
            return True
            
        except Exception as e:
            print(f"[DEBUG] Lỗi khi kiểm tra icons: {e}")
            return False
    
    def check_captcha_required(self, driver):
        """Kiểm tra xem có phải báo giải captcha không - CHỈ KHI THẬT SỰ CÓ CAPTCHA"""
        try:
            current_url = driver.current_url.lower()
            page_source = driver.page_source.lower()
            
            # ĐIỀU KIỆN 1: Kiểm tra URL có chứa challenge/checkpoint - THẬT SỰ QUAN TRỌNG
            if any(x in current_url for x in ["challenge", "checkpoint"]):
                print(f"[DEBUG] URL chứa challenge/checkpoint: {current_url}")
                return True
            
            # ĐIỀU KIỆN 2: Kiểm tra có iframe captcha thật sự
            try:
                captcha_frames = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='recaptcha'], iframe[src*='hcaptcha']")
                if captcha_frames:
                    print("[DEBUG] Tìm thấy iframe captcha thật sự")
                    return True
            except:
                pass
            
            # ĐIỀU KIỆN 3: Kiểm tra có text captcha challenge cụ thể
            specific_captcha_texts = [
                "please solve this captcha",
                "security check required", 
                "verify you're not a robot",
                "complete the security check",
                "we need to verify",
                "suspicious activity detected"
            ]
            
            for text in specific_captcha_texts:
                if text in page_source:
                    print(f"[DEBUG] Tìm thấy text captcha cụ thể: {text}")
                    return True
            
            # KHÔNG detect dựa trên keywords chung chung nữa
            return False
            
        except Exception as e:
            print(f"[DEBUG] Lỗi khi kiểm tra captcha: {e}")
            return False
    
    def check_2fa_required(self, driver):
        """Kiểm tra xem có phải yêu cầu nhập 2FA không"""
        try:
            page_source = driver.page_source.lower()
            
            # Kiểm tra các keywords liên quan đến 2FA
            twofa_keywords = [
                "enter the code", "nhập mã", "verification code",
                "two-factor", "2fa", "authenticator",
                "security code", "mã bảo mật",
                "enter your code", "nhập mã của bạn"
            ]
            
            for keyword in twofa_keywords:
                if keyword in page_source:
                    return True
            
            # Kiểm tra có input field cho verification code
            try:
                code_inputs = driver.find_elements(By.NAME, "verificationCode")
                if code_inputs:
                    return True
                
                # Kiểm tra các selector khác cho 2FA input
                twofa_selectors = [
                    "input[placeholder*='code']",
                    "input[placeholder*='mã']",
                    "input[name*='verification']",
                    "input[name*='security']"
                ]
                
                for selector in twofa_selectors:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        return True
            except:
                pass
            
            return False
            
        except Exception as e:
            print(f"[DEBUG] Lỗi khi kiểm tra 2FA: {e}")
            return False
    
    def check_account_locked(self, driver):
        """Kiểm tra xem có phải bị khóa tài khoản không"""
        try:
            page_source = driver.page_source.lower()
            
            # Kiểm tra các keywords về tài khoản bị khóa
            locked_keywords = [
                "account has been disabled", "tài khoản đã bị vô hiệu hóa",
                "account has been locked", "tài khoản đã bị khóa", 
                "we suspended your account", "chúng tôi đã tạm ngưng tài khoản",
                "account suspended", "tài khoản bị tạm ngưng",
                "disabled for violating", "bị vô hiệu hóa vì vi phạm",
                "your account has been deactivated", "tài khoản đã bị hủy kích hoạt"
            ]
            
            for keyword in locked_keywords:
                if keyword in page_source:
                    return True
            
            return False
            
        except Exception as e:
            print(f"[DEBUG] Lỗi khi kiểm tra account locked: {e}")
            return False

    def check_save_login_info(self, driver):
        """Kiểm tra xem có phải form lưu thông tin đăng nhập không"""
        try:
            page_source = driver.page_source.lower()
            
            # Kiểm tra các keywords về form lưu thông tin đăng nhập
            save_login_keywords = [
                "deine login-informationen speichern",  # German
                "save your login info", "save login info",  # English
                "enregistrer vos informations de connexion",  # French
                "salvar informações de login",  # Portuguese
                "guardar información de inicio de sesión",  # Spanish
                "informationen speichern",  # German short
                "login-informationen",  # German
                "save login information",  # English
                "remember login",  # English
                "lưu thông tin đăng nhập",  # Vietnamese
                "ghi nhớ đăng nhập"  # Vietnamese
            ]
            
            for keyword in save_login_keywords:
                if keyword in page_source:
                    print(f"[DEBUG] Phát hiện form lưu thông tin đăng nhập: {keyword}")
                    return True
            
            # Kiểm tra các button text cụ thể
            try:
                # Tìm button "Informationen speichern" hoặc "Save Info"
                save_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Informationen speichern') or contains(text(), 'Save Info') or contains(text(), 'Jetzt nicht') or contains(text(), 'Not Now')]")
                if save_buttons:
                    print("[DEBUG] Tìm thấy button lưu thông tin đăng nhập")
                    return True
                
                # Kiểm tra các selector khác
                save_selectors = [
                    "button[type='button'][class*='_acan']",  # Instagram save button class
                    "div[role='button'][tabindex='0']",  # Instagram dialog buttons
                    "button:contains('speichern')",  # German save
                    "button:contains('Save')",  # English save
                    "button:contains('Not Now')",  # English not now
                    "button:contains('Jetzt nicht')"  # German not now
                ]
                
                for selector in save_selectors:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            # Kiểm tra text của button
                            for element in elements:
                                text = element.text.lower()
                                if any(word in text for word in ["speichern", "save", "nicht", "not"]):
                                    print(f"[DEBUG] Tìm thấy button lưu thông tin: {text}")
                                    return True
                    except:
                        continue
                        
            except Exception as e:
                print(f"[DEBUG] Lỗi khi tìm button lưu thông tin: {e}")
            
            return False
            
        except Exception as e:
            print(f"[DEBUG] Lỗi khi kiểm tra save login info: {e}")
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

    def close_browser_safely(self, driver, username):
        """Đóng trình duyệt một cách an toàn"""
        try:
            print(f"[INFO] Đang đóng trình duyệt cho {username}")
            
            # Đóng tất cả tabs trừ tab chính
            try:
                handles = driver.window_handles
                if len(handles) > 1:
                    for handle in handles[1:]:
                        driver.switch_to.window(handle)
                        driver.close()
                    driver.switch_to.window(handles[0])
            except Exception:
                pass
            
            # Xóa cache và cookies không cần thiết
            try:
                driver.delete_all_cookies()
            except Exception:
                pass
            
            # Đóng driver
            driver.quit()
            print(f"[SUCCESS] Đã đóng trình duyệt cho {username}")
            
        except Exception as e:
            print(f"[ERROR] Lỗi khi đóng trình duyệt cho {username}: {e}")
            try:
                driver.quit()
            except Exception:
                pass

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