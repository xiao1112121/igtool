import time
import random
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from PySide6.QtWidgets import QSpinBox
from PySide6.QtGui import QFont

def random_delay(min_seconds=0.5, max_seconds=1.5):
    """Tạo delay ngẫu nhiên giữa các thao tác"""
    time.sleep(random.uniform(min_seconds, max_seconds))

def wait_for_element(driver, by, value, timeout=10):
    """Đợi cho đến khi element xuất hiện"""
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        return element
    except TimeoutException:
        return None

def wait_for_element_clickable(driver, by, value, timeout=10):
    """Đợi cho đến khi element có thể click được"""
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )
        # Thử click thông thường trước
        try:
            element.click()
            return element
        except Exception as e:
            # Nếu click thông thường bị chặn, thử click bằng JavaScript
            if "element click intercepted" in str(e).lower():
                driver.execute_script("arguments[0].click();", element)
                return element
            else:
                raise e # Re-raise các lỗi khác
    except TimeoutException:
        return None

def retry_operation(operation_func, max_retries=3, retry_delay=3, *args, **kwargs):
    """
    Thực hiện một operation với logic thử lại
    
    Args:
        operation_func: Function cần thực hiện
        max_retries: Số lần thử lại tối đa
        retry_delay: Thời gian chờ giữa các lần thử (giây)
        *args, **kwargs: Các tham số truyền vào operation_func
        
    Returns:
        Kết quả của operation_func nếu thành công
        
    Raises:
        Exception: Nếu không thể thực hiện operation sau max_retries lần thử
    """
    retry_count = 0
    last_error = None
    
    while retry_count < max_retries:
        try:
            return operation_func(*args, **kwargs)
        except Exception as e:
            last_error = e
            retry_count += 1
            if retry_count < max_retries:
                print(f"[DEBUG] Lỗi khi thực hiện operation (lần thử {retry_count}/{max_retries}): {e}")
                print(f"[DEBUG] Đợi {retry_delay} giây trước khi thử lại...")
                time.sleep(retry_delay)
            else:
                print(f"[ERROR] Không thể thực hiện operation sau {max_retries} lần thử")
                raise last_error 

def create_windows_spinbox(min_val=1, max_val=100, default_value=1):
    """
    Tạo SpinBox với style chuẩn Windows đồng bộ cho tất cả các tab
    
    Args:
        min_val: Giá trị tối thiểu
        max_val: Giá trị tối đa  
        default_value: Giá trị mặc định
    
    Returns:
        QSpinBox: SpinBox với style chuẩn Windows
    """
    spin = QSpinBox()
    spin.setFont(QFont("Segoe UI", 9))
    spin.setFixedSize(54, 26)  # Kích thước chuẩn Windows
    spin.setRange(min_val, max_val)
    spin.setValue(default_value)
    
    # Style chuẩn Windows
    spin.setStyleSheet("""
        QSpinBox {
            font-size: 9px;
            font-weight: normal;
            border: 1px solid #ccc;
            border-radius: 3px;
            background-color: white;
            padding: 2px 4px;
            margin: 0px;
        }
        QSpinBox::up-button, QSpinBox::down-button {
            width: 14px;
            height: 12px;
            border: none;
            background-color: #f0f0f0;
        }
        QSpinBox::up-button:hover, QSpinBox::down-button:hover {
            background-color: #e0e0e0;
        }
        QSpinBox::up-arrow, QSpinBox::down-arrow {
            width: 6px;
            height: 6px;
        }
    """)
    
    return spin 