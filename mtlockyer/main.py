"""Main module"""

import logging
import logging.config
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
import yaml

# Set up logging
mpath = Path(__file__).parent.absolute()
with open(mpath / "logging.yaml", "rt", encoding="utf8") as f:
    config = yaml.safe_load(f.read())
    f.close()
logging.config.dictConfig(config)

APP_NAME = "mtlockyer"
logger = logging.getLogger(APP_NAME)

BASE_URL = "https://myschools.nyc/en/dashboard/"
WAITLIST_PAGE = "waitlists/"


# Selenium chrome web driver
DEFAULT_CHROME_PATH = "/Applications/Chromium.app/Contents/MacOS/Chromium"

CHROME_OPTIONS = [
    "--headless",
    "start-maximized",
    "--disable-blink-features",
    "--disable-blink-features=AutomationControlled",
]

chrome_path = DEFAULT_CHROME_PATH
chrome_args = CHROME_OPTIONS

# Set options to use Chromium with Selenium
wbd_options = webdriver.ChromeOptions()
wbd_options.binary_location = chrome_path
for arg in chrome_args:
    wbd_options.add_argument(arg)
web_driver = webdriver.Chrome(options=wbd_options)


def _check_logged_in(wbd_wait) -> bool:
    logged_in = False
    try:
        wbd_wait.until(
            EC.element_to_be_clickable(
                (
                    By.CLASS_NAME,
                    "basic-card__title__school_name",
                )
            )
        )
        logger.info("Found 'My Account'; assumed login successful")
        logged_in = True
    except TimeoutException:
        logger.error("TimeoutException: Assuming wrong credentials; exiting")
    return logged_in


def login(url: str, un: str, pw: str, timeout: int = 5, driver=web_driver) -> bool:
    """
    Login in selenium browser

    Args:
        url: Login url
        un: Username to use to login
        pw: Password to use to login

    Returns
        True if logged in successfully, otherwise False
    """

    logger.info("Start login")
    driver.get(url)

    wbd_wait = WebDriverWait(driver, timeout)
    wbd_wait.until(EC.element_to_be_clickable((By.ID, "id_username"))).send_keys(un)
    logger.debug("Entered Username")

    wbd_wait.until(EC.element_to_be_clickable((By.ID, "id_password"))).send_keys(pw)
    logger.debug("Entered Password")

    wbd_wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, ".//button[@class='button' and @type='submit']")
        )
    ).click()
    logger.info("Entered login credentials")

    return _check_logged_in(wbd_wait)
