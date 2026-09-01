# Life Stack Backend

The FastAPI and PostgreSQL service behind **Life Stack**, a private personal operating system for two owners. The API owns authentication, financial records and forecasts, read-only bank synchronisation, movie intelligence, business invoicing, profile data, and server-side integrations.

> Status: active personal project. The backend is designed to run as a private Railway service reached only through the frontend's same-origin `/api` reverse proxy.

## Contents

- [Capabilities](#capabilities)
- [Architecture](#architecture)
- [Technology](#technology)
- [Local development](#local-development)
- [Configuration](#configuration)
- [Database and migrations](#database-and-migrations)
- [API overview](#api-overview)
- [Authentication and sessions](#authentication-and-sessions)
- [External integrations](#external-integrations)
- [Production deployment](#production-deployment)
- [Security model](#security-model)
- [Testing](#testing)
- [Project structure](#project-structure)
- [Next feature: Socials](#next-feature-socials)

## Capabilities

| Domain | Backend responsibility |
| --- | --- |
| Authentication | Registration gating, login throttling, Argon2id passwords, JWT access cookies, rotating refresh sessions, device identity, logout, and revocation. |
| Profile and settings | Profile fields, avatar storage, preferred language, password changes, and active-session management. |
| Expenses | User-scoped CRUD, descriptions, categories, and dated spending data. |
| Recurring commitments | CRUD plus backend-owned daily, weekly, monthly, and yearly forecast calculations that respect start/end dates. |
| Banking | Enable Banking institution discovery, hosted consent, encrypted session storage, balances, transaction synchronisation, deduplication, categorisation suggestions, and reviewed expense import. |
| Tasks | Authenticated user-owned task CRUD. |
| Movies | OMDb search/catalogue, personal lists and ratings, OpenAI recommendations, and AI-assisted critique rewriting. |
| Business invoicing | Multiple businesses, clients, invoices, line items, payments, credit notes, versioned branding/signatures, and multilingual ReportLab PDFs. |
| Operations | Alembic migrations, production validation, security headers, liveness/readiness endpoints, and Railway deployment configuration. |

## Architecture

```text
Internet
   │
   ▼
Frontend/Caddy at lifeos.gazdagbalazs.com
   │  /api prefix removed
   ▼
FastAPI at backend.railway.internal:8000
   ├── PostgreSQL at postgres.railway.internal
   ├── OMDb API
   ├── OpenAI Responses API
   └── Enable Banking API
```

The browser does not resolve or contact the private backend hostname. It sends same-origin `/api/*` requests to Caddy, which forwards them within Railway. PostgreSQL has no permanent public endpoint.

Application code follows a small layered design:

```text
API router → service/domain logic → repository → PostgreSQL
                 │
                 └──────────────→ external provider client
```

Routers handle HTTP validation and authentication. Services own calculations, provider normalisation, encryption, and PDF generation. Repositories own parameterised SQL and user scoping.

## Technology

- Python 3.13 production runtime
- FastAPI and Uvicorn
- PostgreSQL with psycopg 3
- Alembic and SQLAlchemy Core for migration execution; application queries remain direct psycopg SQL
- Pydantic for request and response validation
- PyJWT with asymmetric-provider support
- pwdlib/Argon2id with transparent legacy bcrypt upgrades
- cryptography/Fernet for stored provider session secrets
- HTTPX for outbound APIs
- ReportLab for invoice PDFs
- unittest and FastAPI TestClient
- Docker and Railway configuration-as-code

## Local development

### Prerequisites

- Python 3.13 or newer
- PostgreSQL 17 recommended
- The [Life Stack frontend](https://github.com/GazdagB/life-stack-frontend)
- Optional API credentials for movies, AI, and banking

### Setup

```shell
git clone https://github.com/GazdagB/life-stack-backend.git
cd life-stack-backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

Create an empty PostgreSQL database, update `DATABASE_URL`, then apply the schema:

```shell
alembic upgrade head
```

Start the API:

```shell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The root endpoint returns a basic API message. Development API documentation is available at `http://127.0.0.1:8000/docs` when `ENABLE_API_DOCS=true`.

The baseline creates reference expense categories but no account. For a controlled new installation, temporarily set `REGISTRATION_ENABLED=true`, register the intended accounts, then return it to `false`. Do not leave public registration enabled.

## Configuration

Copy `.env.example` and keep the real `.env` outside Git.

### Application and session settings

| Variable | Development default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | Required | PostgreSQL connection URL. Railway should use a reference to the private PostgreSQL service. |
| `ENVIRONMENT` | `development` | Enables production validation and response security policy when set to `production`. |
| `JWT_SECRET_KEY` | Unsafe development fallback | JWT signing secret; production requires at least 32 strong random characters. |
| `JWT_ISSUER` | `life-stack-api` | Required JWT issuer claim. |
| `JWT_AUDIENCE` | `life-stack-web` | Required JWT audience claim. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Access-cookie lifetime. |
| `REFRESH_TOKEN_EXPIRES_DAYS` | `30` | Absolute refresh-session lifetime. |
| `REFRESH_TOKEN_IDLE_DAYS` | `7` | Maximum inactivity between refreshes. |
| `SESSION_COOKIE_SECURE` | `false` | Must be `true` behind production HTTPS. |
| `PUBLIC_API_PREFIX` | `/api` | Browser-visible prefix used when scoping the refresh cookie. |
| `REGISTRATION_ENABLED` | `false` | Controls whether the account creation endpoint is available. |
| `ALLOWED_ORIGINS` | Local Vite origins | Comma-separated credentialed CORS/origin allowlist. |
| `ALLOWED_HOSTS` | Local/test hosts | Comma-separated host allowlist. Railway needs the public hostname and `healthcheck.railway.app`. |
| `ENABLE_API_DOCS` | `true` outside production | Enables OpenAPI, Swagger UI, and ReDoc. |
| `ENABLE_DB_HEALTH_ROUTE` | `false` | Enables the development-only database test router; keep disabled in production. |
| `LOGIN_RATE_LIMIT_WINDOW_SECONDS` | `900` | Login throttle window. |
| `LOGIN_RATE_LIMIT_ACCOUNT_ATTEMPTS` | `5` | Attempts permitted per account/window. |
| `LOGIN_RATE_LIMIT_IP_ATTEMPTS` | `25` | Attempts permitted per client IP/window. |
| `PORT` | `8000` in the entrypoint | HTTP port injected by Railway. |
| `FORWARDED_ALLOW_IPS` | `127.0.0.1` | Proxies trusted by Uvicorn. `*` is acceptable only while the backend has no public endpoint and receives traffic solely from the private proxy. |

Generate a production JWT secret locally:

```shell
openssl rand -base64 48
```

### External services

| Variable | Purpose |
| --- | --- |
| `OMDB_API_KEY` | OMDb movie search and catalogue metadata. |
| `OPENAI_API_KEY` | Movie recommendations and critique rewriting through the Responses API. |
| `OPENAI_MOVIE_MODEL` | Model used for movie intelligence; defaults to `gpt-5.6-luna`. |
| `ENABLE_BANKING_APP_ID` | Enable Banking application/key identifier. |
| `ENABLE_BANKING_PRIVATE_KEY_PATH` | Absolute PEM path for local development. |
| `ENABLE_BANKING_PRIVATE_KEY` | Hosted alternative containing PEM text; use a Railway secret, never Git. |
| `ENABLE_BANKING_BASE_URL` | Provider API URL. |
| `ENABLE_BANKING_REDIRECT_URL` | Exact frontend callback URL registered with the provider. |
| `ENABLE_BANKING_CONSENT_DAYS` | Requested consent duration, capped at 90 days. |
| `BANK_DATA_ENCRYPTION_KEY` | Fernet key used to encrypt provider session IDs at rest. |

Generate the bank-data key once and include it in the protected secret backup process:

```shell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Changing this key without re-encrypting stored values makes existing bank sessions unreadable.

## Database and migrations

Alembic owns the production schema. The current baseline revision is `20260901_01`.

### New empty database

```shell
alembic upgrade head
```

The baseline applies `app/database/schema.sql`. That file is deliberately non-destructive and contains the canonical schema plus reference expense categories. It does not create users, expenses, tasks, or mock business data.

### Existing Life Stack database

An existing database that already includes legacy SQL migrations through `018_add_bank_sync.sql` must be backed up and inspected before Alembic adopts it. Record the current baseline without executing schema creation:

```shell
alembic stamp 20260901_01
```

Do **not** run `alembic upgrade head` against an existing unstamped Life Stack database: the baseline expects an empty database.

The legacy `app.database.initialize` module is only for a disposable, empty development database and requires `ALLOW_DEVELOPMENT_DATABASE_INIT=true`. It refuses to run when `ENVIRONMENT=production`.

### Future changes

Create forward-only revisions and review the generated SQL:

```shell
alembic revision -m "describe the change"
alembic upgrade head --sql
alembic upgrade head
```

The baseline downgrade is intentionally disabled because dropping the entire application schema would destroy all user data.

Before production migration:

1. Create an encrypted `pg_dump --format=custom --no-owner` backup.
2. Verify the PostgreSQL major versions.
3. Restore into an empty test database.
4. Compare critical row counts and authenticate both users.
5. Perform a restore drill before relying on automated backups.

## API overview

The backend exposes routes without `/api`; Caddy adds the browser-visible `/api` boundary.

| Prefix | Major operations |
| --- | --- |
| `/auth` | Register, login, refresh, current user, profile, avatar, preferences, sessions, password change, and logout. |
| `/expenses` | User-scoped expense CRUD. |
| `/recurring-expenses` | Recurring commitment CRUD and `/coverage` forecast. |
| `/todos` | User-scoped task CRUD. |
| `/movies` | Search, catalogue lookup, saved-movie CRUD, recommendations, and critique rewriting. |
| `/businesses` | Business CRUD plus versioned logos and signatures. |
| `/clients` | Client CRUD scoped to user and business. |
| `/invoices` | Invoice CRUD, issue, payments, credit notes, and PDF. |
| `/banking` | Institution discovery, connection start/callback, accounts, synchronisation, transaction review/import, and disconnect. |
| `/healthz` | Liveness check that does not query PostgreSQL. |
| `/readyz` | Readiness check that runs `SELECT 1` and returns no connection details. |

Swagger is the source of exact development request/response schemas when API docs are enabled.

## Authentication and sessions

- New passwords use Argon2id. A successful login transparently upgrades a legacy bcrypt hash.
- Access JWTs include issuer, audience, subject, issued-at, expiry, and refresh-session family identifiers.
- Access and refresh values are sent only through `HttpOnly`, `SameSite=Strict` cookies.
- The access cookie lasts 60 minutes by default; refresh sessions have absolute and idle limits.
- Refresh tokens rotate and are stored only as hashes in PostgreSQL.
- Access tokens are checked against the active refresh-session family, so revocation takes effect before JWT expiry.
- A random browser-profile cookie deduplicates repeated logins from the same browser profile without fingerprinting the device.
- Password changes require the current password and revoke other sessions.
- Login and password reauthentication use persistent HMAC-keyed account/IP throttling.
- Authentication routes return `Cache-Control: no-store`.

## External integrations

### OMDb

OMDb provides movie search and detail metadata. IMDb, Rotten Tomatoes, and Metacritic values appear only when OMDb includes them for that title. Saved movies live in Life Stack PostgreSQL, so lists do not require repeated provider queries.

### OpenAI

The Responses API supplies:

- Four movie recommendations based primarily on the ten most recently rated films, personal scores, and critiques.
- Critique rewriting that preserves the user's opinion and language.

Requests use structured output and `store: false`. Account identity is not sent. API usage requires separate API billing; a ChatGPT subscription does not supply API credits.

### Enable Banking

Enable Banking hosts bank authentication. Life Stack never receives a bank password, PIN, or TAN. Stored data is limited to the fields needed for read-only balances, transaction review, deduplication, and expense import. Provider session IDs are encrypted with Fernet.

Only booked debits can become expenses. Credits and pending authorisations remain in the review model. Disconnecting revokes provider consent but does not delete expenses already imported.

Production needs a production Enable Banking application and a new production private key. Local filesystem key paths do not work in Railway containers.

### Invoice PDFs

ReportLab creates German, Hungarian, or English PDF invoices with selected branding, template, and signature snapshots. PDF generation does not itself transmit statutory invoice data:

- Hungarian NAV Online Számla submission is still planned.
- German EN 16931/XRechnung or eligible hybrid e-invoice generation and delivery is still planned.

## Production deployment

The backend Docker image:

- Uses Python 3.13 slim.
- Installs pinned dependencies.
- Runs as an unprivileged `lifeos` user.
- Starts Uvicorn through an `exec` entrypoint for proper signal handling.
- Listens on Railway's `PORT`.
- Excludes environment files, keys, dumps, virtual environments, and tests from the build context.

`railway.json` runs `alembic upgrade head` as a pre-deploy command and checks `/healthz` before activating the deployment.

Recommended production values include:

```dotenv
ENVIRONMENT=production
PORT=8000
DATABASE_URL=${{Postgres.DATABASE_URL}}
JWT_SECRET_KEY=<strong-random-value>
SESSION_COOKIE_SECURE=true
PUBLIC_API_PREFIX=/api
ALLOWED_ORIGINS=https://lifeos.gazdagbalazs.com
ALLOWED_HOSTS=lifeos.gazdagbalazs.com,healthcheck.railway.app
REGISTRATION_ENABLED=false
ENABLE_API_DOCS=false
ENABLE_DB_HEALTH_ROUTE=false
FORWARDED_ALLOW_IPS=*
ENABLE_BANKING_REDIRECT_URL=https://lifeos.gazdagbalazs.com/expenses/bank-accounts/callback
```

Only use `FORWARDED_ALLOW_IPS=*` while Railway exposes no backend public domain and only the trusted frontend service can reach it through the private network.

## Security model

- Production startup rejects weak JWT secrets, insecure cookies, HTTP origins, wildcard host allowlists, and insecure banking callbacks.
- `TrustedHostMiddleware` and an explicit credentialed CORS allowlist restrict request destinations and origins.
- Unsafe cross-site writes are rejected using Origin and Fetch Metadata checks.
- Responses include MIME, frame, referrer, permissions, HSTS, and restrictive API CSP headers.
- SQL uses bound parameters and every private query is scoped to the authenticated user.
- Registration and API documentation are disabled in normal production operation.
- Bank provider secrets are encrypted at rest; private keys remain deployment secrets.
- Logs must never contain cookies, tokens, full bank identifiers, private keys, or provider responses containing personal data.
- PostgreSQL stays private, backups are encrypted, and restore procedures must be tested.
- Secrets must be rotated deliberately; encryption-key rotation requires data migration.

The production checklist and remaining security work are tracked in [TODO.md](./TODO.md).

## Testing

Run the complete backend suite:

```shell
python -m unittest discover -s tests -p 'test_*.py'
```

Validate migration discovery and SQL generation:

```shell
alembic heads
alembic upgrade head --sql
```

Before committing:

```shell
python -m compileall -q app alembic
git diff --check
```

External-provider tests should mock network calls by default. A real provider sandbox test must use dedicated sandbox credentials and must not run automatically against production accounts.

## Project structure

```text
app/
├── api/               FastAPI routers and HTTP schemas
├── database/          psycopg connection, canonical schema, and legacy migrations
├── docs/              internal design notes
├── repositories/      parameterised, user-scoped PostgreSQL access
├── schemas/           shared application schemas
├── services/          authentication, forecasts, providers, PDFs, and validation
├── config.py          environment parsing and production validation
└── main.py            middleware, router registration, and application instance

alembic/               migration environment and forward revisions
tests/                 unit and route tests
Dockerfile             non-root production image
docker-entrypoint.sh   Uvicorn runtime entrypoint
railway.json           migrations, health check, and restart policy
```

When adding a feature, prefer one router, one service layer when domain/provider logic exists, one repository for persistence, a forward Alembic revision, and focused tests.

## Next feature: Socials

The next product implementation is a **Socials** domain that records follower/subscriber history across multiple platforms.

The backend design should begin with platform-independent accounts and daily metric snapshots. Provider-specific code belongs behind adapters so API rules, token refresh, scopes, and metric naming do not leak into common business logic.

Initial principles:

- Official OAuth and provider APIs only; no authenticated page scraping.
- Never collect or store social-account passwords.
- Encrypt refresh/access tokens at rest with a dedicated key separate from bank-session encryption.
- Request read-only, minimum scopes.
- Support manual snapshots and CSV imports when official metrics are unavailable or paid.
- Store raw provider payloads only when strictly required; prefer normalised counts and timestamps.
- Calculate period changes on the backend using the nearest valid snapshots.
- Keep one platform failure isolated from every other account.
- Preserve history when disconnecting unless the user explicitly deletes it.

The full schema, API, sync, security, and acceptance plan is in [TODO.md](./TODO.md).

## Related repository

- Frontend: [GazdagB/life-stack-frontend](https://github.com/GazdagB/life-stack-frontend)

This is a private personal application. No open-source licence has been granted unless a licence file is added explicitly.
