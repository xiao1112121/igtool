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
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSize, QModelIndex, QRect, QEvent
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

    def init_driver(self, proxy=None, username=None):
        print("[DEBUG] Bắt đầu khởi tạo driver...")
        from selenium.webdriver.chrome.options import Options
        options = Options()
        # Ẩn thanh địa chỉ, tab, menu, mở ở chế độ app window
        options.add_argument("--app=https://www.instagram.com/accounts/login/")
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
        }
        options.add_experimental_option("prefs", prefs)
        # ... các option khác như user-agent, proxy ...
        random_user_agent = random.choice(self.USER_AGENTS)
        options.add_argument(f"user-agent={random_user_agent}")
        random_language = random.choice(self.LANGUAGES)
        options.add_argument(f"--lang={random_language}")
        options.add_argument(f"--accept-lang={random_language}")
        print(f"[DEBUG] Sử dụng User-Agent: {random_user_agent}")
        print(f"[DEBUG] Sử dụng Ngôn ngữ: {random_language}")
        if self.stealth_mode_enabled:
            options.add_argument("--incognito")
            print("[DEBUG] Chế độ ẩn danh được bật.")
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
            print("[DEBUG] Chrome driver đã được khởi tạo thành công")
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
        # Kích thước mỗi cửa sổ
        win_w, win_h = 432, 405
        # Lấy kích thước màn hình (giả sử 1920x1080, có thể lấy động nếu cần)
        try:
            from PySide6.QtGui import QGuiApplication
            screen = QGuiApplication.primaryScreen()
            geometry = screen.geometry()
            screen_w, screen_h = geometry.width(), geometry.height()
        except Exception:
            screen_w, screen_h = 1920, 1080  # fallback nếu không lấy được
        # Số cột tối đa
        max_cols = max(1, screen_w // win_w)
        positions = []
        for i in range(num_windows):
            col = i % max_cols
            row = i // max_cols
            x = col * win_w
            y = row * win_h
            positions.append((x, y, win_w, win_h))
        return positions

    def login_selected_accounts(self):
        selected_accounts = [acc for acc in self.accounts if acc.get("selected")]
        if not selected_accounts:
            QMessageBox.warning(self, "Đăng nhập tài khoản", "Vui lòng chọn ít nhất một tài khoản để đăng nhập.")
            return
        num_accounts_to_login = len(selected_accounts)
        window_positions = self.get_window_positions(num_accounts_to_login)
        max_workers = min(8, num_accounts_to_login)  # Giới hạn tối đa 8 tài khoản đăng nhập đồng thời
        print(f"[DEBUG] Đang đăng nhập {num_accounts_to_login} tài khoản với {max_workers} trình duyệt đồng thời.")
        # BỎ HOÀN TOÀN QProgressDialog, chỉ cập nhật trạng thái trực tiếp vào bảng
        # self.progress_dialog = QProgressDialog(...)
        # self.progress_dialog.show()
        # Thực hiện đăng nhập đa luồng như cũ, nhưng mỗi lần cập nhật trạng thái, cập nhật trực tiếp vào bảng
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_account = {
                executor.submit(self.login_instagram_and_get_info, account, window_positions[i]): account
                for i, account in enumerate(selected_accounts)
            }
            completed_count = 0
            for future in as_completed(future_to_account):
                account = future_to_account[future]
                try:
                    result = future.result()
                    print(f"[DEBUG] Kết quả từ login_instagram_and_get_info cho {account.get('username', 'N/A')}: {result} (Kiểu: {type(result)}) (Độ dài: {len(result) if isinstance(result, tuple) else 'N/A'})")
                    if result is None:
                        print(f"[ERROR] login_instagram_and_get_info trả về None cho {account.get('username', 'N/A') }.")
                        login_status = "Lỗi không xác định (None)"
                        proxy_status = "Lỗi không xác định"
                        driver = None
                    elif isinstance(result, tuple) and len(result) == 3:
                        login_status, proxy_status, driver = result
                        account["status"] = login_status
                        account["proxy_status"] = proxy_status
                        if login_status == "Đã đăng nhập" and driver is not None:
                            # Xóa driver cũ nếu đã tồn tại cho username này
                            self.active_drivers = [d for d in self.active_drivers if not (isinstance(d, dict) and d.get("username") == account.get("username"))]
                            self.active_drivers.append({"username": account.get("username"), "driver": driver})
                            print(f"[DEBUG] Đã lưu driver cho {account.get('username')} vào active_drivers.")
                            self.save_accounts()
                    else:
                        print(f"[ERROR] Kết quả trả về không đúng định dạng cho {account.get('username', 'N/A')}. Expected (status, proxy_status, driver), got: {result}")
                        login_status = "Lỗi dữ liệu trả về"
                        proxy_status = "Lỗi không xác định"
                        driver = None
                    account["status"] = login_status
                    account["proxy_status"] = proxy_status
                except Exception as e:
                    account["status"] = f"Lỗi: {type(e).__name__}"
                    account["proxy_status"] = "Lỗi không xác định"
                    print(f"[ERROR] Tài khoản {account.get('username', 'N/A')} tạo ra một ngoại lệ: {e}")
                    traceback.print_exc()
                finally:
                    completed_count += 1
                    self.update_account_table()
        self.update_account_table()

    def login_instagram_and_get_info(self, account, window_position=None, max_retries=3, retry_delay=5):
        driver = None
        username = account.get("username")
        password = account.get("password")
        proxy = account.get("proxy") if getattr(self, 'use_proxy', True) else None
        def _perform_login():
            login_status = None
            proxy_status = None
            driver = None
            try:
                account["status"] = "Đang khởi tạo trình duyệt..."
                self.update_account_table()
                driver = self.init_driver(proxy, username=username)
                if window_position and len(window_position) == 4:
                    x, y, width, height = window_position
                else:
                    # Giá trị mặc định nếu không truyền vào
                    x, y, width, height = 100, 100, 1200, 800
                driver.set_window_rect(x, y, width, height)
                print(f"[DEBUG] Đã đặt vị trí cửa sổ cho {username} tại ({x}, {y}, {width}, {height})")
                account["status"] = "Đang mở Instagram..."
                self.update_account_table()
                driver.get("https://www.instagram.com/")
                cookies_loaded = self.load_cookies(driver, username)
                if cookies_loaded:
                    account["status"] = "Đã load cookies, kiểm tra session..."
                    self.update_account_table()
                    print(f"[DEBUG] Đã load cookies cho {username}, thử vào Instagram không cần nhập lại.")
                    driver.refresh()
                    time.sleep(2)
                    current_url = driver.current_url
                    # Kiểm tra đã đăng nhập thành công bằng session/cookies
                    if (
                        not detect_checkpoint_or_captcha(driver)
                        and "instagram.com" in current_url
                        and not any(x in current_url for x in ["login", "challenge"])
                    ):
                        try:
                            # Kiểm tra biểu tượng Home
                            home_icon = driver.find_element(By.CSS_SELECTOR, "svg[aria-label='Home']")
                            if home_icon.is_displayed():
                                print("[INFO] Đăng nhập thành công bằng session/profile!")
                                login_status = "Đã đăng nhập"
                                proxy_status = "OK"
                                self.save_cookies(driver, username)
                                account["status"] = "Đã đăng nhập"
                                self.update_account_table()
                                return login_status, proxy_status, driver
                        except Exception:
                            pass
                        # Nếu không tìm thấy Home, thử kiểm tra avatar
                        avatar_btn = None
                        try:
                            avatar_btn = driver.find_element(By.XPATH, "//img[contains(@src, 's150x150') or contains(@alt, 'profile')]")
                            if avatar_btn.is_displayed():
                                print("[INFO] Đăng nhập thành công, đã vào trang cá nhân!")
                                login_status = "Đã đăng nhập"
                                proxy_status = "OK"
                                self.save_cookies(driver, username)
                                account["status"] = "Đã đăng nhập"
                                self.update_account_table()
                                return login_status, proxy_status, driver
                        except Exception:
                            pass
                    else:
                        print(f"[DEBUG] Session/profile không hợp lệ hoặc cần đăng nhập lại cho {username}.")
                        account["status"] = "Session/profile không hợp lệ, thử đăng nhập lại..."
                        self.update_account_table()
                # Nếu chưa đăng nhập, mới nhập lại tài khoản/mật khẩu
                account["status"] = "Đang nhập username..."
                self.update_account_table()
                # Phối hợp kiểm tra ô nhập username và đăng nhập thành công
                username_input = wait_for_element(driver, By.NAME, "username", timeout=5)
                if username_input:
                    # Thực hiện nhập username/password như cũ
                    for c in username:
                        username_input.send_keys(c)
                        time.sleep(random.uniform(0.05, 0.13))
                    random_delay(0.1, 0.2)
                    password_input = wait_for_element(driver, By.NAME, "password", timeout=3)
                    if not password_input:
                        raise Exception("Không thể tìm thấy ô nhập password")
                    for c in password:
                        password_input.send_keys(c)
                        time.sleep(random.uniform(0.05, 0.13))
                    password_input.send_keys(Keys.ENTER)
                    time.sleep(1)
                    # Tiếp tục các bước như cũ (click nút đăng nhập, xử lý popup...)
                    # ...
                else:
                    # Không có ô nhập username, kiểm tra đăng nhập thành công
                    for _ in range(10):
                        current_url = driver.current_url
                        if (
                            not detect_checkpoint_or_captcha(driver)
                            and "instagram.com" in current_url
                            and not any(x in current_url for x in ["login", "challenge"])
                        ):
                            try:
                                home_icon = driver.find_element(By.CSS_SELECTOR, "svg[aria-label='Home']")
                                if home_icon.is_displayed():
                                    print("[INFO] Đăng nhập thành công bằng session/profile!")
                                    login_status = "Đã đăng nhập"
                                    proxy_status = "OK"
                                    self.save_cookies(driver, username)
                                    account["status"] = "Đã đăng nhập"
                                    self.update_account_table()
                                    return login_status, proxy_status, driver
                            except Exception:
                                pass
                            try:
                                avatar_btn = driver.find_element(By.XPATH, "//img[contains(@src, 's150x150') or contains(@alt, 'profile')]")
                                if avatar_btn.is_displayed():
                                    print("[INFO] Đăng nhập thành công, đã vào trang cá nhân!")
                                    login_status = "Đã đăng nhập"
                                    proxy_status = "OK"
                                    self.save_cookies(driver, username)
                                    account["status"] = "Đã đăng nhập"
                                    self.update_account_table()
                                    return login_status, proxy_status, driver
                            except Exception:
                                pass
                        time.sleep(1)
                    # Nếu chưa đủ yếu tố đăng nhập thành công, kiểm tra captcha, 2FA, checkpoint
                    if detect_checkpoint_or_captcha(driver):
                        return "Yêu cầu giải Captcha/Checkpoint", "Lỗi xác minh", None
                    # TODO: Thêm hàm detect_2fa nếu có
                    # elif detect_2fa(driver):
                    #     return "Yêu cầu nhập 2FA", "Lỗi xác minh", None
                    else:
                        return "Không xác định được trạng thái đăng nhập", "Lỗi không xác định", None
                account["status"] = "Đang gửi form đăng nhập..."
                self.update_account_table()
                password_input = wait_for_element(driver, By.NAME, "password", timeout=3)
                if not password_input:
                    raise Exception("Không thể tìm thấy ô nhập password")
                password_input.send_keys(Keys.ENTER)
                time.sleep(1)
                login_button = wait_for_element(driver, By.CSS_SELECTOR, "button[type='submit']", timeout=3)
                if not login_button:
                    try:
                        login_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Log In') or contains(text(), 'Se connecter') or contains(text(), 'Connexion') or contains(text(), 'Đăng nhập') or @type='submit']")
                    except Exception:
                        login_button = None
                if login_button:
                    try:
                        driver.execute_script("arguments[0].click();", login_button)
                        print(f"[DEBUG] Đã click nút đăng nhập cho {username} (đa ngôn ngữ)")
                    except Exception as e:
                        print(f"[ERROR] Không thể click nút đăng nhập: {e}")
                else:
                    print("[ERROR] Không tìm thấy nút đăng nhập!")
                account["status"] = "Đang kiểm tra checkpoint/captcha..."
                self.update_account_table()
                if detect_checkpoint_or_captcha(driver):
                    account["status"] = "Checkpoint/Captcha: Cần thao tác thủ công"
                    self.update_account_table()
                    from PySide6.QtWidgets import QMessageBox
                    msg_box = QMessageBox()
                    msg_box.setWindowTitle("Captcha/Xác minh")
                    msg_box.setText("Phát hiện captcha hoặc checkpoint/xác minh. Vui lòng thao tác thủ công trên trình duyệt, sau đó nhấn 'Tiếp tục' để hoàn tất đăng nhập.")
                    msg_box.setStandardButtons(QMessageBox.Ok)
                    msg_box.button(QMessageBox.Ok).setText("Tiếp tục")
                    msg_box.exec()
                    print("[DEBUG] User đã nhấn Tiếp tục sau khi giải captcha/checkpoint.")
                random_delay(0.3, 0.7)
                login_button = wait_for_element(driver, By.CSS_SELECTOR, "button[type='submit']", timeout=5)
                if not login_button:
                    raise Exception("Không thể tìm thấy nút đăng nhập")
                driver.execute_script("arguments[0].click();", login_button)
                print(f"[DEBUG] Đã click nút đăng nhập cho {username} bằng JavaScript")
                account["status"] = "Đang kiểm tra checkpoint/captcha lần 2..."
                self.update_account_table()
                if detect_checkpoint_or_captcha(driver):
                    account["status"] = "Checkpoint/Captcha: Cần thao tác thủ công"
                    self.update_account_table()
                    from PySide6.QtWidgets import QMessageBox
                    msg_box = QMessageBox()
                    msg_box.setWindowTitle("Captcha/Xác minh")
                    msg_box.setText("Phát hiện captcha hoặc checkpoint/xác minh. Vui lòng thao tác thủ công trên trình duyệt, sau đó nhấn 'Tiếp tục' để hoàn tất đăng nhập.")
                    msg_box.setStandardButtons(QMessageBox.Ok)
                    msg_box.button(QMessageBox.Ok).setText("Tiếp tục")
                    msg_box.exec()
                    print("[DEBUG] User đã nhấn Tiếp tục sau khi giải captcha/checkpoint.")
                # Xử lý pop-up "Lưu thông tin đăng nhập"
                try:
                    not_now_button_xpath = (
                        "//button[text()='Not Now'] | "
                        "//button[text()='Lúc khác'] | "
                        "//button[text()='Später'] | "
                        "//button[text()='Más tarde'] | "
                        "//button[text()='Jetzt nicht'] | "
                        "//button[contains(.,'Not Now')] | "
                        "//button[contains(.,'Lúc khác')] | "
                        "//div[text()='Lưu thông tin đăng nhập?']/ancestor::div[contains(@class, 'x1n2onr6')]//button[contains(.,'Lúc khác')] | "
                        "//div[text()='Save your login info?']/ancestor::div[contains(@class, 'x1n2onr6')]//button[contains(.,'Not Now')]"
                    )
                    not_now_button = wait_for_element_clickable(driver, By.XPATH, not_now_button_xpath, timeout=3)
                    if not_now_button:
                        print(f"[DEBUG] Đã click nút 'Not Now' (lưu thông tin đăng nhập) cho {username}.")
                        random_delay(0.2, 0.5)
                except Exception as e:
                    print(f"[DEBUG] Không tìm thấy hoặc không thể click nút 'Not Now' (lưu thông tin đăng nhập) cho {username}: {e}")
                # Xử lý pop-up "Bật thông báo"
                try:
                    turn_on_notifications_not_now_xpath = (
                        "//button[text()='Not Now'] | "
                        "//button[text()='Lúc khác'] | "
                        "//button[text()='Später'] | "
                        "//button[text()='Ahora no'] | "
                        "//button[contains(.,'Not Now')] | "
                        "//button[contains(.,'Lúc khác')] | "
                        "//div[text()='Turn on notifications?']/ancestor::div[contains(@class, 'x1n2onr6')]//button[contains(.,'Not Now')] | "
                        "//div[text()='Bật thông báo?']/ancestor::div[contains(@class, 'x1n2onr6')]//button[contains(.,'Lúc khác')]"
                    )
                    turn_on_notifications_not_now_button = wait_for_element_clickable(driver, By.XPATH, turn_on_notifications_not_now_xpath, timeout=3)
                    if turn_on_notifications_not_now_button:
                        print(f"[DEBUG] Đã click nút 'Not Now' (thông báo) cho {username}.")
                        random_delay(0.2, 0.5)
                except Exception as e:
                    print(f"[DEBUG] Không tìm thấy hoặc không thể click nút 'Not Now' (thông báo) cho {username}: {e}")
                random_delay(0.5, 1.2)
                # --- Tối ưu vòng lặp chờ avatar/profile ---
                try:
                    account["status"] = "Đang xác thực profile..."
                    self.update_account_table()
                    def fast_find_avatar(driver, timeout=1.5):
                        start = time.time()
                        avatar_selectors = [
                            "//span[@data-testid='user-avatar']",
                            "//div[@role='button']//span[@data-testid='user-avatar']",
                            "//header//img[contains(@alt, 'profile') or contains(@src, 'profile')]",
                            "//img[contains(@src, 's150x150')]",
                            "//img[contains(@src, 'default_profile')]",
                            "//div[contains(@style, 'border-radius')]//img",
                            "//nav//img",
                            "//header//img",
                        ]
                        while time.time() - start < timeout:
                            for sel in avatar_selectors:
                                try:
                                    elem = driver.find_element(By.XPATH, sel)
                                    if elem.is_displayed():
                                        return elem
                                except Exception:
                                    continue
                            time.sleep(0.05)
                        return None

                    avatar_btn = fast_find_avatar(driver, timeout=1.5)
                    if not avatar_btn:
                        try:
                            menu_btn = driver.find_element(By.XPATH, "//div[@role='button' and @tabindex='0']")
                            if menu_btn.is_displayed():
                                driver.execute_script("arguments[0].click();", menu_btn)
                                print("[DEBUG] Đã click menu profile để lộ avatar.")
                                avatar_btn = fast_find_avatar(driver, timeout=0.3)
                        except Exception:
                            pass
                    if not avatar_btn:
                        driver.get("https://www.instagram.com/")
                        self.close_popups(driver)
                        avatar_btn = fast_find_avatar(driver, timeout=1.5)
                    if not avatar_btn:
                        print("[ERROR] Không tìm thấy avatar profile sau đăng nhập (tối ưu selector).")
                        driver.quit()
                        return "Không xác nhận đăng nhập", "Lỗi không xác định", None
                    try:
                        driver.execute_script("arguments[0].click();", avatar_btn)
                        print("[DEBUG] Đã click vào avatar profile (tối ưu selector).")
                    except Exception as e:
                        print(f"[ERROR] Không thể click avatar: {e}")
                        driver.quit()
                        return "Lỗi click avatar", "Lỗi không xác định", None
                    import re
                    profile_loaded = False
                    for _ in range(8):  # Giảm số lần lặp, mỗi lần 0.07s
                        url = driver.current_url
                        if re.search(r"instagram\.com/[^/?#]+/?$", url):
                            profile_loaded = True
                            break
                        try:
                            header = driver.find_element(By.XPATH, "//header//h2 | //header//div//h2")
                            if header.is_displayed():
                                profile_loaded = True
                                break
                        except Exception:
                            pass
                        time.sleep(0.07)
                    if not profile_loaded:
                        print("[ERROR] Không load được profile sau khi click avatar (tối ưu selector).")
                        driver.quit()
                        return "Không xác nhận được profile", "Lỗi không xác định", None
                    # Lấy username từ URL hoặc header
                    profile_username = None
                    url = driver.current_url
                    match = re.search(r"instagram\.com/([^/?#]+)/?$", url)
                    if match:
                        profile_username = match.group(1)
                        print(f"[DEBUG] Username lấy từ URL: {profile_username}")
                    else:
                        try:
                            header = driver.find_element(By.XPATH, "//header//h2 | //header//div//h2")
                            profile_username = header.text.strip()
                            print(f"[DEBUG] Username lấy từ header: {profile_username}")
                        except Exception:
                            print("[ERROR] Không lấy được username từ header profile.")
                    if profile_username and profile_username.lower() == username.lower():
                        print("[INFO] Đăng nhập thành công, username khớp!")
                        login_status = "Đã đăng nhập"
                        proxy_status = "OK"
                        account["status"] = "Đã đăng nhập"
                        account["last_action"] = "Đăng nhập"
                        return login_status, proxy_status, driver
                    else:
                        print("[ERROR] Username trên profile không khớp hoặc không lấy được!")
                        login_status = "Không xác nhận được profile"
                        proxy_status = "Lỗi không xác định"
                        account["last_action"] = "Không xác nhận profile"
                        return login_status, proxy_status, None
                except Exception as e:
                    login_status = "Lỗi không xác định"
                    proxy_status = "Lỗi không xác định"
                    return login_status, proxy_status, None
            finally:
                # Chỉ quit driver nếu đăng nhập thất bại và KHÔNG phải trạng thái cần giữ cửa sổ cho captcha
                if driver and login_status not in ["Đã đăng nhập", "Cần giải Captcha thủ công"]:
                    import threading
                    threading.Thread(target=lambda: driver.quit()).start()
                    print(f"[DEBUG] Đã gửi lệnh đóng trình duyệt cho {username} (thread riêng)")
        # Thực hiện đăng nhập với logic thử lại
        login_status, proxy_status, driver = _perform_login()
        return login_status, proxy_status, driver

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

# Thêm hàm nhận diện captcha/checkpoint đa ngôn ngữ

def detect_checkpoint_or_captcha(driver):
    keywords = [
        "captcha", "robot", "security", "checkpoint", "verify", "xác minh", "bảo mật",
        "本人確認", "協力", "確認", "アカウント", "不審なアクティビティ", "制限", "ステップ"
    ]
    try:
        page_text = driver.page_source.lower()
        for kw in keywords:
            if kw.lower() in page_text:
                return True
        # Kiểm tra iframe recaptcha/hcaptcha
        if driver.find_elements(By.CSS_SELECTOR, "iframe[src*='recaptcha']"):
            return True
        if driver.find_elements(By.CSS_SELECTOR, "iframe[src*='hcaptcha']"):
            return True
    except Exception:
        pass
    return False