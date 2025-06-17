import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from twocaptcha import TwoCaptcha

def handle_cookie_banner(driver, username):
    """Xử lý banner cookie nếu xuất hiện."""
    try:
        accept_cookies_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, 
                "//button[text()='Cho phép tất cả cookie'] | "
                "//button[text()='Accept All'] | "
                "//button[text()='Allow all cookies']"
            ))
        )
        if accept_cookies_button:
            print(f"[DEBUG] Đã chấp nhận cookie cho {username}.")
            time.sleep(random.uniform(1, 2))
            accept_cookies_button.click()
    except TimeoutException:
        print(f"[DEBUG] Không tìm thấy banner cookie cho {username}")

def handle_login_popups(driver, username):
    """Xử lý các popup sau khi đăng nhập."""
    # Xử lý popup "Lưu thông tin đăng nhập"
    try:
        not_now_button_xpath = (
            "//button[text()='Not Now'] | "
            "//button[text()='Lúc khác'] | "
            "//button[text()='Später'] | " # German "Later"
            "//button[text()='Más tarde'] | " # Spanish "Later"
            "//button[text()='Jetzt nicht'] | " # German "Not now"
            "//button[contains(.,'Not Now')] | "
            "//button[contains(.,'Lúc khác')] | "
            "//div[text()='Lưu thông tin đăng nhập?']/ancestor::div[contains(@class, 'x1n2onr6')]//button[contains(.,'Lúc khác')] | "
            "//div[text()='Save your login info?']/ancestor::div[contains(@class, 'x1n2onr6')]//button[contains(.,'Not Now')]"
        )
        not_now_button = WebDriverWait(driver, 7).until(
            EC.element_to_be_clickable((By.XPATH, not_now_button_xpath))
        )
        if not_now_button:
            print(f"[DEBUG] Đã click nút 'Not Now' (lưu thông tin đăng nhập) cho {username}.")
            time.sleep(random.uniform(1, 2))
            not_now_button.click()
    except TimeoutException:
        print(f"[DEBUG] Không tìm thấy popup lưu thông tin đăng nhập cho {username}")

    # Xử lý popup "Bật thông báo"
    try:
        notifications_xpath = (
            "//button[text()='Not Now'] | "
            "//button[text()='Lúc khác'] | "
            "//button[text()='Später'] | "
            "//button[text()='Ahora no'] | " # Spanish "Not now"
            "//button[contains(.,'Not Now')] | "
            "//button[contains(.,'Lúc khác')] | "
            "//div[text()='Turn on notifications?']/ancestor::div[contains(@class, 'x1n2onr6')]//button[contains(.,'Not Now')] | "
            "//div[text()='Bật thông báo?']/ancestor::div[contains(@class, 'x1n2onr6')]//button[contains(.,'Lúc khác')]"
        )
        notifications_button = WebDriverWait(driver, 7).until(
            EC.element_to_be_clickable((By.XPATH, notifications_xpath))
        )
        if notifications_button:
            print(f"[DEBUG] Đã click nút 'Not Now' (thông báo) cho {username}.")
            time.sleep(random.uniform(1, 2))
            notifications_button.click()
    except TimeoutException:
        print(f"[DEBUG] Không tìm thấy popup thông báo cho {username}")

def handle_recaptcha(driver, username, api_key):
    """Xử lý reCAPTCHA khi gặp phải."""
    try:
        # Kiểm tra xem có reCAPTCHA không
        recaptcha_frame = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='recaptcha']"))
        )
        print(f"[DEBUG] Phát hiện reCAPTCHA cho tài khoản {username}")

        # Chuyển đến frame của reCAPTCHA
        driver.switch_to.frame(recaptcha_frame)

        # Lấy site key của reCAPTCHA
        site_key = driver.find_element(By.CLASS_NAME, "g-recaptcha").get_attribute("data-sitekey")
        print(f"[DEBUG] Site key của reCAPTCHA: {site_key}")

        # Chuyển về frame chính
        driver.switch_to.default_content()

        # Gọi API 2captcha để giải captcha
        solver = TwoCaptcha(api_key)
        try:
            result = solver.recaptcha(
                sitekey=site_key,
                url=driver.current_url,
            )
            print(f"[DEBUG] Đã nhận kết quả từ 2captcha cho {username}")

            # Điền kết quả vào reCAPTCHA
            driver.execute_script(
                f'document.getElementById("g-recaptcha-response").innerHTML="{result["code"]}";'
            )
            print(f"[DEBUG] Đã điền kết quả reCAPTCHA cho {username}")

            # Submit form
            submit_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
            )
            submit_button.click()
            print(f"[DEBUG] Đã submit form sau khi giải reCAPTCHA cho {username}")

            # Đợi một chút để xem kết quả
            time.sleep(3)
            return True

        except Exception as e:
            print(f"[ERROR] Lỗi khi giải reCAPTCHA cho {username}: {e}")
            return False

    except TimeoutException:
        print(f"[DEBUG] Không tìm thấy reCAPTCHA cho {username}")
        return True  # Không có reCAPTCHA, coi như thành công
    except Exception as e:
        print(f"[ERROR] Lỗi không xác định khi xử lý reCAPTCHA cho {username}: {e}")
        return False

def verify_login_success(driver, username):
    """Xác minh đăng nhập thành công."""
    try:
        # Đợi URL chuyển hướng
        WebDriverWait(driver, 20).until(
            EC.url_contains("instagram.com") and not EC.url_contains("accounts/login")
        )
        print(f"[DEBUG] URL đã chuyển hướng sau đăng nhập cho {username}.")

        # Kiểm tra biểu tượng Home
        home_icon = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "svg[aria-label='Home']"))
        )
        if home_icon:
            print(f"[DEBUG] Đã tìm thấy biểu tượng Home cho {username}.")
            return True
        return False

    except TimeoutException:
        print(f"[WARN] Không thể xác nhận đăng nhập thành công cho {username}")
        return False
    except Exception as e:
        print(f"[ERROR] Lỗi khi xác minh đăng nhập cho {username}: {e}")
        return False 