# hidb

Home Inventory DataBase

**Note: this README is a work in progress.**

## Setting up for development

**The below steps are only meant for running this code in a development environment.** If you intend
to run this in production, please see "Running in a Production setting" below.

Use [Pyenv](https://github.com/pyenv/pyenv) to manage multiple Python versions.

```shell
# Developed using Python 3.9.5
$ pyenv install 3.9.5

# Set up a Python virtualenv
$ python3 -m venv env
$ source env/bin/activate

# Install dependencies
$ pip3 install -r requirements.txt

# Init the db schema
$ flask --app hidb init-db

# Run the app
# The web app will be accessable at http://localhost:5000/
# Add "-host=0.0.0.0" to allow access from the network; otherwise only localhost is allowed
# This should NOT be used in a production environment!
$ flask --app hidb --debug run

# Run unit tests
$ pytest

# Measure code coverage
$ coverage run -m pytest
$ coverage report
$ coverage html
```

## Running in a Production setting

Use one of the [supported methods of deploying a Flask app](https://flask.palletsprojects.com/en/2.0.x/deploying/).
There are many options available, both commercial/third-party and self-hosted.

```shell
# Build release package
$ python setup.py bdist_wheel
```

This repository also contains the configuration necessary to deploy this app in a [Docker](https://www.docker.com/)
container, which is another viable option for hosting this app.

```shell
# Build Docker container
# Note: must re-run this command to incorporate changes
$ docker-compose build

# Start up Docker container
$ docker-compose up

# Shut down Docker container
$ docker-compose down
```
