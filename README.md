# hidb
Home Inventory DataBase

### Getting Started

Use [Pyenv](https://github.com/pyenv/pyenv) to manage multiple Python versions.

```shell
# Developed using Python 3.9.5
$ pyenv install 3.9.5

# Set up an environment
$ python3 -m venv env
$ source env/bin/activate

# Install dependencies
$ pip3 install -r requirements.txt

# Init the db schema
$ flask --app flaskr init-db

# Run the app
$ flask --app flaskr --debug run

# Run unit tests
$ pytest

# Measure code coverage
$ coverage run -m pytest
$ coverage report
$ coverage html

# Build release package
$ python setup.py bdist_wheel

```
