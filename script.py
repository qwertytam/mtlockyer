"""Script"""

# import sys
import os
from dotenv import load_dotenv

# from pathlib import Path
from mtlockyer.main import login, go_to_waitlist


# mpath = Path(__file__).parent.parent.absolute() / "src"

# print(mpath)
# sys.path.append(mpath)
# from main import login

load_dotenv()

UN = os.getenv("UN")
PW = os.getenv("PW")
STUDENTID = os.getenv("STUDENTID")
SMSNUM = os.getenv("SMSNUM")

LOGIN_URL = "https://myschools.nyc/en/account/log-in/"
BASE_URL = "https://myschools.nyc/en/dashboard/"
WAITLIST_PAGE = "waitlists/"


login(LOGIN_URL, UN, PW)

url = BASE_URL + STUDENTID + "/" + WAITLIST_PAGE
go_to_waitlist(url)
