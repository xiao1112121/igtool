import time
import random
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

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