from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QAbstractItemView, QMenu, QInputDialog, 
                             QMessageBox, QApplication, QComboBox, QLineEdit, QHBoxLayout, 
                             QLabel, QSpacerItem, QSizePolicy)
from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtGui import QColor, QBrush, QAction

import requests
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Import the 2captcha library
from twocaptcha import TwoCaptcha

# Import utility functions
from src.ui.utils import random_delay, wait_for_element, wait_for_element_clickable, retry_operation

class AccountManagementTab(QWidget):
    # Định nghĩa tín hiệu để thông báo khi có tài khoản được thêm/cập nhật
    account_updated = Signal()
    # Định nghĩa tín hiệu để đồng bộ proxy nếu cần
    proxy_updated = Signal()

    def __init__(self):
        super().__init__()
        self.accounts = []
        self.proxies = {} # Sẽ được đồng bộ từ ProxyManagementTab
        self.init_ui()
        self.load_accounts()

        # Cấu hình 2captcha API key
        self.TWO_CAPTCHA_API_KEY = 'b452b70e7afcd461cbd3758dac95b3c0' # Thay bằng API key của bạn

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Thanh tìm kiếm và bộ lọc
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Tìm kiếm tài khoản...")
        self.search_input.textChanged.connect(self.filter_accounts)
        search_layout.addWidget(self.search_input)

        self.status_filter = QComboBox(self)
        self.status_filter.addItem("Tất cả trạng thái")
        self.status_filter.addItem("Đang hoạt động")
        self.status_filter.addItem("Đã khóa")
        self.status_filter.addItem("Cần xác minh")
        self.status_filter.addItem("Lỗi proxy")
        self.status_filter.currentTextChanged.connect(self.filter_accounts)
        search_layout.addWidget(self.status_filter)
        layout.addLayout(search_layout)

        # Table để hiển thị tài khoản
        self.account_table = QTableWidget(0, 7) # 7 cột: ID, Username, Proxy, Status, Last Check, Notes, Actions
        self.account_table.setHorizontalHeaderLabels(["ID", "Username", "Proxy", "Status", "Last Check", "Notes", "Actions"])
        self.account_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.account_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.account_table.setEditTriggers(QAbstractItemView.NoEditTriggers) # Không cho phép chỉnh sửa trực tiếp trên bảng
        self.account_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.account_table.customContextMenuRequested.connect(self.handle_context_menu)
        layout.addWidget(self.account_table)

        # Các nút chức năng
        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Thêm Tài khoản")
        self.add_button.clicked.connect(self.add_account)
        button_layout.addWidget(self.add_button)

        self.edit_button = QPushButton("Sửa Tài khoản")
        self.edit_button.clicked.connect(self.edit_account)
        button_layout.addWidget(self.edit_button)

        self.delete_button = QPushButton("Xóa Tài khoản")
        self.delete_button.clicked.connect(self.delete_account)
        button_layout.addWidget(self.delete_button)

        self.login_button = QPushButton("Đăng nhập Tài khoản Đã chọn")
        self.login_button.clicked.connect(self.login_selected_account)
        button_layout.addWidget(self.login_button)
        
        self.check_status_button = QPushButton("Kiểm tra Trạng thái")
        self.check_status_button.clicked.connect(self.check_account_status)
        button_layout.addWidget(self.check_status_button)

        button_layout.addStretch(1) # Đẩy các nút sang trái
        layout.addLayout(button_layout)

    def load_accounts(self):
        # Tải tài khoản từ file (hoặc database)
        # Placeholder: Trong thực tế, bạn sẽ đọc từ một file JSON hoặc database
        self.accounts = [
            {"id": 1, "username": "user1", "password": "pass1", "proxy": "http://user:pass@host:port", "status": "Đang hoạt động", "last_check": "2023-10-26 10:00", "notes": "Tài khoản chính"},
            {"id": 2, "username": "user2", "password": "pass2", "proxy": "", "status": "Đã khóa", "last_check": "2023-10-25 15:30", "notes": "Cần mở khóa"},
        ]
        self.populate_table()
        print("[DEBUG] AccountManagementTab: Đã tải tài khoản.")

    def save_accounts(self):
        # Lưu tài khoản vào file (hoặc database)
        # Placeholder: Trong thực tế, bạn sẽ ghi vào một file JSON hoặc database
        print("[DEBUG] AccountManagementTab: Đã lưu tài khoản.")
        pass

    def populate_table(self):
        self.account_table.setRowCount(0) # Xóa tất cả các hàng hiện có
        for account in self.accounts:
            row_position = self.account_table.rowCount()
            self.account_table.insertRow(row_position)
            self.account_table.setItem(row_position, 0, QTableWidgetItem(str(account["id"])))
            self.account_table.setItem(row_position, 1, QTableWidgetItem(account["username"]))
            self.account_table.setItem(row_position, 2, QTableWidgetItem(account.get("proxy", "")))
            
            status_item = QTableWidgetItem(account["status"])
            # Thêm màu sắc cho trạng thái
            if account["status"] == "Đang hoạt động":
                status_item.setBackground(QBrush(QColor(144, 238, 144))) # LightGreen
            elif account["status"] == "Đã khóa":
                status_item.setBackground(QBrush(QColor(255, 99, 71))) # Tomato
            elif account["status"] == "Cần xác minh":
                status_item.setBackground(QBrush(QColor(255, 255, 0))) # Yellow
            elif account["status"] == "Lỗi proxy":
                status_item.setBackground(QBrush(QColor(255, 165, 0))) # Orange
            self.account_table.setItem(row_position, 3, status_item)

            self.account_table.setItem(row_position, 4, QTableWidgetItem(account["last_check"]))
            self.account_table.setItem(row_position, 5, QTableWidgetItem(account.get("notes", "")))
        self.filter_accounts() # Áp dụng bộ lọc sau khi nạp dữ liệu

    def filter_accounts(self):
        search_text = self.search_input.text().lower()
        selected_status = self.status_filter.currentText()

        for row in range(self.account_table.rowCount()):
            username_item = self.account_table.item(row, 1)
            status_item = self.account_table.item(row, 3)

            username_match = search_text in username_item.text().lower() if username_item else False
            status_match = (selected_status == "Tất cả trạng thái") or \
                           (status_item and status_item.text() == selected_status)

            self.account_table.setRowHidden(row, not (username_match and status_match))

    def add_account(self):
        # Triển khai hộp thoại để thêm tài khoản mới
        username, ok1 = QInputDialog.getText(self, "Thêm Tài khoản", "Username:")
        if not ok1 or not username: return

        password, ok2 = QInputDialog.getText(self, "Thêm Tài khoản", "Password:", QLineEdit.Password)
        if not ok2 or not password: return
        
        proxy, ok3 = QInputDialog.getText(self, "Thêm Tài khoản", "Proxy (tùy chọn, vd: http://user:pass@host:port):")
        if not ok3: return

        notes, ok4 = QInputDialog.getText(self, "Thêm Tài khoản", "Ghi chú (tùy chọn):")
        if not ok4: return

        new_id = max([acc["id"] for acc in self.accounts]) + 1 if self.accounts else 1
        new_account = {
            "id": new_id,
            "username": username,
            "password": password,
            "proxy": proxy,
            "status": "Chưa kiểm tra",
            "last_check": time.strftime("%Y-%m-%d %H:%M:%S"),
            "notes": notes
        }
        self.accounts.append(new_account)
        self.save_accounts()
        self.populate_table()
        self.account_updated.emit() # Phát tín hiệu cập nhật

    def edit_account(self):
        selected_rows = self.account_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn một tài khoản để sửa.")
            return

        row = selected_rows[0].row()
        account_id = int(self.account_table.item(row, 0).text())
        current_account = next((acc for acc in self.accounts if acc["id"] == account_id), None)

        if not current_account: return

        username, ok1 = QInputDialog.getText(self, "Sửa Tài khoản", "Username:", text=current_account["username"])
        if not ok1 or not username: return

        password, ok2 = QInputDialog.getText(self, "Sửa Tài khoản", "Password:", QLineEdit.Password, text=current_account["password"])
        if not ok2 or not password: return
        
        proxy, ok3 = QInputDialog.getText(self, "Sửa Tài khoản", "Proxy (tùy chọn, vd: http://user:pass@host:port):", text=current_account.get("proxy", ""))
        if not ok3: return

        notes, ok4 = QInputDialog.getText(self, "Sửa Tài khoản", "Ghi chú (tùy chọn):", text=current_account.get("notes", ""))
        if not ok4: return

        current_account.update({
            "username": username,
            "password": password,
            "proxy": proxy,
            "notes": notes
        })
        self.save_accounts()
        self.populate_table()
        self.account_updated.emit() # Phát tín hiệu cập nhật

    def delete_account(self):
        selected_rows = self.account_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn một tài khoản để xóa.")
            return

        reply = QMessageBox.question(self, "Xác nhận xóa", 
                                     "Bạn có chắc chắn muốn xóa tài khoản đã chọn?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            rows_to_delete = sorted([row.row() for row in selected_rows], reverse=True)
            for row in rows_to_delete:
                account_id = int(self.account_table.item(row, 0).text())
                self.accounts = [acc for acc in self.accounts if acc["id"] != account_id]
            self.save_accounts()
            self.populate_table()
            self.account_updated.emit() # Phát tín hiệu cập nhật

    def handle_context_menu(self, pos):
        context_menu = QMenu(self)
        login_action = QAction("Đăng nhập tài khoản này", self)
        login_action.triggered.connect(self.login_selected_account_from_context)
        context_menu.addAction(login_action)
        
        # Thêm các action khác nếu cần
        # edit_action = QAction("Sửa tài khoản", self)
        # edit_action.triggered.connect(self.edit_account)
        # context_menu.addAction(edit_action)

        # delete_action = QAction("Xóa tài khoản", self)
        # delete_action.triggered.connect(self.delete_account)
        # context_menu.addAction(delete_action)

        context_menu.exec(self.account_table.mapToGlobal(pos))

    def login_selected_account_from_context(self):
        selected_rows = self.account_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn một tài khoản để đăng nhập.")
            return
        
        # Lấy thông tin tài khoản từ hàng được chọn
        row = selected_rows[0].row()
        account_id = int(self.account_table.item(row, 0).text())
        selected_account = next((acc for acc in self.accounts if acc["id"] == account_id), None)

        if selected_account:
            self.login_instagram_and_get_info(selected_account)
        else:
            QMessageBox.critical(self, "Lỗi", "Không tìm thấy thông tin tài khoản.")

    def login_selected_account(self):
        selected_rows = self.account_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn một tài khoản để đăng nhập.")
            return
        
        # Lấy thông tin tài khoản từ hàng được chọn (chỉ lấy hàng đầu tiên)
        row = selected_rows[0].row()
        account_id = int(self.account_table.item(row, 0).text())
        selected_account = next((acc for acc in self.accounts if acc["id"] == account_id), None)

        if selected_account:
            self.login_instagram_and_get_info(selected_account)
        else:
            QMessageBox.critical(self, "Lỗi", "Không tìm thấy thông tin tài khoản.")

    def update_account_status(self, account_id, status, last_check=None):
        for account in self.accounts:
            if account["id"] == account_id:
                account["status"] = status
                account["last_check"] = last_check if last_check else time.strftime("%Y-%m-%d %H:%M:%S")
                break
        self.save_accounts()
        self.populate_table()
        self.account_updated.emit() # Phát tín hiệu cập nhật

    def check_account_status(self):
        # Triển khai logic kiểm tra trạng thái tài khoản
        QMessageBox.information(self, "Thông báo", "Chức năng kiểm tra trạng thái đang được triển khai.")
        # Bạn có thể duyệt qua self.accounts và gọi một hàm kiểm tra riêng cho từng tài khoản
        # Ví dụ:
        # for account in self.accounts:
        #     status = self.perform_status_check(account["username"], account.get("proxy"))
        #     self.update_account_status(account["id"], status)

    def login_instagram_and_get_info(self, account):
        username = account["username"]
        password = account["password"]
        proxy = account.get("proxy")

        print(f"[DEBUG] Bắt đầu đăng nhập cho tài khoản {username}...")

        driver = None
        try:
            options = Options()
            options.add_argument("--disable-notifications")
            options.add_argument("--disable-popup-blocking")
            options.add_argument("--ignore-certificate-errors")
            options.add_argument("--incognito")
            
            if proxy:
                print(f"[DEBUG] Sử dụng proxy: {proxy} cho tài khoản {username}")
                options.add_argument(f'--proxy-server={proxy}')
            else:
                print(f"[DEBUG] Không sử dụng proxy cho tài khoản {username}")

            driver = webdriver.Chrome(options=options)
            driver.set_page_load_timeout(30) # Tăng timeout tải trang
            driver.implicitly_wait(5) # Đợi ngầm định cho các phần tử

            driver.get("https://www.instagram.com/accounts/login/")
            print(f"[DEBUG] Đã tải trang Instagram cho {username}.")

            # --- Bắt đầu phần xử lý Cookie và Popup ---
            self.handle_cookie_banner(driver, username)
            
            # Đợi cho trang đăng nhập tải xong và điền thông tin
            username_input = wait_for_element(driver, By.NAME, "username", timeout=10)
            if not username_input:
                raise Exception("Không thể tìm thấy ô nhập username")
            print(f"[DEBUG] Trang đăng nhập đã tải xong cho {username}")

            password_input = wait_for_element(driver, By.NAME, "password", timeout=5)
            if not password_input:
                raise Exception("Không thể tìm thấy ô nhập password")

            random_delay()
            username_input.send_keys(username)
            random_delay()
            password_input.send_keys(password)

            random_delay(1, 2)
            login_button = wait_for_element(driver, By.CSS_SELECTOR, "button[type='submit']", timeout=10)
            if not login_button:
                raise Exception("Không thể tìm thấy nút đăng nhập")
            driver.execute_script("arguments[0].click();", login_button)
            print(f"[DEBUG] Đã click nút đăng nhập cho {username} bằng JavaScript")

            # Xử lý reCAPTCHA nếu xuất hiện
            recaptcha_solved = self.handle_recaptcha(driver, username)
            if not recaptcha_solved:
                print(f"[DEBUG] reCAPTCHA không được giải quyết hoặc xảy ra lỗi cho {username}.")
                self.update_account_status(account["id"], "Cần xác minh", time.strftime("%Y-%m-%d %H:%M:%S"))
                return False, "Failed to solve reCAPTCHA"

            # Kiểm tra xem có popup lưu thông tin đăng nhập hoặc thông báo không
            self.handle_login_popups(driver, username)

            # Kiểm tra xem đăng nhập thành công hay không
            if self.verify_login_success(driver, username):
                print(f"[INFO] Đăng nhập thành công cho tài khoản {username}.")
                self.update_account_status(account["id"], "Đang hoạt động", time.strftime("%Y-%m-%d %H:%M:%S"))
                return True, "Login successful"
            else:
                # Kiểm tra thông báo lỗi cụ thể hơn nếu có thể
                if "checkpoint" in driver.current_url:
                    print(f"[WARN] Tài khoản {username} yêu cầu xác minh checkpoint.")
                    self.update_account_status(account["id"], "Cần xác minh", time.strftime("%Y-%m-%d %H:%M:%S"))
                    return False, "Checkpoint required"
                else:
                    print(f"[ERROR] Đăng nhập thất bại cho tài khoản {username}. URL hiện tại: {driver.current_url}")
                    self.update_account_status(account["id"], "Đã khóa/Lỗi", time.strftime("%Y-%m-%d %H:%M:%S"))
                    return False, "Login failed"

        except TimeoutException as e:
            print(f"[ERROR] Timeout khi đăng nhập cho tài khoản {username}: {e}")
            self.update_account_status(account["id"], "Lỗi timeout", time.strftime("%Y-%m-%d %H:%M:%S"))
            return False, "Timeout"
        except NoSuchElementException as e:
            print(f"[ERROR] Không tìm thấy phần tử khi đăng nhập cho tài khoản {username}: {e}")
            self.update_account_status(account["id"], "Lỗi phần tử", time.strftime("%Y-%m-%d %H:%M:%S"))
            return False, "Element not found"
        except Exception as e:
            print(f"[ERROR] Lỗi không xác định khi đăng nhập cho tài khoản {username}: {e}")
            self.update_account_status(account["id"], "Lỗi không xác định", time.strftime("%Y-%m-%d %H:%M:%S"))
            return False, f"Unknown error: {e}"
        finally:
            if driver:
                driver.quit()
                print(f"[DEBUG] Đã đóng trình duyệt cho tài khoản {username}.")

    def handle_cookie_banner(self, driver, username):
        """Xử lý banner cookie bằng cách chấp nhận tất cả."""
        try:
            accept_cookies_button = wait_for_element_clickable(driver, By.XPATH, 
                "//button[text()='Cho phép tất cả cookie'] | "
                "//button[text()='Accept All'] | "
                "//button[text()='Allow all cookies'] | "
                "//button[contains(.,'Accept')] | "
                "//button[contains(.,'Allow')] | "
                "//button[contains(.,'Cho phép')] | "
                "//span[text()='Accept All']/parent::button | "
                "//span[text()='Allow all cookies']/parent::button", 
                timeout=5
            )
            if accept_cookies_button:
                print(f"[DEBUG] Đã chấp nhận cookie cho {username}.")
                random_delay(1, 2)
                # Đảm bảo click hoạt động
                try:
                    accept_cookies_button.click()
                except Exception as e:
                    print(f"[DEBUG] Lỗi khi click nút chấp nhận cookie thông thường, thử JS: {e}")
                    driver.execute_script("arguments[0].click();", accept_cookies_button)
        except Exception as e:
            print(f"[DEBUG] Không tìm thấy hoặc không thể click nút chấp nhận cookie cho {username}: {e}")

    def handle_login_popups(self, driver, username):
        """Xử lý các pop-up sau khi đăng nhập (lưu thông tin, bật thông báo)."""
        # Xử lý pop-up "Lưu thông tin đăng nhập"
        try:
            not_now_button_xpath = (
                "//button[text()='Not Now'] | "
                "//button[text()='Lúc khác'] | "
                "//button[text()='Später'] | " # German "Later"
                "//button[text()='Más tarde'] | " # Spanish "Later"
                "//button[text()='Jetzt nicht'] | " # German "Not now"
                "//button[contains(.,'Not Now')] | "
                "//button[contains(.,'Lúc khác')] | "
                "//div[text()='Lưu thông tin đăng nhập?']/ancestor::div[contains(@class, 'x1n2onr6')]//button[contains(.,'Lúc khác')] | "
                "//div[text()='Save your login info?']/ancestor::div[contains(@class, 'x1n2onr6')]//button[contains(.,'Not Now')] | "
                "//button[contains(.,'Later')] | "
                "//button[contains(.,'Skip')] | "
                "//button[contains(.,'Bỏ qua')] | "
                "//span[text()='Not Now']/parent::button | "
                "//span[text()='Lúc khác']/parent::button"
            )
            not_now_button = wait_for_element_clickable(driver, By.XPATH, not_now_button_xpath, timeout=7)
            if not_now_button:
                print(f"[DEBUG] Đã click nút 'Not Now' (lưu thông tin đăng nhập) cho {username}.")
                random_delay(1, 2)
                try:
                    not_now_button.click()
                except Exception as e:
                    print(f"[DEBUG] Lỗi khi click nút 'Not Now' thông thường, thử JS: {e}")
                    driver.execute_script("arguments[0].click();", not_now_button)
        except Exception as e:
            print(f"[DEBUG] Không tìm thấy hoặc không thể click nút 'Not Now' (lưu thông tin đăng nhập) cho {username}: {e}")

        # Xử lý pop-up "Bật thông báo"
        try:
            turn_on_notifications_not_now_xpath = (
                "//button[text()='Not Now'] | "
                "//button[text()='Lúc khác'] | "
                "//button[text()='Später'] | "
                "//button[text()='Ahora no'] | " # Spanish "Not now"
                "//button[contains(.,'Not Now')] | "
                "//button[contains(.,'Lúc khác')] | "
                "//div[text()='Turn on notifications?']/ancestor::div[contains(@class, 'x1n2onr6')]//button[contains(.,'Not Now')] | "
                "//div[text()='Bật thông báo?']/ancestor::div[contains(@class, 'x1n2onr6')]//button[contains(.,'Lúc khác')] | "
                "//button[contains(.,'Later')] | "
                "//button[contains(.,'Skip')] | "
                "//button[contains(.,'Bỏ qua')] | "
                "//span[text()='Not Now']/parent::button | "
                "//span[text()='Lúc khác']/parent::button"
            )
            turn_on_notifications_not_now_button = wait_for_element_clickable(driver, By.XPATH, turn_on_notifications_not_now_xpath, timeout=7)
            if turn_on_notifications_not_now_button:
                print(f"[DEBUG] Đã click nút 'Not Now' (thông báo) cho {username}.")
                random_delay(1, 2)
                try:
                    turn_on_notifications_not_now_button.click()
                except Exception as e:
                    print(f"[DEBUG] Lỗi khi click nút 'Not Now' thông thường, thử JS: {e}")
                    driver.execute_script("arguments[0].click();", turn_on_notifications_not_now_button)
        except Exception as e:
            print(f"[DEBUG] Không tìm thấy hoặc không thể click nút 'Not Now' (thông báo) cho {username}: {e}")

    def handle_recaptcha(self, driver, username):
        """Xử lý reCAPTCHA khi gặp phải."""
        try:
            # Kiểm tra xem có reCAPTCHA không
            recaptcha_frame = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='recaptcha']"))
            )
            print(f"[DEBUG] Phát hiện reCAPTCHA cho tài khoản {username}")

            # Chuyển đến frame của reCAPTCHA
            driver.switch_to.frame(recaptcha_frame)

            # Lấy site key của reCAPTCHA - thêm nhiều cách tìm kiếm
            site_key = None
            try:
                site_key = driver.find_element(By.CLASS_NAME, "g-recaptcha").get_attribute("data-sitekey")
            except:
                try:
                    site_key = driver.find_element(By.CSS_SELECTOR, "[data-sitekey]").get_attribute("data-sitekey")
                except:
                    try:
                        site_key = driver.find_element(By.CSS_SELECTOR, "div[data-sitekey]").get_attribute("data-sitekey")
                    except:
                        print(f"[ERROR] Không thể lấy site key của reCAPTCHA cho {username}")
                        return False

            if not site_key:
                print(f"[ERROR] Không tìm thấy site key của reCAPTCHA cho {username}")
                return False

            print(f"[DEBUG] Site key của reCAPTCHA: {site_key}")

            # Chuyển về frame chính
            driver.switch_to.default_content()

            # Gọi API 2captcha để giải captcha
            solver = TwoCaptcha(self.TWO_CAPTCHA_API_KEY)
            try:
                result = solver.recaptcha(
                    sitekey=site_key,
                    url=driver.current_url,
                )
                print(f"[DEBUG] Đã nhận kết quả từ 2captcha cho {username}")

                # Điền kết quả vào reCAPTCHA
                driver.execute_script(
                    f'document.getElementById("g-recaptcha-response").innerHTML="{result["code"]}";'
                )
                print(f"[DEBUG] Đã điền kết quả reCAPTCHA cho {username}")

                # Submit form
                # Có thể cần tìm lại nút submit nếu nó nằm ngoài reCAPTCHA frame
                submit_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
                )
                submit_button.click()
                print(f"[DEBUG] Đã submit form sau khi giải reCAPTCHA cho {username}")

                # Đợi một chút để xem kết quả
                time.sleep(3)
                return True

            except Exception as e:
                print(f"[ERROR] Lỗi khi giải reCAPTCHA cho {username}: {e}")
                return False

        except TimeoutException:
            print(f"[DEBUG] Không tìm thấy reCAPTCHA cho {username}")
            return True  # Không có reCAPTCHA, coi như thành công
        except Exception as e:
            print(f"[ERROR] Lỗi không xác định khi xử lý reCAPTCHA cho {username}: {e}")
            return False

    def verify_login_success(self, driver, username):
        """Kiểm tra xem đăng nhập đã thành công hay chưa."""
        try:
            # Kiểm tra URL hiện tại - nếu không còn là trang login/accounts thì có thể đã thành công
            if "instagram.com/accounts/login" not in driver.current_url and \
               "instagram.com/challenge" not in driver.current_url:
                # Tìm kiếm một phần tử phổ biến trên trang chủ Instagram sau khi đăng nhập
                # Ví dụ: icon home, hoặc tên người dùng ở góc trên bên phải
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//a[@href='/']//div[@role='link'] | //a[@href='/']//div[contains(@class, 'x1i10w56 x1qjc9v5 x78zum5 xdt5ytf x1ad0ptg x1f7z002 x2lahp3 x18cjm0z x1gfvlkf x1c4vz4f x2lahp3 x1gfvlkf x1c4vz4f')]"))
                )
                print(f"[DEBUG] Đã tìm thấy phần tử xác nhận đăng nhập thành công cho {username}.")
                return True
            else:
                print(f"[DEBUG] URL vẫn là trang đăng nhập hoặc challenge cho {username}: {driver.current_url}")
                return False
        except TimeoutException:
            print(f"[DEBUG] Không tìm thấy phần tử xác nhận đăng nhập thành công trong thời gian chờ cho {username}.")
            return False
        except Exception as e:
            print(f"[ERROR] Lỗi khi xác minh đăng nhập thành công cho {username}: {e}")
            return False 