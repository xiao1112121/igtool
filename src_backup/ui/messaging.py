from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QPushButton, 
                            QTableWidget, QTableWidgetItem, QComboBox, QLabel, 
                            QLineEdit, QSpinBox, QRadioButton, QCheckBox, 
                            QGroupBox, QTextEdit)
from PySide6.QtCore import Qt

class MessagingTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QHBoxLayout(self)
        
        # Panel bên trái (30%)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # 1. Cấu hình tin nhắn
        config_group = QGroupBox("Cấu hình tin nhắn")
        config_layout = QVBoxLayout(config_group)
        
        # Số luồng chạy đồng thời
        thread_layout = QHBoxLayout()
        thread_layout.addWidget(QLabel("Số luồng:"))
        thread_spin = QSpinBox()
        thread_spin.setRange(1, 10)
        thread_layout.addWidget(thread_spin)
        config_layout.addLayout(thread_layout)
        
        # Tài khoản lỗi cho chuyển tiếp
        error_layout = QHBoxLayout()
        error_layout.addWidget(QLabel("Tài khoản lỗi:"))
        error_spin = QSpinBox()
        error_spin.setRange(1, 100)
        error_layout.addWidget(error_spin)
        config_layout.addLayout(error_layout)
        
        # Tối đa/tối thiểu inbox
        inbox_layout = QHBoxLayout()
        inbox_layout.addWidget(QLabel("Tối đa inbox:"))
        max_inbox = QSpinBox()
        max_inbox.setRange(1, 1000)
        inbox_layout.addWidget(max_inbox)
        inbox_layout.addWidget(QLabel("Tối thiểu inbox:"))
        min_inbox = QSpinBox()
        min_inbox.setRange(1, 1000)
        inbox_layout.addWidget(min_inbox)
        config_layout.addLayout(inbox_layout)
        
        # Khoảng cách gửi
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("Khoảng cách (giây):"))
        delay_spin = QSpinBox()
        delay_spin.setRange(1, 3600)
        delay_layout.addWidget(delay_spin)
        config_layout.addLayout(delay_layout)
        
        left_layout.addWidget(config_group)
        
        # 2. Nhắn theo danh sách
        list_group = QGroupBox("Nhắn theo danh sách")
        list_layout = QVBoxLayout(list_group)
        
        # Radio buttons
        username_radio = QRadioButton("Nhắn theo danh sách username")
        list_layout.addWidget(username_radio)
        
        # Nút chọn file
        btn_choose_file = QPushButton("Chọn file username.txt")
        list_layout.addWidget(btn_choose_file)
        
        # Checkbox không nhắn trùng
        no_duplicate = QCheckBox("Không nhắn trùng username")
        list_layout.addWidget(no_duplicate)
        
        # Radio buttons người theo dõi
        follower_radio = QRadioButton("Nhắn tin người theo dõi")
        following_radio = QRadioButton("Nhắn tin người đang theo dõi")
        list_layout.addWidget(follower_radio)
        list_layout.addWidget(following_radio)
        
        left_layout.addWidget(list_group)
        
        # 3. Nhắn theo nội dung
        content_group = QGroupBox("Nhắn theo nội dung")
        content_layout = QVBoxLayout(content_group)
        
        # Bảng tin nhắn
        self.message_table = QTableWidget()
        self.message_table.setColumnCount(3)
        self.message_table.setHorizontalHeaderLabels(["", "Nội dung", "Link ảnh/video"])
        content_layout.addWidget(self.message_table)
        
        # Text box nhập nội dung
        message_input = QTextEdit()
        message_input.setPlaceholderText("Nhập nội dung tin nhắn...")
        content_layout.addWidget(message_input)
        
        # Nút chọn ảnh/video và lưu
        btn_layout = QHBoxLayout()
        btn_choose_media = QPushButton("Chọn ảnh/video")
        btn_save = QPushButton("Lưu tin nhắn")
        btn_layout.addWidget(btn_choose_media)
        btn_layout.addWidget(btn_save)
        content_layout.addLayout(btn_layout)
        
        left_layout.addWidget(content_group)
        
        # Panel bên phải (70%)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Thanh công cụ
        toolbar = QWidget()
        toolbar_layout = QHBoxLayout(toolbar)
        
        # ComboBox danh mục
        self.category_combo = QComboBox()
        self.category_combo.addItems(["Tất cả", "Live", "Die"])
        
        # Các nút điều khiển
        btn_load = QPushButton("Load")
        btn_start = QPushButton("Start")
        btn_stop = QPushButton("Stop")
        
        toolbar_layout.addWidget(self.category_combo)
        toolbar_layout.addWidget(btn_load)
        toolbar_layout.addWidget(btn_start)
        toolbar_layout.addWidget(btn_stop)
        
        # Bảng dữ liệu tài khoản
        self.account_table = QTableWidget()
        self.account_table.setColumnCount(6)
        headers = ["", "STT", "Tên người dùng", "Trạng thái", "Thành công", "Tình trạng"]
        self.account_table.setHorizontalHeaderLabels(headers)
        
        # Footer thống kê
        stats_label = QLabel("Thành công: 0 | Thất bại: 0 | Chưa gửi: 0")
        
        # Thêm các thành phần vào layout
        right_layout.addWidget(toolbar)
        right_layout.addWidget(self.account_table)
        right_layout.addWidget(stats_label)
        
        # Thêm các panel vào layout chính
        layout.addWidget(left_panel, 30)
        layout.addWidget(right_panel, 70) 