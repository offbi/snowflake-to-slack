FROM python:3.8-slim

RUN pip install snowflake-to-slack==1.0.0

ENTRYPOINT ["snowflake-to-slack"]
