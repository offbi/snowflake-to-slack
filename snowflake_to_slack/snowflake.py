from contextlib import contextmanager
from typing import Any
from typing import Generator

import snowflake.connector
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from snowflake.connector.connection import SnowflakeConnection


__version__ = "0.1.0"


@contextmanager
def snowflake_connect(**kwargs: Any) -> Generator[SnowflakeConnection, None, None]:
    """Get Snowflake connection

    Yields:
        Generator[SnowflakeConnection, None, None]: Snowflake connection
    """
    if kwargs.get("rsa_key_uri") and kwargs.get("private_key_pass"):
        with open(kwargs.get("rsa_key_uri", ""), "rb") as key:
            p_key = serialization.load_pem_private_key(
                key.read(),
                password=kwargs.get("private_key_pass", "").encode(),
                backend=default_backend(),
            )

        pkb = p_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        kwargs["private_key"] = pkb

    conn = snowflake.connector.connect(**kwargs)
    yield conn
    conn.close()
