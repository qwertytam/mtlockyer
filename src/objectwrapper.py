"""Encapsulates S3 object actions"""

import logging

from src.exceptions import ObjClientExceptions

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


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
            logger.info(
                "Put object '%s' to bucket '%s'",
                self.object.key,
                self.object.bucket_name,
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
            logger.info(
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
            logger.info(
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
            logger.info(
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
                logger.info(
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
            logger.info("Emptied bucket '%s'.", bucket.name)
        except ObjClientExceptions:
            logger.exception("Couldn't empty bucket '%s'.", bucket.name)
            raise
