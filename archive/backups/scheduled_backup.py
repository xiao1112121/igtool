#!/usr/bin/env python3
"""
Script backup định kỳ tự động
Chạy backup mỗi X phút hoặc khi có thay đổi file
"""

import os
import sys
import time
import datetime
import subprocess
import threading
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class CodeChangeHandler(FileSystemEventHandler):
    """Handler để theo dõi thay đổi file code"""
    
    def __init__(self, backup_callback):
        self.backup_callback = backup_callback
        self.last_backup = 0
        self.backup_cooldown = 300  # 5 phút cooldown giữa các backup
        
    def on_modified(self, event):
        if event.is_directory:
            return
            
        # Chỉ backup khi file .py được thay đổi
        if event.src_path.endswith('.py'):
            current_time = time.time()
            if current_time - self.last_backup > self.backup_cooldown:
                self.last_backup = current_time
                file_name = os.path.basename(event.src_path)
                self.backup_callback(f"Auto backup - {file_name} changed")

class ScheduledBackup:
    """Class quản lý backup định kỳ"""
    
    def __init__(self):
        self.observer = None
        self.running = False
        
    def run_backup(self, message=None):
        """Chạy backup với message"""
        try:
            if not message:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                message = f"Scheduled backup - {timestamp}"
            
            print(f"🔄 {message}")
            result = subprocess.run([
                sys.executable, 
                "auto_backup.py", 
                message
            ], check=False, capture_output=True, text=True, cwd=os.getcwd())
            
            if result.returncode == 0:
                print("✅ Backup thành công!")
            else:
                print(f"❌ Backup thất bại: {result.stderr}")
                
        except Exception as e:
            print(f"❌ Lỗi backup: {e}")
    
    def scheduled_backup_worker(self, interval_minutes):
        """Worker thread cho backup định kỳ"""
        while self.running:
            time.sleep(interval_minutes * 60)
            if self.running:
                self.run_backup()
    
    def start_monitoring(self, watch_directory=".", interval_minutes=30):
        """Bắt đầu theo dõi và backup định kỳ"""
        print(f"🚀 Bắt đầu theo dõi thay đổi trong: {os.path.abspath(watch_directory)}")
        print(f"⏰ Backup định kỳ mỗi {interval_minutes} phút")
        print("📝 Backup tự động khi file .py được thay đổi")
        print("Nhấn Ctrl+C để dừng\n")
        
        # Thiết lập file watcher
        event_handler = CodeChangeHandler(self.run_backup)
        self.observer = Observer()
        self.observer.schedule(event_handler, watch_directory, recursive=True)
        
        # Bắt đầu monitoring
        self.running = True
        self.observer.start()
        
        # Bắt đầu scheduled backup thread
        backup_thread = threading.Thread(
            target=self.scheduled_backup_worker, 
            args=(interval_minutes,),
            daemon=True
        )
        backup_thread.start()
        
        try:
            # Backup đầu tiên
            self.run_backup("Monitoring started - Initial backup")
            
            # Vòng lặp chính
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n🛑 Đang dừng monitoring...")
            self.stop_monitoring()
    
    def stop_monitoring(self):
        """Dừng monitoring"""
        self.running = False
        if self.observer:
            self.observer.stop()
            self.observer.join()
        print("✅ Đã dừng monitoring")

def main():
    """Main function"""
    if len(sys.argv) > 1:
        try:
            interval = int(sys.argv[1])
        except ValueError:
            print("❌ Interval phải là số (phút)")
            sys.exit(1)
    else:
        interval = 30  # Default 30 phút
    
    # Kiểm tra dependencies
    try:
        import watchdog
    except ImportError:
        print("❌ Cần cài đặt watchdog: pip install watchdog")
        print("Hoặc chạy backup thủ công với: python auto_backup.py")
        sys.exit(1)
    
    scheduler = ScheduledBackup()
    scheduler.start_monitoring(interval_minutes=interval)

if __name__ == "__main__":
    main() 