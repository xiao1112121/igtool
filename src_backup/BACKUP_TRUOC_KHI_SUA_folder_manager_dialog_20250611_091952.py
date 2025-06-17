from PySide6.QtWidgets import (QDialog, QHBoxLayout, QVBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QLineEdit, QLabel, QMessageBox, QMenu, QHeaderView, QInputDialog, QWidget, QAbstractItemView)
from PySide6.QtCore import Qt, Signal
import os
import json

class FolderManagerDialog(QDialog):
    folders_updated = Signal() # Tín hiệu để thông báo khi danh mục được cập nhật

    def __init__(self, accounts, folder_map, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Quản lý Thư Mục Tài Khoản")
        self.setGeometry(100, 100, 1000, 700) # Tăng kích thước cửa sổ

        self.accounts = accounts # Danh sách tài khoản từ AccountManagementTab
        self.folder_map = folder_map # Ánh xạ username -> folder
        self.folders = self.load_folders() # Danh sách các thư mục duy nhất
        self.selected_folder_in_table = "Tất cả" # Theo dõi thư mục đang chọn trong bảng thư mục

        self.init_ui()
        self.update_folder_table()
        self.update_account_table() # Cập nhật bảng tài khoản khi khởi tạo

    def load_folders(self):
        # Tải danh sách thư mục từ folder_map hoặc tạo mới nếu chưa có
        unique_folders = set(self.folder_map.values())
        if "Tổng" in unique_folders:
            unique_folders.remove("Tổng") # "Tổng" is a default category, not a user-created folder
        return sorted(list(unique_folders))

    def save_folder_map(self):
        # Lưu folder_map vào file hoặc cập nhật AccountsManagementTab nếu cần
        # For now, we will just update the AccountManagementTab later.
        pass

    def init_ui(self):
        main_layout = QHBoxLayout(self)

        # LEFT Panel (Account List and Folder Assignment Controls)
        left_account_panel = QVBoxLayout() # Đổi tên cho rõ ràng hơn
        
        # Search bar for accounts
        account_search_layout = QHBoxLayout()
        self.account_search_input = QLineEdit()
        self.account_search_input.setPlaceholderText("Tìm kiếm tài khoản...")
        self.account_search_input.textChanged.connect(self.filter_accounts_in_dialog)
        account_search_layout.addWidget(self.account_search_input)
        left_account_panel.addLayout(account_search_layout)

        lbl_account_list = QLabel("Danh Sách Tài Khoản")
        lbl_account_list.setAlignment(Qt.AlignCenter)
        left_account_panel.addWidget(lbl_account_list)

        self.account_table = QTableWidget()
        self.account_table.setColumnCount(4) # Chọn, STT, Tên người dùng, Thư mục
        self.account_table.setHorizontalHeaderLabels(["Chọn", "STT", "Tên người dùng", "Thư mục"])
        self.account_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.account_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.account_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.account_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch) # Cột thư mục
        self.account_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.account_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.account_table.itemChanged.connect(self.handle_account_table_item_changed) # For checkbox changes
        self.account_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.account_table.customContextMenuRequested.connect(self.show_account_context_menu) # Context menu for accounts

        left_account_panel.addWidget(self.account_table)

        # Buttons for assigning/unassigning accounts
        assign_buttons_layout = QHBoxLayout()
        btn_assign_selected = QPushButton("Gán thư mục đã chọn")
        btn_assign_selected.clicked.connect(self.assign_selected_accounts_to_folder)
        assign_buttons_layout.addWidget(btn_assign_selected)

        btn_unassign_selected = QPushButton("Bỏ gán thư mục")
        btn_unassign_selected.clicked.connect(self.unassign_selected_accounts)
        assign_buttons_layout.addWidget(btn_unassign_selected)
        left_account_panel.addLayout(assign_buttons_layout)

        main_layout.addLayout(left_account_panel, 2) # Proportion for account panel (e.g., 2/3 of width)

        # RIGHT Panel (Folder Management Controls and Folder List Table)
        right_folder_panel = QVBoxLayout() # Đổi tên cho rõ ràng hơn
        right_folder_panel.setSpacing(10)

        # Add new folder section
        add_folder_layout = QHBoxLayout()
        btn_add = QPushButton("+")
        btn_add.setFixedSize(30, 30)
        btn_add.clicked.connect(self.add_folder)
        self.folder_name_input = QLineEdit()
        self.folder_name_input.setPlaceholderText("Tên danh mục")
        self.folder_name_input.returnPressed.connect(self.add_folder)
        add_folder_layout.addWidget(btn_add)
        add_folder_layout.addWidget(self.folder_name_input)
        right_folder_panel.addLayout(add_folder_layout)

        # Edit and Delete buttons
        btn_edit = QPushButton("Sửa danh mục")
        btn_edit.clicked.connect(self.edit_folder)
        right_folder_panel.addWidget(btn_edit)

        btn_delete = QPushButton("Xóa danh mục")
        btn_delete.clicked.connect(self.delete_folder)
        right_folder_panel.addWidget(btn_delete)

        lbl_folder_list = QLabel("Danh Sách Danh Mục")
        lbl_folder_list.setAlignment(Qt.AlignCenter)
        right_folder_panel.addWidget(lbl_folder_list)

        self.folder_table = QTableWidget()
        self.folder_table.setColumnCount(2)
        self.folder_table.setHorizontalHeaderLabels(["STT", "Tên Danh Mục"])
        self.folder_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.folder_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.folder_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.folder_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.folder_table.itemChanged.connect(self.handle_folder_table_item_changed)
        self.folder_table.cellClicked.connect(self.on_folder_selected_in_table) # New signal connection for folder selection
        self.folder_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.folder_table.customContextMenuRequested.connect(self.show_folder_context_menu)

        right_folder_panel.addWidget(self.folder_table)
        right_folder_panel.addStretch() # Push folder controls to top

        main_layout.addLayout(right_folder_panel, 1) # Proportion for folder panel (e.g., 1/3 of width)

    def update_folder_table(self):
        self.folders = self.load_folders() # Reload to ensure it's up-to-date
        self.folder_table.setRowCount(len(self.folders))
        for row_idx, folder_name in enumerate(self.folders):
            self.folder_table.setItem(row_idx, 0, QTableWidgetItem(str(row_idx + 1))) # STT
            self.folder_table.setItem(row_idx, 1, QTableWidgetItem(folder_name))
            
    def add_folder(self):
        folder_name = self.folder_name_input.text().strip()
        if not folder_name:
            QMessageBox.warning(self, "Lỗi", "Tên danh mục không được để trống.")
            return

        if folder_name in self.folders:
            QMessageBox.warning(self, "Lỗi", "Danh mục đã tồn tại.")
            return

        self.folders.append(folder_name)
        self.folders.sort() # Keep sorted
        self.update_folder_table()
        self.folder_name_input.clear()
        QMessageBox.information(self, "Thành công", f"Đã thêm danh mục '{folder_name}'.")
        self.folders_updated.emit() # Phát tín hiệu cập nhật

    def edit_folder(self):
        selected_rows = self.folder_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Sửa danh mục", "Vui lòng chọn một danh mục để sửa.")
            return

        row = selected_rows[0].row()
        old_folder_name = self.folder_table.item(row, 1).text()

        new_folder_name, ok = QInputDialog.getText(self, "Sửa danh mục", "Tên danh mục mới:", 
                                                 QLineEdit.Normal, old_folder_name)
        if ok and new_folder_name.strip():
            new_folder_name = new_folder_name.strip()
            if new_folder_name == old_folder_name:
                return # No change

            if new_folder_name in self.folders:
                QMessageBox.warning(self, "Lỗi", "Danh mục mới đã tồn tại.")
                return

            # Update folder name in self.folders
            try:
                index = self.folders.index(old_folder_name)
                self.folders[index] = new_folder_name
                self.folders.sort() # Keep sorted
            except ValueError:
                pass # Should not happen if selected from table

            # Update folder_map for accounts that were in the old folder
            for username, folder in self.folder_map.items():
                if folder == old_folder_name:
                    self.folder_map[username] = new_folder_name
            
            self.update_folder_table()
            QMessageBox.information(self, "Thành công", f"Đã sửa danh mục '{old_folder_name}' thành '{new_folder_name}'.")
            self.folders_updated.emit() # Phát tín hiệu cập nhật

    def delete_folder(self):
        selected_rows = self.folder_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Xóa danh mục", "Vui lòng chọn một danh mục để xóa.")
            return

        row = selected_rows[0].row()
        folder_to_delete = self.folder_table.item(row, 1).text()

        reply = QMessageBox.question(self, 'Xóa danh mục', 
                                     f"Bạn có chắc chắn muốn xóa danh mục '{folder_to_delete}'? "
                                     "Tất cả tài khoản trong danh mục này sẽ được chuyển về 'Tổng'.",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            # Remove from self.folders
            self.folders.remove(folder_to_delete)
            
            # Reassign accounts in this folder to "Tổng"
            for username, folder in self.folder_map.items():
                if folder == folder_to_delete:
                    self.folder_map[username] = "Tổng"
            
            self.update_folder_table()
            QMessageBox.information(self, "Thành công", f"Đã xóa danh mục '{folder_to_delete}'.")
            self.folders_updated.emit() # Phát tín hiệu cập nhật

    def handle_folder_table_item_changed(self, item):
        # Placeholder for any future item change handling if editing is enabled
        pass 

    def on_folder_selected_in_table(self, row, column):
        folder_name = self.folder_table.item(row, 1).text()
        self.selected_folder_in_table = folder_name
        self.filter_accounts_in_dialog()

    def show_folder_context_menu(self, position):
        # Placeholder for folder context menu
        pass

    def show_account_context_menu(self, position):
        # Placeholder for account context menu
        pass

    def filter_accounts_in_dialog(self):
        search_text = self.account_search_input.text().strip().lower()
        filtered_accounts = []

        for account in self.accounts:
            username = account.get("username", "").lower()
            current_folder = self.folder_map.get(account.get("username"), "Tổng").lower()
            
            # Filter by search text
            if search_text and search_text not in username and search_text not in current_folder:
                continue

            # Filter by selected folder in folder table
            if self.selected_folder_in_table != "Tất cả" and self.folder_map.get(account.get("username"), "Tổng") != self.selected_folder_in_table:
                continue

            filtered_accounts.append(account)
        
        self.update_account_table(filtered_accounts)

    def handle_account_table_item_changed(self, item):
        if item.column() == 0: # Checkbox column
            row = item.row()
            username = self.account_table.item(row, 2).text()
            for account in self.accounts:
                if account.get("username") == username:
                    account["selected_in_dialog"] = item.checkState() == Qt.Checked
                    break

    def assign_selected_accounts_to_folder(self):
        selected_folder = self.selected_folder_in_table
        if selected_folder == "Tất cả" or selected_folder == "Tổng":
            QMessageBox.warning(self, "Gán thư mục", "Vui lòng chọn một danh mục cụ thể từ danh sách thư mục để gán.")
            return

        selected_accounts_for_assignment = []
        for account in self.accounts:
            if account.get("selected_in_dialog", False):
                selected_accounts_for_assignment.append(account)

        if not selected_accounts_for_assignment:
            QMessageBox.warning(self, "Gán thư mục", "Vui lòng chọn ít nhất một tài khoản để gán.")
            return

        for account in selected_accounts_for_assignment:
            self.folder_map[account.get("username")] = selected_folder
            account["selected_in_dialog"] = False # Deselect after assignment

        self.folders_updated.emit() # Notify AccountManagementTab about folder changes
        QMessageBox.information(self, "Gán thư mục", f"Đã gán {len(selected_accounts_for_assignment)} tài khoản vào thư mục '{selected_folder}'.")
        self.update_account_table()

    def unassign_selected_accounts(self):
        selected_accounts_for_unassignment = []
        for account in self.accounts:
            if account.get("selected_in_dialog", False):
                selected_accounts_for_unassignment.append(account)
        
        if not selected_accounts_for_unassignment:
            QMessageBox.warning(self, "Bỏ gán thư mục", "Vui lòng chọn ít nhất một tài khoản để bỏ gán.")
            return

        for account in selected_accounts_for_unassignment:
            if account.get("username") in self.folder_map:
                self.folder_map[account.get("username")] = "Tổng"
            account["selected_in_dialog"] = False # Deselect after unassignment
        
        self.folders_updated.emit() # Notify AccountManagementTab about folder changes
        QMessageBox.information(self, "Bỏ gán thư mục", f"Đã bỏ gán {len(selected_accounts_for_unassignment)} tài khoản khỏi thư mục.")
        self.update_account_table()

    def update_account_table(self, accounts_to_display=None):
        if accounts_to_display is None:
            accounts_to_display = self.accounts

        self.account_table.blockSignals(True) # Block signals during update
        self.account_table.setRowCount(len(accounts_to_display))
        for row_idx, account in enumerate(accounts_to_display):
            username = account.get("username", "")
            current_folder = self.folder_map.get(username, "Tổng") # Get current folder for the account

            # Checkbox
            chk_box_item = QTableWidgetItem()
            chk_box_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            # Ensure the selected state in the dialog is maintained for checkboxes
            is_selected_in_dialog = account.get("selected_in_dialog", False) # New temporary key for dialog selection
            chk_box_item.setCheckState(Qt.Checked if is_selected_in_dialog else Qt.Unchecked)
            self.account_table.setItem(row_idx, 0, chk_box_item)

            self.account_table.setItem(row_idx, 1, QTableWidgetItem(str(row_idx + 1))) # STT
            self.account_table.setItem(row_idx, 2, QTableWidgetItem(username))
            self.account_table.setItem(row_idx, 3, QTableWidgetItem(current_folder)) # Hiển thị thư mục của tài khoản
        
        self.account_table.blockSignals(False) # Unblock signals

    def update_folder_table(self):
        self.folders = self.load_folders() # Reload to ensure it's up-to-date
        self.folder_table.setRowCount(len(self.folders))
        for row_idx, folder_name in enumerate(self.folders):
            self.folder_table.setItem(row_idx, 0, QTableWidgetItem(str(row_idx + 1))) # STT
            self.folder_table.setItem(row_idx, 1, QTableWidgetItem(folder_name))
            
    def add_folder(self):
        folder_name = self.folder_name_input.text().strip()
        if not folder_name:
            QMessageBox.warning(self, "Lỗi", "Tên danh mục không được để trống.")
            return

        if folder_name in self.folders:
            QMessageBox.warning(self, "Lỗi", "Danh mục đã tồn tại.")
            return

        self.folders.append(folder_name)
        self.folders.sort() # Keep sorted
        self.update_folder_table()
        self.folder_name_input.clear()
        QMessageBox.information(self, "Thành công", f"Đã thêm danh mục '{folder_name}'.")
        self.folders_updated.emit() # Phát tín hiệu cập nhật

    def edit_folder(self):
        selected_rows = self.folder_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Sửa danh mục", "Vui lòng chọn một danh mục để sửa.")
            return

        row = selected_rows[0].row()
        old_folder_name = self.folder_table.item(row, 1).text()

        new_folder_name, ok = QInputDialog.getText(self, "Sửa danh mục", "Tên danh mục mới:", 
                                                 QLineEdit.Normal, old_folder_name)
        if ok and new_folder_name.strip():
            new_folder_name = new_folder_name.strip()
            if new_folder_name == old_folder_name:
                return # No change

            if new_folder_name in self.folders:
                QMessageBox.warning(self, "Lỗi", "Danh mục mới đã tồn tại.")
                return

            # Update folder name in self.folders
            try:
                index = self.folders.index(old_folder_name)
                self.folders[index] = new_folder_name
                self.folders.sort() # Keep sorted
            except ValueError:
                pass # Should not happen if selected from table

            # Update folder_map for accounts that were in the old folder
            for username, folder in self.folder_map.items():
                if folder == old_folder_name:
                    self.folder_map[username] = new_folder_name
            
            self.update_folder_table()
            QMessageBox.information(self, "Thành công", f"Đã sửa danh mục '{old_folder_name}' thành '{new_folder_name}'.")
            self.folders_updated.emit() # Phát tín hiệu cập nhật

    def delete_folder(self):
        selected_rows = self.folder_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Xóa danh mục", "Vui lòng chọn một danh mục để xóa.")
            return

        row = selected_rows[0].row()
        folder_to_delete = self.folder_table.item(row, 1).text()

        reply = QMessageBox.question(self, 'Xóa danh mục', 
                                     f"Bạn có chắc chắn muốn xóa danh mục '{folder_to_delete}'? "
                                     "Tất cả tài khoản trong danh mục này sẽ được chuyển về 'Tổng'.",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            # Remove from self.folders
            self.folders.remove(folder_to_delete)
            
            # Reassign accounts in this folder to "Tổng"
            for username, folder in self.folder_map.items():
                if folder == folder_to_delete:
                    self.folder_map[username] = "Tổng"
            
            self.update_folder_table()
            QMessageBox.information(self, "Thành công", f"Đã xóa danh mục '{folder_to_delete}'.")
            self.folders_updated.emit() # Phát tín hiệu cập nhật

    def handle_folder_table_item_changed(self, item):
        # Placeholder for any future item change handling if editing is enabled
        pass 

    def show_folder_context_menu(self, position):
        # Implement the logic to show the context menu for a selected folder
        pass

    def show_account_context_menu(self, position):
        # Implement the logic to show the context menu for a selected account
        pass

    def handle_account_table_item_changed(self, item):
        # Implement the logic to handle account table item change
        pass

    def assign_selected_accounts_to_folder(self):
        # Implement the logic to assign selected accounts to a folder
        pass

    def unassign_selected_accounts(self):
        # Implement the logic to unassign selected accounts from a folder
        pass

    def update_account_table(self):
        # Implement the logic to update the account table
        pass 