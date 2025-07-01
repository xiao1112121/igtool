import sys
import os
import json
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import random
import time

# Add AI imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from ai.ai_client import get_ai_client, initialize_ai_client
from ai.telegram_bot import get_bot_manager, initialize_bot_manager

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox, QSpinBox, QSlider, QTextEdit,
    QGroupBox, QGridLayout, QHeaderView, QAbstractItemView,
    QMessageBox, QInputDialog, QProgressDialog, QFrame, QSplitter,
    QTabWidget, QCheckBox, QLineEdit, QFormLayout, QScrollArea,
    QButtonGroup, QRadioButton, QFileDialog, QDialog, QDialogButtonBox
)
from PySide6.QtCore import Qt, QTimer, Signal, Slot, QThread, QObject
from PySide6.QtGui import QColor, QPalette, QFont, QPixmap, QIcon

# ===============================================
# 🤖 AI TEST WORKER THREAD
# ===============================================

class AITestWorker(QThread):
    """Worker thread for AI testing to prevent UI blocking"""
    result_ready = Signal(str, dict, str)  # input_msg, result, personality
    error_occurred = Signal(str)  # error_message
    
    def __init__(self, ai_client, message, personality):
        super().__init__()
        self.ai_client = ai_client
        self.message = message
        self.personality = personality
        self.should_stop = False
    
    def run(self):
        """Run AI test in background thread"""
        try:
            if self.should_stop:
                return
                
            # Create event loop for async call
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(
                    self.ai_client.generate_response(
                        message=self.message,
                        personality=self.personality,
                        context="Test từ AI Management Tab"
                    )
                )
                
                if not self.should_stop:
                    self.result_ready.emit(self.message, result, self.personality)
                    
            finally:
                loop.close()
                
        except Exception as e:
            if not self.should_stop:
                self.error_occurred.emit(str(e))
    
    def stop(self):
        """Stop the worker"""
        self.should_stop = True

# ===============================================
# 🤖 AI MANAGEMENT TAB - MAIN CLASS
# ===============================================

class AIManagementTab(QWidget):
    """Tab quản lý AI tự động tương tác Telegram"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ai_accounts = []
        self.personalities = []
        self.chat_groups = []
        self.ai_accounts_file = "ai_accounts.json"
        self.personalities_file = "ai_personalities.json"
        self.chat_groups_file = "ai_chat_groups.json"
        
        # Initialize AI components
        try:
            self.ai_client = initialize_ai_client()
            self.bot_manager = initialize_bot_manager()
            self.ai_initialized = True
            print("[AI] AI components initialized successfully")
        except Exception as e:
            print(f"[AI] Failed to initialize AI components: {e}")
            self.ai_client = None
            self.bot_manager = None
            self.ai_initialized = False
        
        # Load data
        self.load_data()
        
        # Setup UI
        self.init_ui()
        self.apply_light_theme()
        
        # Setup timers
        self.setup_timers()
        
        # Worker references
        self.ai_test_worker = None
        self.progress_dialog = None
    
    def init_ui(self):
        """Khởi tạo giao diện chính"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel (30%) - AI List & Controls
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # Right panel (70%) - Configuration & Monitoring
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter ratios
        splitter.setSizes([300, 700])
        main_layout.addWidget(splitter)
    
    def create_left_panel(self):
        """Tạo panel trái - Danh sách AI"""
        panel = QFrame()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Title
        title = QLabel("🤖 TÀI KHOẢN AI")
        title.setStyleSheet("font-size: 15pt; font-weight: bold; color: #1976d2; padding: 10px; font-family: 'Segoe UI Semibold', 'Segoe UI', 'Roboto', 'Arial';")
        layout.addWidget(title)
        
        # Control buttons
        controls_layout = QHBoxLayout()
        
        btn_add = QPushButton("➕ Thêm AI")
        btn_add.clicked.connect(self.add_ai_account)
        controls_layout.addWidget(btn_add)
        
        btn_import = QPushButton("📥 Nhập")
        btn_import.clicked.connect(self.import_ai_accounts)
        controls_layout.addWidget(btn_import)
        
        btn_export = QPushButton("📤 Xuất")
        btn_export.clicked.connect(self.export_ai_accounts)
        controls_layout.addWidget(btn_export)
        
        layout.addLayout(controls_layout)
        
        # AI accounts table
        self.ai_table = QTableWidget()
        self.setup_ai_table()
        layout.addWidget(self.ai_table)
        
        # Bulk actions
        bulk_layout = QHBoxLayout()
        
        btn_start_all = QPushButton("▶️ Chạy tất cả")
        btn_start_all.clicked.connect(self.start_all_ais)
        bulk_layout.addWidget(btn_start_all)
        
        btn_stop_all = QPushButton("⏹️ Dừng tất cả")
        btn_stop_all.clicked.connect(self.stop_all_ais)
        bulk_layout.addWidget(btn_stop_all)
        
        layout.addLayout(bulk_layout)
        
        # Stats
        self.stats_label = QLabel("📊 Tổng: 0 AI | Hoạt động: 0 | Nghỉ: 0")
        self.stats_label.setStyleSheet("padding: 10px; background: #f5f5f5; border-radius: 5px; border: 1px solid #e0e0e0; font-size: 11pt; font-family: 'Segoe UI Regular', 'Segoe UI', 'Roboto', 'Arial';")
        layout.addWidget(self.stats_label)
        
        return panel
    
    def create_right_panel(self):
        """Tạo panel phải - Cấu hình & Monitoring"""
        panel = QFrame()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Tab widget for different sections
        tab_widget = QTabWidget()
        
        # Tab 1: Personality Configuration
        personality_tab = self.create_personality_tab()
        tab_widget.addTab(personality_tab, "🎭 Tính cách")
        
        # Tab 2: Group Management
        groups_tab = self.create_groups_tab()
        tab_widget.addTab(groups_tab, "👥 Nhóm")
        
        # Tab 3: Monitoring & Analytics
        monitoring_tab = self.create_monitoring_tab()
        tab_widget.addTab(monitoring_tab, "📊 Giám sát")
        
        # Tab 4: Advanced Settings
        advanced_tab = self.create_advanced_tab()
        tab_widget.addTab(advanced_tab, "⚙️ Nâng cao")
        
        layout.addWidget(tab_widget)
        
        return panel

    def setup_ai_table(self):
        """Thiết lập bảng danh sách AI"""
        self.ai_table.setColumnCount(6)
        self.ai_table.setHorizontalHeaderLabels([
            "✓", "Ảnh đại diện", "Tên", "Trạng thái", "Nhóm", "Tính cách"
        ])
        
        # Column widths
        header = self.ai_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.ai_table.setColumnWidth(0, 30)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        self.ai_table.setColumnWidth(1, 60)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        self.ai_table.setColumnWidth(3, 80)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        self.ai_table.setColumnWidth(4, 100)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        self.ai_table.setColumnWidth(5, 120)
        
        # Table settings
        self.ai_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ai_table.setAlternatingRowColors(True)
        self.ai_table.verticalHeader().setVisible(False)
        self.ai_table.setRowHeight(0, 50)
        
        # Connect signals
        self.ai_table.itemDoubleClicked.connect(self.edit_ai_account)
    
    def create_personality_tab(self):
        """Tạo tab cấu hình tính cách"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Personality presets section
        presets_group = QGroupBox("🎭 Mẫu tính cách có sẵn")
        presets_layout = QGridLayout(presets_group)
        
        # Preset buttons
        preset_names = [
            "😄 Hài hước", "😐 Nghiêm túc", "😊 Thân thiện", "🤓 Thông minh",
            "😎 Cool ngầu", "🥰 Dễ thương", "💪 Năng động", "🧘 Bình tĩnh",
            "🎉 Vui vẻ", "📚 Học thuật", "💼 Chuyên nghiệp", "🎨 Sáng tạo"
        ]
        
        self.preset_buttons = []
        for i, name in enumerate(preset_names):
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, n=name: self.select_personality_preset(n))
            presets_layout.addWidget(btn, i // 4, i % 4)
            self.preset_buttons.append(btn)
        
        layout.addWidget(presets_group)
        
        # Custom personality configuration
        custom_group = QGroupBox("⚙️ Cấu hình tùy chỉnh")
        custom_layout = QFormLayout(custom_group)
        
        # Response frequency
        self.response_freq_slider = QSlider(Qt.Horizontal)
        self.response_freq_slider.setRange(1, 10)
        self.response_freq_slider.setValue(5)
        self.response_freq_slider.valueChanged.connect(self.update_personality_config)
        freq_layout = QHBoxLayout()
        freq_layout.addWidget(QLabel("Ít nói"))
        freq_layout.addWidget(self.response_freq_slider)
        freq_layout.addWidget(QLabel("Nhiều nói"))
        custom_layout.addRow("Tần suất trả lời:", freq_layout)
        
        # Response speed
        self.response_speed_spin = QSpinBox()
        self.response_speed_spin.setRange(3, 20)
        self.response_speed_spin.setValue(5)
        self.response_speed_spin.setSuffix(" giây")
        self.response_speed_spin.valueChanged.connect(self.update_personality_config)
        custom_layout.addRow("Tốc độ phản hồi:", self.response_speed_spin)
        
        # Enthusiasm level
        self.enthusiasm_slider = QSlider(Qt.Horizontal)
        self.enthusiasm_slider.setRange(1, 10)
        self.enthusiasm_slider.setValue(5)
        self.enthusiasm_slider.valueChanged.connect(self.update_personality_config)
        enth_layout = QHBoxLayout()
        enth_layout.addWidget(QLabel("Lạnh lùng"))
        enth_layout.addWidget(self.enthusiasm_slider)
        enth_layout.addWidget(QLabel("Nhiệt tình"))
        custom_layout.addRow("Mức độ nhiệt tình:", enth_layout)
        
        # Emotional tendency
        self.emotion_combo = QComboBox()
        self.emotion_combo.addItems(["😊 Tích cực", "😐 Trung lập", "😔 Tiêu cực", "🤪 Ngẫu nhiên"])
        self.emotion_combo.currentTextChanged.connect(self.update_personality_config)
        custom_layout.addRow("Xu hướng cảm xúc:", self.emotion_combo)
        
        # Special keywords
        self.keywords_edit = QTextEdit()
        self.keywords_edit.setMaximumHeight(80)
        self.keywords_edit.setPlaceholderText("Nhập từ khóa đặc trưng, cách nhau bằng dấu phẩy...")
        self.keywords_edit.textChanged.connect(self.update_personality_config)
        custom_layout.addRow("Từ ngữ đặc trưng:", self.keywords_edit)
        
        layout.addWidget(custom_group)
        
        # Apply button
        apply_btn = QPushButton("✅ Áp dụng cho AI đã chọn")
        apply_btn.clicked.connect(self.apply_personality_to_selected)
        layout.addWidget(apply_btn)
        
        # Test AI button
        test_btn = QPushButton("🧪 Test AI Response")
        test_btn.clicked.connect(self.test_ai_response)
        layout.addWidget(test_btn)
        
        layout.addStretch()
        return widget
    
    def create_groups_tab(self):
        """Tạo tab quản lý nhóm"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Groups table
        groups_group = QGroupBox("👥 Nhóm chat")
        groups_layout = QVBoxLayout(groups_group)
        
        # Controls
        groups_controls = QHBoxLayout()
        btn_add_group = QPushButton("➕ Thêm nhóm")
        btn_add_group.clicked.connect(self.add_chat_group)
        btn_remove_group = QPushButton("➖ Xóa nhóm")
        btn_remove_group.clicked.connect(self.remove_chat_group)
        btn_scan_groups = QPushButton("🔍 Quét nhóm")
        btn_scan_groups.clicked.connect(self.scan_telegram_groups)
        
        groups_controls.addWidget(btn_add_group)
        groups_controls.addWidget(btn_remove_group)
        groups_controls.addWidget(btn_scan_groups)
        groups_controls.addStretch()
        
        groups_layout.addLayout(groups_controls)
        
        # Groups table
        self.groups_table = QTableWidget()
        self.setup_groups_table()
        groups_layout.addWidget(self.groups_table)
        
        layout.addWidget(groups_group)
        
        # AI assignment
        assignment_group = QGroupBox("🎯 Phân công AI")
        assignment_layout = QVBoxLayout(assignment_group)
        
        assign_controls = QHBoxLayout()
        btn_assign_random = QPushButton("🎲 Phân công ngẫu nhiên")
        btn_assign_random.clicked.connect(self.random_assign_ais)
        btn_assign_smart = QPushButton("🧠 Phân công thông minh")
        btn_assign_smart.clicked.connect(self.smart_assign_ais)
        
        assign_controls.addWidget(btn_assign_random)
        assign_controls.addWidget(btn_assign_smart)
        assign_controls.addStretch()
        
        assignment_layout.addLayout(assign_controls)
        layout.addWidget(assignment_group)
        
        layout.addStretch()
        return widget
    
    def setup_groups_table(self):
        """Thiết lập bảng nhóm chat"""
        self.groups_table.setColumnCount(6)
        self.groups_table.setHorizontalHeaderLabels([
            "Tên nhóm", "Group ID", "Link", "Thành viên", "Số AI", "Trạng thái"
        ])
        
        header = self.groups_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.groups_table.setColumnWidth(0, 120)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        self.groups_table.setColumnWidth(1, 120)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        self.groups_table.setColumnWidth(3, 80)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        self.groups_table.setColumnWidth(4, 60)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        self.groups_table.setColumnWidth(5, 80)
        
        self.groups_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.groups_table.setAlternatingRowColors(True)
        self.groups_table.verticalHeader().setVisible(False)
    
    def create_monitoring_tab(self):
        """Tạo tab giám sát & phân tích"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Real-time status
        status_group = QGroupBox("📊 Trạng thái thời gian thực")
        status_layout = QGridLayout(status_group)
        
        # Status indicators
        self.active_ais_label = QLabel("🟢 AI hoạt động: 0")
        self.idle_ais_label = QLabel("🟡 AI nghỉ: 0")
        self.error_ais_label = QLabel("🔴 AI lỗi: 0")
        self.total_messages_label = QLabel("💬 Tin nhắn đã gửi: 0")
        
        status_layout.addWidget(self.active_ais_label, 0, 0)
        status_layout.addWidget(self.idle_ais_label, 0, 1)
        status_layout.addWidget(self.error_ais_label, 1, 0)
        status_layout.addWidget(self.total_messages_label, 1, 1)
        
        layout.addWidget(status_group)
        
        # Activity log
        log_group = QGroupBox("📝 Nhật ký hoạt động")
        log_layout = QVBoxLayout(log_group)
        
        log_controls = QHBoxLayout()
        btn_clear_log = QPushButton("🗑️ Xóa nhật ký")
        btn_clear_log.clicked.connect(self.clear_activity_log)
        btn_export_log = QPushButton("📤 Xuất nhật ký")
        btn_export_log.clicked.connect(self.export_activity_log)
        
        log_controls.addWidget(btn_clear_log)
        log_controls.addWidget(btn_export_log)
        log_controls.addStretch()
        
        log_layout.addLayout(log_controls)
        
        self.activity_log = QTextEdit()
        self.activity_log.setMaximumHeight(200)
        self.activity_log.setReadOnly(True)
        log_layout.addWidget(self.activity_log)
        
        layout.addWidget(log_group)
        
        # Emergency controls
        emergency_group = QGroupBox("🚨 Điều khiển khẩn cấp")
        emergency_layout = QHBoxLayout(emergency_group)
        
        btn_emergency_stop = QPushButton("🛑 DỪNG KHẨN CẤP TẤT CẢ")
        btn_emergency_stop.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; padding: 10px;")
        btn_emergency_stop.clicked.connect(self.emergency_stop_all)
        
        btn_pause_all = QPushButton("⏸️ Tạm dừng tất cả")
        btn_pause_all.clicked.connect(self.pause_all_ais)
        
        btn_resume_all = QPushButton("▶️ Tiếp tục tất cả")
        btn_resume_all.clicked.connect(self.resume_all_ais)
        
        emergency_layout.addWidget(btn_emergency_stop)
        emergency_layout.addWidget(btn_pause_all)
        emergency_layout.addWidget(btn_resume_all)
        emergency_layout.addStretch()
        
        layout.addWidget(emergency_group)
        
        layout.addStretch()
        return widget
    
    def create_advanced_tab(self):
        """Tạo tab cài đặt nâng cao"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Special modes
        modes_group = QGroupBox("🚀 Chế độ đặc biệt")
        modes_layout = QVBoxLayout(modes_group)
        
        # Swarm mode
        swarm_layout = QHBoxLayout()
        self.swarm_mode_check = QCheckBox("🐝 Chế độ bầy đàn")
        self.swarm_mode_check.toggled.connect(self.toggle_swarm_mode)
        swarm_layout.addWidget(self.swarm_mode_check)
        swarm_layout.addWidget(QLabel("(Điều phối nhiều AI đồng bộ)"))
        swarm_layout.addStretch()
        modes_layout.addLayout(swarm_layout)
        
        # Ninja mode
        ninja_layout = QHBoxLayout()
        self.ninja_mode_check = QCheckBox("🥷 Chế độ ninja")
        self.ninja_mode_check.toggled.connect(self.toggle_ninja_mode)
        ninja_layout.addWidget(self.ninja_mode_check)
        ninja_layout.addWidget(QLabel("(Chỉ hoạt động khi có trigger)"))
        ninja_layout.addStretch()
        modes_layout.addLayout(ninja_layout)
        
        # Stealth mode
        stealth_layout = QHBoxLayout()
        self.stealth_mode_check = QCheckBox("👻 Chế độ tàng hình")
        self.stealth_mode_check.toggled.connect(self.toggle_stealth_mode)
        stealth_layout.addWidget(self.stealth_mode_check)
        stealth_layout.addWidget(QLabel("(Giảm tần suất khi phát hiện admin)"))
        stealth_layout.addStretch()
        modes_layout.addLayout(stealth_layout)
        
        layout.addWidget(modes_group)
        
        # Anti-detection settings
        antidet_group = QGroupBox("🛡️ Chống phát hiện")
        antidet_layout = QFormLayout(antidet_group)
        
        # Rate limiting
        self.global_rate_limit = QSpinBox()
        self.global_rate_limit.setRange(1, 60)
        self.global_rate_limit.setValue(5)
        self.global_rate_limit.setSuffix(" tin/phút")
        antidet_layout.addRow("Giới hạn tốc độ toàn cục:", self.global_rate_limit)
        
        # Random delays
        self.random_delay_check = QCheckBox("Ngẫu nhiên hóa thời gian phản hồi")
        self.random_delay_check.setChecked(True)
        antidet_layout.addRow("Độ trễ ngẫu nhiên:", self.random_delay_check)
        
        # Human-like typing
        self.typing_simulation_check = QCheckBox("Mô phỏng cách gõ như người thật")
        self.typing_simulation_check.setChecked(True)
        antidet_layout.addRow("Mô phỏng gõ phím:", self.typing_simulation_check)
        
        layout.addWidget(antidet_group)
        
        # Data management
        data_group = QGroupBox("💾 Quản lý dữ liệu")
        data_layout = QHBoxLayout(data_group)
        
        btn_backup = QPushButton("📋 Sao lưu dữ liệu")
        btn_backup.clicked.connect(self.backup_ai_data)
        
        btn_restore = QPushButton("📥 Khôi phục dữ liệu")
        btn_restore.clicked.connect(self.restore_ai_data)
        
        btn_reset = QPushButton("🔄 Đặt lại tất cả")
        btn_reset.clicked.connect(self.reset_all_data)
        
        data_layout.addWidget(btn_backup)
        data_layout.addWidget(btn_restore)
        data_layout.addWidget(btn_reset)
        data_layout.addStretch()
        
        layout.addWidget(data_group)
        
        layout.addStretch()
        return widget
    
    def apply_light_theme(self):
        """Áp dụng light theme với accent xanh dương"""
        self.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                color: #000000;
                font-family: 'Segoe UI Variable', 'Segoe UI', 'Roboto', 'Arial';
                font-size: 11pt;
            }
            
            QTabWidget::pane {
                border: 1px solid #cccccc;
                background-color: #f5f5f5;
            }
            
            QTabBar::tab {
                background-color: #e0e0e0;
                color: #000000;
                padding: 8px 16px;
                margin-right: 2px;
                border: 1px solid #cccccc;
                border-bottom: none;
            }
            
            QTabBar::tab:selected {
                background-color: #1976d2;
                color: #ffffff;
                font-weight: bold;
            }
            
            QTabBar::tab:hover {
                background-color: #f0f0f0;
            }
            
            QPushButton {
                background-color: #f5f5f5;
                color: #000000;
                border: 1px solid #cccccc;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11pt;
                font-family: 'Segoe UI Semibold', 'Segoe UI', 'Roboto', 'Arial';
            }
            
            QPushButton:hover {
                background-color: #e0e0e0;
                border-color: #1976d2;
            }
            
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
            
            QPushButton:checked {
                background-color: #1976d2;
                color: #ffffff;
                border-color: #1976d2;
            }
            
            QLineEdit, QTextEdit, QSpinBox, QComboBox {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #cccccc;
                padding: 6px;
                border-radius: 4px;
                font-size: 11pt;
                font-family: 'Segoe UI Regular', 'Segoe UI', 'Roboto', 'Arial';
            }
            
            QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QComboBox:focus {
                border-color: #1976d2;
            }
            
            QTableWidget {
                background-color: #ffffff;
                alternate-background-color: #f9f9f9;
                gridline-color: #e0e0e0;
                selection-background-color: #e3f2fd;
                selection-color: #000000;
                font-size: 10.5pt;
                font-family: 'Segoe UI Regular', 'Segoe UI', 'Roboto', 'Arial';
            }
            
            QTableWidget::item {
                padding: 8px;
                border: none;
            }
            
            QHeaderView::section {
                background-color: #f5f5f5;
                color: #000000;
                padding: 8px;
                border: 1px solid #cccccc;
                font-weight: bold;
                font-size: 11pt;
                font-family: 'Segoe UI Semibold', 'Segoe UI', 'Roboto', 'Arial';
            }
            
            QCheckBox {
                color: #000000;
                spacing: 8px;
            }
            
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #cccccc;
                border-radius: 3px;
                background-color: #ffffff;
            }
            
            QCheckBox::indicator:checked {
                background-color: #1976d2;
                border-color: #1976d2;
            }
            
            QLabel {
                color: #000000;
                font-size: 11pt;
                font-family: 'Segoe UI Regular', 'Segoe UI', 'Roboto', 'Arial';
            }
            
            QGroupBox {
                color: #000000;
                border: 1px solid #cccccc;
                border-radius: 4px;
                margin-top: 8px;
                font-weight: bold;
                font-size: 11pt;
                font-family: 'Segoe UI Semibold', 'Segoe UI', 'Roboto', 'Arial';
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
                color: #1976d2;
            }
            
            QSplitter::handle {
                background-color: #cccccc;
                width: 2px;
                height: 2px;
            }
            
            QScrollBar:vertical {
                background-color: #f5f5f5;
                width: 12px;
                border-radius: 6px;
            }
            
            QScrollBar::handle:vertical {
                background-color: #cccccc;
                border-radius: 6px;
                min-height: 20px;
            }
            
            QScrollBar::handle:vertical:hover {
                background-color: #999999;
            }
            
            QSlider::groove:horizontal {
                border: 1px solid #cccccc;
                height: 6px;
                background: #f0f0f0;
                border-radius: 3px;
            }
            
            QSlider::handle:horizontal {
                background: #1976d2;
                border: 1px solid #1976d2;
                width: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            
            QSlider::handle:horizontal:hover {
                background: #1565c0;
            }
        """)
    
    def setup_timers(self):
        """Thiết lập các timer cho monitoring"""
        # Timer cập nhật stats
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_stats)
        self.stats_timer.start(2000)  # 2 giây
        
        # Timer monitoring AI status
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self.monitor_ai_status)
        self.monitor_timer.start(5000)  # 5 giây
    
    def load_data(self):
        """Load dữ liệu từ files"""
        # Load AI accounts
        if os.path.exists(self.ai_accounts_file):
            try:
                with open(self.ai_accounts_file, 'r', encoding='utf-8') as f:
                    self.ai_accounts = json.load(f)
            except Exception as e:
                print(f"[ERROR] Không thể load AI accounts: {e}")
                self.ai_accounts = []
        
        # Load personalities
        if os.path.exists(self.personalities_file):
            try:
                with open(self.personalities_file, 'r', encoding='utf-8') as f:
                    self.personalities = json.load(f)
            except Exception as e:
                print(f"[ERROR] Không thể load personalities: {e}")
                self.personalities = self.get_default_personalities()
        else:
            self.personalities = self.get_default_personalities()
        
        # Load chat groups
        if os.path.exists(self.chat_groups_file):
            try:
                with open(self.chat_groups_file, 'r', encoding='utf-8') as f:
                    self.chat_groups = json.load(f)
            except Exception as e:
                print(f"[ERROR] Không thể load chat groups: {e}")
                self.chat_groups = []
    
    def save_data(self):
        """Lưu dữ liệu vào files"""
        try:
            # Save AI accounts
            with open(self.ai_accounts_file, 'w', encoding='utf-8') as f:
                json.dump(self.ai_accounts, f, indent=2, ensure_ascii=False)
            
            # Save personalities
            with open(self.personalities_file, 'w', encoding='utf-8') as f:
                json.dump(self.personalities, f, indent=2, ensure_ascii=False)
            
            # Save chat groups
            with open(self.chat_groups_file, 'w', encoding='utf-8') as f:
                json.dump(self.chat_groups, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"[ERROR] Không thể lưu dữ liệu: {e}")
    
    def get_default_personalities(self):
        """Tạo personalities mặc định"""
        return [
            {
                "id": "funny",
                "name": "😄 Hài hước",
                "response_freq": 7,
                "response_speed": 4,
                "enthusiasm": 8,
                "emotion": "positive",
                "keywords": ["haha", "lol", "vui quá", "hay ghê", "😂", "🤣"]
            },
            {
                "id": "serious",
                "name": "😐 Nghiêm túc",
                "response_freq": 4,
                "response_speed": 8,
                "enthusiasm": 3,
                "emotion": "neutral",
                "keywords": ["theo tôi", "cần phải", "nghiêm túc", "quan trọng"]
            },
            {
                "id": "friendly",
                "name": "😊 Thân thiện",
                "response_freq": 6,
                "response_speed": 5,
                "enthusiasm": 7,
                "emotion": "positive",
                "keywords": ["bạn ơi", "cảm ơn", "rất vui", "😊", "❤️"]
            }
        ] 

    # ===============================================
    # 🎯 SLOT METHODS - Event Handlers
    # ===============================================
    
    def add_ai_account(self):
        """Thêm tài khoản AI mới"""
        # Lấy danh sách tài khoản từ tab Quản lý Tài khoản
        telegram_accounts = self.get_telegram_accounts()
        
        if not telegram_accounts:
            QMessageBox.warning(self, "Lỗi", "Không có tài khoản Telegram nào!\nVui lòng thêm tài khoản ở tab 'Quản lý Tài khoản' trước.")
            return
        
        dialog = AddAIDialog(self, telegram_accounts=telegram_accounts)
        if dialog.exec() == QDialog.Accepted:
            ai_data = dialog.get_ai_data()
            ai_data['id'] = str(uuid.uuid4())
            ai_data['created_at'] = datetime.now().isoformat()
            ai_data['status'] = 'idle'
            ai_data['messages_sent'] = 0
            ai_data['last_active'] = None
            
            self.ai_accounts.append(ai_data)
            self.save_data()
            self.update_ai_table()
            self.log_activity(f"➕ Added new AI: {ai_data['name']}")
    
    def edit_ai_account(self, item):
        """Chỉnh sửa tài khoản AI"""
        row = item.row()
        if row < len(self.ai_accounts):
            ai_data = self.ai_accounts[row]
            telegram_accounts = self.get_telegram_accounts()
            dialog = AddAIDialog(self, ai_data, telegram_accounts)
            if dialog.exec() == QDialog.Accepted:
                updated_data = dialog.get_ai_data()
                self.ai_accounts[row].update(updated_data)
                self.save_data()
                self.update_ai_table()
                self.log_activity(f"✏️ Edited AI: {updated_data['name']}")
    
    def import_ai_accounts(self):
        """Import tài khoản AI từ file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import AI Accounts", "", "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    imported_data = json.load(f)
                
                if isinstance(imported_data, list):
                    for ai_data in imported_data:
                        ai_data['id'] = str(uuid.uuid4())
                        ai_data['created_at'] = datetime.now().isoformat()
                        self.ai_accounts.append(ai_data)
                    
                    self.save_data()
                    self.update_ai_table()
                    self.log_activity(f"📥 Imported {len(imported_data)} AI accounts")
                    QMessageBox.information(self, "Thành công", f"Đã import {len(imported_data)} tài khoản AI!")
                else:
                    QMessageBox.warning(self, "Lỗi", "File không đúng định dạng!")
                    
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể import file: {str(e)}")
    
    def export_ai_accounts(self):
        """Export tài khoản AI ra file"""
        if not self.ai_accounts:
            QMessageBox.warning(self, "Lỗi", "Không có tài khoản AI nào để export!")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export AI Accounts", "ai_accounts_backup.json", "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.ai_accounts, f, indent=2, ensure_ascii=False)
                
                self.log_activity(f"📤 Exported {len(self.ai_accounts)} AI accounts")
                QMessageBox.information(self, "Thành công", f"Đã export {len(self.ai_accounts)} tài khoản AI!")
                
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể export file: {str(e)}")
    
    def start_all_ais(self):
        """Khởi động tất cả AI"""
        count = 0
        for ai in self.ai_accounts:
            if ai['status'] != 'active':
                ai['status'] = 'active'
                ai['last_active'] = datetime.now().isoformat()
                count += 1
        
        if count > 0:
            self.save_data()
            self.update_ai_table()
            self.log_activity(f"▶️ Started {count} AIs")
            QMessageBox.information(self, "Thành công", f"Đã khởi động {count} AI!")
    
    def stop_all_ais(self):
        """Dừng tất cả AI"""
        count = 0
        for ai in self.ai_accounts:
            if ai['status'] == 'active':
                ai['status'] = 'idle'
                count += 1
        
        if count > 0:
            self.save_data()
            self.update_ai_table()
            self.log_activity(f"⏹️ Stopped {count} AIs")
            QMessageBox.information(self, "Thành công", f"Đã dừng {count} AI!")
    
    def select_personality_preset(self, preset_name):
        """Chọn personality preset"""
        # Uncheck other buttons
        for btn in self.preset_buttons:
            if btn.text() != preset_name:
                btn.setChecked(False)
        
        # Find and apply preset
        for personality in self.personalities:
            if personality['name'] == preset_name:
                self.response_freq_slider.setValue(personality['response_freq'])
                self.response_speed_spin.setValue(personality['response_speed'])
                self.enthusiasm_slider.setValue(personality['enthusiasm'])
                
                # Set emotion combo
                emotion_map = {
                    'positive': '😊 Tích cực',
                    'neutral': '😐 Trung lập',
                    'negative': '😔 Tiêu cực',
                    'random': '🤪 Ngẫu nhiên'
                }
                emotion_text = emotion_map.get(personality['emotion'], '😐 Trung lập')
                index = self.emotion_combo.findText(emotion_text)
                if index >= 0:
                    self.emotion_combo.setCurrentIndex(index)
                
                # Set keywords
                keywords = ', '.join(personality['keywords'])
                self.keywords_edit.setPlainText(keywords)
                break
    
    def update_personality_config(self):
        """Cập nhật cấu hình personality"""
        # Uncheck all preset buttons when manually adjusting
        for btn in self.preset_buttons:
            btn.setChecked(False)
    
    def apply_personality_to_selected(self):
        """Áp dụng personality cho AI đã chọn"""
        selected_rows = []
        for row in range(self.ai_table.rowCount()):
            checkbox_item = self.ai_table.item(row, 0)
            if checkbox_item and checkbox_item.checkState() == Qt.Checked:
                selected_rows.append(row)
        
        if not selected_rows:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn ít nhất một AI!")
            return
        
        # Create personality config
        personality_config = {
            'response_freq': self.response_freq_slider.value(),
            'response_speed': self.response_speed_spin.value(),
            'enthusiasm': self.enthusiasm_slider.value(),
            'emotion': self.emotion_combo.currentText(),
            'keywords': [k.strip() for k in self.keywords_edit.toPlainText().split(',') if k.strip()]
        }
        
        # Apply to selected AIs
        for row in selected_rows:
            if row < len(self.ai_accounts):
                self.ai_accounts[row]['personality'] = personality_config
        
        self.save_data()
        self.update_ai_table()
        self.log_activity(f"🎭 Applied personality to {len(selected_rows)} AIs")
        QMessageBox.information(self, "Thành công", f"Đã áp dụng personality cho {len(selected_rows)} AI!")
    
    def add_chat_group(self):
        """Thêm nhóm chat"""
        dialog = AddGroupDialog(self)
        if dialog.exec() == QDialog.Accepted:
            group_data = dialog.get_group_data()
            group_data['members'] = 0
            group_data['ai_count'] = 0
            group_data['activity'] = 'low'
            group_data['status'] = 'active'
            group_data['created_at'] = datetime.now().isoformat()
            
            self.chat_groups.append(group_data)
            self.save_data()
            self.update_groups_table()
            self.log_activity(f"👥 Added group: {group_data['name']}")
    
    def remove_chat_group(self):
        """Xóa nhóm chat"""
        current_row = self.groups_table.currentRow()
        if current_row >= 0 and current_row < len(self.chat_groups):
            group_name = self.chat_groups[current_row]['name']
            reply = QMessageBox.question(
                self, "Xác nhận", f"Bạn có chắc muốn xóa group '{group_name}'?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.chat_groups.pop(current_row)
                self.save_data()
                self.update_groups_table()
                self.log_activity(f"🗑️ Removed group: {group_name}")
    
    def scan_telegram_groups(self):
        """Quét nhóm Telegram"""
        QMessageBox.information(self, "Scan Groups", "Tính năng quét nhóm Telegram đang được phát triển")
        self.log_activity("🔍 Scanned Telegram groups")
    
    def random_assign_ais(self):
        """Gán AI ngẫu nhiên vào nhóm"""
        if not self.ai_accounts or not self.chat_groups:
            QMessageBox.warning(self, "Lỗi", "Cần có ít nhất 1 AI và 1 nhóm!")
            return
        
        count = 0
        for ai in self.ai_accounts:
            if random.choice([True, False]):  # 50% chance
                group = random.choice(self.chat_groups)
                ai['assigned_groups'] = ai.get('assigned_groups', [])
                if group['id'] not in ai['assigned_groups']:
                    ai['assigned_groups'].append(group['id'])
                    count += 1
        
        self.save_data()
        self.update_ai_table()
        self.log_activity(f"🎲 Random assigned {count} AIs to groups")
        QMessageBox.information(self, "Thành công", f"Đã gán ngẫu nhiên {count} AI vào nhóm!")
    
    def smart_assign_ais(self):
        """Gán AI thông minh vào nhóm"""
        QMessageBox.information(self, "Smart Assign", "Tính năng gán thông minh đang được phát triển")
        self.log_activity("🧠 Smart assigned AIs to groups")
    
    def emergency_stop_all(self):
        """Dừng khẩn cấp tất cả AI"""
        reply = QMessageBox.question(
            self, "⚠️ EMERGENCY STOP", 
            "Bạn có chắc muốn dừng khẩn cấp TẤT CẢ AI?\nHành động này không thể hoàn tác!",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            for ai in self.ai_accounts:
                ai['status'] = 'stopped'
                ai['emergency_stopped'] = True
            
            self.save_data()
            self.update_ai_table()
            self.log_activity("🛑 EMERGENCY STOP ALL executed")
            QMessageBox.warning(self, "Emergency Stop", "Đã dừng khẩn cấp tất cả AI!")
    
    def pause_all_ais(self):
        """Tạm dừng tất cả AI"""
        count = 0
        for ai in self.ai_accounts:
            if ai['status'] == 'active':
                ai['status'] = 'paused'
                count += 1
        
        self.save_data()
        self.update_ai_table()
        self.log_activity(f"⏸️ Paused {count} AIs")
    
    def resume_all_ais(self):
        """Tiếp tục tất cả AI"""
        count = 0
        for ai in self.ai_accounts:
            if ai['status'] == 'paused':
                ai['status'] = 'active'
                ai['last_active'] = datetime.now().isoformat()
                count += 1
        
        self.save_data()
        self.update_ai_table()
        self.log_activity(f"▶️ Resumed {count} AIs")
    
    def toggle_swarm_mode(self, checked):
        """Bật/tắt chế độ Swarm"""
        if checked:
            self.log_activity("🐝 Swarm Mode: ENABLED")
        else:
            self.log_activity("🐝 Swarm Mode: DISABLED")
    
    def toggle_ninja_mode(self, checked):
        """Bật/tắt chế độ Ninja"""
        if checked:
            self.log_activity("🥷 Ninja Mode: ENABLED")
        else:
            self.log_activity("🥷 Ninja Mode: DISABLED")
    
    def toggle_stealth_mode(self, checked):
        """Bật/tắt chế độ Stealth"""
        if checked:
            self.log_activity("👻 Stealth Mode: ENABLED")
        else:
            self.log_activity("👻 Stealth Mode: DISABLED")
    
    def backup_ai_data(self):
        """Backup dữ liệu AI"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"ai_backup_{timestamp}.json"
        
        backup_data = {
            'ai_accounts': self.ai_accounts,
            'personalities': self.personalities,
            'chat_groups': self.chat_groups,
            'backup_time': datetime.now().isoformat()
        }
        
        try:
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            self.log_activity(f"📋 Backup created: {backup_file}")
            QMessageBox.information(self, "Backup", f"Đã tạo backup: {backup_file}")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể tạo backup: {str(e)}")
    
    def restore_ai_data(self):
        """Restore dữ liệu AI từ backup"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Restore Backup", "", "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)
                
                self.ai_accounts = backup_data.get('ai_accounts', [])
                self.personalities = backup_data.get('personalities', self.get_default_personalities())
                self.chat_groups = backup_data.get('chat_groups', [])
                
                self.save_data()
                self.update_ai_table()
                self.update_groups_table()
                
                self.log_activity(f"📥 Restored from backup: {file_path}")
                QMessageBox.information(self, "Restore", "Đã restore dữ liệu thành công!")
                
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể restore backup: {str(e)}")
    
    def reset_all_data(self):
        """Reset tất cả dữ liệu"""
        reply = QMessageBox.question(
            self, "⚠️ Reset All Data", 
            "Bạn có chắc muốn XÓA TẤT CẢ dữ liệu AI?\nHành động này không thể hoàn tác!",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.ai_accounts.clear()
            self.chat_groups.clear()
            self.personalities = self.get_default_personalities()
            
            self.save_data()
            self.update_ai_table()
            self.update_groups_table()
            
            self.log_activity("🔄 All data reset")
            QMessageBox.warning(self, "Reset", "Đã reset tất cả dữ liệu!")
    
    def clear_activity_log(self):
        """Xóa activity log"""
        self.activity_log.clear()
        self.log_activity("🗑️ Activity log cleared")
    
    def export_activity_log(self):
        """Export activity log"""
        log_text = self.activity_log.toPlainText()
        if not log_text:
            QMessageBox.warning(self, "Lỗi", "Activity log trống!")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Activity Log", f"activity_log_{timestamp}.txt", "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(log_text)
                
                QMessageBox.information(self, "Export", f"Đã export activity log: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể export log: {str(e)}")
    
    # ===============================================
    # 🔄 UPDATE METHODS - UI Updates
    # ===============================================
    
    def update_ai_table(self):
        """Cập nhật bảng AI"""
        self.ai_table.setRowCount(len(self.ai_accounts))
        
        for row, ai in enumerate(self.ai_accounts):
            # Checkbox
            checkbox_item = QTableWidgetItem()
            checkbox_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            checkbox_item.setCheckState(Qt.Unchecked)
            self.ai_table.setItem(row, 0, checkbox_item)
            
            # Avatar (placeholder)
            avatar_item = QTableWidgetItem("🤖")
            avatar_item.setTextAlignment(Qt.AlignCenter)
            self.ai_table.setItem(row, 1, avatar_item)
            
            # Name
            name_item = QTableWidgetItem(ai.get('name', 'Unknown'))
            self.ai_table.setItem(row, 2, name_item)
            
            # Status
            status = ai.get('status', 'idle')
            status_icons = {
                'active': '🟢 Active',
                'idle': '🟡 Idle',
                'paused': '⏸️ Paused',
                'error': '🔴 Error',
                'stopped': '⏹️ Stopped'
            }
            status_item = QTableWidgetItem(status_icons.get(status, '❓ Unknown'))
            status_item.setTextAlignment(Qt.AlignCenter)
            self.ai_table.setItem(row, 3, status_item)
            
            # Groups
            groups = ai.get('assigned_groups', [])
            groups_text = f"{len(groups)} groups" if groups else "No groups"
            groups_item = QTableWidgetItem(groups_text)
            groups_item.setTextAlignment(Qt.AlignCenter)
            self.ai_table.setItem(row, 4, groups_item)
            
            # Personality
            personality = ai.get('personality', {})
            if personality:
                personality_text = f"Custom ({personality.get('response_freq', 5)}/10)"
            else:
                personality_text = "Default"
            personality_item = QTableWidgetItem(personality_text)
            personality_item.setTextAlignment(Qt.AlignCenter)
            self.ai_table.setItem(row, 5, personality_item)
    
    def update_groups_table(self):
        """Cập nhật bảng nhóm"""
        self.groups_table.setRowCount(len(self.chat_groups))
        
        for row, group in enumerate(self.chat_groups):
            # Group name
            name_item = QTableWidgetItem(group.get('name', 'Unknown'))
            self.groups_table.setItem(row, 0, name_item)
            
            # Group ID
            group_id = group.get('id', '')
            group_id_item = QTableWidgetItem(group_id)
            group_id_item.setTextAlignment(Qt.AlignCenter)
            self.groups_table.setItem(row, 1, group_id_item)
            
            # Link
            link = group.get('link', '')
            link_item = QTableWidgetItem(link)
            link_item.setToolTip(link)  # Hiển thị full link khi hover
            self.groups_table.setItem(row, 2, link_item)
            
            # Members
            members_item = QTableWidgetItem(str(group.get('members', 0)))
            members_item.setTextAlignment(Qt.AlignCenter)
            self.groups_table.setItem(row, 3, members_item)
            
            # AI count
            ai_count_item = QTableWidgetItem(str(group.get('ai_count', 0)))
            ai_count_item.setTextAlignment(Qt.AlignCenter)
            self.groups_table.setItem(row, 4, ai_count_item)
            
            # Status
            status = group.get('status', 'active')
            status_icons = {
                'active': '✅ Active',
                'inactive': '❌ Inactive',
                'monitoring': '👀 Monitoring'
            }
            status_item = QTableWidgetItem(status_icons.get(status, '❓ Unknown'))
            status_item.setTextAlignment(Qt.AlignCenter)
            self.groups_table.setItem(row, 5, status_item)
    
    def update_stats(self):
        """Cập nhật thống kê"""
        total = len(self.ai_accounts)
        active = sum(1 for ai in self.ai_accounts if ai.get('status') == 'active')
        idle = sum(1 for ai in self.ai_accounts if ai.get('status') == 'idle')
        error = sum(1 for ai in self.ai_accounts if ai.get('status') == 'error')
        
        # Update main stats
        self.stats_label.setText(f"📊 Total: {total} AI | Hoạt động: {active} | Nghỉ: {idle}")
        
        # Update monitoring labels
        if hasattr(self, 'active_ais_label'):
            self.active_ais_label.setText(f"🟢 AI hoạt động: {active}")
            self.idle_ais_label.setText(f"🟡 AI nghỉ: {idle}")
            self.error_ais_label.setText(f"🔴 AI lỗi: {error}")
            
            total_messages = sum(ai.get('messages_sent', 0) for ai in self.ai_accounts)
            self.total_messages_label.setText(f"💬 Tin nhắn đã gửi: {total_messages}")
    
    def monitor_ai_status(self):
        """Monitor AI status (chạy định kỳ)"""
        # Simulate status changes for demo
        for ai in self.ai_accounts:
            if ai.get('status') == 'active':
                # Random chance of sending message
                if random.random() < 0.1:  # 10% chance
                    ai['messages_sent'] = ai.get('messages_sent', 0) + 1
                    ai['last_active'] = datetime.now().isoformat()
    
    def log_activity(self, message):
        """Ghi log hoạt động"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        self.activity_log.append(log_message)
        
        # Keep only last 100 lines
        text = self.activity_log.toPlainText()
        lines = text.split('\n')
        if len(lines) > 100:
            self.activity_log.setPlainText('\n'.join(lines[-100:]))
    
    def get_telegram_accounts(self):
        """Lấy danh sách tài khoản Telegram từ tab Quản lý Tài khoản"""
        try:
            # Tìm MainWindow để truy cập account_tab
            main_window = self.parent()
            while main_window and not hasattr(main_window, 'account_tab'):
                main_window = main_window.parent()
            
            if main_window and hasattr(main_window, 'account_tab'):
                accounts = main_window.account_tab.accounts
                # Lọc chỉ những tài khoản đã đăng nhập thành công
                telegram_accounts = []
                for acc in accounts:
                    if 'đăng nhập' in acc.get('status', '').lower():
                        telegram_accounts.append({
                            'username': acc.get('username', ''),
                            'phone': acc.get('username', ''),  # Username là số điện thoại
                            'status': acc.get('status', ''),
                            'proxy': acc.get('proxy', '')
                        })
                return telegram_accounts
            else:
                # Fallback: đọc từ file accounts.json
                if os.path.exists('accounts.json'):
                    with open('accounts.json', 'r', encoding='utf-8') as f:
                        accounts = json.load(f)
                        telegram_accounts = []
                        for acc in accounts:
                            if 'đăng nhập' in acc.get('status', '').lower():
                                telegram_accounts.append({
                                    'username': acc.get('username', ''),
                                    'phone': acc.get('username', ''),
                                    'status': acc.get('status', ''),
                                    'proxy': acc.get('proxy', '')
                                })
                        return telegram_accounts
                return []
        except Exception as e:
            print(f"[ERROR] Không thể lấy danh sách tài khoản Telegram: {e}")
            return []
    
    def test_ai_response(self):
        """Test AI response với personality hiện tại"""
        if not self.ai_initialized:
            QMessageBox.warning(self, "Lỗi", "AI components chưa được khởi tạo!")
            return
        
        # Get test message from user
        test_message, ok = QInputDialog.getText(
            self, "Test AI Response", 
            "Nhập tin nhắn test:", 
            text="Xin chào! Bạn có khỏe không?"
        )
        
        if not ok or not test_message.strip():
            return
        
        # Get current personality settings
        personality_name = "Thân thiện"
        for btn in self.preset_buttons:
            if btn.isChecked():
                personality_name = btn.text().split(" ", 1)[1]  # Remove emoji
                break
        
        # Use QThread instead of threading
        self.ai_test_worker = AITestWorker(self.ai_client, test_message, personality_name)
        self.ai_test_worker.result_ready.connect(self.show_ai_test_result_signal)
        self.ai_test_worker.error_occurred.connect(self.show_ai_test_error_signal)
        
        # Create progress dialog
        self.progress_dialog = QProgressDialog("Đang test AI response...", "Hủy", 0, 0, self)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.canceled.connect(self.cancel_ai_test)
        self.progress_dialog.show()
        
        # Start worker
        self.ai_test_worker.start()
    
    def show_ai_test_result_signal(self, input_msg, result, personality):
        """Signal handler for AI test result"""
        self.progress_dialog.close()
        self.show_ai_test_result(input_msg, result, personality)
    
    def show_ai_test_error_signal(self, error):
        """Signal handler for AI test error"""
        self.progress_dialog.close()
        self.show_ai_test_error(error)
    
    def cancel_ai_test(self):
        """Cancel AI test"""
        if hasattr(self, 'ai_test_worker'):
            self.ai_test_worker.stop()
            self.ai_test_worker.wait()
        self.log_activity("🧪 AI test cancelled by user")
    
    def show_ai_test_result(self, input_msg, result, personality):
        """Hiển thị kết quả test AI"""
        if result["success"]:
            msg = f"""🧪 TEST AI RESPONSE
            
📝 Input: {input_msg}
🎭 Personality: {personality}

✅ AI Response:
{result['response']}

📊 Stats:
• Model: {result.get('model_used', 'N/A')}
• Tokens: {result.get('tokens_used', 0)}
• Delay: {result.get('delay', 0):.1f}s"""
            
            QMessageBox.information(self, "AI Test Result", msg)
            self.log_activity(f"🧪 AI test successful - {personality}")
        else:
            QMessageBox.critical(self, "AI Test Failed", f"❌ Error: {result['error']}")
            self.log_activity(f"🧪 AI test failed - {result['error']}")
    
    def show_ai_test_error(self, error):
        """Hiển thị lỗi test AI"""
        QMessageBox.critical(self, "AI Test Error", f"❌ Test failed: {error}")
        self.log_activity(f"🧪 AI test error - {error}")
    
    async def start_ai_bot(self, ai_data):
        """Khởi động AI bot thực tế"""
        if not self.bot_manager:
            return False
        
        try:
            phone = ai_data.get('telegram_account', {}).get('phone', '')
            session_path = f"sessions/{phone}.session"
            proxy = ai_data.get('telegram_account', {}).get('proxy', '')
            
            success = await self.bot_manager.add_bot(phone, session_path, proxy)
            
            if success:
                # Update personality settings
                personality = ai_data.get('personality', {})
                self.bot_manager.update_bot_personality(
                    phone,
                    personality=personality.get('name', 'Thân thiện'),
                    frequency=personality.get('response_freq', 5),
                    speed=(3, personality.get('response_speed', 10)),
                    enthusiasm=personality.get('enthusiasm', 5),
                    emotion=personality.get('emotion', 'Positive'),
                    keywords=personality.get('keywords', [])
                )
                
                self.log_activity(f"🤖 Started AI bot: {phone}")
                return True
            else:
                self.log_activity(f"❌ Failed to start AI bot: {phone}")
                return False
                
        except Exception as e:
            self.log_activity(f"❌ Error starting AI bot: {e}")
            return False
    
    def closeEvent(self, event):
        """Cleanup when closing tab"""
        # Stop any running AI test
        if self.ai_test_worker and self.ai_test_worker.isRunning():
            self.ai_test_worker.stop()
            self.ai_test_worker.wait(3000)  # Wait max 3 seconds
        
        # Close progress dialog
        if self.progress_dialog:
            self.progress_dialog.close()
        
        event.accept()


# ===============================================
# 🔧 DIALOG CLASSES - Popup Windows
# ===============================================

class AddAIDialog(QDialog):
    """Dialog thêm/sửa AI account"""
    
    def __init__(self, parent=None, ai_data=None, telegram_accounts=None):
        super().__init__(parent)
        self.ai_data = ai_data
        self.telegram_accounts = telegram_accounts or []
        self.setWindowTitle("Thêm AI" if ai_data is None else "Sửa AI")
        self.setModal(True)
        self.resize(450, 350)
        
        self.init_ui()
        
        if ai_data:
            self.load_ai_data(ai_data)
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Form layout
        form_layout = QFormLayout()
        
        # Tên AI
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Nhập tên AI...")
        form_layout.addRow("Tên AI:", self.name_edit)
        
        # Chọn tài khoản Telegram
        self.account_combo = QComboBox()
        self.account_combo.addItem("-- Chọn tài khoản Telegram --", None)
        
        for acc in self.telegram_accounts:
            display_text = f"{acc['phone']} ({acc['status']})"
            self.account_combo.addItem(display_text, acc)
        
        self.account_combo.currentIndexChanged.connect(self.on_account_selected)
        form_layout.addRow("Tài khoản Telegram:", self.account_combo)
        
        # Hiển thị thông tin tài khoản đã chọn (read-only)
        self.phone_label = QLabel("Chưa chọn")
        self.phone_label.setStyleSheet("color: #666; padding: 5px; background: #f5f5f5; border-radius: 3px;")
        form_layout.addRow("Số điện thoại:", self.phone_label)
        
        self.status_label = QLabel("Chưa chọn")
        self.status_label.setStyleSheet("color: #666; padding: 5px; background: #f5f5f5; border-radius: 3px;")
        form_layout.addRow("Trạng thái:", self.status_label)
        
        self.proxy_label = QLabel("Chưa chọn")
        self.proxy_label.setStyleSheet("color: #666; padding: 5px; background: #f5f5f5; border-radius: 3px;")
        form_layout.addRow("Proxy:", self.proxy_label)
        
        # Mô tả AI
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        self.description_edit.setPlaceholderText("Mô tả AI...")
        form_layout.addRow("Mô tả:", self.description_edit)
        
        layout.addLayout(form_layout)
        
        # Thông báo
        info_label = QLabel("💡 Chọn tài khoản Telegram đã đăng nhập từ tab 'Quản lý Tài khoản'")
        info_label.setStyleSheet("color: #1976d2; font-style: italic; padding: 10px; font-size: 10pt; font-family: 'Segoe UI Regular', 'Segoe UI', 'Roboto', 'Arial';")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Thêm AI")
        buttons.button(QDialogButtonBox.Cancel).setText("Hủy")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def on_account_selected(self, index):
        """Xử lý khi chọn tài khoản"""
        account_data = self.account_combo.itemData(index)
        
        if account_data:
            self.phone_label.setText(account_data['phone'])
            self.status_label.setText(account_data['status'])
            self.proxy_label.setText(account_data['proxy'] or "Không sử dụng")
            
            # Tự động đặt tên AI nếu chưa có
            if not self.name_edit.text():
                phone = account_data['phone']
                # Tạo tên AI từ số điện thoại
                if phone.startswith('+84'):
                    ai_name = f"AI_{phone[-4:]}"  # Lấy 4 số cuối
                else:
                    ai_name = f"AI_{phone[-4:]}"
                self.name_edit.setText(ai_name)
        else:
            self.phone_label.setText("Chưa chọn")
            self.status_label.setText("Chưa chọn")
            self.proxy_label.setText("Chưa chọn")
    
    def accept(self):
        """Kiểm tra dữ liệu trước khi chấp nhận"""
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập tên AI!")
            return
        
        if self.account_combo.currentIndex() == 0:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn tài khoản Telegram!")
            return
        
        super().accept()
    
    def load_ai_data(self, ai_data):
        """Load dữ liệu AI vào form"""
        self.name_edit.setText(ai_data.get('name', ''))
        self.description_edit.setPlainText(ai_data.get('description', ''))
        
        # Tìm và chọn tài khoản tương ứng
        phone = ai_data.get('phone', '')
        for i in range(1, self.account_combo.count()):
            account_data = self.account_combo.itemData(i)
            if account_data and account_data['phone'] == phone:
                self.account_combo.setCurrentIndex(i)
                break
    
    def get_ai_data(self):
        """Lấy dữ liệu từ form"""
        account_data = self.account_combo.itemData(self.account_combo.currentIndex())
        
        return {
            'name': self.name_edit.text().strip(),
            'phone': account_data['phone'] if account_data else '',
            'username': account_data['username'] if account_data else '',
            'status_telegram': account_data['status'] if account_data else '',
            'proxy': account_data['proxy'] if account_data else '',
            'description': self.description_edit.toPlainText().strip()
        }


# ===============================================
# 🔧 ADD GROUP DIALOG - Dialog thêm nhóm
# ===============================================

class AddGroupDialog(QDialog):
    """Dialog thêm nhóm chat"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Thêm nhóm chat")
        self.setModal(True)
        self.resize(450, 300)
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Form layout
        form_layout = QFormLayout()
        
        # Tên nhóm
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Nhập tên nhóm...")
        form_layout.addRow("Tên nhóm:", self.name_edit)
        
        # Group ID/Username
        self.group_id_edit = QLineEdit()
        self.group_id_edit.setPlaceholderText("@groupname hoặc -1001234567890")
        form_layout.addRow("Group ID/Username:", self.group_id_edit)
        
        # Link nhóm
        self.link_edit = QLineEdit()
        self.link_edit.setPlaceholderText("https://t.me/groupname")
        form_layout.addRow("Link nhóm:", self.link_edit)
        
        # Mô tả
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        self.description_edit.setPlaceholderText("Mô tả nhóm...")
        form_layout.addRow("Mô tả:", self.description_edit)
        
        layout.addLayout(form_layout)
        
        # Thông báo hướng dẫn
        info_label = QLabel("💡 Có thể nhập Group ID (số âm) hoặc Username (@groupname) hoặc Link nhóm")
        info_label.setStyleSheet("color: #1976d2; font-style: italic; padding: 10px; font-size: 10pt; font-family: 'Segoe UI Regular', 'Segoe UI', 'Roboto', 'Arial';")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Thêm nhóm")
        buttons.button(QDialogButtonBox.Cancel).setText("Hủy")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        # Kết nối signal để tự động điền thông tin
        self.link_edit.textChanged.connect(self.on_link_changed)
    
    def on_link_changed(self, text):
        """Tự động điền thông tin khi nhập link"""
        if text.startswith("https://t.me/"):
            # Trích xuất username từ link
            username = text.replace("https://t.me/", "").strip()
            if username and not self.group_id_edit.text():
                self.group_id_edit.setText(f"@{username}")
            
            # Tự động đặt tên nhóm nếu chưa có
            if username and not self.name_edit.text():
                self.name_edit.setText(username.title())
    
    def accept(self):
        """Kiểm tra dữ liệu trước khi chấp nhận"""
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập tên nhóm!")
            return
        
        if not self.group_id_edit.text().strip() and not self.link_edit.text().strip():
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập ít nhất Group ID hoặc Link nhóm!")
            return
        
        super().accept()
    
    def get_group_data(self):
        """Lấy dữ liệu từ form"""
        return {
            'name': self.name_edit.text().strip(),
            'id': self.group_id_edit.text().strip(),
            'link': self.link_edit.text().strip(),
            'description': self.description_edit.toPlainText().strip()
        } 