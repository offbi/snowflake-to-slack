FROM python:3.8-slim

WORKDIR /work
COPY . .
RUN pip install .

ENTRYPOINT ["snowflake-to-slack"]
