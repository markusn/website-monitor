import pytest
import random
import string
import json
import asyncio
import aiopg
from aiokafka import AIOKafkaProducer
import urllib.parse

from app import main, KAFKA_HOST, POSTGRES_URI

parse_result = urllib.parse.urlparse(POSTGRES_URI)


@pytest.mark.asyncio
async def test_main():
    """
    Assert that consuming three websites stats messages persists the
    expected results.
    """
    # random kafka topic to start with a clean slate
    kafka_topic = ''.join(random.choices(
        string.ascii_uppercase + string.digits, k=10))

    # clear db
    async with aiopg.connect(
        host=parse_result.hostname,
        port=parse_result.port,
        user=parse_result.username,
        password=parse_result.password,
        dbname=parse_result.path[1:]
    ) as conn:
        async with conn.cursor() as cur:
            await cur.execute('DROP TABLE IF EXISTS site')

    # start the great consumer
    task = asyncio.create_task(main(kafka_topic=kafka_topic))

    # wait a bit
    await asyncio.sleep(1)

    # start producing some epic messages
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_HOST,
        value_serializer=lambda x: json.dumps(x).encode()
    )
    await producer.start()
    messages = [
        {'url': 'http://foo.bar', 'key': 'valuefoo'},
        {'url': 'http://bar.baz', 'key': 'valuebar'},
        {'url': 'http://foo.bar', 'key': 'valuefooupdated'}
    ]
    for msg in messages:
        await producer.send_and_wait(kafka_topic, msg)

    await producer.stop()

    # give some time for the jobs to finish
    await asyncio.sleep(1)
    task.cancel()

    # check db contents
    rows = []
    async with aiopg.connect(
        host=parse_result.hostname,
        port=parse_result.port,
        user=parse_result.username,
        password=parse_result.password,
        dbname=parse_result.path[1:]
    ) as conn:
        async with conn.cursor() as cur:
            await cur.execute('SELECT * FROM site')
            async for row in cur:
                rows.append(row)
    assert len(rows) == 2
    rows = sorted(rows, key=lambda x: x[1])

    # url persisted in url column
    assert rows[0][1] == 'http://bar.baz'
    # whole message persisted in data
    assert rows[0][2] == {'url': 'http://bar.baz', 'key': 'valuebar'}

    # url persisted in url column
    assert rows[1][1] == 'http://foo.bar'
    # whole message persisted in data and updated by seconded message
    assert rows[1][2] == {'url': 'http://foo.bar', 'key': 'valuefooupdated'}
