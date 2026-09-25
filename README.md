# Setu Payment Reconciliation Service

A lightweight payment event ingestion and reconciliation backend built with **FastAPI, PostgreSQL, SQLAlchemy, and Pydantic**.

The service ingests payment lifecycle events, maintains transaction state and event history, supports transaction filtering/pagination, and exposes reconciliation summaries and discrepancies.

## Tech Stack

* Python 3.10
* FastAPI
* PostgreSQL
* SQLAlchemy
* Pydantic
* Uvicorn
* Pytest
* Render for deployment

## Architecture

```text
Payment Events
      |
      
      v
POST /events
      |
      v
FastAPI + Pydantic Validation
      |
      v
Service Layer
      |
      +--------------------+
      |                    |
      v                    v
transactions         payment_events
      |
      v
PostgreSQL
      |
      +-----------------------------+
      |              |              |
      v              v              v
Transactions   Reconciliation   Discrepancies
     API           Summary           API
```

The application is organized into:

```text
app/
├── main.py       # FastAPI application and health endpoints
├── database.py   # SQLAlchemy engine and database session
├── models.py     # Database models
├── schemas.py    # Pydantic request schemas
├── routes.py     # API endpoints
└── services.py   # Event processing and idempotency logic
```

## Database Design

The service uses three core tables:

### `merchants`

Stores merchant information.

Key fields:

* `id`
* `merchant_id`
* `name`
* `created_at`

### `transactions`

Stores the current state of each transaction.

Key fields:

* `transaction_id`
* `merchant_id`
* `amount`
* `currency`
* `payment_status`
* `settlement_status`
* `created_at`
* `updated_at`

Indexes are created for commonly filtered fields such as merchant, payment status, creation date, and merchant/status combinations.

### `payment_events`

Stores the complete event history.

Key fields:

* `event_id`
* `event_type`
* `transaction_id`
* `merchant_id`
* `amount`
* `currency`
* `event_timestamp`

A unique constraint on `event_id` provides database-level protection against duplicate event ingestion.

Payment and settlement/reconciliation state are maintained on the `transactions` table, while `payment_events` preserves the complete event history.

## API Endpoints

### 1. Ingest Event

**POST `/events`**

Accepts:

* `payment_initiated`
* `payment_processed`
* `payment_failed`
* `settled`

Example request:

```json
{
  "event_id": "event-001",
  "event_type": "payment_initiated",
  "transaction_id": "txn-001",
  "merchant_id": "merchant-1",
  "merchant_name": "Example Merchant",
  "amount": 1000,
  "currency": "INR",
  "timestamp": "2026-09-25T10:00:00Z"
}
```

The endpoint is idempotent using the event ID.

A duplicate event returns:

```json
{
  "status": "duplicate",
  "message": "Event already processed",
  "event_id": "event-001"
}
```

### 2. List Transactions

**GET `/transactions`**

Supports:

* `merchant_id`
* `status`
* `start_date`
* `end_date`
* `page`
* `page_size`
* `sort_by`
* `sort_order`

Example:

```text
GET /transactions?merchant_id=merchant_2&page=1&page_size=5
```

Filtering, sorting, counting, and pagination are performed in SQL rather than by loading the full dataset into Python.

### 3. Transaction Details

**GET `/transactions/{transaction_id}`**

Returns:

* transaction details
* merchant information
* payment status
* settlement status
* complete event history

### 4. Reconciliation Summary

**GET `/reconciliation/summary`**

Returns transaction counts and total amounts grouped by:

* merchant
* date
* payment status
* settlement status

Aggregation is performed using SQL `GROUP BY`, `COUNT`, and `SUM`.

### 5. Reconciliation Discrepancies

**GET `/reconciliation/discrepancies`**

Identifies inconsistent payment and settlement states.

Current rules include:

* Payment processed but not settled
* Payment failed but settlement exists

The response includes the transaction and a human-readable discrepancy reason.

## Idempotency

Event ingestion is protected at two levels.

### Fast-path duplicate check

Before inserting an event, the service checks whether the `event_id` already exists.

If it exists, the API immediately returns a duplicate response.

### Database-level protection

`payment_events.event_id` has a unique constraint.

This protects against concurrent duplicate requests where two requests could otherwise both pass the initial existence check.

If a concurrent insert violates the unique constraint, the transaction is rolled back and the existing event is returned as a duplicate.

This ensures that duplicate events do not create duplicate event-history records.

## Sample Data

The supplied sample dataset contains:

* 10,355 input events
* 10,165 unique events
* 190 duplicate events
* 5 merchants
* 3,800 transactions
* 10,165 stored payment events

The dataset includes successful, failed, pending, duplicate, and unreconciled scenarios.

The seeded dataset currently contains reconciliation discrepancies including:

* 380 transactions that are processed but not settled
* 95 transactions that are failed but settled
* 475 total discrepancy records

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/BhavyaShaztry-Portfolio/setu-assignment.git
cd setu-assignment
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it on Windows:

```powershell
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure PostgreSQL

Create a PostgreSQL database named:

```text
setu_payments
```

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/setu_payments
```


### 5. Run the application

```bash
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

Swagger documentation:

```text
http://127.0.0.1:8000/docs
```

### 6. Seed sample data

```bash
python seed_data.py
```

The seed script reads:

```text
hiring-assignments/solutions-engineer/sample_events.json
```

and processes the events through the same event-processing service used by the API.

## Testing

Run:

```bash
pytest
```

The project includes tests covering:

* health endpoint
* invalid event validation
* transaction not found handling
* transaction listing and pagination

## Deployment

The service is deployed on Render.

**Base URL:**

```text
https://setu-assignment-dsci.onrender.com
```

Swagger:

```text
https://setu-assignment-dsci.onrender.com/docs
```

Database connectivity can be checked using:

```text
GET /db-health
```

## Postman Collection

A Postman collection is included as part of the submission.

It demonstrates:

1. POST event ingestion
2. Transaction pagination
3. Merchant filtering
4. Status filtering
5. Date filtering
6. Transaction details
7. Reconciliation summary
8. Reconciliation discrepancies

## Design Decisions and Trade-offs

### SQL-based filtering and aggregation

Filtering, pagination, sorting, counting, and reconciliation aggregation are implemented in SQL through SQLAlchemy rather than processing large datasets in Python.

### Database-level idempotency

The unique `event_id` constraint provides protection even under concurrent duplicate requests.

### SQLAlchemy `create_all`

For this assignment, SQLAlchemy `Base.metadata.create_all()` is used to keep local setup simple.

For a production system with evolving schemas, a migration tool such as Alembic would be preferable.

### Event history

Events are stored independently from the current transaction state so that the service maintains an auditable event history.

### Current-state model

The `transactions` table stores the latest payment and settlement state for efficient querying, while the event table retains the underlying history.

## Assumptions

* `event_id` uniquely identifies an incoming event.
* Transaction IDs are unique.
* Merchant IDs are unique.
* Currency is stored as provided by the event.
* Settlement events update settlement state independently of payment state.
* Reconciliation discrepancies are derived from the current payment and settlement state.
* The supplied sample events are assumed to represent the expected lifecycle ordering for the assignment.

## AI Disclosure

AI tool (chatgpt) was used during development for assistance with debugging, documentation.


