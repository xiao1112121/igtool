from PySide6.QtWidgets import QMenu, QMessageBox, QInputDialog
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt
from functools import partial  # Thêm dòng này
import json
import os
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

        # ⭐ MENU QUẢN LÝ PROXY VĨNH VIỄN
        permanent_proxy_menu = self.addMenu("Proxy vĩnh viễn")
        permanent_proxy_menu.addAction(self.create_action("Gán proxy vĩnh viễn", self.assign_permanent_proxy))
        permanent_proxy_menu.addAction(self.create_action("Xóa proxy vĩnh viễn", self.remove_permanent_proxy))
        permanent_proxy_menu.addAction(self.create_action("Xem proxy vĩnh viễn", self.view_permanent_proxy))

        self.addSeparator() # Đường phân cách cho proxy management

        # ⭐ MENU ĐỒNG BỘ PROXY
        self.add_action("🔄 Đồng bộ Proxy từ tab Proxy", self.sync_proxy_from_proxy_tab)
        self.add_action("🎯 Tự động gán Proxy khả dụng", self.auto_assign_available_proxies)
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

    # ⭐ PERMANENT PROXY MANAGEMENT FUNCTIONS
    def assign_permanent_proxy(self):
        """Gán proxy vĩnh viễn cho các tài khoản đã chọn"""
        selected_accounts = [acc for acc in self.parent.accounts if acc.get('selected')]
        if not selected_accounts:
            QMessageBox.warning(self.parent, "Cảnh báo", "Vui lòng chọn ít nhất 1 tài khoản!")
            return
        
        proxy_text, ok = QInputDialog.getText(
            self.parent, 
            "Gán proxy vĩnh viễn", 
            f"Nhập proxy vĩnh viễn cho {len(selected_accounts)} tài khoản:\n(Format: ip:port:user:pass hoặc ip:port)"
        )
        
        if ok and proxy_text.strip():
            proxy_text = proxy_text.strip()
            # Assign permanent proxy to selected accounts
            for account in selected_accounts:
                account["permanent_proxy"] = proxy_text
                print(f"[INFO] Gán permanent proxy cho {account.get('username')}: {proxy_text}")
            
            # Save and update UI
            self.parent.save_accounts()
            self.parent.update_account_table()
            
            QMessageBox.information(
                self.parent, 
                "Thành công", 
                f"Đã gán proxy vĩnh viễn cho {len(selected_accounts)} tài khoản:\n{proxy_text}"
            )

    def remove_permanent_proxy(self):
        """Xóa proxy vĩnh viễn của các tài khoản đã chọn"""
        selected_accounts = [acc for acc in self.parent.accounts if acc.get('selected')]
        if not selected_accounts:
            QMessageBox.warning(self.parent, "Cảnh báo", "Vui lòng chọn ít nhất 1 tài khoản!")
            return
        
        # Count accounts with permanent proxy
        accounts_with_permanent = [acc for acc in selected_accounts if acc.get("permanent_proxy", "").strip()]
        
        if not accounts_with_permanent:
            QMessageBox.information(self.parent, "Thông báo", "Không có tài khoản nào có proxy vĩnh viễn!")
            return
        
        reply = QMessageBox.question(
            self.parent,
            "Xác nhận",
            f"Bạn có chắc muốn xóa proxy vĩnh viễn của {len(accounts_with_permanent)} tài khoản?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            for account in selected_accounts:
                if account.get("permanent_proxy", "").strip():
                    print(f"[INFO] Xóa permanent proxy của {account.get('username')}: {account.get('permanent_proxy')}")
                    account["permanent_proxy"] = ""
            
            # Save and update UI
            self.parent.save_accounts()
            self.parent.update_account_table()
            
            QMessageBox.information(
                self.parent,
                "Thành công", 
                f"Đã xóa proxy vĩnh viễn của {len(accounts_with_permanent)} tài khoản!"
            )

    def view_permanent_proxy(self):
        """Xem thông tin proxy vĩnh viễn của các tài khoản đã chọn"""
        selected_accounts = [acc for acc in self.parent.accounts if acc.get('selected')]
        if not selected_accounts:
            QMessageBox.warning(self.parent, "Cảnh báo", "Vui lòng chọn ít nhất 1 tài khoản!")
            return
        
        # Build info message
        info_lines = []
        accounts_with_permanent = 0
        
        for account in selected_accounts:
            username = account.get("username", "Unknown")
            permanent_proxy = account.get("permanent_proxy", "").strip()
            
            if permanent_proxy:
                info_lines.append(f"✅ {username}: {permanent_proxy}")
                accounts_with_permanent += 1
            else:
                info_lines.append(f"❌ {username}: Không có proxy vĩnh viễn")
        
        message = f"THÔNG TIN PROXY VĨNH VIỄN ({accounts_with_permanent}/{len(selected_accounts)} có proxy):\n\n"
        message += "\n".join(info_lines)
        
        QMessageBox.information(self.parent, "Proxy vĩnh viễn", message)

    def sync_proxy_from_proxy_tab(self):
        """Đồng bộ proxy từ tab Proxy Management"""
        try:
            if hasattr(self.parent, 'sync_proxy_data'):
                print("[DEBUG] ⭐ Calling sync_proxy_data from context menu...")
                self.parent.sync_proxy_data()
            else:
                QMessageBox.warning(
                    self.parent, 
                    "Lỗi", 
                    "❌ Không thể đồng bộ proxy.\nMethod sync_proxy_data không tồn tại."
                )
        except Exception as e:
            print(f"[ERROR] Lỗi khi sync proxy từ context menu: {e}")
            QMessageBox.critical(
                self.parent, 
                "Lỗi đồng bộ", 
                f"❌ Có lỗi xảy ra khi đồng bộ proxy:\n\n{str(e)}"
            )

    def auto_assign_available_proxies(self):
        """Tự động gán proxy khả dụng cho các tài khoản đã chọn"""
        try:
            selected_accounts = [acc for acc in self.parent.accounts if acc.get('selected')]
            if not selected_accounts:
                QMessageBox.warning(self.parent, "Cảnh báo", "Vui lòng chọn ít nhất 1 tài khoản!")
                return
            
            # Load proxy data từ proxy_status.json  
            proxy_file = 'proxy_status.json'
            if not os.path.exists(proxy_file):
                QMessageBox.warning(
                    self.parent, 
                    "Lỗi", 
                    f"⚠️ Không tìm thấy file {proxy_file}\n\nVui lòng import proxy từ tab 'Quản lý Proxy' trước!"
                )
                return
            
            with open(proxy_file, 'r', encoding='utf-8') as f:
                proxy_data = json.load(f)
            
            # Lấy các proxy khả dụng (status OK và chưa được gán)
            available_proxies = []
            for proxy_info in proxy_data:
                proxy_string = proxy_info.get('proxy', '')
                assigned_account = proxy_info.get('assigned_account', '').strip()
                proxy_status = proxy_info.get('status', '').lower()
                
                # Proxy khả dụng: status OK và chưa gán cho ai
                if proxy_status in ['ok', 'hoạt động'] and not assigned_account:
                    available_proxies.append(proxy_string)
            
            if not available_proxies:
                QMessageBox.information(
                    self.parent,
                    "Thông báo", 
                    "📭 Không có proxy khả dụng!\n\n"
                    "💡 Tất cả proxy hoạt động đã được gán hoặc không có proxy nào có status 'OK'."
                )
                return
            
            # Lọc các tài khoản chưa có proxy hoặc muốn thay đổi
            accounts_needing_proxy = []
            for account in selected_accounts:
                username = account.get('username', '')
                regular_proxy = account.get('proxy', '').strip()
                permanent_proxy = account.get('permanent_proxy', '').strip()
                
                # Tài khoản cần proxy nếu không có permanent proxy và (không có regular proxy hoặc muốn override)
                if not permanent_proxy:
                    accounts_needing_proxy.append(account)
            
            if not accounts_needing_proxy:
                QMessageBox.information(
                    self.parent,
                    "Thông báo",
                    "💡 Tất cả tài khoản đã chọn đều có permanent proxy!\n\n"
                    "🔧 Sử dụng 'Xóa proxy vĩnh viễn' nếu muốn gán proxy khả dụng."
                )
                return
            
            # Assign proxy
            assigned_count = 0
            proxy_index = 0
            
            for account in accounts_needing_proxy:
                if proxy_index >= len(available_proxies):
                    break  # Hết proxy khả dụng
                
                username = account.get('username', '')
                old_proxy = account.get('proxy', '')
                new_proxy = available_proxies[proxy_index]
                
                account['proxy'] = new_proxy
                account['proxy_status'] = 'OK'
                
                print(f"[INFO] 🎯 Auto-assigned proxy for {username}: {new_proxy}")
                assigned_count += 1
                proxy_index += 1
            
            # Lưu và cập nhật UI
            if assigned_count > 0:
                self.parent.save_accounts()
                self.parent.update_account_table()
                
                remaining_accounts = len(accounts_needing_proxy) - assigned_count
                remaining_proxies = len(available_proxies) - assigned_count
                
                QMessageBox.information(
                    self.parent,
                    "Gán proxy thành công",
                    f"✅ Đã tự động gán proxy cho {assigned_count} tài khoản!\n\n"
                    f"📊 Còn lại:\n"
                    f"  • {remaining_accounts} tài khoản chưa có proxy\n"
                    f"  • {remaining_proxies} proxy khả dụng\n\n"
                    f"💡 Tip: Sử dụng 'Gán proxy vĩnh viễn' để cố định proxy cho tài khoản quan trọng."
                )
            
        except Exception as e:
            print(f"[ERROR] Lỗi auto assign proxy: {e}")
            QMessageBox.critical(
                self.parent,
                "Lỗi gán proxy",
                f"❌ Có lỗi xảy ra khi gán proxy tự động:\n\n{str(e)}"
            )

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
        # ⭐ MENU TỐI ƯU CHO DATA SCANNER TAB
        
        # Scan controls
        self.add_action("🚀 Bắt đầu quét", self.parent.start_scan)
        self.add_action("⏹️ Dừng quét", self.parent.stop_scan)
        
        self.addSeparator()
        
        # Selection controls 
        self.add_action("✅ Chọn tất cả kết quả", self.select_all_results)
        self.add_action("❌ Bỏ chọn tất cả", self.deselect_all_results)
        
        self.addSeparator()
        
        # Export controls
        export_menu = self.addMenu("📤 Xuất dữ liệu")
        export_menu.addAction(self.create_action("📄 Xuất TXT (chỉ username)", self.export_txt_only))
        export_menu.addAction(self.create_action("📊 Xuất CSV (đầy đủ)", self.parent.export_results))
        export_menu.addAction(self.create_action("📋 Copy username đã chọn", self.copy_selected_usernames))
        
        self.addSeparator()
        
        # Clear controls
        self.add_action("🗑️ Xóa kết quả đã chọn", self.delete_selected_results)
        self.add_action("🗑️ Xóa tất cả kết quả", self.parent.clear_results)
        
        self.addSeparator()
        
        # Stats
        self.add_action("📊 Thống kê chi tiết", self.show_detailed_stats)

    def create_action(self, text, slot):
        action = QAction(text, self)
        if slot:
            action.triggered.connect(slot)
        return action

    def add_action(self, text, slot):
        action = QAction(text, self)
        action.triggered.connect(slot)
        self.addAction(action)
    
    def select_all_results(self):
        """Chọn tất cả kết quả"""
        for i in range(self.parent.result_table.rowCount()):
            checkbox_item = self.parent.result_table.item(i, 0)
            if checkbox_item:
                checkbox_item.setCheckState(Qt.CheckState.Checked)
    
    def deselect_all_results(self):
        """Bỏ chọn tất cả kết quả"""
        for i in range(self.parent.result_table.rowCount()):
            checkbox_item = self.parent.result_table.item(i, 0)
            if checkbox_item:
                checkbox_item.setCheckState(Qt.CheckState.Unchecked)
    
    def export_txt_only(self):
        """Xuất chỉ username ra file TXT"""
        if not self.parent.result_data:
            QMessageBox.warning(self.parent, "Cảnh báo", "Không có dữ liệu để xuất!")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self.parent,
            "Xuất username",
            f"usernames_{self.parent.get_current_timestamp().replace(':', '')}.txt",
            "Text Files (*.txt)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    for res in self.parent.result_data:
                        username = res.get('found_username', res.get('username', ''))
                        f.write(f"{username}\n")
                
                QMessageBox.information(
                    self.parent, 
                    "Xuất thành công", 
                    f"✅ Đã xuất {len(self.parent.result_data)} username ra:\n{file_path}"
                )
            except Exception as e:
                QMessageBox.critical(self.parent, "Lỗi", f"❌ Lỗi xuất file: {str(e)}")
    
    def copy_selected_usernames(self):
        """Copy username đã chọn vào clipboard"""
        selected_usernames = self.parent.get_selected_result_usernames()
        if not selected_usernames:
            QMessageBox.warning(self.parent, "Cảnh báo", "Vui lòng chọn ít nhất 1 username!")
            return
        
        # Copy to clipboard
        QApplication.clipboard().setText('\n'.join(selected_usernames))
        
        QMessageBox.information(
            self.parent,
            "Copy thành công",
            f"✅ Đã copy {len(selected_usernames)} username vào clipboard!"
        )
    
    def delete_selected_results(self):
        """Xóa kết quả đã chọn"""
        selected_indices = []
        for i in range(self.parent.result_table.rowCount()):
            checkbox_item = self.parent.result_table.item(i, 0)
            if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
                selected_indices.append(i)
        
        if not selected_indices:
            QMessageBox.warning(self.parent, "Cảnh báo", "Vui lòng chọn ít nhất 1 kết quả để xóa!")
            return
        
        reply = QMessageBox.question(
            self.parent,
            "Xác nhận xóa",
            f"Bạn có chắc muốn xóa {len(selected_indices)} kết quả đã chọn?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Xóa từ cuối lên đầu để tránh thay đổi index
            for i in reversed(selected_indices):
                if i < len(self.parent.result_data):
                    del self.parent.result_data[i]
            
            # Cập nhật UI
            self.parent.update_result_table()
            self.parent.stats_label.setText(f"Tổng số username quét được: {len(self.parent.result_data)}")
            
            QMessageBox.information(
                self.parent,
                "Xóa thành công",
                f"✅ Đã xóa {len(selected_indices)} kết quả!"
            )
    
    def show_detailed_stats(self):
        """Hiển thị thống kê chi tiết"""
        if not self.parent.result_data:
            QMessageBox.information(self.parent, "Thống kê", "Chưa có dữ liệu để thống kê!")
            return
        
        # Tính toán stats
        total = len(self.parent.result_data)
        scanners = set()
        targets = set()
        scan_types = {}
        
        for res in self.parent.result_data:
            scanner = res.get('scanner_account', res.get('account', ''))
            target = res.get('target_account', res.get('target', ''))
            scan_type = res.get('scan_type', 'Unknown')
            
            if scanner:
                scanners.add(scanner)
            if target:
                targets.add(target)
            
            scan_types[scan_type] = scan_types.get(scan_type, 0) + 1
        
        # Tạo message thống kê
        stats_msg = f"📊 THỐNG KÊ CHI TIẾT\n\n"
        stats_msg += f"🔍 Tổng username tìm được: {total}\n"
        stats_msg += f"👤 Số tài khoản quét: {len(scanners)}\n"
        stats_msg += f"🎯 Số target được quét: {len(targets)}\n\n"
        
        stats_msg += f"📋 PHÂN LOẠI THEO KIỂU QUÉT:\n"
        for scan_type, count in scan_types.items():
            percentage = (count / total * 100) if total > 0 else 0
            stats_msg += f"  • {scan_type}: {count} ({percentage:.1f}%)\n"
        
        QMessageBox.information(self.parent, "Thống kê chi tiết", stats_msg)

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
