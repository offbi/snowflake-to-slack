import json
import logging
from contextlib import closing
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import Any
from typing import Dict
from typing import Generator
from typing import Set

import jinja2
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from snowflake.connector import DictCursor

from snowflake_to_slack.snowflake import snowflake_connect

logger = logging.getLogger("snowflake-to-slack")


class MissingTemplate(Exception):
    pass


def _get_snowflake_messages(
    **kwargs: Any,
) -> Generator[DictCursor, None, None]:
    """Get messages from Snowflake.

    Args:
        kwargs: key value arguments.

    Yields:
        Generator[DictCursor, None, None]: Generator of Snowflake messages.
    """
    sql_cmd = kwargs.pop("sql")
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
    if template_path and Path(template_path).is_dir():
        env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_path))
        return env
    else:
        logger.error(f"Template path {template_path} does not exists!")
        exit(1)


def _render_template(
    jinja_env: jinja2.Environment, template_name: str, params: Dict[str, Any]
) -> str:
    try:
        template = jinja_env.get_template(template_name)
        rendered = template.render(**params)
        return rendered
    except (jinja2.TemplateNotFound, jinja2.TemplateError):
        raise


def _get_message_template(message: Dict[str, Any]) -> str:

    template_name = message.get("MESSAGE_TEMPLATE")
    if not template_name:
        raise MissingTemplate(
            "Missing column `MESSAGE_TEMPLATE` or this column is empty!"
        )
    return template_name


def _send_messages(**kwargs: Any) -> int:
    """Get messages from Snowflake and send them to Slack.

    Returns:
        int: Status code
    """
    date_valid = _get_date_valid(**kwargs)
    jinja_env = _get_jinja_env(**kwargs)
    client = WebClient(token=kwargs.get("slack_token"))
    status_code = 0
    for msg in _get_snowflake_messages(**kwargs):
        channel = kwargs.get("slack_channel") or msg.get("SLACK_CHANNEL", "")
        tags = _get_frequency_tags(msg)
        if kwargs.get("dry_run") or _met_conditions(date_valid=date_valid, tags=tags):
            try:
                template_name = _get_message_template(msg)
            except MissingTemplate as e:
                logger.error(e)
                if kwargs.get("fail_fast"):
                    raise
                status_code = 1
            params = json.loads(msg.get("MESSAGE_PARAMS", "{}"))
            try:
                rendered = _render_template(jinja_env, template_name, params)
                client.chat_postMessage(channel=channel, blocks=rendered)
            except (jinja2.TemplateNotFound, jinja2.TemplateError) as e:
                logger.error(
                    f"Message template: {template_name}\n"
                    f"Message params: {params}\n"
                    f"Error: {e}"
                )
                if kwargs.get("fail_fast"):
                    raise
                status_code = 1
            except SlackApiError as e:
                logger.error(f"Channel: {channel}\nMessage: {rendered}\nError: {e}")
                if kwargs.get("fail_fast"):
                    raise
                status_code = 1
    return status_code


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


def send_messages(**kwargs: Any) -> int:
    """Send Messages from Snowflake into Slack.

    Args:
        kwargs: key value arguments.
    """
    status_code = _send_messages(**kwargs)
    exit(status_code)
