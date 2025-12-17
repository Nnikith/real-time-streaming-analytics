import json
import random
import time
import uuid
from datetime import datetime, timezone
from confluent_kafka import Producer

BOOTSTRAP = "localhost:9092"
TOPIC = "stream.events"

STREAM_IDS = ["stream_1001", "stream_1002", "stream_1003"]
USER_IDS = [f"user_{i}" for i in range(1, 500)]

EVENT_TYPES = ["stream_start", "stream_stop", "viewer_join", "viewer_leave", "chat_message", "donation"]

producer = Producer({"bootstrap.servers": BOOTSTRAP})

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def make_event() -> dict:
    et = random.choices(
        EVENT_TYPES,
        weights=[1, 1, 8, 7, 10, 2],
        k=1
    )[0]
    stream_id = random.choice(STREAM_IDS)
    user_id = random.choice(USER_IDS)

    payload = {
        "event_id": str(uuid.uuid4()),
        "ts": now_iso(),
        "event_type": et,
        "stream_id": stream_id,
        "user_id": user_id,
    }

    if et == "chat_message":
        payload["message_len"] = random.randint(1, 200)

    if et == "donation":
        payload["amount_usd"] = round(random.uniform(1, 200), 2)

    return payload

def delivery_report(err, msg):
    if err is not None:
        print(f"Delivery failed: {err}")

def main():
    print("Producing events to Kafka. Ctrl+C to stop.")
    try:
        while True:
            ev = make_event()
            key = ev["stream_id"]
            producer.produce(TOPIC, key=key, value=json.dumps(ev), callback=delivery_report)
            producer.poll(0)
            time.sleep(0.05)  # ~20 events/sec
    except KeyboardInterrupt:
        pass
    finally:
        producer.flush()

if __name__ == "__main__":
    main()
