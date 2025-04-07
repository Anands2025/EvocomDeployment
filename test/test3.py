from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def test_community_join():
    driver = webdriver.Chrome()
    driver.maximize_window()
    
    try:
        print("[{}] Starting the Community Join test...".format(time.strftime("%Y-%m-%d %H:%M:%S")))
        
        # Login (reusing your existing login code)
        driver.get("http://127.0.0.1:8000/login/")
        # ... (login code here)
        
        # Navigate to community list page
        driver.get("http://127.0.0.1:8000/communities")
        print("[{}] Navigated to the community list page.".format(time.strftime("%Y-%m-%d %H:%M:%S")))
        
        # Find and click on a community to join
        community_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "community-link"))
        )
        community_name = community_link.text
        community_link.click()
        print("[{}] Clicked on community: {}".format(time.strftime("%Y-%m-%d %H:%M:%S"), community_name))
        
        # Click join button
        join_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "join-community-button"))
        )
        join_button.click()
        print("[{}] Clicked join community button.".format(time.strftime("%Y-%m-%d %H:%M:%S")))
        
        # Wait for success message
        success_message = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "success-message"))
        )
        print("[{}] Successfully joined the community!".format(time.strftime("%Y-%m-%d %H:%M:%S")))
        
    finally:
        driver.quit()
        print("[{}] Browser closed. Test completed.".format(time.strftime("%Y-%m-%d %H:%M:%S")))

if __name__ == "__main__":
    test_community_join()