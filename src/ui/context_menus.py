from PySide6.QtWidgets import QMenu, QMessageBox, QInputDialog
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt
from functools import partial  # Thêm dòng này
class AccountContextMenu(QMenu):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent # parent ở đây là AccountManagementTab instance
        self.setup_menu()

    def setup_menu(self):
        # Debug: In ra folder_map khi mở menu
        print("[DEBUG] folder_map khi mở menu:", self.parent.folder_map)
        # Menu chính
        self.add_action("Đăng nhập", self.parent.login_selected_accounts)
        
        # Menu con: Chọn/Bỏ chọn
        select_deselect_menu = self.addMenu("Chọn/Bỏ chọn")
        select_deselect_menu.addAction(self.create_action("Chọn tài khoản đang chọn", self.parent.select_selected_accounts))
        select_deselect_menu.addAction(self.create_action("Bỏ chọn tài khoản đang chọn", self.parent.deselect_selected_accounts))
        select_deselect_menu.addAction(self.create_action("Chọn tất cả", lambda: self.parent.toggle_all_accounts_selection(True)))
        select_deselect_menu.addAction(self.create_action("Bỏ chọn tất cả tài khoản", self.parent.deselect_all_accounts))

        # Menu con: Quản lý thư mục
        folder_management_menu = self.addMenu("Thư mục")
        
        # Reload folder_map từ file nếu có hàm load_folder_map
        if hasattr(self.parent, 'load_folder_map'):
            self.parent.folder_map = self.parent.load_folder_map()
            print("[DEBUG] folder_map sau khi reload:", self.parent.folder_map)
        
        # Lấy danh sách các thư mục hiện có từ folder_map của AccountManagementTab
        folders = []
        if '_FOLDER_SET_' in self.parent.folder_map:
            folders = self.parent.folder_map['_FOLDER_SET_']
            if isinstance(folders, str):
                import json
                try:
                    folders = json.loads(folders)
                except Exception:
                    folders = []
        # Loại bỏ các giá trị không phải tên thư mục thực tế
        folders = [f for f in folders if isinstance(f, str) and f not in ("Tổng", "_FOLDER_SET_")]
        folders = sorted(folders)
        print("[DEBUG] folders lấy được:", folders)
        # Add to folder submenu
        # Add to folder submenu
        add_to_folder_menu = folder_management_menu.addMenu("Thêm vào thư mục")
        if folders:
            for folder_name in folders:
                # Sử dụng partial thay vì lambda để tránh vấn đề với biến vòng lặp
                action = QAction(folder_name, self)
                action.triggered.connect(partial(self.parent.add_selected_to_folder, folder_name))
                add_to_folder_menu.addAction(action)
        else:
            no_folder_action = QAction("Chưa có thư mục nào", self)
            no_folder_action.setEnabled(False)
            add_to_folder_menu.addAction(no_folder_action)
        
        # Remove from folder submenu: chỉ còn 1 action duy nhất
        folder_management_menu.addAction(self.create_action("Xóa khỏi thư mục", self.parent.remove_selected_from_folder))
        # Đã xóa action 'Xóa thư mục đang chọn' khỏi menu 'Thư mục'. Không thêm action này vào menu nữa.
        # (Không có dòng nào thêm action này vào folder_management_menu)

        folder_management_menu.addSeparator()
        folder_management_menu.addAction(self.create_action("Xóa thư mục đang chọn", self.parent.delete_selected_folder)) # Nếu muốn xóa một thư mục cụ thể

        # Menu con: Trạng thái tài khoản
        set_status_menu = self.addMenu("Chuyển trạng thái")
        set_status_menu.addAction(self.create_action("Live", lambda: self.parent.set_account_status_selected("Live")))
        set_status_menu.addAction(self.create_action("Die", lambda: self.parent.set_account_status_selected("Die")))
        set_status_menu.addAction(self.create_action("Chưa đăng nhập", lambda: self.parent.set_account_status_selected("Chưa đăng nhập")))
        set_status_menu.addAction(self.create_action("Đăng nhập thất bại", lambda: self.parent.set_account_status_selected("Đăng nhập thất bại")))

        self.addSeparator() # Đường phân cách

        self.add_action("Cập nhật thông tin Proxy", self.parent.update_selected_proxy_info)
        self.add_action("Mở thư mục UserData", self.parent.open_selected_user_data_folder)
        
        self.addSeparator()

        self.add_action("Xuất tài khoản", self.parent.export_accounts)
        self.add_action("Nhập tài khoản", self.parent.import_accounts)
        self.add_action("Bật/Tắt chế độ ẩn danh", self.parent.toggle_stealth_mode)
        self.add_action("Xóa tài khoản", self.parent.delete_selected_accounts)
        self.add_action("Xóa tất cả tài khoản", self.parent.delete_all_accounts)


    def create_action(self, text, slot):
        action = QAction(text, self)
        if slot: # Only connect if slot is provided
            action.triggered.connect(slot)
        return action

    def add_action(self, text, slot): # Keep this for top-level menu items if preferred
        action = QAction(text, self)
        action.triggered.connect(slot)
        self.addAction(action) # Use QMenu's addAction for adding directly to this menu

class ProxyContextMenu(QMenu):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setup_menu()

    def setup_menu(self):
        # Menu cho Proxy Management Tab
        self.add_action("Thêm proxy", self.parent.add_proxy)
        self.add_action("Xóa proxy", self.parent.delete_proxy)
        self.add_action("Kiểm tra proxy", self.parent.check_proxy)
        self.add_action("Xuất proxy", self.parent.export_proxies)
        self.add_action("Nhập proxy", self.parent.import_proxies)
        self.add_action("Xóa tất cả proxy", self.parent.delete_all_proxies)

    def add_action(self, text, slot):
        action = QAction(text, self)
        action.triggered.connect(slot)
        self.addAction(action)

class MessagingContextMenu(QMenu):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setup_menu()

    def setup_menu(self):
        # Menu cho Messaging Tab
        self.add_action("Gửi tin nhắn", self.parent.send_message)
        self.addSeparator()
        self.add_action("Chọn", self.select_rows)
        self.add_action("Chọn tất cả", self.select_all)
        self.add_action("Bỏ chọn", self.deselect_rows)
        self.add_action("Bỏ chọn tất cả", self.deselect_all)
        self.addSeparator()
        self.add_action("Copy thông tin", self.copy_info)
        self.add_action("Xem log gửi chi tiết", self.show_log)
        self.addSeparator()
        self.add_action("Tải danh sách người nhận", self.parent.load_recipients)
        self.add_action("Xuất danh sách người nhận", self.parent.export_recipients)
        self.add_action("Xóa danh sách người nhận", self.parent.clear_recipients)

    def get_selected_rows(self, context_row=None):
        selection = self.parent.account_table.selectionModel().selectedRows()
        if selection:
            return [idx.row() for idx in selection]
        elif context_row is not None:
            return [context_row]
        return []

    def select_rows(self):
        self.parent.select_selected_accounts()

    def select_all(self):
        for acc in self.parent.accounts:
            acc["selected"] = True
        self.parent.update_account_table()

    def deselect_rows(self):
        self.parent.deselect_selected_accounts()

    def deselect_all(self):
        for acc in self.parent.accounts:
            acc["selected"] = False
        self.parent.update_account_table()

    def copy_info(self):
        rows = self.get_selected_rows(getattr(self, 'context_row', None))
        if not rows:
            return
        lines = []
        for row in rows:
            acc = self.parent.accounts[row]
            stt = str(row+1)
            username = acc.get("username", "")
            status = acc.get("status", "")
            success = str(acc.get("success", ""))
            state = acc.get("state", "")
            lines.append(f"{stt}\t{username}\t{status}\t{success}\t{state}")
        QApplication.clipboard().setText("\n".join(lines))

    def show_log(self):
        rows = self.get_selected_rows(getattr(self, 'context_row', None))
        if not rows:
            return
        acc = self.parent.accounts[rows[0]]
        logs = acc.get("send_log", [])
        if not logs:
            QMessageBox.information(self.parent, "Log gửi chi tiết", "Không có dữ liệu lịch sử gửi.")
            return
        msg = ""
        for log in logs:
            msg += f"Thời gian: {log.get('time', '')}\nKết quả: {log.get('result', '')}\nNội dung/Lỗi: {log.get('content', '')}\n---\n"
        QMessageBox.information(self.parent, f"Log gửi: {acc.get('username', '')}", msg)

    def add_action(self, text, slot):
        action = QAction(text, self)
        action.triggered.connect(slot)
        self.addAction(action)

class DataScannerContextMenu(QMenu):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setup_menu()

    def setup_menu(self):
        # Menu cho Data Scanner Tab
        self.add_action("Bắt đầu quét", self.parent.start_scan)
        self.add_action("Dừng quét", self.parent.stop_scan)
        self.add_action("Xuất kết quả", self.parent.export_results)
        self.add_action("Xóa kết quả", self.parent.clear_results)

    def add_action(self, text, slot):
        action = QAction(text, self)
        action.triggered.connect(slot)
        self.addAction(action)

class HistoryLogContextMenu(QMenu):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setup_menu()

    def setup_menu(self):
        # Menu cho History Log Tab
        self.add_action("Xuất lịch sử", self.parent.export_history)
        self.add_action("Xóa lịch sử", self.parent.clear_history)
        self.add_action("Lọc lịch sử", self.parent.filter_history)

    def add_action(self, text, slot):
        action = QAction(text, self)
        action.triggered.connect(slot)
        self.addAction(action)
