from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QPushButton, 
                            QTableWidget, QTableWidgetItem, QComboBox, QLabel, 
                            QLineEdit, QMenu, QCheckBox)
from PySide6.QtCore import Qt

class AccountManagementTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QHBoxLayout(self)
        
        # Panel bên trái (25%)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Nút thêm tài khoản và thư mục
        btn_add_account = QPushButton("Thêm tài khoản")
        btn_add_folder = QPushButton("Thêm thư mục")
        left_layout.addWidget(btn_add_account)
        left_layout.addWidget(btn_add_folder)
        left_layout.addStretch()
        
        # Panel bên phải (75%)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Thanh công cụ phía trên
        toolbar = QWidget()
        toolbar_layout = QHBoxLayout(toolbar)
        
        # ComboBox danh mục
        self.category_combo = QComboBox()
        self.category_combo.addItems(["Tất cả", "Live", "Die"])
        
        # Nút Load
        btn_load = QPushButton("Load")
        
        # Thống kê
        stats_label = QLabel("Tổng: 0 | Live: 0 | Die: 0")
        
        # Ô tìm kiếm
        search_input = QLineEdit()
        search_input.setPlaceholderText("Tìm kiếm username...")
        
        toolbar_layout.addWidget(self.category_combo)
        toolbar_layout.addWidget(btn_load)
        toolbar_layout.addWidget(stats_label)
        toolbar_layout.addWidget(search_input)
        
        # Bảng dữ liệu
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        headers = ["", "STT", "Tên đăng nhập", "Mật khẩu", "Trạng thái", 
                  "Follower", "Following", "Proxy", "Hành động cuối"]
        self.table.setHorizontalHeaderLabels(headers)
        
        # Thêm các thành phần vào layout chính
        right_layout.addWidget(toolbar)
        right_layout.addWidget(self.table)
        
        # Thêm các panel vào layout chính
        layout.addWidget(left_panel, 25)
        layout.addWidget(right_panel, 75)
        
        # Thiết lập context menu cho bảng
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
    def show_context_menu(self, position):
        menu = QMenu()
        
        # Thêm các action vào menu
        select_action = menu.addAction("Chọn")
        deselect_action = menu.addAction("Bỏ chọn")
        menu.addSeparator()
        login_action = menu.addAction("Đăng nhập Instagram")
        update_action = menu.addAction("Cập nhật thông tin")
        menu.addSeparator()
        copy_action = menu.addAction("Copy")
        paste_action = menu.addAction("Dán")
        delete_action = menu.addAction("Xóa")
        menu.addSeparator()
        check_action = menu.addAction("Kiểm tra thông tin")
        move_action = menu.addAction("Chuyển danh mục")
        
        # Hiển thị menu tại vị trí chuột
        menu.exec(self.table.viewport().mapToGlobal(position)) 