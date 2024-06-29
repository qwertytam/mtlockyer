"""Main module"""

import json
import logging
import logging.config
from datetime import datetime as dt
from datetime import timezone as tz
from pathlib import Path

import yaml
from bs4 import BeautifulSoup as bs
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from mtlockyer.constants import (
    BASE_URL,
    DT_FORMAT,
    WAITLIST_PAGE,
    DEFAULT_WL_DICT,
)

# Set up logging
mpath = Path(__file__).parent.absolute()
with open(mpath / "logging.yaml", "rt", encoding="utf8") as f:
    config = yaml.safe_load(f.read())
    f.close()
logging.config.dictConfig(config)

APP_NAME = "mtlockyer"
logger = logging.getLogger(APP_NAME)


def create_web_driver(chrome_path: str, chrome_options: list):
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
        logger.info("basic-card; assumed login successful")
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


def go_to_waitlist(
    student_id: str, driver: webdriver.Chrome, timeout: int = 5
) -> webdriver.Chrome:
    """
    Go to page with waitlist information for given student id

    Args:
        student_id: Student ID
        driver: Selenium web driver
        timeout: Time to wait for website response

    Returns
        Driver on waitlist page
    """
    url = BASE_URL + student_id + "/" + WAITLIST_PAGE
    driver.get(url)
    wbd_wait = WebDriverWait(driver, timeout)
    wbd_wait.until(EC.element_to_be_clickable((By.ID, "main-nav-search")))
    wbd_wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))

    return driver


def get_latest_waitlist_posn(html_content: str) -> str:
    """
    Get waitlist position on page

    Args:
        html_content: html parge to parse for waitlist position

    Returns
        Waitlist position
    """
    soup = bs(html_content, "html.parser")
    el = soup.find_all(string=lambda text: "WAITLIST POSITION:" in text, limit=1)
    return el[0].parent.b.contents[0]


def save_waitlist_posn(posn: str, wl_date: str, last_update: str, file_path: Path):
    """
    Save waitlist position to json file

    Args:
        posn: Waitlist position
        wl_date: Datetime that waitlist last changed
        last_update: Datetime that last checked waitlist position
        file_path: File path and name to save information to

    Returns
        Waitlist position
    """

    wl_dict = {
        "waitlist_datetime": wl_date,
        "last_updated": last_update,
        "waitlist_position": posn,
    }
    logger.debug("Saving waitlist position to '%s'", file_path)
    with open(file_path, "w", encoding="utf8") as json_file:
        json.dump(wl_dict, json_file, indent=4)


def get_saved_waitlist_data(file_path: Path) -> dict:
    """
    Get saved waitlist information from file

    Args:
        file_path: File path to get information from

    Returns
        Dictionary of waitlist information
    """
    try:
        with open(file_path, "r", encoding="utf-8") as json_file:
            wl_dict = json.load(json_file)
    except FileNotFoundError:
        logger.info("File not found; returning default wl dictionary")
        wl_dict = DEFAULT_WL_DICT
        dt_now = dt.now().astimezone(tz.utc).strftime(DT_FORMAT)
        wl_dict["waitlist_datetime"] = dt_now
        wl_dict["last_updated"] = dt_now

    return wl_dict


def get_saved_waitlist_posn(wl_dict: dict) -> str:
    """
    Get saved waitlist position from waitlist dictionary

    Args:
        wl_dict: Waitlist dictionary to get position from

    Returns
        Waitlist position
    """
    return wl_dict["waitlist_position"]


def get_saved_waitlist_datetime(wl_dict: dict) -> dt:
    """
    Get datetime from when the waitlist position last changed

    Args:
        wl_dict: Waitlist dictionary to get position from

    Returns
        Waitlist change datetime
    """
    return dt.strptime(wl_dict["waitlist_datetime"], DT_FORMAT)


def get_saved_waitlist_last_update(wl_dict: dict) -> dt:
    """
    Get datetime from when the waitlist position was last checked

    Args:
        wl_dict: Waitlist dictionary to get position from

    Returns
        Waitlist last check datetime
    """
    return dt.strptime(wl_dict["last_updated"], DT_FORMAT)


def compare_waitlist_posns(file_path: Path, posn: str) -> bool:
    """
    Check if waitlist position has changed; if changed, updates json file
    that contains waitlist information

    Args:
        file_path: File path to json file that has the previous waitlist data
        posn: Most recent waitlist position from live web page

    Returns
        True if waitlist position has changed
    """
    has_changed = False

    wl_data = get_saved_waitlist_data(file_path)
    wl_posn = get_saved_waitlist_posn(wl_data)

    logger.debug("posn: %s, wl_posn: %s", posn, wl_posn)
    if int(posn) != int(wl_posn):
        has_changed = True

    logger.debug("has_changed: %s", has_changed)
    dt_now = dt.now().astimezone(tz.utc).strftime(DT_FORMAT)
    if has_changed:
        save_waitlist_posn(posn, dt_now, dt_now, file_path)
    else:
        existing_date = get_saved_waitlist_datetime(wl_data).strftime(DT_FORMAT)
        save_waitlist_posn(wl_posn, existing_date, dt_now, file_path)

    return has_changed
