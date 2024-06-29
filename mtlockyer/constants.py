"""Constants"""

# URLs
LOGIN_URL = "https://myschools.nyc/en/account/log-in/"
BASE_URL = "https://myschools.nyc/en/dashboard/"
WAITLIST_PAGE = "waitlists/"
DT_FORMAT = "%Y-%m-%d %H:%M:%S.%f %Z%z"

# Selenium Chrome webdriver options
CHROME_OPTIONS = [
    "--headless",
    "start-maximized",
    "--disable-blink-features",
    "--disable-blink-features=AutomationControlled",
]

# In case file not found
DEFAULT_WL_DICT = {
    "waitlist_datetime": None,
    "last_updated": None,
    "waitlist_position": -1,
}
