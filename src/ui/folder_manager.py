from PySide6.QtWidgets import (QDialog, QHBoxLayout, QVBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QLineEdit, QLabel, QMessageBox, QMenu, QHeaderView, QInputDialog, QWidget)
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QFont, QCloseEvent
import os
import json
from typing import Dict, List, Optional, Union, Any

# Lớp quản lý dialog thư mục tài khoản
class FolderManagerDialog(QDialog):
    folders_updated = Signal() # Tín hiệu để thông báo khi thư mục được cập nhật

    def __init__(self, accounts: List[Dict[str, Union[str, bool]]], folder_map: Dict[str, Any], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Quản lý Thư Mục Tài Khoản") # Đặt tiêu đề cửa sổ
        self.setFixedSize(835, 500) # Kích thước cố định: 835 x 500 px

        self.accounts = accounts # Danh sách tài khoản từ AccountManagementTab
        self.folder_map = folder_map # Ánh xạ username -> folder
        self.folders = self.load_folders() # Danh sách các thư mục duy nhất
        self.selected_folder_in_table = "Tất cả" # Theo dõi thư mục đang chọn trong bảng thư mục

        self.DATA_DIR = "data" # Thư mục lưu trữ dữ liệu
        if not os.path.exists(self.DATA_DIR):
            os.makedirs(self.DATA_DIR) # Tạo thư mục nếu chưa tồn tại
        self.FOLDER_MAP_FILE = os.path.join(self.DATA_DIR, "folder_map.json") # Đường dẫn file lưu map thư mục (đồng bộ tên file)

        self.init_ui() # Khởi tạo giao diện
        self.update_folder_table() # Cập nhật bảng thư mục
        self.update_account_table() # Cập nhật bảng tài khoản khi khởi tạo
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowCloseButtonHint)

        # Khi khởi tạo, nếu có file thì load lại folder_map
        self.load_folders_on_startup()  

        # Sau mỗi lần thêm/xóa/sửa thư mục, gọi save_folder_map()
        # (Bạn cần gọi save_folder_map() trong các hàm add_folder, delete_folder, edit_folder)

    def load_folders(self):
        # [MODIFIED] Lấy đủ cả các folder từng tạo (kể cả chưa có account nào)
        folders = []
        if "_FOLDER_SET_" in self.folder_map:       # [ADDED]
            folders = list(self.folder_map["_FOLDER_SET_"])   # [ADDED]
        # Đảm bảo lấy cả folder đang có account gán mà chưa có trong _FOLDER_SET_
        for f in self.folder_map.values():           # [ADDED]
            if isinstance(f, str) and f != "Tổng" and f not in folders and f != "_FOLDER_SET_":   # [ADDED]
                folders.append(f)                    # [ADDED]
        if "Tổng" in folders:
            folders.remove("Tổng") # Loại bỏ thư mục đặc biệt 'Tổng' khỏi danh sách
        return sorted(folders) # Trả về danh sách thư mục đã sắp xếp

    def save_folder_map(self):
        # [MODIFIED] Luôn ghi danh sách folder vào key _FOLDER_SET_ [ADDED]
        self.folder_map["_FOLDER_SET_"] = self.folders  # Lưu list trực tiếp, không dùng json.dumps
        try:
            with open(self.FOLDER_MAP_FILE, "w", encoding="utf-8") as f:
                json.dump(self.folder_map, f, ensure_ascii=False, indent=2) # Lưu map thư mục ra file
        except Exception as e:
            print(f"[ERROR] Lỗi khi lưu folder_map: {e}")

    def init_ui(self):
        main_layout = QVBoxLayout(self) # Changed to QVBoxLayout
        main_layout.setContentsMargins(0, 0, 0, 0) # Xóa lề ngoài cùng
        main_layout.setSpacing(0) # Xóa khoảng cách ngoài cùng

        # Layout cấp cao nhất cho hai panel chính (Danh sách thư mục và Danh sách tài khoản)
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0) # Xóa lề
        content_layout.setSpacing(0) # Xóa khoảng cách

        # Panel TRÁI (Quản lý thư mục và bảng thư mục) - 35% chiều rộng
        folder_list_panel = QVBoxLayout()
        folder_list_panel.setContentsMargins(10, 10, 5, 5)
        folder_list_panel.setSpacing(8)

        # Khu vực thêm thư mục mới
        add_folder_layout = QHBoxLayout()
        self.folder_name_input = QLineEdit()
        self.folder_name_input.setPlaceholderText("Tên thư mục") # Gợi ý nhập tên thư mục
        self.folder_name_input.returnPressed.disconnect()
        self.folder_name_input.returnPressed.connect(self.save_folder) # Đảm bảo không gán nhiều lần
        add_folder_layout.addWidget(self.folder_name_input)

        btn_add_folder_top = QPushButton("LƯU") # Nút thêm thư mục
        btn_add_folder_top.setFixedSize(40, 30) # Kích thước nhỏ cho nút
        btn_add_folder_top.setStyleSheet("QPushButton { font-size: 18px; font-weight: bold; }") # Style cho nút
        # Đảm bảo khi thêm thư mục thì lưu luôn folder_map
        def add_folder_and_save():
            self.save_folder()
        btn_add_folder_top.clicked.connect(add_folder_and_save)
        add_folder_layout.addWidget(btn_add_folder_top)
        add_folder_layout.addStretch() # Đẩy input và nút sang trái
        folder_list_panel.addLayout(add_folder_layout)

        lbl_folder_list = QLabel("Danh Sách Thư Mục") # Tiêu đề bảng thư mục
        lbl_folder_list.setAlignment(Qt.AlignmentFlag.AlignCenter)
        folder_list_panel.addWidget(lbl_folder_list)

        self.folder_table = QTableWidget()
        self.folder_table.setColumnCount(2)
        self.folder_table.setHorizontalHeaderLabels(["STT", "Tên nhóm thư mục"])
        # Thiết lập font cho tiêu đề bảng thư mục
        header_font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        self.folder_table.horizontalHeader().setFont(header_font)
        # Thiết lập font cho dữ liệu trong bảng thư mục
        table_data_font = QFont("Segoe UI", 10, QFont.Weight.Normal)
        self.folder_table.setFont(table_data_font)

        self.folder_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.folder_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.folder_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.folder_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.folder_table.itemChanged.connect(self.handle_folder_table_item_changed)
        self.folder_table.cellClicked.connect(self.on_folder_selected_in_table) # Bắt sự kiện chọn thư mục
        self.folder_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.folder_table.customContextMenuRequested.connect(self.show_folder_context_menu)

        self.folder_table.horizontalHeader().setFixedHeight(40)
        folder_list_panel.addWidget(self.folder_table)

        content_layout.addLayout(folder_list_panel, 35) # 35% chiều rộng panel trái
        # RIGHT Panel (Account List and Folder Assignment Controls) - 65% width
        account_list_panel = QVBoxLayout()
        account_list_panel.setContentsMargins(5, 10, 10, 5)
        account_list_panel.setSpacing(8)

        # Search bar for accounts
        account_search_layout = QHBoxLayout()
        self.account_search_input = QLineEdit()
        self.account_search_input.setPlaceholderText("Tìm kiếm tài khoản...")
        self.account_search_input.textChanged.connect(self.filter_accounts_in_dialog)
        account_search_layout.addWidget(self.account_search_input)
        account_list_panel.addLayout(account_search_layout)

        lbl_account_list = QLabel("Danh Sách Tài Khoản")
        lbl_account_list.setAlignment(Qt.AlignmentFlag.AlignCenter)
        account_list_panel.addWidget(lbl_account_list)

        self.account_table = QTableWidget()
        self.account_table.setColumnCount(6) # STT, Số điện thoại, Mật khẩu 2FA, Username, ID, Nhóm hiện tại
        self.account_table.setHorizontalHeaderLabels(["STT", "Số điện thoại", "Mật khẩu 2FA", "Username", "ID", "Nhóm hiện tại"])
        # Thiết lập font cho tiêu đề bảng tài khoản
        self.account_table.horizontalHeader().setFont(header_font)

        # Thiết lập font cho dữ liệu trong bảng tài khoản
        self.account_table.setFont(table_data_font)

        self.account_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.account_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Số điện thoại
        self.account_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Mật khẩu 2FA
        self.account_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Username
        self.account_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # ID
        self.account_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)           # Nhóm hiện tại
        self.account_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.account_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.account_table.itemChanged.connect(self.handle_account_table_item_changed) # For checkbox changes
        self.account_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.account_table.customContextMenuRequested.connect(self.show_account_context_menu)  # Hiển thị menu ngữ cảnh cho tài khoản
        self.account_table.verticalHeader().setVisible(False) # Hide row numbers

        self.account_table.horizontalHeader().setFixedHeight(40)
        account_list_panel.addWidget(self.account_table)

        content_layout.addLayout(account_list_panel, 65) # 65% chiều rộng

        main_layout.addLayout(content_layout, 8) # Chiếm 80% chiều cao cửa sổ

        # Style header xanh đậm, chữ trắng, in đậm cho cả hai bảng
        header_style = (
            "QHeaderView::section {"
            "background-color: #1976D2;"
            "color: white;"
            "font-weight: bold;"
            "font-size: 14px;"
            "border: 1px solid #bbb;"
            "padding: 4px;"
            "}"
        )
        self.folder_table.horizontalHeader().setStyleSheet(header_style)
        self.account_table.horizontalHeader().setStyleSheet(header_style)
        self.folder_table.horizontalHeader().setFixedHeight(40)
        self.account_table.horizontalHeader().setFixedHeight(40)

        # Ẩn hoàn toàn cột verticalHeader ở bảng danh sách thư mục
        self.folder_table.verticalHeader().setVisible(False)
        # Ẩn hoàn toàn cột verticalHeader ở bảng tài khoản (nếu chưa có)
        self.account_table.verticalHeader().setVisible(False)

        self.load_folders_on_startup()

    def update_folder_table(self):
        # Cập nhật lại bảng danh sách thư mục dựa trên self.folders
        self.folder_table.blockSignals(True)  # Ngăn callback lặp khi cập nhật bảng
        self.folder_table.setRowCount(len(self.folders))
        for row_idx, folder_name in enumerate(self.folders):
            self.folder_table.setItem(row_idx, 0, QTableWidgetItem(str(row_idx + 1))) # STT
            self.folder_table.setItem(row_idx, 1, QTableWidgetItem(folder_name)) # Tên thư mục
        self.folder_table.blockSignals(False)

    def save_folder(self):
        folder_name = self.folder_name_input.text().strip()
        if not folder_name:
            QMessageBox.warning(self, "Lỗi", "Tên thư mục không được để trống.")
            return

        if folder_name in self.folders:
            QMessageBox.warning(self, "Lỗi", "Thư mục đã tồn tại.")
            return

        self.folders.append(folder_name)
        self.folders.sort()  # Keep sorted
        self.folder_map["_FOLDER_SET_"] = self.folders  # Lưu list trực tiếp
        self.save_folder_map()  # Lưu vào file

        # Load lại từ file và cập nhật giao diện
        self.folders = self.load_folders()
        self.update_folder_table()

        self.folder_name_input.clear()
        QMessageBox.information(self, "Thành công", f"Đã lưu thư mục '{folder_name}'.")
        self.folders_updated.emit()  # Phát tín hiệu cập nhật

    def load_folders_on_startup(self):
        # Load folders from file on startup
        loaded_map = self.load_folder_map()
        if loaded_map:
            self.folder_map = loaded_map
            self.folders = self.load_folders()
            self.update_folder_table()
            self.update_account_table()

    def edit_folder(self):
        selected_rows = self.folder_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Sửa thư mục", "Vui lòng chọn một thư mục để sửa.")
            return

        row = selected_rows[0].row()
        item = self.folder_table.item(row, 1)
        old_folder_name = item.text() if item else ""

        new_folder_name, ok = QInputDialog.getText(self, "Sửa thư mục", "Tên thư mục mới:", QLineEdit.EchoMode.Normal, old_folder_name)
        if ok and new_folder_name.strip():
            new_folder_name = new_folder_name.strip()
            if new_folder_name == old_folder_name:
                return  # No change

            if new_folder_name in self.folders:
                QMessageBox.warning(self, "Lỗi", "Thư mục mới đã tồn tại.")
                return

            # Update folder name in self.folders
            try:
                index = self.folders.index(old_folder_name)
                self.folders[index] = new_folder_name
                self.folders.sort()  # Keep sorted
            except ValueError:
                pass  # Should not happen if selected from table

            # Update folder_map for accounts that were in the old folder
            for username, folder in self.folder_map.items():
                if folder == old_folder_name:
                    self.folder_map[username] = new_folder_name
            self.folder_map["_FOLDER_SET_"] = self.folders
            self.update_folder_table()
            QMessageBox.information(self, "Thành công", f"Đã sửa thư mục '{old_folder_name}' thành '{new_folder_name}'.")
            self.folders_updated.emit()  # Phát tín hiệu cập nhật
            self.save_folder_map()  # Ensure data is saved to file

    def delete_folder(self):
        selected_rows = self.folder_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Xóa thư mục", "Vui lòng chọn một thư mục để xóa.")
            return

        row = selected_rows[0].row()
        item = self.folder_table.item(row, 1)
        folder_to_delete = item.text() if item else ""

        if folder_to_delete == "Tổng":
            QMessageBox.warning(self, "Lỗi", "Không thể xóa thư mục 'Tổng'.")
            return

        # Confirm deletion
        reply = QMessageBox.question(self, 'Xóa thư mục', f"Bạn có chắc chắn muốn xóa thư mục '{folder_to_delete}'? Tất cả tài khoản trong thư mục này sẽ được chuyển về 'Tổng'.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            self.folders.remove(folder_to_delete)
            self.folder_map["_FOLDER_SET_"] = self.folders
            self.update_folder_table()

            # Update folder_map for accounts that were in the deleted folder
            for username, folder in self.folder_map.items():
                if folder == folder_to_delete:
                    self.folder_map[username] = "Tổng"  # Assign to default folder
            self.update_account_table()
            QMessageBox.information(self, "Thành công", f"Đã xóa thư mục '{folder_to_delete}'.")
            self.folders_updated.emit()  # Phát tín hiệu cập nhật
            self.save_folder_map()  # Ensure data is saved to file

    def handle_folder_table_item_changed(self, item: QTableWidgetItem) -> None:
        # Placeholder for any future item change handling if editing is enabled
        pass

    def on_folder_selected_in_table(self, row: int, column: int) -> None:
        item = self.folder_table.item(row, 1)
        folder_name = item.text() if item else ""
        self.selected_folder_in_table = folder_name
        self.filter_accounts_in_dialog()

    def show_folder_context_menu(self, pos: QPoint) -> None:
        menu = QMenu(self.folder_table)
        action_delete = menu.addAction("Xóa thư mục")
        action_edit = menu.addAction("Chỉnh sửa thư mục")
        action = menu.exec(self.folder_table.viewport().mapToGlobal(pos))
        row = self.folder_table.indexAt(pos).row()
        if row < 0:
            return
        if action == action_delete:
            self.delete_folder_by_row(row)
        elif action == action_edit:
            self.edit_folder_by_row(row)
    def show_account_context_menu(self, pos: QPoint):
        menu = QMenu(self.account_table)
        action_move = menu.addAction("Chuyển thư mục")
        action_remove = menu.addAction("Xóa khỏi thư mục")
        action = menu.exec(self.account_table.viewport().mapToGlobal(pos))
        row = self.account_table.indexAt(pos).row()
        if row < 0:
            return
        if action == action_move:
            self.move_account_to_folder(row)
        elif action == action_remove:
            self.remove_account_from_folder(row)

    def filter_accounts_in_dialog(self):
        search_text = self.account_search_input.text().strip().lower()
        filtered_accounts: List[Dict[str, Union[str, bool]]] = []

        for account in self.accounts:
            username = str(account.get("username", "")).lower()
            current_folder = str(self.folder_map.get(str(account.get("username", "")), "Tổng")).lower()

            # Filter by search text
            if search_text and search_text not in username and search_text not in current_folder:
                continue

            # Filter by selected folder in folder table
            if self.selected_folder_in_table != "Tất cả" and self.folder_map.get(str(account.get("username", "")), "Tổng") != self.selected_folder_in_table:
                continue

            filtered_accounts.append(account)

        self.update_account_table(filtered_accounts)

    def handle_account_table_item_changed(self, item: QTableWidgetItem):
        if item.column() == 0: # Checkbox column
            row = item.row()
            username_item = self.account_table.item(row, 1)
            username = username_item.text() if username_item else ""
            for account in self.accounts:
                if account.get("username") == username:
                    account["selected_in_dialog"] = str(item.checkState() == Qt.CheckState.Checked)
                    break

    def assign_selected_accounts_to_folder(self):
        selected_folder = self.selected_folder_in_table
        if selected_folder == "Tất cả" or selected_folder == "Tất cả ":
            QMessageBox.warning(self, "Gán thư mục", "Vui lòng chọn một thư mục cụ thể từ danh sách thư mục để gán.")
            return

        selected_accounts_for_assignment: List[Dict[str, Union[str, bool]]] = []
        for account in self.accounts:
            if account.get("selected_in_dialog", "False") == "True":
                selected_accounts_for_assignment.append(account)

        if not selected_accounts_for_assignment:
            QMessageBox.warning(self, "Gán thư mục", "Vui lòng chọn ít nhất một tài khoản để gán.")
            return

        for account in selected_accounts_for_assignment:
            self.folder_map[str(account.get("username", ""))] = selected_folder
            account["selected_in_dialog"] = "False" # Deselect after assignment

        self.folders_updated.emit() # Notify AccountManagementTab about folder changes
        QMessageBox.information(self, "Gán thư mục", f"Đã gán {len(selected_accounts_for_assignment)} tài khoản vào thư mục '{selected_folder}'.")
        self.update_account_table()
        self.save_folder_map()

    def unassign_selected_accounts(self):
        selected_accounts_for_unassignment: List[Dict[str, Union[str, bool]]] = []
        for account in self.accounts:
            if account.get("selected_in_dialog", "False") == "True":
                selected_accounts_for_unassignment.append(account)

        if not selected_accounts_for_unassignment:
            QMessageBox.warning(self, "Bỏ gán thư mục", "Vui lòng chọn ít nhất một tài khoản để bỏ gán.")
            return

        for account in selected_accounts_for_unassignment:
            if str(account.get("username", "")) in self.folder_map:
                self.folder_map[str(account.get("username", ""))] = "Tổng"
            account["selected_in_dialog"] = "False" # Deselect after unassignment

        self.folders_updated.emit() # Notify AccountManagementTab about folder changes
        QMessageBox.information(self, "Bỏ gán thư mục", f"Đã bỏ gán {len(selected_accounts_for_unassignment)} tài khoản khỏi thư mục.")
        self.update_account_table()
        self.save_folder_map()

    def update_account_table(self, accounts_to_display: Optional[List[Dict[str, Union[str, bool]]]] = None) -> None:
        if accounts_to_display is None:
            accounts_to_display = self.accounts

        self.account_table.blockSignals(True) # Block signals during update
        self.account_table.setRowCount(len(accounts_to_display))
        for row_idx, account in enumerate(accounts_to_display):
            username = str(account.get("username", ""))
            telegram_2fa = account.get("telegram_2fa", "") or account.get("two_fa_password", "") or account.get("password_2fa", "") or account.get("twofa", "") or "Chưa có 2FA"
            current_folder = str(self.folder_map.get(username, "Tổng")) # Get current folder for the account

            # Cột 0: STT
            self.account_table.setItem(row_idx, 0, QTableWidgetItem(str(row_idx + 1)))
            # Cột 1: Số điện thoại
            self.account_table.setItem(row_idx, 1, QTableWidgetItem(username))
            # Cột 2: Mật khẩu 2FA
            self.account_table.setItem(row_idx, 2, QTableWidgetItem(telegram_2fa))
            # Cột 3: Username
            account_username = account.get("telegram_username", "") or account.get("username_telegram", "") or account.get("tg_username", "") or "Chưa có username"
            self.account_table.setItem(row_idx, 3, QTableWidgetItem(account_username))
            # Cột 4: ID
            account_id = account.get("telegram_id", "") or account.get("id_telegram", "") or account.get("tg_id", "") or account.get("user_id", "") or "Chưa có ID"
            self.account_table.setItem(row_idx, 4, QTableWidgetItem(account_id))
            # Cột 5: Nhóm hiện tại
            self.account_table.setItem(row_idx, 5, QTableWidgetItem(current_folder))

        self.account_table.blockSignals(False) # Unblock signals

    def transfer_accounts_to_folder(self):
        # Implement the logic to transfer accounts to a folder
        pass 

    def delete_folder_by_row(self, row: int) -> None:
        # Xóa thư mục theo dòng
        item = self.folder_table.item(row, 1)
        folder_name = item.text() if item else ""
        if not folder_name:
            return
        if folder_name == "Tổng":
            QMessageBox.warning(self, "Lỗi", "Không thể xóa thư mục 'Tổng'.")
            return
        reply = QMessageBox.question(self, 'Xóa thư mục', f"Bạn có chắc chắn muốn xóa thư mục '{folder_name}'? Tất cả tài khoản trong thư mục này sẽ được chuyển về 'Tổng'.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if folder_name in self.folders:
                self.folders.remove(folder_name)
            self.folder_map["_FOLDER_SET_"] = self.folders
            # Chuyển các account về 'Tổng'
            for username, folder in self.folder_map.items():
                if folder == folder_name:
                    self.folder_map[username] = "Tổng"
            self.update_folder_table()
            self.update_account_table()
            QMessageBox.information(self, "Thành công", f"Đã xóa thư mục '{folder_name}'.")
            self.folders_updated.emit()
            self.save_folder_map()

    def edit_folder_by_row(self, row: int):
        item = self.folder_table.item(row, 1)
        old_folder_name = item.text() if item else ""
        if not old_folder_name:
            return
        new_folder_name, ok = QInputDialog.getText(self, "Sửa thư mục", "Tên thư mục mới:", QLineEdit.EchoMode.Normal, old_folder_name)
        if ok and new_folder_name.strip():
            new_folder_name = new_folder_name.strip()
            if new_folder_name == old_folder_name:
                return
            if new_folder_name in self.folders:
                QMessageBox.warning(self, "Lỗi", "Thư mục mới đã tồn tại.")
                return
            try:
                index = self.folders.index(old_folder_name)
                self.folders[index] = new_folder_name
                self.folders.sort()
            except ValueError:
                pass
            for username, folder in self.folder_map.items():
                if folder == old_folder_name:
                    self.folder_map[username] = new_folder_name
            self.folder_map["_FOLDER_SET_"] = self.folders
            self.update_folder_table()
            self.update_account_table()
            QMessageBox.information(self, "Thành công", f"Đã sửa thư mục '{old_folder_name}' thành '{new_folder_name}'.")
            self.folders_updated.emit()
            self.save_folder_map()

    def move_account_to_folder(self, row: int):
        username_item = self.account_table.item(row, 1)  # Cột 1 là số điện thoại (username)
        username = username_item.text() if username_item else ""
        if not username:
            return
        # Hiện dialog chọn thư mục mới
        folder_list = [f for f in self.folders if f != "Tổng"]
        if not folder_list:
            QMessageBox.warning(self, "Chuyển thư mục", "Chưa có thư mục nào để chuyển.")
            return
        current_folder = self.folder_map.get(username, "Tổng")
        new_folder, ok = QInputDialog.getItem(self, "Chuyển thư mục", f"Chọn thư mục mới cho tài khoản '{username}':", folder_list, editable=False)
        if ok and new_folder and new_folder != current_folder:
            self.folder_map[username] = new_folder
            self.update_account_table()
            self.save_folder_map()
            QMessageBox.information(self, "Chuyển thư mục", f"Đã chuyển tài khoản '{username}' sang thư mục '{new_folder}'.")
            self.folders_updated.emit()

    def remove_account_from_folder(self, row: int):
        username_item = self.account_table.item(row, 1)  # Cột 1 là số điện thoại (username)
        username = username_item.text() if username_item else ""
        if not username:
            return
        if self.folder_map.get(username, "Tổng") == "Tổng":
            QMessageBox.information(self, "Bỏ gán thư mục", f"Tài khoản '{username}' đã ở thư mục 'Tổng'.")
            return
        self.folder_map[username] = "Tổng"
        self.update_account_table()
        self.save_folder_map()
        QMessageBox.information(self, "Bỏ gán thư mục", f"Đã bỏ gán tài khoản '{username}' khỏi thư mục.")
        self.folders_updated.emit()

    def closeEvent(self, event: QCloseEvent):
        # Đảm bảo luôn lưu folder_map trước khi đóng dialog
        try:
            self.save_folder_map()
        except Exception as e:
            print(f"[ERROR] Lưu folder_map khi đóng dialog: {e}")
        super().closeEvent(event) 

    def load_folder_map(self):
        if os.path.exists(self.FOLDER_MAP_FILE):
            with open(self.FOLDER_MAP_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return None 
