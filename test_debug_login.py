#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script để kiểm tra debug logging có hoạt động không
"""

import sys
import os

# Thêm thư mục gốc vào sys.path
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print(f"[TEST] Project root: {project_root}")
print(f"[TEST] sys.path: {sys.path}")

try:
    # Tạo QApplication trước
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    print("[TEST] ✅ Tạo QApplication thành công")
    
    from src.ui.account_management import AccountManagementTab
    print("[TEST] ✅ Import AccountManagementTab thành công")
    
    # Tạo instance để test
    account_tab = AccountManagementTab()
    print("[TEST] ✅ Tạo AccountManagementTab instance thành công")
    
    # Test một vài method
    print(f"[TEST] Số lượng accounts: {len(account_tab.accounts)}")
    
    # Test debug method nếu có driver giả
    class MockDriver:
        def __init__(self):
            self.current_url = "https://www.instagram.com/"
            self.title = "Instagram"
        
        def find_elements(self, by, selector):
            print(f"[MOCK] find_elements called with: {by}, {selector}")
            return []
        
        def get_attribute(self, attr):
            return f"mock_{attr}"
        
        @property
        def location(self):
            return {'x': 100, 'y': 200}
        
        @property
        def size(self):
            return {'width': 50, 'height': 30}
        
        def is_displayed(self):
            return True
    
    mock_driver = MockDriver()
    print("[TEST] Tạo mock driver thành công")
    
    # Test debug function
    try:
        account_tab.debug_instagram_dom(mock_driver, "test_user")
        print("[TEST] ✅ Debug function hoạt động")
    except Exception as e:
        print(f"[TEST] ❌ Debug function lỗi: {e}")
        import traceback
        traceback.print_exc()
    
    # Test check icons function
    try:
        result = account_tab.check_home_and_explore_icons(mock_driver)
        print(f"[TEST] check_home_and_explore_icons result: {result}")
    except Exception as e:
        print(f"[TEST] ❌ check_home_and_explore_icons lỗi: {e}")
        import traceback
        traceback.print_exc()
    
    prin