import asyncio
import os

import pytest
from sum_ai.quota import QuotaManager, QuotaRejected


@pytest.mark.skipif(not os.environ.get("REDIS_URL"), reason="REDIS_URL required")
def test_distributed_request_and_model_limits():
    from uuid import uuid4

    from redis.asyncio import Redis

    async def exercise():
        redis = Redis.from_url(os.environ["REDIS_URL"])
        one, two = QuotaManager(redis), QuotaManager(redis)
        actor = "test-" + str(uuid4())
        for _ in range(10):
            await one.admit_request(actor)
        with pytest.raises(QuotaRejected) as error:
            await two.admit_request(actor)
        assert error.value.retry_after > 0
        reservations = [await one.reserve(actor, "ollama", "test", 100) for _ in range(4)]
        with pytest.raises(QuotaRejected):
            await two.reserve(actor, "ollama", "test", 100)
        await one.settle(reservations[0], 50)
        await one.release(reservations[1])
        fifth = await two.reserve(actor, "ollama", "test", 100)
        await two.release(fifth)
        for reservation in reservations[2:]:
            await one.release(reservation)
        await redis.aclose()

    asyncio.run(exercise())


def test_fail_closed_without_redis():
    class BrokenRedis:
        async def eval(self, *_args):
            raise ConnectionError("offline")

    async def exercise():
        with pytest.raises(QuotaRejected) as error:
            await QuotaManager(BrokenRedis()).reserve("admin", "openai", "model", 100)
        assert error.value.status == 503

    asyncio.run(exercise())
