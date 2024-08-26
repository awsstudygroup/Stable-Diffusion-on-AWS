import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# Define the URLs
urls = [
    "https://khatra.com.vn/gach-lat-nen/",
    "https://khatra.com.vn/gach-op-tuong/",
    "https://khatra.com.vn/gach-trang-tri/",
    "https://khatra.com.vn/gach-gia-go/",
    "https://khatra.com.vn/tiles/gach-terrazzo/",
    "https://khatra.com.vn/gach-trang-tri/the/",
    "https://khatra.com.vn/gach-trang-tri/gach-bong/",
    "https://khatra.com.vn/lib/"
]

# Function to download images from a URL
def download_images(url, folder_name):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    images = soup.find_all('img')

    # Create folder if it doesn't exist
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    for index, img in enumerate(images):
        img_url = img.get('src')
        if img_url:
            # Handle relative URLs
            if not img_url.startswith('http'):
                img_url = url + img_url
            try:
                img_data = requests.get(img_url).content
                img_name = os.path.join(folder_name, f'image_{index+1}.jpg')
                with open(img_name, 'wb') as handler:
                    handler.write(img_data)
                print(f"Downloaded {img_name}")
            except Exception as e:
                print(f"Failed to download {img_url}: {e}")

# Main loop to process each URL
for url in urls:
    parsed_url = urlparse(url)
    folder_name = parsed_url.path.strip('/').replace('/', '_')
    print(f"Processing {url} into folder {folder_name}")
    download_images(url, folder_name)
