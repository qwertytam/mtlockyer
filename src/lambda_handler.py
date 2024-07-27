"""Main module"""

import logging
import json
from datetime import datetime as dt
from datetime import timezone as tz

from src.main import get_aws_secret, initialise_driver, login
from src.main import go_to_waitlist, get_latest_waitlist_posn, compare_waitlist_posns
from src.main import send_email
from src.constants import DateFormats, URLConstants


logger = logging.getLogger(__name__)
logger.setLevel("INFO")


def lambda_handler(event, context):
    """
    AWS Lambda handler

    Args:
        event: AWS Lambda event dictionary
        context: AWS Lambda context dictionary

    Returns:
        Status response dictionary
    """
    logger.info("Starting lambda with event: '%s'", event)
    site_un = event.get("site-un", "")

    aws_secrets = json.loads(get_aws_secret("mtlockeyer-aws-secrets"))
    site_pw = aws_secrets.get("site-pw", "")
    student_id = aws_secrets.get("student-id", "")

    driver = initialise_driver()

    logger.info("site_un: '%s'", site_un)
    logger.info("student_id: '%s'", student_id)

    print("site_un: '%s'", site_un)
    print("student_id: '%s'", student_id)

    _ = login(str(URLConstants.LOGIN_URL.value), site_un, site_pw, driver)

    driver = go_to_waitlist(student_id, driver)

    wl_posn = get_latest_waitlist_posn(driver.page_source)
    logger.info("Latest waitlist position: '%s'", wl_posn)

    s3_bucket = event.get("s3-bucket", "")
    s3_object_key = event.get("s3-object-key", "")

    s3_bucket_object = {"bucket": s3_bucket, "object_key": s3_object_key}
    has_changed, wl_posn_old = compare_waitlist_posns(
        wl_posn, s3_bucket_object=s3_bucket_object
    )
    logger.info("Has waitlist position changed?: '%s'", has_changed)

    driver.quit()

    if has_changed:
        sns_topic_arn = event.get("sns-topic-arn", "")
        logger.info("sns_topic_arn: '%s'", sns_topic_arn)
        print("sns_topic_arn: '%s'", sns_topic_arn)

        subject_text = f"Now #{wl_posn} on the waitlist; previously #{wl_posn_old}"
        body_text = (
            "Sent at "
            + f"{dt.now().astimezone(tz.utc).strftime(str(DateFormats.DEFAULT.value))}"
        )

        _ = send_email(sns_topic_arn, subject_text, body_text)

    response = {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": {"message": "completed"},
    }

    return response
