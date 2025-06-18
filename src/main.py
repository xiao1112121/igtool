import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QTabWidget,
                             QWidget, QVBoxLayout, QStyleFactory, QLabel, QHBoxLayout, QFrame)
from PySide6.QtGui import QAction, QPixmap
import os

# Thêm thư mục gốc của dự án vào sys.path để cho phép import các module trong src
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print(f"[DEBUG] main.py: Current file directory: {os.path.dirname(__file__)}")
print(f"[DEBUG] main.py: Project root calculated: {project_root}")
print(f"[DEBUG] main.py: sys.path after modification: {sys.path}")
print("[DEBUG] main.py: Bắt đầu nhập module...")

# Thêm đường dẫn thư mục 'ui' vào sys.path (đã bị comment bỏ vì sử dụng import tuyệt đối)
# script_dir = os.path.dirname(__file__)
# ui_dir = os.path.join(script_dir, 'ui')
# if ui_dir not in sys.path:
#     sys.path.append(ui_dir)

# print(f"[DEBUG] main.py: sys.path sau khi thêm ui_dir: {sys.path}")

try:
    from src.ui.account_management import AccountManagementTab
    print("[DEBUG] main.py: Đã nhập AccountManagementTab.")
except ImportError as e:
    print(f"[ERROR] main.py: Lỗi khi nhập AccountManagementTab: {e}")
    sys.exit(1)

try:
    from src.ui.proxy_management import ProxyManagementTab
    print("[DEBUG] main.py: Đã nhập ProxyManagementTab.")
except ImportError as e:
    print(f"[ERROR] main.py: Lỗi khi nhập ProxyManagementTab: {e}")
    sys.exit(1)

try:
    from src.ui.messaging import MessagingTab
    print("[DEBUG] main.py: Đã nhập MessagingTab.")
except ImportError as e:
    print(f"[ERROR] main.py: Lỗi khi nhập MessagingTab: {e}")
    sys.exit(1)
# Removed unused import of HistoryLogTab
print("[DEBUG] main.py: Bỏ qua nhập HistoryLogTab vì không được sử dụng.")

try:
    from src.ui.data_scanner import DataScannerTab
    print("[DEBUG] main.py: Đã nhập DataScannerTab.")
except ImportError as e:
    print(f"[ERROR] main.py: Lỗi khi nhập DataScannerTab: {e}")
    sys.exit(1)

try:
    from src.ui.pixel_ruler import PixelRulerOverlay
    print("[DEBUG] main.py: Đã nhập PixelRulerOverlay.")
except ImportError as e:
    print(f"[ERROR] main.py: Lỗi khi nhập PixelRulerOverlay: {e}")
    # Không thoát ứng dụng nếu không nhập được thước kẻ, chỉ thông báo lỗi

print("[DEBUG] main.py: Tất cả các module đã được nhập thành công.")
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.pixel_ruler = None
        print("[DEBUG] MainWindow: Bắt đầu khởi tạo.")
        self.setWindowTitle("Instagram Automation Tool")
        self.setGeometry(100, 100, 1200, 800)
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header (logo + nền)
        header = QFrame()
        header.setFixedHeight(80)
        header.setStyleSheet("background-image: url('cityline.png'); background-repeat: repeat-x; background-position: top center; background-color: #eaf6ff; border: none;")
        layout.addWidget(header)

        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        print("[DEBUG] MainWindow: Đang khởi tạo AccountManagementTab.")
        try:
            self.account_tab = AccountManagementTab()
            self.tab_widget.addTab(self.account_tab, "Quản lý Tài khoản")
            print("[DEBUG] MainWindow: Đã khởi tạo AccountManagementTab thành công.")
        except Exception as e:
            print(f"[ERROR] MainWindow: Lỗi khi khởi tạo AccountManagementTab: {e}")
            import traceback
            print("[ERROR] MainWindow: Traceback chi tiết:")
            traceback.print_exc()
            self.account_tab = None # Đảm bảo account_tab là None nếu khởi tạo thất bại
        
        print("[DEBUG] MainWindow: Đang khởi tạo MessagingTab.")
        try:
            self.messaging_tab = MessagingTab(self.account_tab)
            self.tab_widget.addTab(self.messaging_tab, "Nhắn tin")
            print("[DEBUG] MainWindow: Đã khởi tạo MessagingTab thành công.")   
        except Exception as e:
            print(f"[ERROR] MainWindow: Lỗi khi khởi tạo MessagingTab: {e}")

        print("[DEBUG] MainWindow: Đang khởi tạo DataScannerTab.")
        try:
            self.scanner_tab = DataScannerTab()
            self.tab_widget.addTab(self.scanner_tab, "Quét dữ liệu")
            print("[DEBUG] MainWindow: Đã khởi tạo DataScannerTab thành công.")
        except Exception as e:
            print(f"[ERROR] MainWindow: Lỗi khi khởi tạo DataScannerTab: {e}")

        print("[DEBUG] MainWindow: Đang khởi tạo ProxyManagementTab.")
        try:
            self.proxy_tab = ProxyManagementTab()
            self.tab_widget.addTab(self.proxy_tab, "Quản lý Proxy")
            print("[DEBUG] MainWindow: Đã khởi tạo ProxyManagementTab thành công.") 
        except Exception as e:
            print(f"[ERROR] MainWindow: Lỗi khi khởi tạo ProxyManagementTab: {e}")

        # Kết nối tín hiệu proxy_updated từ proxy_tab đến account_tab
        print("[DEBUG] MainWindow: Đang kết nối tín hiệu proxy_updated.")
        try:
            # self.proxy_tab.proxy_updated.connect(self.account_tab.sync_proxy_data) # Bỏ qua vì phiên bản cũ không có sync_proxy_data
            print("[DEBUG] MainWindow: Đã bỏ qua kết nối tín hiệu proxy_updated cho phiên bản cũ.")
        except Exception as e:
            print(f"[ERROR] MainWindow: Lỗi khi kết nối tín hiệu proxy_updated: {e}")

        print("[DEBUG] MainWindow: Hoàn tất khởi tạo MainWindow.")

    def toggle_pixel_ruler(self, checked: bool) -> None:
        if checked:
            if self.pixel_ruler is None:
                self.pixel_ruler = PixelRulerOverlay(parent=self) # Truyền MainWindow làm parent widget
                self.pixel_ruler.showFullScreen() # Hiển thị toàn màn hình
            else:
                self.pixel_ruler.show() # Chỉ hiện lại nếu đã tồn tại
        else:
            if self.pixel_ruler is not None:
                self.pixel_ruler.hide()

    def closeEvent(self, event):
        if self.pixel_ruler is not None:
            self.pixel_ruler.deleteLater() # Xóa widget thước kẻ
        super().closeEvent(event)

def apply_qss(app, filename="src/style.qss"):
    print(f"[DEBUG] apply_qss: Đang cố gắng đọc file CSS: {filename}")
    try:
        with open(filename, "r", encoding="utf-8") as f:
            stylesheet = f.read()
            app.setStyleSheet(stylesheet)
        print(f"[DEBUG] apply_qss: Đã áp dụng style từ {filename}")
    except FileNotFoundError:
        print(f"[ERROR] apply_qss: File CSS không tìm thấy tại {filename}")
    except Exception as e:
        print(f"[ERROR] apply_qss: Lỗi khi đọc hoặc áp dụng CSS: {e}")

if __name__ == "__main__":
    print("[DEBUG] main: Bắt đầu thực thi __main__.")
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion"))
    print("[DEBUG] main: Đã tạo QApplication.")
    
    # Áp dụng CSS
    apply_qss(app)
    print("[DEBUG] main: Đã gọi apply_qss.")

    main_window = MainWindow()
    print("[DEBUG] main: Đã tạo MainWindow.")
    main_window.show()
    print("[DEBUG] main: Đã gọi main_window.show().")
    
    sys.exit(app.exec())
    print("[DEBUG] main: Đã thoát ứng dụng.") 


