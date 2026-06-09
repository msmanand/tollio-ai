from app.routes import router
from fastapi import FastAPI


app = FastAPI(
    title="Tollio AI API",
    description="Backend contracts for budget-aware toll commute planning.",
    version="0.1.0",
)

app.include_router(router)
