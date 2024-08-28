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

# Function to download images from a specific section
def download_images_from_section(soup, section_selector, folder_name, image_prefix=None):
    section = soup.select_one(section_selector)
    if not section:
        print(f"No section found for selector: {section_selector}")
        return

    images = section.find_all('img')

    for index, img in enumerate(images):
        img_url = img.get('src')

        if img_url:
            # Handle relative URLs
            if not img_url.startswith('http'):
                img_url = url + img_url

            # Determine image extension
            img_ext = os.path.splitext(img_url)[1]
            if not img_ext:
                img_ext = '.jpg'  # Default to .jpg if no extension found

            # Create image name
            if image_prefix:
                img_name = f"{image_prefix}_{index + 1}{img_ext}"
            else:
                img_name_tag = section.find('div', class_='product-item-text')
                if img_name_tag:
                    img_name = f"{img_name_tag.text.strip().replace(' ', '_')}{img_ext}"
                else:
                    img_name = f"image_{index + 1}{img_ext}"  # Fallback in case no name is found

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
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    parsed_url = urlparse(url)
    folder_name = parsed_url.path.strip('/')
    
    # Create folder if it doesn't exist
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    print(f"Processing {url} into folder {folder_name}")
    
    # Download images from the first section
    download_images_from_section(
        soup,
        'body > main > section.product-details-info > div > div > div.col-12.col-md-9 > div > div.col-12.col-xl-8.info-group.mt-4 > div.post-details-content',
        folder_name,
        image_prefix='kientruc'
    )
