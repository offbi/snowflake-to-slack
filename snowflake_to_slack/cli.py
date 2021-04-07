import logging
from datetime import datetime

import click

from snowflake_to_slack.message import send_messages


LOG_FORMAT = "%(levelname)s\t%(message)s"

logging.basicConfig(format=LOG_FORMAT, force=True)  # type: ignore
logger = logging.getLogger("snowflake-to-slack")
logger.setLevel(logging.INFO)


def add_options(options):
    def _add_options(func):
        for option in reversed(options):
            func = option(func)
        return func

    return _add_options


snowflake = [
    click.option(
        "--user",
        envvar="SNOWFLAKE_USER",
        required=True,
        help="Snowflake Username",
    ),
    click.option(
        "--password",
        envvar="SNOWFLAKE_PASS",
        help="Snowflake Password",
    ),
    click.option(
        "--rsa-key-uri",
        envvar="SNOWFLAKE_RSA_KEY_URI",
        help="URI of RSA key for authorization.",
    ),
    click.option(
        "--private-key-pass",
        envvar="SNOWFLAKE_PRIVATE_KEY_PASS",
        help="RSA key password.",
    ),
    click.option(
        "--account",
        envvar="SNOWFLAKE_ACCOUNT",
        required=True,
        help="Snowflake Account",
    ),
    click.option(
        "--warehouse",
        envvar="SNOWFLAKE_WAREHOUSE",
        required=True,
        help="Snowflake Warehouse",
    ),
    click.option(
        "--database",
        envvar="SNOWFLAKE_DATABASE",
        required=True,
        help="Snowflake Database",
    ),
    click.option(
        "--role",
        envvar="SNOWFLAKE_ROLE",
        required=True,
        help="Snowflake Role",
    ),
]

slack = [
    click.option("--slack-token", envvar="SLACK_TOKEN", help="Slack Token"),
    click.option(
        "--slack-channel",
        help="Slack Channel. This parameter overrides value from database.",
    ),
]

other = [
    click.option(
        "--fail-fast",
        is_flag=True,
        show_default=True,
        help="Raise error and stop execution if error shows during sending message.",
    ),
    click.option(
        "--dry-run",
        is_flag=True,
        show_default=True,
        help="Just print message into stdout. Do not send message to Slack.",
    ),
    click.option(
        "--date-valid",
        default=datetime.now().strftime("%Y-%m-%d"),
        show_default=True,
        help="Date valid. Default current date.",
    ),
    click.option("--sql", envvar="SQL", required=True, help="SQL command to run."),
    click.option(
        "--template-path",
        envvar="TEMPLATE_PATH",
        required=True,
        help="Path with your Jinja templates.",
    ),
]


@click.command(help="Send data from Snowflake into Slack.")
@add_options(snowflake)
@add_options(slack)
@add_options(other)
def snowflake_to_slack(**kwargs):
    rsa_uri = kwargs.get("rsa_key_uri")
    rsa_pass = kwargs.get("private_key_pass")
    if rsa_uri and rsa_pass:
        kwargs.update(private_key=True)
    if (rsa_uri or rsa_pass) and not (all([rsa_uri, rsa_pass])):
        logger.error(
            "If you want to use rsa key for Snowflake authorization, "
            "you have to provide both `--rsa-key-uri` and `--private-key-pass` "
            "parameters!"
        )
        exit(1)
    if kwargs.get("password") and kwargs.get("private_key"):
        logger.error(
            "You specified both password and rsa key for Snowflake authorization. "
            "Please use one or the other!"
        )
        exit(1)
    if not (kwargs.get("slack_token") or kwargs.get("dry_run")):
        logger.error(
            "Slack token parameter is missing. Please use `--slack-token` "
            "or run it with `--dry-run` parameter!"
        )
        exit(1)
    send_messages(**kwargs)
