from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def test_event_creation():
    driver = webdriver.Chrome()
    driver.maximize_window()
    
    try:
        print("[{}] Starting the Event Creation test...".format(time.strftime("%Y-%m-%d %H:%M:%S")))
        
        # Login (reusing your existing login code)
        driver.get("http://127.0.0.1:8000/login/")
        # ... (login code here)
        
        # Navigate to event creation page
        driver.get("http://127.0.0.1:8000/events/create")
        print("[{}] Navigated to the event creation page.".format(time.strftime("%Y-%m-%d %H:%M:%S")))
        
        # Fill in event details
        driver.find_element(By.ID, "event-name").send_keys("Test Event")
        driver.find_element(By.ID, "event-description").send_keys("This is a test event created by Selenium")
        driver.find_element(By.ID, "event-date").send_keys("2024-12-31")
        driver.find_element(By.ID, "event-time").send_keys("14:00")
        driver.find_element(By.ID, "event-location").send_keys("Test Location")
        print("[{}] Filled in event details.".format(time.strftime("%Y-%m-%d %H:%M:%S")))
        
        # Submit the form
        driver.find_element(By.ID, "create-event-button").click()
        print("[{}] Submitted the event creation form.".format(time.strftime("%Y-%m-%d %H:%M:%S")))
        
        # Wait for success message
        success_message = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "success-message"))
        )
        print("[{}] Event creation successful!".format(time.strftime("%Y-%m-%d %H:%M:%S")))
        
    finally:
        driver.quit()
        print("[{}] Browser closed. Test completed.".format(time.strftime("%Y-%m-%d %H:%M:%S")))

if __name__ == "__main__":
    test_event_creation()