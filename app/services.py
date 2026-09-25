
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Merchant, PaymentEvent, Transaction
from app.schemas import EventCreate


def process_event(event: EventCreate, db: Session):
    # Fast path for normal duplicate requests
    existing_event = (
        db.query(PaymentEvent)
        .filter(PaymentEvent.event_id == event.event_id)
        .first()
    )

    if existing_event:
        return {
            "status": "duplicate",
            "message": "Event already processed",
            "event_id": event.event_id,
        }

    try:
        # Find or create merchant
        merchant = (
            db.query(Merchant)
            .filter(Merchant.merchant_id == event.merchant_id)
            .first()
        )

        if not merchant:
            merchant = Merchant(
                merchant_id=event.merchant_id,
                name=event.merchant_name,
            )
            db.add(merchant)
            db.flush()

        # Find or create transaction
        transaction = (
            db.query(Transaction)
            .filter(Transaction.transaction_id == event.transaction_id)
            .first()
        )

        if not transaction:
            transaction = Transaction(
                transaction_id=event.transaction_id,
                merchant_id=event.merchant_id,
                amount=event.amount,
                currency=event.currency,
                payment_status="initiated",
                settlement_status="pending",
                created_at=event.timestamp,
            )
            db.add(transaction)
            db.flush()

        # Store event history
        payment_event = PaymentEvent(
            event_id=event.event_id,
            event_type=event.event_type,
            transaction_id=event.transaction_id,
            merchant_id=event.merchant_id,
            amount=event.amount,
            currency=event.currency,
            event_timestamp=event.timestamp,
        )

        db.add(payment_event)

        # Update current transaction state
        if event.event_type == "payment_initiated":
            transaction.payment_status = "initiated"

        elif event.event_type == "payment_processed":
            transaction.payment_status = "processed"

        elif event.event_type == "payment_failed":
            transaction.payment_status = "failed"

        elif event.event_type == "settled":
            transaction.settlement_status = "settled"

        db.commit()

        return {
            "status": "processed",
            "event_id": event.event_id,
            "transaction_id": transaction.transaction_id,
            "payment_status": transaction.payment_status,
            "settlement_status": transaction.settlement_status,
        }

    except IntegrityError:
        db.rollback()

        # The unique event_id constraint protects against
        # concurrent duplicate requests.
        existing_event = (
            db.query(PaymentEvent)
            .filter(PaymentEvent.event_id == event.event_id)
            .first()
        )

        if existing_event:
            return {
                "status": "duplicate",
                "message": "Event already processed",
                "event_id": event.event_id,
            }

        raise

