"""Class to hold constants"""

from enum import Enum


class DateFormats(Enum):
    """For outputting datetimes as strings"""

    DEFAULT = "%Y-%m-%d %H:%M:%S.%f %Z%z"


class URLConstants(Enum):
    """ "Useful reference urls"""

    LOGIN_URL = "https://myschools.nyc/en/account/log-in/"
    BASE_URL = "https://myschools.nyc/en/dashboard/"
    WAITLIST_PAGE = "waitlists/"


class DataFileDictFormat(Enum):
    """To populate empty file"""

    DEFAULT_WL_DICT = {
        "waitlist_datetime": "",
        "last_updated": "",
        "waitlist_position": -1,
    }
