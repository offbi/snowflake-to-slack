from unittest.mock import patch

import pytest
from slack_sdk.errors import SlackApiError
from slack_sdk.web.client import WebClient

from snowflake_to_slack import __version__
from snowflake_to_slack.message import _prepare_messages
from snowflake_to_slack.message import send_messages


TEST_PREPARE_MESSAGE = (
    (
        [
            {
                "FREQUENCY": "always",
                "METRICS": r'{ "test": 1 }',
                "MESSAGE": r'[{"type": "section", "text": '
                r'{"type": "mrkdwn", "text": "You have $test"}}]',
                "CHANNEL": "bb",
            }
        ],
        [
            {
                "channel": "bb",
                "message": r'[{"type": "section", "text": '
                r'{"type": "mrkdwn", "text": "You have 1"}}]',
            }
        ],
        0,
    ),
    (
        [
            {
                "FREQUENCY": "aaapy",
                "METRICS": r'{ "test": 1 }',
                "MESSAGE": r'[{"type": "section", "text": '
                r'{"type": "mrkdwn", "text": "You have $test"}}]',
                "CHANNEL": "bb",
            }
        ],
        [
            {
                "channel": "bb",
                "message": r'[{"type": "section", "text": '
                r'{"type": "mrkdwn", "text": "You have 1"}}]',
            }
        ],
        0,
    ),
)


def test_version():
    assert __version__ == "0.1.0"


@pytest.mark.parametrize(
    ("input_data", "expected", "expected_status_code"), TEST_PREPARE_MESSAGE
)
def test_prepare_message(input_data, expected, expected_status_code):

    with patch(
        "snowflake_to_slack.message._get_snowflake_messages"
    ) as snowflake_messages:
        snowflake_messages.return_value = iter(input_data)
        result = list(_prepare_messages(date_valid="2020-01-01"))
        assert result == expected


@pytest.mark.parametrize(
    ("input_data", "expected", "expected_status_code"), TEST_PREPARE_MESSAGE
)
def test_send_messages(input_data, expected, expected_status_code):

    with patch(
        "snowflake_to_slack.message._get_snowflake_messages"
    ) as snowflake_messages:
        snowflake_messages.return_value = iter(input_data)
        with patch.object(WebClient, "chat_postMessage", return_value=None):
            status_code = send_messages(slack_token="ff", date_valid="2020-01-01")
            assert status_code == expected_status_code


@pytest.mark.parametrize(
    ("input_data", "expected", "expected_status_code"), TEST_PREPARE_MESSAGE
)
def test_send_messages_fail_fast(input_data, expected, expected_status_code):

    with patch(
        "snowflake_to_slack.message._get_snowflake_messages"
    ) as snowflake_messages:
        snowflake_messages.return_value = iter(input_data)
        with patch.object(
            WebClient, "chat_postMessage", side_effect=SlackApiError("fff", 404)
        ):
            with pytest.raises(SlackApiError):
                send_messages(slack_token="ff", date_valid="2020-01-01", fail_fast=True)


@pytest.mark.parametrize(
    ("input_data", "expected", "expected_status_code"), TEST_PREPARE_MESSAGE
)
def test_send_messages_fail_fast_false(input_data, expected, expected_status_code):

    with patch(
        "snowflake_to_slack.message._get_snowflake_messages"
    ) as snowflake_messages:
        snowflake_messages.return_value = iter(input_data)
        with patch.object(
            WebClient, "chat_postMessage", side_effect=SlackApiError("fff", 404)
        ):
            status_code = send_messages(slack_token="ff", date_valid="2020-01-01")
            assert status_code == 1
