from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.repositories.bank_repository import (
    authorize_connection, create_pending_connection, disconnect_connection,
    get_accounts_for_connection, get_connection_for_user, get_pending_connection,
    ignore_transaction, import_transaction, list_connections, list_transactions,
    mark_connection_synced, save_account_sync,
)
from app.services.auth_service import get_current_user_id
from app.services.bank_sync_service import (
    decrypt_provider_secret, enable_banking_client, encrypt_provider_secret,
    new_authorization_state, normalize_account,
    normalize_transaction, select_balance, state_hash,
)


router = APIRouter(prefix="/banking", tags=["banking"])


class StartConnectionRequest(BaseModel):
    institution_name: str = Field(min_length=1, max_length=200)
    country: Literal["DE", "HU"]
    psu_type: Literal["personal", "business"] = "personal"


class CompleteConnectionRequest(BaseModel):
    code: str = Field(min_length=1, max_length=2000)
    state: str = Field(min_length=20, max_length=200)


class ImportTransactionRequest(BaseModel):
    category_id: int = Field(ge=1)


@router.get("/institutions")
def get_institutions(
    country: str = Query(pattern="^(DE|HU|de|hu)$"),
    psu_type: Literal["personal", "business"] = "personal",
    _user_id: int = Depends(get_current_user_id),
):
    return enable_banking_client.institutions(country.upper(), psu_type)


@router.post("/connections/start")
def start_connection(request: StartConnectionRequest, user_id: int = Depends(get_current_user_id)):
    raw_state, hashed_state = new_authorization_state()
    authorization = enable_banking_client.start_authorization(
        request.institution_name.strip(), request.country, raw_state, request.psu_type,
    )
    connection = create_pending_connection(user_id, {
        "institution_name": request.institution_name.strip(), "institution_country": request.country,
        "psu_type": request.psu_type, "authorization_id": authorization.get("authorization_id"),
        "state_hash": hashed_state, "consent_valid_until": authorization["valid_until"],
    })
    return {"connection_id": connection["id"], "authorization_url": authorization["url"]}


@router.post("/connections/complete")
def complete_connection(request: CompleteConnectionRequest, user_id: int = Depends(get_current_user_id)):
    connection = get_pending_connection(user_id, state_hash(request.state))
    if connection is None:
        raise HTTPException(status_code=400, detail="This bank connection request is invalid or has expired.")
    session = enable_banking_client.authorize_session(request.code)
    accounts = [normalize_account(account) for account in session.get("accounts", []) if account.get("uid")]
    if not accounts:
        raise HTTPException(status_code=502, detail="The bank did not return any accessible accounts.")
    authorize_connection(user_id, connection["id"], encrypt_provider_secret(session["session_id"]), accounts)
    return {"connection_id": connection["id"], "accounts_added": len(accounts)}


@router.get("/connections")
def get_connections(user_id: int = Depends(get_current_user_id)):
    return list_connections(user_id)


@router.post("/connections/{connection_id}/sync")
def sync_connection(connection_id: int, user_id: int = Depends(get_current_user_id)):
    connection = get_connection_for_user(user_id, connection_id)
    if connection is None or connection["status"] == "DISCONNECTED":
        raise HTTPException(status_code=404, detail="Bank connection not found.")
    if not connection.get("provider_session_id"):
        raise HTTPException(status_code=409, detail="Bank authorization is not complete.")
    imported = 0
    try:
        for account in get_accounts_for_connection(user_id, connection_id):
            balance = select_balance(enable_banking_client.balances(str(account["provider_account_id"])))
            normalized = [item for item in (
                normalize_transaction(str(account["provider_account_id"]), transaction)
                for transaction in enable_banking_client.transactions(str(account["provider_account_id"]))
            ) if item is not None]
            imported += save_account_sync(user_id, account["id"], balance, normalized)
        mark_connection_synced(user_id, connection_id)
    except HTTPException as error:
        mark_connection_synced(user_id, connection_id, str(error.detail)[:500])
        raise
    return {"new_transactions": imported}


@router.get("/transactions")
def get_transactions(
    status: Literal["PENDING", "IMPORTED", "IGNORED"] = "PENDING",
    user_id: int = Depends(get_current_user_id),
):
    return list_transactions(user_id, status)


@router.post("/transactions/{transaction_id}/import")
def import_bank_transaction(transaction_id: int, request: ImportTransactionRequest, user_id: int = Depends(get_current_user_id)):
    expense = import_transaction(user_id, transaction_id, request.category_id)
    if expense is None:
        raise HTTPException(status_code=409, detail="This transaction cannot be imported.")
    return expense


@router.post("/transactions/{transaction_id}/ignore")
def ignore_bank_transaction(transaction_id: int, user_id: int = Depends(get_current_user_id)):
    result = ignore_transaction(user_id, transaction_id)
    if result is None:
        raise HTTPException(status_code=409, detail="This transaction cannot be ignored.")
    return {"id": transaction_id, "status": "IGNORED"}


@router.delete("/connections/{connection_id}")
def disconnect_bank(connection_id: int, user_id: int = Depends(get_current_user_id)):
    connection = get_connection_for_user(user_id, connection_id)
    if connection is None:
        raise HTTPException(status_code=404, detail="Bank connection not found.")
    if connection.get("provider_session_id") and connection["status"] != "DISCONNECTED":
        enable_banking_client.delete_session(decrypt_provider_secret(connection["provider_session_id"]))
    disconnected = disconnect_connection(user_id, connection_id)
    if disconnected is None:
        return {"id": connection_id, "status": "DISCONNECTED"}
    return {"id": disconnected["id"], "status": disconnected["status"]}
