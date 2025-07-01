import sys
import os

# Apply blinker compatibility patch before any other imports
try:
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    # Apply blinker patch if available
        import blinker_patch  # Apply the patch
except Exception as e:
    print(f"[WARN] Could not apply blinker patch: {e}")

from PySide6.QtWidgets import (QApplication, QMainWindow, QTabWidget,
                             QWidget, QVBoxLayout, QStyleFactory, QFrame, QMessageBox)
from PySide6.QtGui import QCloseEvent
from PySide6.QtCore import QThread, QTimer
import traceback
import logging
from types import TracebackType
from typing import Optional, Any, List, Dict

# Thêm thư mục gốc của dự án vào sys.path để cho phép import các module trong src
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print(f"[DEBUG] main.py: Current file directory: {os.path.dirname(__file__)}")
print(f"[DEBUG] main.py: Project root calculated: {project_root}")
print(f"[DEBUG] main.py: sys.path after modification: {sys.path}")
print("[DEBUG] main.py: Bắt đầu nhập module...")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('application.log'),
        logging.StreamHandler()
    ]
)

# Global exception handler
def handle_exception(exc_type: type[BaseException], exc_value: BaseException, exc_traceback: Optional[TracebackType]) -> None:
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    logging.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    
    # Show user-friendly error dialog
    try:
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Lỗi ứng dụng")
        msg.setText("Ứng dụng gặp lỗi không mong muốn.")
        msg.setDetailedText(str(exc_value))
        msg.exec()
    except Exception:
        pass

sys.excepthook = handle_exception

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
    logging.error(f"Failed to import AccountManagementTab: {e}")
    sys.exit(1)

try:
    from src.ui.proxy_management import ProxyManagementTab
    print("[DEBUG] main.py: Đã nhập ProxyManagementTab.")
except ImportError as e:
    print(f"[ERROR] main.py: Lỗi khi nhập ProxyManagementTab: {e}")
    logging.error(f"Failed to import ProxyManagementTab: {e}")
    sys.exit(1)

try:
    from src.ui.messaging import MessagingTab
    print("[DEBUG] main.py: Đã nhập MessagingTab.")
except ImportError as e:
    print(f"[ERROR] main.py: Lỗi khi nhập MessagingTab: {e}")
    logging.error(f"Failed to import MessagingTab: {e}")
    sys.exit(1)
# Removed unused import of HistoryLogTab
print("[DEBUG] main.py: Bỏ qua nhập HistoryLogTab vì không được sử dụng.")

try:
    from src.ui.data_scanner import DataScannerTab
    print("[DEBUG] main.py: Đã nhập DataScannerTab.")
except ImportError as e:
    print(f"[ERROR] main.py: Lỗi khi nhập DataScannerTab: {e}")
    logging.error(f"Failed to import DataScannerTab: {e}")
    DataScannerTab = None

try:
    from src.ui.pixel_ruler import PixelRulerOverlay
    print("[DEBUG] main.py: Đã nhập PixelRulerOverlay.")
    pixel_ruler_available = True
except ImportError as e:
    print(f"[ERROR] main.py: Lỗi khi nhập PixelRulerOverlay: {e}")
    logging.warning(f"PixelRulerOverlay not available: {e}")
    pixel_ruler_available = False
    PixelRulerOverlay = None  # Set to None to avoid unbound variable error

print("[DEBUG] main.py: Tất cả các module đã được nhập thành công.")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.pixel_ruler = None
        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self.cleanup_resources)
        self.cleanup_timer.start(30000)  # Cleanup every 30 seconds
        
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
        # Fix image path
        image_path = os.path.join(os.path.dirname(__file__), 'cityline.png')
        if os.path.exists(image_path):
            header.setStyleSheet(f"""
                background-image: url('{image_path.replace(os.sep, '/')}');
                background-repeat: repeat-x;
                background-position: top center;
                background-color: #eaf6ff;
                border: none;
                border-bottom: 2px solid #1976D2;
                border-radius: 0px;
            """)
        else:
            # Fallback gradient header
            header.setStyleSheet("""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #E3F2FD, stop:0.5 #BBDEFB, stop:1 #90CAF9);
                border: none;
                border-bottom: 2px solid #1976D2;
                border-radius: 0px;
            """)
        layout.addWidget(header)

        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Initialize tabs with better error handling
        self.initialize_tabs()

        print("[DEBUG] MainWindow: Hoàn tất khởi tạo MainWindow.")

    def initialize_tabs(self):
        """Initialize all tabs with proper error handling"""
        # Account Management Tab
        print("[DEBUG] MainWindow: Đang khởi tạo AccountManagementTab.")
        try:
            self.account_tab = AccountManagementTab()
            
            # Apply quick fix for login hanging
            try:
                # Set shorter timeouts for the account tab
                if hasattr(self.account_tab, 'init_driver'):
                    original_init = self.account_tab.init_driver
                    def init_driver_with_timeout(proxy: Optional[Dict[str, Any]] = None, username: Optional[str] = None):
                        driver = original_init(proxy, username)
                        if driver:
                            try:
                                driver.set_page_load_timeout(15)  # 15 second page load timeout
                                driver.implicitly_wait(5)        # 5 second implicit wait
                                driver.set_script_timeout(12)    # 12 second script timeout
                                print("[DEBUG] MainWindow: Đã áp dụng timeout limits cho WebDriver.")
                            except Exception as timeout_error:
                                print(f"[WARN] MainWindow: Không thể áp dụng timeout: {timeout_error}")
                        return driver
                    self.account_tab.init_driver = init_driver_with_timeout
                print("[DEBUG] MainWindow: Đã áp dụng timeout limits cho WebDriver.")
            except Exception as e:
                print(f"[WARN] MainWindow: Không thể áp dụng timeout limits: {e}")
            
            self.tab_widget.addTab(self.account_tab, "Quản lý Tài khoản")
            print("[DEBUG] MainWindow: Đã khởi tạo AccountManagementTab thành công.")
        except Exception as e:
            print(f"[ERROR] MainWindow: Lỗi khi khởi tạo AccountManagementTab: {e}")
            logging.error(f"Failed to initialize AccountManagementTab: {e}")
            traceback.print_exc()
            self.account_tab = None
            # Add placeholder tab
            placeholder = QWidget()
            self.tab_widget.addTab(placeholder, "Quản lý Tài khoản (Lỗi)")

        # Messaging Tab
        print("[DEBUG] MainWindow: Đang khởi tạo MessagingTab.")
        try:
            self.messaging_tab = MessagingTab(self.account_tab)
            self.tab_widget.addTab(self.messaging_tab, "Nhắn tin")
            print("[DEBUG] MainWindow: Đã khởi tạo MessagingTab thành công.")   
        except Exception as e:
            print(f"[ERROR] MainWindow: Lỗi khi khởi tạo MessagingTab: {e}")
            logging.error(f"Failed to initialize MessagingTab: {e}")
            self.messaging_tab = None
            placeholder = QWidget()
            self.tab_widget.addTab(placeholder, "Nhắn tin (Lỗi)")

        # Data Scanner Tab
        print("[DEBUG] MainWindow: Đang khởi tạo DataScannerTab.")
        try:
            if DataScannerTab is not None:
                # ⭐ TRUYỀN REFERENCE CỦA ACCOUNT TAB VÀO DATA SCANNER
                self.scanner_tab = DataScannerTab(self.account_tab)
                self.tab_widget.addTab(self.scanner_tab, "Quét dữ liệu")
                print("[DEBUG] MainWindow: Đã khởi tạo DataScannerTab thành công.")
            else:
                print("[WARN] MainWindow: DataScannerTab không khả dụng.")
                self.scanner_tab = None
                placeholder = QWidget()
                self.tab_widget.addTab(placeholder, "Quét dữ liệu (Không khả dụng)")
        except Exception as e:
            print(f"[ERROR] MainWindow: Lỗi khi khởi tạo DataScannerTab: {e}")
            logging.error(f"Failed to initialize DataScannerTab: {e}")
            self.scanner_tab = None
            placeholder = QWidget()
            self.tab_widget.addTab(placeholder, "Quét dữ liệu (Lỗi)")

        # Proxy Management Tab
        print("[DEBUG] MainWindow: Đang khởi tạo ProxyManagementTab.")
        try:
            self.proxy_tab = ProxyManagementTab()
            self.tab_widget.addTab(self.proxy_tab, "Quản lý Proxy")
            print("[DEBUG] MainWindow: Đã khởi tạo ProxyManagementTab thành công.") 
        except Exception as e:
            print(f"[ERROR] MainWindow: Lỗi khi khởi tạo ProxyManagementTab: {e}")
            logging.error(f"Failed to initialize ProxyManagementTab: {e}")
            self.proxy_tab = None
            placeholder = QWidget()
            self.tab_widget.addTab(placeholder, "Quản lý Proxy (Lỗi)")

        # Connect signals if both tabs are available
        if hasattr(self, 'proxy_tab') and hasattr(self, 'account_tab') and self.proxy_tab and self.account_tab:
            try:
                # Connect proxy_updated signal if it exists
                if hasattr(self.proxy_tab, 'proxy_updated') and hasattr(self.account_tab, 'sync_proxy_data'):
                    self.proxy_tab.proxy_updated.connect(self.account_tab.sync_proxy_data)
                    print("[DEBUG] MainWindow: Đã kết nối tín hiệu proxy_updated.")
                else:
                    print("[DEBUG] MainWindow: Bỏ qua kết nối tín hiệu proxy_updated (không có sync_proxy_data).")
            except Exception as e:
                print(f"[ERROR] MainWindow: Lỗi khi kết nối tín hiệu proxy_updated: {e}")
                logging.error(f"Failed to connect proxy_updated signal: {e}")

        # ⭐ ĐỒNG BỘ FOLDERS GIỮA CÁC TAB
        try:
            # Connect folders_updated signal từ account_tab tới data_scanner_tab
            if hasattr(self, 'account_tab') and hasattr(self, 'scanner_tab') and self.account_tab and self.scanner_tab:
                if hasattr(self.account_tab, 'folders_updated') and hasattr(self.scanner_tab, 'on_folders_updated'):
                    self.account_tab.folders_updated.connect(self.scanner_tab.on_folders_updated)
                    print("[DEBUG] MainWindow: Đã kết nối tín hiệu folders_updated cho DataScannerTab.")
                else:
                    print("[DEBUG] MainWindow: Bỏ qua kết nối folders_updated cho DataScannerTab (method không tồn tại).")
            
            # Connect folders_updated signal từ account_tab tới messaging_tab
            if hasattr(self, 'account_tab') and hasattr(self, 'messaging_tab') and self.account_tab and self.messaging_tab:
                if hasattr(self.account_tab, 'folders_updated') and hasattr(self.messaging_tab, 'on_folders_updated'):
                    self.account_tab.folders_updated.connect(self.messaging_tab.on_folders_updated)
                    print("[DEBUG] MainWindow: Đã kết nối tín hiệu folders_updated cho MessagingTab.")
                else:
                    print("[DEBUG] MainWindow: Bỏ qua kết nối folders_updated cho MessagingTab (method không tồn tại).")
        except Exception as e:
            print(f"[ERROR] MainWindow: Lỗi khi kết nối tín hiệu folders_updated: {e}")
            logging.error(f"Failed to connect folders_updated signal: {e}")

    def cleanup_resources(self):
        """Periodic cleanup of resources"""
        try:
            # Cleanup drivers if account_tab exists
            if hasattr(self, 'account_tab') and self.account_tab:
                # Clean up any orphaned drivers
                if hasattr(self.account_tab, 'active_drivers'):
                    active_drivers: List[Any] = self.account_tab.active_drivers
                    for driver in list(active_drivers):
                        try:
                            if driver and hasattr(driver, 'quit'):
                                driver.quit()
                        except Exception:
                            pass
                    active_drivers.clear()
        except Exception as e:
            logging.warning(f"Error during cleanup: {e}")

    def toggle_pixel_ruler(self, checked: bool) -> None:
        if not pixel_ruler_available:
            print("[WARN] PixelRulerOverlay không khả dụng.")
            return
            
        if checked:
            if self.pixel_ruler is None:
                try:
                    if PixelRulerOverlay is not None:
                        self.pixel_ruler = PixelRulerOverlay(parent=self) # Truyền MainWindow làm parent widget
                        self.pixel_ruler.showFullScreen() # Hiển thị toàn màn hình
                except Exception as e:
                    print(f"[ERROR] Không thể tạo PixelRulerOverlay: {e}")
                    logging.error(f"Failed to create PixelRulerOverlay: {e}")
                    return
            else:
                self.pixel_ruler.show() # Chỉ hiện lại nếu đã tồn tại
        else:
            if self.pixel_ruler is not None:
                self.pixel_ruler.hide()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Properly cleanup resources when closing"""
        try:
            print("[DEBUG] MainWindow: Bắt đầu cleanup khi đóng ứng dụng...")
            
            # Stop cleanup timer
            if hasattr(self, 'cleanup_timer'):
                self.cleanup_timer.stop()
            
            # Cleanup pixel ruler
            if self.pixel_ruler is not None:
                self.pixel_ruler.deleteLater()
            
            # Cleanup account tab drivers
            if hasattr(self, 'account_tab') and self.account_tab:
                try:
                    if hasattr(self.account_tab, 'close_all_drivers'):
                        self.account_tab.close_all_drivers()
                except Exception as e:
                    logging.warning(f"Error closing drivers: {e}")
            
            # Wait for threads to finish
            QThread.msleep(1000)  # Wait 1 second for threads to cleanup
            
            print("[DEBUG] MainWindow: Hoàn tất cleanup.")
            super().closeEvent(event)
            
        except Exception as e:
            logging.error(f"Error during closeEvent: {e}")
            super().closeEvent(event)

def apply_qss(app: QApplication, use_modern: bool = True) -> None:
    """Apply stylesheet to the application with option for modern or classic theme"""
    
    # Choose stylesheet based on preference
    if use_modern:
        filename = "src/style_modern.qss"
        fallback = "src/style.qss"
    else:
        filename = "src/style.qss"
        fallback = None
    
    print(f"[DEBUG] apply_qss: Đang cố gắng đọc file CSS: {filename}")
    
    # Try primary stylesheet
    try:
        with open(filename, "r", encoding="utf-8") as f:
            stylesheet = f.read()
            app.setStyleSheet(stylesheet)
        print(f"[DEBUG] apply_qss: Đã áp dụng style từ {filename}")
        return
    except FileNotFoundError:
        print(f"[WARN] apply_qss: File CSS không tìm thấy tại {filename}")
        if fallback:
            print(f"[DEBUG] apply_qss: Thử fallback: {fallback}")
            try:
                with open(fallback, "r", encoding="utf-8") as f:
                    stylesheet = f.read()
                    app.setStyleSheet(stylesheet)
                print(f"[DEBUG] apply_qss: Đã áp dụng fallback style từ {fallback}")
                return
            except Exception as e:
                print(f"[ERROR] apply_qss: Lỗi khi đọc fallback CSS: {e}")
        logging.warning(f"CSS file not found: {filename}")
    except Exception as e:
        print(f"[ERROR] apply_qss: Lỗi khi đọc hoặc áp dụng CSS: {e}")
        logging.error(f"Error applying CSS: {e}")
    
    # Apply minimal inline styles as last resort
    minimal_style = """
    QMainWindow { background-color: #f8fafc; }
    QPushButton { 
        background: #3b82f6; 
        color: white; 
        border: none; 
        border-radius: 6px; 
        padding: 8px 16px; 
        font-weight: 500;
    }
    QPushButton:hover { background: #2563eb; }
    QGroupBox { 
        background: white; 
        border: 1px solid #e2e8f0; 
        border-radius: 8px; 
        margin-top: 8px; 
        padding-top: 12px; 
    }
    QTableWidget { 
        background: white; 
        border: 1px solid #e2e8f0; 
        border-radius: 8px; 
        gridline-color: #f1f5f9; 
    }
    """
    app.setStyleSheet(minimal_style)
    print("[DEBUG] apply_qss: Đã áp dụng minimal fallback style")

if __name__ == "__main__":
    print("[DEBUG] main: Bắt đầu thực thi __main__.")
    
    try:
        app = QApplication(sys.argv)
        app.setStyle(QStyleFactory.create("Fusion"))
        print("[DEBUG] main: Đã tạo QApplication.")
        
        # Áp dụng CSS - sử dụng style cũ để tránh lỗi
        apply_qss(app, use_modern=False)
        print("[DEBUG] main: Đã gọi apply_qss.")

        main_window = MainWindow()
        print("[DEBUG] main: Đã tạo MainWindow.")
        main_window.show()
        print("[DEBUG] main: Đã gọi main_window.show().")
        
        # Add periodic cleanup
        # Add periodic cleanup timer
        cleanup_timer: QTimer = QTimer()
        cleanup_timer.timeout.connect(lambda: None)  # Placeholder for any periodic tasks
        cleanup_timer.start(60000)  # Every minute
        
        exit_code: int = app.exec()
        print("[DEBUG] main: Ứng dụng đã thoát với mã:", exit_code)
        sys.exit(exit_code)
        
    except Exception as e:
        logging.critical(f"Critical error in main: {e}")
        print(f"[CRITICAL] main: Lỗi nghiêm trọng: {e}")
        traceback.print_exc()
        sys.exit(1) 


