from fastapi import FastAPI
from sqlalchemy import text

from app.database import Base, engine
from app import models
from app.routes import router



Base.metadata.create_all(bind=engine)



app = FastAPI(
    title="Setu Payment Reconciliation Service",
    version="1.0.0",
)

app.include_router(router)

@app.get("/")
def health_check():
    return {
        "status": "ok",
        "message": "Payment service is running",
    }


@app.get("/db-health")
def database_health():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        return {
            "database": "connected",
            "result": result.scalar(),
        }