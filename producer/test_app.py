import pytest
import random
import string
import json
import asyncio
from aiokafka import AIOKafkaConsumer

from app import main, KAFKA_HOST


@pytest.mark.asyncio
async def test_main():
    """
    Assert that checking two websites in the wild generates to Kafka messages
    with the expected payload.
    """
    # random kafka topic to start with a clean slate
    kafka_topic = ''.join(random.choices(
        string.ascii_uppercase + string.digits, k=10))

    # start async cron scheduler
    task = asyncio.create_task(
        main(
            sites=[
                {'url': 'https://google.se', 'regex': None},
                {'url': 'https://news.ycombinator.com', 'regex': None}
            ],
            kafka_topic=kafka_topic,
            run_total=1
        )
    )

    # give some time for the jobs to finish
    await asyncio.sleep(1)
    task.cancel()

    # check if the messages are in kafka
    consumer = AIOKafkaConsumer(
        kafka_topic,
        auto_offset_reset='earliest',
        value_deserializer=lambda x: json.loads(x),
        bootstrap_servers=KAFKA_HOST
    )
    await consumer.start()

    messages = []
    async for msg in consumer:
        messages.append(msg.value)
        if len(messages) == 2:
            break

    # assert we got the result for the sites
    messages = sorted(messages, key=lambda k: k['url'])
    expected_keys = ['checked_at', 'status_code',
                     'url', 're_check', 'duration']
    assert messages[0]['url'] == 'https://google.se'
    assert all(key in messages[0] for key in expected_keys)
    assert messages[1]['url'] == 'https://news.ycombinator.com'
    assert all(key in messages[1] for key in expected_keys)
    await consumer.stop()
