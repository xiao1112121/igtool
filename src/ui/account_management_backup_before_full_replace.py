import os
import tempfile
import shutil
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView, QSizePolicy, QApplication,
                            QMenu, QSpinBox, QFrame, QFileDialog, QMessageBox,
                             QInputDialog, QCheckBox, QStyledItemDelegate, QProgressDialog, QComboBox, QLabel, QLineEdit)
from PySide6.QtCore import Qt, QSize, QPoint, Signal, QModelIndex, QRect, QEvent
from PySide6.QtGui import QAction, QGuiApplication, QColor, QPainter, QPen, QIcon
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from concurrent.futures import ThreadPoolExecutor, as_completed
import undetected_chromedriver as uc
import time
import json
import re
from .folder_manager import FolderManagerDialog
from PySide6.QtWidgets import QStyle
import random # Import random

class CheckboxDelegate(QStyledItemDelegate):
    # Sử dụng một UserRole tùy chỉnh để tránh xung đột với Qt.CheckStateRole mặc định
    CheckboxStateRole = Qt.UserRole + 1
    checkbox_clicked = Signal(int, bool) # Thêm tín hiệu mới: row, new_state

    def paint(self, painter: QPainter, option, index: QModelIndex):
        super().paint(painter, option, index) # Gọi phương thức paint của lớp cha để vẽ nền mặc định (bao gồm cả màu chọn)
        # Lấy trạng thái checkbox từ model bằng UserRole tùy chỉnh
        check_state_data = index.data(self.CheckboxStateRole)
        is_checked = bool(check_state_data) # Convert to boolean

        # Tính toán vị trí và kích thước cho checkbox 15x15px, căn giữa trong ô
        checkbox_size = 15
        rect = option.rect
        x = rect.x() + (rect.width() - checkbox_size) // 2
        y = rect.y() + (rect.height() - checkbox_size) // 2
        checkbox_rect = QRect(x, y, checkbox_size, checkbox_size)

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        # Vẽ nền và viền của checkbox
        if is_checked:
            painter.setBrush(QColor("#1976D2")) # Màu xanh lam khi chọn
            painter.setPen(QColor("#1976D2"))
        else:
            painter.setBrush(Qt.white) # Nền trắng khi không chọn
            painter.setPen(QColor("#CCCCCC")) # Viền xám khi không chọn
        
        painter.drawRoundedRect(checkbox_rect, 2, 2) # Vẽ hình vuông bo góc

        # Vẽ dấu tích nếu đã chọn
        if is_checked:
            # Vẽ dấu tích trắng đơn giản
            painter.setPen(QPen(Qt.white, 2)) # Bút màu trắng, độ dày 2
            # Đường chéo thứ nhất của dấu tích (từ dưới lên)
            painter.drawLine(x + 3, y + 7, x + 6, y + 10)
            # Đường chéo thứ hai của dấu tích (từ điểm giữa lên trên)
            painter.drawLine(x + 6, y + 10, x + 12, y + 4)
            
        painter.restore()

    def editorEvent(self, event, model, option, index: QModelIndex):
        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            # Lấy trạng thái hiện tại từ UserRole tùy chỉnh
            current_state = index.data(self.CheckboxStateRole)
            new_state = not bool(current_state) # Đảo ngược trạng thái
            
            # Cập nhật trạng thái trong model bằng UserRole tùy chỉnh
            model.setData(index, new_state, self.CheckboxStateRole)
            
            # Phát tín hiệu khi checkbox được click
            self.checkbox_clicked.emit(index.row(), new_state)
            return True # Đã xử lý sự kiện
        return False # Quan trọng: Trả về False để các sự kiện không phải click được xử lý mặc định

class CheckableHeaderView(QHeaderView):
    toggleAllCheckboxes = Signal(bool) # Tín hiệu để thông báo khi checkbox trong header được toggle

    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self._checked = False # Trạng thái của checkbox trong header
        self.setSectionsClickable(True)

    def paintSection(self, painter, rect, logicalIndex):
        if logicalIndex == 0:  # Cột đầu tiên là cột checkbox
            checkbox_size = 15 # Kích thước của checkbox
            # Căn giữa checkbox trong ô tiêu đề
            x = rect.x() + (rect.width() - checkbox_size) // 2
            y = rect.y() + (rect.height() - checkbox_size) // 2
            checkbox_rect = QRect(x, y, checkbox_size, checkbox_size)

            painter.save()
            painter.setRenderHint(QPainter.Antialiasing)

            # Vẽ nền và viền của checkbox
            if self._checked:
                painter.setBrush(QColor("#1976D2")) # Màu xanh lam khi chọn
                painter.setPen(QColor("#1976D2"))
            else:
                painter.setBrush(Qt.white) # Nền trắng khi không chọn
                painter.setPen(QColor("#CCCCCC")) # Viền xám khi không chọn
            
            painter.drawRoundedRect(checkbox_rect, 2, 2) # Vẽ hình vuông bo góc

            # Vẽ dấu tích nếu đã chọn
            if self._checked:
                painter.setPen(QPen(Qt.white, 2)) # Bút màu trắng, độ dày 2
                painter.drawLine(x + 3, y + 7, x + 6, y + 10)
                painter.drawLine(x + 6, y + 10, x + 12, y + 4)
                
            painter.restore()
            # KHÔNG gọi super().paintSection ở đây cho cột checkbox
        else:
            # Gọi phương thức gốc để vẽ phần còn lại của header cho các cột khác
            super().paintSection(painter, rect, logicalIndex)

    def mousePressEvent(self, event):
        if self.logicalIndexAt(event.pos()) == 0 and event.button() == Qt.LeftButton: # Chỉ xử lý click trên cột đầu tiên
            self._checked = not self._checked
            self.toggleAllCheckboxes.emit(self._checked)
            self.viewport().update() # Cập nhật lại giao diện header để hiển thị trạng thái checkbox mới
            event.accept() # Chấp nhận sự kiện để ngăn xử lý mặc định
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
        "en-US,en;q=0.9", # English (United States), English
        "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7", # Vietnamese, English
        "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7", # French, English
        "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7", # German, English
        "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7"  # Japanese, English
    ]

    PROXY_USAGE_THRESHOLD = 5 # Ngưỡng sử dụng proxy trước khi xoay vòng

    def __init__(self, proxy_tab_instance=None, parent=None):
        super().__init__(parent)
        self.proxy_tab = proxy_tab_instance  # Reference to ProxyManagementTab instance
        self.accounts_file = "accounts.json"
        self.folder_map_file = "folder_map.json" # File to store folder mappings
        self.accounts = self.load_accounts()
        self.folder_map = self.load_folder_map() # Load folder map
        self.active_drivers = []
        self.stealth_mode_enabled = False # Khởi tạo cờ chế độ stealth
        self.proxies = self.load_proxies() # Tải danh sách proxy
        self.init_ui()
        self.update_account_table()
        
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

        # btn_login_selected = QPushButton("Đăng nhập tài khoản đã chọn")
        # btn_login_selected.clicked.connect(self.login_selected_accounts)
        # self.sidebar_layout.addWidget(btn_login_selected)

        # btn_get_info_selected = QPushButton("Lấy thông tin tài khoản đã chọn")
        # btn_get_info_selected.clicked.connect(self.get_info_selected_accounts)
        # self.sidebar_layout.addWidget(btn_get_info_selected)

        # btn_select_all = QPushButton("Chọn tất cả")
        # btn_select_all.clicked.connect(self.select_all_accounts)
        # self.sidebar_layout.addWidget(btn_select_all)

        # btn_deselect_all = QPushButton("Bỏ chọn tất cả")
        # btn_deselect_all.clicked.connect(self.deselect_all_accounts)
        # self.sidebar_layout.addWidget(btn_deselect_all)

        btn_add_folder = QPushButton("Thêm thư mục")
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
        toolbar_frame.setStyleSheet("QFrame { padding-top: 6px; padding-bottom: 6px; }")
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setSpacing(8)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)

        # ComboBox for Category
        self.category_combo = QComboBox()
        self.category_combo.addItem("Tất cả")
        self.load_folder_list_to_combo() # Load folders into combobox
        self.category_combo.currentIndexChanged.connect(self.on_folder_changed)
        self.category_combo.setFixedSize(200, 35)  # Kích thước 200x35px
        toolbar_layout.addWidget(self.category_combo)

        # Nút LOAD
        btn_load = QPushButton("LOAD")
        btn_load.setFixedSize(80, 35) # Đặt kích thước cố định cho nút LOAD là 80x35px để hiển thị đầy đủ chữ
        btn_load.setProperty("role", "main") # Sử dụng style main button
        btn_load.setProperty("color", "yellow") # Sử dụng màu vàng
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
        self.search_input.setFixedWidth(150) # Đặt chiều rộng cố định
        self.search_input.setFixedHeight(35)  # Giữ nguyên chiều cao
        toolbar_layout.addWidget(self.search_input)

        # Layout for buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)  # Space between buttons

        btn_search = QPushButton("🔍") # Đổi tên nút và đặt biểu tượng kính lúp trực tiếp
        btn_search.clicked.connect(lambda: self.filter_accounts(self.search_input.text())) # Kết nối với filter_accounts
        btn_search.setFixedSize(50, 35)  # Đặt kích thước cố định là 50x35px
        btn_search.setProperty("role", "main") # Sử dụng style main button
        btn_search.setProperty("color", "blue") # Đổi màu xanh da trời
        button_layout.addWidget(btn_search)
        
        toolbar_layout.addLayout(button_layout)
        
        right_layout.addWidget(toolbar_frame)

        # Account table
        self.account_table = QTableWidget()
        self.account_table.setColumnCount(10)  # Tăng lên 10 cột
        self.account_table.setHorizontalHeaderLabels([
            "", "STT", "Tên đăng nhập", "Mật khẩu", "Trạng thái", 
            "Proxy", "Trạng thái Proxy", "Follower", "Following", "Hành động cuối"
        ])
        
        # Thiết lập delegate cho cột "Chọn"
        self.checkbox_delegate = CheckboxDelegate(self)
        self.account_table.setItemDelegateForColumn(0, self.checkbox_delegate)
        # Kết nối tín hiệu checkbox_clicked từ delegate
        self.checkbox_delegate.checkbox_clicked.connect(self.on_checkbox_clicked)

        # Thay thế QHeaderView mặc định bằng CheckableHeaderView
        self.header_checkbox = CheckableHeaderView(Qt.Horizontal, self.account_table)
        self.account_table.setHorizontalHeader(self.header_checkbox)
        header = self.header_checkbox # Gán lại biến header để các dòng code sau vẫn sử dụng được

        header.setSectionResizeMode(0, QHeaderView.Fixed) # Cột "Chọn"
        self.account_table.setColumnWidth(0, 29)
        header.setSectionResizeMode(1, QHeaderView.Fixed) # Cột "STT"
        self.account_table.setColumnWidth(1, 29) # Đặt chiều rộng cột STT thành 29px
        header.setSectionResizeMode(2, QHeaderView.Fixed) # Cột "Tên đăng nhập" - Chuyển về Fixed
        self.account_table.setColumnWidth(2, 150) # Đặt chiều rộng cố định
        header.setSectionResizeMode(3, QHeaderView.Fixed) # Cột "Mật khẩu" - Chuyển về Fixed
        self.account_table.setColumnWidth(3, 150) # Đặt chiều rộng cố định
        header.setSectionResizeMode(4, QHeaderView.Fixed) # Cột "Trạng thái"
        self.account_table.setColumnWidth(4, 120) # Giữ nguyên chiều rộng
        header.setSectionResizeMode(5, QHeaderView.Fixed) # Cột "Proxy" - Chuyển về Fixed
        self.account_table.setColumnWidth(5, 200) # Đặt chiều rộng cố định
        header.setSectionResizeMode(6, QHeaderView.Fixed) # Cột "Trạng thái Proxy"
        self.account_table.setColumnWidth(6, 120) # Đặt chiều rộng cố định
        header.setSectionResizeMode(7, QHeaderView.Fixed) # Cột "Follower"
        self.account_table.setColumnWidth(7, 79)
        header.setSectionResizeMode(8, QHeaderView.Fixed) # Cột "Following"
        self.account_table.setColumnWidth(8, 79)
        header.setSectionResizeMode(9, QHeaderView.Stretch) # Cột "Hành động cuối" - Giữ nguyên Stretch
        self.account_table.verticalHeader().setDefaultSectionSize(29) # Thiết lập chiều cao hàng nội dung thành 29px

        # Thiết lập căn lề cho các tiêu đề cột
        self.account_table.horizontalHeader().setDefaultAlignment(Qt.AlignHCenter | Qt.AlignVCenter)

        self.account_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.account_table.setEditTriggers(QTableWidget.NoEditTriggers)  # Disable editing
        self.account_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.account_table.customContextMenuRequested.connect(self.show_context_menu)
        self.account_table.itemChanged.connect(self.handle_item_changed) # Connect itemChanged signal
        self.account_table.verticalHeader().setVisible(False) # Ẩn cột số thứ tự bên trái
        self.account_table.itemDoubleClicked.connect(self.on_table_item_double_clicked) # Connect double click signal

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
                        "fullname": "", # NEW: Thêm trường Họ tên
                        "proxy": proxy,
                        "status": "Chưa đăng nhập",
                        "gender": "-", # Thêm cột giới tính
                        "followers": "",
                        "following": "",
                        "last_action": "", # Thêm cột hành động cuối
                        "proxy_status": "Chưa kiểm tra" # Khởi tạo trạng thái proxy
                    }
                    self.accounts.append(new_account)
                    self.save_accounts()
                    self.update_account_table()
                    QMessageBox.information(self, "Thêm tài khoản", "Tài khoản đã được thêm thành công.")

    def update_account_table(self, accounts_to_display=None):
        if accounts_to_display is None:
            accounts_to_display = self.accounts

        # Cập nhật thống kê
        total_count = len(accounts_to_display)
        live_count = sum(1 for acc in accounts_to_display if acc.get("status") == "Live" or acc.get("status") == "Đã đăng nhập")
        die_count = sum(1 for acc in accounts_to_display if acc.get("status") == "Die") # Giả định có trạng thái "Die"

        self.total_accounts_label.setText(f"Tổng: {total_count}")
        self.live_accounts_label.setText(f"Live: {live_count}")
        self.die_accounts_label.setText(f"Die: {die_count}")

        self.account_table.blockSignals(True)  # Block signals to prevent itemChanged from firing
        self.account_table.setRowCount(len(accounts_to_display))
        for row_idx, account in enumerate(accounts_to_display):
            # Cột "Chọn" - Sử dụng QTableWidgetItem và delegate
            item_checkbox = QTableWidgetItem()
            # Đặt cờ cho phép tương tác với checkbox, bao gồm cả khả năng tick/bỏ tick bởi người dùng và khả năng chọn
            item_checkbox.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable)
            # Đặt trạng thái ban đầu của checkbox vào UserRole tùy chỉnh
            item_checkbox.setData(CheckboxDelegate.CheckboxStateRole, account.get("selected", False))
            self.account_table.setItem(row_idx, 0, item_checkbox) # Thiết lập item cho cột 0

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
            password_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter) # Căn lề trái cho mật khẩu
            self.account_table.setItem(row_idx, 3, password_item)

            # Trạng thái
            status_item = QTableWidgetItem(account.get("status", "Chưa đăng nhập"))
            status_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            if account.get("status") == "Live" or account.get("status") == "Đã đăng nhập":
                status_item.setForeground(QColor("#388E3C")) # Màu xanh đậm
            else:
                status_item.setForeground(QColor("#D32F2F")) # Màu đỏ
            self.account_table.setItem(row_idx, 4, status_item)

            # Proxy
            proxy_text = account.get("proxy", "")
            proxy_item = QTableWidgetItem(proxy_text)
            proxy_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            proxy_item.setToolTip(proxy_text) # Tooltip đầy đủ
            self.account_table.setItem(row_idx, 5, proxy_item)

            # Trạng thái Proxy
            proxy_status_item = QTableWidgetItem(account.get("proxy_status", "Chưa kiểm tra"))
            proxy_status_item.setTextAlignment(Qt.AlignCenter)
            # Màu sắc dựa trên trạng thái proxy
            if account.get("proxy_status") == "OK":
                proxy_status_item.setForeground(QColor("#4CAF50")) # Green
            elif account.get("proxy_status") == "Risky":
                proxy_status_item.setForeground(QColor("#FFC107")) # Amber/Orange
            elif account.get("proxy_status") == "Die":
                proxy_status_item.setForeground(QColor("#D32F2F")) # Red
            else:
                proxy_status_item.setForeground(QColor("#9E9E9E")) # Grey
            self.account_table.setItem(row_idx, 6, proxy_status_item)

            # Follower
            follower_text = account.get("followers", "")
            display_follower = "=0" if not follower_text else follower_text
            follower_item = QTableWidgetItem(display_follower)
            follower_item.setTextAlignment(Qt.AlignCenter)
            self.account_table.setItem(row_idx, 7, follower_item)

            # Following
            following_text = account.get("following", "")
            display_following = "=0" if not following_text else following_text
            following_item = QTableWidgetItem(display_following)
            following_item.setTextAlignment(Qt.AlignCenter)
            self.account_table.setItem(row_idx, 8, following_item)

            # Hành động cuối
            last_action_item = QTableWidgetItem(account.get("last_action", ""))
            last_action_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.account_table.setItem(row_idx, 9, last_action_item)

            # Set editable flags for specific columns if not currently logged in
            # Chỉ cho phép chỉnh sửa Tên đăng nhập, Mật khẩu, Proxy nếu trạng thái không phải "Live" hoặc "Đã đăng nhập"
            if account.get("status") != "Live" and account.get("status") != "Đã đăng nhập":
                for col in [2, 3, 5]:  # Tên đăng nhập, Mật khẩu, Proxy
                    item = self.account_table.item(row_idx, col)
                    if item:
                        item.setFlags(item.flags() | Qt.ItemIsEditable)
            else:
                for col in [2, 3, 5]:  # Tên đăng nhập, Mật khẩu, Proxy
                    item = self.account_table.item(row_idx, col)
                    if item:
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        self.account_table.blockSignals(False)  # Unblock signals

    def on_checkbox_clicked(self, row, new_state):
        # Hàm này được kết nối từ delegate để xử lý khi trạng thái checkbox thay đổi
        print(f"DEBUG: Checkbox state for row {row} changed to {new_state}")
        # Xử lý thay đổi trạng thái checkbox
        if row >= 0 and row < len(self.accounts):
                for account in self.accounts:
                if account.get("username") == self.account_table.item(row, 2).text():
                    account["selected"] = new_state
                        break
        self.save_accounts()
        self.update_account_table()
            
    def handle_item_changed(self, item):
        print(f"DEBUG: handle_item_changed called for column {item.column()}")
        # Slot này được gọi khi một item trong bảng thay đổi.
        # Xử lý chỉnh sửa thủ công Tên đăng nhập, Mật khẩu, Proxy
        if item.column() in [2, 3, 5]: # Tên đăng nhập, Mật khẩu, Proxy
            row = item.row()
            # Lấy username từ bảng để đảm bảo cập nhật đúng tài khoản
            username_in_table = self.account_table.item(row, 2).text()
            for account in self.accounts:
                if account["username"] == username_in_table:
                    if item.column() == 2:
                        account["username"] = item.text()
                    elif item.column() == 3:
                        account["password"] = item.text()
                    elif item.column() == 5:
                        account["proxy"] = item.text()
                    break
            self.save_accounts() # Lưu thay đổi vào accounts.json

    def select_all_accounts(self):
        for account in self.accounts:
            account["selected"] = True
        self.update_account_table()

    def deselect_all_accounts(self):
        # Bỏ chọn tất cả tài khoản đã được tick chọn (không cần bôi đen)
        deselected_count = 0
        for row_idx in range(self.account_table.rowCount()):
            item = self.account_table.item(row_idx, 0) # Cột checkbox
            if item and item.checkState() == Qt.Checked:
                self.account_table.model().setData(item.index(), False, CheckboxDelegate.CheckboxStateRole)
                if row_idx < len(self.accounts):
                    self.accounts[row_idx]["selected"] = False
                deselected_count += 1
        self.save_accounts()
        QMessageBox.information(self, "Bỏ chọn tất cả", f"Đã bỏ chọn tất cả {deselected_count} tài khoản.")
        print(f"[DEBUG] Đã bỏ chọn tất cả {deselected_count} tài khoản.")

    def filter_accounts(self, text):
        filtered_accounts = []
        current_folder = self.category_combo.currentText()

        for account in self.accounts:
            username = account.get("username", "").lower()
            proxy = account.get("proxy", "").lower()
            
            # Kiểm tra theo thư mục
            in_selected_folder = True
            if current_folder != "Tất cả":
                account_folder = self.folder_map.get(username, "Tổng")
                if account_folder != current_folder:
                    in_selected_folder = False
            
            # Kiểm tra theo tìm kiếm
            matches_search = False
            if not text or text.lower() in username or text.lower() in proxy:
                matches_search = True

            if in_selected_folder and matches_search:
                filtered_accounts.append(account)
        
        self.update_account_table(filtered_accounts)

    def get_window_positions(self, num_windows):
        screen = QGuiApplication.primaryScreen().geometry()
        screen_width = screen.width()
        screen_height = screen.height()

        window_width = 465
        window_height = 488

        # Calculate columns and rows for 2 rows, max 5 windows per row
        max_cols = 5
        rows = 2
        
        positions = []
        for i in range(num_windows):
            col = i % max_cols
            row = i // max_cols
            
            # Ensure we don't go beyond 2 rows
            if row >= rows:
                break

            x = col * window_width
            y = row * window_height

            # Prevent windows from going off-screen (basic check)
            if x + window_width > screen_width or y + window_height > screen_height:
                print(f"[WARN] Cửa sổ {i+1} có thể bị tràn màn hình. Điều chỉnh kích thước cửa sổ hoặc số lượng tài khoản.")
                # Simple adjustment: try to place at the top-left if it overflows
                if x + window_width > screen_width:
                    x = 0
                if y + window_height > screen_height:
                    y = 0

            positions.append(QPoint(x, y))
        return positions


    def login_selected_accounts(self):
        # Implementation of login_selected_accounts method
        pass

    def get_info_selected_accounts(self):
        QMessageBox.information(self, "Chức năng", "Lấy thông tin tài khoản đang được phát triển.")
        print("[DEBUG] Chức năng get_info_selected_accounts được gọi.")

    def open_browser_for_selected(self):
        QMessageBox.information(self, "Chức năng", "Mở trình duyệt đang được phát triển.")
        print("[DEBUG] Chức năng open_browser_for_selected được gọi.")

    def logout_selected_accounts(self):
        QMessageBox.information(self, "Chức năng", "Đăng xuất tài khoản đang được phát triển.")
        print("[DEBUG] Chức năng logout_selected_accounts được gọi.")

    def delete_selected_accounts(self):
        QMessageBox.information(self, "Chức năng", "Xóa tài khoản đang được phát triển.")
        print("[DEBUG] Chức năng delete_selected_accounts được gọi.")

    def select_selected_accounts(self):
        # Chọn các tài khoản đang được bôi đen (highlighted)
        selected_rows = self.account_table.selectionModel().selectedRows()
        for index in selected_rows:
            row = index.row()
            if row < len(self.accounts):
                # Lấy QTableWidgetItem của cột checkbox
                item_checkbox = self.account_table.item(row, 0)
                if item_checkbox and item_checkbox.checkState() == Qt.Unchecked:
                    item_checkbox.setCheckState(Qt.Checked)
                    self.accounts[row]["selected"] = True
                            self.save_accounts()
        QMessageBox.information(self, "Chọn tài khoản", f"Đã chọn {len(selected_rows)} tài khoản được bôi đen.")
        print(f"[DEBUG] Đã chọn {len(selected_rows)} tài khoản được bôi đen.")

    def deselect_selected_accounts(self):
        # Bỏ chọn các tài khoản đang được bôi đen VÀ đã được tick chọn
        selected_rows = self.account_table.selectionModel().selectedRows()
        deselected_count = 0
        for index in selected_rows:
            row = index.row()
            if row < len(self.accounts):
                item_checkbox = self.account_table.item(row, 0)
                if item_checkbox and item_checkbox.checkState() == Qt.Checked:
                    item_checkbox.setCheckState(Qt.Unchecked)
                    self.accounts[row]["selected"] = False
                    deselected_count += 1
                    self.save_accounts()
        QMessageBox.information(self, "Bỏ chọn tài khoản", f"Đã bỏ chọn {deselected_count} tài khoản được bôi đen.")
        print(f"[DEBUG] Đã bỏ chọn {deselected_count} tài khoản được bôi đen.")
    
    def add_selected_to_folder(self, folder_name):
        QMessageBox.information(self, "Chức năng", f"Thêm vào thư mục '{folder_name}' đang được phát triển.")
        print(f"[DEBUG] Chức năng add_selected_to_folder được gọi với folder: {folder_name}")

    def remove_selected_from_folder(self, folder_name):
        QMessageBox.information(self, "Chức năng", f"Xóa khỏi thư mục '{folder_name}' đang được phát triển.")
        print(f"[DEBUG] Chức năng remove_selected_from_folder được gọi với folder: {folder_name}")

    def delete_selected_folder(self):
        QMessageBox.information(self, "Chức năng", "Xóa thư mục đang được phát triển.")
        print("[DEBUG] Chức năng delete_selected_folder được gọi.")

    def set_account_status_selected(self, status):
        QMessageBox.information(self, "Chức năng", f"Chuyển trạng thái tài khoản về '{status}' đang được phát triển.")
        print(f"[DEBUG] Chức năng set_account_status_selected được gọi với status: {status}")

    def update_selected_proxy_info(self):
        QMessageBox.information(self, "Chức năng", "Cập nhật thông tin Proxy đang được phát triển.")
        print("[DEBUG] Chức năng update_selected_proxy_info được gọi.")

    def open_selected_user_data_folder(self):
        QMessageBox.information(self, "Chức năng", "Mở thư mục UserData đang được phát triển.")
        print("[DEBUG] Chức năng open_selected_user_data_folder được gọi.")

    def show_context_menu(self, position):
        menu = QMenu(self)

        # Group 1: THAO TÁC
        action_group_1 = menu.addMenu("THAO TÁC")
        action_login = action_group_1.addAction(QIcon(), "Đăng nhập tài khoản đã chọn")
        action_get_info = action_group_1.addAction(QIcon(), "Lấy thông tin tài khoản đã chọn")
        action_open_browser = action_group_1.addAction(QIcon(), "Mở trình duyệt")
        action_logout = action_group_1.addAction(QIcon(), "Đăng xuất")
        action_delete = action_group_1.addAction(QIcon(), "Xóa tài khoản")

        # Group 2: CHỌN / BỎ CHỌN
        action_group_2 = menu.addMenu("CHỌN / BỎ CHỌN")
        action_select_highlighted = action_group_2.addAction(QIcon(), "CHỌN (Tài khoản đã bôi đen)")
        action_deselect_highlighted = action_group_2.addAction(QIcon(), "BỎ CHỌN (Tài khoản đã bôi đen)")
        action_deselect_all = action_group_2.addAction(QIcon(), "BỎ CHỌN TẤT CẢ")

        # Group 3: QUẢN LÝ THƯ MỤC
        action_group_3 = menu.addMenu("QUẢN LÝ THƯ MỤC")
        # Sub-menu "THÊM VÀO THƯ MỤC"
        add_to_folder_menu = action_group_3.addMenu("THÊM VÀO THƯ MỤC")
        # Sub-menu "XÓA KHỎI THƯ MỤC"
        remove_from_folder_menu = action_group_3.addMenu("XÓA KHỎI THƯ MỤC")
        action_delete_folder = action_group_3.addAction(QIcon(), "Xóa thư mục")

        # Dynamically add folder actions to sub-menus
        selected_rows = self.account_table.selectionModel().selectedRows()
        if selected_rows:
            # Lấy danh sách thư mục từ self.folder_map (là một dict)
            folders = list(self.folder_map.keys())
            if folders:
                for folder_name in folders:
                    # Tạo action cho từng thư mục trong menu "THÊM VÀO THƯ MỤC"
                    action_add_to_folder = add_to_folder_menu.addAction(folder_name)
                    action_add_to_folder.triggered.connect(lambda checked, f=folder_name: self.add_selected_to_folder(f))
                    
                    # Tạo action cho từng thư mục trong thư mục "XÓA KHỎI THƯ MỤC"
                    action_remove_from_folder = remove_from_folder_menu.addAction(folder_name)
                    action_remove_from_folder.triggered.connect(lambda checked, f=folder_name: self.remove_selected_from_folder(f))
            else:
                add_to_folder_menu.addAction("Không có thư mục").setEnabled(False)
                remove_from_folder_menu.addAction("Không có thư mục").setEnabled(False)
        else:
            add_to_folder_menu.addAction("Chọn tài khoản trước").setEnabled(False)
            remove_from_folder_menu.addAction("Chọn tài khoản trước").setEnabled(False)


        # Group 4: CẬP NHẬT TRẠNG THÁI
        action_group_4 = menu.addMenu("CẬP NHẬT TRẠNG THÁI")
        action_set_live = action_group_4.addAction(QIcon(), "Chuyển về Live")
        action_set_checkpoint = action_group_4.addAction(QIcon(), "Chuyển về Checkpoint")
        action_set_die = action_group_4.addAction(QIcon(), "Chuyển về Die")
        action_set_not_logged_in = action_group_4.addAction(QIcon(), "Chuyển về Chưa đăng nhập")

        # Group 5: THÔNG TIN KHÁC
        action_group_5 = menu.addMenu("THÔNG TIN KHÁC")
        action_update_proxy_info = action_group_5.addAction(QIcon(), "Cập nhật thông tin Proxy")
        action_open_user_data_folder = action_group_5.addAction(QIcon(), "Mở thư mục UserData")

        # Connect actions to placeholder methods
        action_login.triggered.connect(self.login_selected_accounts)
        action_get_info.triggered.connect(self.get_info_selected_accounts)
        action_open_browser.triggered.connect(self.open_browser_for_selected)
        action_logout.triggered.connect(self.logout_selected_accounts)
        action_delete.triggered.connect(self.delete_selected_accounts)
        action_select_highlighted.triggered.connect(self.select_selected_accounts)
        action_deselect_highlighted.triggered.connect(self.deselect_selected_accounts)
        action_deselect_all.triggered.connect(self.deselect_all_accounts) # Bỏ chọn tất cả
        action_delete_folder.triggered.connect(self.delete_selected_folder)
        action_set_live.triggered.connect(lambda: self.set_account_status_selected("Live"))
        action_set_checkpoint.triggered.connect(lambda: self.set_account_status_selected("Checkpoint"))
        action_set_die.triggered.connect(lambda: self.set_account_status_selected("Die"))
        action_set_not_logged_in.triggered.connect(lambda: self.set_account_status_selected("Chưa đăng nhập"))
        action_update_proxy_info.triggered.connect(self.update_selected_proxy_info)
        action_open_user_data_folder.triggered.connect(self.open_selected_user_data_folder)

        menu.exec(self.account_table.viewport().mapToGlobal(position))

    def on_table_item_double_clicked(self, index):
        # Implementation of on_table_item_double_clicked method
        selected_account = self.accounts[index.row()]
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
        for row_idx in range(self.account_table.rowCount()):
            item = self.account_table.item(row_idx, 0) # Cột checkbox
            if item:
                # Cập nhật trạng thái trong model bằng UserRole tùy chỉnh
                self.account_table.model().setData(item.index(), checked, CheckboxDelegate.CheckboxStateRole)
                # Cập nhật trạng thái 'selected' trong dữ liệu tài khoản
                if row_idx < len(self.accounts):
                    self.accounts[row_idx]["selected"] = checked
                self.save_accounts()

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
                        elif len(parts) == 2: # No auth proxy
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
            new_proxy_info["is_in_use"] = True # Đánh dấu là đang được sử dụng khi gán
            new_proxy_info["status"] = "Đang sử dụng" # Cập nhật trạng thái proxy trong danh sách toàn cầu
            account["proxy_status"] = "Đang chuyển đổi" # Đánh dấu trạng thái tài khoản đang chuyển đổi proxy
            print(f"[INFO] Đã gán proxy mới {account['proxy']} cho tài khoản {username}.")
        else:
            account["proxy_status"] = "Không có proxy khả dụng" # Nếu không tìm thấy proxy nào phù hợp
            print(f"[WARN] Không tìm thấy proxy khả dụng nào cho tài khoản {username}.")
        
        self.save_accounts() # Lưu thay đổi vào accounts.json

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
                time.sleep(5 * delay_multiplier) # Spend some time on the post
                driver.back() # Go back to home feed
                time.sleep(2 * delay_multiplier)
        except Exception as e:
            print(f"[WARN] Lỗi khi thực hiện warm-up: {e}")
        print("[DEBUG] Đã hoàn tất phiên warm-up.")
