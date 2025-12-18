import json
import random
import time
import uuid
import os
from datetime import datetime, timezone
from confluent_kafka import Producer

# -----------------------------
# Config (env overrides)
# -----------------------------
BOOTSTRAP = os.getenv("BOOTSTRAP", "kafka:29092")
TOPIC = os.getenv("TOPIC", "stream.events")

STREAM_IDS = os.getenv("STREAM_IDS", "stream_1001,stream_1002,stream_1003").split(",")

USER_COUNT = int(os.getenv("USER_COUNT", "500"))
USER_IDS = [f"user_{i}" for i in range(1, USER_COUNT + 1)]

# Events per second (default 20)
EVENTS_PER_SEC = float(os.getenv("EVENTS_PER_SEC", "20"))
SLEEP_SECONDS = 1.0 / EVENTS_PER_SEC if EVENTS_PER_SEC > 0 else 0.05

EVENT_TYPES = ["stream_start", "stream_stop", "viewer_join", "viewer_leave", "chat_message", "donation"]

# Weights: tweak as you like
EVENT_WEIGHTS = [1, 1, 8, 7, 10, 2]

producer = Producer({
    "bootstrap.servers": BOOTSTRAP,
    # good defaults for local dev
    "enable.idempotence": True,
    "acks": "all",
    "retries": 10,
    "linger.ms": 10,
})


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_event() -> dict:
    et = random.choices(EVENT_TYPES, weights=EVENT_WEIGHTS, k=1)[0]
    stream_id = random.choice(STREAM_IDS)
    user_id = random.choice(USER_IDS)

    payload = {
        "event_id": str(uuid.uuid4()),
        "ts": now_iso(),
        "event_type": et,
        "stream_id": stream_id,
        "user_id": user_id,
    }

    # Optional fields
    if et == "chat_message":
        payload["message_len"] = random.randint(1, 200)

    if et == "donation":
        payload["amount_usd"] = round(random.uniform(1, 200), 2)

    return payload


def delivery_report(err, msg):
    if err is not None:
        print(f"Delivery failed: {err}")


def main():
    print(f"Producing events to Kafka topic={TOPIC} bootstrap={BOOTSTRAP} rate={EVENTS_PER_SEC}/sec. Ctrl+C to stop.")
    try:
        while True:
            ev = make_event()
            key = ev["stream_id"]
            producer.produce(
                TOPIC,
                key=key,
                value=json.dumps(ev).encode("utf-8"),
                callback=delivery_report,
            )
            producer.poll(0)  # serve delivery callbacks
            time.sleep(SLEEP_SECONDS)
    except KeyboardInterrupt:
        pass
    finally:
        producer.flush(10)


if __name__ == "__main__":
    main()
