from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from app.repositories.todo_ai_repository import (
    get_todos_for_assessment,
    list_todo_assessments,
    upsert_todo_assessments,
)
from app.repositories.todos_repository import query_all_todos, query_post_todo,query_update_todo, query_delete_todo
from app.services.auth_service import get_current_user_id
from app.services.todo_ai_service import add_staleness, assess_todos
from pydantic import BaseModel, Field
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


class TodoAssessRequest(BaseModel):
    todo_ids: list[int] | None = Field(default=None, max_length=30)
    language: Literal["en", "de", "hu"] = "en"


@router.get("/")
def get_all(current_user_id: int = Depends(get_current_user_id)):
    return query_all_todos(current_user_id)

@router.post("/")
def create_one(todo: TodoCreate, current_user_id: int = Depends(get_current_user_id)):
    return query_post_todo(current_user_id, todo)


@router.get("/ai-assessments")
def get_ai_assessments(current_user_id: int = Depends(get_current_user_id)):
    return {"assessments": add_staleness(list_todo_assessments(current_user_id))}


@router.post("/ai-assess")
def assess_selected_todos(
    request: TodoAssessRequest,
    current_user_id: int = Depends(get_current_user_id),
):
    todos = get_todos_for_assessment(current_user_id, request.todo_ids)
    if request.todo_ids and len(todos) != len(set(request.todo_ids)):
        raise HTTPException(status_code=404, detail="One or more TODOs were not found")
    assessments, provider_status, warning = assess_todos(todos, request.language)
    if assessments:
        upsert_todo_assessments(current_user_id, assessments)
    return {
        "assessments": add_staleness(list_todo_assessments(
            current_user_id,
            [todo["id"] for todo in todos],
        )),
        "provider_status": provider_status,
        "warning": warning,
    }

@router.put("/{todo_id}")
def update_one(todo: TodoCreate, todo_id: int, current_user_id: int = Depends(get_current_user_id)):
    return query_update_todo(current_user_id, todo_id, todo)

@router.delete("/{todo_id}")
def delete_one(todo_id: int, current_user_id: int = Depends(get_current_user_id)):
    return query_delete_todo(current_user_id, todo_id)
