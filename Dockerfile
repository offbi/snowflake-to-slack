FROM python:3.8-slim

RUN pip install snowflake-to-slack==0.1.1

ENTRYPOINT ["snowflake-to-slack"]
