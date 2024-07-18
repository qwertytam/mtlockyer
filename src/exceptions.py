"""Encapsulates boto exceptions"""

from botocore.exceptions import ClientError


class ObjClientExceptions(ClientError):
    """Encapsulates boto client exceptions"""
