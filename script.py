"""Script"""

import os
from dotenv import load_dotenv

from mtlockyer.main import create_web_driver, login, go_to_waitlist, get_latest_waitlist_posn
from mtlockyer.constants import LOGIN_URL

load_dotenv()

UN = f"{os.getenv("UN")}"
PW = f"{os.getenv("PW")}"
STUDENTID = f"{os.getenv("STUDENTID")}"
SMSNUM = os.getenv("SMSNUM")

driver = create_web_driver()
logged_in = login(LOGIN_URL, UN, PW, driver)
driver = go_to_waitlist(STUDENTID, driver)
wl_posn = get_latest_waitlist_posn(driver.page_source)
print(f"wl_posn: {wl_posn}")
driver.quit()
