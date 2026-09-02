# Life Stack Backend Roadmap

> **Next product feature:** AI Task Assistant — classify TODOs by AI capability and safely produce useful drafts, documents, and action plans.
>
> Socials remains planned after the AI Task Assistant foundation is stable.

## Status legend

- [ ] Planned
- [x] Implemented
- Items are ordered by dependency inside each section.

## Next: AI Task Assistant

### Product behaviour and safety model

- [x] Classify every user-owned TODO as `FULLY_AI_ACTIONABLE`, `PARTIALLY_AI_ACTIONABLE`, or `HUMAN_REQUIRED` using structured output.
- [x] Return a short explanation, confidence level, missing information, AI-capable steps, and human-required steps for every classification.
- [x] Treat classification as advice rather than permission to perform an action.
- [ ] Require explicit confirmation before generating an artifact, changing a TODO, accessing an external provider, or performing any consequential action.
- [x] Never automatically send email, submit forms, cancel contracts, make payments, sign documents, or impersonate the user.
- [x] Keep handwriting, wet signatures, identity verification, phone calls, physical delivery, and provider authentication clearly marked as human steps.
- [ ] Allow the user to correct classifications and store that feedback for deterministic rule improvement.
- [x] Show when a result is based on incomplete task details rather than inventing missing names, dates, addresses, membership numbers, or legal terms.

### Data model and API

- [x] Add user-scoped `todo_ai_assessments` with TODO ID, classification, confidence, reasoning summary, structured steps, missing fields, model version, and timestamps.
- [ ] Add user-scoped `todo_ai_artifacts` metadata for drafts and generated files without storing provider prompts or unnecessary personal data.
- [x] Add assessment content fingerprints so changed TODOs are automatically marked for reassessment.
- [x] Add `/todos/ai-assess` for an explicitly selected batch and `/todos/ai-assessments` for user-scoped retrieval.
- [ ] Add a single-TODO retrieval and refresh endpoint if the document action flow needs it.
- [ ] Add `/todos/{id}/ai-actions` to list only the actions currently supported by Life Stack.
- [ ] Add `/todos/{id}/ai-artifacts` for preview, regeneration, acceptance, download, and deletion.
- [ ] Keep all queries and generated artifacts strictly scoped to the authenticated user.
- [x] Add bounded batch sizes and provider request timeouts.
- [ ] Add per-user assessment rate limits and idempotency protection.

### Assessment engine

- [x] Combine deterministic safety rules with OpenAI structured output instead of relying on unconstrained free-form classification.
- [x] Use the OpenAI Responses API with strict JSON Schema and `store: false`.
- [x] Send only the minimum required TODO title, description, and due date.
- [ ] Detect common capabilities such as drafting, summarising, planning, translating, calculating, researching, document generation, and data entry preparation.
- [x] Detect human-only boundaries such as signatures, calls, physical errands, identity checks, account login, legal acceptance, and payment authorisation.
- [ ] Separate “AI can prepare this” from “Life Stack currently has an implemented tool for this.”
- [ ] Fall back to `HUMAN_REQUIRED` with low confidence when the model is unavailable or safe classification is not possible.
- [x] Never mark a high-impact task fully actionable solely because text generation is possible.

### Document generation

- [ ] Implement a reusable document-action interface beginning with formal letters.
- [ ] Generate editable letter drafts before PDFs; never make the PDF the only review surface.
- [ ] Reuse the existing ReportLab PDF stack with locale-aware typography and page-layout tests.
- [ ] Support sender, recipient, subject, reference/membership number, requested effective date, body, attachments note, place/date, and a blank signature area.
- [ ] Validate all required fields and present a completion checklist before generation.
- [ ] Preserve the accepted wording separately from generated PDF bytes so documents can be regenerated.
- [ ] Add PDF download audit metadata without logging document contents or personal identifiers.

### First end-to-end template: cancellation letter

- [x] Recognise cancellation tasks such as “Verdi subscription cancellation letter” as partially AI-actionable.
- [ ] Ask for the organisation address, membership/contract number, sender address, desired cancellation date, and delivery preference when missing.
- [ ] Draft an appropriate German `Kündigungsschreiben` without inventing contractual notice periods.
- [ ] Include a request for written confirmation and the effective cancellation date.
- [ ] Generate a printable PDF with a clearly marked handwritten-signature area.
- [ ] Return a human checklist: verify details, print, sign, copy/scan for records, and send using the chosen delivery method.
- [ ] Keep sending, signing, and proof-of-delivery tracking outside automated execution until separately implemented and approved.

### Security, privacy, and quality

- [x] Treat TODO descriptions as untrusted data and defend against prompt injection in assessment prompts.
- [x] Scope assessment queries and persistence to the authenticated user without loading unrelated profile, business, bank, movie, or document context.
- [ ] Redact secrets, credentials, full bank data, authentication tokens, and unrelated profile fields from model input and logs.
- [ ] Define retention and deletion behaviour for assessments, accepted drafts, generated PDFs, and rejected generations.
- [x] Add unit tests for classification rules, structured-output parsing, missing information, and safe fallback behaviour.
- [ ] Route-test authentication, ownership isolation, batch limits, rate limits, artifact deletion, and provider failures.
- [ ] Render and visually inspect cancellation-letter PDFs in German before release.
- [ ] Add evaluation fixtures for fully actionable, partially actionable, and human-required tasks, including ambiguous and high-impact cases.

## Next: Socials domain

### Product decisions and provider research

- [ ] Confirm initial platforms: YouTube, Instagram, Facebook, TikTok, X, Twitch, LinkedIn, and GitHub.
- [ ] Document the exact metric available for each account type: subscribers, followers, page fans, or followers/watchers.
- [ ] Research current official API access, app-review requirements, scopes, quotas, token lifetimes, costs, and personal-use restrictions for every provider before coding its adapter.
- [ ] Select the first official integration based on stable read-only access; keep every other platform usable through manual snapshots.
- [ ] Define whether an account may be shared between Life Stack users or remains strictly user-owned; default to user-owned.
- [ ] Define history retention for disconnect, disable, delete, and account ownership changes.
- [ ] Explicitly prohibit authenticated scraping and social-account password collection.

### Data model and migration

- [ ] Create a forward Alembic revision for `social_accounts`.
- [ ] Store `user_id`, platform, provider account ID, handle, display name, profile URL, optional project/business label, tracking mode, status, and timestamps.
- [ ] Permit multiple accounts per platform while preventing duplicate provider-account links per user.
- [ ] Create `social_metric_snapshots` with account, metric name, value, captured-at timestamp, source, and optional note.
- [ ] Enforce non-negative integer metric values and one canonical snapshot per account/metric/time bucket.
- [ ] Create `social_connections` or equivalent encrypted credential storage separate from account display data.
- [ ] Store token expiry, granted scopes, last refresh, last sync, next eligible sync, and sanitised last-error state.
- [ ] Add indexes for user/account listing and account/date-range chart queries.
- [ ] Decide whether provider sync audit events need a dedicated retention-limited table.
- [ ] Add an encryption key dedicated to social credentials; do not reuse `BANK_DATA_ENCRYPTION_KEY`.

### Domain calculations

- [ ] Define platform-independent metric names and map provider terminology at the adapter boundary.
- [ ] Calculate current value from the latest successful snapshot.
- [ ] Calculate seven-, 30-, 90-, and 365-day absolute and percentage change using the nearest snapshot at or before the comparison boundary.
- [ ] Return `null`, not a misleading zero, when history is insufficient.
- [ ] Calculate cross-platform totals as summed account metrics and label them as non-deduplicated audience.
- [ ] Handle account renames and provider identifier changes without splitting history.
- [ ] Keep manual and provider snapshots idempotent and define precedence when they share a date.

### API design

- [ ] Add `/socials/summary` for current totals and period changes.
- [ ] Add `/socials/accounts` user-scoped CRUD.
- [ ] Add `/socials/accounts/{id}` details and current sync metadata.
- [ ] Add `/socials/accounts/{id}/snapshots` list/create endpoints with validated date ranges and pagination.
- [ ] Add `/socials/accounts/{id}/series` for chart-ready time-series data.
- [ ] Add CSV upload with preview/validate and explicit confirm steps.
- [ ] Add `/socials/providers/{platform}/connect` and protected OAuth callback endpoints.
- [ ] Add account sync, reconnect, disconnect, disable, and delete endpoints.
- [ ] Return stable, frontend-actionable error codes without exposing provider payloads or credentials.
- [ ] Apply authentication, ownership checks, request-size limits, and rate limits to every route.

### Provider adapter architecture

- [ ] Define a provider interface for authorisation URL, callback exchange, token refresh, account discovery, metric fetch, and revocation.
- [ ] Keep provider HTTP schemas out of repositories and common API response models.
- [ ] Request only minimum read-only scopes.
- [ ] Encrypt tokens before persistence and decrypt only immediately before provider calls.
- [ ] Refresh tokens under a per-connection lock to avoid concurrent rotation races.
- [ ] Add bounded timeouts, retry only safe/idempotent requests, and respect `Retry-After`.
- [ ] Track provider quota errors separately from authentication and permanent permission failures.
- [ ] Redact tokens, authorisation codes, provider request bodies, and personal identifiers from logs.
- [ ] Verify OAuth state, exact redirect URI, PKCE where supported, and token issuer/audience where applicable.

### Synchronisation

- [ ] Implement manual one-account sync first.
- [ ] Upsert snapshots idempotently using provider account, metric, and provider observation time.
- [ ] Isolate failures so one provider/account cannot fail the entire summary.
- [ ] Add stale-data thresholds and a computed health state.
- [ ] Add scheduled Railway sync only after manual sync is stable and observable.
- [ ] Add per-provider concurrency limits and global job time budgets.
- [ ] Record sanitised sync outcomes and surface reconnect-required status.
- [ ] Avoid generating duplicate snapshots when the metric has not changed unless needed for continuity.

### Manual and CSV fallback

- [ ] Allow manual accounts without provider credentials.
- [ ] Validate manual snapshots against future dates, negative values, and accidental extreme changes.
- [ ] Define a CSV format with platform, handle/account ID, metric, date/time, value, and optional note.
- [ ] Preview parsed rows, duplicates, errors, and replacements before committing imports.
- [ ] Process confirmed CSV imports transactionally.
- [ ] Add export for account history so the user is never locked into Life Stack.

### Security, privacy, and operations

- [ ] Add social credential variables to `.env.example` without values.
- [ ] Document platform-specific data use, privacy URLs, deletion callbacks, and app-review requirements.
- [ ] Add CSRF/state-expiry tests for OAuth callbacks.
- [ ] Add account-level sync rate limiting and provider quota protection.
- [ ] Define token rotation and emergency revocation procedures.
- [ ] Include social tables and the dedicated encryption key in backup/restore planning.
- [ ] Add a user-facing provider-data deletion path and verify history-retention choices.
- [ ] Decide whether social handles/profile URLs should appear in logs; default to redaction.
- [ ] Threat-model malicious CSV files, OAuth account substitution, token leakage, replay, SSRF, and provider impersonation.

### Tests and acceptance criteria

- [ ] Unit-test period-change calculations, missing history, multiple metrics, and timezone boundaries.
- [ ] Unit-test encryption, token refresh locking, provider mapping, retry behaviour, and redaction.
- [ ] Route-test authentication, ownership isolation, validation, deletion, and OAuth state failures.
- [ ] Integration-test the migration on a temporary PostgreSQL schema.
- [ ] Contract-test provider adapters against recorded sanitised fixtures.
- [ ] A user can create a manual account, add snapshots, and retrieve accurate chart data.
- [ ] At least one official provider can connect, sync, reconnect, revoke, and disconnect end to end.
- [ ] A failed provider leaves other accounts available and returns a partial-status response.
- [ ] No raw token, authorisation code, social password, or full provider payload enters logs or API responses.
- [ ] The complete backend test suite and production configuration validation pass.

## Railway release preparation

- [x] Add non-root production Docker image and signal-safe Uvicorn entrypoint.
- [x] Add safe Alembic baseline and pre-deploy migration command.
- [x] Add liveness/readiness endpoints and Railway health configuration.
- [x] Harden the legacy development initializer against production execution.
- [x] Back up and inspect the current local PostgreSQL database.
- [x] Stamp the verified existing database at `20260901_01`; never run the baseline against it.
- [ ] Create the Railway PostgreSQL and private backend services in the same EU region as the frontend.
- [ ] Configure all production variables through Railway references/secrets.
- [x] Import data through a temporary protected database connection, verify it, then remove public database access.
- [ ] Enable Railway backups/PITR plus encrypted off-platform dumps and perform a restore drill.
- [ ] Verify `healthcheck.railway.app` host allowance, proxy client IP behaviour, secure cookies, rate limiting, and logs.
- [ ] Register and test the production Enable Banking callback only after the HTTPS domain is live.

## Banking follow-ups

- [x] Implement read-only connections, encrypted provider sessions, account balances, transaction sync, review, import, and disconnect.
- [x] Deduplicate provider transactions and preserve manually entered expenses.
- [ ] Complete sandbox end-to-end testing.
- [ ] Add scheduled synchronisation with overlap protection.
- [ ] Add consent-expiry detection and reconnect workflow.
- [ ] Add CSV import for unsupported institutions.
- [ ] Complete PSD2/GDPR retention, audit, and deletion review.

## Movie intelligence follow-ups

- [x] Store personal lists, ratings, critiques, and external ratings in PostgreSQL.
- [x] Recommend unseen films using recent ratings and critiques.
- [x] Rewrite critiques with structured OpenAI output and storage disabled.
- [x] Normalize OMDb genres into queryable watched-movie categories without discarding the original provider metadata.
- [x] Add user-scoped watched-movie category filters, grouping, counts, and deterministic ordering.
- [x] Store an explicit `watched_at` value rather than inferring watch order from record update timestamps.
- [x] Add a user-scoped movie statistics endpoint for longest watched movie, highest personal rating, oldest release, newest release, and most recently watched.
- [x] Return all tied winners and explicit `null` results when required metadata is missing or no watched movies qualify.
- [x] Unit-test runtime parsing, genre normalization, release-year parsing, watched-date ordering, ties, missing metadata, and strict user isolation.
- [ ] Persist explicit recommendation acceptance/rejection feedback.
- [ ] Evaluate recommendation quality with deterministic fixtures and user feedback history.

## Private account allowlist

- [ ] Add a normalized `ALLOWED_USER_EMAILS` production setting and document it in `.env.example` without real addresses.
- [ ] Fail closed in production when the allowlist is missing or empty, while retaining a safe development/test configuration.
- [ ] Enforce the allowlist during login, registration, and profile email changes; do not rely only on `REGISTRATION_ENABLED=false`.
- [ ] Compare canonicalized email addresses consistently and reject duplicate or malformed allowlist entries during startup.
- [ ] Return a generic authentication failure for disallowed accounts so the API does not reveal account or allowlist membership.
- [ ] Add an owner-safe way to inspect configured allowlist membership without exposing it to unauthenticated users or logs.
- [ ] Test allowed and denied login, disabled registration, email-change bypass attempts, case normalization, missing production configuration, and existing-session revocation policy.
- [ ] Document the Railway secret-rotation procedure and the process for safely adding or removing a household member.

## Statutory invoicing follow-ups

- [ ] Integrate Gazd Systems with NAV Online Számla 3.0 using encrypted technical-user credentials, retries, and acceptance polling.
- [ ] Generate and validate EN 16931/XRechnung or eligible hybrid invoices for applicable Gavod Gebäudeservice B2B invoices.
- [ ] Add outbound invoice email and immutable delivery audit records.
- [ ] Add jurisdiction-specific validation tests and production reconciliation tools.

## Net worth tracking

- [x] Add a user-scoped net-worth domain covering assets, liabilities, and ownership percentage.
- [x] Support manually valued cash, bank accounts, investments, property, vehicles, businesses, loans, credit cards, and other assets or debts.
- [x] Reuse linked-bank balances without double-counting accounts that also have a manual valuation.
- [ ] Store immutable valuation snapshots so historical net worth can be reconstructed accurately.
- [x] Calculate current total assets, total liabilities, and net worth per selected currency.
- [ ] Track change over one month, three months, one year, and all time without confusing transfers with gains or losses.
- [ ] Add multi-currency valuations with an explicit base currency, exchange-rate source, and captured conversion rate.
- [ ] Distinguish liquid assets, investments, property, and debt in summary responses.
- [x] Add user-scoped CRUD, summary, history-series, and snapshot endpoints with ownership checks.
- [ ] Define safe deletion, archival, bank-disconnection, and historical-retention behaviour.
- [ ] Unit-test aggregation, liabilities, partial ownership, currency conversion, missing valuations, and bank/manual deduplication.

## Longer-term backend ideas

- [ ] Income and cash-flow forecasting domain.
- [ ] Goals, habits, workouts, notes, and journaling APIs.
- [ ] Unified notification/event service.
- [ ] Account-level export and verified deletion workflow.
- [ ] Structured observability with correlation IDs and strict personal-data redaction.
