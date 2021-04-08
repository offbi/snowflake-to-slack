import unittest.mock as mock

import jinja2
import pytest
from click.testing import CliRunner
from slack_sdk.errors import SlackApiError

from snowflake_to_slack.cli import snowflake_to_slack

DAILY_DB_DATA = [
    {
        "FREQUENCY": "daily",
        "SLACK_CHANNEL": "test",
        "MESSAGE_TEMPLATE": "simple.j2",
        "MESSAGE_PARAMS": '{"test": "simple"}',
    }
]

MULTIPLE_DAILY_DB_DATA = [
    {
        "FREQUENCY": "daily",
        "SLACK_CHANNEL": "test",
        "MESSAGE_TEMPLATE": "simple.j2",
        "MESSAGE_PARAMS": '{"test": "simple"}',
    },
    {
        "FREQUENCY": "never",
        "SLACK_CHANNEL": "test2",
        "MESSAGE_TEMPLATE": "simple.j2",
        "MESSAGE_PARAMS": '{"test": "simple"}',
    },
]

MISSING_TEMPLATE = [
    {
        "FREQUENCY": "daily",
        "SLACK_CHANNEL": "test",
        "MESSAGE_TEMPLATE": "simple.jinja2",
        "MESSAGE_PARAMS": '{"test": "simple"}',
    }
]


NO_FREQUENCY_DB_DATA = [
    {
        "SLACK_CHANNEL": "test",
        "MESSAGE_TEMPLATE": "simple.j2",
        "MESSAGE_PARAMS": '{"test": "simple"}',
    }
]

BASIC_PARAMS = [
    "--user",
    "test",
    "--account",
    "test",
    "--warehouse",
    "test",
    "--database",
    "test",
    "--role",
    "test",
    "--sql",
    "SELECT 1",
]

REQUIRED_PARAMS = BASIC_PARAMS + ["--template-path", "./tests/test_templates"]

# table, params
TESTS = (
    (
        DAILY_DB_DATA,
        REQUIRED_PARAMS + ["--password", "test", "--slack-token", "123"],
        0,
    ),
    (DAILY_DB_DATA, REQUIRED_PARAMS + ["--password", "test", "--dry-run"], 0),
    (DAILY_DB_DATA, REQUIRED_PARAMS + ["--password", "test"], 1),
    (
        DAILY_DB_DATA,
        REQUIRED_PARAMS
        + ["--password", "test", "--private-key-pass", "test", "--slack-token", "123"],
        1,
    ),
    (
        DAILY_DB_DATA,
        REQUIRED_PARAMS
        + ["--password", "test", "--rsa-key-uri", "test", "--slack-token", "123"],
        1,
    ),
    (
        DAILY_DB_DATA,
        REQUIRED_PARAMS
        + [
            "--password",
            "test",
            "--private-key-pass",
            "test",
            "--rsa-key-uri",
            "test",
            "--slack-token",
            "123",
        ],
        1,
    ),
    (DAILY_DB_DATA, REQUIRED_PARAMS, 1),
    (
        NO_FREQUENCY_DB_DATA,
        REQUIRED_PARAMS + ["--password", "test", "--slack-token", "123"],
        0,
    ),
    (
        DAILY_DB_DATA,
        REQUIRED_PARAMS
        + [
            "--rsa-key-uri",
            "./tests/fake_rsa_key.p8",
            "--private-key-pass",
            "test123",
            "--slack-token",
            "123",
        ],
        0,
    ),
    (
        DAILY_DB_DATA,
        BASIC_PARAMS
        + ["--password", "test", "--slack-token", "123", "--template-path", "fake"],
        1,
    ),
    (
        MISSING_TEMPLATE,
        REQUIRED_PARAMS + ["--password", "test", "--slack-token", "123"],
        1,
    ),
    (
        MULTIPLE_DAILY_DB_DATA,
        REQUIRED_PARAMS + ["--password", "test", "--slack-token", "123"],
        0,
    ),
)


@mock.patch("slack_sdk.WebClient.chat_postMessage")
@mock.patch("snowflake.connector.connect")
@pytest.mark.parametrize(("table_data", "cli_params", "exit_code"), TESTS)
def test_cli(snow, _, table_data, cli_params, exit_code):
    runner = CliRunner()
    mock_con = snow.return_value
    mock_cur = mock_con.cursor.return_value
    mock_cur.__iter__.return_value = iter(table_data)
    result = runner.invoke(snowflake_to_slack, cli_params)
    assert result.exit_code == exit_code


@mock.patch("slack_sdk.WebClient.chat_postMessage")
@mock.patch("snowflake.connector.connect")
def test_raise_missing_template(snow, _):
    runner = CliRunner()
    mock_con = snow.return_value
    mock_cur = mock_con.cursor.return_value
    mock_cur.__iter__.return_value = iter(MISSING_TEMPLATE)
    params = REQUIRED_PARAMS + [
        "--password",
        "test",
        "--slack-token",
        "123",
        "--fail-fast",
    ]
    with pytest.raises(jinja2.TemplateNotFound):
        runner.invoke(snowflake_to_slack, params, catch_exceptions=False)


@mock.patch(
    "slack_sdk.WebClient.chat_postMessage", side_effect=SlackApiError("Slack error", "")
)
@mock.patch("snowflake.connector.connect")
def test_raise_slack(snow, _):
    runner = CliRunner()
    mock_con = snow.return_value
    mock_cur = mock_con.cursor.return_value
    mock_cur.__iter__.return_value = iter(DAILY_DB_DATA)
    params = REQUIRED_PARAMS + [
        "--password",
        "test",
        "--slack-token",
        "123",
        "--fail-fast",
    ]
    with pytest.raises(SlackApiError):
        runner.invoke(snowflake_to_slack, params, catch_exceptions=False)


@mock.patch(
    "slack_sdk.WebClient.chat_postMessage", side_effect=SlackApiError("Slack error", "")
)
@mock.patch("snowflake.connector.connect")
def test_slac_error(snow, _):
    runner = CliRunner()
    mock_con = snow.return_value
    mock_cur = mock_con.cursor.return_value
    mock_cur.__iter__.return_value = iter(DAILY_DB_DATA)
    params = REQUIRED_PARAMS + ["--password", "test", "--slack-token", "123"]
    result = runner.invoke(snowflake_to_slack, params)
    assert result.exit_code == 1
