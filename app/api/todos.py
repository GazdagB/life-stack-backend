from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from app.repositories.todo_ai_repository import (
    get_todos_for_assessment,
    list_todo_assessments,
    upsert_todo_assessments,
)
from app.repositories.todo_ai_work_repository import (
    append_work_message,
    apply_assistant_turn,
    delete_work_message,
    get_or_create_work_session,
    get_todo_work_context,
    get_work_session,
    list_work_messages,
    update_work_draft,
)
from app.repositories.todos_repository import query_all_todos, query_post_todo,query_update_todo, query_delete_todo
from app.services.auth_service import get_current_user_id
from app.services.todo_ai_service import add_staleness, assess_todos
from app.services.todo_ai_work_service import (
    effective_work_actions,
    todo_ai_work_client,
    validate_work_context,
)
from app.services.todo_ai_work_pdf_service import build_todo_work_pdf
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


class TodoWorkStartRequest(BaseModel):
    language: Literal["en", "de", "hu"] = "en"


class TodoWorkMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    language: Literal["en", "de", "hu"] = "en"


class TodoWorkDraftRequest(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    content: str = Field(min_length=1, max_length=20000)


def _work_bundle(user_id: int, context: dict, session: dict):
    return {
        "todo": {
            "id": context["id"], "title": context["title"],
            "description": context.get("description") or "",
            "due_date": context.get("due_date"), "status": context["status"],
        },
        "assessment": {
            "classification": context.get("classification"),
            "reason": context.get("reason"),
            "ai_steps": context.get("ai_steps") or [],
            "human_steps": context.get("assessed_human_steps") or [],
            "missing_information": context.get("missing_information") or [],
            "supported_actions": effective_work_actions(context),
        },
        "session": session,
        "messages": list_work_messages(user_id, session["id"]),
    }


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


@router.post("/{todo_id}/ai-session")
def start_todo_ai_work(
    todo_id: int,
    request: TodoWorkStartRequest,
    current_user_id: int = Depends(get_current_user_id),
):
    context = get_todo_work_context(current_user_id, todo_id)
    validate_work_context(context)
    session = get_or_create_work_session(
        current_user_id, todo_id, context["assessment_fingerprint"],
    )
    messages = list_work_messages(current_user_id, session["id"])
    if not messages:
        turn = todo_ai_work_client.reply(context, [], request.language)
        session = apply_assistant_turn(
            current_user_id, session["id"], turn, todo_ai_work_client.model,
        )
    return _work_bundle(current_user_id, context, session)


@router.get("/{todo_id}/ai-session")
def read_todo_ai_work(todo_id: int, current_user_id: int = Depends(get_current_user_id)):
    context = get_todo_work_context(current_user_id, todo_id)
    session = get_work_session(current_user_id, todo_id)
    return _work_bundle(current_user_id, context, session)


@router.post("/{todo_id}/ai-session/messages")
def continue_todo_ai_work(
    todo_id: int,
    request: TodoWorkMessageRequest,
    current_user_id: int = Depends(get_current_user_id),
):
    context = get_todo_work_context(current_user_id, todo_id)
    validate_work_context(context)
    session = get_work_session(current_user_id, todo_id)
    user_message = append_work_message(
        current_user_id, session["id"], "USER", request.content.strip(),
    )
    messages = list_work_messages(current_user_id, session["id"])
    try:
        turn = todo_ai_work_client.reply(context, messages, request.language)
    except HTTPException:
        delete_work_message(current_user_id, user_message["id"])
        raise
    session = apply_assistant_turn(
        current_user_id, session["id"], turn, todo_ai_work_client.model,
    )
    return _work_bundle(current_user_id, context, session)


@router.put("/{todo_id}/ai-session/draft")
def save_todo_ai_work_draft(
    todo_id: int,
    request: TodoWorkDraftRequest,
    current_user_id: int = Depends(get_current_user_id),
):
    context = get_todo_work_context(current_user_id, todo_id)
    session = get_work_session(current_user_id, todo_id)
    session = update_work_draft(
        current_user_id, session["id"], request.title.strip(), request.content.strip(),
    )
    return _work_bundle(current_user_id, context, session)


@router.get("/{todo_id}/ai-session/pdf")
def download_todo_ai_work_pdf(
    todo_id: int,
    current_user_id: int = Depends(get_current_user_id),
):
    context = get_todo_work_context(current_user_id, todo_id)
    session = get_work_session(current_user_id, todo_id)
    if "GENERATE_PDF" not in effective_work_actions(context):
        raise HTTPException(status_code=422, detail="PDF preparation is not available for this TODO")
    if not session.get("deliverable_content"):
        raise HTTPException(status_code=409, detail="Finish and review the draft before downloading a PDF")
    pdf = build_todo_work_pdf(
        session.get("deliverable_title") or context["title"],
        session["deliverable_content"],
        include_signature=context.get("classification") == "PARTIALLY_AI_ACTIONABLE",
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="todo-{todo_id}-draft.pdf"'},
    )

@router.put("/{todo_id}")
def update_one(todo: TodoCreate, todo_id: int, current_user_id: int = Depends(get_current_user_id)):
    return query_update_todo(current_user_id, todo_id, todo)

@router.delete("/{todo_id}")
def delete_one(todo_id: int, current_user_id: int = Depends(get_current_user_id)):
    return query_delete_todo(current_user_id, todo_id)
