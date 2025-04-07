from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def test_event_registration():
    driver = webdriver.Chrome()
    driver.maximize_window()
    
    try:
        print("[{}] Starting the Event Registration test...".format(time.strftime("%Y-%m-%d %H:%M:%S")))
        
        # Login (reusing your existing login code)
        driver.get("http://127.0.0.1:8000/login/")
        # ... (login code here)
        
        # Navigate to events page
        driver.get("http://127.0.0.1:8000/events")
        print("[{}] Navigated to the events page.".format(time.strftime("%Y-%m-%d %H:%M:%S")))
        
        # Find and click on an event to register
        event_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "event-link"))
        )
        event_name = event_link.text
        event_link.click()
        print("[{}] Clicked on event: {}".format(time.strftime("%Y-%m-%d %H:%M:%S"), event_name))
        
        # Click register button
        register_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "register-event-button"))
        )
        register_button.click()
        print("[{}] Clicked register for event button.".format(time.strftime("%Y-%m-%d %H:%M:%S")))
        
        # Handle payment if required (assuming a free event for simplicity)
        
        # Wait for success message
        success_message = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "success-message"))
        )
        print("[{}] Successfully registered for the event!".format(time.strftime("%Y-%m-%d %H:%M:%S")))
        
    finally:
        driver.quit()
        print("[{}] Browser closed. Test completed.".format(time.strftime("%Y-%m-%d %H:%M:%S")))

if __name__ == "__main__":
    test_event_registration()