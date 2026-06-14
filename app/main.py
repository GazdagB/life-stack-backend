from fastapi import FastAPI
from app.api.expenses import router as expenses_router
from app.api.test_db import router as test_db_router
app = FastAPI()

app.include_router(expenses_router)
app.include_router(test_db_router)

@app.get("/")
async def root():
    return {"message": "LifeStack OS API is running!"}
