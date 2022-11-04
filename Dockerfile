# start by pulling the python image
FROM python:3.9.15-bullseye

# Make a working directory
RUN mkdir /hidb
WORKDIR /hidb

# First, copy the requirements.txt only as it helps with caching
# Details: https://pythonspeed.com/articles/docker-caching-model/
COPY ./requirements.txt /hidb
RUN pip install -r requirements.txt

# Copy the source code
COPY . /hidb

# Turn of debugging in production
ENV FLASK_DEBUG 0

# Set entrypoint
ENV FLASK_APP flask_run.py
ENV FLASK_RUN_HOST 0.0.0.0
EXPOSE 4000

# Run Flask command
CMD ["gunicorn", "-b", "0.0.0.0:5000", "hidb.run:application"]
