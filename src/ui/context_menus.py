"""
Context Menu classes cho các tab trong ứng dụng
"""

from PySide6.QtWidgets import QMenu, QMessageBox, QInputDialog, QTableWidgetSelectionRange
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QGuiApplication
from functools import partial


class AccountContextMenu(QMenu):
    """Context menu đơn giản cho Account Management Tab"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

    def show_account_context_menu(self, pos):
        """Hiển thị context menu cho tài khoản"""
        index = self.parent.account_table.indexAt(pos)
        if not index.isValid():
            return

        row = index.row()
        menu = QMenu(self.parent)

        # --- Nhóm: Chọn / Bỏ chọn ---
        action_select = QAction("✅ Chọn dòng này", self.parent)
        action_deselect = QAction("❎ Bỏ chọn dòng này", self.parent)
        action_select_all = QAction("🔘 Chọn tất cả", self.parent)
        action_deselect_all = QAction("🚫 Bỏ chọn tất cả", self.parent)

        action_select.triggered.connect(lambda: self.select_account_row(row))
        action_deselect.triggered.connect(lambda: self.deselect_account_row(row))
        action_select_all.triggered.connect(self.select_all_account_rows)
        action_deselect_all.triggered.connect(self.deselect_all_account_rows)

        # --- Nhóm: Tác vụ tài khoản ---
        action_login = QAction("🔁 Đăng nhập lại", self.parent)
        action_browser = QAction("🚀 Mở trình duyệt", self.parent)
        action_proxy = QAction("🛠️ Sửa Proxy", self.parent)
        action_delete_session = QAction("🧼 Xóa Session", self.parent)
        action_delete = QAction("❌ Xóa tài khoản", self.parent)
        action_export = QAction("📤 Xuất thông tin", self.parent)
        action_copy = QAction("📋 Sao chép số điện thoại", self.parent)
        action_check = QAction("🧪 Kiểm tra hoạt động", self.parent)
        action_start = QAction("🤖 Chạy tương tác", self.parent)
        action_pause = QAction("⏸️ Tạm dừng tương tác", self.parent)

        # Gán hàm xử lý tương ứng
        action_login.triggered.connect(lambda: self.login_account(row))
        action_browser.triggered.connect(lambda: self.open_browser(row))
        action_proxy.triggered.connect(lambda: self.edit_proxy(row))
        action_delete_session.triggered.connect(lambda: self.delete_session(row))
        action_delete.triggered.connect(lambda: self.delete_account(row))
        action_export.triggered.connect(self.export_selected_accounts)
        action_copy.triggered.connect(lambda: self.copy_phone_number(row))
        action_check.triggered.connect(lambda: self.check_status(row))
        action_start.triggered.connect(lambda: self.start_interaction(row))
        action_pause.triggered.connect(lambda: self.pause_interaction(row))

        # --- Thêm các action vào menu ---
        menu.addActions([action_select, action_deselect, action_select_all, action_deselect_all])
        menu.addSeparator()
        menu.addActions([
            action_login, action_browser, action_proxy,
            action_delete_session, action_delete,
            action_export, action_copy, action_check,
            action_start, action_pause
        ])

        menu.exec_(self.parent.account_table.viewport().mapToGlobal(pos))

    # --- Các hàm xử lý selection ---
    def select_account_row(self, row):
        """Tick checkbox cho tất cả dòng được bôi đen"""
        from src.ui.account_management import CheckboxDelegate
        
        # Lấy tất cả dòng được bôi đen
        selected_ranges = self.parent.account_table.selectionModel().selectedRows()
        selected_rows = [index.row() for index in selected_ranges]
        
        # Nếu không có dòng nào được bôi đen, chỉ tick dòng hiện tại
        if not selected_rows:
            selected_rows = [row]
        
        # Tick checkbox cho tất cả dòng được chọn
        for selected_row in selected_rows:
            if selected_row < self.parent.account_table.rowCount():
                checkbox_item = self.parent.account_table.item(selected_row, 0)
                if checkbox_item:
                    checkbox_item.setData(CheckboxDelegate.CheckboxStateRole, True)
        
        self.parent.account_table.viewport().update()
        print(f"[DEBUG] Đã tick checkbox cho {len(selected_rows)} dòng: {selected_rows}")

    def deselect_account_row(self, row):
        """Bỏ tick checkbox cho tất cả dòng được bôi đen"""
        from src.ui.account_management import CheckboxDelegate
        
        # Lấy tất cả dòng được bôi đen
        selected_ranges = self.parent.account_table.selectionModel().selectedRows()
        selected_rows = [index.row() for index in selected_ranges]
        
        # Nếu không có dòng nào được bôi đen, chỉ bỏ tick dòng hiện tại
        if not selected_rows:
            selected_rows = [row]
        
        # Bỏ tick checkbox cho tất cả dòng được chọn
        for selected_row in selected_rows:
            if selected_row < self.parent.account_table.rowCount():
                checkbox_item = self.parent.account_table.item(selected_row, 0)
                if checkbox_item:
                    checkbox_item.setData(CheckboxDelegate.CheckboxStateRole, False)
        
        self.parent.account_table.viewport().update()
        print(f"[DEBUG] Đã bỏ tick checkbox cho {len(selected_rows)} dòng: {selected_rows}")

    def select_all_account_rows(self):
        """Tick checkbox cho tất cả dòng"""
        from src.ui.account_management import CheckboxDelegate
        for row in range(self.parent.account_table.rowCount()):
            checkbox_item = self.parent.account_table.item(row, 0)
            if checkbox_item:
                checkbox_item.setData(CheckboxDelegate.CheckboxStateRole, True)
        self.parent.account_table.viewport().update()
        print(f"[DEBUG] Đã tick checkbox cho tất cả {self.parent.account_table.rowCount()} dòng")

    def deselect_all_account_rows(self):
        """Bỏ tick checkbox cho tất cả dòng"""
        from src.ui.account_management import CheckboxDelegate
        for row in range(self.parent.account_table.rowCount()):
            checkbox_item = self.parent.account_table.item(row, 0)
            if checkbox_item:
                checkbox_item.setData(CheckboxDelegate.CheckboxStateRole, False)
        self.parent.account_table.viewport().update()
        print(f"[DEBUG] Đã bỏ tick checkbox cho tất cả {self.parent.account_table.rowCount()} dòng")

    # --- Các hàm xử lý tác vụ tài khoản ---
    def login_account(self, row):
        phone = self.parent.account_table.item(row, 1).text()  # Cột 1 là phone
        print(f"[LOGIN] Đăng nhập lại: {phone}")

    def open_browser(self, row):
        print("[Browser] Mở trình duyệt")

    def edit_proxy(self, row):
        print("[Proxy] Sửa Proxy")

    def delete_session(self, row):
        print("[Session] Xóa Session")

    def delete_account(self, row):
        self.parent.account_table.removeRow(row)

    def export_selected_accounts(self):
        print("[EXPORT] Xuất dữ liệu...")

    def copy_phone_number(self, row):
        phone = self.parent.account_table.item(row, 1).text()  # Cột 1 là phone
        from PySide6.QtGui import QGuiApplication
        QGuiApplication.clipboard().setText(phone)
        print(f"[COPY] {phone} đã được copy!")

    def check_status(self, row):
        print("[STATUS] Kiểm tra hoạt động")

    def start_interaction(self, row):
        print("[START] Bắt đầu tương tác")

    def pause_interaction(self, row):
        print("[PAUSE] Tạm dừng tương tác")


# --- Các context menu khác giữ nguyên ---
class ProxyContextMenu(QMenu):
    """Context menu cho Proxy Management Tab"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

    def setup_menu(self):
        self.add_action("🔄 Refresh Proxy List", lambda: print("Refresh proxy list"))
        self.add_action("📊 Check Proxy Status", lambda: print("Check proxy status"))

    def add_action(self, text, slot):
        action = QAction(text, self)
        action.triggered.connect(slot)
        self.addAction(action)


class MessagingContextMenu(QMenu):
    """Context menu cho Messaging Tab"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

    def setup_menu(self):
        self.add_action("📨 Send Message", lambda: print("Send message"))
        self.add_action("📋 Copy Info", lambda: print("Copy info"))

    def add_action(self, text, slot):
        action = QAction(text, self)
        action.triggered.connect(slot)
        self.addAction(action)


class DataScannerContextMenu(QMenu):
    """Context menu cho Data Scanner Tab"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

    def setup_menu(self):
        self.add_action("🔍 Scan Data", lambda: print("Scan data"))
        self.add_action("📊 Show Stats", lambda: print("Show stats"))

    def add_action(self, text, slot):
        action = QAction(text, self)
        action.triggered.connect(slot)
        self.addAction(action)


class HistoryLogContextMenu(QMenu):
    """Context menu cho History Log Tab"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

    def setup_menu(self):
        self.add_action("📜 View Log", lambda: print("View log"))
        self.add_action("🗑️ Clear Log", lambda: print("Clear log"))

    def add_action(self, text, slot):
        action = QAction(text, self)
        action.triggered.connect(slot)
        self.addAction(action)
