"""Script"""

import os
import argparse

from pathlib import Path
from dotenv import load_dotenv

from mtlockyer.main import create_web_driver, login
from mtlockyer.main import (
    go_to_waitlist,
    get_latest_waitlist_posn,
    compare_waitlist_posns,
)
from mtlockyer.constants import LOGIN_URL, CHROME_OPTIONS

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
    driver = create_web_driver(CHROME_PATH, CHROME_OPTIONS)
    _ = login(LOGIN_URL, UN, PW, driver)
    driver = go_to_waitlist(STUDENTID, driver)
    wl_posn = get_latest_waitlist_posn(driver.page_source)
    print(f"wl_posn: {wl_posn}")

    has_changed = compare_waitlist_posns(fp, wl_posn)
    print(f"has_change: {has_changed}")

    driver.quit()


def lambda_handler(event, context):
    """
    Function for AWS Lambda microservice
    """
    fp = event.get("filepath", "./wl_posn.json")
    main(fp)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Example script to run waitlist checker"
    )
    parser.add_argument("filepath", type=str, help="The name of the file to process")

    args = parser.parse_args()

    main(args.filepath)
