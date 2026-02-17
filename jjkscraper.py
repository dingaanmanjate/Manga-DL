import os
import time
import requests
import img2pdf
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
MAX_WORKERS = 20  # Number of simultaneous image downloads

def get_driver():
    options = uc.ChromeOptions()
    options.add_argument("--headless")
    driver = uc.Chrome(options=options, browser_executable_path=CHROME_PATH)
    return driver

def download_image(url, session):
    """Helper for multithreaded downloading"""
    try:
        r = session.get(url, timeout=10)
        if r.status_code == 200:
            return r.content
    except Exception:
        return None

def download_chapter(url, chapter_name):
    if not os.path.exists(SAVE_FOLDER):
        os.makedirs(SAVE_FOLDER)
    
    filename = os.path.join(SAVE_FOLDER, f"{chapter_name}.pdf")
    
    # AVOID REDOWNLOADING
    if os.path.exists(filename):
        print(f"[-] Skipping: {chapter_name} (Already exists)")
        return

    print(f"[+] Starting: {chapter_name}")
    driver = get_driver()
    try:
        driver.get(url)
        # Wait for content to exist
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        # Faster dynamic scroll
        last_height = driver.execute_script("return document.body.scrollHeight")
        for i in range(1, last_height, 2000):
            driver.execute_script(f"window.scrollTo(0, {i});")
            time.sleep(0.3)

        img_elements = driver.find_elements(By.CSS_SELECTOR, "img")
        urls = []
        for img in img_elements:
            src = img.get_attribute("src")
            if src and any(x in src for x in ["content", "uploads", "img"]):
                urls.append(src)

        if not urls:
            print(f"[!] No images found for {chapter_name}")
            return

        print(f"[*] Downloading {len(urls)} images in parallel...")
        
        # Multithreaded downloading
        images_data = []
        with requests.Session() as session:
            session.headers.update({'User-Agent': 'Mozilla/5.0'})
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                results = list(executor.map(lambda u: download_image(u, session), urls))
                images_data = [r for r in results if r is not None]

        if images_data:
            with open(filename, "wb") as f:
                f.write(img2pdf.convert(images_data))
            print(f"[SUCCESS] Saved: {filename}")
    except Exception as e:
        print(f"[ERROR] Failed {chapter_name}: {e}")
    finally:
        driver.quit()

def main():
    manga_url = "https://read-jjk.com/"
    print(f"Connecting to {manga_url} and indexing chapters...")
    
    driver = get_driver()
    try:
        driver.get(manga_url)
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "a")))
        
        links = driver.find_elements(By.TAG_NAME, "a")
        chapters = []
        for link in links:
            href = link.get_attribute("href")
            text = link.text.strip()
            if href and "chapter-" in href and "read-jjk.com" in href:
                chapters.append((href, text))
        
        chapters = list(dict.fromkeys(chapters))
        driver.quit()
        
        print(f"Found {len(chapters)} chapters total.")
        
        # Process in reverse order (oldest to newest)
        for url, title in reversed(chapters):
            clean_name = title.replace(" ", "_").replace("/", "-")
            download_chapter(url, clean_name)

    except Exception as e:
        print(f"Main Error: {e}")
        if 'driver' in locals(): driver.quit()

if __name__ == "__main__":
    main()