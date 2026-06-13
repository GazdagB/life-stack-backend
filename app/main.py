from fastapi import FastAPI
from app.api.expenses import router as expenses_router

app = FastAPI()

app.include_router(expenses_router)

@app.get("/")
async def root():
    return {"message": "LifeStack OS API is running!"}
