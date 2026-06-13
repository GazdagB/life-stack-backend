from fastapi import APIRouter

router = APIRouter(
    prefix="/expenses",
    tags=["expenses"],
)


@router.get("/")
def get_expenses():
    return {"message": "GET /expenses"}

@router.post("")
def create_expense():
    return {"message": "POST /expenses"}
