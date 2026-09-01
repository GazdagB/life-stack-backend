import hashlib
import json
import secrets
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import httpx
import jwt
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException

from app.config import settings


SUPPORTED_COUNTRIES = {"DE", "HU"}
BOOKED_STATUSES = {"BOOK", "BOOKED"}

CATEGORY_KEYWORDS = {
    2: ("e.on", "vattenfall", "mvm", "telekom", "vodafone", "internet", "energy"),
    3: ("aldi", "lidl", "rewe", "penny", "kaufland", "tesco", "spar", "auchan"),
    4: ("mcdonald", "restaurant", "cafe", "coffee", "wolt", "foodora", "burger king"),
    5: ("shell", "omv", "aral", "uber", "bolt", "bkv", "mav", "parking"),
    6: ("apotheke", "pharmacy", "gyógyszertár", "doctor", "clinic"),
    7: ("netflix", "spotify", "openai", "chatgpt", "youtube", "disney", "icloud"),
    8: ("cinema", "kino", "mozi", "steam", "playstation", "xbox"),
    9: ("amazon", "ikea", "dm ", "rossmann", "mediamarkt", "temu", "zalando"),
    12: ("allianz", "versicherung", "insurance", "biztosító", "generali"),
    13: ("finanzamt", "nav ", "tax", "steuer", "adó"),
}


def _bank_cipher(key: str | None = None) -> Fernet:
    encryption_key = key or settings.BANK_DATA_ENCRYPTION_KEY
    if not encryption_key:
        raise HTTPException(status_code=503, detail="Bank data encryption is not configured.")
    try:
        return Fernet(encryption_key.encode())
    except (TypeError, ValueError) as error:
        raise HTTPException(status_code=503, detail="The bank data encryption key is invalid.") from error


def encrypt_provider_secret(value: str, key: str | None = None) -> str:
    return _bank_cipher(key).encrypt(value.encode()).decode()


def decrypt_provider_secret(value: str, key: str | None = None) -> str:
    try:
        return _bank_cipher(key).decrypt(value.encode()).decode()
    except InvalidToken as error:
        raise HTTPException(status_code=503, detail="Stored bank authorization could not be decrypted.") from error


def suggest_category(text: str) -> int:
    normalized = f" {text.lower()} "
    for category_id, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            return category_id
    return 10


def transaction_fingerprint(account_id: str, transaction: dict[str, Any]) -> str:
    stable_reference = (
        transaction.get("transaction_id")
        or transaction.get("entry_reference")
        or transaction.get("reference_number")
    )
    if stable_reference:
        source = [account_id, str(stable_reference)]
    else:
        source = [
            account_id,
            transaction.get("credit_debit_indicator"),
            transaction.get("booking_date") or transaction.get("transaction_date"),
            transaction.get("transaction_amount"),
            transaction.get("remittance_information"),
            transaction.get("balance_after_transaction"),
        ]
    return hashlib.sha256(json.dumps(source, sort_keys=True, default=str).encode()).hexdigest()


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return " ".join(filter(None, (_text(item) for item in value))).strip()
    if isinstance(value, dict):
        return " ".join(filter(None, (_text(item) for item in value.values()))).strip()
    return str(value).strip()


def normalize_transaction(account_id: str, transaction: dict[str, Any]) -> dict | None:
    amount_data = transaction.get("transaction_amount") or {}
    try:
        amount = abs(Decimal(str(amount_data.get("amount"))))
    except (InvalidOperation, TypeError):
        return None
    date_value = transaction.get("booking_date") or transaction.get("transaction_date")
    if not date_value:
        return None
    booking_date = str(date_value)[:10]
    indicator = str(transaction.get("credit_debit_indicator") or "").upper()
    direction = "DEBIT" if indicator in {"DBIT", "DEBIT"} else "CREDIT"
    status_value = str(transaction.get("status") or "BOOK").upper()
    status = "BOOKED" if status_value in BOOKED_STATUSES else "PENDING"
    party = transaction.get("creditor") if direction == "DEBIT" else transaction.get("debtor")
    merchant = _text((party or {}).get("name"))[:300] or None
    remittance = _text(transaction.get("remittance_information"))
    code_description = _text((transaction.get("bank_transaction_code") or {}).get("description"))
    description = (remittance or code_description)[:1000] or None
    searchable = " ".join(filter(None, [merchant, description]))
    return {
        "provider_fingerprint": transaction_fingerprint(account_id, transaction),
        "entry_reference": _text(transaction.get("entry_reference"))[:300] or None,
        "direction": direction,
        "booking_status": status,
        "amount": amount,
        "currency": str(amount_data.get("currency") or "EUR")[:3].upper(),
        "booking_date": booking_date,
        "merchant_name": merchant,
        "description": description,
        "merchant_category_code": _text(transaction.get("merchant_category_code"))[:10] or None,
        "suggested_category_id": suggest_category(searchable),
    }


def normalize_account(account: dict[str, Any]) -> dict:
    account_id = account.get("account_id") or {}
    iban = _text(account_id.get("iban"))
    servicer = account.get("account_servicer") or {}
    return {
        "provider_account_id": account["uid"],
        "identification_hash": account["identification_hash"],
        "account_name": (_text(account.get("name")) or _text(account.get("details")))[:200] or None,
        "bank_name": _text(servicer.get("name"))[:200] or None,
        "iban_last4": iban[-4:] if iban else None,
        "currency": str(account.get("currency") or "EUR")[:3].upper(),
    }


class EnableBankingClient:
    def __init__(self, app_id: str | None = None, private_key: str | None = None, base_url: str | None = None):
        self.app_id = app_id or settings.ENABLE_BANKING_APP_ID
        self.private_key = private_key
        self.base_url = (base_url or settings.ENABLE_BANKING_BASE_URL).rstrip("/")

    def _private_key(self) -> str:
        if self.private_key:
            return self.private_key
        if settings.ENABLE_BANKING_PRIVATE_KEY:
            return settings.ENABLE_BANKING_PRIVATE_KEY.replace("\\n", "\n")
        if settings.ENABLE_BANKING_PRIVATE_KEY_PATH:
            try:
                return Path(settings.ENABLE_BANKING_PRIVATE_KEY_PATH).read_text()
            except OSError as error:
                raise HTTPException(status_code=503, detail="The bank integration private key could not be read.") from error
        raise HTTPException(status_code=503, detail="Bank synchronization is not configured.")

    def _token(self) -> str:
        if not self.app_id:
            raise HTTPException(status_code=503, detail="Bank synchronization is not configured.")
        now = datetime.now(UTC)
        return jwt.encode(
            {"iss": "enablebanking.com", "aud": "api.enablebanking.com", "iat": now, "exp": now + timedelta(minutes=5)},
            self._private_key(),
            algorithm="RS256",
            headers={"typ": "JWT", "kid": self.app_id},
        )

    def _ensure_configured(self) -> None:
        if settings.banking_configuration_error():
            raise HTTPException(
                status_code=503,
                detail="Bank synchronization is temporarily unavailable.",
            )
        # Validate the Fernet key before starting any provider workflow. This
        # prevents creating a consent that cannot later be stored securely.
        try:
            _bank_cipher()
        except HTTPException as error:
            raise HTTPException(
                status_code=503,
                detail="Bank synchronization is temporarily unavailable.",
            ) from error

    def _request(self, method: str, path: str, **kwargs) -> dict:
        self._ensure_configured()
        try:
            response = httpx.request(
                method,
                f"{self.base_url}{path}",
                headers={"Authorization": f"Bearer {self._token()}", "Accept": "application/json"},
                timeout=30.0,
                **kwargs,
            )
        except httpx.HTTPError as error:
            raise HTTPException(status_code=502, detail="The bank data provider is temporarily unavailable.") from error
        if response.is_error:
            try:
                payload = response.json()
                provider_message = payload.get("detail") or payload.get("message") or payload.get("error")
            except (ValueError, AttributeError):
                provider_message = None
            status = 429 if response.status_code == 429 else 502
            if response.status_code in {401, 403}:
                status = 503
            raise HTTPException(status_code=status, detail=provider_message or "The bank data provider rejected the request.")
        if response.status_code == 204 or not response.content:
            return {}
        return response.json()

    def institutions(self, country: str, psu_type: str = "personal") -> list[dict]:
        country = country.upper()
        if country not in SUPPORTED_COUNTRIES:
            raise HTTPException(status_code=422, detail="Only German and Hungarian institutions are supported.")
        payload = self._request("GET", "/aspsps", params={"country": country, "psu_type": psu_type})
        institutions = payload.get("aspsps", payload if isinstance(payload, list) else [])
        return [
            {"name": item["name"], "country": country, "logo": item.get("logo"), "bic": item.get("bic")}
            for item in institutions if item.get("name")
        ]

    def start_authorization(self, institution_name: str, country: str, state: str, psu_type: str) -> dict:
        valid_until = datetime.now(UTC) + timedelta(days=settings.ENABLE_BANKING_CONSENT_DAYS)
        payload = self._request(
            "POST", "/auth",
            json={
                "access": {"balances": True, "transactions": True, "valid_until": valid_until.isoformat()},
                "aspsp": {"name": institution_name, "country": country},
                "state": state,
                "redirect_url": settings.ENABLE_BANKING_REDIRECT_URL,
                "psu_type": psu_type,
            },
        )
        payload["valid_until"] = valid_until
        return payload

    def authorize_session(self, code: str) -> dict:
        return self._request("POST", "/sessions", json={"code": code})

    def balances(self, account_id: str) -> dict:
        return self._request("GET", f"/accounts/{account_id}/balances")

    def transactions(self, account_id: str, date_from: date) -> list[dict]:
        transactions: list[dict] = []
        continuation_key = None
        base_params = {"date_from": date_from.isoformat()}
        for _ in range(20):
            params = dict(base_params)
            if continuation_key:
                params["continuation_key"] = continuation_key
            page = self._request("GET", f"/accounts/{account_id}/transactions", params=params)
            transactions.extend(page.get("transactions", []))
            continuation_key = page.get("continuation_key")
            if not continuation_key:
                break
        return transactions

    def delete_session(self, session_id: str) -> None:
        self._request("DELETE", f"/sessions/{session_id}")


def new_authorization_state() -> tuple[str, str]:
    state = secrets.token_urlsafe(32)
    return state, hashlib.sha256(state.encode()).hexdigest()


def state_hash(state: str) -> str:
    return hashlib.sha256(state.encode()).hexdigest()


def select_balance(payload: dict) -> dict | None:
    balances = payload.get("balances", [])
    if not balances:
        return None
    priorities = {"CLAV": 0, "ITAV": 1, "CLBD": 2, "ITBD": 3}
    selected = min(balances, key=lambda item: priorities.get(item.get("balance_type"), 99))
    amount = selected.get("balance_amount") or {}
    if amount.get("amount") is None:
        return None
    return {"amount": Decimal(str(amount["amount"])), "currency": amount.get("currency", "EUR")}


def transaction_sync_start(
    last_synced_at: datetime | None,
    *,
    now: datetime | None = None,
    initial_days: int | None = None,
    overlap_days: int | None = None,
) -> date:
    reference = now or datetime.now(UTC)
    if last_synced_at is None:
        return (reference - timedelta(days=initial_days or settings.BANK_INITIAL_SYNC_DAYS)).date()
    overlap = settings.BANK_SYNC_OVERLAP_DAYS if overlap_days is None else overlap_days
    return (last_synced_at - timedelta(days=overlap)).date()


enable_banking_client = EnableBankingClient()
