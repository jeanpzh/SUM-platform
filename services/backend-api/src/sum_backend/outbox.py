from __future__ import annotations

import logging
import os
import signal
import threading

from .config import Settings
from .repository import PostgresJobs


def dispatch_once(repository, publisher) -> int:
    delivered = 0
    for row in repository.claim_outbox(limit=10):
        try:
            publisher.send(str(row["id"]), row["event_name"], row["payload"])
            repository.ack_outbox(row)
            delivered += 1
        except Exception:
            repository.retry_outbox(row)
            logging.getLogger(__name__).warning(
                "Despacho pendiente; se reintentará. event_id=%s", row["id"]
            )
    return delivered


class InngestPublisher:
    def __init__(self):
        import httpx

        base = os.environ.get("INNGEST_EVENT_BASE_URL", "http://localhost:8288").rstrip("/")
        key = os.environ["INNGEST_EVENT_KEY"]
        self.url = f"{base}/e/{key}"
        self.client = httpx.Client(timeout=10)

    def send(self, event_id: str, name: str, data: dict):
        response = self.client.post(self.url, json={"id": event_id, "name": name, "data": data})
        response.raise_for_status()
        result = response.json()
        if result.get("status", 200) != 200 or not result.get("ids"):
            raise RuntimeError("El orquestador no confirmó la recepción.")

    def close(self):
        self.client.close()


def main():
    logging.basicConfig(level=logging.INFO)
    settings = Settings.from_env()
    repository = PostgresJobs(settings.database_url, settings.pool_size, settings.max_pending_jobs)
    repository.open()
    publisher = InngestPublisher()
    stop = threading.Event()
    for sig in [signal.SIGTERM, signal.SIGINT]:
        signal.signal(sig, lambda *_: stop.set())
    try:
        while not stop.is_set():
            try:
                dispatch_once(repository, publisher)
            except Exception:
                logging.warning("No se pudo consultar el outbox; se reintentará.")
            stop.wait(1)
    finally:
        publisher.close()
        repository.close()


if __name__ == "__main__":
    main()
