<p align="center">
 <img src="https://github.com/offbi/snowflake-to-slack/blob/main/.github/snowflake-to-slack.png?raw=true" alt="dbt-pre-commit" width=400/>
 <h1 align="center">snowflake-to-slack</h1>
</p>
<p align="center">
 <a href="https://github.com/offbi/snowflake-to-slack/actions?workflow=CI">
 <img src="https://github.com/offbi/snowflake-to-slack/workflows/CI/badge.svg?branch=main" alt="CI" />
 </a>
 <a href="https://codecov.io/gh/offbi/snowflake-to-slack">
 <img src="https://codecov.io/gh/offbi/snowflake-to-slack/branch/main/graph/badge.svg"/>
 </a>
 <a href="https://github.com/psf/black">
 <img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="black"/>
 </a>
 <a href="https://github.com/pre-commit/pre-commit">
 <img src="https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white" alt="black"/>
 </a>
</p>

Easily send Slack messages templated with data from Snowflake.

`snowflake-to-slack` can be executed as:

- [Github Action](#github-actions)
- [Docker container](#docker-container)
- [Python script](#python-script)

## Use cases

- send daily / weekly / monthly reports to your SDR or any channel in human words.
- send information on whether anomalies were detected in the selected metrics. With e.g. [SQL anomaly detection](https://hakibenita.com/sql-anomaly-detection).
- view information about yesterday's credit spend in Slack.
- monitor [dbt](https://docs.getdbt.com) model execution and dependencies from Slack with [dbt_artifacts](https://github.com/tailsdotcom/dbt_artifacts).

## How to setup `snowflake-to-slack`

1. First you need to [generate Slack Token](https://github.com/offbi/snowflake-to-slack/blob/main/generate-slack-token.md).
2. Design your Slack message with [Slack Block Kit](https://app.slack.com/block-kit-builder/T107X2XNZ#%7B%22blocks%22:%5B%7B%22type%22:%22section%22,%22text%22:%7B%22type%22:%22mrkdwn%22,%22text%22:%22You%20have%20a%20new%20request:%5Cn*%3CfakeLink.toEmployeeProfile.com%7CFred%20Enriquez%20-%20New%20device%20request%3E*%22%7D%7D,%7B%22type%22:%22section%22,%22fields%22:%5B%7B%22type%22:%22mrkdwn%22,%22text%22:%22*Type:*%5CnComputer%20(laptop)%22%7D,%7B%22type%22:%22mrkdwn%22,%22text%22:%22*When:*%5CnSubmitted%20Aut%2010%22%7D,%7B%22type%22:%22mrkdwn%22,%22text%22:%22*Last%20Update:*%5CnMar%2010,%202015%20(3%20years,%205%20months)%22%7D,%7B%22type%22:%22mrkdwn%22,%22text%22:%22*Reason:*%5CnAll%20vowel%20keys%20aren't%20working.%22%7D,%7B%22type%22:%22mrkdwn%22,%22text%22:%22*Specs:*%5Cn%5C%22Cheetah%20Pro%2015%5C%22%20-%20Fast,%20really%20fast%5C%22%22%7D%5D%7D,%7B%22type%22:%22actions%22,%22elements%22:%5B%7B%22type%22:%22button%22,%22text%22:%7B%22type%22:%22plain_text%22,%22emoji%22:true,%22text%22:%22Approve%22%7D,%22style%22:%22primary%22,%22value%22:%22click_me_123%22%7D,%7B%22type%22:%22button%22,%22text%22:%7B%22type%22:%22plain_text%22,%22emoji%22:true,%22text%22:%22Deny%22%7D,%22style%22:%22danger%22,%22value%22:%22click_me_123%22%7D%5D%7D%5D%7D)
3. Inside your repository (it can be also `dbt` repository) create new folder. e.g. `slack_templates` and copy designed message here. I recommend you to use `.j2` suffix, e.g. `test.j2`.
4. Inside your Slack template, replace all dynamic values you want to replace with Snowflake data with `{{<COLUMN NAME>}}`. E.g.

```
{
	"blocks": [
		{
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": "Hello {{GREETINGS}}"
			}
		}
	]
}
```

Then if I will have SQL query in Snowflake like this:

```
SELECT 'guys!' AS GREETINGS
```

The message `Hello guys!` will be sent to Slack.

**BEWARE you need to uppercase your variable names in template since Snowflake is uppercasing column names by default!!**

Inside templates you can use anything from Jinja templating language (as you probably know from `dbt`), e.g.:

```
-- default
"text": "Hello {{GREETINGS|default('girls!')}}"

-- conditions
{% if SLACK_CHANNEL == '#general' %}
    "text": "Hello people"
{% else %}
   "text": "Hello {{USERNAME}}!"
{% endif %}

-- for loop
"text": "You have:
{% for i in range(3) %}
 {{ i }}
{% endfor %}
seconds to answer!
"
```
You can also [include](https://jinja.palletsprojects.com/en/2.11.x/templates/#include) and [import](https://jinja.palletsprojects.com/en/2.11.x/templates/#import) other templates!

See [Template Designer Documentation](https://jinja.palletsprojects.com/en/2.11.x/templates/) for full reference of Jinja2 syntax.

5. Create Snowflake SQL script. Here are some things you should know:

    - Every row from SQL will be send as separated Slack Message. It means that if you want to send PM to different Slack users you do not have to create separete SQL for her/him, but you create one SQL and add column `SLACK_CHANNEL` with Slack user id. With this you are able to burst it.
    - There are some special columns that influence the message distribution:
        - `SLACK_MESSAGE_TEMPLATE`: full name of Jinja template (e.g. `test.j2`) from template path. This value can be overriden with cli parameters (see later).
        - `SLACK_MESSAGE_TEXT`: useful if you want to send just simple message without block kit and without templating. So you can use `SLACK_MESSAGE_TEMPLATE` or `SLACK_MESSAGE_TEXT`. If you use both, `SLACK_MESSAGE_TEMPLATE` will be used for main message in Slack and `SLACK_MESSAGE_TEXT` for notification message. This value can be overriden with cli parameters (see later).
        - `SLACK_CHANNEL`: name of Slack channel (with `#`) where you want to send your message. Can also be the name (`john.doe`) or ID of Slack user.
        - `SLACK_FREQUENCY`: useful e.g. in cases when you have one SQL and you want to burst it to many users. Some users wants this report daily but some weekly. Specify list of values separated with comma e.g. `weekly,monthly`. Allowed values are: `daily,weekly,monthly,quartely,yearly,monday,tuesday,wednesday,thursday,friday,saturday,sunday,never,always`
    - Name of column can be used in template (but it doesn't have to).

    Example
    ```
    SELECT
       'test.j2' AS SLACK_MESSAGE_TEMPLATE,
       'This is notification' AS SLACK_MESSAGE_TEXT,
       'weekly,monthly' AS SLACK_FREQUENCY,
       '#random' as SLACK_CHANNEL,
       -------
       'guys!' as GREETINGS
    ```

6. You of course need some Snowflake credentials :). You can use simple name/password or [key-pair](https://docs.snowflake.com/en/user-guide/key-pair-auth.html) authorization.

## Sending messages

You can send Slack messages with:

- [Github Action](#github-actions)
- [Docker container](#docker-container)
- [Python script](#python-script)

### Github Actions

#### Quickstart

- inside your Github repository create folder `.github/workflows` (unless it already exists).
- create new file e.g. `main.yml`
- specify your workflow, e.g.:
```
on:
  schedule:
    # * is a special character in YAML so you have to quote this string
    - cron:  '0 0 * * *'

jobs:
  snowflake-to-slack:
    runs-on: ubuntu-latest
    name: snowflake to slack
    steps:
      - name: Checkout repository
        uses: actions/checkout@v2.3.3
      - name: Slack message 1
        uses: offbi/snowflake-to-slack@1.0.0
        with:
          user: ${{ secrets.USER }}
          password: "${{ secrets.PASSWORD }}"
          account: "<your Snowflake account name>"
          warehouse: "<your Snowflake warehouse name>"
          database: "<your Snowflake database name>"
          role: "<your Snowflake role name>"
          slack-token: ${{ secrets.SLACK_TOKEN }}
          sql: "<your Snowflake select statement>"
          template-path: /github/workspace/<name of template folder in your repo>
```
**Beware before you run `snowflake-to-slack` you needt to run `actions/checkout` action. `template-path` hash to be specified ad `/github/workspace/<name of template folder>`**
- it is adviced to use [Github Secrets](https://docs.github.com/en/actions/reference/encrypted-secrets) to specify passwords and slack-tokens.
- push to Github :)

To learn more about Github actions see https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions.

#### Github Action parameters

- `user`: Snowflake Username. Required: true
- `password`: Snowflake Password. Required: false
- `rsa-key-uri`: URI of RSA key for authorization. Required: false
- `private-key-pass`: RSA key password. Required: false
- `account`: Snowflake Account. Required: true
- `warehouse`: Snowflake Warehouse. Required: true
- `database`: Snowflake Database. Required: true
- `role`: Snowflake Role. Required: true
- `slack-token`: Slack Token. Required: true
- `slack-channel`: Slack Channel. This parameter overrides value from database Required: false
- `fail-fast`: Raise error and stop execution if error shows during sending message. Required: false
- `dry-run`: Just print message into stdout. Do not send message to Slack. Required: false
- `date-valid`: Date valid for deciding if message should be executed. Default current date. Required: false
- `sql`: SQL command to run. Required: true
- `template-path`: Path with your Jinja templates. Required: true
- `slack-frequency`: Frequency. Together with date-valid determines whether the message is sent. This parameter overrides value from database. Required: false.
- `slack-message-template`: Message template. It overrides `SLACK_MESSAGE_TEMPLATE` from Snowflake. Required: false.
- `slack-message-text`: Message text. It overrides `SLACK_MESSAGE_TEXT` from Snowflake. Required: false.

### Docker container

To run Docker container execute:

```
docker run <list of envs> offbi/snowflake-to-slack <params>
```

### Python script

Install `snowflake-to-slack` with:

```
pip install snowflake-to-slack=='1.0.0'
snowflake-to-slack <params>
```

## List of `snowflake-to-slack` params

- `--user`: Snowflake Username. Required: true. Env variable `SNOWFLAKE_USER`.
- `--password`: Snowflake Password. Required: false. Env variable `SNOWFLAKE_PASS`.
- `--rsa-key-uri`: URI of RSA key for authorization. Required: false. Env variable `SNOWFLAKE_RSA_KEY_URI`.
- `--private-key-pass`: RSA key password. Required: false. Env variable `SNOWFLAKE_PRIVATE_KEY_PASS`.
- `--account`: Snowflake Account. Required: true. Env variable `SNOWFLAKE_ACCOUNT`.
- `--warehouse`: Snowflake Warehouse. Required: true. Env variable `SNOWFLAKE_WAREHOUSE`.
- `--database`: Snowflake Database. Required: true. Env variable `SNOWFLAKE_USER`.
- `--role`: Snowflake Role. Required: true. Env variable `SNOWFLAKE_ROLE`.
- `--slack-token`: Slack Token. Required: true. Env variable `SLACK_TOKEN`.
- `--slack-channel`: Slack Channel. This parameter overrides value from database Required: false. Env variable `SLACK_CHANNEL`.
- `--fail-fast`: Raise error and stop execution if error shows during sending message. Required: false. Env variable `FAIL_FAST`.
- `--dry-run`: Just print message into stdout. Do not send message to Slack. Required: false. Env variable `DRY_RUN`.
- `--date-valid`: Date valid for deciding if message should be executed. Default current date. Required: false. Env variable `DATE_VALID`.
- `--sql`: SQL command to run. Required: true. Env variable `SQL`.
- `--template-path`: Path with your Jinja templates. Required: true. Env variable `TEMPLATE_PATH`.
- `--slack-frequency`: Frequency. Together with date-valid determines whether the message is sent. This parameter overrides value from database. Required: false. Env variable `SLACK_FREQUENCY`.
- `--slack-message-template`: Message template. It overrides `SLACK_MESSAGE_TEMPLATE` from Snowflake. Required: false. Env variable `SLACK_MESSAGE_TEMPLATE`.
- `--slack-message-text`: Message text. It overrides `SLACK_MESSAGE_TEXT` from Snowflake. Required: false. Env variable `SLACK_MESSAGE_TEXT`.
