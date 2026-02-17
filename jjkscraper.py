import os
import sys
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
MAX_WORKERS = 10 

def get_driver():
    options = uc.ChromeOptions()
    options.add_argument("--headless")
    return uc.Chrome(options=options, browser_executable_path=CHROME_PATH)

def download_image(url, session):
    try:
        r = session.get(url, timeout=10)
        return r.content if r.status_code == 200 else None
    except:
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
        
        # Fast scroll
        h = driver.execute_script("return document.body.scrollHeight")
        for i in range(1, h, 2000):
            driver.execute_script(f"window.scrollTo(0, {i});")
            time.sleep(0.3)

        img_elements = driver.find_elements(By.CSS_SELECTOR, "img")
        urls = [img.get_attribute("src") for img in img_elements if img.get_attribute("src") and any(x in img.get_attribute("src") for x in ["content", "uploads", "img"])]

        if urls:
            with requests.Session() as s:
                s.headers.update({'User-Agent': 'Mozilla/5.0'})
                with ThreadPoolExecutor(max_workers=MAX_WORKERS) as exe:
                    results = list(exe.map(lambda u: download_image(u, s), urls))
                    images_data = [r for r in results if r]
            
            if images_data:
                with open(filename, "wb") as f:
                    f.write(img2pdf.convert(images_data))
                print(f"[SUCCESS] {chapter_name}")
    finally:
        driver.quit()

def parse_selection(chapters_list, user_input):
    """Handles the 34, 34:60, and 34:: logic"""
    # Sort chapters so indexing matches series order (Chapter 1, 2, 3...)
    # Assumes the site link contains the number, e.g., 'chapter-34'
    chapters_list.sort(key=lambda x: float(''.join(filter(lambda c: c.isdigit() or c=='.', x[0].split('chapter-')[-1].split('/')[0]))))
    
    # Extract just the numbers for comparison
    nums = [float(''.join(filter(lambda c: c.isdigit() or c=='.', c[0].split('chapter-')[-1].split('/')[0]))) for c in chapters_list]

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
    manga_url = "https://read-jjk.com/"
    
    print("Indexing series structure...")
    driver = get_driver()
    driver.get(manga_url)
    links = driver.find_elements(By.TAG_NAME, "a")
    all_chapters = list(dict.fromkeys([(l.get_attribute("href"), l.text.strip()) for l in links if l.get_attribute("href") and "chapter-" in l.get_attribute("href")]))
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