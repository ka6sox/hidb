# start by pulling the python image
FROM python:3.13.2-bookworm

# Make a working directory
RUN mkdir /hidb
WORKDIR /hidb

# Copy requirements first for layer caching
# Details: https://pythonspeed.com/articles/docker-caching-model/
COPY requirements.txt /hidb/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application
COPY . /hidb

# Turn off debugging in production
ENV FLASK_DEBUG=0

ENV FLASK_APP=hidb
ENV FLASK_RUN_HOST=0.0.0.0
EXPOSE 5000

CMD ["gunicorn", "-b", "0.0.0.0:5000", "hidb.run:application"]
