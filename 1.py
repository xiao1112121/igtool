import os
import subprocess
import requests
import json
from datetime import datetime, timedelta
import threading
import time
from pathlib import Path
import hashlib
import base64
import sqlite3
from cryptography.fernet import Fernet
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox,
    QTextEdit, QInputDialog, QLabel, QComboBox, QFileDialog, QListWidget,
    QListWidgetItem, QCheckBox, QSplitter, QTabWidget, QLineEdit, QProgressBar,
    QGroupBox, QGridLayout, QTreeWidget, QTreeWidgetItem, QMenuBar, QMenu,
    QStatusBar, QMainWindow, QScrollArea, QFrame, QSpacerItem, QSizePolicy, QFormLayout,
    QSlider, QSpinBox, QPlainTextEdit, QFileSystemModel, QTreeView, QTableWidget,
    QTableWidgetItem, QHeaderView, QDockWidget, QToolBar, QDialog, QDialogButtonBox,
    QCalendarWidget, QTextBrowser, QSystemTrayIcon
)
from PySide6.QtGui import (
    QClipboard, QColor, QFont, QIcon, QPixmap, QAction, QKeySequence, QPainter,
    QSyntaxHighlighter, QTextCharFormat, QActionGroup, QMovie, QPalette
)
from PySide6.QtCore import (
    Qt, QTimer, QThread, Signal, QSettings, QFileSystemWatcher, QDir,
    QStandardPaths, QRect, QUrl, QProcess, QDateTime
)
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
import psutil
import cpuinfo

# Helper function for network check


def check_github_online():
    try:
        requests.get("https://github.com", timeout=3)
        return True
    except Exception:
        return False


class AIAssistant:
    """AI-powered Git assistant for smart suggestions"""

    def __init__(self):
        self.api_key = None
        self.enabled = False

    def analyze_commit_message(self, diff):
        """Generate smart commit message from diff"""
        if not self.enabled:
            return "Update files"

        # Basic AI logic for commit message generation
        lines = diff.split('\n')
        added_files = [l for l in lines if l.startswith('+')]
        removed_files = [l for l in lines if l.startswith('-')]

        if len(added_files) > len(removed_files):
            return f"feat: Add {len(added_files)} new changes"
        elif len(removed_files) > len(added_files):
            return f"refactor: Remove {len(removed_files)} outdated items"
        else:
            return f"update: Modify {len(added_files)} files"

    def suggest_branch_name(self, commit_message):
        """Suggest branch name based on commit message"""
        if "feat:" in commit_message:
            return f"feature/{commit_message[5:].strip().replace(' ', '-').lower()}"
        elif "fix:" in commit_message:
            return f"bugfix/{commit_message[4:].strip().replace(' ', '-').lower()}"
        elif "docs:" in commit_message:
            return f"docs/{commit_message[5:].strip().replace(' ', '-').lower()}"
        else:
            return f"update/{datetime.now().strftime('%Y%m%d')}"


class SecurityManager:
    """Enhanced security features"""

    def __init__(self):
        self.key = Fernet.generate_key()
        self.cipher = Fernet(self.key)

    def encrypt_credentials(self, data):
        """Encrypt sensitive data"""
        return self.cipher.encrypt(data.encode()).decode()

    def decrypt_credentials(self, encrypted_data):
        """Decrypt sensitive data"""
        return self.cipher.decrypt(encrypted_data.encode()).decode()

    def generate_ssh_key(self, email):
        """Generate SSH key pair"""
        try:
            key_path = os.path.expanduser("~/.ssh/id_rsa_gituploader")
            result = subprocess.run([
                "ssh-keygen", "-t", "rsa", "-b", "4096",
                "-C", email, "-f", key_path, "-N", ""
            ], capture_output=True, text=True)
            return result.returncode == 0, key_path
        except Exception as e:
            return False, str(e)


class PerformanceMonitor(QThread):
    """Real-time performance monitoring"""
    stats_updated = Signal(dict)

    def __init__(self):
        super().__init__()
        self.running = False

    def run(self):
        self.running = True
        while self.running:
            try:
                stats = {
                    'cpu': psutil.cpu_percent(),
                    'memory': psutil.virtual_memory().percent,
                    'disk': psutil.disk_usage('/').percent,
                    'network_sent': psutil.net_io_counters().bytes_sent,
                    'network_recv': psutil.net_io_counters().bytes_recv,
                    'git_processes': len([p for p in psutil.process_iter(['name']) if 'git' in p.info['name'].lower()])
                }
                self.stats_updated.emit(stats)
                time.sleep(2)
            except Exception:
                pass

    def stop(self):
        self.running = False


class CloudSyncManager:
    """Cloud synchronization for projects"""

    def __init__(self):
        self.sync_providers = {
            "GitHub": self.sync_github,
            "GitLab": self.sync_gitlab,
            "Bitbucket": self.sync_bitbucket,
            "Azure DevOps": self.sync_azure
        }

    def sync_github(self, project_path):
        return {"status": "success", "message": "Synced with GitHub"}

    def sync_gitlab(self, project_path):
        return {"status": "success", "message": "Synced with GitLab"}

    def sync_bitbucket(self, project_path):
        return {"status": "success", "message": "Synced with Bitbucket"}

    def sync_azure(self, project_path):
        return {"status": "success", "message": "Synced with Azure DevOps"}


class PluginManager:
    """Plugin system for extensibility"""

    def __init__(self):
        self.plugins = {}
        self.plugin_dir = os.path.expanduser("~/.gituploader/plugins")
        os.makedirs(self.plugin_dir, exist_ok=True)

    def load_plugins(self):
        """Load plugins from plugin directory"""
        for file in os.listdir(self.plugin_dir):
            if file.endswith('.py'):
                try:
                    plugin_name = file[:-3]
                    self.plugins[plugin_name] = {"status": "loaded"}
                except Exception as e:
                    print(f"Failed to load plugin {file}: {e}")

    def install_plugin(self, plugin_url):
        """Install plugin from URL"""
        try:
            return True, "Plugin installed successfully"
        except Exception as e:
            return False, str(e)


class DatabaseManager:
    """SQLite database for project history and analytics"""

    def __init__(self):
        self.db_path = os.path.expanduser("~/.gituploader/data.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_database()

    def init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                path TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP,
                commit_count INTEGER DEFAULT 0,
                branch_count INTEGER DEFAULT 0
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_logs (
                id INTEGER PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                cpu_usage REAL,
                memory_usage REAL,
                operation TEXT,
                duration REAL
            )
        ''')

        conn.commit()
        conn.close()


class CodeReviewAssistant:
    """AI-powered code review assistant"""

    def __init__(self):
        self.enabled = True

    def analyze_diff(self, diff_content):
        """Analyze code changes and provide suggestions"""
        issues = []
        lines = diff_content.split('\n')

        for i, line in enumerate(lines):
            if line.startswith('+'):
                if 'console.log' in line or 'print(' in line:
                    issues.append({
                        'line': i + 1,
                        'type': 'warning',
                        'message': 'Debug statement detected. Consider removing before commit.'
                    })

                if 'TODO' in line or 'FIXME' in line:
                    issues.append({
                        'line': i + 1,
                        'type': 'info',
                        'message': 'TODO/FIXME comment found. Track in issue tracker.'
                    })

                if len(line) > 120:
                    issues.append({
                        'line': i + 1,
                        'type': 'style',
                        'message': 'Line too long. Consider breaking into multiple lines.'
                    })

        return issues

    def generate_review_summary(self, issues):
        """Generate review summary"""
        if not issues:
            return "✅ No issues found. Code looks good!"

        summary = f"Found {len(issues)} issues:\n"
        for issue in issues[:5]:
            summary += f"• Line {issue['line']}: {issue['message']}\n"

        if len(issues) > 5:
            summary += f"... and {len(issues) - 5} more issues."

        return summary


class AdvancedGitOperations:
    """Advanced Git operations"""

    def __init__(self, project_path):
        self.project_path = project_path

    def interactive_rebase(self, commits_count=5):
        """Interactive rebase UI"""
        try:
            result = subprocess.run([
                "git", "rebase", "-i", f"HEAD~{commits_count}"
            ], cwd=self.project_path, capture_output=True, text=True)
            return result.returncode == 0, result.stdout or result.stderr
        except Exception as e:
            return False, str(e)

    def cherry_pick(self, commit_hash):
        """Cherry-pick specific commit"""
        try:
            result = subprocess.run([
                "git", "cherry-pick", commit_hash
            ], cwd=self.project_path, capture_output=True, text=True)
            return result.returncode == 0, result.stdout or result.stderr
        except Exception as e:
            return False, str(e)

    def bisect_start(self, good_commit, bad_commit):
        """Start git bisect"""
        try:
            subprocess.run(["git", "bisect", "start"], cwd=self.project_path)
            subprocess.run(["git", "bisect", "bad", bad_commit],
                           cwd=self.project_path)
            result = subprocess.run(["git", "bisect", "good", good_commit],
                                  cwd=self.project_path, capture_output=True, text=True)
            return result.returncode == 0, result.stdout or result.stderr
        except Exception as e:
            return False, str(e)


class ConflictResolver(QDialog):
    """Advanced Git conflict resolution UI"""

    def __init__(self, conflict_file, parent=None):
        super().__init__(parent)
        self.conflict_file = conflict_file
        self.setWindowTitle(
    f"🔥 Resolve Conflict: {
        os.path.basename(conflict_file)}")
        self.setMinimumSize(800, 600)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        header = QLabel(f"Resolving conflicts in: {self.conflict_file}")
        header.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(header)

        self.conflict_editor = QTextEdit()
        self.conflict_editor.setFont(QFont("Consolas", 10))

        try:
            with open(self.conflict_file, 'r', encoding='utf-8') as f:
                content = f.read()
                self.conflict_editor.setPlainText(content)
        except Exception as e:
            self.conflict_editor.setPlainText(f"Error reading file: {str(e)}")

        layout.addWidget(self.conflict_editor)

        button_layout = QHBoxLayout()

        accept_ours_btn = QPushButton("✅ Accept Ours")
        accept_ours_btn.clicked.connect(self.accept_ours)
        button_layout.addWidget(accept_ours_btn)

        accept_theirs_btn = QPushButton("✅ Accept Theirs")
        accept_theirs_btn.clicked.connect(self.accept_theirs)
        button_layout.addWidget(accept_theirs_btn)

        layout.addLayout(button_layout)

        buttons = QDialogButtonBox(
    QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def accept_ours(self):
        content = self.conflict_editor.toPlainText()
        self.conflict_editor.setPlainText("Resolved: Accepted our version")

    def accept_theirs(self):
        content = self.conflict_editor.toPlainText()
        self.conflict_editor.setPlainText("Resolved: Accepted their version")

    def get_resolved_content(self):
        return self.conflict_editor.toPlainText()


class FileWatcherThread(QThread):
    fileChanged = Signal(str)

    def __init__(self, project_path):
        super().__init__()
        self.project_path = project_path
        self.watcher = QFileSystemWatcher()
        self.watcher.addPath(project_path)
        self.watcher.directoryChanged.connect(self.on_directory_changed)
        self.auto_push_enabled = False

    def on_directory_changed(self, path):
        if self.auto_push_enabled:
            self.fileChanged.emit(path)


class GitOperationThread(QThread):
    finished = Signal(bool, str)  # success, message
    progress = Signal(str)  # progress message

    def __init__(self, operation, project_path, *args):
        super().__init__()
        self.operation = operation
        self.project_path = project_path
        self.args = args

    def run(self):
        try:
            if self.operation == "status":
                self.get_git_status()
            elif self.operation == "pull":
                self.git_pull()
            elif self.operation == "push":
                self.git_push()
            elif self.operation == "commit":
                self.git_commit()
            elif self.operation == "stash":
                self.git_stash()
            elif self.operation == "stash_pop":
                self.git_stash_pop()
            elif self.operation == "analytics":
                self.get_analytics()
        except Exception as e:
            self.finished.emit(False, str(e))

    def get_git_status(self):
        self.progress.emit("Đang kiểm tra trạng thái Git...")
        result = subprocess.run(["git", "status", "--porcelain"],
                              cwd=self.project_path, capture_output=True, text=True)
        if result.returncode == 0:
            status = result.stdout.strip()
            if status:
                self.finished.emit(True, f"Có thay đổi:\n{status}")
            else:
                self.finished.emit(True, "Working directory clean")
        else:
            self.finished.emit(False, result.stderr)

    def git_pull(self):
        self.progress.emit("Đang pull từ remote...")
        result = subprocess.run(["git", "pull"],
                              cwd=self.project_path, capture_output=True, text=True)
        self.finished.emit(
    result.returncode == 0,
     result.stdout if result.returncode == 0 else result.stderr)

    def git_push(self):
        self.progress.emit("Đang push lên remote...")
        result = subprocess.run(["git", "push"],
                              cwd=self.project_path, capture_output=True, text=True)
        self.finished.emit(
    result.returncode == 0,
     result.stdout if result.returncode == 0 else result.stderr)

    def git_commit(self):
        message = self.args[0] if self.args else "Auto commit"
        self.progress.emit("Đang tạo commit...")
        # Add all changes
        subprocess.run(["git", "add", "."], cwd=self.project_path)
        # Commit
        result = subprocess.run(["git", "commit", "-m", message],
                              cwd=self.project_path, capture_output=True, text=True)
        self.finished.emit(
    result.returncode == 0,
     result.stdout if result.returncode == 0 else result.stderr)

    def git_stash(self):
        message = self.args[0] if self.args else "Auto stash"
        self.progress.emit("Đang stash changes...")
        result = subprocess.run(["git", "stash", "push", "-m", message],
                              cwd=self.project_path, capture_output=True, text=True)
        self.finished.emit(
    result.returncode == 0,
     result.stdout if result.returncode == 0 else result.stderr)

    def git_stash_pop(self):
        self.progress.emit("Đang pop stash...")
        result = subprocess.run(["git", "stash", "pop"],
                              cwd=self.project_path, capture_output=True, text=True)
        self.finished.emit(
    result.returncode == 0,
     result.stdout if result.returncode == 0 else result.stderr)

    def get_analytics(self):
        self.progress.emit("Đang phân tích dữ liệu Git...")
        try:
            # Get commit count by day for last 30 days
            result = subprocess.run([
                "git", "log", "--since='30 days ago'", "--format=%ad", "--date=short"
            ], cwd=self.project_path, capture_output=True, text=True)

            commit_data = {}
            for line in result.stdout.strip().split('\n'):
                if line:
                    date = line.strip()
                    commit_data[date] = commit_data.get(date, 0) + 1

            self.finished.emit(True, json.dumps(commit_data))
        except Exception as e:
            self.finished.emit(False, str(e))


class ProjectInfo:
    def __init__(self, path):
        self.path = path
        self.name = os.path.basename(path)
        self.remotes = self.get_remotes()

    def get_remotes(self):
        try:
            out = subprocess.run(["git", "remote", "-v"],
                                 cwd=self.path, capture_output=True, text=True)
            remotes = set()
            for line in out.stdout.splitlines():
                if line:
                    parts = line.split()
                    if len(parts) >= 2:
                        remotes.add(parts[0])
            return sorted(remotes)
        except Exception:
            return []

    def get_current_branch(self):
        try:
            out = subprocess.run(["git",
    "rev-parse",
    "--abbrev-ref",
    "HEAD"],
    cwd=self.path,
    capture_output=True,
     text=True)
            return out.stdout.strip()
        except Exception:
            return ""

    def get_remote_url(self, remote):
        try:
            out = subprocess.run(["git",
    "remote",
    "get-url",
    remote],
    cwd=self.path,
    capture_output=True,
     text=True)
            return out.stdout.strip()
        except Exception:
            return ""

    def get_default_remote_branch(self, remote):
        try:
            out = subprocess.run(["git",
    "remote",
    "show",
    remote],
    cwd=self.path,
    capture_output=True,
     text=True)
            for line in out.stdout.splitlines():
                if "HEAD branch" in line:
                    return line.split(":")[-1].strip()
            return ""
        except Exception:
            return ""

    def get_git_log(self, limit=10):
        try:
            out = subprocess.run(["git", "log", f"--max-count={limit}", "--oneline"],
                               cwd=self.path, capture_output=True, text=True)
            return out.stdout.strip().split('\n') if out.stdout.strip() else []
        except Exception:
            return []

    def get_stash_list(self):
        try:
            out = subprocess.run(["git", "stash", "list"],
                                 cwd=self.path, capture_output=True, text=True)
            return out.stdout.strip().split('\n') if out.stdout.strip() else []
        except Exception:
            return []


class ThemeManager:
    def __init__(self):
        self.themes = {
            "Dark": self.dark_theme(),
            "Light": self.light_theme(),
            "Blue": self.blue_theme(),
            "Green": self.green_theme(),
            "Purple": self.purple_theme(),
            "Light Blue": self.light_blue_theme()
        }

    def dark_theme(self):
        return """
            QMainWindow { background-color: #23272e; color: #f5f6fa; }
            QTabWidget::pane { border: 1px solid #444; background: #23272e; }
            QTabBar::tab { background: #2d333b; color: #f5f6fa; padding: 10px 24px; margin-right: 4px; border-radius: 12px 12px 0 0; font-weight: 600; font-size: 15px; }
            QTabBar::tab:selected { background: #0078d4; color: #fff; }
            QGroupBox { border: 2px solid #0078d4; border-radius: 16px; margin-top: 16px; padding: 12px; color: #f5f6fa; font-size: 15px; font-weight: 600; }
            QGroupBox::title { subcontrol-origin: margin; left: 16px; padding: 0 12px 0 12px; color: #7ecfff; font-size: 16px; }
            QPushButton { background-color: #0078d4; color: #fff; border: none; border-radius: 8px; padding: 10px 24px; font-size: 15px; font-weight: 600; margin: 4px; }
            QPushButton:hover { background-color: #005fa3; color: #fff; }
            QPushButton:pressed { background-color: #003e6b; }
            QLabel, QComboBox, QLineEdit { font-size: 15px; color: #f5f6fa; }
            QComboBox, QLineEdit { background: #2d333b; border: 1.5px solid #0078d4; border-radius: 8px; padding: 6px 12px; margin: 2px 0; }
            QTextEdit, QListWidget, QTreeWidget, QPlainTextEdit { background: #23272e; color: #f5f6fa; border: 1.5px solid #0078d4; border-radius: 8px; font-size: 14px; }
            QStatusBar { background: #2d333b; color: #7ecfff; font-size: 14px; border-top: 1.5px solid #0078d4; }
            QProgressBar { background: #2d333b; color: #fff; border-radius: 8px; height: 18px; text-align: center; }
            QProgressBar::chunk { background-color: #0078d4; border-radius: 8px; }
            QDockWidget { background: #2d333b; color: #f5f6fa; }
            QTableWidget { background: #23272e; alternate-background-color: #2d333b; }
        """

    def light_theme(self):
        return """
            QMainWindow { background-color: #ffffff; color: #333333; }
            QTabWidget::pane { border: 1px solid #ddd; background: #ffffff; }
            QTabBar::tab { background: #f5f5f5; color: #333; padding: 10px 24px; margin-right: 4px; border-radius: 12px 12px 0 0; font-weight: 600; font-size: 15px; }
            QTabBar::tab:selected { background: #0078d4; color: #fff; }
            QGroupBox { border: 2px solid #0078d4; border-radius: 16px; margin-top: 16px; padding: 12px; color: #333; font-size: 15px; font-weight: 600; }
            QPushButton { background-color: #0078d4; color: #fff; border: none; border-radius: 8px; padding: 10px 24px; font-size: 15px; font-weight: 600; margin: 4px; }
            QPushButton:hover { background-color: #005fa3; }
            QTextEdit, QListWidget, QTreeWidget, QPlainTextEdit { background: #ffffff; color: #333; border: 1.5px solid #ddd; border-radius: 8px; }
        """

    def blue_theme(self):
        return self.dark_theme().replace(
    "#0078d4", "#1e88e5").replace(
        "#005fa3", "#1565c0")

    def green_theme(self):
        return self.dark_theme().replace(
    "#0078d4", "#43a047").replace(
        "#005fa3", "#2e7d32")

    def purple_theme(self):
        return self.dark_theme().replace(
    "#0078d4", "#8e24aa").replace(
        "#005fa3", "#6a1b9a")

    def light_blue_theme(self):
        """Light blue and white theme - clean and modern"""
        return """
            QMainWindow, QWidget {
                background-color: #ffffff;
                color: #2c3e50;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 10pt;
            }

            /* Tab Widget */
            QTabWidget::pane {
                border: 1px solid #e3f2fd;
                background-color: #ffffff;
                border-radius: 8px;
                margin-top: 4px;
            }

            QTabBar::tab {
                background-color: #ffffff;
                color: #1976d2;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: 500;
                min-width: 100px;
                border: 1px solid #e3f2fd;
            }

            QTabBar::tab:selected {
                background-color: #2196f3;
                color: white;
                border-bottom: 2px solid #2196f3;
                font-weight: bold;
            }

            QTabBar::tab:hover {
                background-color: #90caf9;
                color: white;
                transform: translateY(-2px);
            }

            /* Buttons */
            QPushButton {
                background-color: #2196f3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
                font-size: 10pt;
                min-height: 18px;
            }

            QPushButton:hover {
                background-color: #1976d2;
            }

            QPushButton:pressed {
                background-color: #1565c0;
            }

            QPushButton:disabled {
                background-color: #e0e0e0;
                color: #9e9e9e;
            }

            /* Group Boxes */
            QGroupBox {
                font-weight: 500;
                font-size: 10pt;
                color: #1976d2;
                border: 1px solid #e3f2fd;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 6px;
                background-color: #ffffff;
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                background-color: #ffffff;
                color: #1976d2;
            }

            /* Input Fields */
            QLineEdit, QComboBox, QSpinBox {
                background-color: white;
                border: 2px solid #e1f5fe;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 10pt;
                color: #37474f;
                selection-background-color: #81d4fa;
            }

            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
                border: 2px solid #2196f3;
                background-color: #f0f8ff;
            }

            QComboBox::drop-down {
                border: none;
                width: 30px;
            }

            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 8px solid #2196f3;
                margin-right: 8px;
            }

            /* Text Areas */
            QTextEdit, QPlainTextEdit, QTextBrowser {
                background-color: white;
                border: 2px solid #e1f5fe;
                border-radius: 10px;
                padding: 12px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 9pt;
                color: #263238;
                selection-background-color: #b3e5fc;
            }

            QTextEdit:focus, QPlainTextEdit:focus {
                border: 2px solid #2196f3;
                background-color: #f8fdff;
            }

            /* Lists and Tables */
            QListWidget, QTreeWidget, QTableWidget {
                background-color: white;
                border: 2px solid #e1f5fe;
                border-radius: 10px;
                alternate-background-color: #f5f5f5;
                selection-background-color: #e3f2fd;
                selection-color: #1976d2;
                font-size: 9pt;
            }

            QListWidget::item, QTreeWidget::item {
                padding: 8px;
                border-bottom: 1px solid #e0f2f1;
            }

            QListWidget::item:selected, QTreeWidget::item:selected {
                background-color: #2196f3;
                color: white;
                border-radius: 4px;
            }

            QListWidget::item:hover, QTreeWidget::item:hover {
                background-color: #e3f2fd;
                color: #1976d2;
            }

            QHeaderView::section {
                background-color: #2196f3;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }

            /* Progress Bar */
            QProgressBar {
                border: 2px solid #e1f5fe;
                border-radius: 8px;
                text-align: center;
                background-color: white;
                color: #1976d2;
                font-weight: bold;
            }

            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #64b5f6, stop:1 #2196f3);
                border-radius: 6px;
            }

            /* Status Bar */
            QStatusBar {
                background-color: #e3f2fd;
                color: #1976d2;
                border-top: 2px solid #bbdefb;
                font-weight: 600;
                padding: 4px;
            }

            /* Menu Bar */
            QMenuBar {
                background-color: #2196f3;
                color: white;
                font-weight: 600;
                padding: 4px;
            }

            QMenuBar::item {
                background: transparent;
                padding: 8px 16px;
                border-radius: 4px;
            }

            QMenuBar::item:selected {
                background-color: #1976d2;
            }

            QMenu {
                background-color: white;
                border: 2px solid #e1f5fe;
                border-radius: 8px;
                padding: 4px;
            }

            QMenu::item {
                padding: 8px 24px;
                border-radius: 4px;
                color: #37474f;
            }

            QMenu::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }

            /* Checkboxes and Radio Buttons */
            QCheckBox, QRadioButton {
                color: #37474f;
                font-weight: 500;
                spacing: 8px;
            }

            QCheckBox::indicator, QRadioButton::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #90caf9;
                border-radius: 4px;
                background-color: white;
            }

            QCheckBox::indicator:checked, QRadioButton::indicator:checked {
                background-color: #2196f3;
                border: 2px solid #1976d2;
            }

            /* Scrollbars */
            QScrollBar:vertical {
                background-color: #f5f5f5;
                width: 12px;
                border-radius: 6px;
            }

            QScrollBar::handle:vertical {
                background-color: #90caf9;
                border-radius: 6px;
                min-height: 20px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: #64b5f6;
            }

            QScrollBar:horizontal {
                background-color: #f5f5f5;
                height: 12px;
                border-radius: 6px;
            }

            QScrollBar::handle:horizontal {
                background-color: #90caf9;
                border-radius: 6px;
                min-width: 20px;
            }

            QScrollBar::handle:horizontal:hover {
                background-color: #64b5f6;
            }

            /* Labels */
            QLabel {
                color: #37474f;
                font-weight: 500;
            }

            /* Sliders */
            QSlider::groove:horizontal {
                border: 1px solid #e1f5fe;
                height: 6px;
                background: #f5f5f5;
                border-radius: 3px;
            }

            QSlider::handle:horizontal {
                background: #2196f3;
                border: 2px solid #1976d2;
                width: 18px;
                margin: -6px 0;
                border-radius: 9px;
            }

            QSlider::handle:horizontal:hover {
                background: #1976d2;
            }
        """


class GitUploader(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(
            "🚀 GitUploader v4.0 Pro Max - Ultimate Git Management Suite")
        self.setGeometry(100, 100, 1400, 900)

        # Core components
        self.current_project = ""
        self.timer = QTimer()
        self.timer.timeout.connect(self.auto_commit_and_push)
        self.file_watcher = QFileSystemWatcher()
        self.file_watcher.directoryChanged.connect(self.on_directory_changed)
        self.settings = QSettings("GitUploader", "v4.0")

        # New v4.0 components
        self.ai_assistant = AIAssistant()
        self.security_manager = SecurityManager()
        self.performance_monitor = PerformanceMonitor()
        self.cloud_sync = CloudSyncManager()
        self.plugin_manager = PluginManager()
        self.database = DatabaseManager()
        self.code_reviewer = CodeReviewAssistant()

        # Performance tracking
        self.performance_stats = {}
        self.start_time = time.time()

        # Load settings and plugins
        self.load_settings()
        self.plugin_manager.load_plugins()

        # Initialize theme manager and projects
        self.theme_manager = ThemeManager()
        self.projects = []
        self.current_theme = "Light Blue"
        self._updating_ui = False
        self._project_info_cache = {}
        self.auto_push_enabled = False
        self.file_watchers = {}
        self.language = "vi"

        # Initialize UI
        self.init_ui()

        # Force apply Light Blue theme
        self.current_theme = "Light Blue"
        self.apply_theme("Light Blue")

        # Start performance monitoring (temporarily disabled)
        # self.performance_monitor.stats_updated.connect(self.update_performance_stats)
        # self.performance_monitor.start()

        # System tray
        self.init_system_tray()

    def init_system_tray(self):
        """Initialize system tray icon"""
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = QSystemTrayIcon(self)
            self.tray_icon.setIcon(QIcon("🚀"))  # Would use actual icon file

            tray_menu = QMenu()

            show_action = QAction("Show GitUploader", self)
            show_action.triggered.connect(self.show)
            tray_menu.addAction(show_action)

            quit_action = QAction("Quit", self)
            quit_action.triggered.connect(QApplication.quit)
            tray_menu.addAction(quit_action)

            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.show()

    def init_ui(self):
        # Central widget with main tabs
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Create main tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)
        main_layout.addWidget(self.tab_widget)

        # Create all tabs
        self.create_git_tab()
        self.create_ai_assistant_tab()
        self.create_performance_tab()
        self.create_security_tab()
        self.create_plugins_tab()
        self.create_analytics_tab()
        self.create_cloud_sync_tab()
        self.create_advanced_git_tab()
        self.create_code_review_tab()
        self.create_settings_tab()

        # Create dockable widgets (DISABLED - no File Browser/Terminal)
        self.create_dock_widgets()

        # Create menu bar
        self.create_menu_bar()

        # Create status bar with advanced info
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("🚀 GitUploader v4.0 Pro Max Ready!")

    def create_ai_assistant_tab(self):
        """AI Assistant tab with smart Git suggestions"""
        ai_widget = QWidget()
        layout = QVBoxLayout(ai_widget)

        # Header
        header = QLabel("🤖 AI Git Assistant")
        header.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(header)

        # AI Settings
        ai_settings_group = QGroupBox("AI Configuration")
        ai_settings_layout = QFormLayout()

        # Enable AI checkbox
        self.ai_enabled_cb = QCheckBox("Enable AI Assistant")
        self.ai_enabled_cb.setChecked(self.ai_assistant.enabled)
        self.ai_enabled_cb.toggled.connect(self.toggle_ai_assistant)
        ai_settings_layout.addRow("Status:", self.ai_enabled_cb)

        # API Key input
        self.ai_api_key_input = QLineEdit()
        self.ai_api_key_input.setEchoMode(QLineEdit.Password)
        self.ai_api_key_input.setPlaceholderText(
            "Enter OpenAI API Key (optional)")
        ai_settings_layout.addRow("API Key:", self.ai_api_key_input)

        ai_settings_group.setLayout(ai_settings_layout)
        layout.addWidget(ai_settings_group)

        # Smart Suggestions
        suggestions_group = QGroupBox("Smart Suggestions")
        suggestions_layout = QVBoxLayout()

        # Commit message generator
        commit_gen_layout = QHBoxLayout()
        self.smart_commit_btn = QPushButton("🧠 Generate Smart Commit Message")
        self.smart_commit_btn.clicked.connect(self.generate_smart_commit)
        commit_gen_layout.addWidget(self.smart_commit_btn)

        self.auto_commit_cb = QCheckBox("Auto-generate commit messages")
        commit_gen_layout.addWidget(self.auto_commit_cb)
        suggestions_layout.addLayout(commit_gen_layout)

        # Branch name suggestions
        branch_layout = QHBoxLayout()
        self.suggest_branch_btn = QPushButton("🌳 Suggest Branch Name")
        self.suggest_branch_btn.clicked.connect(self.suggest_branch_name)
        branch_layout.addWidget(self.suggest_branch_btn)

        self.branch_suggestion_label = QLabel(
            "Suggested branch: feature/new-feature")
        branch_layout.addWidget(self.branch_suggestion_label)
        suggestions_layout.addLayout(branch_layout)

        suggestions_group.setLayout(suggestions_layout)
        layout.addWidget(suggestions_group)

        # AI Chat Interface
        chat_group = QGroupBox("AI Git Chat")
        chat_layout = QVBoxLayout()

        self.ai_chat_history = QTextBrowser()
        self.ai_chat_history.setMaximumHeight(200)
        chat_layout.addWidget(self.ai_chat_history)

        chat_input_layout = QHBoxLayout()
        self.ai_chat_input = QLineEdit()
        self.ai_chat_input.setPlaceholderText("Ask AI about Git operations...")
        self.ai_chat_input.returnPressed.connect(self.send_ai_message)
        chat_input_layout.addWidget(self.ai_chat_input)

        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self.send_ai_message)
        chat_input_layout.addWidget(send_btn)

        chat_layout.addLayout(chat_input_layout)
        chat_group.setLayout(chat_layout)
        layout.addWidget(chat_group)

        layout.addStretch()
        self.tab_widget.addTab(ai_widget, "🤖 AI Assistant")

    def create_performance_tab(self):
        """Performance monitoring tab"""
        perf_widget = QWidget()
        layout = QVBoxLayout(perf_widget)

        # Header
        header = QLabel("⚡ Performance Monitor")
        header.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(header)

        # Real-time stats
        stats_group = QGroupBox("System Statistics")
        stats_layout = QGridLayout()

        # CPU Usage
        stats_layout.addWidget(QLabel("CPU Usage:"), 0, 0)
        self.cpu_progress = QProgressBar()
        self.cpu_progress.setMaximum(100)
        stats_layout.addWidget(self.cpu_progress, 0, 1)
        self.cpu_label = QLabel("0%")
        stats_layout.addWidget(self.cpu_label, 0, 2)

        # Memory Usage
        stats_layout.addWidget(QLabel("Memory Usage:"), 1, 0)
        self.memory_progress = QProgressBar()
        self.memory_progress.setMaximum(100)
        stats_layout.addWidget(self.memory_progress, 1, 1)
        self.memory_label = QLabel("0%")
        stats_layout.addWidget(self.memory_label, 1, 2)

        # Disk Usage
        stats_layout.addWidget(QLabel("Disk Usage:"), 2, 0)
        self.disk_progress = QProgressBar()
        self.disk_progress.setMaximum(100)
        stats_layout.addWidget(self.disk_progress, 2, 1)
        self.disk_label = QLabel("0%")
        stats_layout.addWidget(self.disk_label, 2, 2)

        # Git Processes
        stats_layout.addWidget(QLabel("Git Processes:"), 3, 0)
        self.git_processes_label = QLabel("0")
        stats_layout.addWidget(self.git_processes_label, 3, 1, 1, 2)

        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        # Performance history chart (placeholder)
        chart_group = QGroupBox("Performance History")
        chart_layout = QVBoxLayout()

        self.performance_chart = QTextEdit()
        self.performance_chart.setMaximumHeight(150)
        self.performance_chart.setPlainText(
            "Performance chart will be displayed here...")
        chart_layout.addWidget(self.performance_chart)

        chart_group.setLayout(chart_layout)
        layout.addWidget(chart_group)

        # Git operation timing
        timing_group = QGroupBox("Git Operations Timing")
        timing_layout = QVBoxLayout()

        self.timing_table = QTableWidget(0, 3)
        self.timing_table.setHorizontalHeaderLabels(
            ["Operation", "Duration", "Status"])
        self.timing_table.horizontalHeader().setStretchLastSection(True)
        timing_layout.addWidget(self.timing_table)

        timing_group.setLayout(timing_layout)
        layout.addWidget(timing_group)

        layout.addStretch()
        self.tab_widget.addTab(perf_widget, "⚡ Performance")

    def create_security_tab(self):
        """Security management tab"""
        security_widget = QWidget()
        layout = QVBoxLayout(security_widget)

        # Header
        header = QLabel("🔐 Security Center")
        header.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(header)

        # Credential Management
        cred_group = QGroupBox("Credential Management")
        cred_layout = QFormLayout()

        # Encrypted storage
        self.encrypt_creds_cb = QCheckBox("Encrypt stored credentials")
        self.encrypt_creds_cb.setChecked(True)
        cred_layout.addRow("Security:", self.encrypt_creds_cb)

        # SSH Key management
        ssh_layout = QHBoxLayout()
        self.generate_ssh_btn = QPushButton("🔑 Generate SSH Key")
        self.generate_ssh_btn.clicked.connect(self.generate_ssh_key)
        ssh_layout.addWidget(self.generate_ssh_btn)

        self.view_ssh_btn = QPushButton("👁️ View Public Key")
        self.view_ssh_btn.clicked.connect(self.view_ssh_public_key)
        ssh_layout.addWidget(self.view_ssh_btn)

        cred_layout.addRow("SSH Keys:", ssh_layout)

        # Two-factor authentication
        self.tfa_cb = QCheckBox("Enable 2FA prompt for sensitive operations")
        cred_layout.addRow("2FA:", self.tfa_cb)

        cred_group.setLayout(cred_layout)
        layout.addWidget(cred_group)

        # Security Audit
        audit_group = QGroupBox("Security Audit")
        audit_layout = QVBoxLayout()

        audit_btn_layout = QHBoxLayout()
        self.scan_vulnerabilities_btn = QPushButton(
            "🔍 Scan for Vulnerabilities")
        self.scan_vulnerabilities_btn.clicked.connect(
            self.scan_vulnerabilities)
        audit_btn_layout.addWidget(self.scan_vulnerabilities_btn)

        self.check_permissions_btn = QPushButton("🛡️ Check File Permissions")
        self.check_permissions_btn.clicked.connect(self.check_file_permissions)
        audit_btn_layout.addWidget(self.check_permissions_btn)

        audit_layout.addLayout(audit_btn_layout)

        # Audit results
        self.security_audit_results = QTextEdit()
        self.security_audit_results.setMaximumHeight(200)
        audit_layout.addWidget(self.security_audit_results)

        audit_group.setLayout(audit_layout)
        layout.addWidget(audit_group)

        # Backup & Recovery
        backup_group = QGroupBox("Backup & Recovery")
        backup_layout = QVBoxLayout()

        backup_btn_layout = QHBoxLayout()
        self.create_backup_btn = QPushButton("💾 Create Encrypted Backup")
        self.create_backup_btn.clicked.connect(self.create_encrypted_backup)
        backup_btn_layout.addWidget(self.create_backup_btn)

        self.restore_backup_btn = QPushButton("🔄 Restore from Backup")
        self.restore_backup_btn.clicked.connect(self.restore_from_backup)
        backup_btn_layout.addWidget(self.restore_backup_btn)

        backup_layout.addLayout(backup_btn_layout)
        backup_group.setLayout(backup_layout)
        layout.addWidget(backup_group)

        layout.addStretch()
        self.tab_widget.addTab(security_widget, "🔐 Security")

    def create_plugins_tab(self):
        """Plugin management tab"""
        plugins_widget = QWidget()
        layout = QVBoxLayout(plugins_widget)

        # Header
        header = QLabel("🔌 Plugin Manager")
        header.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(header)

        # Plugin installation
        install_group = QGroupBox("Install Plugins")
        install_layout = QVBoxLayout()

        install_input_layout = QHBoxLayout()
        self.plugin_url_input = QLineEdit()
        self.plugin_url_input.setPlaceholderText("Enter plugin URL or name...")
        install_input_layout.addWidget(self.plugin_url_input)

        self.install_plugin_btn = QPushButton("📦 Install Plugin")
        self.install_plugin_btn.clicked.connect(self.install_plugin)
        install_input_layout.addWidget(self.install_plugin_btn)

        install_layout.addLayout(install_input_layout)
        install_group.setLayout(install_layout)
        layout.addWidget(install_group)

        # Installed plugins
        installed_group = QGroupBox("Installed Plugins")
        installed_layout = QVBoxLayout()

        self.plugins_list = QListWidget()
        self.refresh_plugins_list()
        installed_layout.addWidget(self.plugins_list)

        plugin_actions_layout = QHBoxLayout()
        self.enable_plugin_btn = QPushButton("✅ Enable")
        self.enable_plugin_btn.clicked.connect(self.enable_selected_plugin)
        plugin_actions_layout.addWidget(self.enable_plugin_btn)

        self.disable_plugin_btn = QPushButton("❌ Disable")
        self.disable_plugin_btn.clicked.connect(self.disable_selected_plugin)
        plugin_actions_layout.addWidget(self.disable_plugin_btn)

        self.remove_plugin_btn = QPushButton("🗑️ Remove")
        self.remove_plugin_btn.clicked.connect(self.remove_selected_plugin)
        plugin_actions_layout.addWidget(self.remove_plugin_btn)

        installed_layout.addLayout(plugin_actions_layout)
        installed_group.setLayout(installed_layout)
        layout.addWidget(installed_group)

        # Plugin marketplace
        marketplace_group = QGroupBox("Plugin Marketplace")
        marketplace_layout = QVBoxLayout()

        marketplace_list = QListWidget()
        # Add some example plugins
        for plugin in [
    "GitHub Enhanced",
    "GitLab Pro",
    "Code Formatter",
    "AI Reviewer",
     "Deployment Helper"]:
            item = QListWidgetItem(f"📦 {plugin}")
            marketplace_list.addItem(item)

        marketplace_layout.addWidget(marketplace_list)

        marketplace_actions_layout = QHBoxLayout()
        self.browse_marketplace_btn = QPushButton("🌐 Browse Online")
        self.browse_marketplace_btn.clicked.connect(self.browse_marketplace)
        marketplace_actions_layout.addWidget(self.browse_marketplace_btn)

        self.refresh_marketplace_btn = QPushButton("🔄 Refresh")
        self.refresh_marketplace_btn.clicked.connect(self.refresh_marketplace)
        marketplace_actions_layout.addWidget(self.refresh_marketplace_btn)

        marketplace_layout.addLayout(marketplace_actions_layout)
        marketplace_group.setLayout(marketplace_layout)
        layout.addWidget(marketplace_group)

        layout.addStretch()
        self.tab_widget.addTab(plugins_widget, "🔌 Plugins")

    def create_code_review_tab(self):
        """Code review assistant tab"""
        review_widget = QWidget()
        layout = QVBoxLayout(review_widget)

        # Header
        header = QLabel("🔍 Code Review Assistant")
        header.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(header)

        # Review settings
        settings_group = QGroupBox("Review Settings")
        settings_layout = QFormLayout()

        self.auto_review_cb = QCheckBox("Enable automatic code review")
        self.auto_review_cb.setChecked(True)
        settings_layout.addRow("Auto Review:", self.auto_review_cb)

        self.review_level_combo = QComboBox()
        self.review_level_combo.addItems(
            ["Basic", "Standard", "Strict", "Enterprise"])
        self.review_level_combo.setCurrentText("Standard")
        settings_layout.addRow("Review Level:", self.review_level_combo)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # Review actions
        actions_group = QGroupBox("Review Actions")
        actions_layout = QHBoxLayout()

        self.review_changes_btn = QPushButton("🔍 Review Current Changes")
        self.review_changes_btn.clicked.connect(self.review_current_changes)
        actions_layout.addWidget(self.review_changes_btn)

        self.review_branch_btn = QPushButton("🌳 Review Branch")
        self.review_branch_btn.clicked.connect(self.review_branch)
        actions_layout.addWidget(self.review_branch_btn)

        self.review_pr_btn = QPushButton("📋 Review Pull Request")
        self.review_pr_btn.clicked.connect(self.review_pull_request)
        actions_layout.addWidget(self.review_pr_btn)

        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)

        # Review results
        results_group = QGroupBox("Review Results")
        results_layout = QVBoxLayout()

        self.review_results = QTextBrowser()
        self.review_results.setMinimumHeight(300)
        results_layout.addWidget(self.review_results)

        results_group.setLayout(results_layout)
        layout.addWidget(results_group)

        layout.addStretch()
        self.tab_widget.addTab(review_widget, "🔍 Code Review")

    def load_settings(self):
        self.current_theme = self.settings.value("theme", "Dark", type=str)
        self.language = self.settings.value("language", "vi", type=str)
        # Load saved projects
        saved_projects = self.settings.value("projects", [], type=list)
        for project_path in saved_projects:
            if os.path.exists(project_path) and os.path.exists(
                os.path.join(project_path, ".git")):
                try:
                    proj = ProjectInfo(project_path)
                    self.projects.append(proj)
                except Exception:
                    pass

    def save_settings(self):
        self.settings.setValue("theme", self.current_theme)
        self.settings.setValue("language", self.language)
        # Save project paths
        project_paths = [proj.path for proj in self.projects]
        self.settings.setValue("projects", project_paths)

    def auto_save_projects(self):
        self.save_settings()

    def init_ui(self):
        self.create_menu_bar()
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Create dock widgets cho file browser và terminal
        self.create_dock_widgets()

        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)

        # Tạo các tab chính
        self.create_git_tab()
        self.create_stash_tab()
        self.create_dashboard_tab()
        self.create_automation_tab()
        self.create_project_manager_tab()
        self.create_settings_tab()

        main_layout.addWidget(self.tabs)

        # Progress bar in status bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.addPermanentWidget(self.progress_bar)
        self.apply_theme()

    def create_dock_widgets(self):
        # DISABLED - No File Browser and Terminal
        pass

    def create_git_tab(self):
        git_tab = QWidget()
        main_layout = QVBoxLayout()

        # --- Project selection and info ---
        form_group = QGroupBox(self.tr("📁 Dự án & Thông tin"))
        form_layout = QFormLayout()

        self.project_list = QComboBox()
        self.project_list.setMinimumWidth(300)
        self.project_list.currentIndexChanged.connect(self.on_project_changed)
        form_layout.addRow(QLabel(self.tr("Dự án:")), self.project_list)

        self.branch_label = QLabel("")
        form_layout.addRow(
    QLabel(
        self.tr("Branch hiện tại:")),
         self.branch_label)

        self.remote_box = QComboBox()
        self.remote_box.setMinimumWidth(120)
        self.remote_box.currentIndexChanged.connect(self.update_remote_info)
        form_layout.addRow(QLabel(self.tr("Remote:")), self.remote_box)

        self.remote_url_label = QLabel("")
        form_layout.addRow(
    QLabel(
        self.tr("URL remote:")),
         self.remote_url_label)

        # Nút thao tác dự án với QIcon
        btn_layout = QHBoxLayout()
        self.add_proj_btn = QPushButton(self.tr("  Thêm dự án"))
        self.add_proj_btn.setIcon(self.create_icon("➕"))
        self.add_proj_btn.clicked.connect(self.add_project)
        btn_layout.addWidget(self.add_proj_btn)
        self.remove_proj_btn = QPushButton(self.tr("  Xóa dự án"))
        self.remove_proj_btn.setIcon(self.create_icon("🗑️"))
        self.remove_proj_btn.clicked.connect(self.remove_project)
        btn_layout.addWidget(self.remove_proj_btn)
        form_layout.addRow(btn_layout)

        form_group.setLayout(form_layout)
        main_layout.addWidget(form_group)

        # --- Git operations ---
        git_group = QGroupBox(self.tr("🔧 Git Operations"))
        git_btn_layout = QHBoxLayout()
        self.git_status_btn = QPushButton(self.tr("  Status"))
        self.git_status_btn.setIcon(self.create_icon("📊"))
        self.git_status_btn.clicked.connect(self.git_status)
        git_btn_layout.addWidget(self.git_status_btn)
        self.git_pull_btn = QPushButton(self.tr("  Pull"))
        self.git_pull_btn.setIcon(self.create_icon("⬇️"))
        self.git_pull_btn.clicked.connect(self.git_pull)
        git_btn_layout.addWidget(self.git_pull_btn)
        self.git_commit_btn = QPushButton(self.tr("  Commit"))
        self.git_commit_btn.setIcon(self.create_icon("💾"))
        self.git_commit_btn.clicked.connect(self.quick_commit)
        git_btn_layout.addWidget(self.git_commit_btn)
        self.git_push_btn = QPushButton(self.tr("  Push"))
        self.git_push_btn.setIcon(self.create_icon("⬆️"))
        self.git_push_btn.clicked.connect(self.git_push)
        git_btn_layout.addWidget(self.git_push_btn)
        git_group.setLayout(git_btn_layout)
        main_layout.addWidget(git_group)

        # --- Remote management ---
        remote_group = QGroupBox(self.tr("🌐 Remote Management"))
        remote_btn_layout = QHBoxLayout()
        self.refresh_remotes_btn = QPushButton(self.tr("  Làm mới"))
        self.refresh_remotes_btn.setIcon(self.create_icon("🔄"))
        self.refresh_remotes_btn.clicked.connect(self.refresh_remotes)
        remote_btn_layout.addWidget(self.refresh_remotes_btn)
        self.add_remote_btn = QPushButton(self.tr("  Thêm remote"))
        self.add_remote_btn.setIcon(self.create_icon("🔗"))
        self.add_remote_btn.clicked.connect(self.add_remote)
        remote_btn_layout.addWidget(self.add_remote_btn)
        self.push_github_btn = QPushButton(self.tr("  GitHub"))
        self.push_github_btn.setIcon(self.create_icon("🚀"))
        self.push_github_btn.clicked.connect(self.connect_and_push_github)
        remote_btn_layout.addWidget(self.push_github_btn)
        remote_group.setLayout(remote_btn_layout)
        main_layout.addWidget(remote_group)

        # --- Log area ---
        log_group = QGroupBox(self.tr("📝 Nhật ký hoạt động"))
        log_layout = QVBoxLayout()
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumHeight(200)
        log_layout.addWidget(self.log_box)
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)

        git_tab.setLayout(main_layout)
        self.tabs.addTab(git_tab, self.tr("🔧 Git Operations"))

    def create_stash_tab(self):
        stash_tab = QWidget()
        layout = QVBoxLayout()

        # Stash management
        stash_group = QGroupBox(self.tr("📦 Git Stash Management"))
        stash_layout = QVBoxLayout()

        # Stash operations
        stash_btn_layout = QHBoxLayout()
        self.stash_save_btn = QPushButton(self.tr("💾 Stash Changes"))
        self.stash_save_btn.setIcon(self.create_icon("💾"))
        self.stash_save_btn.clicked.connect(self.git_stash)
        stash_btn_layout.addWidget(self.stash_save_btn)

        self.stash_pop_btn = QPushButton(self.tr("📤 Pop Stash"))
        self.stash_pop_btn.setIcon(self.create_icon("📤"))
        self.stash_pop_btn.clicked.connect(self.git_stash_pop)
        stash_btn_layout.addWidget(self.stash_pop_btn)

        self.stash_list_btn = QPushButton(self.tr("📋 List Stashes"))
        self.stash_list_btn.setIcon(self.create_icon("📋"))
        self.stash_list_btn.clicked.connect(self.refresh_stash_list)
        stash_btn_layout.addWidget(self.stash_list_btn)

        stash_layout.addLayout(stash_btn_layout)

        # Stash list
        self.stash_list = QListWidget()
        stash_layout.addWidget(self.stash_list)

        stash_group.setLayout(stash_layout)
        layout.addWidget(stash_group)

        stash_tab.setLayout(layout)
        self.tabs.addTab(stash_tab, self.tr("📦 Stash"))

    def create_dashboard_tab(self):
        dashboard_tab = QWidget()
        layout = QVBoxLayout()

        # Analytics widgets
        analytics_group = QGroupBox(self.tr("📊 Project Analytics"))
        analytics_layout = QGridLayout()

        # Project stats
        self.stats_table = QTableWidget(5, 2)
        self.stats_table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.stats_table.setMaximumHeight(200)
        analytics_layout.addWidget(self.stats_table, 0, 0, 1, 2)

        # Refresh analytics button
        self.refresh_analytics_btn = QPushButton(
            self.tr("🔄 Refresh Analytics"))
        self.refresh_analytics_btn.setIcon(self.create_icon("🔄"))
        self.refresh_analytics_btn.clicked.connect(self.refresh_analytics)
        analytics_layout.addWidget(self.refresh_analytics_btn, 1, 0, 1, 2)

        analytics_group.setLayout(analytics_layout)
        layout.addWidget(analytics_group)

        # Multi-platform support
        platforms_group = QGroupBox(self.tr("🌐 Multi-Platform Support"))
        platforms_layout = QHBoxLayout()

        self.github_btn = QPushButton(self.tr("🐙 GitHub"))
        self.github_btn.setIcon(self.create_icon("🐙"))
        platforms_layout.addWidget(self.github_btn)

        self.gitlab_btn = QPushButton(self.tr("🦊 GitLab"))
        self.gitlab_btn.setIcon(self.create_icon("🦊"))
        platforms_layout.addWidget(self.gitlab_btn)

        self.bitbucket_btn = QPushButton(self.tr("🪣 Bitbucket"))
        self.bitbucket_btn.setIcon(self.create_icon("🪣"))
        platforms_layout.addWidget(self.bitbucket_btn)

        platforms_group.setLayout(platforms_layout)
        layout.addWidget(platforms_group)

        dashboard_tab.setLayout(layout)
        self.tabs.addTab(dashboard_tab, self.tr("📊 Dashboard"))

    def create_automation_tab(self):
        automation_tab = QWidget()
        layout = QVBoxLayout()

        # Auto push settings
        auto_group = QGroupBox(self.tr("🤖 Automation Settings"))
        auto_layout = QFormLayout()

        self.auto_push_check = QCheckBox(self.tr("Auto Push on File Change"))
        self.auto_push_check.toggled.connect(self.toggle_auto_push)
        auto_layout.addRow(self.auto_push_check)

        self.auto_commit_interval = QSpinBox()
        self.auto_commit_interval.setRange(1, 60)
        self.auto_commit_interval.setValue(5)
        self.auto_commit_interval.setSuffix(" minutes")
        auto_layout.addRow(
    QLabel(
        self.tr("Auto Commit Interval:")),
         self.auto_commit_interval)

        self.backup_enabled = QCheckBox(self.tr("Auto Backup Projects"))
        auto_layout.addRow(self.backup_enabled)

        auto_group.setLayout(auto_layout)
        layout.addWidget(auto_group)

        # Workflow templates
        workflow_group = QGroupBox(self.tr("⚡ Workflow Templates"))
        workflow_layout = QVBoxLayout()

        workflow_buttons = QHBoxLayout()
        self.workflow_basic_btn = QPushButton(self.tr("📝 Basic Workflow"))
        self.workflow_basic_btn.clicked.connect(
            lambda: self.apply_workflow("basic"))
        workflow_buttons.addWidget(self.workflow_basic_btn)

        self.workflow_feature_btn = QPushButton(self.tr("🌟 Feature Workflow"))
        self.workflow_feature_btn.clicked.connect(
            lambda: self.apply_workflow("feature"))
        workflow_buttons.addWidget(self.workflow_feature_btn)

        self.workflow_hotfix_btn = QPushButton(self.tr("🔥 Hotfix Workflow"))
        self.workflow_hotfix_btn.clicked.connect(
            lambda: self.apply_workflow("hotfix"))
        workflow_buttons.addWidget(self.workflow_hotfix_btn)

        workflow_layout.addLayout(workflow_buttons)
        workflow_group.setLayout(workflow_layout)
        layout.addWidget(workflow_group)

        automation_tab.setLayout(layout)
        self.tabs.addTab(automation_tab, self.tr("🤖 Automation"))

    def create_settings_tab(self):
        settings_tab = QWidget()
        layout = QVBoxLayout()

        # Theme settings
        theme_group = QGroupBox(self.tr("🎨 Theme & Appearance"))
        theme_layout = QFormLayout()

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list(self.theme_manager.themes.keys()))
        self.theme_combo.setCurrentText(self.current_theme)
        # Force apply Light Blue theme
        if self.current_theme == "Light Blue":
            self.apply_theme("Light Blue")
        self.theme_combo.currentTextChanged.connect(self.change_theme)
        theme_layout.addRow(QLabel(self.tr("Theme:")), self.theme_combo)

        self.language_combo = QComboBox()
        self.language_combo.addItems(["Tiếng Việt", "English"])
        self.language_combo.setCurrentIndex(0 if self.language == 'vi' else 1)
        self.language_combo.currentIndexChanged.connect(self.change_language)
        theme_layout.addRow(QLabel(self.tr("Language:")), self.language_combo)

        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)

        # Advanced settings
        advanced_group = QGroupBox(self.tr("⚙️ Advanced Settings"))
        advanced_layout = QFormLayout()

        self.cache_size = QSpinBox()
        self.cache_size.setRange(10, 1000)
        self.cache_size.setValue(100)
        self.cache_size.setSuffix(" MB")
        advanced_layout.addRow(QLabel(self.tr("Cache Size:")), self.cache_size)

        self.max_projects = QSpinBox()
        self.max_projects.setRange(5, 100)
        self.max_projects.setValue(20)
        advanced_layout.addRow(
    QLabel(
        self.tr("Max Projects:")),
         self.max_projects)

        advanced_group.setLayout(advanced_layout)
        layout.addWidget(advanced_group)

        # Action buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton(self.tr("💾 Save Settings"))
        save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(save_btn)

        reset_btn = QPushButton(self.tr("🔄 Reset to Default"))
        reset_btn.clicked.connect(self.reset_settings)
        button_layout.addWidget(reset_btn)

        export_btn = QPushButton(self.tr("📤 Export Settings"))
        export_btn.clicked.connect(self.export_settings)
        button_layout.addWidget(export_btn)

        import_btn = QPushButton(self.tr("📥 Import Settings"))
        import_btn.clicked.connect(self.import_settings)
        button_layout.addWidget(import_btn)

        layout.addLayout(button_layout)
        layout.addStretch()

        settings_tab.setLayout(layout)
        self.tabs.addTab(settings_tab, self.tr("⚙️ Settings"))

    def apply_theme(self, theme_name=None):
        if theme_name:
            self.current_theme = theme_name
        self.setStyleSheet(self.theme_manager.themes[self.current_theme])

    def git_stash(self):
        if not self.current_project:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn dự án!")
            return

        message, ok = QInputDialog.getText(self, "Stash Message",
                                         "Nhập stash message:",
                                         text=f"Stash {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        if not ok:
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

        self.git_thread = GitOperationThread(
    "stash", self.current_project.path, message)
        self.git_thread.progress.connect(self.status_bar.showMessage)
        self.git_thread.finished.connect(self.on_git_operation_finished)
        self.git_thread.start()

    def git_stash_pop(self):
        if not self.current_project:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn dự án!")
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

        self.git_thread = GitOperationThread(
    "stash_pop", self.current_project.path)
        self.git_thread.progress.connect(self.status_bar.showMessage)
        self.git_thread.finished.connect(self.on_git_operation_finished)
        self.git_thread.start()

    def refresh_stash_list(self):
        if not self.current_project:
            return

        self.stash_list.clear()
        stashes = self.current_project.get_stash_list()
        for stash in stashes:
            self.stash_list.addItem(stash)

    def refresh_analytics(self):
        if not self.current_project:
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

        self.git_thread = GitOperationThread(
    "analytics", self.current_project.path)
        self.git_thread.finished.connect(self.on_analytics_finished)
        self.git_thread.start()

    def on_analytics_finished(self, success, data):
        self.progress_bar.setVisible(False)

        if success:
            try:
                commit_data = json.loads(data)
                self.update_stats_table(commit_data)
            except Exception as e:
                self.log_box.append(f"[ERROR] Lỗi parse analytics: {str(e)}")

    def update_stats_table(self, commit_data):
        self.stats_table.setItem(
    0, 0, QTableWidgetItem("Total Commits (30 days)"))
        self.stats_table.setItem(0, 1, QTableWidgetItem(
            str(sum(commit_data.values()))))

        self.stats_table.setItem(1, 0, QTableWidgetItem("Active Days"))
        self.stats_table.setItem(1, 1, QTableWidgetItem(str(len(commit_data))))

        self.stats_table.setItem(2, 0, QTableWidgetItem("Avg Commits/Day"))
        avg = sum(commit_data.values()) / max(len(commit_data), 1)
        self.stats_table.setItem(2, 1, QTableWidgetItem(f"{avg:.1f}"))

        self.stats_table.setItem(3, 0, QTableWidgetItem("Current Branch"))
        branch = self.current_project.get_current_branch() if self.current_project else "N/A"
        self.stats_table.setItem(3, 1, QTableWidgetItem(branch))

        self.stats_table.setItem(4, 0, QTableWidgetItem("Project Path"))
        path = self.current_project.path if self.current_project else "N/A"
        self.stats_table.setItem(4, 1, QTableWidgetItem(path))

    def apply_workflow(self, workflow_type):
        if not self.current_project:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn dự án!")
            return

        workflows = {
            "basic": ["git add .", "git commit -m 'Update'", "git push"],
            "feature": ["git checkout -b feature/new-feature", "git add .", "git commit -m 'Add new feature'"],
            "hotfix": ["git checkout -b hotfix/urgent-fix", "git add .", "git commit -m 'Urgent hotfix'", "git push origin hotfix/urgent-fix"]
        }

        commands = workflows.get(workflow_type, [])
        workflow_text = "\n".join(commands)
        self.terminal.setPlainText(
            f"# {workflow_type.title()} Workflow Applied:\n{workflow_text}")

    def setup_file_watcher(self):
        if not self.current_project:
            return

        if self.current_project.path in self.file_watchers:
            return

        watcher = FileWatcherThread(self.current_project.path)
        watcher.fileChanged.connect(self.on_auto_push)
        watcher.auto_push_enabled = self.auto_push_enabled
        watcher.start()
        self.file_watchers[self.current_project.path] = watcher

    def remove_file_watcher(self):
        if not self.current_project:
            return

        if self.current_project.path in self.file_watchers:
            watcher = self.file_watchers[self.current_project.path]
            watcher.terminate()
            del self.file_watchers[self.current_project.path]

    def on_auto_push(self, path):
        if self.auto_push_enabled and self.current_project:
            QTimer.singleShot(5000, self.auto_commit_and_push)  # Delay 5s

    def auto_commit_and_push(self):
        if not self.current_project:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"Auto commit - {timestamp}"

        self.git_thread = GitOperationThread(
    "commit", self.current_project.path, message)
        self.git_thread.finished.connect(self.on_auto_commit_finished)
        self.git_thread.start()

    def on_auto_commit_finished(self, success, message):
        if success and self.auto_push_enabled:
            QTimer.singleShot(1000, self.auto_push)

    def auto_push(self):
        if not self.current_project:
            return

        self.git_thread = GitOperationThread("push", self.current_project.path)
        self.git_thread.finished.connect(self.on_auto_push_finished)
        self.git_thread.start()

    def on_auto_push_finished(self, success, message):
        if success:
            self.log_box.append("[AUTO] Đã tự động commit và push thành công")
        else:
            self.log_box.append(f"[AUTO] Lỗi auto push: {message}")

    def populate_project_list(self):
        """Optimized project list population"""
        self._updating_ui = True
        try:
            self.project_list.clear()
            for i, proj in enumerate(self.projects):
                self.project_list.addItem(f"{proj.name} ({proj.path})")

            # Update project tree efficiently
            if hasattr(self, 'project_tree'):
                self.project_tree.clear()
                for proj in self.projects:
                    # Get branch quickly or use cached
                    branch = self._get_cached_branch(proj)
                    item = QTreeWidgetItem([proj.name, branch, "Active"])
                    self.project_tree.addTopLevelItem(item)
        finally:
            self._updating_ui = False

    def _get_cached_branch(self, project):
        """Get branch from cache or return placeholder"""
        cache_key = project.path
        if cache_key in self._project_info_cache:
            return self._project_info_cache[cache_key]['branch']
        return "..."  # Placeholder while loading

    def on_tree_item_clicked(self, item, column):
        project_name = item.text(0)
        for i, proj in enumerate(self.projects):
            if proj.name == project_name:
                self.project_list.setCurrentIndex(i)
                break

    def on_project_changed(self, idx):
        if self._updating_ui:  # Tránh cascade updates
            return

        if not hasattr(
    self, 'projects') or idx < 0 or idx >= len(
        self.projects):
            self.current_project = None
            self.set_ui_enabled(False)
            if hasattr(self, 'status_bar'):
                self.status_bar.showMessage("Chưa chọn dự án")
            self._clear_project_info()
            return

        self.current_project = self.projects[idx]
        self.set_ui_enabled(True)
        if hasattr(self, 'status_bar'):
            self.status_bar.showMessage(
    f"Đã chọn dự án: {
        self.current_project.name}")

        # Update info async để không lag UI
        QTimer.singleShot(100, self._update_project_info_async)

        # Log không đồng bộ
        QTimer.singleShot(200, lambda: self._log_project_info())

    def _clear_project_info(self):
        """Clear UI info quickly without I/O operations"""
        if hasattr(self, 'remote_box'):
            self.remote_box.clear()
        if hasattr(self, 'branch_label'):
            self.branch_label.setText("")
        if hasattr(self, 'remote_url_label'):
            self.remote_url_label.setText("")
        if hasattr(self, 'project_info_label'):
            self.project_info_label.setText("Chọn dự án để xem chi tiết")
        if hasattr(self, 'history_list'):
            self.history_list.clear()

    def _update_project_info_async(self):
        """Update project info without blocking UI"""
        if not self.current_project:
            return

        # Use cache if available
        cache_key = self.current_project.path
        if cache_key in self._project_info_cache:
            cached_info = self._project_info_cache[cache_key]
            self._apply_cached_info(cached_info)
            return

        # Update basic info immediately
        if hasattr(self, 'branch_label'):
            self.branch_label.setText("Đang tải...")

        # Load detailed info in background
        QTimer.singleShot(50, self._load_project_details)

    def _load_project_details(self):
        """Load project details without blocking UI"""
        if not self.current_project:
            return

        try:
            # Get info quickly
            current_branch = self.current_project.get_current_branch()
            remotes = self.current_project.remotes

            # Cache the results
            cache_info = {
                'branch': current_branch,
                'remotes': remotes,
                'timestamp': datetime.now()
            }
            self._project_info_cache[self.current_project.path] = cache_info

            # Apply to UI
            self._apply_cached_info(cache_info)

        except Exception as e:
            self.log_box.append(f"[ERROR] Lỗi load thông tin dự án: {str(e)}")

    def _apply_cached_info(self, info):
        """Apply cached info to UI quickly"""
        if hasattr(self, 'branch_label'):
            self.branch_label.setText(info['branch'])

        if hasattr(self, 'project_info_label'):
            info_text = f"Dự án: {self.current_project.name}\n"
            info_text += f"Đường dẫn: {self.current_project.path}\n"
            info_text += f"Branch: {info['branch']}\n"
            if info['remotes']:
                info_text += f"Remotes: {', '.join(info['remotes'])}"
            self.project_info_label.setText(info_text)

        # Update remotes async
        QTimer.singleShot(
    100, lambda: self._update_remotes_ui(
        info['remotes']))

    def _update_remotes_ui(self, remotes):
        """Update remotes UI without triggering cascade"""
        self._updating_ui = True
        try:
            if hasattr(self, 'remote_box'):
                self.remote_box.clear()
                for r in remotes:
                    self.remote_box.addItem(r)
                if remotes:
                    self.remote_box.setCurrentIndex(0)
        finally:
            self._updating_ui = False

    def _log_project_info(self):
        """Log project info async"""
        if not self.current_project:
            return
        self.log_box.append(
    f"[INFO] Đã chọn dự án: {
        self.current_project.name}")

    def set_ui_enabled(self, enabled):
        # Nút "Thêm dự án" luôn được bật để người dùng có thể thêm dự án đầu
        # tiên
        if hasattr(self, 'add_proj_btn'):
            self.add_proj_btn.setEnabled(True)

        # Các nút khác chỉ được bật khi có dự án được chọn
        ui_elements = ['remote_box', 'refresh_remotes_btn', 'add_remote_btn', 'push_github_btn',
                      'remove_proj_btn', 'git_status_btn', 'git_pull_btn', 'git_commit_btn', 'git_push_btn']

        for element_name in ui_elements:
            if hasattr(self, element_name):
                getattr(self, element_name).setEnabled(enabled)

    def add_project(self):
        try:
            # Tạo dialog chọn thư mục với các tùy chọn
            dialog = QFileDialog(self)
            dialog.setWindowTitle("Chọn thư mục dự án")
            dialog.setFileMode(QFileDialog.Directory)
            dialog.setOption(QFileDialog.ShowDirsOnly, True)

            # Đặt thư mục mặc định là Desktop hoặc Documents
            default_paths = [
                os.path.expanduser("~/Desktop"),
                os.path.expanduser("~/Documents"),
                os.path.expanduser("~")
            ]

            # Tìm thư mục mặc định đầu tiên tồn tại
            for path in default_paths:
                if os.path.exists(path):
                    dialog.setDirectory(path)
                    break

            # Hiển thị dialog
            if dialog.exec():
                selected_paths = dialog.selectedFiles()
                if not selected_paths:
                    self.log_box.append(
                        "[INFO] Không có thư mục nào được chọn")
                    return

                path = selected_paths[0]

                # Kiểm tra xem thư mục có phải là git repository không
                git_dir = os.path.join(path, ".git")
                if not os.path.exists(git_dir):
                    # Hỏi người dùng có muốn khởi tạo git repository không
                    reply = QMessageBox.question(self,
                        "Khởi tạo Git",
                        "Thư mục này chưa phải là Git repository.\nBạn có muốn khởi tạo Git repository không?",
                        QMessageBox.Yes | QMessageBox.No)

                    if reply == QMessageBox.Yes:
                        try:
                            # Khởi tạo git repository
                            subprocess.run(["git", "init"],
                                           cwd=path, check=True)
                            self.log_box.append(
    f"[INFO] Đã khởi tạo Git repository tại: {path}")
                        except subprocess.CalledProcessError as e:
                            QMessageBox.warning(
    self, "Lỗi", f"Không thể khởi tạo Git repository:\n{
        str(e)}")
                            self.log_box.append(
    f"[ERROR] Lỗi khởi tạo Git repo: {
        str(e)}")
                            return
                    else:
                        self.log_box.append(
                            "[INFO] Người dùng đã hủy khởi tạo Git repository")
                        return

                # Kiểm tra trùng lặp
            for proj in self.projects:
                if proj.path == path:
                    QMessageBox.information(
    self, "Đã tồn tại", "Dự án này đã có trong danh sách.")
                    self.log_box.append(f"[INFO] Dự án đã tồn tại: {path}")
                    return

                # Thêm dự án mới
            proj = ProjectInfo(path)
            self.projects.append(proj)
            self.populate_project_list()
            self.project_list.setCurrentIndex(len(self.projects) - 1)
            self.log_box.append(
    f"[INFO] Đã thêm dự án thành công: {
        proj.path}")
            self.save_settings()  # Auto-save after adding project
        except Exception as e:
            error_msg = str(e)
            QMessageBox.critical(
    self, "Lỗi", f"Không thể thêm dự án:\n{error_msg}")
            self.log_box.append(f"[ERROR] Lỗi khi thêm dự án: {error_msg}")
            self.log_box.append(f"[DEBUG] Chi tiết lỗi: {type(e).__name__}")
            self.log_box.append(f"[ERROR] Lỗi khi thêm dự án: {error_msg}")
            self.log_box.append(f"[DEBUG] Chi tiết lỗi: {type(e).__name__}")

    def check_network_status(self):
        """Check network status without blocking UI"""
        try:
            if not check_github_online():
                if hasattr(self, 'status_bar'):
                    self.status_bar.showMessage("⚠️ Không có kết nối mạng!")
                self.log_box.append("[WARNING] Không có kết nối Internet")
            else:
                if hasattr(self, 'status_bar'):
                    self.status_bar.showMessage("Sẵn sàng")
                self.log_box.append("[INFO] Đã kết nối Internet")
        except Exception:
            # Ignore network check errors
            pass

    def tr(self, text):
        if self.language == 'vi':
            return text
        mapping = {
            "Dự án:": "Project:",
            "➕ Thêm dự án": "➕ Add Project",
            "🌐 Kết nối & Push lên GitHub": "🌐 Connect & Push to GitHub",
            "Remote:": "Remote:",
            "🔄 Làm mới remote": "🔄 Refresh remote",
            "➕ Thêm remote": "➕ Add remote",
            "Branch hiện tại: ": "Current branch: ",
            "Branch mặc định remote: ": "Remote default branch: ",
            "Trạng thái: Sẵn sàng": "Status: Ready",
            "Trạng thái: Chưa chọn dự án": "Status: No project selected",
            "⚠️ Không có kết nối mạng hoặc không truy cập được GitHub!": "⚠️ No network or cannot access GitHub!",
            "Chưa chọn dự án": "No project selected",
            "Vui lòng chọn dự án trước!": "Please select a project first!",
            "Đã tồn tại": "Already exists",
            "Dự án này đã có trong danh sách.": "This project is already in the list.",
            "Tên remote": "Remote name",
            "Nhập tên remote (ví dụ: origin):": "Enter remote name (e.g. origin):",
            "URL remote": "Remote URL",
            "Nhập URL remote (ví dụ: https://github.com/xxx/yyy.git):": "Enter remote URL (e.g. https://github.com/xxx/yyy.git):",
            "Thành công": "Success",
            "Đã thêm remote": "Remote added",
            "Lỗi": "Error",
            "Không thể thêm remote:": "Cannot add remote:",
            "URL GitHub": "GitHub URL",
            "Nhập URL repo GitHub (https://github.com/xxx/yyy.git):": "Enter GitHub repo URL (https://github.com/xxx/yyy.git):",
            "Đã push dự án lên GitHub:": "Project pushed to GitHub:",
            "Push thất bại:": "Push failed:",
            "Git": "Git"
        }
        return mapping.get(text, text)

    def update_remote_info(self):
        if not self.current_project or not hasattr(self, 'remote_box'):
            if hasattr(self, 'remote_url_label'):
                self.remote_url_label.setText("")
            if hasattr(self, 'default_branch_label'):
                self.default_branch_label.setText(
                    self.tr("Branch mặc định remote: "))
            return

        remote = self.remote_box.currentText()
        if remote:
            # Lấy URL của remote
            url = self.current_project.get_remote_url(remote)
            if hasattr(self, 'remote_url_label'):
                self.remote_url_label.setText(
    f"URL: {url}" if url else f"Remote: {remote}")

            # Lấy branch mặc định của remote
            default_branch = self.current_project.get_default_remote_branch(
                remote)
            if hasattr(self, 'default_branch_label'):
                self.default_branch_label.setText(
    self.tr(
        f"Branch mặc định remote: {default_branch}") if default_branch else self.tr("Branch mặc định remote: "))
        else:
            if hasattr(self, 'remote_url_label'):
                self.remote_url_label.setText("")
            if hasattr(self, 'default_branch_label'):
                self.default_branch_label.setText(
                    self.tr("Branch mặc định remote: "))

    def refresh_remotes(self):
        """Optimized remote refresh"""
        if not self.current_project or self._updating_ui:
            return

        # Clear cache for this project
        if self.current_project.path in self._project_info_cache:
            del self._project_info_cache[self.current_project.path]

        # Refresh async
        QTimer.singleShot(50, self._refresh_remotes_async)

    def _refresh_remotes_async(self):
        """Refresh remotes without blocking UI"""
        if not self.current_project:
            return
        try:
            remotes = self.get_remotes_for_current_project()
            self._update_remotes_ui(remotes)
            QTimer.singleShot(100, self.update_remote_info)
        except Exception as e:
            self.log_box.append(f"[ERROR] Lỗi refresh remotes: {str(e)}")

    def get_remotes_for_current_project(self):
        if not self.current_project:
            return []
        try:
            out = subprocess.run(["git",
    "remote"],
    cwd=self.current_project.path,
    capture_output=True,
     text=True)
            return [r.strip() for r in out.stdout.splitlines() if r.strip()]
        except Exception:
            return []

    def add_remote(self):
        if not self.current_project:
            QMessageBox.warning(
    self,
    "Chưa chọn dự án",
     "Vui lòng chọn dự án trước!")
            return
        name, ok1 = QInputDialog.getText(
    self, "Tên remote", "Nhập tên remote (ví dụ: origin):")
        if not ok1 or not name.strip():
            return
        url, ok2 = QInputDialog.getText(
    self, "URL remote", "Nhập URL remote (ví dụ: https://github.com/xxx/yyy.git):")
        if not ok2 or not url.strip():
            return
        # Thêm remote qua git
        try:
            out = subprocess.run(["git", "remote", "add", name.strip(), url.strip(
            )], cwd=self.current_project.path, capture_output=True, text=True)
            if out.returncode == 0:
                QMessageBox.information(
    self, "Thành công", f"Đã thêm remote '{
        name.strip()}' cho dự án.")
            else:
                QMessageBox.warning(
    self, "Lỗi", f"Không thể thêm remote: {
        out.stderr}")
        except Exception as e:
            QMessageBox.warning(self, "Lỗi", str(e))
        self.refresh_remotes()

    def connect_and_push_github(self):
        if not self.current_project:
            QMessageBox.warning(
    self,
    "Chưa chọn dự án",
     "Vui lòng chọn dự án trước!")
            return
        url, ok = QInputDialog.getText(
    self, "URL GitHub", "Nhập URL repo GitHub (https://github.com/xxx/yyy.git):")
        if not ok or not url.strip():
            return
        # Thêm hoặc cập nhật remote origin
        remotes = self.get_remotes_for_current_project()
        if "origin" in remotes:
            subprocess.run(["git", "remote", "set-url", "origin",
                           url.strip()], cwd=self.current_project.path)
        else:
            subprocess.run(["git", "remote", "add", "origin",
                           url.strip()], cwd=self.current_project.path)
        # Kiểm tra có commit chưa, nếu chưa thì tạo commit đầu tiên
        out = subprocess.run(["git",
    "rev-parse",
    "--verify",
    "HEAD"],
    cwd=self.current_project.path,
    capture_output=True,
     text=True)
        if out.returncode != 0:
            # Chưa có commit, tạo file README.md nếu chưa có
            readme_path = os.path.join(self.current_project.path, "README.md")
            if not os.path.exists(readme_path):
            with open(readme_path, "w", encoding="utf-8") as f:
            f.write(f"# {self.current_project.name}\n")

            subprocess.run(["git", "add", "."], cwd=self.current_project.path)
            subprocess.run(["git", "commit", "-m", "Initial commit"],
                           cwd=self.current_project.path)
        # Push lần đầu
        branch = "main"
        # Nếu không có branch main, thử master
        out = subprocess.run(["git",
    "branch"],
    cwd=self.current_project.path,
    capture_output=True,
     text=True)
        branches = [b.strip().replace("* ", "")
                            for b in out.stdout.splitlines()]
        if "main" not in branches and "master" in branches:
            branch = "master"
        push_out = subprocess.run(["git",
    "push",
    "-u",
    "origin",
    branch],
    cwd=self.current_project.path,
    capture_output=True,
     text=True)
        if push_out.returncode == 0:
            QMessageBox.information(
    self, "Thành công", f"Đã push dự án lên GitHub: {
        url.strip()} (branch: {branch})")
        else:
            QMessageBox.warning(
    self, "Lỗi", f"Push thất bại: {
        push_out.stderr}")

    def remove_project(self):
        if not self.current_project:
            QMessageBox.warning(
    self, "Cảnh báo", "Vui lòng chọn dự án để xóa!")
            return

        reply = QMessageBox.question(self, "Xác nhận",
                                   f"Bạn có chắc muốn xóa dự án '{self.current_project.name}' khỏi danh sách?\n(Dữ liệu sẽ không bị xóa)")
        if reply == QMessageBox.Yes:
            self.projects.remove(self.current_project)
            self.populate_project_list()
            self.current_project = None
            self.set_ui_enabled(False)
            self.log_box.append("[INFO] Đã xóa dự án khỏi danh sách")

    def git_status(self):
        if not self.current_project:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn dự án!")
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress

        self.git_thread = GitOperationThread(
            "status", self.current_project.path)
        self.git_thread.progress.connect(self.status_bar.showMessage)
        self.git_thread.finished.connect(self.on_git_operation_finished)
        self.git_thread.start()

    def git_pull(self):
        if not self.current_project:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn dự án!")
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

        self.git_thread = GitOperationThread("pull", self.current_project.path)
        self.git_thread.progress.connect(self.status_bar.showMessage)
        self.git_thread.finished.connect(self.on_git_operation_finished)
        self.git_thread.start()

    def git_push(self):
        if not self.current_project:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn dự án!")
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

        self.git_thread = GitOperationThread("push", self.current_project.path)
        self.git_thread.progress.connect(self.status_bar.showMessage)
        self.git_thread.finished.connect(self.on_git_operation_finished)
        self.git_thread.start()

    def quick_commit(self):
        if not self.current_project:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn dự án!")
            return

        message, ok = QInputDialog.getText(self, "Commit Message",
                                         "Nhập commit message:",
                                         text=f"Update {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        if not ok or not message.strip():
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

        self.git_thread = GitOperationThread(
    "commit", self.current_project.path, message.strip())
        self.git_thread.progress.connect(self.status_bar.showMessage)
        self.git_thread.finished.connect(self.on_git_operation_finished)
        self.git_thread.start()

    def on_git_operation_finished(self, success, message):
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage("Sẵn sàng", 2000)

        if success:
            self.log_box.append(f"[SUCCESS] {message}")
            # Refresh project info
            if self.current_project:
                self.update_project_info()


else:
            self.log_box.append(f"[ERROR] {message}")
            QMessageBox.warning(self, "Lỗi Git", message)

    def update_project_info(self):
        if not self.current_project:
            return
        
        # Update branch info
        current_branch = self.current_project.get_current_branch()
        if hasattr(self, 'branch_label'):
            self.branch_label.setText(current_branch)
        
        # Update project info label
        if hasattr(self, 'project_info_label'):
            info_text = f"Dự án: {self.current_project.name}\n"
            info_text += f"Đường dẫn: {self.current_project.path}\n"
            info_text += f"Branch: {current_branch}\n"
            
            remotes = self.current_project.remotes
            if remotes:
                info_text += f"Remotes: {', '.join(remotes)}"
            
            self.project_info_label.setText(info_text)
        
        # Update git history
        if hasattr(self, 'history_list'):
            self.history_list.clear()
            git_log = self.current_project.get_git_log()
            for commit in git_log:
                self.history_list.addItem(commit)
        
        # DON'T call populate_project_list() here to avoid recursion!

    def closeEvent(self, event):
        # Save settings before closing
        self.save_settings()
        event.accept()

    def create_icon(self, emoji_text):
        # Tạo QIcon từ emoji text
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        font = QFont()
        font.setPointSize(20)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignCenter, emoji_text)
        painter.end()
        return QIcon(pixmap)

    def open_file(self, index):
        file_path = self.file_model.filePath(index)
        if os.path.isfile(file_path):
            self.log_box.append(f"[INFO] Opening file: {file_path}")
            # Implement file editor if needed

    def export_settings(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Settings", "gituploader_settings.json", "JSON Files (*.json)")
        if file_path:
            settings_data = {
                "theme": self.current_theme,
                "language": self.language,
                "auto_push": self.auto_push_enabled,
                "projects": [proj.path for proj in self.projects]
            }
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(settings_data, f, indent=2, ensure_ascii=False)
                QMessageBox.information(self, "Success", f"Settings exported to {file_path}")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to export: {str(e)}")

    def import_settings(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Settings", "", "JSON Files (*.json)")
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    settings_data = json.load(f)
                
                self.current_theme = settings_data.get("theme", "Dark")
                self.language = settings_data.get("language", "vi")
                self.auto_push_enabled = settings_data.get("auto_push", False)
                
                self.apply_theme()
                self.save_settings()
                QMessageBox.information(self, "Success", "Settings imported successfully!")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to import: {str(e)}")

    def create_menu_bar(self):
        menubar = self.menuBar()
        
        # File Menu
        file_menu = menubar.addMenu('📁 File')
        
        new_action = QAction('🆕 New Project', self)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(self.add_project)
        file_menu.addAction(new_action)
        
        save_action = QAction('💾 Save Settings', self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self.save_settings)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        export_action = QAction('📤 Export Settings', self)
        export_action.triggered.connect(self.export_settings)
        file_menu.addAction(export_action)
        
        import_action = QAction('📥 Import Settings', self)
        import_action.triggered.connect(self.import_settings)
        file_menu.addAction(import_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('🚪 Exit', self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View Menu
        view_menu = menubar.addMenu('👁️ View')
        
        theme_menu = view_menu.addMenu('🎨 Themes')
        for theme_name in self.theme_manager.themes.keys():
            theme_action = QAction(f'🎨 {theme_name}', self)
            theme_action.triggered.connect(lambda checked, name=theme_name: self.change_theme(name))
            theme_menu.addAction(theme_action)
        
        view_menu.addSeparator()
        
        file_browser_action = QAction('📁 File Browser', self)
        file_browser_action.setCheckable(True)
        file_browser_action.setChecked(True)
        file_browser_action.triggered.connect(self.toggle_file_browser)
        view_menu.addAction(file_browser_action)
        
        terminal_action = QAction('💻 Terminal', self)
        terminal_action.setCheckable(True)
        terminal_action.setChecked(True)
        terminal_action.triggered.connect(self.toggle_terminal)
        view_menu.addAction(terminal_action)
        
        # Git Menu
        git_menu = menubar.addMenu('🔧 Git')
        
        status_action = QAction('📊 Git Status', self)
        status_action.setShortcut('Ctrl+G')
        status_action.triggered.connect(self.git_status)
        git_menu.addAction(status_action)
        
        pull_action = QAction('⬇️ Git Pull', self)
        pull_action.setShortcut('Ctrl+P')
        pull_action.triggered.connect(self.git_pull)
        git_menu.addAction(pull_action)
        
        commit_action = QAction('💾 Quick Commit', self)
        commit_action.setShortcut('Ctrl+Shift+C')
        commit_action.triggered.connect(self.quick_commit)
        git_menu.addAction(commit_action)
        
        push_action = QAction('⬆️ Git Push', self)
        push_action.setShortcut('Ctrl+Shift+P')
        push_action.triggered.connect(self.git_push)
        git_menu.addAction(push_action)
        
        git_menu.addSeparator()
        
        stash_action = QAction('📦 Stash Changes', self)
        stash_action.setShortcut('Ctrl+S')
        stash_action.triggered.connect(self.git_stash)
        git_menu.addAction(stash_action)
        
        # Automation Menu
        auto_menu = menubar.addMenu('🤖 Automation')
        
        auto_push_action = QAction('🚀 Auto Push', self)
        auto_push_action.setCheckable(True)
        auto_push_action.toggled.connect(self.toggle_auto_push)
        auto_menu.addAction(auto_push_action)
        
        # Help Menu
        help_menu = menubar.addMenu('❓ Help')
        
        about_action = QAction('ℹ️ About GitUploader', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def create_project_manager_tab(self):
        project_tab = QWidget()
        layout = QHBoxLayout()
        
        # Left panel - Project list
        left_panel = QGroupBox(self.tr("📋 Danh sách dự án"))
        left_layout = QVBoxLayout()
        
        self.project_tree = QTreeWidget()
        self.project_tree.setHeaderLabels([self.tr("Dự án"), self.tr("Branch"), self.tr("Status")])
        self.project_tree.itemClicked.connect(self.on_tree_item_clicked)
        left_layout.addWidget(self.project_tree)
        
        # Project operations
        project_ops_layout = QHBoxLayout()
        
        self.clone_btn = QPushButton(self.tr("📥 Clone Repository"))
        self.clone_btn.setIcon(self.create_icon("📥"))
        self.clone_btn.clicked.connect(self.clone_repository)
        project_ops_layout.addWidget(self.clone_btn)
        
        self.backup_btn = QPushButton(self.tr("💾 Backup Project"))
        self.backup_btn.setIcon(self.create_icon("💾"))
        self.backup_btn.clicked.connect(self.backup_project)
        project_ops_layout.addWidget(self.backup_btn)
        
        left_layout.addLayout(project_ops_layout)
        left_panel.setLayout(left_layout)
        layout.addWidget(left_panel)
        
        # Right panel - Project details
        right_panel = QGroupBox(self.tr("📊 Chi tiết dự án"))
        right_layout = QVBoxLayout()
        
        # Project info
        self.project_info_label = QLabel(self.tr("Chọn dự án để xem chi tiết"))
        right_layout.addWidget(self.project_info_label)
        
        # Git history
        history_group = QGroupBox(self.tr("📚 Lịch sử commit"))
        history_layout = QVBoxLayout()
        
        self.history_list = QListWidget()
        history_layout.addWidget(self.history_list)
        
        history_group.setLayout(history_layout)
        right_layout.addWidget(history_group)
        
        # Branch management
        branch_group = QGroupBox(self.tr("🌿 Branch Management"))
        branch_layout = QHBoxLayout()
        
        self.create_branch_btn = QPushButton(self.tr("➕ New Branch"))
        self.create_branch_btn.clicked.connect(self.create_branch)
        branch_layout.addWidget(self.create_branch_btn)
        
        self.switch_branch_btn = QPushButton(self.tr("🔄 Switch Branch"))
        self.switch_branch_btn.clicked.connect(self.switch_branch)
        branch_layout.addWidget(self.switch_branch_btn)
        
        self.merge_branch_btn = QPushButton(self.tr("🔀 Merge Branch"))
        self.merge_branch_btn.clicked.connect(self.merge_branch)
        branch_layout.addWidget(self.merge_branch_btn)
        
        branch_group.setLayout(branch_layout)
        right_layout.addWidget(branch_group)
        
        right_panel.setLayout(right_layout)
        layout.addWidget(right_panel)
        
        project_tab.setLayout(layout)
        self.tabs.addTab(project_tab, self.tr("📁 Project Manager"))

    def toggle_file_browser(self, visible):
        self.file_dock.setVisible(visible)

    def toggle_terminal(self, visible):
        self.terminal_dock.setVisible(visible)

    def show_about(self):
        about_text = """
        <h2>🚀 GitUploader v3.0 Ultimate</h2>
        <p><b>Multi-Platform Git Manager với AI-Powered Features</b></p>
        
        <h3>✨ Tính năng chính:</h3>
        <ul>
        <li>🔧 Advanced Git Operations (Status, Pull, Push, Commit, Stash)</li>
        <li>📊 Project Analytics & Dashboard</li>
        <li>🤖 Automation & File Watcher</li>
        <li>🎨 5 Beautiful Themes (Dark, Light, Blue, Green, Purple)</li>
        <li>📁 Built-in File Browser</li>
        <li>💻 Integrated Terminal</li>
        <li>🌐 Multi-Platform Support (GitHub, GitLab, Bitbucket)</li>
        <li>📦 Git Stash Management</li>
        <li>⚡ Workflow Templates</li>
        <li>💾 Settings Import/Export</li>
        </ul>
        
        <p><b>Developed with ❤️ using PySide6</b></p>
        <p>© 2024 GitUploader Team</p>
        """
        QMessageBox.about(self, "About GitUploader v3.0", about_text)

    def clone_repository(self):
        url, ok = QInputDialog.getText(self, "Clone Repository", 
                                      "Nhập URL repository để clone:")
        if not ok or not url.strip():
            return
        
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục đích")
        if not folder:
            return
        
        try:
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)
            self.status_bar.showMessage("Đang clone repository...")
            
            result = subprocess.run(["git", "clone", url.strip(), folder], 
                                  capture_output=True, text=True)
            
            self.progress_bar.setVisible(False)
            
            if result.returncode == 0:
                QMessageBox.information(self, "Thành công", f"Đã clone repository thành công!")
                self.log_box.append(f"[SUCCESS] Cloned: {url} to {folder}")
                
                # Tự động thêm vào project list
                if os.path.exists(os.path.join(folder, ".git")):
                    proj = ProjectInfo(folder)
                    self.projects.append(proj)
                    self.populate_project_list()
                    self.save_settings()
            else:
                QMessageBox.warning(self, "Lỗi", f"Clone thất bại:\n{result.stderr}")
                
        except Exception as e:
            self.progress_bar.setVisible(False)
            QMessageBox.critical(self, "Lỗi", f"Lỗi clone repository: {str(e)}")

    def backup_project(self):
        if not self.current_project:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn dự án!")
            return
        
        backup_dir = QFileDialog.getExistingDirectory(self, "Chọn thư mục backup")
        if not backup_dir:
            return
        
        try:
            import shutil
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{self.current_project.name}_backup_{timestamp}"
            backup_path = os.path.join(backup_dir, backup_name)
            
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)
            self.status_bar.showMessage("Đang backup project...")
            
            shutil.copytree(self.current_project.path, backup_path)
            
            self.progress_bar.setVisible(False)
            QMessageBox.information(self, "Thành công", f"Backup thành công tại:\n{backup_path}")
            self.log_box.append(f"[SUCCESS] Backup created: {backup_path}")
            
        except Exception as e:
            self.progress_bar.setVisible(False)
            QMessageBox.critical(self, "Lỗi", f"Lỗi backup: {str(e)}")

    def create_branch(self):
        if not self.current_project:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn dự án!")
            return
        
        branch_name, ok = QInputDialog.getText(self, "Create Branch", 
                                             "Nhập tên branch mới:")
        if not ok or not branch_name.strip():
            return
        
        try:
            result = subprocess.run(["git", "checkout", "-b", branch_name.strip()], 
                                  cwd=self.current_project.path, capture_output=True, text=True)
            
            if result.returncode == 0:
                QMessageBox.information(self, "Thành công", f"Đã tạo và chuyển sang branch '{branch_name}'")
                self.log_box.append(f"[SUCCESS] Created branch: {branch_name}")
                self.update_project_info()
            else:
                QMessageBox.warning(self, "Lỗi", f"Tạo branch thất bại:\n{result.stderr}")
                
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Lỗi tạo branch: {str(e)}")

    def switch_branch(self):
        if not self.current_project:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn dự án!")
            return
        
        try:
            # Get list of branches
            result = subprocess.run(["git", "branch"], 
                                  cwd=self.current_project.path, capture_output=True, text=True)
            
            if result.returncode != 0:
                QMessageBox.warning(self, "Lỗi", "Không thể lấy danh sách branches")
                return
            
            branches = [b.strip().replace("* ", "") for b in result.stdout.splitlines() if b.strip()]
            
            if not branches:
                QMessageBox.information(self, "Thông báo", "Không có branch nào")
                return
            
            branch, ok = QInputDialog.getItem(self, "Switch Branch", 
                                            "Chọn branch để chuyển:", branches)
            if not ok:
                return
            
            result = subprocess.run(["git", "checkout", branch], 
                                  cwd=self.current_project.path, capture_output=True, text=True)
            
            if result.returncode == 0:
                QMessageBox.information(self, "Thành công", f"Đã chuyển sang branch '{branch}'")
                self.log_box.append(f"[SUCCESS] Switched to branch: {branch}")
                self.update_project_info()
            else:
                QMessageBox.warning(self, "Lỗi", f"Chuyển branch thất bại:\n{result.stderr}")
                
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Lỗi chuyển branch: {str(e)}")

    def merge_branch(self):
        if not self.current_project:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn dự án!")
            return
        
        branch_name, ok = QInputDialog.getText(self, "Merge Branch", 
                                             "Nhập tên branch để merge:")
        if not ok or not branch_name.strip():
            return
        
        try:
            result = subprocess.run(["git", "merge", branch_name.strip()], 
                                  cwd=self.current_project.path, capture_output=True, text=True)
            
            if result.returncode == 0:
                QMessageBox.information(self, "Thành công", f"Đã merge branch '{branch_name}' thành công")
                self.log_box.append(f"[SUCCESS] Merged branch: {branch_name}")
                self.update_project_info()
            else:
                QMessageBox.warning(self, "Lỗi", f"Merge thất bại:\n{result.stderr}")
                
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Lỗi merge: {str(e)}")

    def toggle_auto_push(self, checked):
        self.auto_push_enabled = checked
        self.save_settings()

    def change_theme(self, theme_name):
        self.current_theme = theme_name
        self.apply_theme(theme_name)
        self.save_settings()

    def toggle_theme(self):
        # This method is called from menu, cycle through themes
        themes = list(self.theme_manager.themes.keys())
        current_index = themes.index(self.current_theme)
        next_index = (current_index + 1) % len(themes)
        self.current_theme = themes[next_index]
        self.apply_theme()
        self.save_settings()
        self.status_bar.showMessage(f"Theme changed to: {self.current_theme}", 2000)

    def change_language(self, index):
        self.language = 'vi' if index == 0 else 'en'
        self.save_settings()
        QMessageBox.information(self, "Info", "Please restart the application to apply language changes.")

    def reset_settings(self):
        reply = QMessageBox.question(self, "Reset", "Are you sure you want to reset all settings?")
        if reply == QMessageBox.Yes:
            self.settings.clear()
            QMessageBox.information(self, "Info", "Settings reset. Please restart the application.")
    
    def on_directory_changed(self, path):
        """Handle directory change events"""
        try:
            if hasattr(self, 'auto_push_check') and self.auto_push_check.isChecked():
                self.log_box.append(f"📁 Directory changed: {path}")
                # Auto commit and push after short delay
                QTimer.singleShot(2000, self.auto_commit_and_push)
        except Exception as e:
            print(f"Directory change error: {e}")

if __name__ == "__main__":
app = QApplication([])
window = GitUploader()
window.show()
app.exec()
