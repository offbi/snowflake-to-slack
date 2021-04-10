# Publishing

Tutorial of publishing to help me not to forgot to anything :D

## 0. Bump new version

- setup.cfg
- __init__.py

## 1. Run tests

Run pytests:

```
pytest -vvv --cov=snowflake_to_slack --cov-config=setup.cfg --cov-report=term-missing --cov-report=html
```

Run pre-commit:

```
pre-commit run --all-files
```

## 2. Publish to pypi

```
python setup.py sdist
twine upload dist/*
```

## 3. Docker

Bump version in Dockerfile

Build:

```
docker build . -t offbi/snowflake-to-slack
docker tag offbi/snowflake-to-slack:latest offbi/snowflake-to-slack:<version>
```

Test:

```
docker run offbi/snowflake-to-slack
```

Publish to Docker Hub

```
docker push offbi/snowflake-to-slack
docker push offbi/snowflake-to-slack:<version>
```

## 4. Github Action

Bump docker version in action.yml

## 5. Write CHANGELOG

## 6. Push to Github

## 7. Create new Github deployment
