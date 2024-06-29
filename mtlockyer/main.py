"""Main module"""

import logging
import logging.config
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup as bs
import re
import yaml

from mtlockyer.constants import DEFAULT_CHROME_PATH, CHROME_OPTIONS
from mtlockyer.constants import BASE_URL, WAITLIST_PAGE

# Set up logging
mpath = Path(__file__).parent.absolute()
with open(mpath / "logging.yaml", "rt", encoding="utf8") as f:
    config = yaml.safe_load(f.read())
    f.close()
logging.config.dictConfig(config)

APP_NAME = "mtlockyer"
logger = logging.getLogger(APP_NAME)


def create_web_driver(chrome_path=DEFAULT_CHROME_PATH, chrome_options=CHROME_OPTIONS):
    """
    Set options to use Chromium with Selenium

    Args:
        chrome_path: Path to chrome binary
        chrome_options: Options to use

    Returns
        Web driver
    """
    options = webdriver.ChromeOptions()
    options.binary_location = chrome_path
    for arg in chrome_options:
        options.add_argument(arg)
    driver = webdriver.Chrome(options=options)

    return driver


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


def login(url: str, un: str, pw: str, driver, timeout: int = 5) -> bool:
    """
    Login in selenium browser

    Args:
        url: Login url
        un: Username to use to login
        pw: Password to use to login
        driver: Selenium web driver
        timeout: Time to wait for website response

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

    logged_in = _check_logged_in(wbd_wait)

    return logged_in


def go_to_waitlist(student_id: str, driver, timeout: int = 5):
    """
    ...
    """
    url = BASE_URL + student_id + "/" + WAITLIST_PAGE
    driver.get(url)
    wbd_wait = WebDriverWait(driver, timeout)
    wbd_wait.until(EC.element_to_be_clickable((By.ID, "main-nav-search")))
    logger.info("wait 1")
    wbd_wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
    logger.info("wait 2")

    # print(driver.page_source)

    return driver


def _string_in_tag(search_string: str, tag) -> bool:
    logger.info(f"tag.string: {tag.string}")
    logger.info(f"search_string: {search_string}")
    return tag.string == search_string


def get_latest_waitlist_posn(html_content: str) -> int:
    """
    ...
    """
    soup = bs(html_content, "html.parser")
    el = soup.find_all(string=lambda text: "WAITLIST POSITION:" in text, limit=1)
    return el[0].parent.b.contents[0]
