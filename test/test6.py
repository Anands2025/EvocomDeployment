from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from datetime import datetime

def test_community_gallery_upload():
    driver = webdriver.Chrome()
    driver.maximize_window()
    
    try:
        print("[{}] Starting the Community Gallery Image Upload test...".format(time.strftime("%Y-%m-%d %H:%M:%S")))
        
        # Login as community admin
        driver.get("http://127.0.0.1:8000/login/")
        email_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "signin-email"))
        )
        email_input.send_keys("sarinrajesh2025@mca.ajce.in")
        
        password_input = driver.find_element(By.ID, "signin-password")
        password_input.send_keys("sarin@123")
        
        login_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Sign In')]")
        login_button.click()
        print("[{}] Logged in as community admin.".format(time.strftime("%Y-%m-%d %H:%M:%S")))
        
        # Navigate to community management page
        driver.get("http://127.0.0.1:8000/community/manage")
        print("[{}] Navigated to community management page.".format(time.strftime("%Y-%m-%d %H:%M:%S")))
        
        # Click on gallery management section
        gallery_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "gallery-tab"))
        )
        gallery_tab.click()
        print("[{}] Opened gallery management section.".format(time.strftime("%Y-%m-%d %H:%M:%S")))
        
        # Click add image button
        add_image_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "add-gallery-image"))
        )
        add_image_button.click()
        print("[{}] Clicked add image button.".format(time.strftime("%Y-%m-%d %H:%M:%S")))
        
        # Fill in image details
        image_title = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "image-title"))
        )
        test_title = f"Test Gallery Image - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        image_title.send_keys(test_title)
        
        image_description = driver.find_element(By.ID, "image-description")
        image_description.send_keys("This is a test gallery image uploaded via Selenium automated testing.")
        
        # Upload test image
        image_input = driver.find_element(By.ID, "gallery-image")
        image_path = "D:\\Main Project\\evocom\\static\\img\\test-gallery.jpg"  # Adjust path as needed
        image_input.send_keys(image_path)
        print("[{}] Filled in image details and selected file.".format(time.strftime("%Y-%m-%d %H:%M:%S")))
        
        # Submit the form
        submit_button = driver.find_element(By.ID, "submit-gallery-image")
        submit_button.click()
        print("[{}] Submitted the gallery image.".format(time.strftime("%Y-%m-%d %H:%M:%S")))
        
        # Wait for success message
        success_message = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "success-message"))
        )
        print("[{}] Gallery image uploaded successfully!".format(time.strftime("%Y-%m-%d %H:%M:%S")))
        
        # Verify image appears in gallery
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.xpath, f"//img[@alt='{test_title}']"))
        )
        print("[{}] Image verified in gallery.".format(time.strftime("%Y-%m-%d %H:%M:%S")))
        
    except Exception as e:
        print("[{}] Error occurred: {}".format(time.strftime("%Y-%m-%d %H:%M:%S"), str(e)))
        raise e
        
    finally:
        driver.quit()
        print("[{}] Browser closed. Test completed.".format(time.strftime("%Y-%m-%d %H:%M:%S")))

if __name__ == "__main__":
    test_community_gallery_upload()