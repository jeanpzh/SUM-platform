"""Atomic Redis quotas and leased model-call concurrency."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from uuid import uuid4

from sum_contracts.models import ServiceError

REQUEST_SCRIPT = """
if redis.call('EXISTS', KEYS[2]) == 1 then return {1, 0} end
local current = tonumber(redis.call('GET', KEYS[1]) or '0')
if current >= tonumber(ARGV[1]) then return {0, redis.call('TTL', KEYS[1])} end
current = redis.call('INCR', KEYS[1])
if current == 1 then redis.call('EXPIRE', KEYS[1], 60) end
redis.call('SET', KEYS[2], '1', 'EX', 120)
return {1, 0}
"""

STUDENT_REQUEST_SCRIPT = """
if redis.call('EXISTS', KEYS[3]) == 1 then return {1, 0} end
if tonumber(redis.call('GET', KEYS[1]) or '0') >= tonumber(ARGV[1]) then
  return {0, math.max(redis.call('TTL', KEYS[1]), 1)}
end
if tonumber(redis.call('GET', KEYS[2]) or '0') >= tonumber(ARGV[2]) then
  return {0, math.max(redis.call('TTL', KEYS[2]), 1)}
end
local minute = redis.call('INCR', KEYS[1])
if minute == 1 then redis.call('EXPIRE', KEYS[1], 60) end
redis.call('INCR', KEYS[2])
redis.call('EXPIRE', KEYS[2], ARGV[3])
redis.call('SET', KEYS[3], '1', 'EX', 120)
return {1, 0}
"""

RESERVE_SCRIPT = """
local now = tonumber(ARGV[1])
if #KEYS == 5 and tonumber(redis.call('GET', KEYS[5]) or '0') + tonumber(ARGV[4]) > tonumber(ARGV[8]) then
  return {0, math.max(redis.call('TTL', KEYS[5]), 1)}
end
redis.call('ZREMRANGEBYSCORE', KEYS[2], '-inf', now)
if tonumber(redis.call('GET', KEYS[1]) or '0') >= tonumber(ARGV[2]) then
  return {0, math.max(redis.call('TTL', KEYS[1]), 1)}
end
if redis.call('ZCARD', KEYS[2]) >= tonumber(ARGV[3]) then return {0, 2} end
if tonumber(redis.call('GET', KEYS[3]) or '0') + tonumber(ARGV[4]) > tonumber(ARGV[5]) then
  return {0, math.max(redis.call('TTL', KEYS[3]), 1)}
end
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], 60) end
local tokens = redis.call('INCRBY', KEYS[3], ARGV[4])
if tokens == tonumber(ARGV[4]) then redis.call('EXPIRE', KEYS[3], 60) end
redis.call('ZADD', KEYS[2], now + tonumber(ARGV[6]), ARGV[7])
redis.call('EXPIRE', KEYS[2], 180)
redis.call('SET', KEYS[4], ARGV[4], 'EX', 180)
if #KEYS == 5 then
  redis.call('INCRBY', KEYS[5], ARGV[4])
  redis.call('EXPIRE', KEYS[5], ARGV[9])
end
return {1, 0}
"""

SETTLE_SCRIPT = """
local reserved = redis.call('GET', KEYS[1])
if not reserved then return 0 end
redis.call('DEL', KEYS[1])
redis.call('ZREM', KEYS[2], ARGV[1])
local difference = tonumber(ARGV[2]) - tonumber(reserved)
if #KEYS == 4 and redis.call('EXISTS', KEYS[4]) == 1 and difference ~= 0 then
  redis.call('INCRBY', KEYS[4], difference)
end
if redis.call('EXISTS', KEYS[3]) == 1 and difference ~= 0 then
  redis.call('INCRBY', KEYS[3], difference)
end
return 1
"""


class QuotaRejected(ServiceError):
    def __init__(self, code: str, retry_after: int = 1, status: int = 429):
        super().__init__(code, "La capacidad de IA no está disponible. Intente más tarde.", status)
        self.retry_after = max(1, retry_after)


@dataclass(frozen=True)
class Reservation:
    id: str
    actor_key: str
    provider_key: str
    estimated_tokens: int
    expires_at_ms: int
    daily_key: str | None = None


class QuotaManager:
    def __init__(self, redis, request_limit: int = 10, provider_limit: int = 30,
                 concurrency_limit: int = 4, actor_tokens_per_minute: int = 80000,
                 student_requests_per_minute: int = 5, student_requests_per_day: int = 50,
                 student_tokens_per_minute: int = 20000, student_tokens_per_day: int = 100000):
        self.redis = redis
        self.request_limit = request_limit
        self.provider_limit = provider_limit
        self.concurrency_limit = concurrency_limit
        self.actor_tokens_per_minute = actor_tokens_per_minute
        self.student_requests_per_minute = student_requests_per_minute
        self.student_requests_per_day = student_requests_per_day
        self.student_tokens_per_minute = student_tokens_per_minute
        self.student_tokens_per_day = student_tokens_per_day

    @staticmethod
    def _key(value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()[:24]

    async def admit_request(self, actor_id: str, idempotency_key: str | None = None) -> None:
        if not actor_id or len(actor_id) > 200:
            raise ServiceError("AI_INPUT_INVALID", "El usuario no es válido.")
        key = "ai:req:" + self._key(actor_id)
        replay_key = key + ":replay:" + self._key(idempotency_key or str(uuid4()))
        try:
            if actor_id.startswith("student:"):
                import time
                now = int(time.time())
                daily = key + ":day:" + str(now // 86400)
                accepted, retry = await self.redis.eval(STUDENT_REQUEST_SCRIPT, 3, key, daily, replay_key,
                    self.student_requests_per_minute, self.student_requests_per_day, 86400 - now % 86400 + 180)
            else:
                accepted, retry = await self.redis.eval(REQUEST_SCRIPT, 2, key, replay_key, self.request_limit)
        except Exception as exc:
            raise QuotaRejected("AI_QUOTA_UNAVAILABLE", status=503) from exc
        if not accepted:
            raise QuotaRejected("AI_USER_RATE_LIMIT" if actor_id.startswith("student:") else "AI_ADMIN_RATE_LIMIT", int(retry))

    async def reserve(self, actor_id: str, provider: str, model: str,
                      estimated_tokens: int) -> Reservation:
        if not actor_id or not provider or not model or not 1 <= estimated_tokens <= 9000:
            raise ServiceError("AI_INPUT_INVALID", "La reserva de capacidad no es válida.")
        import time

        now_ms = int(time.time() * 1000)
        actor_key = self._key(actor_id)
        provider_key = self._key(provider)
        reservation_id = str(uuid4())
        minute = now_ms // 60000
        call_key = f"ai:calls:{provider_key}:{minute}"
        inflight_key = f"ai:inflight:{provider_key}"
        token_key = f"ai:tokens:{actor_key}:{minute}"
        reservation_key = f"ai:reservation:{reservation_id}"
        student = actor_id.startswith("student:")
        daily_key = f"ai:daily-tokens:{actor_key}:{now_ms // 86400000}" if student else None
        keys = [call_key, inflight_key, token_key, reservation_key]
        if daily_key:
            keys.append(daily_key)
        try:
            accepted, retry = await self.redis.eval(RESERVE_SCRIPT, len(keys), *keys,
                now_ms, self.provider_limit, self.concurrency_limit, estimated_tokens,
                self.student_tokens_per_minute if student else self.actor_tokens_per_minute,
                130000, reservation_id, self.student_tokens_per_day,
                86400 - (now_ms // 1000) % 86400 + 180)
        except Exception as exc:
            raise QuotaRejected("AI_QUOTA_UNAVAILABLE", status=503) from exc
        if not accepted:
            raise QuotaRejected("AI_PROVIDER_RATE_LIMIT", int(retry))
        return Reservation(reservation_id, token_key, inflight_key, estimated_tokens, now_ms + 130000, daily_key)

    async def settle(self, reservation: Reservation, used_tokens: int) -> None:
        if not 0 <= used_tokens <= 9000:
            raise ServiceError("AI_USAGE_INVALID", "El uso del modelo no es válido.")
        try:
            keys = [f"ai:reservation:{reservation.id}", reservation.provider_key, reservation.actor_key]
            if reservation.daily_key:
                keys.append(reservation.daily_key)
            await self.redis.eval(SETTLE_SCRIPT, len(keys), *keys,
                                  reservation.id, used_tokens)
        except Exception as exc:
            raise QuotaRejected("AI_QUOTA_UNAVAILABLE", status=503) from exc

    async def release(self, reservation: Reservation) -> None:
        await self.settle(reservation, 0)
