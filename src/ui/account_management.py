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
    QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView, QSizePolicy, QStyledItemDelegate, QMenu, QProgressDialog, QInputDialog)
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
from src.utils.captcha_handler import CaptchaHandler
from src.ui.utils import random_delay, wait_for_element, wait_for_element_clickable, retry_operation
from src.ui.context_menus import AccountContextMenu
from concurrent.futures import ThreadPoolExecutor, as_completed

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
        self.captcha_handler = CaptchaHandler('b452b70e7afcd461cbd3758dac95b3c0')  # Thêm dòng này

    def init_driver(self, proxy=None):
        print("[DEBUG] Bắt đầu khởi tạo driver...")
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
        try:
            driver = wire_webdriver.Chrome(seleniumwire_options=proxy_options, options=options)
            print("[DEBUG] Chrome driver đã được khởi tạo thành công")
            return driver
        except Exception as e:
            print(f"[ERROR] Lỗi khi khởi tạo Chrome driver: {str(e)}")
            raise

    def handle_recaptcha(self, driver, username):
        """Xử lý reCAPTCHA khi gặp phải."""
        try:
            # Kiểm tra xem có reCAPTCHA không
            recaptcha_frame = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='recaptcha']"))
            )
            print(f"[DEBUG] Phát hiện reCAPTCHA cho tài khoản {username}")

            # Chuyển đến frame của reCAPTCHA
            driver.switch_to.frame(recaptcha_frame)

            # Lấy site key của reCAPTCHA
            site_key = driver.find_element(By.CLASS_NAME, "g-recaptcha").get_attribute("data-sitekey")
            print(f"[DEBUG] Site key của reCAPTCHA: {site_key}")

            # Chuyển về frame chính
            driver.switch_to.default_content()

            # Gọi API 2captcha để giải captcha
            solver = TwoCaptcha('b452b70e7afcd461cbd3758dac95b3c0')  # Sử dụng API key đã được cấu hình
            try:
                result = solver.recaptcha(
                    sitekey=site_key,
                    url=driver.current_url,
                )
                print(f"[DEBUG] Đã nhận kết quả từ 2captcha cho {username}")

                # Điền kết quả vào reCAPTCHA
                driver.execute_script(
                    f'document.getElementById("g-recaptcha-response").innerHTML="{result["code"]}";'
                )
                print(f"[DEBUG] Đã điền kết quả reCAPTCHA cho {username}")

                # Submit form
                submit_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
                )
                submit_button.click()
                print(f"[DEBUG] Đã submit form sau khi giải reCAPTCHA cho {username}")

                # Đợi một chút để xem kết quả
                time.sleep(3)
                return True

            except Exception as e:
                print(f"[ERROR] Lỗi khi giải reCAPTCHA cho {username}: {e}")
                return False

        except TimeoutException:
            print(f"[DEBUG] Không tìm thấy reCAPTCHA cho {username}")
            return True  # Không có reCAPTCHA, coi như thành công
        except Exception as e:
            print(f"[ERROR] Lỗi không xác định khi xử lý reCAPTCHA cho {username}: {e}")
            return False

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

        # Nút LOAD
        btn_load = QPushButton("LOAD")
        btn_load.setFixedSize(60, 30)  # Đặt kích thước cố định cho nút LOAD là 80x35px để hiển thị đầy đủ chữ
        btn_load.setProperty("role", "main")  # Sử dụng style main button
        btn_load.setProperty("color", "yellow")  # Sử dụng màu vàng
        btn_load.clicked.connect(self.load_accounts)
        toolbar_layout.addWidget(btn_load)

        # Khu vực thống kê
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(8)

        self.total_accounts_label = QLabel("Tổng: 0")
        self.total_accounts_label.setStyleSheet("color: #333333; font-weight: semibold; font-size: 10.5pt;")
        stats_layout.addWidget(self.total_accounts_label)

        self.live_accounts_label = QLabel("Live: 0")
        self.live_accounts_label.setStyleSheet("color: #4CAF50; font-weight: semibold; font-size: 10.5pt;")
        stats_layout.addWidget(self.live_accounts_label)

        self.die_accounts_label = QLabel("Die: 0")
        self.die_accounts_label.setStyleSheet("color: #D32F2F; font-weight: semibold; font-size: 10.5pt;")
        stats_layout.addWidget(self.die_accounts_label)

        toolbar_layout.addLayout(stats_layout)

        # Search bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Tìm kiếm tài khoản...")
        self.search_input.textChanged.connect(self.filter_accounts)
        self.search_input.setFixedWidth(150)  # Đặt chiều rộng cố định
        self.search_input.setFixedHeight(35)  # Giữ nguyên chiều cao
        toolbar_layout.addWidget(self.search_input)

        # Layout for buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)  # Space between buttons

        btn_search = QPushButton("🔍")  # Đổi tên nút và đặt biểu tượng kính lúp trực tiếp
        btn_search.clicked.connect(lambda: self.filter_accounts(self.search_input.text()))  # Kết nối với filter_accounts
        btn_search.setFixedSize(50, 35)  # Đặt kích thước cố định là 50x35px
        btn_search.setProperty("role", "main")  # Sử dụng style main button
        btn_search.setProperty("color", "blue")  # Đổi màu xanh da trời
        button_layout.addWidget(btn_search)

        toolbar_layout.addLayout(button_layout)

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

        self.account_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.account_table.setEditTriggers(QTableWidget.NoEditTriggers)  # Disable editing
        self.account_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.account_table.customContextMenuRequested.connect(self.show_context_menu)
        self.account_table.itemChanged.connect(self.handle_item_changed)  # Connect itemChanged signal
        self.account_table.verticalHeader().setVisible(False)  # Ẩn cột số thứ tự bên trái
        self.account_table.itemDoubleClicked.connect(self.on_table_item_double_clicked)  # Connect double click signal

        right_layout.addWidget(self.account_table)
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

    def update_account_table(self, accounts_to_display: Optional[List[Dict[str, Union[str, bool]]]] = None) -> None:
        if accounts_to_display is None:
            accounts_to_display = self.accounts

        self.account_table.blockSignals(True) # Block signals during update
        self.account_table.setRowCount(len(accounts_to_display))
        status_color_map = {
            "Hoạt động": "#C8E6C9",
            "Checkpoint": "#FFF9C4",
            "Bị khóa": "#FFCDD2",
            "Banned": "#E57373",
            "Cần xác minh": "#B3E5FC",
            "Đang nuôi": "#F0F4C3",
            "Spam": "#FFECB3",
            "Đang gửi tin nhắn": "#D1C4E9",
            "Lỗi đăng nhập": "#FFAB91",
            "Hết phiên": "#B0BEC5",
            "Proxy lỗi": "#BCAAA4",
            "Chưa kiểm tra": "#F5F5F5",
            "Tạm dừng": "#BDBDBD",
            "Mới thêm": "#AED581",
        }
        for row_idx, account in enumerate(accounts_to_display):
            username = str(account.get("username", ""))
            current_folder = str(self.folder_map.get(username, "Tổng"))
            # Cột 0: STT
            self.account_table.setItem(row_idx, 0, QTableWidgetItem(str(row_idx + 1)))
            # Cột 1: Tên người dùng
            self.account_table.setItem(row_idx, 1, QTableWidgetItem(username))
            # Cột 2: Thư mục
            self.account_table.setItem(row_idx, 2, QTableWidgetItem(current_folder))
            # Đổi màu dòng theo trạng thái
            status = account.get("status", "")
            color = status_color_map.get(status, "#FFFFFF")
            for col in range(self.account_table.columnCount()):
                item = self.account_table.item(row_idx, col)
                if item:
                    item.setBackground(QColor(color))
        self.account_table.blockSignals(False) # Unblock signals

    def on_checkbox_clicked(self, row, new_state):
        # Hàm này được kết nối từ delegate để xử lý khi trạng thái checkbox thay đổi
        if row < len(self.accounts):
            self.accounts[row]["selected"] = new_state
            self.save_accounts()
            print(f"[DEBUG] Checkbox tại hàng {row} được chuyển thành: {new_state}. Tài khoản: {self.accounts[row]['username']}")

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

    def get_window_positions(self, num_windows):
        screen = QGuiApplication.primaryScreen().geometry()
        screen_width = screen.width()
        screen_height = screen.height()
        window_width = 448
        window_height = 415
        positions = []
        max_cols = max(1, screen_width // window_width)
        max_rows = max(1, screen_height // window_height)
        cols = max_cols
        for i in range(num_windows):
            row = i // cols
            col = i % cols
            x = col * window_width
            y = row * window_height
            # Thêm random nhỏ để tránh trùng hoàn toàn
            x += random.randint(0, 12)
            y += random.randint(0, 12)
            # Đảm bảo không vượt quá màn hình
            x = min(max(0, x), screen_width - window_width)
            y = min(max(0, y), screen_height - window_height)
            positions.append((x, y, window_width, window_height))
        return positions

    def login_selected_accounts(self):
        selected_accounts = [acc for acc in self.accounts if acc.get("selected")]
        if not selected_accounts:
            QMessageBox.warning(self, "Đăng nhập tài khoản", "Vui lòng chọn ít nhất một tài khoản để đăng nhập.")
            return
        num_accounts_to_login = len(selected_accounts)
        window_positions = self.get_window_positions(num_accounts_to_login)
        max_workers = min(5, num_accounts_to_login)
        print(f"[DEBUG] Đang đăng nhập {num_accounts_to_login} tài khoản với {max_workers} trình duyệt đồng thời.")
        self.progress_dialog = QProgressDialog("Đang đăng nhập tài khoản...", "Hủy", 0, num_accounts_to_login, self)
        self.progress_dialog.setWindowTitle("Tiến trình đăng nhập")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.canceled.connect(self.close_all_drivers)
        self.progress_dialog.show()
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
                    elif isinstance(result, tuple) and len(result) == 2:
                        login_status, proxy_status = result
                        account["status"] = login_status
                        account["proxy_status"] = proxy_status
                        if login_status == "Đã đăng nhập":
                            self.save_accounts()
                    else:
                        print(f"[ERROR] Kết quả trả về không đúng định dạng cho {account.get('username', 'N/A')}. Expected (status, proxy_status), got: {result}")
                        login_status = "Lỗi dữ liệu trả về"
                        proxy_status = "Lỗi không xác định"
                    account["status"] = login_status
                    account["proxy_status"] = proxy_status
                except Exception as e:
                    account["status"] = f"Lỗi: {type(e).__name__}"
                    account["proxy_status"] = "Lỗi không xác định"
                    print(f"[ERROR] Tài khoản {account.get('username', 'N/A')} tạo ra một ngoại lệ: {e}")
                    traceback.print_exc()
                finally:
                    completed_count += 1
                    self.progress_dialog.setValue(completed_count)
                    self.update_account_table()
        self.progress_dialog.close()
        self.update_account_table()

    def login_instagram_and_get_info(self, account, window_position=None, max_retries=3, retry_delay=5):
        driver = None
        username = account.get("username")
        password = account.get("password")
        proxy = account.get("proxy")
        def _perform_login():
            nonlocal driver
            nonlocal proxy
            login_status = "Thất bại"
            proxy_status = "Chưa kiểm tra"
            try:
                print(f"[DEBUG] Bắt đầu đăng nhập cho tài khoản {username}")
                # Khởi tạo driver với proxy nếu có
                if proxy:
                    current_proxy_info = next((p for p in self.proxies if f"{p.get('ip')}:{p.get('port')}:{p.get('user')}:{p.get('pass')}" == proxy), None)
                    if current_proxy_info and current_proxy_info.get("status") == "Die":
                        print(f"[WARN] Proxy {proxy} cho tài khoản {username} đang ở trạng thái Die, đang cố gắng gán proxy mới.")
                        self._assign_new_proxy(account)
                        proxy = account.get("proxy")  # Cập nhật proxy sau khi gán mới
                        if not proxy:  # Nếu không tìm được proxy mới
                            proxy_status = "Không có proxy khả dụng"
                            return "Lỗi Proxy", proxy_status
                    elif proxy == "":  # Nếu proxy là một chuỗi rỗng (người dùng không điền)
                        print(f"[DEBUG] Tài khoản {username} không sử dụng proxy.")
                        proxy = None  # Đặt proxy về None để init_driver không dùng proxy
                    elif proxy is None and self.proxies:  # Nếu proxy là None và có proxy khả dụng
                        print(f"[DEBUG] Tài khoản {username} chưa có proxy, đang cố gắng gán proxy mới từ danh sách.")
                        self._assign_new_proxy(account)
                        proxy = account.get("proxy")  # Cập nhật proxy sau khi gán mới
                        if not proxy:  # Nếu không tìm được proxy mới
                            proxy_status = "Không có proxy khả dụng"
                            return "Lỗi Proxy", proxy_status
                    elif proxy is None and not self.proxies:  # Nếu proxy là None và không có proxy khả dụng
                        print(f"[DEBUG] Tài khoản {username} không sử dụng proxy (hoặc không có proxy nào được tải).")
                        proxy = None  # Đặt proxy về None để init_driver không dùng proxy

                # Đảm bảo proxy đã được gán giá trị trước khi sử dụng
                if proxy is None:
                    proxy = None  # Đảm bảo proxy là None nếu không có proxy nào được gán

                driver = self.init_driver(proxy)

                # Đặt vị trí và kích thước cửa sổ nếu có
                if window_position:
                    x, y, width, height = window_position
                    driver.set_window_rect(x, y, width, height)
                    print(f"[DEBUG] Đã đặt vị trí cửa sổ cho {username} tại ({x}, {y}, {width}, {height})")

                # Truy cập trang đăng nhập Instagram
                driver.get("https://www.instagram.com/accounts/login/")
                print(f"[DEBUG] Đã truy cập trang đăng nhập cho {username}")
                # --- Tắt popup/banner nếu có ---
                self.close_popups(driver)

                # Chờ và chấp nhận cookie nếu banner xuất hiện
                try:
                    accept_cookies_button = wait_for_element_clickable(driver, By.XPATH, "//button[text()='Cho phép tất cả cookie'] | //button[text()='Accept All'] | //button[text()='Allow all cookies']", timeout=5)
                    if accept_cookies_button:
                        print(f"[DEBUG] Đã chấp nhận cookie cho {username}.")
                        random_delay(1, 2)  # Chờ một chút sau khi click
                except Exception as e:
                    print(f"[DEBUG] Không tìm thấy hoặc không thể click nút chấp nhận cookie cho {username}: {e}")

                # Đợi cho trang đăng nhập tải xong
                username_input = wait_for_element(driver, By.NAME, "username", timeout=10)
                if not username_input:
                    raise Exception("Không thể tìm thấy ô nhập username")
                print(f"[DEBUG] Trang đăng nhập đã tải xong cho {username}")

                # Điền thông tin đăng nhập
                password_input = wait_for_element(driver, By.NAME, "password", timeout=5)
                if not password_input:
                    raise Exception("Không thể tìm thấy ô nhập password")

                random_delay()
                username_input.send_keys(username)

                random_delay()
                password_input.send_keys(password)

                random_delay(1, 2)  # Thêm một độ trễ ngắn trước khi click nút đăng nhập
                login_button = wait_for_element(driver, By.CSS_SELECTOR, "button[type='submit']", timeout=10)
                if not login_button:
                    raise Exception("Không thể tìm thấy nút đăng nhập")
                driver.execute_script("arguments[0].click();", login_button)  # Click bằng JavaScript
                print(f"[DEBUG] Đã click nút đăng nhập cho {username} bằng JavaScript")

                # Thêm xử lý cho pop-up "Lưu thông tin đăng nhập"
                try:
                    not_now_button_xpath = (
                        "//button[text()='Not Now'] | "
                        "//button[text()='Lúc khác'] | "
                        "//button[text()='Später'] | "  # German "Later"
                        "//button[text()='Más tarde'] | "  # Spanish "Later"
                        "//button[text()='Jetzt nicht'] | "  # German "Not now"
                        "//button[contains(.,'Not Now')] | "  # More general contains
                        "//button[contains(.,'Lúc khác')] | "  # More general contains
                        "//div[text()='Lưu thông tin đăng nhập?']/ancestor::div[contains(@class, 'x1n2onr6')]//button[contains(.,'Lúc khác')] | "  # Specific for login info save prompt (Vietnamese)
                        "//div[text()='Save your login info?']/ancestor::div[contains(@class, 'x1n2onr6')]//button[contains(.,'Not Now')]"  # Specific for login info save prompt (English)
                    )
                    not_now_button = wait_for_element_clickable(driver, By.XPATH, not_now_button_xpath, timeout=7)  # Tăng timeout
                    if not_now_button:
                        print(f"[DEBUG] Đã click nút 'Not Now' (lưu thông tin đăng nhập) cho {username}.")
                        random_delay(1, 2)  # Chờ một chút sau khi click
                except Exception as e:
                    print(f"[DEBUG] Không tìm thấy hoặc không thể click nút 'Not Now' (lưu thông tin đăng nhập) cho {username}: {e}")

                # Thêm xử lý cho pop-up "Bật thông báo" (nếu có)
                try:
                    turn_on_notifications_not_now_xpath = (
                        "//button[text()='Not Now'] | "
                        "//button[text()='Lúc khác'] | "
                        "//button[text()='Später'] | "
                        "//button[text()='Ahora no'] | "  # Spanish "Not now"
                        "//button[contains(.,'Not Now')] | "
                        "//button[contains(.,'Lúc khác')] | "
                        "//div[text()='Turn on notifications?']/ancestor::div[contains(@class, 'x1n2onr6')]//button[contains(.,'Not Now')] | "  # Specific for notifications prompt (English)
                        "//div[text()='Bật thông báo?']/ancestor::div[contains(@class, 'x1n2onr6')]//button[contains(.,'Lúc khác')]"  # Specific for notifications prompt (Vietnamese)
                    )
                    turn_on_notifications_not_now_button = wait_for_element_clickable(driver, By.XPATH, turn_on_notifications_not_now_xpath, timeout=7)  # Tăng timeout
                    if turn_on_notifications_not_now_button:
                        print(f"[DEBUG] Đã click nút 'Not Now' (thông báo) cho {username}.")
                        random_delay(1, 2)  # Chờ một chút sau khi click
                except Exception as e:
                    print(f"[DEBUG] Không tìm thấy hoặc không thể click nút 'Not Now' (thông báo) cho {username}: {e}")

                # Đợi một chút để xem có CAPTCHA không
                random_delay(2, 4)

                # Kiểm tra và xử lý reCAPTCHA/hCaptcha nếu có
                try:
                    # Chờ cho reCAPTCHA frame xuất hiện (nếu có)
                    recaptcha_frame = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='recaptcha']"))
                    )
                    print(f"[DEBUG] Phát hiện reCAPTCHA cho tài khoản {username}")

                    # Gọi CaptchaHandler để giải captcha
                    if not self.captcha_handler.handle_recaptcha(driver, username):
                        print("[ERROR] Không thể giải captcha")
                        login_status = "Lỗi Captcha"
                        proxy_status = "Lỗi không xác định"
                        return login_status, proxy_status
                    else:
                        print(f"[DEBUG] Đã xử lý reCAPTCHA thành công cho tài khoản {username}.")
                        # Sau khi giải captcha, driver có thể đã chuyển trang hoặc cần chờ thêm
                        # Đợi cho các trường đăng nhập xuất hiện trở lại
                        if not wait_for_element(driver, By.NAME, "username"):
                            print("[ERROR] Không thể tìm thấy ô nhập username sau khi giải captcha")
                            login_status = "Không tìm thấy username input sau Captcha"
                            proxy_status = "Lỗi không xác định"
                            return login_status, proxy_status

                except TimeoutException:
                    print(f"[DEBUG] Không tìm thấy reCAPTCHA cho tài khoản {username}.")
                except Exception as e:
                    print(f"[ERROR] Lỗi không xác định khi xử lý reCAPTCHA cho {username}: {e}")
                    login_status = "Lỗi không xác định Captcha"
                    proxy_status = "Lỗi không xác định"
                    return login_status, proxy_status

                # Sau khi click nút đăng nhập
                # Đợi chuyển hướng hoặc xuất hiện biểu tượng Home
                login_success_flag = False
                try:
                    # Sau khi click đăng nhập, kiểm tra cực nhanh sự xuất hiện của avatar profile (vòng tròn góc phải)
                    import random
                    def fast_find_avatar(driver, timeout=1.2):
                        import time
                        start = time.time()
                        avatar_selectors = [
                            # 1. Avatar ở góc phải dưới (menu profile)
                            "//span[@data-testid='user-avatar']",
                            "//div[@role='button']//span[@data-testid='user-avatar']",
                            # 2. Avatar ở header profile
                            "//header//img[contains(@alt, 'profile') or contains(@src, 'profile')]",
                            # 3. Avatar mặc định (có thể là svg hoặc img không alt)
                            "//img[contains(@src, 's150x150')]",
                            "//img[contains(@src, 'default_profile')]",
                            # 4. Avatar có border (thường là div có border-radius)
                            "//div[contains(@style, 'border-radius')]//img",
                            # 5. Avatar trong menu (mobile/desktop)
                            "//nav//img",
                            # 6. Avatar fallback: bất kỳ img nào trong header
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

                    avatar_btn = fast_find_avatar(driver, timeout=1.2)
                    if not avatar_btn:
                        # Thử click menu profile (nếu có) rồi thử lại
                        try:
                            menu_btn = driver.find_element(By.XPATH, "//div[@role='button' and @tabindex='0']")
                            if menu_btn.is_displayed():
                                driver.execute_script("arguments[0].click();", menu_btn)
                                print("[DEBUG] Đã click menu profile để lộ avatar.")
                                avatar_btn = fast_find_avatar(driver, timeout=0.7)
                        except Exception:
                            pass
                    if not avatar_btn:
                        # Thử reload lại trang chủ 1 lần rồi thử lại
                        driver.get("https://www.instagram.com/")
                        self.close_popups(driver)
                        avatar_btn = fast_find_avatar(driver, timeout=1.2)
                    if not avatar_btn:
                        print("[ERROR] Không tìm thấy avatar profile sau đăng nhập (tối ưu selector).")
                        driver.quit()
                        return "Không xác nhận đăng nhập", "Lỗi không xác định"
                    # Click avatar
                    try:
                        driver.execute_script("arguments[0].click();", avatar_btn)
                        print("[DEBUG] Đã click vào avatar profile (tối ưu selector).")
                    except Exception as e:
                        print(f"[ERROR] Không thể click avatar: {e}")
                        driver.quit()
                        return "Lỗi click avatar", "Lỗi không xác định"
                    # Chờ profile load (URL đổi hoặc header xuất hiện)
                    import re
                    profile_loaded = False
                    for _ in range(12):  # 1.2s, mỗi lần 0.1s
                        url = driver.current_url
                        if re.search(r"instagram\\.com/[^/?#]+/?$", url):
                            profile_loaded = True
                            break
                        try:
                            header = driver.find_element(By.XPATH, "//header//h2 | //header//div//h2")
                            if header.is_displayed():
                                profile_loaded = True
                                break
                        except Exception:
                            pass
                        import time; time.sleep(0.1)
                    if not profile_loaded:
                        print("[ERROR] Không load được profile sau khi click avatar (tối ưu selector).")
                        driver.quit()
                        return "Không xác nhận được profile", "Lỗi không xác định"
                    # Lấy username từ URL hoặc header
                    profile_username = None
                    url = driver.current_url
                    match = re.search(r"instagram\\.com/([^/?#]+)/?$", url)
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
                    # So sánh username (không try lồng nhau)
                    if profile_username and profile_username.lower() == username.lower():
                        print("[INFO] Đăng nhập thành công, username khớp!")
                        login_status = "Đã đăng nhập"
                        proxy_status = "OK"
                        account["status"] = "Đã đăng nhập"
                        account["last_action"] = "Đăng nhập"
                        return login_status, proxy_status
                    else:
                        print("[ERROR] Username trên profile không khớp hoặc không lấy được!")
                        login_status = "Không xác nhận được profile"
                        proxy_status = "Lỗi không xác định"
                        account["last_action"] = "Không xác nhận profile"
                        return login_status, proxy_status
                except Exception as e:
                    login_status = "Lỗi không xác định"
                return login_status, proxy_status
            finally:
                if driver:
                    try:
                        driver.quit()
                        print(f"[DEBUG] Đã đóng trình duyệt cho {username}")
                    except Exception as e:
                        print(f"[WARN] Lỗi khi đóng driver: {e}")

        # Thực hiện đăng nhập với logic thử lại
        return retry_operation(_perform_login, max_retries=max_retries, retry_delay=retry_delay)

    def close_all_drivers(self):
        for driver in self.active_drivers:
            try:
                driver.quit()
            except Exception as e:
                print(f"[WARN] Lỗi khi đóng trình duyệt: {e}")
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
        # Kiểm tra xem self.folder_map có được khởi tạo không
        if not hasattr(self, 'folder_map') or not self.folder_map:
            self.folder_map = self.load_folder_map()

        # Thêm các thư mục duy nhất từ folder_map vào combobox, bỏ qua _FOLDER_SET_ và các giá trị không phải str
        unique_folders = sorted(list(set(
            v for k, v in self.folder_map.items()
            if k != "_FOLDER_SET_" and isinstance(v, str) and v != "Tổng"
        )))
        for folder_name in unique_folders:
            self.category_combo.addItem(folder_name)
        print(f"[DEBUG] Đã tải danh sách thư mục vào combobox: {list(self.folder_map.keys())}")

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
        import time
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
                    time.sleep(0.2)
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