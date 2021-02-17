"""
Checks websites and publishes stats on Kafka.
"""
from async_cron.schedule import Scheduler
from async_cron.job import CronJob
from aiokafka import AIOKafkaProducer
import httpx
import asyncio
import time
import logging
import json
import os
import sys
from aiokafka.helpers import create_ssl_context


# Service environment
WEBSITE_MONITOR_ENVIRONMENT = os.environ.get(
    "WEBSITE_MONITOR_ENVIRONMENT", "development")

# Configuration
config = {}
with open(f'./config/{WEBSITE_MONITOR_ENVIRONMENT}.json') as json_file:
    config = json.loads(json_file.read())

SITES = config.get('sites', [])

KAFKA_HOST = os.environ.get('kafka_host', config.get('kafka_host'))
KAFKA_TOPIC = os.environ.get('kafka_topic', config.get('kafka_topic'))
KAFKA_SSL_CA = os.environ.get('kafka_ssl_ca', config.get('kafka_ssl_ca'))
KAFKA_SSL_CERT = os.environ.get('kafka_ssl_cert', config.get('kafka_ssl_cert'))
KAFKA_SSL_KEY = os.environ.get('kafka_ssl_key', config.get('kafka_ssl_key'))

# Logging
logging.basicConfig(level=os.environ.get(
    "log_level", config.get('log_level', "INFO")))
log = logging.getLogger(__name__)


async def check_site(producer, site, kafka_topic):
    url = site['url']
    log.info(f'Checking {url}')
    try:
        async with httpx.AsyncClient() as http_client:
            checked_at = time.time()
            start_time = time.monotonic()
            res = await http_client.get(url)
            duration = time.monotonic() - start_time
            msg = {
                'checked_at': checked_at,
                'status_code': res.status_code,
                'url': url,
                're_check': None,
                'duration': duration
            }
            await producer.send_and_wait(kafka_topic, msg)
            log.info(f'Finished checking {url}')
    except Exception as e:
        log.error(f'Got error checking {url}: {e}')
        raise e


def serializer(value):
    return json.dumps(value).encode()


async def main(
    kafka_topic=KAFKA_TOPIC,
    sites=SITES,
    run_total=None
):

    ssl_context = None
    security_protocol = 'PLAINTEXT'
    if KAFKA_SSL_CA is not None:
        ssl_context = create_ssl_context(
            cafile=KAFKA_SSL_CA,
            certfile=KAFKA_SSL_CERT,
            keyfile=KAFKA_SSL_KEY
        )
        security_protocol = 'SSL'

    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_HOST,
        value_serializer=serializer,
        security_protocol=security_protocol,
        ssl_context=ssl_context
    )

    msh = Scheduler()
    try:
        for site in sites:
            url = site['url']
            log.info(f'Monitoring {url}')
            msh.add_job(
                CronJob(run_total=run_total, name=f'check_{url}')
                .every().second.go(check_site, producer, site, kafka_topic))
        await producer.start()
        await msh.start()
    except Exception as e:
        log.error(f'Got error starting scheduler: {e}')
        raise e
    finally:
        await producer.stop()

if __name__ == "__main__":
    log.info('Starting website-monitor producer')
    try:
        asyncio.run(main())
        sys.exit(0)
    except Exception as e:
        log.error(f'Got error, exiting {e}')
        sys.exit(1)
