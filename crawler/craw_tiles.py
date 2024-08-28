import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# Define the URLs
urls = [
    "https://dongtam.com.vn/san-pham/gach-men-granite/bst-hoang-lien-son/",
    # "https://dongtam.com.vn/?post_type=dt_product&p=19334",
    "https://dongtam.com.vn/san-pham/gach-men-granite/bo-suu-tap-cararas/",
    "https://dongtam.com.vn/san-pham/gach-men-granite/bst-gecko/",
    "https://dongtam.com.vn/san-pham/gach-men-granite/bst-ly-son/",
    "https://dongtam.com.vn/san-pham/gach-men-granite/bst-6060tamdao/",
    "https://dongtam.com.vn/san-pham/gach-men-granite/bst-deluxe/",
    "https://dongtam.com.vn/san-pham/gach-men-granite/bst-dong-van/",
    "https://dongtam.com.vn/san-pham/gach-men-granite/bst-gach-100x100/",
    "https://dongtam.com.vn/san-pham/gach-men-granite/bst-vam-co-dong/",
    "https://dongtam.com.vn/san-pham/gach-men-granite/bst-nile/",
    "https://dongtam.com.vn/san-pham/gach-men-granite/bo-suu-tap-amber/",
    "https://dongtam.com.vn/san-pham/gach-men-granite/bo-suu-tap-gach-ceramic-cloud/",
    "https://dongtam.com.vn/san-pham/gach-men-granite/bst-lanbiang/",
    "https://dongtam.com.vn/san-pham/gach-men-granite/bst-4080sapa/",
    "https://dongtam.com.vn/san-pham/gach-men-granite/3060gecko001/",
    "https://dongtam.com.vn/san-pham/gach-men-granite/bo-suu-tap-gach-porcelain-thien-thach/",
    "https://dongtam.com.vn/san-pham/gach-men-granite/bst-3060thachdong/",
    "https://dongtam.com.vn/san-pham/gach-men-granite/bo-suu-tap-roxy/",
    "https://dongtam.com.vn/san-pham/gach-men-granite/bst-platinum/",
    # "https://dongtam.com.vn/?post_type=dt_product&p=19548",
    "https://dongtam.com.vn/san-pham/gach-men-granite/bst-vam-co-tay/",
    "https://dongtam.com.vn/san-pham/gach-men-granite/bst-gach-van-go/",
    "https://dongtam.com.vn/san-pham/gach-men-granite/bst-moment/",
    "https://dongtam.com.vn/san-pham/gach-men-granite/bst-marina-2/",
    "https://dongtam.com.vn/san-pham/gach-men-granite/bst-banyan/",
    "https://dongtam.com.vn/san-pham/gach-men-granite/bo-suu-tap-mosaic/",
    "https://dongtam.com.vn/san-pham/gach-men-granite/bst-db-nano/",
    "https://dongtam.com.vn/san-pham/gach-men-granite/bo-suu-tap-1530diamond/",
    "https://dongtam.com.vn/san-pham/gach-men-granite/bst-marble/",
    # "https://dongtam.com.vn/?post_type=dt_product&p=20462",
    "https://dongtam.com.vn/san-pham/gach-men-granite/bst-6060-victoria/",
    "https://dongtam.com.vn/san-pham/gach-men-granite/bst-trang-an/",
    # "https://dongtam.com.vn/?post_type=dt_product&p=20407",
    "https://dongtam.com.vn/san-pham/gach-men-granite/bo-suu-tap-victoria/",
    "https://dongtam.com.vn/san-pham/gach-men-granite/bo-suu-tap-art/",
    "https://dongtam.com.vn/san-pham/gach-men-granite/bst-van-da/",
    "https://dongtam.com.vn/san-pham/gach-men-granite/bst-1020rock/",
    "https://dongtam.com.vn/san-pham/gach-men-granite/bst-fame/",
    "https://dongtam.com.vn/san-pham/gach-men-granite/bst-san-vuon-greenery/",
    "https://dongtam.com.vn/san-pham/gach-men-granite/bo-suu-tap-regal/",
    "https://dongtam.com.vn/san-pham/gach-men-granite/bst-pharaon/",
    "https://dongtam.com.vn/san-pham/gach-bong/gach-bong-hoa-van-don-gian/",
    "https://dongtam.com.vn/san-pham/gach-bong/gach-bong-vien/",
    "https://dongtam.com.vn/san-pham/gach-bong/gach-bong-da-sac/",
    "https://dongtam.com.vn/san-pham/gach-bong/gach-bong-luc-giac/",
    "https://dongtam.com.vn/san-pham/gach-bong/gach-bong-dau-an-6/"
]

# Function to download images from a URL
def download_images(url, folder_name):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Get all <a> elements containing images and names
    links = soup.find_all('a', href=True)
    
    # Create folder if it doesn't exist
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    for link in links:
        # Skip links that don't contain the required structure
        if not link.find('div', class_='new-post custom-new-post'):
            continue

        # Extract the product name
        product_name_tag = link.find('div', class_='product-item-text')
        if product_name_tag:
            product_name = product_name_tag.text.strip().replace(' ', '_')
        else:
            continue

        # Extract the image
        images = link.find_all('img')
        for img in images:
            img_url = img.get('src')

            # Skip images inside <div class="overlay">
            if img.find_parent('div', class_='overlay'):
                continue

            if img_url:
                # Handle relative URLs
                if not img_url.startswith('http'):
                    img_url = url + img_url

                # Create the image file name
                img_name = f"{product_name}.jpg"
                img_name = os.path.join(folder_name, img_name)

                try:
                    img_data = requests.get(img_url).content
                    with open(img_name, 'wb') as handler:
                        handler.write(img_data)
                    print(f"Downloaded {img_name}")
                except Exception as e:
                    print(f"Failed to download {img_url}: {e}")

# Main loop to process each URL
for url in urls:
    parsed_url = urlparse(url)
    folder_name = parsed_url.path.strip('/')
    print(f"Processing {url} into folder {folder_name}")
    download_images(url, folder_name)
