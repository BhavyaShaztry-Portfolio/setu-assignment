from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import cast, Date, func
from app.database import get_db
from app.models import Transaction
from app.schemas import EventCreate
from app.services import process_event

router = APIRouter()


@router.post("/events")
def ingest_event(event: EventCreate, db: Session = Depends(get_db)):
    return process_event(event, db)


@router.get("/transactions")
def get_transactions(
    merchant_id: str | None = None,
    status: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    db: Session = Depends(get_db),
):
    query = db.query(Transaction)

    # Filters
    if merchant_id:
        query = query.filter(Transaction.merchant_id == merchant_id)

    if status:
        query = query.filter(Transaction.payment_status == status)

    if start_date:
        query = query.filter(Transaction.created_at >= start_date)

    if end_date:
        query = query.filter(Transaction.created_at <= end_date)

    # Sorting
    if sort_by == "created_at":
        if sort_order.lower() == "asc":
            query = query.order_by(Transaction.created_at.asc())
        else:
            query = query.order_by(Transaction.created_at.desc())

    elif sort_by == "amount":
        if sort_order.lower() == "asc":
            query = query.order_by(Transaction.amount.asc())
        else:
            query = query.order_by(Transaction.amount.desc())

    total = query.count()

    transactions = (
        query
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "transactions": [
            {
                "transaction_id": transaction.transaction_id,
                "merchant_id": transaction.merchant_id,
                "amount": transaction.amount,
                "currency": transaction.currency,
                "payment_status": transaction.payment_status,
                "settlement_status": transaction.settlement_status,
                "created_at": transaction.created_at,
            }
            for transaction in transactions
        ],
    }
@router.get("/transactions/{transaction_id}")
def get_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
):
    transaction = (
        db.query(Transaction)
        .filter(Transaction.transaction_id == transaction_id)
        .first()
    )

    if not transaction:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found",
        )

    return {
        "transaction_id": transaction.transaction_id,
        "merchant": {
            "merchant_id": transaction.merchant.merchant_id,
            "name": transaction.merchant.name,
        },
        "amount": transaction.amount,
        "currency": transaction.currency,
        "payment_status": transaction.payment_status,
        "settlement_status": transaction.settlement_status,
        "created_at": transaction.created_at,
        "updated_at": transaction.updated_at,
        "event_history": [
            {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "timestamp": event.event_timestamp,
            }
            for event in transaction.events
        ],
    }
@router.get("/reconciliation/summary")
def reconciliation_summary(
    db: Session = Depends(get_db),
):
    results = (
        db.query(
            Transaction.merchant_id,
            cast(Transaction.created_at, Date).label("date"),
            Transaction.payment_status,
            Transaction.settlement_status,
            func.count(Transaction.id).label("transaction_count"),
            func.sum(Transaction.amount).label("total_amount"),
        )
        .group_by(
            Transaction.merchant_id,
            cast(Transaction.created_at, Date),
            Transaction.payment_status,
            Transaction.settlement_status,
        )
        .order_by(
            cast(Transaction.created_at, Date).desc(),
            Transaction.merchant_id,
        )
        .all()
    )

    return {
        "summary": [
            {
                "merchant_id": row.merchant_id,
                "date": row.date,
                "payment_status": row.payment_status,
                "settlement_status": row.settlement_status,
                "transaction_count": row.transaction_count,
                "total_amount": round(float(row.total_amount or 0), 2),
            }
            for row in results
        ]
    }
@router.get("/reconciliation/discrepancies")
def reconciliation_discrepancies(
    db: Session = Depends(get_db),
):
    transactions = (
        db.query(Transaction)
        .filter(
            (
                (Transaction.payment_status == "processed")
                & (Transaction.settlement_status != "settled")
            )
            |
            (
                (Transaction.payment_status == "failed")
                & (Transaction.settlement_status == "settled")
            )
        )
        .order_by(Transaction.created_at.desc())
        .all()
    )

    discrepancies = []

    for transaction in transactions:
        if (
            transaction.payment_status == "processed"
            and transaction.settlement_status != "settled"
        ):
            reason = "Payment processed but not settled"

        elif (
            transaction.payment_status == "failed"
            and transaction.settlement_status == "settled"
        ):
            reason = "Payment failed but settlement exists"

        else:
            reason = "Inconsistent payment and settlement state"

        discrepancies.append(
            {
                "transaction_id": transaction.transaction_id,
                "merchant_id": transaction.merchant_id,
                "amount": transaction.amount,
                "currency": transaction.currency,
                "payment_status": transaction.payment_status,
                "settlement_status": transaction.settlement_status,
                "reason": reason,
            }
        )

    return {
        "count": len(discrepancies),
        "discrepancies": discrepancies,
    }