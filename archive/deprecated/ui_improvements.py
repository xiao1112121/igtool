#!/usr/bin/env python3
"""
UI Improvements Module
Provides utility functions to enhance the visual appearance and user experience
"""

from PySide6.QtWidgets import (QPushButton, QTableWidget, QGroupBox, QLineEdit, 
                              QComboBox, QSpinBox, QLabel, QProgressBar, QFrame,
                              QTabWidget, QTabBar, QHeaderView, QMenu, QWidget)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from typing import Union, Optional


def apply_modern_button_style(button: QPushButton, variant: str = "primary") -> None:
    """Apply modern button styling with variants"""
    base_style = """
        QPushButton {
            border: none;
            border-radius: 8px;
            padding: 10px 20px;
            font-weight: 500;
            font-size: 11pt;
            min-height: 36px;
        }
        QPushButton:disabled {
            background: #94a3b8;
            color: #64748b;
        }
    """
    
    variants = {
        "primary": """
            QPushButton {
                background: #3b82f6;
                color: white;
            }
            QPushButton:hover {
                background: #2563eb;
            }
        """,
        "success": """
            QPushButton {
                background: #10b981;
                color: white;
            }
            QPushButton:hover {
                background: #059669;
            }
        """,
        "danger": """
            QPushButton {
                background: #ef4444;
                color: white;
            }
            QPushButton:hover {
                background: #dc2626;
            }
        """
    }
    
    style = base_style + variants.get(variant, variants["primary"])
    button.setStyleSheet(style)


def apply_modern_table_style(table: QTableWidget) -> None:
    """Apply modern table styling"""
    style = """
        QTableWidget {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            gridline-color: #f1f5f9;
            font-size: 10pt;
            selection-background-color: #eff6ff;
            alternate-background-color: #f8fafc;
        }
        QTableWidget::item {
            padding: 12px 8px;
            border: none;
            border-bottom: 1px solid #f1f5f9;
        }
        QTableWidget::item:selected {
            background: #eff6ff;
            color: #1e40af;
        }
    """
    table.setStyleSheet(style)
    table.setAlternatingRowColors(True)


def apply_modern_input_style(widget) -> None:
    """Apply modern input styling"""
    style = f"""
        {widget.__class__.__name__} {{
            background: #ffffff;
            border: 1px solid #d1d5db;
            border-radius: 8px;
            padding: 10px 12px;
            font-size: 11pt;
            color: #374151;
            min-height: 20px;
        }}
        {widget.__class__.__name__}:focus {{
            border-color: #3b82f6;
        }}
    """
    widget.setStyleSheet(style)


def apply_modern_groupbox_style(groupbox: QGroupBox) -> None:
    """Apply modern group box styling"""
    style = """
        QGroupBox {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            margin-top: 12px;
            padding-top: 16px;
            font-weight: 600;
            font-size: 12pt;
        }
        QGroupBox::title {
            color: #1e40af;
            subcontrol-origin: margin;
            left: 16px;
            top: 8px;
            background: #ffffff;
            padding: 0 8px;
        }
    """
    groupbox.setStyleSheet(style)


def apply_status_label_style(label: QLabel, status: str = "info") -> None:
    """Apply status-specific styling to labels"""
    status_styles = {
        "success": "background: #d1fae5; color: #059669; border: 1px solid #a7f3d0;",
        "error": "background: #fee2e2; color: #dc2626; border: 1px solid #fca5a5;",
        "warning": "background: #fef3c7; color: #d97706; border: 1px solid #fcd34d;",
        "info": "background: #dbeafe; color: #1d4ed8; border: 1px solid #93c5fd;"
    }
    
    base_style = f"""
        QLabel {{
            font-weight: 500;
            font-size: 10pt;
            padding: 4px 8px;
            border-radius: 4px;
            {status_styles.get(status, status_styles["info"])}
        }}
    """
    label.setStyleSheet(base_style)


def apply_modern_tab_style(tab_widget: QTabWidget) -> None:
    """Apply modern tab widget styling"""
    style = """
        QTabWidget {
            background: transparent;
            border: none;
        }
        QTabWidget::pane {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            margin-top: 8px;
            padding: 16px;
        }
        QTabBar {
            background: transparent;
            qproperty-drawBase: 0;
        }
        QTabBar::tab {
            background: #f1f5f9;
            color: #64748b;
            border: 1px solid #e2e8f0;
            border-bottom: none;
            padding: 12px 24px;
            margin-right: 2px;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            font-weight: 500;
            font-size: 11pt;
            min-width: 120px;
        }
        QTabBar::tab:selected {
            background: #ffffff;
            color: #1e40af;
            border-color: #e2e8f0;
            font-weight: 600;
            border-bottom: 2px solid #3b82f6;
        }
        QTabBar::tab:hover:!selected {
            background: #e2e8f0;
            color: #475569;
        }
    """
    tab_widget.setStyleSheet(style)


def apply_modern_progress_style(progress: QProgressBar) -> None:
    """Apply modern progress bar styling"""
    style = """
        QProgressBar {
            background: #f1f5f9;
            border: none;
            border-radius: 8px;
            text-align: center;
            font-weight: 500;
            color: #374151;
            height: 24px;
        }
        QProgressBar::chunk {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #3b82f6, stop:1 #1d4ed8);
            border-radius: 8px;
        }
    """
    progress.setStyleSheet(style)


def apply_modern_menu_style(menu: QMenu) -> None:
    """Apply modern context menu styling"""
    style = """
        QMenu {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 8px;
        }
        QMenu::item {
            background: transparent;
            color: #374151;
            padding: 10px 16px;
            border-radius: 8px;
            font-size: 11pt;
            margin: 2px;
        }
        QMenu::item:selected {
            background: #eff6ff;
            color: #1e40af;
        }
        QMenu::separator {
            height: 1px;
            background: #e2e8f0;
            margin: 8px 16px;
        }
    """
    menu.setStyleSheet(style)


def create_modern_frame(title: str = None) -> QFrame:
    """Create a modern styled frame container"""
    frame = QFrame()
    style = """
        QFrame {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 16px;
        }
    """
    frame.setStyleSheet(style)
    
    if title:
        frame.setToolTip(title)
    
    return frame


def add_hover_effect(widget) -> None:
    """Add hover effect animation to widgets"""
    # This would require more complex implementation with QPropertyAnimation
    # For now, we'll rely on CSS hover states
    pass


def apply_dark_theme(widget) -> None:
    """Apply dark theme to a widget (experimental)"""
    dark_style = """
        {widget_type} {{
            background-color: #1e293b;
            color: #f1f5f9;
            border-color: #475569;
        }}
    """.format(widget_type=widget.__class__.__name__)
    
    widget.setStyleSheet(dark_style)


# Utility functions for common UI patterns
def create_action_button(text: str, variant: str = "primary") -> QPushButton:
    """Create a standardized action button"""
    button = QPushButton(text)
    apply_modern_button_style(button, variant)
    return button


def create_status_label(text: str, status: str = "info") -> QLabel:
    """Create a standardized status label"""
    label = QLabel(text)
    apply_status_label_style(label, status)
    return label


def enhance_widget_appearance(widget) -> None:
    """Auto-apply appropriate styling based on widget type"""
    if isinstance(widget, QPushButton):
        apply_modern_button_style(widget)
    elif isinstance(widget, QTableWidget):
        apply_modern_table_style(widget)
    elif isinstance(widget, (QLineEdit, QComboBox, QSpinBox)):
        apply_modern_input_style(widget)
    elif isinstance(widget, QGroupBox):
        apply_modern_groupbox_style(widget)
    elif isinstance(widget, QTabWidget):
        apply_modern_tab_style(widget)
    elif isinstance(widget, QProgressBar):
        apply_modern_progress_style(widget)
    elif isinstance(widget, QMenu):
        apply_modern_menu_style(widget)


if __name__ == "__main__":
    print("🎨 UI Improvements module loaded successfully!")
    print("Available functions:")
    print("- apply_modern_button_style()")
    print("- apply_modern_table_style()")
    print("- apply_modern_input_style()")
    print("- apply_modern_groupbox_style()")
    print("- apply_status_label_style()")
    print("- enhance_widget_appearance()") 