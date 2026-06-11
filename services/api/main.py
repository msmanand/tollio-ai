import os

from app.routes import router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="Tollio AI API",
    description="Backend contracts for budget-aware toll commute planning.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ] + [origin.strip() for origin in os.getenv("TOLLIO_CORS_ORIGINS", "").split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(router)
