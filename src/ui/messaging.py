from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QPushButton, 
                            QTableWidget, QTableWidgetItem, QComboBox, QLabel, 
                            QLineEdit, QSpinBox, QRadioButton, QCheckBox, 
                            QGroupBox, QTextEdit, QHeaderView, QFileDialog, QMessageBox, QButtonGroup,
                            QProgressBar, QScrollArea, QFrame, QSplitter, QTabWidget, QApplication,
                            QSizePolicy, QStyledItemDelegate, QMenu, QAbstractItemView, QInputDialog)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSize, QModelIndex, QRect, QEvent
from PySide6.QtGui import QFont, QIcon, QPixmap, QColor, QPalette, QPainter, QPen, QAction
from src.ui.context_menus import MessagingContextMenu
from src.ui.account_management import CheckboxDelegate
import json

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
        self.accounts = []  # Lưu toàn bộ tài khoản
        self.init_ui()
        self.load_message_templates()
        
    def init_ui(self):
        layout = QHBoxLayout(self)
        
        # Panel bên trái (35%)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Thu nhỏ cỡ chữ cho panel bên trái
        left_panel.setStyleSheet("font-size: 12px;")
        
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
        
        # Radio buttons + nút nhập data + nút info
        radio_row_layout = QHBoxLayout()
        self.username_radio = QRadioButton("Theo danh sách username")
        radio_row_layout.addWidget(self.username_radio)
        radio_row_layout.addStretch(1)
        self.btn_choose_file = QPushButton("Nhập data")
        self.btn_choose_file.setFixedWidth(90)
        radio_row_layout.addWidget(self.btn_choose_file)
        # Nút info
        self.info_btn = QPushButton("i")
        self.info_btn.setFixedSize(22, 22)
        self.info_btn.setStyleSheet("QPushButton { border-radius: 11px; background: #1976D2; color: white; font-weight: bold; font-size: 13px; } QPushButton::hover { background: #1565c0; }")
        self.info_btn.setToolTip('<div style="background:#fff; color:#1976D2; font-size:13px; padding:6px;">'
            '<ul style="margin:0; padding-left:18px;">'
            '<li><b>Theo danh sách username</b>: Nhắn theo dữ liệu được tải lên (có thể là id, username,...)</li>'
            '<li><b>Theo người theo dõi</b>: Nhắn cho những người đang theo dõi chính tài khoản gửi tin nhắn</li>'
            '<li><b>Theo người đang theo dõi</b>: Nhắn cho những người mà tài khoản gửi tin nhắn đang theo dõi</li>'
            '<li><b>Không nhắn trùng username</b>: Khi tick, các tài khoản không được phép gửi trùng người nhận; bỏ tick thì được phép gửi trùng người nhận.</li>'
            '<li>Chỉ các tài khoản đã tick chọn mới được gửi tin nhắn.</li>'
            '</ul>'
        )
        radio_row_layout.addWidget(self.info_btn)
        list_layout.addLayout(radio_row_layout)
        self.follower_radio = QRadioButton("Theo người theo dõi")
        self.following_radio = QRadioButton("Theo người đang theo dõi")
        self.radio_group = QButtonGroup(self)
        self.radio_group.addButton(self.username_radio)
        self.radio_group.addButton(self.follower_radio)
        self.radio_group.addButton(self.following_radio)
        self.radio_group.setExclusive(True)
        list_layout.addWidget(self.follower_radio)
        list_layout.addWidget(self.following_radio)
        # Nút nhập data đã chuyển lên trên
        # list_layout.addWidget(self.btn_choose_file)  # XÓA DÒNG NÀY nếu còn
        self.no_duplicate = QCheckBox("Không nhắn trùng username")
        list_layout.addWidget(self.no_duplicate)
        list_layout.addWidget(self.username_stats_label)
        self.btn_choose_file.setVisible(True)
        self.no_duplicate.setVisible(True)
        self.username_stats_label.setVisible(True)
        # Ẩn/hiện nút nhập data và checkbox theo radio
        def update_input_mode():
            if self.username_radio.isChecked():
                self.btn_choose_file.setEnabled(True)
                self.no_duplicate.setEnabled(True)
            else:
                self.btn_choose_file.setEnabled(False)
                self.no_duplicate.setEnabled(False)
        self.username_radio.toggled.connect(update_input_mode)
        self.follower_radio.toggled.connect(update_input_mode)
        self.following_radio.toggled.connect(update_input_mode)
        update_input_mode()
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
        /* Không đổi nền khi checked */
        QRadioButton:checked {
            background: white;
            color: #1976D2;
        }
        """
        self.username_radio.setStyleSheet(radio_style)
        self.follower_radio.setStyleSheet(radio_style)
        self.following_radio.setStyleSheet(radio_style)
        # Đổi nền nút nhập data thành xanh dương và chỉnh kích thước
        self.btn_choose_file.setStyleSheet("QPushButton { background-color: #1976D2; color: white; border-radius: 4px; } QPushButton::hover { background-color: #1565c0; }")
        self.btn_choose_file.setMinimumSize(70, 35)
        self.btn_choose_file.setMaximumSize(90, 35)
        self.btn_choose_file.clicked.disconnect()
        self.btn_choose_file.clicked.connect(self.open_or_create_data_file)
        # Xử lý lọc trùng
        self.no_duplicate.stateChanged.connect(self.filter_duplicate_usernames)
        left_layout.addWidget(list_group)
        
        # 3. Nhắn theo nội dung
        content_group = QGroupBox("Nhắn theo nội dung")
        content_layout = QVBoxLayout(content_group)
        
        # Bảng tin nhắn có thêm cột checkbox nhỏ gọn
        self.message_table = QTableWidget()
        self.message_table.setColumnCount(3)
        self.message_table.setHorizontalHeaderLabels(["", "Nội dung", "Link ảnh/video"])
        header1 = self.message_table.horizontalHeader()
        header1.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header1.resizeSection(0, 24)
        header1.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header1.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header1.resizeSection(2, 120)  # Thu nhỏ cột Link ảnh/video
        self.message_table.verticalHeader().setVisible(False)
        header1.setStretchLastSection(True)
        self.message_table.horizontalHeader().setFixedHeight(40)
        # Menu chuột phải cho bảng nội dung tin nhắn
        self.message_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.message_table.customContextMenuRequested.connect(self.show_message_context_menu)
        self.message_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        content_layout.addWidget(self.message_table)
        
        # Text box nhập nội dung
        message_input = QTextEdit()
        message_input.setPlaceholderText("Nhập nội dung tin nhắn...")
        message_input.setFixedHeight(50)
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
        self.load_folder_list_to_combo()
        self.category_combo.currentIndexChanged.connect(self.on_folder_changed)
        
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
        header2.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header2.resizeSection(0, 32)
        header2.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header2.resizeSection(1, 40)
        header2.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header2.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header2.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header2.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.account_table.verticalHeader().setVisible(False)
        header2.setStretchLastSection(True)
        self.account_table.horizontalHeader().setFixedHeight(40)
        # Đặt delegate checkbox giống tab Quản lý Tài khoản
        self.checkbox_delegate = CheckboxDelegate(self)
        self.account_table.setItemDelegateForColumn(0, self.checkbox_delegate)
        self.checkbox_delegate.checkbox_clicked.connect(self.on_checkbox_clicked)
        
        # Footer thống kê
        stats_label = QLabel("Thành công: 0 | Thất bại: 0 | Chưa gửi: 0")
        
        # Thêm các thành phần vào layout
        right_layout.addWidget(self.account_table)
        right_layout.addWidget(stats_label)
        
        # Thêm các panel vào layout chính
        layout.addWidget(left_panel, 35)
        layout.addWidget(right_panel, 65) 

        self.load_accounts()  # Nạp tài khoản khi khởi tạo

        self.account_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.account_table.customContextMenuRequested.connect(self.show_context_menu)
        self.account_table.setSelectionBehavior(QAbstractItemView.SelectRows)

    def open_or_create_data_file(self):
        import os
        import subprocess
        data_file = "usernames_data.txt"
        if not os.path.exists(data_file):
            with open(data_file, "w", encoding="utf-8") as f:
                f.write("")
        # Mở file bằng notepad (Windows)
        try:
            subprocess.Popen(["notepad.exe", data_file])
        except Exception as e:
            QMessageBox.warning(self, "Lỗi", f"Không thể mở file: {e}")

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
        # Cột 0: checkbox nhỏ
        item_checkbox = QTableWidgetItem()
        item_checkbox.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        item_checkbox.setCheckState(Qt.Unchecked)
        self.message_table.setItem(row, 0, item_checkbox)
        self.message_table.setItem(row, 1, QTableWidgetItem(message))
        self.message_table.setItem(row, 2, QTableWidgetItem(media))
        # Reset input
        content.clear()
        self.selected_media_path = None
        self.save_message_templates()

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
            update_input_mode() # Ensure correct visibility after loading settings

    def _validate_delay_spin(self):
        if self.delay_spin.value() < 5:
            QMessageBox.warning(self, "Cảnh báo", "Khoảng cách gửi tối thiểu phải là 5 giây!")

    def show_context_menu(self, pos):
        index = self.account_table.indexAt(pos)
        context_row = index.row() if index.isValid() else None
        menu = MessagingContextMenu(self)
        menu.context_row = context_row
        menu.exec(self.account_table.viewport().mapToGlobal(pos))

    def load_folder_list_to_combo(self):
        self.category_combo.clear()
        self.category_combo.addItem("Tất cả")
        import os, json
        folder_map_file = os.path.join("data", "folder_map.json")
        if os.path.exists(folder_map_file):
            with open(folder_map_file, "r", encoding="utf-8") as f:
                folder_map = json.load(f)
            if folder_map and "_FOLDER_SET_" in folder_map:
                for folder in folder_map["_FOLDER_SET_"]:
                    if folder != "Tổng":
                        self.category_combo.addItem(folder)
        print(f"[DEBUG][MessagingTab] Đã tải danh sách thư mục vào combobox: {self.category_combo.count()} mục")

    def on_folder_changed(self):
        selected_folder = self.category_combo.currentText()
        import os, json
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

    def load_accounts(self):
        # Nạp toàn bộ tài khoản từ accounts.json, chỉ lấy tài khoản đã đăng nhập
        import os, json
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
            item = QTableWidgetItem()
            item.setData(CheckboxDelegate.CheckboxStateRole, acc.get("selected", False))
            self.account_table.setItem(i, 0, item)
            self.account_table.setItem(i, 1, QTableWidgetItem(str(i+1)))
            self.account_table.setItem(i, 2, QTableWidgetItem(acc.get("username", "")))
            self.account_table.setItem(i, 3, QTableWidgetItem(acc.get("status", "")))
            self.account_table.setItem(i, 4, QTableWidgetItem(str(acc.get("success", ""))))
            self.account_table.setItem(i, 5, QTableWidgetItem(acc.get("state", "")))
        self.account_table.clearSelection()

    def on_checkbox_clicked(self, row, new_state):
        # Cập nhật trạng thái 'selected' trong dữ liệu gốc
        if 0 <= row < len(self.accounts):
            self.accounts[row]["selected"] = new_state

    def send_message(self):
        # Lọc danh sách người nhận theo chế độ radio
        if self.username_radio.isChecked():
            selected_accounts = [acc for acc in self.accounts if acc.get("selected")]
            if self.no_duplicate.isChecked():
                seen = set()
                filtered = []
                for acc in selected_accounts:
                    username = acc.get("username", "")
                    if username not in seen:
                        filtered.append(acc)
                        seen.add(username)
                selected_accounts = filtered
            if not selected_accounts:
                QMessageBox.warning(self, "Gửi tin nhắn", "Vui lòng tick chọn ít nhất một tài khoản để gửi tin nhắn.")
                return
            # Lấy các bài viết đã tick chọn
            selected_templates = []
            for row in range(self.message_table.rowCount()):
                item_checkbox = self.message_table.item(row, 0)
                if item_checkbox and item_checkbox.checkState() == Qt.Checked:
                    content = self.message_table.item(row, 1).text() if self.message_table.item(row, 1) else ""
                    media = self.message_table.item(row, 2).text() if self.message_table.item(row, 2) else ""
                    selected_templates.append({"content": content, "media": media})
            if not selected_templates:
                QMessageBox.warning(self, "Gửi tin nhắn", "Vui lòng tick chọn ít nhất một bài viết để gửi.")
                return
            usernames = ', '.join(acc.get("username", "") for acc in selected_accounts)
            msg_preview = '\n'.join(f"- {tpl['content']} | {tpl['media']}" for tpl in selected_templates)
            QMessageBox.information(self, "Gửi tin nhắn", f"Đã gửi tin nhắn demo tới: {usernames}\nNội dung:\n{msg_preview}")
        elif self.follower_radio.isChecked():
            # TODO: Lấy danh sách followers của tài khoản gửi tin nhắn
            QMessageBox.information(self, "Gửi tin nhắn", "Chức năng gửi cho người theo dõi đang được phát triển.")
        elif self.following_radio.isChecked():
            # TODO: Lấy danh sách following của tài khoản gửi tin nhắn
            QMessageBox.information(self, "Gửi tin nhắn", "Chức năng gửi cho người đang theo dõi đang được phát triển.")

    def load_recipients(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Chọn file danh sách username", "", "Text Files (*.txt)")
        if not file_path:
            return
        usernames = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                username = line.strip()
                if username:
                    usernames.append(username)
        if not usernames:
            QMessageBox.warning(self, "Lỗi file", "File không có username hợp lệ!")
            return
        # Nạp vào bảng account_table (chỉ thêm mới, không xóa các tài khoản cũ)
        for username in usernames:
            if not any(acc.get("username") == username for acc in self.accounts):
                self.accounts.append({"username": username, "status": "", "selected": False, "success": 0, "state": ""})
        self.update_account_table()
        QMessageBox.information(self, "Thành công", f"Đã nạp {len(usernames)} username vào danh sách tài khoản.")

    def export_recipients(self):
        selected_accounts = [acc for acc in self.accounts if acc.get("selected")]
        if not selected_accounts:
            QMessageBox.warning(self, "Xuất danh sách", "Vui lòng tick chọn ít nhất một tài khoản để xuất.")
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "Xuất danh sách người nhận", "", "Text Files (*.txt)")
        if not file_path:
            return
        with open(file_path, 'w', encoding='utf-8') as f:
            for acc in selected_accounts:
                f.write(acc.get("username", "") + "\n")
        QMessageBox.information(self, "Thành công", f"Đã xuất {len(selected_accounts)} username ra file.")

    def clear_recipients(self):
        QMessageBox.information(self, "Chức năng", "Xóa danh sách người nhận đang được phát triển.")

    # Đồng bộ logic chọn/bỏ chọn với tab Quản lý Tài khoản
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

    def show_message_context_menu(self, pos):
        index = self.message_table.indexAt(pos)
        if not index.isValid():
            return
        menu = QMenu(self)
        action_select = menu.addAction("Chọn bài viết")
        action_delete = menu.addAction("Xóa nội dung")
        action_edit = menu.addAction("Chỉnh sửa nội dung hoặc link")
        action = menu.exec(self.message_table.viewport().mapToGlobal(pos))
        selected_rows = set(idx.row() for idx in self.message_table.selectionModel().selectedRows())
        row = index.row()
        if action == action_select:
            # Tick chọn các dòng đang bôi đen
            for r in selected_rows:
                item_checkbox = self.message_table.item(r, 0)
                if item_checkbox:
                    item_checkbox.setCheckState(Qt.Checked)
            self.save_message_templates()
        elif action == action_delete:
            self.message_table.removeRow(row)
            self.save_message_templates()
        elif action == action_edit:
            old_content = self.message_table.item(row, 1).text() if self.message_table.item(row, 1) else ""
            old_link = self.message_table.item(row, 2).text() if self.message_table.item(row, 2) else ""
            new_content, ok1 = QInputDialog.getText(self, "Chỉnh sửa nội dung", "Nội dung:", QLineEdit.EchoMode.Normal, old_content)
            if not ok1:
                return
            new_link, ok2 = QInputDialog.getText(self, "Chỉnh sửa link ảnh/video", "Link ảnh/video:", QLineEdit.EchoMode.Normal, old_link)
            if not ok2:
                return
            self.message_table.setItem(row, 1, QTableWidgetItem(new_content))
            self.message_table.setItem(row, 2, QTableWidgetItem(new_link))
            self.save_message_templates()

    def load_message_templates(self):
        import os
        file_path = "message_templates.json"
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    templates = json.load(f)
                except Exception:
                    templates = []
            self.message_table.setRowCount(0)
            for tpl in templates:
                row = self.message_table.rowCount()
                self.message_table.insertRow(row)
                # Cột 0: checkbox nhỏ
                item_checkbox = QTableWidgetItem()
                item_checkbox.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                item_checkbox.setCheckState(Qt.Unchecked)
                self.message_table.setItem(row, 0, item_checkbox)
                self.message_table.setItem(row, 1, QTableWidgetItem(tpl.get("content", "")))
                self.message_table.setItem(row, 2, QTableWidgetItem(tpl.get("media", "")))

    def save_message_templates(self):
        templates = []
        for row in range(self.message_table.rowCount()):
            content = self.message_table.item(row, 1).text() if self.message_table.item(row, 1) else ""
            media = self.message_table.item(row, 2).text() if self.message_table.item(row, 2) else ""
            templates.append({"content": content, "media": media})
        with open("message_templates.json", "w", encoding="utf-8") as f:
            json.dump(templates, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    window = MessagingTab()
    window.show()
    sys.exit(app.exec()) 