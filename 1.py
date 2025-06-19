import subprocess
subprocess.call("git fetch origin", shell=True)
subprocess.call("git reset --hard origin/main", shell=True)
print("Đã khôi phục code từ GitHub!")
import tkinter as tk
from tkinter import messagebox
import subprocess

def backup_to_github():
    try:
        subprocess.check_call(['git', 'add', '.'])
        subprocess.check_call(['git', 'commit', '-m', 'Backup code'])
        subprocess.check_call(['git', 'push'])
        messagebox.showinfo("Thành công", "Đã sao lưu code lên GitHub!")
    except Exception as e:
        messagebox.showerror("Lỗi", f"Sao lưu thất bại: {e}")

def restore_from_github():
    try:
        subprocess.check_call(['git', 'pull'])
        messagebox.showinfo("Thành công", "Đã khôi phục code từ GitHub!")
    except Exception as e:
        messagebox.showerror("Lỗi", f"Khôi phục thất bại: {e}")

root = tk.Tk()
root.title("Sao lưu & Khôi phục GitHub")

backup_btn = tk.Button(root, text="Sao lưu code lên GitHub", command=backup_to_github, width=30)
backup_btn.pack(pady=10)

restore_btn = tk.Button(root, text="Khôi phục code từ GitHub", command=restore_from_github, width=30)
restore_btn.pack(pady=10)

root.mainloop()