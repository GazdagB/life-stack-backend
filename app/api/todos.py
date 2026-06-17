from datetime import date
from typing import Literal

from fastapi import APIRouter
from app.repositories.todos_repository import query_all_todos, query_post_todo,query_update_todo, query_delete_todo
from pydantic import BaseModel
router = APIRouter(
    prefix="/todos",
    tags=["todos"]
)

class TodoCreate(BaseModel):
    title: str
    description: str = ""
    priority: Literal["P1" , "P2" , "P3" , "P4" ,"P5"] = "P3"
    due_date: date | None = None
    status: Literal["not_started", "in_progress", "completed", "canceled"] = "not_started"
    sort_order: int | None = 0
    source:  Literal["manual", "cybro", "import", "system"] = "manual"


@router.get("/")
def get_all():
    return query_all_todos()

@router.post("/")
def create_one(todo: TodoCreate):
    return query_post_todo(todo)

@router.put("/{todo_id}")
def update_one(todo: TodoCreate, todo_id: int):
    return query_update_todo(todo_id,todo)

@router.delete("/{todo_id}")
def delete_one(todo_id: int): 
    return query_delete_todo(todo_id)