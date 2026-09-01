from psycopg.rows import dict_row

from app.database.db import get_connection


def create_pending_connection(user_id: int, data: dict):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "DELETE FROM bank_connections WHERE user_id = %s AND status = 'PENDING'",
                (user_id,),
            )
            return cur.execute(
                """
                INSERT INTO bank_connections (
                    user_id, institution_name, institution_country, psu_type,
                    authorization_id, state_hash, status, consent_valid_until
                ) VALUES (%s, %s, %s, %s, %s, %s, 'PENDING', %s)
                RETURNING *
                """,
                (
                    user_id, data["institution_name"], data["institution_country"],
                    data["psu_type"], data["authorization_id"], data["state_hash"],
                    data["consent_valid_until"],
                ),
            ).fetchone()


def get_pending_connection(user_id: int, state_hash: str):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return cur.execute(
                """SELECT * FROM bank_connections
                   WHERE user_id = %s AND state_hash = %s AND status = 'PENDING'""",
                (user_id, state_hash),
            ).fetchone()


def authorize_connection(user_id: int, connection_id: int, session_id: str, accounts: list[dict]):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            connection = cur.execute(
                """
                UPDATE bank_connections
                SET provider_session_id = %s, status = 'AUTHORIZED', last_error = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND user_id = %s AND status = 'PENDING'
                RETURNING *
                """,
                (session_id, connection_id, user_id),
            ).fetchone()
            for account in accounts:
                cur.execute(
                    """
                    INSERT INTO bank_accounts (
                        user_id, connection_id, provider_account_id, identification_hash,
                        account_name, bank_name, iban_last4, currency
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, provider_account_id) DO UPDATE SET
                        connection_id = EXCLUDED.connection_id,
                        identification_hash = EXCLUDED.identification_hash,
                        account_name = EXCLUDED.account_name,
                        bank_name = EXCLUDED.bank_name,
                        iban_last4 = EXCLUDED.iban_last4,
                        currency = EXCLUDED.currency,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        user_id, connection_id, account["provider_account_id"],
                        account["identification_hash"], account["account_name"],
                        account["bank_name"], account["iban_last4"], account["currency"],
                    ),
                )
            return connection


def list_connections(user_id: int):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            connections = cur.execute(
                """SELECT id, provider, institution_name, institution_country, psu_type,
                          status, consent_valid_until, last_synced_at, last_error,
                          created_at, updated_at
                   FROM bank_connections
                   WHERE user_id = %s AND status <> 'PENDING'
                   ORDER BY created_at DESC""",
                (user_id,),
            ).fetchall()
            accounts = cur.execute(
                """SELECT id, connection_id, account_name, bank_name, iban_last4,
                          currency, current_balance, balance_updated_at
                   FROM bank_accounts WHERE user_id = %s ORDER BY created_at""",
                (user_id,),
            ).fetchall()
    by_connection: dict[int, list[dict]] = {}
    for account in accounts:
        by_connection.setdefault(account["connection_id"], []).append(account)
    for connection in connections:
        connection["accounts"] = by_connection.get(connection["id"], [])
    return connections


def get_connection_for_user(user_id: int, connection_id: int):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return cur.execute(
                "SELECT * FROM bank_connections WHERE id = %s AND user_id = %s",
                (connection_id, user_id),
            ).fetchone()


def get_accounts_for_connection(user_id: int, connection_id: int):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return cur.execute(
                """SELECT * FROM bank_accounts
                   WHERE user_id = %s AND connection_id = %s ORDER BY id""",
                (user_id, connection_id),
            ).fetchall()


def save_account_sync(user_id: int, account_id: int, balance: dict | None, transactions: list[dict]):
    inserted = 0
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            if balance:
                cur.execute(
                    """
                    UPDATE bank_accounts
                    SET current_balance = %s, currency = %s,
                        balance_updated_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND user_id = %s
                    """,
                    (balance["amount"], balance["currency"], account_id, user_id),
                )
            for transaction in transactions:
                result = cur.execute(
                    """
                    INSERT INTO bank_transactions (
                        user_id, bank_account_id, provider_fingerprint, entry_reference,
                        direction, booking_status, amount, currency, booking_date,
                        merchant_name, description, merchant_category_code, suggested_category_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, bank_account_id, provider_fingerprint) DO UPDATE SET
                        entry_reference = EXCLUDED.entry_reference,
                        booking_status = EXCLUDED.booking_status,
                        amount = EXCLUDED.amount,
                        currency = EXCLUDED.currency,
                        booking_date = EXCLUDED.booking_date,
                        merchant_name = EXCLUDED.merchant_name,
                        description = EXCLUDED.description,
                        merchant_category_code = EXCLUDED.merchant_category_code,
                        suggested_category_id = EXCLUDED.suggested_category_id,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE bank_transactions.import_status = 'PENDING'
                        AND bank_transactions.booking_status = 'PENDING'
                        AND EXCLUDED.booking_status = 'BOOKED'
                    RETURNING id
                    """,
                    (
                        user_id, account_id, transaction["provider_fingerprint"],
                        transaction["entry_reference"], transaction["direction"],
                        transaction["booking_status"], transaction["amount"],
                        transaction["currency"], transaction["booking_date"],
                        transaction["merchant_name"], transaction["description"],
                        transaction["merchant_category_code"], transaction["suggested_category_id"],
                    ),
                ).fetchone()
                inserted += int(result is not None)
    return inserted


def mark_connection_synced(user_id: int, connection_id: int, error: str | None = None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE bank_connections
                SET last_synced_at = CASE WHEN %s IS NULL THEN CURRENT_TIMESTAMP ELSE last_synced_at END,
                    last_error = %s,
                    status = CASE WHEN %s IS NULL THEN 'AUTHORIZED' ELSE 'ERROR' END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND user_id = %s
                """,
                (error, error, error, connection_id, user_id),
            )


def list_transactions(user_id: int, import_status: str = "PENDING"):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return cur.execute(
                """
                SELECT bt.id, bt.direction, bt.booking_status, bt.amount, bt.currency,
                       bt.booking_date, bt.merchant_name, bt.description,
                       bt.suggested_category_id, bt.import_status,
                       ba.account_name, ba.iban_last4, ba.bank_name
                FROM bank_transactions bt
                JOIN bank_accounts ba ON ba.id = bt.bank_account_id AND ba.user_id = bt.user_id
                WHERE bt.user_id = %s AND bt.import_status = %s
                ORDER BY bt.booking_date DESC, bt.id DESC
                """,
                (user_id, import_status),
            ).fetchall()


def import_transaction(user_id: int, transaction_id: int, category_id: int):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            transaction = cur.execute(
                """
                SELECT bt.*, ba.bank_name, ba.account_name
                FROM bank_transactions bt
                JOIN bank_accounts ba ON ba.id = bt.bank_account_id AND ba.user_id = bt.user_id
                WHERE bt.id = %s AND bt.user_id = %s AND bt.direction = 'DEBIT'
                    AND bt.booking_status = 'BOOKED' AND bt.import_status = 'PENDING'
                FOR UPDATE
                """,
                (transaction_id, user_id),
            ).fetchone()
            if transaction is None:
                return None
            title = (transaction["merchant_name"] or transaction["description"] or "Bank transaction")[:30]
            description_parts = [transaction["description"]]
            account_label = transaction["account_name"] or transaction["bank_name"]
            if account_label:
                description_parts.append(f"Imported from {account_label}")
            description = " · ".join(part for part in description_parts if part)[:1000] or None
            expense = cur.execute(
                """
                INSERT INTO expenses (title, amount, expense_date, category_id, user_id, description)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    title, transaction["amount"], transaction["booking_date"],
                    category_id, user_id, description,
                ),
            ).fetchone()
            cur.execute(
                """UPDATE bank_transactions
                   SET import_status = 'IMPORTED', expense_id = %s, updated_at = CURRENT_TIMESTAMP
                   WHERE id = %s""",
                (expense["id"], transaction_id),
            )
            return expense


def ignore_transaction(user_id: int, transaction_id: int):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return cur.execute(
                """
                UPDATE bank_transactions SET import_status = 'IGNORED', updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND user_id = %s AND import_status = 'PENDING'
                RETURNING id
                """,
                (transaction_id, user_id),
            ).fetchone()


def disconnect_connection(user_id: int, connection_id: int):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return cur.execute(
                """
                UPDATE bank_connections
                SET status = 'DISCONNECTED', updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND user_id = %s AND status <> 'DISCONNECTED'
                RETURNING *
                """,
                (connection_id, user_id),
            ).fetchone()
