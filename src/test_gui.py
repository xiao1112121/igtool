from PySide6.QtWidgets import QApplication, QWidget, QLabel
import sys

def main():
    app = QApplication(sys.argv)
    
    window = QWidget()
    window.setWindowTitle("Test PySide6")
    window.setGeometry(100, 100, 300, 200)
    
    label = QLabel("Hello PySide6!", parent=window)
    label.move(100, 80)
    
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    print("[DEBUG] test_gui.py: Bắt đầu chạy ứng dụng PySide6 cơ bản.")
    main()
    print("[DEBUG] test_gui.py: Ứng dụng PySide6 cơ bản đã thoát.") 