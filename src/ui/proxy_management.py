from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QComboBox, QLabel, QLineEdit, QHeaderView, QGroupBox, QSizePolicy, QFileDialog, QMessageBox, QInputDialog, QFrame, QTextEdit, QProgressBar, QCheckBox, QSpinBox, QScrollArea, QSplitter, QTabWidget, QApplication, QStyledItemDelegate, QMenu)
from PySide6.QtCore import Qt, QThread, Signal, QMutex, QTimer, QSize, QModelIndex, QRect, QEvent
from PySide6.QtGui import QFont, QIcon, QPixmap, QColor, QPalette, QPainter, QPen
import csv
import os
import requests
import threading
import time
from urllib.parse import urlparse
import random
import json
from src.ui.context_menus import ProxyContextMenu

# Danh sách các website để test proxy
TEST_WEBSITES = [
    'https://www.google.com',
    'https://www.facebook.com',
    'https://www.instagram.com',
    'https://www.youtube.com',
    'https://www.amazon.com'
]

class ProxyChecker(QThread):
    finished = Signal(int, str, str, str)  # row, status, speed, note
    
    def __init__(self, row, proxy, proxy_type, test_url=None):
        super().__init__()
        self.row = row
        self.proxy = proxy
        self.proxy_type = proxy_type
        self.test_url = test_url
        self._is_running = True
        self.mutex = QMutex()
        
    def stop(self):
        self.mutex.lock()
        self._is_running = False
        self.mutex.unlock()
        
    def is_running(self):
        self.mutex.lock()
        running = self._is_running
        self.mutex.unlock()
        return running
        
    def run(self):
        try:
            # Parse proxy string
            parts = self.proxy.split(':')
            if len(parts) == 2:
                host, port = parts
                proxies = {
                    'http': f'{self.proxy_type.lower()}://{host}:{port}',
                    'https': f'{self.proxy_type.lower()}://{host}:{port}'
                }
            else:
                host, port, user, password = parts
                proxies = {
                    'http': f'{self.proxy_type.lower()}://{user}:{password}@{host}:{port}',
                    'https': f'{self.proxy_type.lower()}://{user}:{password}@{host}:{port}'
                }
            
            # Test proxy với website ngẫu nhiên
            url = self.test_url if self.test_url else random.choice(TEST_WEBSITES)
            start_time = time.time()
            
            if not self.is_running():
                return
                
            response = requests.get(url, 
                                 proxies=proxies, 
                                 timeout=10,
                                 verify=False)
                                 
            if not self.is_running():
                return
                
            end_time = time.time()
            
            if response.status_code == 200:
                speed = f"{(end_time - start_time):.2f}s"
                self.finished.emit(self.row, "Hoạt động", speed, f"Test: {urlparse(url).netloc}")
            else:
                self.finished.emit(self.row, "Lỗi", "", f"Status code: {response.status_code}")
                
        except Exception as e:
            if self.is_running():
                self.finished.emit(self.row, "Lỗi", "", str(e))

class ProxyManagementTab(QWidget):
    proxy_updated = Signal()  # Thêm tín hiệu proxy_updated
    def __init__(self):
        super().__init__()
        self.proxy_data = []
        self.checker_threads = []  # Lưu trữ các thread đang chạy
        self.init_ui()
        self.load_proxy_status()  # Thay vì chỉ import_default_proxy_files

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(12, 12, 12, 12)
        # Sidebar (10%)
        sidebar_box = QGroupBox("Chức năng")
        sidebar_box.setFont(QFont("Segoe UI Semibold", 14))
        sidebar_layout = QVBoxLayout(sidebar_box)
        sidebar_layout.setSpacing(10)
        sidebar_layout.setContentsMargins(12, 24, 12, 12)
        btn_add_proxy = QPushButton("Thêm proxy")
        btn_add_proxy.setFont(QFont("Segoe UI Semibold", 12))
        btn_add_proxy.clicked.connect(self.add_proxy_dialog)
        btn_import = QPushButton("Import .txt/.csv")
        btn_import.setFont(QFont("Segoe UI Semibold", 12))
        btn_import.clicked.connect(self.import_proxy_file)
        btn_check = QPushButton("Check Proxy")
        btn_check.setFont(QFont("Segoe UI Semibold", 12))
        btn_check.clicked.connect(self.check_proxies)
        btn_check_all = QPushButton("Check Tất Cả")
        btn_check_all.setFont(QFont("Segoe UI Semibold", 12))
        btn_check_all.clicked.connect(self.check_all_proxies)
        btn_sort_speed = QPushButton("Sắp xếp theo tốc độ")
        btn_sort_speed.setFont(QFont("Segoe UI Semibold", 12))
        btn_sort_speed.clicked.connect(self.sort_by_speed)
        btn_export_alive = QPushButton("Xuất proxy hoạt động")
        btn_export_alive.setFont(QFont("Segoe UI Semibold", 12))
        btn_export_alive.clicked.connect(self.export_alive_proxies)
        btn_delete_error = QPushButton("Xóa proxy lỗi")
        btn_delete_error.setFont(QFont("Segoe UI Semibold", 12))
        btn_delete_error.clicked.connect(self.delete_error_proxies)
        btn_delete = QPushButton("Xóa proxy đã chọn")
        btn_delete.setFont(QFont("Segoe UI Semibold", 12))
        btn_delete.clicked.connect(self.delete_selected_proxies)
        sidebar_layout.addWidget(btn_add_proxy)
        sidebar_layout.addWidget(btn_import)
        sidebar_layout.addWidget(btn_check)
        sidebar_layout.addWidget(btn_check_all)
        sidebar_layout.addWidget(btn_sort_speed)
        sidebar_layout.addWidget(btn_export_alive)
        sidebar_layout.addWidget(btn_delete_error)
        sidebar_layout.addWidget(btn_delete)
        sidebar_layout.addStretch()
        sidebar_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        # Nội dung chính (20%)
        config_box = QGroupBox("Cấu hình proxy")
        config_box.setFont(QFont("Segoe UI Semibold", 14))
        config_layout = QVBoxLayout(config_box)
        config_layout.setSpacing(10)
        config_layout.setContentsMargins(12, 24, 12, 12)
        # Thêm combobox lọc trạng thái
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Lọc theo trạng thái:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems(["Tất cả", "Hoạt động", "Lỗi", "Chưa kiểm tra"])
        self.status_filter.currentTextChanged.connect(self.filter_proxies)
        filter_layout.addWidget(self.status_filter)
        config_layout.addLayout(filter_layout)
        # Thêm ô nhập website test
        website_layout = QHBoxLayout()
        website_layout.addWidget(QLabel("Website test:"))
        self.website_input = QLineEdit()
        self.website_input.setText("https://www.instagram.com")
        self.website_input.setDisabled(True)
        website_layout.addWidget(self.website_input)
        config_layout.addLayout(website_layout)
        label_type = QLabel("Loại proxy:")
        label_type.setFont(QFont("Segoe UI", 12))
        self.combo_type = QComboBox()
        self.combo_type.setFont(QFont("Segoe UI", 12))
        self.combo_type.addItems(["HTTP", "SOCKS4", "SOCKS5"])
        label_note = QLabel("Chỉ nhập proxy hợp lệ, hỗ trợ định dạng: ip:port hoặc ip:port:user:pass")
        label_note.setFont(QFont("Segoe UI", 10.5))
        label_note.setStyleSheet("color: #666666; font-style: italic;")
        config_layout.addWidget(label_type)
        config_layout.addWidget(self.combo_type)
        config_layout.addWidget(label_note)
        config_layout.addStretch()
        config_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        # Bảng dữ liệu (70%)
        table_box = QGroupBox("Danh sách proxy")
        table_box.setFont(QFont("Segoe UI Semibold", 14))
        table_layout = QVBoxLayout(table_box)
        table_layout.setSpacing(8)
        table_layout.setContentsMargins(12, 24, 12, 12)
        self.proxy_table = QTableWidget()
        self.proxy_table.setColumnCount(7)
        self.proxy_table.setHorizontalHeaderLabels(["STT", "Proxy", "Loại", "Trạng thái", "Tốc độ", "Ghi chú", "Đã gán cho tài khoản"])
        header = self.proxy_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.resizeSection(0, 36)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.Stretch)
        self.proxy_table.verticalHeader().setVisible(False)
        header.setStretchLastSection(True)
        self.proxy_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.proxy_table.verticalHeader().setDefaultSectionSize(32)
        self.proxy_table.horizontalHeader().setFixedHeight(30)
        table_layout.addWidget(self.proxy_table)
        table_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # Thêm vào layout chính với stretch mới
        main_layout.addWidget(sidebar_box, stretch=15)
        main_layout.addWidget(config_box, stretch=20)
        main_layout.addWidget(table_box, stretch=65)
        self.update_table()

    def add_proxy_dialog(self):
        text, ok = QInputDialog.getText(self, "Thêm proxy", "Nhập proxy (ip:port hoặc ip:port:user:pass):")
        if ok and text.strip():
            proxy_type = self.combo_type.currentText()
            if self.validate_proxy(text.strip()):
                self.proxy_data.append({
                    'proxy': text.strip(),
                    'type': proxy_type,
                    'status': 'Chưa kiểm tra',
                    'speed': '',
                    'note': ''
                })
                self.update_table()
                self.save_proxy_status()
                QMessageBox.information(self, "Thành công", "Đã thêm proxy mới!")
            else:
                QMessageBox.warning(self, "Lỗi", "Proxy không hợp lệ!")

    def import_proxy_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Chọn file proxy", "", "Text/CSV Files (*.txt *.csv)")
        if file_path:
            count = 0
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f) if file_path.endswith('.csv') else (line.split() for line in f)
                for row in reader:
                    proxy = row[0] if isinstance(row, list) else row[0]
                    if self.validate_proxy(proxy):
                        self.proxy_data.append({
                            'proxy': proxy,
                            'type': self.combo_type.currentText(),
                            'status': 'Chưa kiểm tra',
                            'speed': '',
                            'note': ''
                        })
                        count += 1
            self.update_table()
            self.save_proxy_status()
            QMessageBox.information(self, "Import proxy", f"Đã import {count} proxy hợp lệ!")

    def delete_selected_proxies(self):
        selected = set(idx.row() for idx in self.proxy_table.selectedIndexes())
        if not selected:
            QMessageBox.warning(self, "Lỗi", "Hãy chọn proxy để xóa!")
            return
        self.proxy_data = [p for i, p in enumerate(self.proxy_data) if i not in selected]
        self.update_table()
        self.save_proxy_status()
        QMessageBox.information(self, "Xóa proxy", "Đã xóa proxy đã chọn!")

    def validate_proxy(self, proxy):
        # Đơn giản: kiểm tra có dạng ip:port hoặc ip:port:user:pass
        parts = proxy.split(':')
        return len(parts) == 2 or len(parts) == 4

    def update_table(self):
        self.proxy_table.setRowCount(len(self.proxy_data))
        for i, p in enumerate(self.proxy_data):
            self.proxy_table.setItem(i, 0, QTableWidgetItem(str(i+1)))
            self.proxy_table.setItem(i, 1, QTableWidgetItem(p['proxy']))
            self.proxy_table.setItem(i, 2, QTableWidgetItem(p['type']))
            self.proxy_table.setItem(i, 3, QTableWidgetItem(p['status']))
            self.proxy_table.setItem(i, 4, QTableWidgetItem(p['speed']))
            self.proxy_table.setItem(i, 5, QTableWidgetItem(p['note']))
            self.proxy_table.setItem(i, 6, QTableWidgetItem(p.get('assigned_account', '')))

    def load_proxy_status(self):
        if os.path.exists('proxy_status.json'):
            with open('proxy_status.json', 'r', encoding='utf-8') as f:
                self.proxy_data = json.load(f)
            self.update_table()
        else:
            self.import_default_proxy_files()

    def save_proxy_status(self):
        with open('proxy_status.json', 'w', encoding='utf-8') as f:
            json.dump(self.proxy_data, f, ensure_ascii=False, indent=2)

    def import_default_proxy_files(self):
        base_dir = os.path.abspath(os.path.dirname(__file__))
        for fname in ["proxy.txt", "proxy.csv"]:
            fpath = os.path.join(base_dir, "..", "..", fname)
            if os.path.exists(fpath):
                count = 0
                with open(fpath, "r", encoding="utf-8") as f:
                    if fname.endswith('.csv'):
                        reader = csv.reader(f)
                        for row in reader:
                            proxy = row[0] if isinstance(row, list) else row[0]
                            if self.validate_proxy(proxy):
                                self.proxy_data.append({
                                    'proxy': proxy,
                                    'type': self.combo_type.currentText(),
                                    'status': 'Chưa kiểm tra',
                                    'speed': '',
                                    'note': '',
                                    'assigned_account': ''
                                })
                                count += 1
                    else:
                        for line in f:
                            proxy = line.strip()
                            if self.validate_proxy(proxy):
                                self.proxy_data.append({
                                    'proxy': proxy,
                                    'type': self.combo_type.currentText(),
                                    'status': 'Chưa kiểm tra',
                                    'speed': '',
                                    'note': '',
                                    'assigned_account': ''
                                })
                                count += 1
                if count > 0:
                    self.update_table()
                    self.save_proxy_status()

    def get_test_url(self):
        return 'https://www.instagram.com'

    def check_proxies(self):
        selected = set(idx.row() for idx in self.proxy_table.selectedIndexes())
        if not selected:
            QMessageBox.warning(self, "Lỗi", "Hãy chọn proxy để kiểm tra!")
            return
        for i in range(self.proxy_table.rowCount()):
            if i in selected:
                self.proxy_table.setItem(i, 3, QTableWidgetItem("Đang kiểm tra..."))
                self.proxy_table.setItem(i, 4, QTableWidgetItem(""))
                self.proxy_table.setItem(i, 5, QTableWidgetItem(""))
        for row in selected:
            proxy = self.proxy_data[row]['proxy']
            proxy_type = self.proxy_data[row]['type']
            checker = ProxyChecker(row, proxy, proxy_type, self.get_test_url())
            checker.finished.connect(self.update_proxy_status)
            self.checker_threads.append(checker)
            checker.start()

    def check_all_proxies(self):
        if not self.proxy_data:
            QMessageBox.warning(self, "Lỗi", "Không có proxy để kiểm tra!")
            return
        self.stop_all_checkers()
        for i in range(self.proxy_table.rowCount()):
            self.proxy_table.setItem(i, 3, QTableWidgetItem("Đang kiểm tra..."))
            self.proxy_table.setItem(i, 4, QTableWidgetItem(""))
            self.proxy_table.setItem(i, 5, QTableWidgetItem(""))
        for row in range(len(self.proxy_data)):
            proxy = self.proxy_data[row]['proxy']
            proxy_type = self.proxy_data[row]['type']
            checker = ProxyChecker(row, proxy, proxy_type, self.get_test_url())
            checker.finished.connect(self.update_proxy_status)
            self.checker_threads.append(checker)
            checker.start()

    def stop_all_checkers(self):
        # Dừng tất cả các thread đang chạy
        for checker in self.checker_threads:
            checker.stop()
            checker.wait()  # Đợi thread kết thúc
        self.checker_threads.clear()
        
    def closeEvent(self, event):
        # Dừng tất cả các thread khi đóng tab
        self.stop_all_checkers()
        super().closeEvent(event)
        
    def filter_proxies(self):
        status = self.status_filter.currentText()
        for row in range(self.proxy_table.rowCount()):
            if status == "Tất cả":
                self.proxy_table.setRowHidden(row, False)
            else:
                current_status = self.proxy_data[row]['status']
                self.proxy_table.setRowHidden(row, current_status != status)

    def sort_by_speed(self):
        # Lọc ra các proxy đã kiểm tra và có tốc độ
        checked_proxies = []
        unchecked_proxies = []
        
        for proxy in self.proxy_data:
            if proxy['status'] == 'Hoạt động' and proxy['speed']:
                # Chuyển đổi tốc độ từ string (ví dụ: "1.23s") sang float
                try:
                    speed = float(proxy['speed'].replace('s', ''))
                    checked_proxies.append((proxy, speed))
                except ValueError:
                    unchecked_proxies.append((proxy, float('inf')))
            else:
                unchecked_proxies.append((proxy, float('inf')))
        
        # Sắp xếp các proxy đã kiểm tra theo tốc độ
        checked_proxies.sort(key=lambda x: x[1])
        
        # Kết hợp lại danh sách: proxy đã kiểm tra (sắp xếp) + proxy chưa kiểm tra
        self.proxy_data = [p[0] for p in checked_proxies] + [p[0] for p in unchecked_proxies]
        
        # Cập nhật bảng
        self.update_table()
        
        # Hiển thị thông báo
        if checked_proxies:
            QMessageBox.information(self, "Sắp xếp", 
                f"Đã sắp xếp {len(checked_proxies)} proxy theo tốc độ phản hồi.\n"
                f"Proxy nhanh nhất: {checked_proxies[0][0]['proxy']} ({checked_proxies[0][0]['speed']})\n"
                f"Proxy chậm nhất: {checked_proxies[-1][0]['proxy']} ({checked_proxies[-1][0]['speed']})")
        else:
            QMessageBox.warning(self, "Sắp xếp", "Không có proxy nào đã được kiểm tra tốc độ!")

    def update_proxy_status(self, row, status, speed, note):
        if row < len(self.proxy_data):  # Kiểm tra row có hợp lệ
            self.proxy_data[row]['status'] = status
            self.proxy_data[row]['speed'] = speed
            self.proxy_data[row]['note'] = note
            self.update_table()
            self.save_proxy_status()
            self.proxy_updated.emit()

    def export_alive_proxies(self):
        alive = [p['proxy'] for p in self.proxy_data if p['status'] == 'Hoạt động']
        if not alive:
            QMessageBox.warning(self, "Xuất proxy", "Không có proxy hoạt động để xuất!")
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "Lưu proxy hoạt động", "proxy_alive.txt", "Text Files (*.txt)")
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                for proxy in alive:
                    f.write(proxy + '\n')
            QMessageBox.information(self, "Xuất proxy", f"Đã lưu {len(alive)} proxy hoạt động vào file!")

    def delete_error_proxies(self):
        before = len(self.proxy_data)
        self.proxy_data = [p for p in self.proxy_data if p['status'] != 'Lỗi']
        self.update_table()
        self.save_proxy_status()
        after = len(self.proxy_data)
        QMessageBox.information(self, "Xóa proxy lỗi", f"Đã xóa {before - after} proxy lỗi khỏi danh sách!")

    def show_context_menu(self, pos):
        """Hiển thị menu chuột phải."""
        print(f"[DEBUG] show_context_menu được gọi tại vị trí: {pos}")
        menu = ProxyContextMenu(self)
        menu.exec(self.proxy_table.viewport().mapToGlobal(pos)) 