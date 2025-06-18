import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QTabWidget, 
                             QWidget, QVBoxLayout)
from PySide6.QtCore import Qt

class InstagramApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Instagram Interaction Tool")
        self.setMinimumSize(1200, 800)
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Create tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Initialize tabs
        self.init_account_management_tab()
        self.init_messaging_tab()
        self.init_data_scanner_tab()
        
    def init_account_management_tab(self):
        from ui.account_management import AccountManagementTab
        self.account_tab = AccountManagementTab()
        self.tabs.addTab(self.account_tab, "Quản lý tài khoản")
        
    def init_messaging_tab(self):
        from ui.messaging import MessagingTab
        self.messaging_tab = MessagingTab()
        self.tabs.addTab(self.messaging_tab, "Nhắn tin")
        
    def init_data_scanner_tab(self):
        from ui.data_scanner import DataScannerTab
        self.scanner_tab = DataScannerTab()
        self.tabs.addTab(self.scanner_tab, "Quét dữ liệu")

def main():
    app = QApplication(sys.argv)
    window = InstagramApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 