"""
Consumes website stats from Kafka and persist them in Postgres.
"""
from aiokafka import AIOKafkaConsumer
from aiokafka.helpers import create_ssl_context
import aiopg
import asyncio
import logging
import json
import os
import sys
import glob
import urllib.parse

# Service environment
WEBSITE_MONITOR_ENVIRONMENT = os.environ.get(
    "WEBSITE_MONITOR_ENVIRONMENT", "development")

# Configuration
config = {}
with open(f'./config/{WEBSITE_MONITOR_ENVIRONMENT}.json') as json_file:
    config = json.loads(json_file.read())

KAFKA_HOST = os.environ.get('kafka_host', config.get('kafka_host'))
KAFKA_TOPIC = os.environ.get('kafka_topic', config.get('kafka_topic'))
KAFKA_SSL_CA = os.environ.get('kafka_ssl_ca', config.get('kafka_ssl_ca'))
KAFKA_SSL_CERT = os.environ.get('kafka_ssl_cert', config.get('kafka_ssl_cert'))
KAFKA_SSL_KEY = os.environ.get('kafka_ssl_key', config.get('kafka_ssl_key'))
POSTGRES_URI = os.environ.get('postgres_uri', config.get('postgres_uri'))

# Logging
log = logging.getLogger(__name__)
logging.basicConfig(level=os.environ.get(
    "log_level", config.get('log_level', "INFO")))


def deserializer(serialized):
    return json.loads(serialized)


async def main(
    kafka_topic=KAFKA_TOPIC
):
    parse_result = urllib.parse.urlparse(POSTGRES_URI)
    pool = await aiopg.create_pool(
        host=parse_result.hostname,
        port=parse_result.port,
        user=parse_result.username,
        password=parse_result.password,
        dbname=parse_result.path[1:]
    )
    await run_migrations(pool)
    await consume(pool, KAFKA_HOST, kafka_topic)


async def run_migrations(pool):
    async with pool.acquire() as conn:
        for fname in sorted(glob.glob('./migrations/*.sql')):
            log.info(f'Running migrations in {fname}')
            with open(fname) as file:
                async with conn.cursor() as cur:
                    await cur.execute(file.read())


async def consume(pool, kafka_host, kafka_topic):
    ssl_context = None
    security_protocol = 'PLAINTEXT'
    if KAFKA_SSL_CA is not None:
        ssl_context = create_ssl_context(
            cafile=KAFKA_SSL_CA,
            certfile=KAFKA_SSL_CERT,
            keyfile=KAFKA_SSL_KEY
        )
        security_protocol = 'SSL'

    consumer = AIOKafkaConsumer(
        kafka_topic,
        auto_offset_reset='latest',
        value_deserializer=deserializer,
        bootstrap_servers=kafka_host,
        security_protocol=security_protocol,
        ssl_context=ssl_context
    )
    await consumer.start()
    try:
        async for msg in consumer:
            asyncio.create_task(handle_message(pool, msg))
    except Exception as e:
        raise e
    finally:
        await consumer.stop()


async def handle_message(pool, msg):
    val = msg.value
    log.info(f'Handling message {val}')
    url = val['url']
    log.info(f'Got new stats for {url}')
    jsonb = json.dumps(val)
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(" ".join([
                "INSERT INTO site (url, data) VALUES (%s, %s)",
                "ON CONFLICT ON CONSTRAINT site_url_key",
                "DO UPDATE SET data = %s"
            ]), (url, jsonb, jsonb))
            log.info(f'Persisted stats for {url}')

if __name__ == "__main__":
    log.info('Starting website-monitor consumer')
    try:
        asyncio.run(main())
        sys.exit(0)
    except Exception as e:
        log.error(e)
        sys.exit(1)
