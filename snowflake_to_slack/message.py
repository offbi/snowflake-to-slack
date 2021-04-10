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


class SingletonMeta(type):

    _instances: Dict[Any, Any] = {}

    def __call__(cls: Any, *args: Any, **kwargs: Any) -> Any:
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class MissingMessage(Exception):
    pass


class JinjaEnv(jinja2.Environment, metaclass=SingletonMeta):
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
    date_valid = kwargs.get("date_valid", "")
    return datetime.strptime(date_valid, "%Y-%m-%d")


def _get_frequency_tags(msg: DictCursor) -> Set[str]:
    """Get frequency tags.

    Args:
        msg (DictCursor): Snowflake message.

    Returns:
        Set[str]: set of frequency tags.
    """
    tags = set()
    frequency = msg.get("SLACK_FREQUENCY")
    if frequency:
        tags = {tag.strip().lower() for tag in frequency.split(",") if tag}
    return tags


def _get_jinja_env(**kwargs: Any) -> JinjaEnv:
    """Get Jinja2 environment

    Returns:
        JinjaEnv: Jinja environment
    """
    template_path = kwargs.get("template_path")
    if template_path and Path(template_path).is_dir():
        jinja_env = JinjaEnv(loader=jinja2.FileSystemLoader(template_path))
        return jinja_env
    else:
        logger.error(f"Template path {template_path} does not exists!")
        exit(1)


def _render_template(
    jinja_env: JinjaEnv, template_name: str, params: Dict[str, Any]
) -> str:
    try:
        template = jinja_env.get_template(template_name)
        rendered = template.render(**params)
        return rendered
    except (jinja2.TemplateNotFound, jinja2.TemplateError):
        raise


def _met_conditions(date_: datetime, tags: Set[str]) -> bool:
    """Should we send the notification?

    Args:
        date_ (datetime): date for decision.
        tags (Set[str]): tags.

    Returns:
        bool: Conditions are met.
    """
    weekday = date_.weekday()
    day = (date_ + timedelta(days=1)).day
    month = (date_ + timedelta(days=1)).month
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


def _send_message(
    jinja_env: JinjaEnv,
    slack_client: WebClient,
    msg: Dict[str, Any],
    date_: datetime,
    **kwargs: Any,
) -> int:
    """Send message to slack

    Args:
        jinja_env (JinjaEnv): jinja2 environment
        slack_client (WebClient): Slack client
        msg (Dict[str, Any]): Snowflake message
        date_ (datetime): Date valid

    Raises:
        MissingMessage: Message has no test or template

    Returns:
        int: status code
    """
    status_code = 0
    channel = kwargs.get("slack_channel") or msg.get("SLACK_CHANNEL", "")
    tags = _get_frequency_tags(msg)
    msg_template = msg.get("SLACK_MESSAGE_TEMPLATE")
    msg_text = msg.get("SLACK_MESSAGE_TEXT")
    blocks = None
    if kwargs.get("dry_run") or _met_conditions(date_=date_, tags=tags):
        try:
            # If snowflake message contanins message template
            if msg_template:
                blocks = _render_template(jinja_env, msg_template, msg)
            # If snowflake message contanins message text
            elif msg_text:
                pass
            else:
                raise MissingMessage(
                    "Every row in Snowflake table has to have `SLACK_MESSAGE_TEMPLATE`"
                    " or/and `SLACK_MESSAGE_TEXT` columns!"
                )
            slack_client.chat_postMessage(channel=channel, blocks=blocks, text=msg_text)
        except (
            jinja2.TemplateNotFound,
            jinja2.TemplateError,
            MissingMessage,
            SlackApiError,
        ) as e:
            logger.error(f"Snowflake row: {msg}\n" f"Error: {e}")
            if kwargs.get("fail_fast"):
                raise
            status_code = 1
    return status_code


def _process_messages(**kwargs: Any) -> int:
    """Process messages from Snowflake and send them to Slack.

    Returns:
        int: Status code
    """
    date_ = _get_date_valid(**kwargs)
    jinja_env = _get_jinja_env(**kwargs)
    slack_client = WebClient(token=kwargs.get("slack_token"))
    status_code = 0
    for msg in _get_snowflake_messages(**kwargs):
        status_code |= _send_message(
            jinja_env=jinja_env,
            slack_client=slack_client,
            msg=msg,
            date_=date_,
            **kwargs,
        )
    return status_code


def send_messages(**kwargs: Any) -> int:
    """Send Messages from Snowflake into Slack.

    Args:
        kwargs: key value arguments.
    """
    status_code = _process_messages(**kwargs)
    exit(status_code)
