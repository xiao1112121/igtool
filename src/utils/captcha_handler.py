from twocaptcha import TwoCaptcha
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time

class CaptchaHandler:
    def __init__(self, api_key):
        self.solver = TwoCaptcha(api_key)
        self.retry_count = 3
        self.wait_time = 10

    def handle_recaptcha(self, driver, username):
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
            try:
                result = self.solver.recaptcha(
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

    def handle_hcaptcha(self, driver, username):
        """Xử lý hCaptcha khi gặp phải."""
        try:
            # Kiểm tra xem có hCaptcha không
            hcaptcha_frame = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='hcaptcha']"))
            )
            print(f"[DEBUG] Phát hiện hCaptcha cho tài khoản {username}")

            # Chuyển đến frame của hCaptcha
            driver.switch_to.frame(hcaptcha_frame)

            # Lấy site key của hCaptcha
            site_key = driver.find_element(By.CLASS_NAME, "h-captcha").get_attribute("data-sitekey")
            print(f"[DEBUG] Site key của hCaptcha: {site_key}")

            # Chuyển về frame chính
            driver.switch_to.default_content()

            # Gọi API 2captcha để giải captcha
            try:
                result = self.solver.hcaptcha(
                    sitekey=site_key,
                    url=driver.current_url,
                )
                print(f"[DEBUG] Đã nhận kết quả từ 2captcha cho {username}")

                # Điền kết quả vào hCaptcha
                driver.execute_script(
                    f'document.querySelector("[name=h-captcha-response]").innerHTML="{result["code"]}";'
                )
                print(f"[DEBUG] Đã điền kết quả hCaptcha cho {username}")

                # Submit form
                submit_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
                )
                submit_button.click()
                print(f"[DEBUG] Đã submit form sau khi giải hCaptcha cho {username}")

                # Đợi một chút để xem kết quả
                time.sleep(3)
                return True

            except Exception as e:
                print(f"[ERROR] Lỗi khi giải hCaptcha cho {username}: {e}")
                return False

        except TimeoutException:
            print(f"[DEBUG] Không tìm thấy hCaptcha cho {username}")
            return True  # Không có hCaptcha, coi như thành công
        except Exception as e:
            print(f"[ERROR] Lỗi không xác định khi xử lý hCaptcha cho {username}: {e}")
            return False