JJK Scraper README
Setup: Arch Linux + google-chrome (AUR).

Install: pip install undetected-chromedriver selenium requests img2pdf setuptools

Usage:

python jjkscraper.py 34 — Download Chapter 34.

python jjkscraper.py 34:60 — Download Range 34 to 60.

python jjkscraper.py 34:: — Download Chapter 34 to latest.

Features:

Parallel Downloads: Multithreaded image grabbing for speed.

Anti-Bot: Uses undetected-chromedriver to bypass Cloudflare.

Smart Skip: Skips existing PDFs in ./JJK_Manga_Library/.

Py 3.14 Fix: Handles distutils removal via setuptools patch.

Headless: Runs in background without opening browser windows.

Note: Ensure CHROME_PATH in script is /usr/bin/google-chrome-stable.