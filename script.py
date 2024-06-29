"""Script"""

# import sys
import os
from dotenv import load_dotenv

# from pathlib import Path
from mtlockyer.main import login


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

login(LOGIN_URL, UN, PW)
