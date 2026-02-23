import os
import sys
import time
import requests
import img2pdf
from PIL import Image
import io
from concurrent.futures import ThreadPoolExecutor

# --- FIX FOR PYTHON 3.12+ distutils ERROR ---
try:
    import distutils.version
except ImportError:
    import setuptools 
# --------------------------------------------

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# SETTINGS
SAVE_FOLDER = "JJK_Manga_Library"
CHROME_PATH = "/usr/bin/google-chrome-stable"
MAX_WORKERS = 10 

def get_driver():
    options = uc.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return uc.Chrome(options=options, browser_executable_path=CHROME_PATH)

def download_image(url, session):
    try:
        r = session.get(url, timeout=15)
        if r.status_code == 200:
            # Convert to RGB to remove alpha channel for img2pdf compatibility
            img = Image.open(io.BytesIO(r.content))
            if img.mode in ("RGBA", "P", "LA"):
                img = img.convert("RGB")
            
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG')
            return img_byte_arr.getvalue()
        return None
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return None

def download_chapter(url, chapter_name):
    if not os.path.exists(SAVE_FOLDER): os.makedirs(SAVE_FOLDER)
    filename = os.path.join(SAVE_FOLDER, f"{chapter_name}.pdf")
    
    # Check if exists before even starting driver
    if os.path.exists(filename):
        print(f"[-] Skipping: {chapter_name} (Exists)")
        return

    print(f"[+] Downloading: {chapter_name}")
    driver = get_driver()
    try:
        driver.get(url)
        time.sleep(5)
        
        # Fast scroll to trigger lazy loading
        h = driver.execute_script("return document.body.scrollHeight")
        for i in range(1, h, 2000):
            driver.execute_script(f"window.scrollTo(0, {i});")
            time.sleep(0.5)

        img_elements = driver.find_elements(By.CSS_SELECTOR, ".wp-manga-chapter-img")
        urls = [img.get_attribute("src") for img in img_elements if img.get_attribute("src")]

        if not urls:
            # Fallback for some chapters that might not use that class
            img_elements = driver.find_elements(By.CSS_SELECTOR, ".reading-content img")
            urls = [img.get_attribute("src") for img in img_elements if img.get_attribute("src")]

        if urls:
            print(f"Found {len(urls)} images.")
            with requests.Session() as s:
                s.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
                with ThreadPoolExecutor(max_workers=MAX_WORKERS) as exe:
                    results = list(exe.map(lambda u: download_image(u, s), urls))
                    images_data = [r for r in results if r]
            
            if images_data:
                with open(filename, "wb") as f:
                    f.write(img2pdf.convert(images_data))
                print(f"[SUCCESS] {chapter_name}")
            else:
                print(f"[FAILED] No image data retrieved for {chapter_name}")
        else:
            print(f"[FAILED] No images found for {chapter_name}")
    finally:
        driver.quit()

def parse_selection(chapters_list, user_input):
    """Handles the 34, 34:60, and 34:: logic"""
    # Sort chapters so indexing matches series order (Chapter 1, 2, 3...)
    # Extract number from the URL or title
    def get_num(c):
        url = c[0]
        try:
            # Try to get number from URL like .../chapter-205/
            part = url.split('chapter-')[-1].split('/')[0]
            return float(''.join(filter(lambda x: x.isdigit() or x=='.', part)))
        except:
            return 0.0

    chapters_list.sort(key=get_num)
    
    # Extract just the numbers for comparison
    nums = [get_num(c) for c in chapters_list]

    if "::" in user_input:
        start = float(user_input.replace("::", ""))
        return [c for i, c in enumerate(chapters_list) if nums[i] >= start]
    elif ":" in user_input:
        start, end = map(float, user_input.split(":"))
        return [c for i, c in enumerate(chapters_list) if start <= nums[i] <= end]
    else:
        target = float(user_input)
        return [c for i, c in enumerate(chapters_list) if nums[i] == target]

def main():
    if len(sys.argv) < 2:
        print("Usage:\n  python script.py 34\n  python script.py 34:60\n  python script.py 34::")
        return

    user_arg = sys.argv[1]
    manga_url = "https://www.mangaread.org/manga/jujutsu-kaisen/"
    
    print("Indexing series structure...")
    driver = get_driver()
    driver.get(manga_url)
    
    try:
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CLASS_NAME, "wp-manga-chapter")))
    except:
        print("Timeout waiting for chapters. Proceeding anyway.")

    links = driver.find_elements(By.CSS_SELECTOR, ".wp-manga-chapter a")
    all_chapters = []
    seen_urls = set()
    for l in links:
        url = l.get_attribute("href")
        title = l.text.strip()
        if url and url not in seen_urls:
            if not title:
                # If title is empty, try to get it from the URL
                title = url.split('/')[-2].replace('-', ' ').title()
            all_chapters.append((url, title))
            seen_urls.add(url)
    
    driver.quit()

    try:
        selected = parse_selection(all_chapters, user_arg)
        print(f"Queueing {len(selected)} chapters.")
        for url, title in selected:
            clean_name = title.replace(" ", "_").replace("/", "-")
            download_chapter(url, clean_name)
    except Exception as e:
        print(f"Input Error: Ensure you used numbers correctly. {e}")

if __name__ == "__main__":
    main()