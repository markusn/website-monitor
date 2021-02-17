# website-monitor
[![Build Status](https://travis-ci.com/markusn/website-monitor.svg?branch=master)](https://travis-ci.com/markusn/website-monitor)

A simple website monitor based on Kafka and Postgres. The application is
split into a producer which checks the websites and a consumer which persists
the website stats.

# Design
The `producer` checks a pre-configured list of websites every second for stats
which are published on a configured Kafka topic. Each website is checked
asynchronously which gives good performance even when configured to check many
slow sites.

The message published on Kafka MUST be JSON and MUST contain the field `url`
which must contain the url being checked.

The `consumer` consumes messages from the pre-configured Kafka topic and
persists these to Postgres. Each message is processed asynchronously. The
`url` field from the message is stored in a separate indexed (unique) column
for fast lookups. All other fields are stored as a JSONB.  

# Requirements
Python 3.8.5

# Configuration
The producer and consumer are configured separately. An example
configuration file can be found in `producer/config/development.json` and
`consumer/config/development.json`.

A new configuration file should be added
for each environment. As an example: for the production environment add a
file `production.json` to the appropriate folder. To make the application aware
of which environment it is running in set the `WEBSITE_MONITOR_ENVIRONMENT`
environment variable.

Each key in the configuration file can be overridden by a environment
variable with the same name. The most important ones being `kafka_host`
and `postgres_uri`.

As an example: to override the Kafka host without modifying the configuration
file run the producer/consumer as:

```bash
kafka_host=YOUR_NEW_EPIC_HOST python app.py
```

## Configure Kafka SSL authentication
To configure Kafka SSL authentication grab the CA, Certificate and Key files.
Configure `kafka_ssl_ca`, `kafka_ssl_cert` and `kafka_ssl_key` to point to the
files.

Example:

```bash
kafka_host=YOUR_NEW_EPIC_HOST \
kafka_ssl_ca=ca.pem \
kafka_ssl_cert=service.cert \
kafka_ssl_key=service.key \
python app.py
```

# Running
To install the deps and run both services on the same machine use the
run script:

```bash
kafka_host=YOUR_HOST postgres_uri=YOUR_POSTGRES_URI ./run.sh
```

# Deployment
Build the Docker recipes and deploy using your favorite container
provider.

```bash
cd producer
docker build .
cd ../consumer
docker build .
```

# Linting
`flake8` is used for linting, run as part of the `test.sh` script.

# Tests
The tests assume that Kafka and Postgres are already up and running. The
existing tests are basic "system level" tests, i.e. the test scope is
testing each individual service and not their interactions.

(Optional) Start Kafka and Postgres locally using `docker-compose`:

```bash
docker-compose up -d
```

To install deps and run linting and system tests use the test script:

```bash
./test.sh
```