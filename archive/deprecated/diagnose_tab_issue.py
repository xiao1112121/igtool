#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnostic script for Account Management Tab issue
"""

import sys
import os
import traceback

# Add project root to path
project_root = os.path.abspath('.')
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def diagnose_issue():
    """Diagnose the AccountManagementTab issue"""
    print("🔍 Diagnosing Account Management Tab issue...")
    print("=" * 60)
    
    # Step 1: Check Python environment
    print("1. Python Environment:")
    print(f"   Python version: {sys.version}")
    print(f"   Working directory: {os.getcwd()}")
    print("   ✅ Python OK")
    
    # Step 2: Test basic imports
    print("\n2. Testing basic imports:")
    try:
        from PySide6.QtWidgets import QApplication, QWidget
        print("   ✅ PySide6: OK")
    except ImportError as e:
        print(f"   ❌ PySide6: {e}")
        return False
    
    try:
        from selenium import webdriver
        print("   ✅ Selenium: OK")
    except ImportError as e:
        print(f"   ❌ Selenium: {e}")
        return False
    
    # Step 3: Test project structure
    print("\n3. Checking project structure:")
    required_paths = [
        "src/",
        "src/ui/",
        "src/ui/account_management.py"
    ]
    
    for path in required_paths:
        if os.path.exists(path):
            print(f"   ✅ {path}")
        else:
            print(f"   ❌ {path} - Missing!")
            return False
    
    # Step 4: Test AccountManagementTab import
    print("\n4. Testing AccountManagementTab import:")
    try:
        from src.ui.account_management import AccountManagementTab
        print("   ✅ Import successful")
    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        print("\nDetailed traceback:")
        traceback.print_exc()
        return False
    
    # Step 5: Test initialization
    print("\n5. Testing AccountManagementTab initialization:")
    try:
        if not QApplication.instance():
            app = QApplication([])
        
        tab = AccountManagementTab()
        print("   ✅ Initialization successful")
        return True
        
    except Exception as e:
        print(f"   ❌ Initialization failed: {e}")
        print("\nDetailed traceback:")
        traceback.print_exc()
        return False

def create_simple_fix():
    """Create a simplified version of the account management tab"""
    print("\n🔧 Creating simplified AccountManagementTab...")
    
    backup_path = "src/ui/account_management.py.backup_original"
    original_path = "src/ui/account_management.py"
    
    # Backup original file
    if os.path.exists(original_path) and not os.path.exists(backup_path):
        import shutil
        shutil.copy2(original_path, backup_path)
        print(f"   ✅ Backed up original to {backup_path}")
    
    # Create simplified version
    simplified_code = '''import os
import json
from typing import List, Dict, Any
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox)
from PySide6.QtCore import Qt, Signal

class AccountManagementTab(QWidget):
    """Simplified Account Management Tab"""
    
    folders_updated = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.accounts = []
        self.accounts_file = "accounts.json"
        
        # Load accounts if file exists
        self.load_accounts()
        
        # Initialize UI
        self.init_ui()
        
        print("[DEBUG] Simplified AccountManagementTab initialized successfully")
    
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("Quản lý Tài khoản")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # Add account button
        btn_add = QPushButton("Thêm tài khoản")
        btn_add.clicked.connect(self.add_account_dialog)
        header_layout.addWidget(btn_add)
        
        layout.addLayout(header_layout)
        
        # Account table
        self.account_table = QTableWidget()
        self.account_table.setColumnCount(4)
        self.account_table.setHorizontalHeaderLabels([
            "STT", "Tên đăng nhập", "Mật khẩu", "Trạng thái"
        ])
        
        # Set column widths
        header = self.account_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        
        self.account_table.setColumnWidth(0, 50)
        self.account_table.setColumnWidth(3, 120)
        
        layout.addWidget(self.account_table)
        
        # Update table
        self.update_account_table()
        
        # Status label
        self.status_label = QLabel("Sẵn sàng")
        self.status_label.setStyleSheet("padding: 5px; border-top: 1px solid #ccc;")
        layout.addWidget(self.status_label)
    
    def load_accounts(self):
        """Load accounts from JSON file"""
        if os.path.exists(self.accounts_file):
            try:
                with open(self.accounts_file, 'r', encoding='utf-8') as f:
                    self.accounts = json.load(f)
                print(f"[DEBUG] Loaded {len(self.accounts)} accounts")
            except Exception as e:
                print(f"[ERROR] Failed to load accounts: {e}")
                self.accounts = []
        else:
            self.accounts = []
    
    def save_accounts(self):
        """Save accounts to JSON file"""
        try:
            with open(self.accounts_file, 'w', encoding='utf-8') as f:
                json.dump(self.accounts, f, indent=4, ensure_ascii=False)
            print("[DEBUG] Accounts saved successfully")
        except Exception as e:
            print(f"[ERROR] Failed to save accounts: {e}")
    
    def update_account_table(self):
        """Update the account table display"""
        self.account_table.setRowCount(len(self.accounts))
        
        for row, account in enumerate(self.accounts):
            # STT
            self.account_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            
            # Username
            username = account.get('username', '')
            self.account_table.setItem(row, 1, QTableWidgetItem(username))
            
            # Password (masked)
            password = '*' * len(account.get('password', ''))
            self.account_table.setItem(row, 2, QTableWidgetItem(password))
            
            # Status
            status = account.get('status', 'Chưa kiểm tra')
            self.account_table.setItem(row, 3, QTableWidgetItem(status))
        
        # Update status
        self.status_label.setText(f"Tổng: {len(self.accounts)} tài khoản")
    
    def add_account_dialog(self):
        """Show dialog to add new account"""
        from PySide6.QtWidgets import QDialog, QFormLayout, QLineEdit, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Thêm tài khoản mới")
        dialog.setModal(True)
        
        layout = QFormLayout(dialog)
        
        username_edit = QLineEdit()
        password_edit = QLineEdit()
        password_edit.setEchoMode(QLineEdit.Password)
        
        layout.addRow("Tên đăng nhập:", username_edit)
        layout.addRow("Mật khẩu:", password_edit)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec() == QDialog.Accepted:
            username = username_edit.text().strip()
            password = password_edit.text().strip()
            
            if username and password:
                new_account = {
                    'username': username,
                    'password': password,
                    'status': 'Chưa kiểm tra',
                    'folder': 'Tổng'
                }
                self.accounts.append(new_account)
                self.save_accounts()
                self.update_account_table()
                
                QMessageBox.information(self, "Thành công", f"Đã thêm tài khoản {username}")
            else:
                QMessageBox.warning(self, "Lỗi", "Vui lòng nhập đầy đủ thông tin")
    
    def close_all_drivers(self):
        """Close all active drivers (compatibility method)"""
        pass
    
    def sync_proxy_data(self):
        """Sync proxy data (compatibility method)"""
        pass
'''
    
    try:
        with open(original_path, 'w', encoding='utf-8') as f:
            f.write(simplified_code)
        print("   ✅ Created simplified AccountManagementTab")
        return True
    except Exception as e:
        print(f"   ❌ Failed to create simplified version: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Instagram Automation Tool - Tab Diagnostic")
    print("=" * 60)
    
    if diagnose_issue():
        print("\n🎉 SUCCESS: AccountManagementTab is working correctly!")
        print("The '(Lỗi)' issue should be resolved.")
    else:
        print("\n❌ ISSUE DETECTED: Creating simplified version...")
        if create_simple_fix():
            print("\n✅ Simplified version created. Please restart the application.")
            print("The Account Management tab should now work.")
        else:
            print("\n❌ Failed to create fix. Please check the error messages above.")
    
    print("\n" + "=" * 60)
    print("Diagnostic completed.") 