# Livetse Promotion Service

Production-ready FastAPI service for Livetse promotional content, announcements, banners, and advertising campaigns.

**Version:** `1.2.0`

## What this service manages

- **Announcements** with scheduling, visibility/targeting and type:
  - `info`
  - `warning`
  - `error`
  - `success`
- **Banners** with scheduling and upload support.
- **Advertising campaigns** with multiple images/assets per campaign.
- **Ad placement positions** per platform/page (`landing`, `app`, `extension`).
- **Ad statistics** per asset/day.
- RS256 JWT validation through JWKS or a static public key.
- PostgreSQL + SQLAlchemy Async + Alembic.
- Optional Redis-backed distributed rate limiting.
- External upload service integration.
- Structured logging, request IDs, security headers, CORS, GZip and Trusted Host protection.
- Runtime feature flags controlled from environment variables.

---

## Architecture

```text
Client / Admin
     |
     | HTTP + Bearer JWT (admin routes)
     v
+----------------------------+
| Livetse Promotion Service  |
| FastAPI                    |
+-------------+--------------+
              |
      +-------+--------+----------------+
      |                |                |
      v                v                v
 PostgreSQL          Redis        Upload Service
 persistence       rate limit       images/files
```

Internal module flow:

```text
router/admin
    |
    v
 service
    |
    v
 repository
    |
    v
 PostgreSQL
```

---

## Project structure

```text
.
├── main.py
├── app/
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── jwks.py
│   │   ├── logging.py
│   │   ├── middleware.py
│   │   ├── rate_limit.py
│   │   ├── redis.py
│   │   └── security.py
│   ├── modules/
│   │   ├── announcements/
│   │   ├── banners/
│   │   └── ads/
│   ├── services/
│   │   └── upload_client.py
│   └── shared/
├── alembic/
│   └── versions/
├── tests/
├── .env.example
├── Dockerfile
├── Makefile
├── requirements.txt
└── requirements-dev.txt
```

---

# Production configuration

Copy `.env.example` only for local/staging use. In real production, inject environment variables and secrets through the orchestrator/secret manager whenever possible.

The service supports `APP_ENV_FILE` if a specific env file must be loaded:

```bash
APP_ENV_FILE=/run/secrets/promotion.env
```

## Application / feature switches

| Variable | Default | Description |
|---|---:|---|
| `APP_NAME` | `livetse-promotion-service` | Service name |
| `APP_ENV` | `development` | `development`, `test`, `staging`, `production` |
| `APP_VERSION` | `1.2.0` | Service version |
| `BASE_URL` | empty | Public service base URL |
| `ENABLE_ANNOUNCEMENTS` | `true` | Register announcement APIs |
| `ENABLE_BANNERS` | `true` | Register banner APIs |
| `ENABLE_ADS` | `true` | Register ad APIs |
| `ENABLE_UPLOADS` | `true` | Enable upload-service operations |
| `ENABLE_DOCS` | auto | Enable Swagger/ReDoc/OpenAPI; defaults off in production |

## Database

| Variable | Default | Description |
|---|---:|---|
| `DATABASE_URL` | required | `postgresql+asyncpg://...` |
| `DATABASE_NAME` | empty | Optional informational database name |
| `DB_POOL_SIZE` | `10` | SQLAlchemy base pool size |
| `DB_MAX_OVERFLOW` | `10` | Extra pool connections |
| `DB_POOL_TIMEOUT` | `30` | Pool wait timeout in seconds |
| `DB_POOL_RECYCLE` | `1800` | Connection recycle seconds |
| `DB_ECHO` | `false` | SQLAlchemy SQL output |
| `AUTO_CREATE_SCHEMA` | `false` | Dev-only schema creation; forbidden in production |
| `HEALTH_READY_DB_CHECK_ENABLED` | `true` | DB check in `/health/ready` |

Production uses Alembic migrations. Do **not** enable `AUTO_CREATE_SCHEMA` in production.

## Logging

| Variable | Default | Description |
|---|---:|---|
| `LOG_ENABLED` | `true` | Master logging switch |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, etc. |
| `LOG_JSON` | `true` | JSON structured logs when true; plain text when false |
| `LOG_ACCESS_ENABLED` | `true` | Application request/access event logs |
| `LOG_SQL_ENABLED` | `false` | SQLAlchemy engine logs |
| `LOG_UVICORN_ACCESS_ENABLED` | `false` | Uvicorn native access logger |

Recommended production values:

```env
LOG_ENABLED=true
LOG_LEVEL=INFO
LOG_JSON=true
LOG_ACCESS_ENABLED=true
LOG_SQL_ENABLED=false
LOG_UVICORN_ACCESS_ENABLED=false
```

## Rate limiting

| Variable | Default | Description |
|---|---:|---|
| `RATE_LIMIT_ENABLED` | `true` | Master rate-limit switch |
| `RATE_LIMIT_BACKEND` | `memory` | `memory` or `redis` |
| `RATE_LIMIT_REQUESTS` | `120` | Requests allowed per window |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Fixed-window duration |
| `RATE_LIMIT_PREFIX` | `promotion:ratelimit` | Redis key prefix |
| `RATE_LIMIT_FAIL_OPEN` | `true` | Continue serving if backend is unavailable |
| `RATE_LIMIT_EXEMPT_PATHS` | health paths | Comma-separated paths excluded from limiting |

For a **single local process**, `memory` is sufficient. For production with multiple Uvicorn workers/pods/instances, use Redis:

```env
REDIS_ENABLED=true
REDIS_URL=redis://redis:6379/0
RATE_LIMIT_ENABLED=true
RATE_LIMIT_BACKEND=redis
RATE_LIMIT_REQUESTS=120
RATE_LIMIT_WINDOW_SECONDS=60
```

The service returns `429 Too Many Requests` when the configured limit is exceeded and includes rate-limit headers.

## Redis

| Variable | Default | Description |
|---|---:|---|
| `REDIS_ENABLED` | `false` | Enable Redis client lifecycle |
| `REDIS_URL` | empty | Redis connection URL |
| `REDIS_CONNECT_TIMEOUT` | `2` | Connect timeout |
| `REDIS_SOCKET_TIMEOUT` | `2` | Socket timeout |
| `REDIS_HEALTH_CHECK_INTERVAL` | `30` | Redis connection health interval |

If `RATE_LIMIT_BACKEND=redis`, both `REDIS_ENABLED=true` and `REDIS_URL` are required.

## HTTP middleware / security

| Variable | Default | Description |
|---|---:|---|
| `ENABLE_REQUEST_CONTEXT` | `true` | Request ID and access context middleware |
| `ENABLE_SECURITY_HEADERS` | `true` | Security response headers |
| `ENABLE_GZIP` | `true` | GZip response compression |
| `GZIP_MINIMUM_SIZE` | `1024` | Minimum response size for GZip |
| `ENABLE_CORS` | `true` | CORS middleware |
| `CORS_ORIGINS` | empty | Allowed origins, comma-separated |
| `CORS_ALLOW_CREDENTIALS` | `true` | CORS credentials |
| `CORS_ALLOW_METHODS` | standard methods | Comma-separated methods |
| `CORS_ALLOW_HEADERS` | auth/content headers | Comma-separated headers |
| `ENABLE_TRUSTED_HOSTS` | `true` | Trusted Host middleware |
| `TRUSTED_HOSTS` | `*` | Comma-separated allowed hosts |

Production safety checks reject wildcard trusted hosts and wildcard CORS origins when their corresponding middleware is enabled.

## JWT / admin authorization

The service is a resource server and does **not** issue access tokens.

Preferred production configuration:

```env
JWT_JWKS_URL=https://auth.example.com/.well-known/jwks.json
JWT_REQUIRE_EXP=true
JWT_LEEWAY_SECONDS=10
ADMIN_ROLES=ADMIN,SUPER_ADMIN
```

A static RSA public key or key file can be used instead:

```env
JWT_PUBLIC_KEY=
JWT_PUBLIC_KEY_PATH=/run/secrets/auth-public.pem
```

Relevant variables:

```text
JWT_JWKS_URL
JWT_PUBLIC_KEY
JWT_PUBLIC_KEY_PATH
JWT_ISSUER
JWT_AUDIENCE
JWT_REQUIRE_EXP
JWT_LEEWAY_SECONDS
JWT_JWKS_CACHE_TTL_SECONDS
JWT_JWKS_CONNECT_TIMEOUT
JWT_JWKS_READ_TIMEOUT
ADMIN_ROLES
```

Production startup fails when no JWT verification source is configured.

## Upload service

```env
ENABLE_UPLOADS=true
UPLOAD_SERVICE_URL=https://upload.example.com
UPLOAD_SERVICE_API_KEY=CHANGE_TO_A_LONG_RANDOM_UPLOAD_API_KEY
UPLOAD_CONNECT_TIMEOUT=5
UPLOAD_READ_TIMEOUT=60
UPLOAD_MAX_CONNECTIONS=50
UPLOAD_MAX_KEEPALIVE_CONNECTIONS=20
MAX_UPLOAD_SIZE_MB=10
ALLOWED_UPLOAD_CONTENT_TYPES=image/jpeg,image/png,image/webp,image/gif
BANNERS_UPLOAD_FOLDER=banners
ANNOUNCEMENTS_UPLOAD_FOLDER=announcements
ADS_UPLOAD_FOLDER=ads
```

When uploads are disabled, upload/delete operations return a service-unavailable error instead of silently attempting upstream requests.

---

# Announcements

Announcements now include an explicit `type` field.

Allowed values are exactly:

```text
info
warning
error
success
```

`danger` is **not** a valid type.

If `type` is omitted during creation, it defaults to:

```text
info
```

Example:

```json
{
  "text": "Scheduled maintenance starts tonight.",
  "type": "warning",
  "sections": ["LANDING", "DASHBOARD"],
  "visibility": "PUBLIC",
  "subscription_types": [],
  "target_data_tiers": [],
  "target_live_tread_access": null,
  "target_user_data_groups": [],
  "target_devices": [],
  "display_start_at": "2026-08-11T18:00:00Z",
  "display_expire_at": "2026-08-12T03:00:00Z",
  "is_active": true
}
```

Admin list filtering also supports:

```http
GET /announcements/admin?type=warning
```

For multipart upload creation:

```text
type=info|warning|error|success
```

is accepted and defaults to `info`.

## Announcement endpoints

Public:

```text
GET /announcements/latest
GET /announcements/history
```

Admin:

```text
GET    /announcements/admin
GET    /announcements/admin/{announcement_id}
POST   /announcements/admin
POST   /announcements/admin/upload
PUT    /announcements/admin/{announcement_id}
PUT    /announcements/admin/{announcement_id}/upload
DELETE /announcements/admin/{announcement_id}
```

---

# Advertising campaigns and positions

A campaign can contain **multiple images/assets**.

Every ad image now has:

```text
platform
position
```

Supported platforms:

```text
landing
app
extension
```

Example concept:

```text
Landing page

position 1 -> campaign X / image A
position 2 -> campaign Y / image B
position 3 -> campaign X / image C
position 4 -> campaign Z / image D
```

The public endpoint:

```http
GET /ads/?platform=landing
```

returns currently active assets ordered by:

```text
position ASC
```

Each response item includes both:

```json
{
  "campaign_id": "...",
  "platform": "landing",
  "position": 1,
  "image_url": "...",
  "link_url": "..."
}
```

This means the frontend can render page positions directly in the returned order or by the explicit `position` value.

## Position conflict protection

By default:

```env
ADS_POSITION_CONFLICT_CHECK_ENABLED=true
ADS_MIN_POSITION=1
ADS_MAX_POSITION=100
```

Rules:

1. One campaign cannot contain two assets with the same `platform + position`.
2. Two **active campaigns with overlapping schedules** cannot reserve the same `platform + position`.
3. The same `platform + position` can be reused by campaigns whose schedules do not overlap.
4. Activating or rescheduling an existing campaign also re-checks its asset positions.
5. Public delivery is sorted by position.

Example conflict:

```text
Campaign X: landing / position 1 / Aug 1 -> Aug 20
Campaign Y: landing / position 1 / Aug 10 -> Aug 30
```

If both are active, the service rejects the conflicting operation with `422`.

This can be disabled explicitly if business rules require collisions:

```env
ADS_POSITION_CONFLICT_CHECK_ENABLED=false
```

## Create ad asset without upload

```http
POST /ads/admin/{campaign_id}/assets
Content-Type: multipart/form-data
Authorization: Bearer <JWT>
```

Required fields:

```text
platform
position
```

Optional fields:

```text
title
image_url
link_url
```

Example:

```bash
curl -X POST \
  http://localhost:8000/ads/admin/$CAMPAIGN_ID/assets \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "platform=landing" \
  -F "position=1" \
  -F "title=Landing hero campaign" \
  -F "image_url=https://cdn.example.com/ad.webp" \
  -F "link_url=https://example.com"
```

## Create ad asset with file upload

```http
POST /ads/admin/{campaign_id}/assets/upload
```

Example:

```bash
curl -X POST \
  http://localhost:8000/ads/admin/$CAMPAIGN_ID/assets/upload \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@ad.webp" \
  -F "platform=landing" \
  -F "position=2" \
  -F "title=Second landing position" \
  -F "link_url=https://example.com"
```

## Change an asset position

```http
PUT /ads/admin/assets/{asset_id}
Content-Type: application/json
```

Example:

```json
{
  "platform": "landing",
  "position": 4
}
```

The same conflict validation runs before the new placement is committed.

## Ads endpoints

Public:

```text
GET /ads/?platform={landing|app|extension}
```

Admin campaigns:

```text
GET    /ads/admin
GET    /ads/admin/{campaign_id}
POST   /ads/admin
PUT    /ads/admin/{campaign_id}
DELETE /ads/admin/{campaign_id}
```

Admin assets:

```text
GET    /ads/admin/{campaign_id}/assets
GET    /ads/admin/assets/{asset_id}
POST   /ads/admin/{campaign_id}/assets
POST   /ads/admin/{campaign_id}/assets/upload
PUT    /ads/admin/assets/{asset_id}
DELETE /ads/admin/assets/{asset_id}
```

Statistics:

```text
POST /ads/admin/stats
GET  /ads/admin/assets/{asset_id}/stats
GET  /ads/admin/{campaign_id}/stats
```

---

# Banners

The existing banner module remains available and can be independently disabled with:

```env
ENABLE_BANNERS=false
```

It supports scheduled banners, platform selection, sort order, image metadata and upload integration.

---

# Database migrations

Current migration chain:

```text
20260809_0001_initial_schema
        |
        v
20260809_0002_production_hardening
        |
        v
20260811_0003_announcement_types_ad_positions
```

The latest migration:

- creates PostgreSQL enum `announcement_type`;
- adds `announcements.type` with default `info`;
- adds index `ix_announcements_type`;
- adds `ad_assets.position`;
- backfills deterministic positions for existing assets;
- adds positive-position check;
- adds per-campaign/platform/position uniqueness;
- adds `platform + position` index.

Run before starting the new application version:

```bash
alembic upgrade head
```

For an existing pre-Alembic database, follow the baseline/stamping process already established for the project before upgrading to head.

---

# Running locally

Create a local env file such as `.env.development`:

```env
APP_ENV=development
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/promotion
UPLOAD_SERVICE_URL=http://localhost:8001
UPLOAD_SERVICE_API_KEY=local-development-key-123456
JWT_PUBLIC_KEY_PATH=./dev-public.pem
ENABLE_DOCS=true
RATE_LIMIT_BACKEND=memory
REDIS_ENABLED=false
TRUSTED_HOSTS=localhost,127.0.0.1
CORS_ORIGINS=http://localhost:3000
```

Install dependencies:

```bash
python -m pip install -r requirements-dev.txt
```

Migrate:

```bash
alembic upgrade head
```

Run:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

or:

```bash
make run
```

---

# Tests

```bash
python -m pytest -q
```

Compile check:

```bash
python -m compileall -q app main.py alembic
```

The test suite includes validation for:

- RS256 authentication behavior;
- admin authorization;
- upload MIME/size validation;
- campaign date ranges;
- banner date ranges;
- announcement tier normalization;
- announcement types including `error`;
- rejection of legacy `danger` type;
- positive ad positions.

---

# Docker

Build:

```bash
docker build -t livetse-promotion-service:1.2.0 .
```

Run:

```bash
docker run --rm \
  --env-file .env.production \
  -p 8000:8000 \
  livetse-promotion-service:1.2.0
```

Runtime variables used by the Docker command:

```env
PORT=8000
WEB_CONCURRENCY=2
FORWARDED_ALLOW_IPS=127.0.0.1
```

For multi-worker containers, Redis-backed rate limiting is recommended.

---

# Health checks

Liveness:

```http
GET /health/live
```

Readiness:

```http
GET /health/ready
```

`/health/ready` checks PostgreSQL by default. The DB check can be disabled with:

```env
HEALTH_READY_DB_CHECK_ENABLED=false
```

Both health endpoints are excluded from rate limiting by default.

---

# Production deployment order

Recommended release sequence:

```text
1. Provision PostgreSQL / Redis / Upload Service / Auth JWKS.
2. Inject production environment variables and secrets.
3. Run: alembic upgrade head
4. Start the new service version.
5. Verify: /health/live
6. Verify: /health/ready
7. Verify admin JWT access.
8. Create a test announcement with each type if needed.
9. Verify landing ad positions and conflict behavior.
10. Monitor JSON logs and 429/error rates.
```

---

# Production checklist

- [ ] `APP_ENV=production`
- [ ] strong database credentials
- [ ] `AUTO_CREATE_SCHEMA=false`
- [ ] `alembic upgrade head` completed
- [ ] `JWT_JWKS_URL` or static public key configured
- [ ] valid `UPLOAD_SERVICE_API_KEY`
- [ ] explicit `TRUSTED_HOSTS`
- [ ] explicit `CORS_ORIGINS`
- [ ] Swagger/OpenAPI disabled unless intentionally exposed
- [ ] `LOG_JSON=true`
- [ ] SQL logs disabled unless debugging
- [ ] `RATE_LIMIT_ENABLED=true`
- [ ] Redis backend enabled for multiple workers/instances
- [ ] upload size/content types reviewed
- [ ] ad position range reviewed
- [ ] health endpoints connected to container/orchestrator probes
- [ ] secrets are injected, not committed

---

# Important behavior summary

### Announcement type

```text
info | warning | error | success
```

### Ad placement

```text
campaign -> many assets/images
asset -> platform + position
public output -> active assets ordered by position
```

### Position collision

```text
same platform + same position + overlapping active campaign schedule
=> rejected by default
```

### Runtime controls

Most operational behavior can now be enabled/disabled or tuned through `.env`, including:

```text
business modules
uploads
docs
logging + log format + log level
access logs
SQL logs
rate limiting
rate-limit backend/window/limit
Redis
request context
security headers
GZip
CORS
Trusted Hosts
DB readiness checks
ad position conflict checks
```
