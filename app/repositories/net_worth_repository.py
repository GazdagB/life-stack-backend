from datetime import date

from fastapi import HTTPException
from psycopg.rows import dict_row

from app.database.db import get_connection


ITEM_SELECT = """
    SELECT nwi.*, ba.account_name, ba.bank_name, ba.iban_last4,
           ba.balance_updated_at,
           CASE WHEN nwi.linked_bank_account_id IS NULL
                THEN nwi.current_value
                ELSE ABS(COALESCE(ba.current_balance, nwi.current_value))
           END AS effective_value
    FROM net_worth_items nwi
    LEFT JOIN bank_accounts ba
      ON ba.id = nwi.linked_bank_account_id AND ba.user_id = nwi.user_id
"""


def list_net_worth_items(user_id: int):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return cur.execute(
                ITEM_SELECT + " WHERE nwi.user_id = %s ORDER BY nwi.active DESC, nwi.kind, nwi.name",
                (user_id,),
            ).fetchall()


def _validate_linked_bank_account(
    cur,
    user_id: int,
    bank_account_id: int | None,
    currency: str,
    item_id: int | None = None,
) -> None:
    if bank_account_id is None:
        return
    account = cur.execute(
        "SELECT currency FROM bank_accounts WHERE id = %s AND user_id = %s",
        (bank_account_id, user_id),
    ).fetchone()
    if account is None:
        raise HTTPException(status_code=404, detail="Linked bank account not found")
    if account["currency"] != currency:
        raise HTTPException(status_code=422, detail="The item currency must match the linked bank account")
    if item_id is None:
        duplicate = cur.execute(
            "SELECT id FROM net_worth_items WHERE user_id = %s AND linked_bank_account_id = %s",
            (user_id, bank_account_id),
        ).fetchone()
    else:
        duplicate = cur.execute(
            """SELECT id FROM net_worth_items
               WHERE user_id = %s AND linked_bank_account_id = %s AND id <> %s""",
            (user_id, bank_account_id, item_id),
        ).fetchone()
    if duplicate is not None:
        raise HTTPException(status_code=409, detail="This bank account is already included in net worth")


def _snapshot_item(cur, user_id: int, item_id: int, recorded_on: date | None = None):
    snapshot_date = recorded_on or date.today()
    cur.execute(
        """
        INSERT INTO net_worth_snapshots (
            user_id, item_id, value, currency, kind, ownership_percent, recorded_on, source
        )
        SELECT nwi.user_id, nwi.id,
               CASE WHEN nwi.linked_bank_account_id IS NULL
                    THEN nwi.current_value
                    ELSE ABS(COALESCE(ba.current_balance, nwi.current_value)) END,
               nwi.currency, nwi.kind, nwi.ownership_percent, %s,
               CASE WHEN nwi.linked_bank_account_id IS NULL THEN 'MANUAL' ELSE 'BANK_SYNC' END
        FROM net_worth_items nwi
        LEFT JOIN bank_accounts ba ON ba.id = nwi.linked_bank_account_id AND ba.user_id = nwi.user_id
        WHERE nwi.id = %s AND nwi.user_id = %s
        ON CONFLICT (item_id, recorded_on) DO UPDATE SET
            value = EXCLUDED.value,
            currency = EXCLUDED.currency,
            kind = EXCLUDED.kind,
            ownership_percent = EXCLUDED.ownership_percent,
            source = EXCLUDED.source
        """,
        (snapshot_date, item_id, user_id),
    )


def create_net_worth_item(user_id: int, item):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            _validate_linked_bank_account(
                cur, user_id, item.linked_bank_account_id, item.currency,
            )
            created = cur.execute(
                """
                INSERT INTO net_worth_items (
                    user_id, name, kind, category, current_value, currency,
                    ownership_percent, linked_bank_account_id, notes, active
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (user_id, item.name, item.kind, item.category, item.current_value,
                 item.currency, item.ownership_percent, item.linked_bank_account_id,
                 item.notes, item.active),
            ).fetchone()
            _snapshot_item(cur, user_id, created["id"])
            return cur.execute(
                ITEM_SELECT + " WHERE nwi.id = %s AND nwi.user_id = %s",
                (created["id"], user_id),
            ).fetchone()


def update_net_worth_item(user_id: int, item_id: int, item):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            _validate_linked_bank_account(
                cur, user_id, item.linked_bank_account_id, item.currency, item_id,
            )
            updated = cur.execute(
                """
                UPDATE net_worth_items SET
                    name = %s, kind = %s, category = %s, current_value = %s,
                    currency = %s, ownership_percent = %s, linked_bank_account_id = %s,
                    notes = %s, active = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND user_id = %s RETURNING id
                """,
                (item.name, item.kind, item.category, item.current_value, item.currency,
                 item.ownership_percent, item.linked_bank_account_id, item.notes,
                 item.active, item_id, user_id),
            ).fetchone()
            if updated is None:
                raise HTTPException(status_code=404, detail="Net worth item not found")
            _snapshot_item(cur, user_id, item_id)
            return cur.execute(
                ITEM_SELECT + " WHERE nwi.id = %s AND nwi.user_id = %s",
                (item_id, user_id),
            ).fetchone()


def delete_net_worth_item(user_id: int, item_id: int):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            deleted = cur.execute(
                "DELETE FROM net_worth_items WHERE id = %s AND user_id = %s RETURNING id",
                (item_id, user_id),
            ).fetchone()
            if deleted is None:
                raise HTTPException(status_code=404, detail="Net worth item not found")
            return {"id": deleted["id"], "message": "Net worth item deleted"}


def snapshot_all_items(user_id: int, recorded_on: date):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            item_ids = cur.execute(
                "SELECT id FROM net_worth_items WHERE user_id = %s AND active = TRUE",
                (user_id,),
            ).fetchall()
            for item in item_ids:
                _snapshot_item(cur, user_id, item["id"], recorded_on)
            return {"recorded_on": recorded_on, "snapshots": len(item_ids)}


def get_net_worth_history(user_id: int, currency: str, date_from: date):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return cur.execute(
                """
                WITH dates AS (
                    SELECT DISTINCT recorded_on
                    FROM net_worth_snapshots
                    WHERE user_id = %s AND currency = %s AND recorded_on >= %s
                )
                SELECT dates.recorded_on,
                       COALESCE(SUM(CASE WHEN latest.kind = 'ASSET'
                           THEN latest.value * latest.ownership_percent / 100 ELSE 0 END), 0) AS assets,
                       COALESCE(SUM(CASE WHEN latest.kind = 'LIABILITY'
                           THEN latest.value * latest.ownership_percent / 100 ELSE 0 END), 0) AS liabilities
                FROM dates
                JOIN net_worth_items nwi ON nwi.user_id = %s
                JOIN LATERAL (
                    SELECT nws.value, nws.ownership_percent, nws.kind, nws.currency
                    FROM net_worth_snapshots nws
                    WHERE nws.item_id = nwi.id AND nws.recorded_on <= dates.recorded_on
                    ORDER BY nws.recorded_on DESC LIMIT 1
                ) latest ON TRUE
                WHERE latest.currency = %s
                GROUP BY dates.recorded_on
                ORDER BY dates.recorded_on
                """,
                (user_id, currency, date_from, user_id, currency),
            ).fetchall()
