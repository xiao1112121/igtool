from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QPushButton, 
                            QTableWidget, QTableWidgetItem, QComboBox, QLabel, 
                            QLineEdit, QSpinBox, QRadioButton, QCheckBox, 
                            QGroupBox, QTextEdit, QFrame, QGridLayout, QStackedWidget, QFileDialog, QMessageBox)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QIcon, QFont
import random

class DataScannerTab(QWidget):
    def __init__(self):
        super().__init__()
        self.config_data = [{} for _ in range(4)]  # Lưu cấu hình từng mục
        self.username_lists = [[], [], [], []]    # Lưu danh sách username từng mục
        self.scan_running = False
        self.scan_timer = None
        self.account_data = []
        self.result_data = []
        self.init_ui()
        
    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(10)
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
            self.menu_buttons.append(btn)
            sidebar.addWidget(btn)
        sidebar.addStretch()
        sidebar_widget = QWidget()
        sidebar_widget.setLayout(sidebar)
        # Phần giữa (25%) - Cấu hình
        self.stacked_config = QStackedWidget()
        self.config_widgets = [self.create_config_widget(i) for i in range(4)]
        for w in self.config_widgets:
            self.stacked_config.addWidget(w)
        # Bảng phải (60%) - Bảng dữ liệu
        right_panel = QVBoxLayout()
        # Bảng trên
        top_group = QGroupBox("Danh sách tài khoản")
        top_layout = QVBoxLayout(top_group)
        self.stats_label = QLabel("Tổng số bài viết quét được: 0")
        self.stats_label.setFont(QFont("Segoe UI", 10))
        top_layout.addWidget(self.stats_label)
        toolbar = QHBoxLayout()
        self.category_combo = QComboBox()
        self.category_combo.addItems(["Tất cả", "Live", "Die"])
        self.category_combo.currentIndexChanged.connect(self.load_accounts)
        self.btn_load = QPushButton("Load")
        self.btn_load.setStyleSheet("background:#FFD700;color:white;border-radius:5px;min-width:70px;min-height:35px;")
        self.btn_load.clicked.connect(self.load_accounts)
        self.btn_start = QPushButton("Start")
        self.btn_start.setStyleSheet("background:#4CAF50;color:white;border-radius:5px;min-width:70px;min-height:35px;")
        self.btn_start.clicked.connect(self.start_scan)
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setStyleSheet("background:#f44336;color:white;border-radius:5px;min-width:70px;min-height:35px;")
        self.btn_stop.clicked.connect(self.stop_scan)
        toolbar.addWidget(self.category_combo)
        toolbar.addWidget(self.btn_load)
        toolbar.addWidget(self.btn_start)
        toolbar.addWidget(self.btn_stop)
        top_layout.addLayout(toolbar)
        self.account_table = QTableWidget()
        self.account_table.setColumnCount(5)
        self.account_table.setHorizontalHeaderLabels(["", "STT", "Username", "Trạng thái", "Thành công"])
        self.account_table.setColumnWidth(0, 40)
        self.account_table.setColumnWidth(1, 40)
        self.account_table.setColumnWidth(2, 140)
        self.account_table.setColumnWidth(3, 165)
        self.account_table.setColumnWidth(4, 150)
        top_layout.addWidget(self.account_table)
        # Bảng dưới
        bottom_group = QGroupBox("Kết quả quét")
        bottom_layout = QVBoxLayout(bottom_group)
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(5)
        self.result_table.setHorizontalHeaderLabels(["", "STT", "Tài khoản quét", "Tài khoản bị quét", "Username quét được"])
        self.result_table.setColumnWidth(0, 40)
        self.result_table.setColumnWidth(1, 40)
        self.result_table.setColumnWidth(2, 140)
        self.result_table.setColumnWidth(3, 140)
        self.result_table.setColumnWidth(4, 140)
        bottom_layout.addWidget(self.result_table)
        right_panel.addWidget(top_group)
        right_panel.addWidget(bottom_group)
        right_panel_widget = QWidget()
        right_panel_widget.setLayout(right_panel)
        # Thêm vào layout chính với tỷ lệ 15-25-60
        main_layout.addWidget(sidebar_widget, stretch=3)
        main_layout.addWidget(self.stacked_config, stretch=5)
        main_layout.addWidget(right_panel_widget, stretch=12)
        # Chọn mặc định menu đầu tiên
        self.menu_buttons[0].setChecked(True)
        self.stacked_config.setCurrentIndex(0)
        self.load_accounts()
        
    def create_config_widget(self, idx):
        # Tạo widget cấu hình cho từng loại quét, giữ lại dữ liệu khi chuyển mục
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        titles = [
            "Cấu hình quét tài khoản theo dõi",
            "Cấu hình quét bài viết tài khoản",
            "Cấu hình quét chi tiết tài khoản",
            "Cấu hình quét follow tài khoản"
        ]
        title = QLabel(titles[idx])
        title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(title)
        # Số luồng
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Số luồng chạy đồng thời"))
        spin_thread = QSpinBox()
        spin_thread.setFixedSize(65, 24)
        spin_thread.setRange(1, 10)
        row1.addWidget(spin_thread)
        row1.addWidget(QLabel("Luồng"))
        layout.addLayout(row1)
        # Chuyển tài khoản nếu lỗi
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Chuyển tài khoản nếu lỗi liên tiếp"))
        spin_error = QSpinBox()
        spin_error.setFixedSize(65, 24)
        spin_error.setRange(1, 100)
        row2.addWidget(spin_error)
        layout.addLayout(row2)
        # Khoảng cách quét
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Khoảng cách hai lần quét (giây)"))
        spin_min = QSpinBox(); spin_min.setFixedSize(65, 24); spin_min.setRange(1, 3600)
        spin_max = QSpinBox(); spin_max.setFixedSize(65, 24); spin_max.setRange(1, 3600)
        row3.addWidget(spin_min); row3.addWidget(QLabel("-")); row3.addWidget(spin_max)
        layout.addLayout(row3)
        # Số lượng username
        row4 = QHBoxLayout()
        row4.addWidget(QLabel("Mỗi tài khoản quét tối đa (username)"))
        spin_user_min = QSpinBox(); spin_user_min.setFixedSize(65, 24); spin_user_min.setRange(1, 1000)
        spin_user_max = QSpinBox(); spin_user_max.setFixedSize(65, 24); spin_user_max.setRange(1, 1000)
        row4.addWidget(spin_user_min); row4.addWidget(QLabel("-")); row4.addWidget(spin_user_max)
        layout.addLayout(row4)
        # Số lần quét mỗi username
        row5 = QHBoxLayout()
        row5.addWidget(QLabel("Mỗi username quét tối đa"))
        spin_uname_min = QSpinBox(); spin_uname_min.setFixedSize(65, 24); spin_uname_min.setRange(1, 1000)
        spin_uname_max = QSpinBox(); spin_uname_max.setFixedSize(65, 24); spin_uname_max.setRange(1, 1000)
        row5.addWidget(spin_uname_min); row5.addWidget(QLabel("-")); row5.addWidget(spin_uname_max)
        layout.addLayout(row5)
        # Radio group
        radio_group = QGroupBox()
        radio_layout = QVBoxLayout(radio_group)
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
        # Sinh dữ liệu mẫu cho tài khoản
        self.account_data = []
        for i in range(1, 11):
            self.account_data.append({
                'checked': False,
                'username': f'user{i}',
                'status': 'Chờ',
                'success': 0
            })
        self.update_account_table()

    def update_account_table(self):
        self.account_table.setRowCount(len(self.account_data))
        for i, acc in enumerate(self.account_data):
            chk = QTableWidgetItem()
            chk.setCheckState(Qt.Checked if acc['checked'] else Qt.Unchecked)
            self.account_table.setItem(i, 0, chk)
            self.account_table.setItem(i, 1, QTableWidgetItem(str(i+1)))
            self.account_table.setItem(i, 2, QTableWidgetItem(acc['username']))
            self.account_table.setItem(i, 3, QTableWidgetItem(acc['status']))
            self.account_table.setItem(i, 4, QTableWidgetItem(str(acc['success'])))

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