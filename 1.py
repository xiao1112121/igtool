import os
import subprocess
import requests
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox, QTextEdit, QInputDialog, QLabel, QComboBox, QFileDialog, QListWidget, QListWidgetItem, QCheckBox, QSplitter, QTabWidget, QLineEdit
)
from PySide6.QtGui import QClipboard, QColor, QFont
from PySide6.QtCore import Qt

# Helper function for network check
def check_github_online():
    try:
        requests.get("https://github.com", timeout=3)
        return True
    except Exception:
        return False

class ProjectInfo:
    def __init__(self, path):
        self.path = path
        self.name = os.path.basename(path)
        self.remotes = self.get_remotes()

    def get_remotes(self):
        try:
            out = subprocess.run(["git", "remote", "-v"], cwd=self.path, capture_output=True, text=True)
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
            out = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=self.path, capture_output=True, text=True)
            return out.stdout.strip()
        except Exception:
            return ""

    def get_remote_url(self, remote):
        try:
            out = subprocess.run(["git", "remote", "get-url", remote], cwd=self.path, capture_output=True, text=True)
            return out.stdout.strip()
        except Exception:
            return ""

    def get_default_remote_branch(self, remote):
        try:
            out = subprocess.run(["git", "remote", "show", remote], cwd=self.path, capture_output=True, text=True)
            for line in out.stdout.splitlines():
                if "HEAD branch" in line:
                    return line.split(":")[-1].strip()
            return ""
        except Exception:
            return ""

class GitUploader(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GitHub Multi-Project Sync Tool (Pro)")
        self.setMinimumWidth(900)
        self.projects = []
        self.current_project = None
        self.language = 'vi'  # vi/en
        self.dark_mode = False
        self.init_ui()
        self.set_ui_enabled(False)
        self.check_network_status()

    def init_ui(self):
        main_layout = QVBoxLayout()
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)
        # --- Tab 1: Git ---
        git_tab = QWidget()
        layout = QVBoxLayout()

        # Dự án
        proj_layout = QHBoxLayout()
        self.project_list = QComboBox()
        self.project_list.setMinimumWidth(200)
        self.project_list.currentIndexChanged.connect(self.on_project_changed)
        proj_layout.addWidget(QLabel(self.tr("Dự án:")))
        proj_layout.addWidget(self.project_list)
        self.add_proj_btn = QPushButton(self.tr("➕ Thêm dự án"))
        self.add_proj_btn.clicked.connect(self.add_project)
        proj_layout.addWidget(self.add_proj_btn)
        # Nút kết nối & push lên GitHub
        self.push_github_btn = QPushButton(self.tr("🌐 Kết nối & Push lên GitHub"))
        self.push_github_btn.clicked.connect(self.connect_and_push_github)
        proj_layout.addWidget(self.push_github_btn)
        layout.addLayout(proj_layout)

        # Remote
        remote_layout = QHBoxLayout()
        self.remote_box = QComboBox()
        self.remote_box.setMinimumWidth(120)
        self.remote_box.currentIndexChanged.connect(self.update_remote_info)
        remote_layout.addWidget(QLabel(self.tr("Remote:")))
        remote_layout.addWidget(self.remote_box)
        self.refresh_remotes_btn = QPushButton(self.tr("🔄 Làm mới remote"))
        self.refresh_remotes_btn.clicked.connect(self.refresh_remotes)
        remote_layout.addWidget(self.refresh_remotes_btn)
        self.add_remote_btn = QPushButton(self.tr("➕ Thêm remote"))
        self.add_remote_btn.clicked.connect(self.add_remote)
        remote_layout.addWidget(self.add_remote_btn)
        self.remote_url_label = QLabel("")
        remote_layout.addWidget(self.remote_url_label)
        layout.addLayout(remote_layout)

        # Branch info
        branchinfo_layout = QHBoxLayout()
        self.branch_label = QLabel(self.tr("Branch hiện tại: "))
        branchinfo_layout.addWidget(self.branch_label)
        self.default_branch_label = QLabel(self.tr("Branch mặc định remote: "))
        branchinfo_layout.addWidget(self.default_branch_label)
        layout.addLayout(branchinfo_layout)

        self.status_label = QLabel(self.tr("Trạng thái: Sẵn sàng"))
        layout.addWidget(self.status_label)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(self.log_box)

        git_tab.setLayout(layout)
        self.tabs.addTab(git_tab, self.tr("Git"))
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.tabs)

    def on_project_changed(self, idx):
        if not hasattr(self, 'projects') or idx < 0 or idx >= len(self.projects):
            self.current_project = None
            self.set_ui_enabled(False)
            self.status_label.setText(self.tr("Trạng thái: Chưa chọn dự án"))
            return
        self.current_project = self.projects[idx]
        self.set_ui_enabled(True)
        self.status_label.setText(self.tr(f"Trạng thái: Đã chọn dự án {self.current_project.name}"))
        # Có thể gọi các hàm cập nhật giao diện khác ở đây nếu cần

    def set_ui_enabled(self, enabled):
        for w in [self.add_proj_btn, self.remote_box, self.refresh_remotes_btn, self.add_remote_btn]:
            w.setEnabled(enabled)

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
            if dialog.exec_():
                selected_paths = dialog.selectedFiles()
                if not selected_paths:
                    self.log_box.append("[INFO] Không có thư mục nào được chọn")
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
                            subprocess.run(["git", "init"], cwd=path, check=True)
                            self.log_box.append(f"[INFO] Đã khởi tạo Git repository tại: {path}")
                        except subprocess.CalledProcessError as e:
                            QMessageBox.warning(self, "Lỗi", f"Không thể khởi tạo Git repository:\n{str(e)}")
                            self.log_box.append(f"[ERROR] Lỗi khởi tạo Git repo: {str(e)}")
                            return
                    else:
                        self.log_box.append("[INFO] Người dùng đã hủy khởi tạo Git repository")
                        return

                # Kiểm tra trùng lặp
                for proj in self.projects:
                    if proj.path == path:
                        QMessageBox.information(self, "Đã tồn tại", "Dự án này đã có trong danh sách.")
                        self.log_box.append(f"[INFO] Dự án đã tồn tại: {path}")
                        return

                # Thêm dự án mới
                proj = ProjectInfo(path)
                self.projects.append(proj)
                self.project_list.addItem(f"{proj.name} ({proj.path})")
                self.project_list.setCurrentIndex(len(self.projects)-1)
                self.log_box.append(f"[INFO] Đã thêm dự án thành công: {proj.path}")
            else:
                self.log_box.append("[INFO] Người dùng đã hủy chọn thư mục")
                
        except Exception as e:
            error_msg = str(e)
            QMessageBox.critical(self, "Lỗi", f"Không thể thêm dự án:\n{error_msg}")
            self.log_box.append(f"[ERROR] Lỗi khi thêm dự án: {error_msg}")
            self.log_box.append(f"[DEBUG] Chi tiết lỗi: {type(e).__name__}")

    def check_network_status(self):
        if not check_github_online():
            self.status_label.setText(self.tr("⚠️ Không có kết nối mạng hoặc không truy cập được GitHub!"))
        else:
            self.status_label.setText(self.tr("Trạng thái: Sẵn sàng"))

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
        # Đảm bảo hàm này tồn tại để tránh lỗi AttributeError
        # Có thể cập nhật label remote_url_label nếu muốn
        if hasattr(self, 'remote_url_label'):
            remote = self.remote_box.currentText() if hasattr(self, 'remote_box') else ''
            self.remote_url_label.setText(f"Remote: {remote}")

    def refresh_remotes(self):
        # Cập nhật lại danh sách remote thực tế từ git
        if not self.current_project:
            return
        self.remote_box.clear()
        remotes = self.get_remotes_for_current_project()
        for r in remotes:
            self.remote_box.addItem(r)
        if remotes:
            self.remote_box.setCurrentIndex(0)
        self.update_remote_info()

    def get_remotes_for_current_project(self):
        if not self.current_project:
            return []
        try:
            out = subprocess.run(["git", "remote"], cwd=self.current_project.path, capture_output=True, text=True)
            return [r.strip() for r in out.stdout.splitlines() if r.strip()]
        except Exception:
            return []

    def add_remote(self):
        if not self.current_project:
            QMessageBox.warning(self, "Chưa chọn dự án", "Vui lòng chọn dự án trước!")
            return
        name, ok1 = QInputDialog.getText(self, "Tên remote", "Nhập tên remote (ví dụ: origin):")
        if not ok1 or not name.strip():
            return
        url, ok2 = QInputDialog.getText(self, "URL remote", "Nhập URL remote (ví dụ: https://github.com/xxx/yyy.git):")
        if not ok2 or not url.strip():
            return
        # Thêm remote qua git
        try:
            out = subprocess.run(["git", "remote", "add", name.strip(), url.strip()], cwd=self.current_project.path, capture_output=True, text=True)
            if out.returncode == 0:
                QMessageBox.information(self, "Thành công", f"Đã thêm remote '{name.strip()}' cho dự án.")
            else:
                QMessageBox.warning(self, "Lỗi", f"Không thể thêm remote: {out.stderr}")
        except Exception as e:
            QMessageBox.warning(self, "Lỗi", str(e))
        self.refresh_remotes()

    def connect_and_push_github(self):
        if not self.current_project:
            QMessageBox.warning(self, "Chưa chọn dự án", "Vui lòng chọn dự án trước!")
            return
        url, ok = QInputDialog.getText(self, "URL GitHub", "Nhập URL repo GitHub (https://github.com/xxx/yyy.git):")
        if not ok or not url.strip():
            return
        # Thêm hoặc cập nhật remote origin
        remotes = self.get_remotes_for_current_project()
        if "origin" in remotes:
            subprocess.run(["git", "remote", "set-url", "origin", url.strip()], cwd=self.current_project.path)
        else:
            subprocess.run(["git", "remote", "add", "origin", url.strip()], cwd=self.current_project.path)
        # Kiểm tra có commit chưa, nếu chưa thì tạo commit đầu tiên
        out = subprocess.run(["git", "rev-parse", "--verify", "HEAD"], cwd=self.current_project.path, capture_output=True, text=True)
        if out.returncode != 0:
            # Chưa có commit, tạo file README.md nếu chưa có
            readme_path = os.path.join(self.current_project.path, "README.md")
            if not os.path.exists(readme_path):
                with open(readme_path, "w", encoding="utf-8") as f:
                    f.write(f"# {self.current_project.name}\n")
            
            subprocess.run(["git", "add", "."], cwd=self.current_project.path)
            subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=self.current_project.path)
        # Push lần đầu
        branch = "main"
        # Nếu không có branch main, thử master
        out = subprocess.run(["git", "branch"], cwd=self.current_project.path, capture_output=True, text=True)
        branches = [b.strip().replace("* ", "") for b in out.stdout.splitlines()]
        if "main" not in branches and "master" in branches:
            branch = "master"
        push_out = subprocess.run(["git", "push", "-u", "origin", branch], cwd=self.current_project.path, capture_output=True, text=True)
        if push_out.returncode == 0:
            QMessageBox.information(self, "Thành công", f"Đã push dự án lên GitHub: {url.strip()} (branch: {branch})")
        else:
            QMessageBox.warning(self, "Lỗi", f"Push thất bại: {push_out.stderr}")

if __name__ == "__main__":
    app = QApplication([])
    window = GitUploader()
    window.show()
    app.exec()
