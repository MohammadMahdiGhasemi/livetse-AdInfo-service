# Livetse Promotion Service

FastAPI service for announcements, banners and ad campaigns/assets/stats.

## Production hardening included

This version adds:

- strict environment-based configuration with production safety checks;
- RS256 Bearer JWT verification using JWKS/static public keys;
- role-based admin authorization from verified JWT claims;
- optional issuer/audience enforcement and automatic JWKS key rotation support;
- reusable pooled `httpx.AsyncClient` for the upload service;
- upload MIME/type and size limits without reading the whole file into RAM;
- database connection pool configuration and graceful shutdown;
- `/health/live` and `/health/ready` endpoints;
- request IDs, structured JSON logs and basic security response headers;
- configurable CORS and trusted hosts;
- Alembic migrations instead of automatic schema mutation in production;
- DB integrity constraints/indexes for date ranges, required ad fields and stats;
- non-root Docker image and container healthcheck;
- CI tests and compile checks;
- safer upload replacement/cleanup behavior for banners and failed DB writes.

## Required production configuration

Copy `.env.example` to your secret/config system. Do **not** commit real secrets.

Required values include:

- `DATABASE_URL` — must use `postgresql+asyncpg://...`
- `JWT_JWKS_URL` — preferred identity-service JWKS endpoint for RS256 verification/key rotation
- `JWT_PUBLIC_KEY` / `JWT_PUBLIC_KEY_PATH` — optional static-key fallback when JWKS is unavailable
- `ADMIN_ROLES` — comma-separated roles allowed to access admin endpoints (default `ADMIN,SUPER_ADMIN`)
- `UPLOAD_SERVICE_URL`
- `UPLOAD_SERVICE_API_KEY` — minimum 16 chars in production
- `TRUSTED_HOSTS` — explicit hostnames in production, not `*`

Production also refuses `AUTO_CREATE_SCHEMA=true` and wildcard trusted hosts/CORS.
Interactive API docs are disabled by default in production.

Generate strong secrets with your organization’s secret manager or, for example:

```bash
openssl rand -hex 32
```

## Database migrations

### Fresh database

```bash
alembic upgrade head
```

### Existing database created by the old `create_all()` startup behavior

1. Take a database backup/snapshot.
2. Run `scripts/pre_migration_check.sql` and make sure every returned count is `0`.
3. Verify the existing tables/indexes correspond to the old service schema.
4. Mark that old schema as the Alembic baseline:

```bash
alembic stamp 20260809_0001
```

5. Apply the hardening migration:

```bash
alembic upgrade head
```

Revision `20260809_0002` intentionally validates legacy data. If it fails because of NULL/invalid rows, correct those rows explicitly and rerun the migration. Do not blindly stamp `head`, because that would mark constraints as applied when they are not actually present.

For production orchestration, run migrations as a separate deployment job before rolling out application replicas rather than having every replica migrate on startup.

## Run locally

Use environment variables or a local `.env.development` file.

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn main:app --reload --port 8000
```

Health endpoints:

```text
GET /health/live
GET /health/ready
```

## Tests

```bash
make test
```

CI also runs Python bytecode compilation and the test suite.

## Docker

Build:

```bash
docker build -t livetse-promotion-service:1.0.0 .
```

Run migrations as a one-off job using the same image/environment:

```bash
docker run --rm --env-file .env.production \
  livetse-promotion-service:1.0.0 alembic upgrade head
```

Run the service:

```bash
docker run --rm -p 8000:8000 --env-file .env.production \
  -e WEB_CONCURRENCY=2 \
  livetse-promotion-service:1.0.0
```

The image runs as an unprivileged user.

### Worker / database pool sizing

Each worker owns its own SQLAlchemy pool. Approximate worst-case DB connections are:

```text
WEB_CONCURRENCY × (DB_POOL_SIZE + DB_MAX_OVERFLOW)
```

With the defaults (`2 × (10 + 10)`), the service may consume up to about 40 DB connections under burst load. Size these values against PostgreSQL’s connection budget and the number of replicas.

## Reverse proxy

`FORWARDED_ALLOW_IPS` defaults to `127.0.0.1`. Set it only to the IP/CIDR of the trusted reverse proxy/container network. Do not use `*` when the service is directly reachable from untrusted networks.

TLS should normally terminate at your ingress/reverse proxy. Admin endpoints require a verified RS256 Bearer token whose `role` is included in `ADMIN_ROLES`; network-layer restrictions are still recommended.

## Upload service

Allowed upload content types and maximum size are controlled by:

```text
MAX_UPLOAD_SIZE_MB
ALLOWED_UPLOAD_CONTENT_TYPES
```

The default allowed types are JPEG, PNG, WebP and GIF. Upload-service upstream errors are returned to clients as sanitized errors; upstream bodies/API keys are not exposed.

## Deployment checklist

- [ ] Production secrets are stored outside the repository and rotated from development values.
- [ ] `APP_ENV=production`.
- [ ] `AUTO_CREATE_SCHEMA=false`.
- [ ] `ENABLE_DOCS=false` unless explicitly required.
- [ ] `TRUSTED_HOSTS` contains only real production hostnames.
- [ ] `CORS_ORIGINS` contains only approved browser origins, or is empty if CORS is unnecessary.
- [ ] DB backup completed before first Alembic adoption on an existing DB.
- [ ] `scripts/pre_migration_check.sql` returns zero invalid rows.
- [ ] `alembic upgrade head` completed successfully.
- [ ] `/health/live` and `/health/ready` pass behind the deployed ingress.
- [ ] Upload service connectivity/API key tested.
- [ ] `JWT_JWKS_URL` (preferred) or a static RSA public key is configured.
- [ ] JWT issuer/audience configured if those claims are part of the authentication contract.
- [ ] `ADMIN_ROLES` matches the roles issued by the identity service.
- [ ] DB pool size checked against worker/replica count.
- [ ] Logs are collected from stdout and `X-Request-ID` is propagated by the gateway.
