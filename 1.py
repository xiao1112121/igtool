from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QMessageBox
import subprocess

class GitUploader(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GitHub Sync Tool")
        self.setMinimumWidth(300)

        layout = QVBoxLayout()

        self.upload_btn = QPushButton("🔼 Tải lên GitHub")
        self.upload_btn.clicked.connect(self.upload_to_github)
        layout.addWidget(self.upload_btn)

        self.restore_btn = QPushButton("🔄 Khôi phục bản tải gần nhất")
        self.restore_btn.clicked.connect(self.restore_from_github)
        layout.addWidget(self.restore_btn)

        self.setLayout(layout)

    def upload_to_github(self):
        try:
            subprocess.run(["git", "add", "."], check=True)
            subprocess.run(["git", "commit", "-m", "Auto upload from GUI"], check=True)
            subprocess.run(["git", "push"], check=True)
            QMessageBox.information(self, "Thành công", "✅ Đã tải lên GitHub!")
        except subprocess.CalledProcessError:
            QMessageBox.critical(self, "Lỗi", "❌ Lỗi khi tải lên GitHub!")

    def restore_from_github(self):
        try:
            subprocess.run(["git", "fetch"], check=True)
            subprocess.run(["git", "reset", "--hard", "origin/main"], check=True)
            QMessageBox.information(self, "Thành công", "✅ Đã khôi phục bản mới nhất từ GitHub!")
        except subprocess.CalledProcessError:
            QMessageBox.critical(self, "Lỗi", "❌ Không thể khôi phục từ GitHub!")

if __name__ == "__main__":
    app = QApplication([])
    window = GitUploader()
    window.show()
    app.exec()
