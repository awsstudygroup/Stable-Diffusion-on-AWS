from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Setup Selenium WebDriver (ensure you have the correct path to your ChromeDriver)
chrome_options = Options()
chrome_options.add_argument("--headless")  # Run in headless mode (optional)
driver = webdriver.Chrome(options=chrome_options)

# URL of the page to crawl
# url = 'https://dongtam.com.vn/danh-muc-san-pham/gach-men-granite/'  # Replace with your actual URL
url = 'https://dongtam.com.vn/danh-muc-san-pham/gach-bong/'  # Replace with your actual URL

# Open the page
driver.get(url)

# Initialize an empty list to store the links
all_links = set()

# Function to extract links from the specified element
def extract_links():
    product_items = driver.find_elements(By.CSS_SELECTOR, "body > main > section.product-collection > div > div.product-item-info.row a")
    for item in product_items:
        link = item.get_attribute('href')
        if link:
            all_links.add(link)

# Click the "Load More" button until no more new content is loaded
while True:
    extract_links()  # Extract links on the current page
    
    try:
        # Wait until the "Load More" button is clickable and click it
        load_more_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.load-more[data-type='products']"))
        )
        load_more_button.click()
        
        # Wait a little for new content to load
        time.sleep(5)
    except Exception as e:
        # If there is no "Load More" button or it fails to load, break the loop
        print(f"Stopped clicking 'Load More' due to: {e}")
        break

# Extract links one last time after the final "Load More" click
extract_links()

# Extract the filename from the URL path
url_path = url.rstrip('/').split('/')[-1]
filename = f"{url_path}_links.txt"

# Output the collected links
with open(filename, 'w') as file:
    for link in all_links:
        file.write(f'\"{link}\",\n')

# Close the WebDriver
driver.quit()
