from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.expenses import router as expenses_router
from app.api.test_db import router as test_db_router
from app.api.todos import router as todos_router
from app.api.auth import router as auth_router
from app.api.recurring_expenses import router as recurring_expenses_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(expenses_router)
app.include_router(test_db_router)
app.include_router(todos_router)

app.include_router(auth_router)
app.include_router(recurring_expenses_router)

@app.get("/")
async def root():
    return {"message": "LifeStack OS API is running!"}
