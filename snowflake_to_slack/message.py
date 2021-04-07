import json
import logging
from contextlib import closing
from datetime import datetime
from datetime import timedelta
from string import Template
from typing import Any
from typing import Dict
from typing import Generator
from typing import Set
from pathlib import Path

import jinja2
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from snowflake.connector import DictCursor

from snowflake_to_slack.snowflake import snowflake_connect

logger = logging.getLogger("snowflake-to-slack")


def _get_snowflake_messages(
    **kwargs: Any,
) -> Generator[DictCursor, None, None]:
    """Get messages from Snowflake.

    Args:
        kwargs: key value arguments.

    Yields:
        Generator[DictCursor, None, None]: Generator of Snowflake messages.
    """
    sql_cmd = kwargs.pop("sql_cmd")
    with snowflake_connect(**kwargs) as con:
        with closing(con.cursor(DictCursor)) as cur:
            cur.execute(sql_cmd)
            for msg in cur:
                yield msg


def _get_date_valid(**kwargs: Any) -> datetime:
    """Get date valid.

    Returns:
        datetime: date of valid.
    """
    return datetime.strptime(kwargs["date_valid"], "%Y-%m-%d")


def _get_frequency_tags(msg: DictCursor) -> Set[str]:
    """Get frequency tags.

    Args:
        msg (DictCursor): Snowflake message.

    Returns:
        Set[str]: set of frequency tags.
    """
    tags = set()
    frequency = msg.get("FREQUENCY")
    if frequency:
        tags = {tag.strip().lower() for tag in frequency.split(",") if tag}
    return tags


def _get_jinja_env(**kwargs: Any) -> jinja2.Environment:
    """Get Jinja2 environment

    Returns:
        jinja2.Environment: Jinja environment
    """
    template_path = kwargs.get("template_path")
    if template_path and Path(template_path).is_dir:
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_path)
        )
        return env
    else:
        logger.error(f"Template path {template_path} does not exists!")
        exit(1)


def _prepare_messages(**kwargs: Any) -> Generator[Dict[str, str], None, None]:
    """Prepare messages for Slack notification.

    Args:
        kwargs: key value arguments.

    Yields:
        Generator[Dict[str, str], None, None]: Generator of all prepared messages.
    """
    date_valid = _get_date_valid(**kwargs)
    jinja_env = _get_jinja_env(**kwargs)
    for msg in _get_snowflake_messages(**kwargs):
        prepared_message = {}
        tags = _get_frequency_tags(msg)
        if kwargs.get("dry_run") or _met_conditions(date_valid=date_valid, tags=tags):
            metrics = json.loads(msg.get("METRICS", "{}"))
            message = Template(msg.get("MESSAGE", "")).safe_substitute(**metrics)
            prepared_message["message"] = message
            prepared_message["channel"] = msg.get("CHANNEL")
            yield prepared_message


def _met_conditions(date_valid: datetime, tags: Set[str]) -> bool:
    """Should we send the notification?

    Args:
        date_valid (datetime): date for decision.
        tags (Set[str]): tags.

    Returns:
        bool: Conditions are met.
    """
    weekday = date_valid.weekday()
    day = (date_valid + timedelta(days=1)).day
    month = (date_valid + timedelta(days=1)).month
    results = []
    condition_list = {
        "daily": True,
        "weekly": True if weekday == 6 else False,
        "monthly": True if day == 1 else False,
        "quarterly": True if day == 1 and month in [4, 7, 10, 1] else False,
        "yearly": True if day == 1 and month == 1 else False,
        "monday": True if weekday == 0 else False,
        "tuesday": True if weekday == 1 else False,
        "wednesday": True if weekday == 2 else False,
        "thursday": True if weekday == 3 else False,
        "friday": True if weekday == 4 else False,
        "saturday": True if weekday == 5 else False,
        "sunday": True if weekday == 6 else False,
        "never": False,
        "always": True,
    }
    intersection_list = list(set(tags) & set(condition_list.keys()))
    if intersection_list:
        for tag in intersection_list:
            results.append(condition_list.get(tag, True))
        return any(results)
    else:
        return True


def _notify_slack(
    message_blocks: str, channel: str, slack_token: str, fail_fast: bool
) -> int:
    """Send slack notification.

    Args:
        message_blocks (str): message block.
        channel (str): channel or person.
        slack_token (str): slack token
        fail_fast (bool): raise error if any error occures

    Raises:
        SlackApiError: messege was not set

    Returns:
        int: status code
    """
    client = WebClient(token=slack_token)

    try:
        client.chat_postMessage(channel=channel, blocks=message_blocks)
        logger.debug(f"{channel}: {message_blocks}")
        return 0
    except SlackApiError as e:
        logger.error(f"Channel: {channel}\nMessage: {message_blocks}\nError: {e}")
        if fail_fast:
            raise
        return 1


def send_messages(**kwargs: Any) -> int:
    """Send Messages from Snowflake into Slack.

    Args:
        kwargs: key value arguments.
    """
    messages = _prepare_messages(**kwargs)
    slack_token = kwargs.get("slack_token", "")
    fail_fast = kwargs.get("fail_fast", False)
    status_code = 0
    for message in messages:
        channel = kwargs.get("slack_channel") or message.get("channel")
        if channel:
            msg_status_code = _notify_slack(
                slack_token=slack_token,
                channel=channel,
                message_blocks=message.get("message", ""),
                fail_fast=fail_fast,
            )
        else:
            logger.warn(f"Missing channel: {message}")
            msg_status_code = 1
        status_code |= msg_status_code
    exit(status_code)
