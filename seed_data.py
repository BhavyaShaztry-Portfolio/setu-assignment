import json

from app.database import SessionLocal
from app.schemas import EventCreate
from app.services import process_event


SAMPLE_FILE = "hiring-assignments/solutions-engineer/sample_events.json"


def main():
    with open(SAMPLE_FILE, "r", encoding="utf-8") as file:
        events = json.load(file)

    print(f"Found {len(events)} events")

    db = SessionLocal()

    processed = 0
    duplicates = 0

    try:
        for raw_event in events:
            event = EventCreate(
                event_id=raw_event["event_id"],
                event_type=raw_event["event_type"],
                transaction_id=raw_event["transaction_id"],
                merchant_id=raw_event["merchant_id"],
                merchant_name=raw_event["merchant_name"],
                amount=raw_event["amount"],
                currency=raw_event["currency"],
                timestamp=raw_event["timestamp"],
            )

            result = process_event(event, db)

            if result["status"] == "processed":
                processed += 1
            else:
                duplicates += 1

        print(f"Processed: {processed}")
        print(f"Duplicates: {duplicates}")

    finally:
        db.close()


if __name__ == "__main__":
    main()