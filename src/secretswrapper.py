"""Encapsulates AWS Secrets"""

import logging

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


class GetSecretWrapper:
    """
    AWS  Secrets Manager wrapper
    """

    def __init__(self, secretsmanager_client):
        self.client = secretsmanager_client

    def get_secret(self, secret_name: str) -> str:
        """
        Retrieve individual secrets from AWS Secrets Manager using the
        get_secret_value API.

        Args:
            secret_name: The name of the secret fetched
        """
        logger.info("Entering get_secret()")
        try:
            get_secret_value_response = self.client.get_secret_value(
                SecretId=secret_name
            )
            logging.info("Secret retrieved successfully.")
            return get_secret_value_response["SecretString"]
        except self.client.exceptions.ResourceNotFoundException:
            msg = f"The requested secret {secret_name} was not found."
            logger.info(msg)
            return msg
        except Exception as e:
            logger.error("An unknown error occurred: '%s'", e, exc_info=True)
            raise
