import configparser

from snowflake_to_slack import __version__


def test_version():
    config = configparser.ConfigParser()
    config.read("setup.cfg")
    assert __version__ == config["metadata"]["version"]
