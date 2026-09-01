# LifeOS

A personal operating system for tracking and analyzing all aspects of my life.

## Database migrations

Alembic owns the production schema. For a brand-new empty database, run:

```shell
alembic upgrade head
```

The baseline migration applies `app/database/schema.sql`, which is deliberately
non-destructive and contains only the canonical schema and reference expense
categories. It never creates a user or mock expenses.

An existing LifeOS database that already contains every change through legacy
migration `018_add_bank_sync.sql` must be backed up and inspected before it is
adopted by Alembic. After confirming that schema is current, record the baseline
without executing it:

```shell
alembic stamp 20260901_01
```

Do not run `alembic upgrade head` against an existing, unstamped database: the
baseline is for an empty database. `app.database.initialize` remains available
only for disposable local development databases and now requires the explicit
`ALLOW_DEVELOPMENT_DATABASE_INIT=true` opt-in. It is always disabled when
`ENVIRONMENT=production`.

New database changes must be added as forward Alembic revisions. The baseline
downgrade is intentionally disabled because dropping the entire application
schema would destroy user data.

## Production containers

The backend Docker image runs FastAPI as an unprivileged Linux user. Railway
runs `alembic upgrade head` as its pre-deploy command, checks `/healthz`, and
then starts Uvicorn on `PORT`. `/readyz` performs a private PostgreSQL readiness
check without returning connection details.

The backend should not receive a Railway public domain. Caddy in the frontend
service proxies public `/api/*` requests to `backend.railway.internal:8000`.
Set `PORT=8000` and `FORWARDED_ALLOW_IPS=*` on the private Railway backend; do
not use the wildcard if the backend is ever exposed directly to the internet.
Keep `PUBLIC_API_PREFIX=/api`; this scopes the refresh-token cookie to the
browser-visible proxy path even though Caddy removes `/api` before forwarding.

## Planned Features

- Expense tracking
- Income tracking
- Goal management
- Habit tracking
- Workout tracking
- Notes and journaling
- Life analytics

## Tech Stack

- React
- FastAPI
- PostgreSQL

## Movie search

Movie search uses the OMDb API from the backend. Add `OMDB_API_KEY` to `.env` after
requesting a key at https://www.omdbapi.com/apikey.aspx. External ratings are shown
when OMDb provides them; IMDb, Rotten Tomatoes, and Metacritic coverage varies by title.

AI movie recommendations use the OpenAI Responses API. Add `OPENAI_API_KEY` to
`.env`; `OPENAI_MOVIE_MODEL` is optional and defaults to `gpt-5.6-luna`. Only the
10 most recently rated movie titles, basic metadata, personal scores, critiques,
and up to 250 saved-title exclusions are sent. Account identity is never included,
and API responses are requested with storage disabled.

## Read-only bank synchronization

Migration `018_add_bank_sync.sql` adds Enable Banking connections, accounts, and
a reviewable transaction inbox. The backend uses Enable Banking's hosted bank
authorization, so LifeOS never receives a bank password, PIN, or TAN. It stores
only the account label, currency, balance, last four IBAN characters, and the
minimal transaction fields needed for expense tracking. Provider session IDs are
encrypted with Fernet before they are stored in PostgreSQL.

Add these values to `.env` before connecting an account:

```dotenv
ENABLE_BANKING_APP_ID=<application-id-from-enable-banking>
ENABLE_BANKING_PRIVATE_KEY_PATH=/absolute/path/to/enable-banking-private.pem
BANK_DATA_ENCRYPTION_KEY=<one-time-fernet-key>
ENABLE_BANKING_REDIRECT_URL=http://localhost:5173/expenses/bank-accounts/callback
```

Generate the encryption key once, keep it in the deployment secret store, and
include it in encrypted backups:

```shell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Synchronization upserts pending transactions when the bank later books them and
deduplicates them per account. Only a booked debit can be imported as an expense;
credits and pending card authorizations remain outside the expense ledger.
Disconnecting revokes the provider session and stops future synchronization but
keeps expenses that were already imported.

## Business invoicing

Migration `011_add_business_invoicing.sql` adds separate legal businesses,
segmented clients, immutable issued invoices, line items, payments, credit notes,
and jurisdiction submission state. Businesses are created explicitly by each
user; no default legal entities are recreated automatically.

Migration `012_add_invoice_branding.sql` adds per-business website, accent
color, footer text, and versioned logo assets. Issued invoice snapshots retain
the selected logo asset ID, so later branding changes do not alter historical
PDFs.

Migration `013_add_invoice_template_signature.sql` adds a selectable modern or
classic letterhead template, a customizable thank-you line, and versioned
signature images. Issued invoice snapshots retain the selected template and
signature asset ID, so later edits do not change historical PDFs.

Invoice PDFs are generated by the backend with ReportLab in German, Hungarian,
or English. Install the updated requirements before starting the API. A PDF is
the human-readable invoice view, not proof of tax-authority transmission:

- Hungarian invoices remain `PENDING` until a NAV Online Számla 3.0 adapter is
  configured with the business's technical-user credentials and acceptance is
  confirmed by NAV.
- German domestic B2B invoices remain `PENDING` until a validated EN 16931
  structured invoice (for example XRechnung or an eligible hybrid format) is
  generated and delivered through the chosen channel.

## Internet-facing security

Migration `014_add_auth_rate_limits.sql` adds persistent login throttling. The
API permits five attempts per account and 25 per client IP in a 15-minute
window by default, then returns `429` with a `Retry-After` header. Limiter keys
are HMAC-hashed, so raw usernames and IP addresses are not stored.

Migration `015_require_todo_ownership.sql` closes the legacy task authorization
gap by requiring every todo to have an owner. Every task read and mutation is
now authenticated and scoped to that user.

Migration `016_add_user_preferences.sql` adds the account-level language
preference used by the frontend. The API accepts only English (`en`), German
(`de`), or Hungarian (`hu`) and returns the preference from `/auth/me` so it
follows the user across devices.

New passwords use Argon2id. Existing bcrypt hashes remain valid and are
transparently replaced with Argon2id after the account's next successful login.
Access tokens require the configured issuer, audience, subject, issued-at, and
expiry claims.

Authenticated settings expose active refresh-session families rather than raw
tokens. Users can revoke one device or every other device, and access JWTs are
bound to those families so revocation takes effect immediately. Password changes
require the current password, enforce the same persistent account/IP throttle as
login, require at least 15 characters, and revoke all other device sessions.

Migration `017_add_session_device_identity.sql` adds a hashed, random browser-profile
identifier to refresh sessions. Its raw value lives only in a long-lived `HttpOnly`
cookie. A successful login from the same account and browser profile atomically
revokes that profile's previous session before creating the new one, preventing
duplicate Chrome entries without browser fingerprinting.

For production, serve the frontend and `/api` from the same HTTPS origin behind
a maintained reverse proxy or identity-aware access gateway. Configure at
least:

```dotenv
ENVIRONMENT=production
JWT_SECRET_KEY=<at-least-32-random-characters>
SESSION_COOKIE_SECURE=true
ALLOWED_ORIGINS=https://your-private-app.example
ALLOWED_HOSTS=your-private-app.example,healthcheck.railway.app
REGISTRATION_ENABLED=false
ENABLE_API_DOCS=false
ENABLE_DB_HEALTH_ROUTE=false
```

Create the two intended users before deployment (or enable registration only
briefly during controlled setup), then keep registration disabled. Production
startup fails when the JWT secret is weak, secure cookies are disabled, an
HTTP origin is configured, or wildcard hosts are allowed.

When the app is behind a trusted local reverse proxy, configure Uvicorn proxy
headers with only that proxy's IP in `forwarded-allow-ips`; never trust forwarded
client-IP headers from the open internet. This is required for accurate IP rate
limits. Keep PostgreSQL private, use a least-privilege database role, encrypt and
test backups, rotate secrets, and regularly audit Python and npm dependencies.
