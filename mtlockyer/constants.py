"""Defaults"""

# Selenium chrome web driver
DEFAULT_CHROME_PATH = "/Applications/Chromium.app/Contents/MacOS/Chromium"

CHROME_OPTIONS = [
    "--headless",
    "start-maximized",
    "--disable-blink-features",
    "--disable-blink-features=AutomationControlled",
]

# URLs
LOGIN_URL = "https://myschools.nyc/en/account/log-in/"
BASE_URL = "https://myschools.nyc/en/dashboard/"
WAITLIST_PAGE = "waitlists/"
