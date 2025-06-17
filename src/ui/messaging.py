from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QPushButton, 
                            QTableWidget, QTableWidgetItem, QComboBox, QLabel, 
                            QLineEdit, QSpinBox, QRadioButton, QCheckBox, 
                            QGroupBox, QTextEdit, QHeaderView, QFileDialog, QMessageBox, QButtonGroup,
                            QProgressBar, QScrollArea, QFrame, QSplitter, QTabWidget, QApplication,
                            QSizePolicy, QStyledItemDelegate, QMenu)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSize, QModelIndex, QRect, QEvent
from PySide6.QtGui import QFont, QIcon, QPixmap, QColor, QPalette, QPainter, QPen
from src.ui.context_menus import MessagingContextMenu

class MessagingTab(QWidget):
    def __init__(self):
        super().__init__()
        # Biến lưu trạng thái
        self.usernames = []  # Danh sách username hợp lệ đã tải lên
        self.username_file_loaded = False
        self.username_file_path = None
        self.duplicate_filtered = False
        self.username_stats_label = QLabel("Số lượng username: 0")
        self.last_username_file_error = None
        self.init_ui()
        
    def init_ui(self):
        layout = QHBoxLayout(self)
        
        # Panel bên trái (35%)
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
        list_layout.setContentsMargins(8, 18, 8, 8)
        
        # Radio buttons
        self.username_radio = QRadioButton("Theo danh sách username")
        self.follower_radio = QRadioButton("Theo người theo dõi")
        self.following_radio = QRadioButton("Theo người đang theo dõi")
        self.radio_group = QButtonGroup(self)
        self.radio_group.addButton(self.username_radio)
        self.radio_group.addButton(self.follower_radio)
        self.radio_group.addButton(self.following_radio)
        self.radio_group.setExclusive(True)
        list_layout.addWidget(self.username_radio)
        list_layout.addWidget(self.follower_radio)
        list_layout.addWidget(self.following_radio)
        # Nút chọn file và checkbox chỉ cho lựa chọn username
        self.btn_choose_file = QPushButton("Chọn file username.txt")
        self.no_duplicate = QCheckBox("Không nhắn trùng username")
        list_layout.addWidget(self.btn_choose_file)
        list_layout.addWidget(self.no_duplicate)
        list_layout.addWidget(self.username_stats_label)
        self.btn_choose_file.setVisible(True)
        self.no_duplicate.setVisible(True)
        self.username_stats_label.setVisible(True)
        # Ẩn/hiện nút chọn file và checkbox theo radio
        self.username_radio.toggled.connect(self._update_list_options)
        self.follower_radio.toggled.connect(self._update_list_options)
        self.following_radio.toggled.connect(self._update_list_options)
        self.username_radio.setChecked(True)
        self._update_list_options()
        # Style cho checkbox khi tick
        self.no_duplicate.setStyleSheet("QCheckBox::indicator:checked { background-color: #4caf50; border: 1px solid #388e3c; } QCheckBox::indicator { width: 16px; height: 16px; }")
        # Style cho radio button khi chọn
        radio_style = """
        QRadioButton {
            background: white;
            color: #222;
            border-radius: 4px;
            padding: 2px 8px;
        }
        QRadioButton::indicator { width: 16px; height: 16px; }
        QRadioButton:checked {
            background: #2196f3;
            color: white;
        }
        """
        self.username_radio.setStyleSheet(radio_style)
        self.follower_radio.setStyleSheet(radio_style)
        self.following_radio.setStyleSheet(radio_style)
        # Xử lý chọn file username.txt
        self.btn_choose_file.clicked.connect(self.choose_username_file)
        # Xử lý lọc trùng
        self.no_duplicate.stateChanged.connect(self.filter_duplicate_usernames)
        left_layout.addWidget(list_group)
        
        # 3. Nhắn theo nội dung
        content_group = QGroupBox("Nhắn theo nội dung")
        content_layout = QVBoxLayout(content_group)
        
        # Bảng tin nhắn
        self.message_table = QTableWidget()
        self.message_table.setColumnCount(3)
        self.message_table.setHorizontalHeaderLabels(["", "Nội dung", "Link ảnh/video"])
        header1 = self.message_table.horizontalHeader()
        header1.setSectionResizeMode(0, QHeaderView.Fixed)
        header1.setSectionResizeMode(1, QHeaderView.Stretch)
        header1.setSectionResizeMode(2, QHeaderView.Stretch)
        header1.resizeSection(0, 60)
        self.message_table.verticalHeader().setVisible(False)
        header1.setStretchLastSection(True)
        self.message_table.horizontalHeader().setFixedHeight(40)
        content_layout.addWidget(self.message_table)
        
        # Text box nhập nội dung
        message_input = QTextEdit()
        message_input.setPlaceholderText("Nhập nội dung tin nhắn...")
        content_layout.addWidget(message_input)
        
        # Nút chọn ảnh/video và lưu
        btn_layout = QHBoxLayout()
        self.btn_choose_media = QPushButton("Chọn ảnh/video")
        self.btn_save = QPushButton("Lưu tin nhắn")
        btn_layout.addWidget(self.btn_choose_media)
        btn_layout.addWidget(self.btn_save)
        content_layout.addLayout(btn_layout)
        self.selected_media_path = None
        self.btn_choose_media.clicked.connect(self.choose_media_file)
        self.btn_save.clicked.connect(self.save_message_content)
        
        left_layout.addWidget(content_group)
        
        # Panel bên phải (65%)
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
        btn_load.setStyleSheet(load_button_style)
        btn_start.setStyleSheet(start_button_style)
        btn_stop.setStyleSheet(stop_button_style)

        toolbar_layout.addWidget(self.category_combo)
        toolbar_layout.addWidget(btn_load)
        toolbar_layout.addWidget(btn_start)
        toolbar_layout.addWidget(btn_stop)
        right_layout.addWidget(toolbar)
        
        # Bảng dữ liệu tài khoản
        self.account_table = QTableWidget()
        self.account_table.setColumnCount(6)
        headers = ["", "STT", "Tên người dùng", "Trạng thái", "Thành công", "Tình trạng"]
        self.account_table.setHorizontalHeaderLabels(headers)
        header2 = self.account_table.horizontalHeader()
        header2.setSectionResizeMode(0, QHeaderView.Fixed)
        header2.resizeSection(0, 32)
        header2.setSectionResizeMode(1, QHeaderView.Fixed)
        header2.resizeSection(1, 40)
        header2.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header2.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header2.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header2.setSectionResizeMode(5, QHeaderView.Stretch)
        self.account_table.verticalHeader().setVisible(False)
        header2.setStretchLastSection(True)
        self.account_table.horizontalHeader().setFixedHeight(40)
        
        # Footer thống kê
        stats_label = QLabel("Thành công: 0 | Thất bại: 0 | Chưa gửi: 0")
        
        # Thêm các thành phần vào layout
        right_layout.addWidget(self.account_table)
        right_layout.addWidget(stats_label)
        
        # Thêm các panel vào layout chính
        layout.addWidget(left_panel, 35)
        layout.addWidget(right_panel, 65) 

    def _update_list_options(self):
        if self.username_radio.isChecked():
            self.btn_choose_file.setVisible(True)
            self.no_duplicate.setVisible(True)
            self.username_stats_label.setVisible(True)
        else:
            self.btn_choose_file.setVisible(False)
            self.no_duplicate.setVisible(False)
            self.username_stats_label.setVisible(False)

    def choose_username_file(self):
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        file_path, _ = QFileDialog.getOpenFileName(self, "Chọn file username.txt", "", "Text Files (*.txt)")
        if not file_path:
            return
        usernames = []
        errors = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for idx, line in enumerate(f):
                username = line.strip()
                if not username:
                    errors.append(f"Dòng {idx+1} trống.")
                    continue
                if ' ' in username or ',' in username or '\t' in username:
                    errors.append(f"Dòng {idx+1} chứa ký tự không hợp lệ: {username}")
                    continue
                if username.count('@') > 0:
                    username = username.replace('@', '')
                if username:
                    usernames.append(username)
        if not usernames:
            QMessageBox.warning(self, "Lỗi file", "File không có username hợp lệ!")
            self.usernames = []
            self.username_file_loaded = False
            self.username_stats_label.setText("Số lượng username: 0")
            return
        self.usernames = usernames
        self.username_file_loaded = True
        self.username_file_path = file_path
        self.last_username_file_error = errors
        self.update_username_stats()
        if errors:
            QMessageBox.warning(self, "Cảnh báo file", "Một số dòng bị loại bỏ:\n" + '\n'.join(errors))

    def update_username_stats(self):
        count = len(self.usernames)
        self.username_stats_label.setText(f"Số lượng username: {count}")

    def filter_duplicate_usernames(self):
        if self.no_duplicate.isChecked() and self.usernames:
            unique_usernames = list(dict.fromkeys(self.usernames))
            self.usernames = unique_usernames
            self.duplicate_filtered = True
        else:
            self.duplicate_filtered = False
        self.update_username_stats()

    def choose_media_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Chọn ảnh hoặc video", "", "Media Files (*.png *.jpg *.jpeg *.mp4 *.mov *.avi)")
        if file_path:
            self.selected_media_path = file_path
            QMessageBox.information(self, "Đã chọn file", f"Đã chọn: {file_path}")
        else:
            self.selected_media_path = None

    def save_message_content(self):
        # Lưu nội dung vào bảng tin nhắn
        content = self.findChild(QTextEdit)
        if not content:
            return
        message = content.toPlainText().strip()
        media = self.selected_media_path or ""
        if not message and not media:
            QMessageBox.warning(self, "Thiếu nội dung", "Vui lòng nhập nội dung hoặc chọn ảnh/video!")
            return
        row = self.message_table.rowCount()
        self.message_table.insertRow(row)
        self.message_table.setItem(row, 0, QTableWidgetItem(str(row+1)))
        self.message_table.setItem(row, 1, QTableWidgetItem(message))
        self.message_table.setItem(row, 2, QTableWidgetItem(media))
        # Reset input
        content.clear()
        self.selected_media_path = None

    def closeEvent(self, event):
        for driver in self.active_drivers:
            try:
                driver.quit()
            except:
                pass
        self.active_drivers.clear()
        super().closeEvent(event)

    def save_settings(self):
        import json
        settings = {
            "thread_spin_value": self.thread_spin.value(),
            "error_spin_value": self.error_spin.value(),
            "max_inbox_value": self.max_inbox.value(),
            "min_inbox_value": self.min_inbox.value(),
            "delay_spin_value": self.delay_spin.value(),
            "username_radio_checked": self.username_radio.isChecked(),
            "follower_radio_checked": self.follower_radio.isChecked(),
            "following_radio_checked": self.following_radio.isChecked(),
            "no_duplicate_checked": self.no_duplicate.isChecked(),
            "username_file_path": self.username_file_path
        }
        with open("messaging_settings.json", "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)

    def load_settings(self):
        import json, os
        if os.path.exists("messaging_settings.json"):
            with open("messaging_settings.json", "r", encoding="utf-8") as f:
                settings = json.load(f)
            self.thread_spin.setValue(settings.get("thread_spin_value", 1))
            self.error_spin.setValue(settings.get("error_spin_value", 1))
            self.max_inbox.setValue(settings.get("max_inbox_value", 1))
            self.min_inbox.setValue(settings.get("min_inbox_value", 1))
            self.delay_spin.setValue(settings.get("delay_spin_value", 1))
            if settings.get("username_radio_checked", True):
                self.username_radio.setChecked(True)
            elif settings.get("follower_radio_checked", False):
                self.follower_radio.setChecked(True)
            elif settings.get("following_radio_checked", False):
                self.following_radio.setChecked(True)
            else:
                self.username_radio.setChecked(True) # Default if none checked
            self.no_duplicate.setChecked(settings.get("no_duplicate_checked", False))
            saved_path = settings.get("username_file_path")
            if saved_path and os.path.exists(saved_path):
                self.username_file_path = saved_path
                self.choose_username_file(saved_path) # Reload file to update usernames list and stats
            self._update_list_options() # Ensure correct visibility after loading settings

    def _validate_delay_spin(self):
        if self.delay_spin.value() < 5:
            QMessageBox.warning(self, "Cảnh báo", "Khoảng cách gửi tối thiểu phải là 5 giây!")

    def show_context_menu(self, pos):
        """Hiển thị menu chuột phải."""
        print(f"[DEBUG] show_context_menu được gọi tại vị trí: {pos}")
        menu = MessagingContextMenu(self)
        menu.exec(self.recipient_table.viewport().mapToGlobal(pos))

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    window = MessagingTab()
    window.show()
    sys.exit(app.exec()) 