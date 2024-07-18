"""Main module"""

import logging
import json
from tempfile import mkdtemp
from datetime import datetime as dt
from datetime import timezone as tz
from pathlib import Path
from typing import Optional
from bs4 import BeautifulSoup as bs

import boto3

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from src.constants import DateFormats, URLConstants, DataFileDictFormat
from src.objectwrapper import ObjectWrapper
from src.secretswrapper import GetSecretWrapper

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


def get_aws_secret(secret_name: str) -> str:
    """
    Retrieve a secret from AWS Secrets Manager

    Args:
        secret_name: Name of the secret to retrieve
    """
    try:
        if not secret_name:
            raise ValueError("Secret name must be provided.")

        client = boto3.client("secretsmanager")
        wrapper = GetSecretWrapper(client)
        secret = wrapper.get_secret(secret_name)
        # Note: Secrets should not be logged.
        return secret
    except Exception as e:
        logging.error("Error retrieving secret: '%s'", e, exc_info=True)
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
    logger.info("Initialising driver")
    chrome_options = ChromeOptions()
    if options is None:
        logger.info("Using default options")
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
        logger.info("Using passed options '%s'", options)
        for option in options:
            chrome_options.add_argument(option)
    logger.info("Finished adding options")

    chrome_options.binary_location = binary_location
    logger.info("Added binary location")

    if isinstance(service_log_path, str) and isinstance(executable_path, str):
        logger.info("Adding executable and serivce log path")
        service = Service(
            executable_path=executable_path,
            service_log_path=service_log_path,
        )
        logger.info("Calling webdriver.Chrome")
        driver = webdriver.Chrome(service=service, options=chrome_options)
    else:
        logger.info("Not adding service")
        logger.info("Calling webdriver.Chrome")
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

    logger.info("Email sent with response: '%s'", response)

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
        logger.info("basic-card; assumed login successful")
        logged_in = True
    except TimeoutException:
        # logger.error("TimeoutException: Assuming wrong credentials; exiting")
        logger.info("TimeoutException: Assuming wrong credentials; exiting")
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

    logger.info("Start login to '%s'", url)
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
    url = (
        str(URLConstants.BASE_URL.value)
        + student_id
        + "/"
        + str(URLConstants.WAITLIST_PAGE.value)
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

    logger.info("Have written '%s' to '%s", wl_dict, file_path)


def __save_waitlist_to_s3(wl_dict: dict, s3_bucket_object: dict):
    s3_resource = boto3.resource("s3")
    bucket = s3_resource.Bucket(s3_bucket_object["bucket"])
    obj_wrapper = ObjectWrapper(bucket.Object(s3_bucket_object["object_key"]))
    obj_wrapper.put(bytes(json.dumps(wl_dict, indent=4).encode(encoding="utf-8")))

    logger.info(
        "Have put '%s' into object '%s'", wl_dict, s3_bucket_object["object_key"]
    )


def save_waitlist_posn(
    posn: str,
    wl_date: str,
    last_update: str,
    file_path: Optional[Path] = None,
    s3_bucket_object: Optional[dict] = None,
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
        logger.info("Saving waitlist position to file")
        __save_waitlist_to_file(wl_dict, file_path)
    else:
        if s3_bucket_object is None:
            s3_bucket_object = {"bucket": "", "object_key": ""}
        logger.info("Saving waitlist position to s3")
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
        logger.info("File not found; returning default wl dictionary")
        wl_dict = DataFileDictFormat.DEFAULT_WL_DICT.value
        dt_now = dt.now().astimezone(tz.utc).strftime(str(DateFormats.DEFAULT.value))
        wl_dict["waitlist_datetime"] = dt_now
        wl_dict["last_updated"] = dt_now

    logger.info("Found file '%s'; returning data", file_path)
    return wl_dict


def __get_waitlist_from_s3(s3_bucket_object: dict) -> dict:
    s3_resource = boto3.resource("s3")
    bucket = s3_resource.Bucket(s3_bucket_object["bucket"])
    obj_wrapper = ObjectWrapper(bucket.Object(s3_bucket_object["object_key"]))

    logger.info("Getting object list")
    obj_list = obj_wrapper.list(bucket=bucket)

    obj_key = s3_bucket_object["object_key"]

    logger.info("Is list None? '%s'", obj_list is None)
    logger.info("what type is list> '%s'", type(obj_list))
    logger.info("Is objkey in objlist '%s'", obj_key in obj_list)

    prefix = "hello there!"
    logger.info("Getting object list with prefix '%s'", prefix)
    obj_list = obj_wrapper.list(bucket=bucket, prefix=prefix)

    logger.info("Is list None? '%s'", obj_list is None)
    logger.info("what type is list> '%s'", type(obj_list))
    logger.info("Is objkey in objlist '%s'", obj_key in obj_list)

    wl_bytes = obj_wrapper.get()
    wl_dict = json.loads(wl_bytes.decode("utf8").replace("'", '"'))

    logger.info(
        "Found object '%s'; returning data:\n%s\nEND",
        s3_bucket_object,
        json.dumps(wl_dict, indent=4),
    )
    return wl_dict


def get_saved_waitlist_data(
    file_path: Optional[Path] = None, s3_bucket_object: Optional[dict] = None
) -> dict:
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
        logger.info("Getting waitlist position from file")
        wl_dict = __get_waitlist_from_file(file_path)
    else:
        if s3_bucket_object is None:
            s3_bucket_object = {"bucket": "", "object_key": ""}
        logger.info("Getting waitlist position from s3")
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
    logger.info("wl_dict is type '%s' with string output:\n%s", type(wl_dict), wl_dict)

    for k in wl_dict.keys():
        logger.info("k: '%s' v: '%s'", k, wl_dict[k])
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
    posn: str, file_path: Optional[Path] = None, s3_bucket_object: Optional[dict] = None
) -> bool:
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
        existing_date = get_saved_waitlist_datetime(wl_data).strftime(
            str(DateFormats.DEFAULT.value)
        )
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
    logger.info("Entered `lambda_handler()` with '%s' and '%s'", event, context)
    site_un = event.get("site-un", "")

    aws_secrets = json.loads(get_aws_secret("mtlockeyer-aws-secrets"))
    site_pw = aws_secrets.get("site-pw", "")
    student_id = aws_secrets.get("student-id", "")

    logger.info("Initialising driver")
    driver = initialise_driver()

    logged_in = login(str(URLConstants.LOGIN_URL.value), site_un, site_pw, driver)
    logger.info("Was login a succes? '%s'", logged_in)

    logger.info("Going to waitlist")
    driver = go_to_waitlist(student_id, driver)

    logger.info("Getting waitlist position")
    wl_posn = get_latest_waitlist_posn(driver.page_source)
    logger.info("Waitlist position wl_posn: '%s'", wl_posn)

    s3_bucket = event.get("s3-bucket", "")
    s3_object_key = event.get("s3-object-key", "")

    logger.info(
        "Checking if waitlist position has changed on bucket '%s' and object '%s'",
        s3_bucket,
        s3_object_key,
    )
    s3_bucket_object = {"bucket": s3_bucket, "object_key": s3_object_key}
    has_changed = compare_waitlist_posns(wl_posn, s3_bucket_object=s3_bucket_object)
    logger.info("has_changed?: '%s'", has_changed)

    driver.quit()

    if has_changed:
        sns_topic_arn = event.get("sns-topic-arn", "")
        subject_text = f"Now #{wl_posn} on the waitlist"
        body_text = (
            "Sent at "
            + f"{dt.now().astimezone(tz.utc).strftime(str(DateFormats.DEFAULT.value))}"
        )

        logger.info(
            "Trying email send from "
            "sns_topic_arn '%s' "
            "subject '%s' "
            "body '%s' ",
            sns_topic_arn,
            subject_text,
            body_text,
        )

        _ = send_email(sns_topic_arn, subject_text, body_text)

    response = {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": {"message": "completed"},
    }

    return response
