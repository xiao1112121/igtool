# Fix UnboundLocalError trong Threading System

## Vấn đề
Ứng dụng gặp lỗi `UnboundLocalError` khi sử dụng chức năng gửi tin nhắn qua threading.

## Nguyên nhân
Trong `MessageSenderThread.run()`, có các biến local có thể không được khởi tạo trong một số trường hợp:

1. **Biến `final_status`**: Không được khởi tạo khi `self.is_stopped()` return `True`
2. **Biến `total_targets`**: Có thể không được khởi tạo nếu driver creation failed

## Giải pháp đã áp dụng

### 1. Sửa lỗi `final_status` UnboundLocalError
```python
# Trước (có lỗi):
if not self.is_stopped():
    if acc["success"] >= max_success:
        final_status = "Thành công"
    elif error_count >= max_error:
        final_status = "Lỗi"
    else:
        final_status = "Kết thúc"
        
self.progress_updated.emit(username, final_status, ...)  # ❌ UnboundLocalError nếu is_stopped() = True

# Sau (đã sửa):
final_status = "Kết thúc"  # ✅ Khởi tạo mặc định
if not self.is_stopped():
    if acc["success"] >= max_success:
        final_status = "Thành công"
    elif error_count >= max_error:
        final_status = "Lỗi"
    else:
        final_status = "Kết thúc"
else:
    final_status = "Đã dừng"  # ✅ Xử lý trường hợp dừng
        
self.progress_updated.emit(username, final_status, ...)  # ✅ An toàn
```

### 2. Sửa lỗi `total_targets` UnboundLocalError
```python
# Trước (có lỗi):
driver = self.get_driver_for_account(acc)
if driver is None:
    self.error_occurred.emit(username, "Không thể lấy driver")
    continue  # ❌ Skip khỏi loop, total_targets chưa được khởi tạo

total_targets = len(self.usernames)  # ❌ Có thể không được chạy
# ... later usage of total_targets

# Sau (đã sửa):
total_targets = len(self.usernames)  # ✅ Khởi tạo ngay từ đầu

driver = self.get_driver_for_account(acc)
if driver is None:
    self.error_occurred.emit(username, "Không thể lấy driver")
    continue  # ✅ An toàn, total_targets đã được khởi tạo
```

## Kết quả
- ✅ Không còn lỗi `UnboundLocalError` khi sử dụng chức năng gửi tin nhắn
- ✅ Thread có thể dừng an toàn với trạng thái "Đã dừng"
- ✅ Xử lý đúng trường hợp không thể tạo driver

## Files đã sửa
- `src/ui/messaging.py`: Sửa lỗi UnboundLocalError trong `MessageSenderThread.run()`

## Test
Chạy ứng dụng và thử sử dụng chức năng gửi tin nhắn. Lỗi UnboundLocalError sẽ không còn xảy ra. 