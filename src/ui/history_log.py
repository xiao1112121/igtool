from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, 
                            QPushButton, QHBoxLayout)
from PySide6.QtCore import Qt

class HistoryLogTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        main_layout = QHBoxLayout(self) # Changed to QHBoxLayout
        
        # Left Menu Panel (15%)
        left_menu_panel = QWidget()
        left_menu_layout = QVBoxLayout(left_menu_panel)
        left_menu_layout.setContentsMargins(0, 0, 0, 0) # Remove margins for consistency
        left_menu_layout.setSpacing(0) # Remove spacing for consistency
        left_menu_layout.addStretch() # Push any future widgets to top
        main_layout.addWidget(left_menu_panel, stretch=15)

        # Right Content Panel (85%)
        right_content_panel = QWidget()
        right_content_layout = QVBoxLayout(right_content_panel)
        right_content_layout.setContentsMargins(0, 0, 0, 0) # Remove margins for consistency
        right_content_layout.setSpacing(0) # Remove spacing for consistency

        # Tạo text area để hiển thị log
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        right_content_layout.addWidget(self.log_text)
        
        # Tạo các nút điều khiển
        button_layout = QHBoxLayout()
        
        self.clear_button = QPushButton("Xóa log")
        self.clear_button.clicked.connect(self.clear_log)
        button_layout.addWidget(self.clear_button)
        
        self.save_button = QPushButton("Lưu log")
        self.save_button.clicked.connect(self.save_log)
        button_layout.addWidget(self.save_button)
        
        right_content_layout.addLayout(button_layout)
        main_layout.addWidget(right_content_panel, stretch=85)
        
    def clear_log(self):
        self.log_text.clear()
        
    def save_log(self):
        # TODO: Implement save log functionality
        pass
        
    def add_log(self, message):
        self.log_text.append(message) 