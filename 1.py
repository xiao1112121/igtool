import tkinter as tk
from tkinter import messagebox, simpledialog
import subprocess

def git_push():
    msg = simpledialog.askstring("Thông báo", "Nhập nội dung commit:")
    if not msg:
        messagebox.showwarning("Chưa nhập nội dung", "Vui lòng nhập nội dung commit!")
        return
    try:
        subprocess.check_call("git add .", shell=True)
        subprocess.check_call(f'git commit -m "{msg}"', shell=True)
        subprocess.check_call("git push", shell=True)
        messagebox.showinfo("Thành công", "Đã backup code lên GitHub thành công!")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Lỗi", f"Lệnh git bị lỗi: {e}")

def git_restore():
    ok = messagebox.askyesno("Xác nhận", "Bạn chắc chắn muốn khôi phục lại code từ GitHub?\nMọi thay đổi chưa backup sẽ bị mất!")
    if not ok:
        return
    try:
        subprocess.check_call("git fetch origin", shell=True)
        subprocess.check_call("git reset --hard origin/main", shell=True)
        messagebox.showinfo("Thành công", "Đã khôi phục code về bản trên GitHub!")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Lỗi", f"Lệnh git bị lỗi: {e}")

root = tk.Tk()
root.title("GitHub Control Panel")
root.geometry("320x180")

btn_push = tk.Button(root, text="Backup lên GitHub", command=git_push, font=("Segoe UI", 12), bg="#4caf50", fg="white", width=18, height=2)
btn_restore = tk.Button(root, text="Khôi phục từ GitHub", command=git_restore, font=("Segoe UI", 12), bg="#1976d2", fg="white", width=18, height=2)

btn_push.pack(pady=15)
btn_restore.pack(pady=10)

root.mainloop()
