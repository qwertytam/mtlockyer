"""Script"""

import os
import argparse

from pathlib import Path
from dotenv import load_dotenv

from src.main import initialise_driver, login
from src.main import (
    go_to_waitlist,
    get_latest_waitlist_posn,
    compare_waitlist_posns,
)

from src.main import URLConstants

load_dotenv()

UN = f"{os.getenv('UN')}"
PW = f"{os.getenv('PW')}"
STUDENTID = f"{os.getenv('STUDENTID')}"
SMSNUM = os.getenv("SMSNUM")
CHROME_PATH = f"{os.getenv('CHROME_PATH')}"


def main(fp: Path):
    """
    Main script
    """
    driver = initialise_driver(
        executable_path=None,
        service_log_path=None,
        options=[
            "--headless",
            "start-maximized",
            "--disable-blink-features",
            "--disable-blink-features=AutomationControlled",
        ],
    )
    _ = login(URLConstants.LOGIN_URL.value, UN, PW, driver)
    driver = go_to_waitlist(STUDENTID, driver)
    wl_posn = get_latest_waitlist_posn(driver.page_source)
    print(f"wl_posn: {wl_posn}")

    has_changed = compare_waitlist_posns(wl_posn, file_path=fp)
    print(f"has_changed: {has_changed}")

    driver.quit()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Example script to run waitlist checker"
    )
    parser.add_argument("filepath", type=str, help="The name of the file to process")

    args = parser.parse_args()

    main(args.filepath)
