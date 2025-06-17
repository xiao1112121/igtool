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

class DataScannerTab(QWidget):
    def __init__(self):
        super().__init__()
        self.config_data = [{} for _ in range(4)]  # Lưu cấu hình từng mục
        self.username_lists = [[], [], [], []]    # Lưu danh sách username từng mục
        self.scan_running = False
        self.scan_timer = None
        self.account_data = []
        self.result_data = []
        self.accounts = []  # Lưu toàn bộ tài khoản
        self.init_ui()
        
    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(12, 12, 12, 12)
        # Sidebar trái (15%)
        sidebar = QVBoxLayout()
        sidebar.setSpacing(10)
        self.menu_buttons = []
        menu_titles = [
            "Quét tài khoản theo dõi",
            "Quét bài viết tài khoản",
            "Quét chi tiết tài khoản",
            "Quét follow tài khoản"
        ]
        for i, title in enumerate(menu_titles):
            btn = QPushButton(title)
            btn.setCheckable(True)
            btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            btn.setStyleSheet("QPushButton {text-align: left; border: none; background: white;} QPushButton:checked {background: #e0e0e0;}")
            btn.clicked.connect(lambda checked, idx=i: self.switch_config(idx))
            btn.setProperty("sidebar", "true")
            self.menu_buttons.append(btn)
            sidebar.addWidget(btn)
        sidebar.addStretch()
        sidebar_widget = QWidget()
        sidebar_widget.setLayout(sidebar)
        sidebar_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        # Phần giữa (20%) - Cấu hình
        self.stacked_config = QStackedWidget()
        self.config_widgets = [self.create_config_widget(i) for i in range(4)]
        for w in self.config_widgets:
            self.stacked_config.addWidget(w)
        self.stacked_config.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        # Bảng phải (65%) - Bảng dữ liệu
        right_panel = QVBoxLayout()
        right_panel.setSpacing(12)
        # Bảng trên
        top_group = QGroupBox("Danh sách tài khoản")
        top_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        top_layout = QVBoxLayout(top_group)
        top_layout.setSpacing(8)
        top_layout.setContentsMargins(12, 18, 12, 12)
        self.stats_label = QLabel("Tổng số bài viết quét được: 0")
        self.stats_label.setFont(QFont("Segoe UI", 8))
        self.stats_label.setWordWrap(True)
        top_layout.addWidget(self.stats_label)
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        self.category_combo = QComboBox()
        self.load_folder_list_to_combo()
        self.category_combo.currentIndexChanged.connect(self.on_folder_changed)
        
        self.btn_load = QPushButton("Load")
        self.btn_start = QPushButton("Start")
        self.btn_stop = QPushButton("Stop")

        # Style cho các nút Load, Start, Stop
        load_button_style = """
        QPushButton {
            min-width: 40px;
            max-width: 40px;
            min-height: 35px;
            max-height: 35px;
            border: 1px solid #888;
            border-radius: 4px;
            color: white;
            background-color: #fdd835;
        }
        """
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
            background-color: #f44336;
        }
        """
        self.btn_load.setStyleSheet(load_button_style)
        self.btn_start.setStyleSheet(start_button_style)
        self.btn_stop.setStyleSheet(stop_button_style)
        
        self.btn_load.clicked.connect(self.load_accounts)
        self.btn_start.clicked.connect(self.start_scan)
        self.btn_stop.clicked.connect(self.stop_scan)
        
        toolbar.addWidget(self.category_combo)
        toolbar.addWidget(self.btn_load)
        toolbar.addWidget(self.btn_start)
        toolbar.addWidget(self.btn_stop)
        top_layout.addLayout(toolbar)
        self.account_table = QTableWidget()
        self.account_table.setColumnCount(5)
        self.account_table.setHorizontalHeaderLabels(["", "STT", "Username", "Trạng thái", "Thành công"])
        header1 = self.account_table.horizontalHeader()
        header1.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header1.resizeSection(0, 32)
        header1.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header1.resizeSection(1, 40)
        header1.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header1.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header1.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.account_table.verticalHeader().setVisible(False)
        header1.setStretchLastSection(True)
        self.account_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.account_table.verticalHeader().setDefaultSectionSize(32)
        self.account_table.horizontalHeader().setFixedHeight(40)
        # Đặt delegate checkbox giống tab Quản lý Tài khoản
        self.checkbox_delegate = CheckboxDelegate(self)
        self.account_table.setItemDelegateForColumn(0, self.checkbox_delegate)
        self.checkbox_delegate.checkbox_clicked.connect(self.on_checkbox_clicked)
        self.account_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        top_layout.addWidget(self.account_table)
        # Bảng dưới
        bottom_group = QGroupBox("Kết quả quét")
        bottom_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        bottom_layout = QVBoxLayout(bottom_group)
        bottom_layout.setSpacing(8)
        bottom_layout.setContentsMargins(12, 18, 12, 12)
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(5)
        self.result_table.setHorizontalHeaderLabels(["", "STT", "Tài khoản quét", "Tài khoản bị quét", "Username quét được"])
        header2 = self.result_table.horizontalHeader()
        header2.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header2.resizeSection(0, 32)
        header2.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header2.resizeSection(1, 40)
        header2.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header2.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header2.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.result_table.verticalHeader().setVisible(False)
        header2.setStretchLastSection(True)
        self.result_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.result_table.verticalHeader().setDefaultSectionSize(32)
        self.result_table.horizontalHeader().setFixedHeight(40)
        bottom_layout.addWidget(self.result_table)
        right_panel.addWidget(top_group, stretch=1)
        right_panel.addWidget(bottom_group, stretch=1)
        right_panel_widget = QWidget()
        right_panel_widget.setLayout(right_panel)
        right_panel_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # Thêm vào layout chính với tỷ lệ 15-20-65
        main_layout.addWidget(sidebar_widget, stretch=15)
        main_layout.addWidget(self.stacked_config, stretch=20)
        main_layout.addWidget(right_panel_widget, stretch=65)
        # Chọn mặc định menu đầu tiên
        self.menu_buttons[0].setChecked(True)
        self.stacked_config.setCurrentIndex(0)
        self.load_accounts()
        
    def create_config_widget(self, idx):
        # Tạo widget cấu hình cho từng loại quét, giữ lại dữ liệu khi chuyển mục
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(8, 8, 8, 8)
        titles = [
            "Cấu hình quét tài khoản theo dõi",
            "Cấu hình quét bài viết tài khoản",
            "Cấu hình quét chi tiết tài khoản",
            "Cấu hình quét follow tài khoản"
        ]
        title = QLabel(titles[idx])
        title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        title.setWordWrap(True)
        layout.addWidget(title)
        # Số luồng
        row1 = QHBoxLayout()
        row1.setSpacing(6)
        row1.addWidget(QLabel("Số luồng chạy đồng thời"))
        spin_thread = QSpinBox()
        spin_thread.setFixedSize(65, 24)
        spin_thread.setRange(1, 10)
        row1.addWidget(spin_thread)
        row1.addWidget(QLabel("Luồng"))
        layout.addLayout(row1)
        # Chuyển tài khoản nếu lỗi
        row2 = QHBoxLayout()
        row2.setSpacing(6)
        row2.addWidget(QLabel("Chuyển tài khoản nếu lỗi liên tiếp"))
        spin_error = QSpinBox()
        spin_error.setFixedSize(65, 24)
        spin_error.setRange(1, 100)
        row2.addWidget(spin_error)
        layout.addLayout(row2)
        # Khoảng cách quét
        row3 = QHBoxLayout()
        row3.setSpacing(6)
        row3.addWidget(QLabel("Khoảng cách hai lần quét (giây)"))
        spin_min = QSpinBox(); spin_min.setFixedSize(65, 24); spin_min.setRange(1, 3600)
        spin_max = QSpinBox(); spin_max.setFixedSize(65, 24); spin_max.setRange(1, 3600)
        row3.addWidget(spin_min); row3.addWidget(QLabel("-")); row3.addWidget(spin_max)
        layout.addLayout(row3)
        # Số lượng username
        row4 = QHBoxLayout()
        row4.setSpacing(6)
        row4.addWidget(QLabel("Mỗi tài khoản quét tối đa (username)"))
        spin_user_min = QSpinBox(); spin_user_min.setFixedSize(65, 24); spin_user_min.setRange(1, 1000)
        spin_user_max = QSpinBox(); spin_user_max.setFixedSize(65, 24); spin_user_max.setRange(1, 1000)
        row4.addWidget(spin_user_min); row4.addWidget(QLabel("-")); row4.addWidget(spin_user_max)
        layout.addLayout(row4)
        # Số lần quét mỗi username
        row5 = QHBoxLayout()
        row5.setSpacing(6)
        row5.addWidget(QLabel("Mỗi username quét tối đa"))
        spin_uname_min = QSpinBox(); spin_uname_min.setFixedSize(65, 24); spin_uname_min.setRange(1, 1000)
        spin_uname_max = QSpinBox(); spin_uname_max.setFixedSize(65, 24); spin_uname_max.setRange(1, 1000)
        row5.addWidget(spin_uname_min); row5.addWidget(QLabel("-")); row5.addWidget(spin_uname_max)
        layout.addLayout(row5)
        # Radio group
        radio_group = QGroupBox()
        radio_layout = QVBoxLayout(radio_group)
        radio_layout.setSpacing(4)
        radio1 = QRadioButton("Quét người theo dõi của chính tài khoản")
        radio2 = QRadioButton("Quét theo danh sách tài khoản")
        radio_layout.addWidget(radio1)
        radio_layout.addWidget(radio2)
        layout.addWidget(radio_group)
        # Link text
        link_text = QLabel("Nhập link trang cá nhân hoặc username vào đây mỗi dòng một giá trị...")
        link_text.setStyleSheet("color: blue; text-decoration: underline;")
        link_text.setCursor(Qt.CursorShape.PointingHandCursor)
        link_text.mousePressEvent = lambda event, i=idx: self.open_txt_file(i)
        layout.addWidget(link_text)
        layout.addStretch()
        # Lưu các widget cấu hình để lấy giá trị khi cần
        self.config_data[idx] = {
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
            'link_text': link_text
        }
        return widget
        
    def switch_config(self, idx):
        for i, btn in enumerate(self.menu_buttons):
            btn.setChecked(i == idx)
        self.stacked_config.setCurrentIndex(idx) 

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
            # Cột 2: Tên người dùng
            self.account_table.setItem(i, 2, QTableWidgetItem(acc.get("username", "")))
            # Cột 3: Trạng thái
            self.account_table.setItem(i, 3, QTableWidgetItem(acc.get("status", "")))
            # Cột 4: Thành công
            self.account_table.setItem(i, 4, QTableWidgetItem(str(acc.get("success", ""))))

    def start_scan(self):
        if self.scan_running:
            return
        self.scan_running = True
        self.result_data = []
        self.result_table.setRowCount(0)
        self.stats_label.setText("Tổng số bài viết quét được: 0")
        self.scan_idx = 0
        self.scan_timer = QTimer()
        self.scan_timer.timeout.connect(self.scan_step)
        self.scan_timer.start(500)  # 0.5s mỗi bước

    def scan_step(self):
        if self.scan_idx >= len(self.account_data):
            self.scan_timer.stop()
            self.scan_running = False
            return
        acc = self.account_data[self.scan_idx]
        acc['status'] = 'Đang quét'
        self.update_account_table()
        # Giả lập kết quả
        n_result = random.randint(1, 3)
        for j in range(n_result):
            self.result_data.append({
                'account': acc['username'],
                'target': f'target{j+1}',
                'username': f'result_{acc["username"]}_{j+1}'
            })
        acc['status'] = 'Hoàn thành'
        acc['success'] = n_result
        self.update_account_table()
        self.update_result_table()
        self.stats_label.setText(f"Tổng số bài viết quét được: {len(self.result_data)}")
        self.scan_idx += 1

    def stop_scan(self):
        if self.scan_timer:
            self.scan_timer.stop()
        self.scan_running = False

    def update_result_table(self):
        self.result_table.setRowCount(len(self.result_data))
        for i, res in enumerate(self.result_data):
            chk = QTableWidgetItem()
            chk.setCheckState(Qt.Unchecked)
            self.result_table.setItem(i, 0, chk)
            self.result_table.setItem(i, 1, QTableWidgetItem(str(i+1)))
            self.result_table.setItem(i, 2, QTableWidgetItem(res['account']))
            self.result_table.setItem(i, 3, QTableWidgetItem(res['target']))
            self.result_table.setItem(i, 4, QTableWidgetItem(res['username']))

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