"""Main module"""

import logging
import json
from tempfile import mkdtemp
from datetime import datetime as dt
from datetime import timezone as tz
from enum import Enum
from pathlib import Path
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from bs4 import BeautifulSoup as bs

logger = logging.getLogger(__name__)


# Constant classes >>> move to seperate module when possible
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
        "waitlist_datetime": None,
        "last_updated": None,
        "waitlist_position": -1,
    }


class ObjClientExceptions(ClientError):
    """Encapsulates boto client exceptions"""


class ObjectWrapper:
    """Encapsulates S3 object actions"""

    def __init__(self, s3_object):
        """
        Args:
            s3_object: A Boto3 object resource
        """
        self.object = s3_object
        self.key = self.object.key

    def put(self, data):
        """
        Upload data to the object

        Args:
            data: The data (bytes or string) to upload. When this is a string,
            it is interpreted as a file name, which is  opened in read bytes
            mode.
        """
        put_data = data
        if isinstance(data, str):
            try:
                put_data = open(data, "rb")
            except IOError:
                logger.exception("Expected file name or binary data, got '%s'.", data)
                raise

        try:
            self.object.put(Body=put_data)
            self.object.wait_until_exists()
            print(
                f"Put object '{self.object.key}' to bucket '{self.object.bucket_name}'."
            )
        except ObjClientExceptions:
            logger.exception(
                "Couldn't put object '%s' to bucket '%s'.",
                self.object.key,
                self.object.bucket_name,
            )
            raise
        finally:
            if getattr(put_data, "close", None):
                put_data.close()

    def get(self):
        """
        Gets the object

        Return:
            The object data in bytes.
        """
        try:
            body = self.object.get()["Body"].read()
            print(
                "Got object '%s' from bucket '%s'.",
                self.object.key,
                self.object.bucket_name,
            )
        except ObjClientExceptions:
            logger.exception(
                "Couldn't get object '%s' from bucket '%s'.",
                self.object.key,
                self.object.bucket_name,
            )
            raise
        else:
            return body

    @staticmethod
    def list(bucket, prefix=None):
        """
        Lists the objects in a bucket, optionally filtered by a prefix.

        Args:
            bucket: The Boto3 bucket to query
            prefix: When specified, only objects that start with this prefix are
            listed.

        Return:
            The list of objects.
        """
        try:
            if not prefix:
                objects = list(bucket.objects.all())
            else:
                objects = list(bucket.objects.filter(Prefix=prefix))
            print(
                "Got objects %s from bucket '%s'", [o.key for o in objects], bucket.name
            )
        except ObjClientExceptions:
            logger.exception("Couldn't get objects for bucket '%s'.", bucket.name)
            raise
        else:
            return objects

    def delete(self):
        """
        Deletes the object
        """
        try:
            self.object.delete()
            self.object.wait_until_not_exists()
            print(
                "Deleted object '%s' from bucket '%s'.",
                self.object.key,
                self.object.bucket_name,
            )
        except ObjClientExceptions:
            logger.exception(
                "Couldn't delete object '%s' from bucket '%s'.",
                self.object.key,
                self.object.bucket_name,
            )
            raise

    @staticmethod
    def delete_objects(bucket, object_keys):
        """
        Removes a list of objects from a bucket. This operation is done as a
        batch in a single request.

        Args:
            bucket: The Boto3 bucket that contains the objects
            object_keys: The list of keys that identify the objects to remove
        Return:
            The response that contains data about which objects were and were
            not deleted
        """
        try:
            response = bucket.delete_objects(
                Delete={"Objects": [{"Key": key} for key in object_keys]}
            )
            if "Deleted" in response:
                print(
                    "Deleted objects '%s' from bucket '%s'.",
                    [del_obj["Key"] for del_obj in response["Deleted"]],
                    bucket.name,
                )
            if "Errors" in response:
                logger.warning(
                    "Could not delete objects '%s' from bucket '%s'.",
                    [
                        f"{del_obj['Key']}: {del_obj['Code']}"
                        for del_obj in response["Errors"]
                    ],
                    bucket.name,
                )
        except ObjClientExceptions:
            logger.exception("Couldn't delete any objects from bucket %s.", bucket.name)
            raise
        else:
            return response

    @staticmethod
    def empty_bucket(bucket):
        """
        Remove all objects from a bucket

        Args:
            bucket: The Boto3 bucket to empty
        """
        try:
            bucket.objects.delete()
            print("Emptied bucket '%s'.", bucket.name)
        except ObjClientExceptions:
            logger.exception("Couldn't empty bucket '%s'.", bucket.name)
            raise


def initialise_driver(
    binary_location="/opt/chrome/chrome-linux64/chrome",
    executable_path="/opt/chrome-driver/chromedriver-linux64/chromedriver",
    service_log_path="/tmp/chromedriver.log",
    options=None,
):
    """
    Initialise Chrome driver

    Args:
        binary_location: Location for chrome binary; default is for AWS Lambda
        executable_path: Location for chrome executable; default is for AWS Lambda
        service_log_path: Location for chrome service logs; default is for AWS Lambda

    Returns:
        Selenium Chrome web driver
    """
    print("Initialising driver")
    chrome_options = ChromeOptions()
    if options is None:
        print("Using default options")
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-dev-tools")
        chrome_options.add_argument("--no-zygote")
        chrome_options.add_argument("--single-process")
        chrome_options.add_argument(f"--user-data-dir={mkdtemp()}")
        chrome_options.add_argument(f"--data-path={mkdtemp()}")
        chrome_options.add_argument(f"--disk-cache-dir={mkdtemp()}")
        chrome_options.add_argument("--remote-debugging-pipe")
        chrome_options.add_argument("--verbose")
        chrome_options.add_argument("--log-path=/tmp")
        chrome_options.add_argument("--disable-software-rasterizer")
    else:
        print(f"Using passed options {options}")
        for option in options:
            chrome_options.add_argument(option)
    print("Finished adding options")

    chrome_options.binary_location = binary_location
    print("added binary location")

    if isinstance(service_log_path, str) and isinstance(executable_path, str):
        print("adding executable and serivce log path")
        service = Service(
            executable_path=executable_path,
            service_log_path=service_log_path,
        )
        print("calling webdriver.Chrome")
        driver = webdriver.Chrome(service=service, options=chrome_options)
    else:
        print("not adding service")
        print("calling webdriver.Chrome")
        driver = webdriver.Chrome(options=chrome_options)


    

    return driver


def send_email(sns_topic_arn, subject_text, body_text):
    """
    Send email using AWS SNS service

    Args:
        sns_topic_arn: AWS SNS Topic ARN to use
        subject_text: Email subject
        body_text: Email message body text

    Returns:
        response dictionary
    """

    sns_client = boto3.client("sns")
    response = sns_client.publish(
        TopicArn=sns_topic_arn,
        Subject=subject_text,
        Message=body_text,
    )

    print(f"Email sent with response: {response}")

    return {
        "statusCode": 200,
        "body": json.dumps(
            f"Email send success. MessageID is: '{response['MessageId']}'"
        ),
    }


def _check_logged_in(wbd_wait) -> bool:
    """
    Check if logged in

    Checks for presence of specific html class name in html

    Args:
        wbd_wait: Selenium WebDriverWait to check for logged in presence

    Returns:
        True if logged in, else false
    """
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
        # logger.info("basic-card; assumed login successful")
        print("basic-card; assumed login successful")
        logged_in = True
    except TimeoutException:
        # logger.error("TimeoutException: Assuming wrong credentials; exiting")
        print("TimeoutException: Assuming wrong credentials; exiting")
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

    # logger.info("Start login")
    print(f"Starting login: url '{url}' un '{un}' pw '{pw}'")
    print(f"types: url '{type(url)}' un '{type(un)}' pw '{type(pw)}'")
    driver.get(url)

    wbd_wait = WebDriverWait(driver, timeout)
    wbd_wait.until(EC.element_to_be_clickable((By.ID, "id_username"))).send_keys(un)
    # logger.debug("Entered Username")

    wbd_wait.until(EC.element_to_be_clickable((By.ID, "id_password"))).send_keys(pw)
    # logger.debug("Entered Password")

    wbd_wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, ".//button[@class='button' and @type='submit']")
        )
    ).click()
    # logger.info("Entered login credentials")
    print("Entered login credentials")

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
    url = (
        str(URLConstants.BASE_URL.value) + student_id + "/" + str(URLConstants.WAITLIST_PAGE.value)
    )
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


def __save_waitlist_to_file(wl_dict: dict, file_path: Path):
    with open(file_path, "w", encoding="utf8") as json_file:
        json.dump(wl_dict, json_file, indent=4)

    print(f"Have written '{wl_dict}' to '{file_path}")


def __save_waitlist_to_s3(wl_dict: dict, s3_bucket_object: dict):
    s3_resource = boto3.resource("s3")
    bucket = s3_resource.Bucket(s3_bucket_object["bucket"])
    obj_wrapper = ObjectWrapper(bucket.Object(s3_bucket_object["object_key"]))
    obj_wrapper.put(bytes(json.dumps(wl_dict, indent=4).encode(encoding="utf-8")))

    print(f"Have put '{wl_dict}' into object '{s3_bucket_object["object_key"]}'")


def save_waitlist_posn(
    posn: str,
    wl_date: str,
    last_update: str,
    file_path: Optional[Path]=None,
    s3_bucket_object: Optional[dict]=None,
):
    """
    Save waitlist position to json file

    If `file_path` is provided, then writes to file; else writes to AWS s3 bucket

    Args:
        posn: Waitlist position
        wl_date: Datetime that waitlist last changed
        last_update: Datetime that last checked waitlist position
        file_path: File path and name to save information to
        s3_bucket_object: AWS S3 bucket and object to save information to

        For s3_bucket_object, requires keys {'bucket': bucket, 'object_key': object_key}

    Returns
        Waitlist position
    """
    wl_dict = {
        "waitlist_datetime": wl_date,
        "last_updated": last_update,
        "waitlist_position": posn,
    }
    # logger.debug("Saving waitlist position to '%s'", file_path)
    if file_path is not None:
        print("Saving waitlist position to file")
        __save_waitlist_to_file(wl_dict, file_path)
    else:
        if s3_bucket_object is None:
            s3_bucket_object = {"bucket": "", "object_key": ""}
        print("Saving waitlist position to s3")
        __save_waitlist_to_s3(wl_dict, s3_bucket_object)


def __get_waitlist_from_file(file_path: Path) -> dict:
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
        # logger.info("File not found; returning default wl dictionary")
        print("File not found; returning default wl dictionary")
        wl_dict = DataFileDictFormat.DEFAULT_WL_DICT.value
        dt_now = dt.now().astimezone(tz.utc).strftime(str(DateFormats.DEFAULT.value))
        wl_dict["waitlist_datetime"] = dt_now
        wl_dict["last_updated"] = dt_now


    print(f"Found file '{file_path}'; returning data")
    return wl_dict


def __get_waitlist_from_s3(s3_bucket_object: dict) -> dict:
    s3_resource = boto3.resource("s3")
    bucket = s3_resource.Bucket(s3_bucket_object["bucket"])
    obj_wrapper = ObjectWrapper(bucket.Object(s3_bucket_object["object_key"]))
    wl_bytes = obj_wrapper.get()
    wl_dict = json.loads(wl_bytes.decode('utf8').replace("'", '"'))

    print(f"Found object '{s3_bucket_object}'; "
          f"returning data:\n{json.dumps(wl_dict, indent=4)}\nEND")
    return wl_dict


def get_saved_waitlist_data(
    file_path: Optional[Path]=None,
    s3_bucket_object: Optional[dict]=None) -> dict:
    """
    Get saved waitlist information from file or AWS S3 bucket object

    Args:
        file_path: File path to get information from
        s3_bucket_object: AWS S3 bucket and object to get information from

        For s3_bucket_object, requires keys {'bucket': bucket, 'object_key': object_key}

    Returns
        Dictionary of waitlist information
    """

    if file_path is not None:
        print("Getting waitlist position from file")
        wl_dict = __get_waitlist_from_file(file_path)
    else:
        if s3_bucket_object is None:
            s3_bucket_object = {"bucket": "", "object_key": ""}
        print("Getting waitlist position from s3")
        wl_dict = __get_waitlist_from_s3(s3_bucket_object)

    return wl_dict


def get_saved_waitlist_posn(wl_dict: dict) -> str:
    """
    Get saved waitlist position from waitlist dictionary

    Args:
        wl_dict: Waitlist dictionary to get position from

    Returns
        Waitlist position
    """
    print(f"wl_dict is type '{type(wl_dict)}' with string output:\n{wl_dict}")
    
    for k in wl_dict.keys():
        print(f"k: '{k}' v: '{wl_dict[k]}'")
    return wl_dict["waitlist_position"]


def get_saved_waitlist_datetime(wl_dict: dict) -> dt:
    """
    Get datetime from when the waitlist position last changed

    Args:
        wl_dict: Waitlist dictionary to get position from

    Returns
        Waitlist change datetime
    """
    return dt.strptime(wl_dict["waitlist_datetime"], str(DateFormats.DEFAULT.value))


def get_saved_waitlist_last_update(wl_dict: dict) -> dt:
    """
    Get datetime from when the waitlist position was last checked

    Args:
        wl_dict: Waitlist dictionary to get position from

    Returns
        Waitlist last check datetime
    """
    return dt.strptime(wl_dict["last_updated"], str(DateFormats.DEFAULT.value))


def compare_waitlist_posns(
    posn: str, file_path: Optional[Path]=None, s3_bucket_object: Optional[dict]=None) -> bool:
    """
    Check if waitlist position has changed; if changed, updates json file
    that contains waitlist information

    Args:
        posn: Most recent waitlist position from live web page
        file_path: File path to json file that has the previous waitlist data
        s3_bucket_object: AWS S3 bucket and object to get information from

        For s3_bucket_object, requires keys {'bucket': bucket, 'object_key': object_key}

    Returns
        True if waitlist position has changed
    """
    has_changed = False

    wl_data = get_saved_waitlist_data(file_path, s3_bucket_object)
    wl_posn = get_saved_waitlist_posn(wl_data)

    # logger.debug("posn: %s, wl_posn: %s", posn, wl_posn)
    if int(posn) != int(wl_posn):
        has_changed = True

    # logger.debug("has_changed: %s", has_changed)
    dt_now = dt.now().astimezone(tz.utc).strftime(str(DateFormats.DEFAULT.value))
    if has_changed:
        save_waitlist_posn(posn, dt_now, dt_now, file_path, s3_bucket_object)
    else:
        existing_date = get_saved_waitlist_datetime(wl_data).strftime(str(DateFormats.DEFAULT.value))
        save_waitlist_posn(wl_posn, existing_date, dt_now, file_path, s3_bucket_object)

    return has_changed


def lambda_handler(event, context):
    """
    AWS Lambda handler

    Args:
        event: AWS Lambda event dictionary
        context: AWS Lambda context dictionary

    Returns:
        Status response dictionary
    """
    print(f"Entered `lambda_handler()` with '{event}' and {context}")

    site_un = event.get("site-un", "")
    site_pw = event.get("site-pw", "")
    student_id = event.get("student-id", "")

    print("Initialising driver")
    driver = initialise_driver()

    print("Logging in")
    logged_in = login(str(URLConstants.LOGIN_URL.value), site_un, site_pw, driver)
    print(f"Was login a succes? {logged_in}")

    print("Going to waitlist")
    driver = go_to_waitlist(student_id, driver)

    print("Getting waitlist position")
    wl_posn = get_latest_waitlist_posn(driver.page_source)
    print(f"Waitlist position wl_posn: {wl_posn}")

    s3_bucket = event.get("s3-bucket", "")
    s3_object_key = event.get("s3-object-key", "")

    print("Checking if waitlist position has changed on "
          f"bucket '{s3_bucket}' and object '{s3_object_key}'")
    s3_bucket_object = {'bucket': s3_bucket, 'object_key': s3_object_key}
    has_changed = compare_waitlist_posns(wl_posn, s3_bucket_object=s3_bucket_object)
    print(f"has_change?: '{has_changed}'")

    driver.quit()

    sns_topic_arn = event.get("sns-topic-arn", "")
    subject_text = f"There is {'a' if has_changed else 'no'} in waitlist position"
    body_text = f"Sent at {dt.now().astimezone(tz.utc).strftime(str(DateFormats.DEFAULT.value))}"

    print(
        "Trying email send from "
        f"sns_topic_arn '{sns_topic_arn}' "
        f"subject '{subject_text}' "
        f"body '{body_text}' "
    )

    _ = send_email(sns_topic_arn, subject_text, body_text)

    response = {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": {"message":  "completed"},
    }

    return response
