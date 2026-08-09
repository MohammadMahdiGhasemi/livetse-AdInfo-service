# Livetse Promotion Service

Production-oriented Promotion Service for the Livetse platform, built with FastAPI, PostgreSQL, SQLAlchemy Async, Alembic, RS256 JWT authentication, JWKS key discovery, and an external upload service.

The service provides three main business capabilities:

- **Announcements** — public and targeted user announcements.
- **Banners** — scheduled promotional banners with image upload lifecycle management.
- **Ads** — advertising campaigns, platform-specific assets, and daily statistics.

The service is designed to run as a stateless HTTP application behind a reverse proxy or container ingress.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Business Modules](#business-modules)
- [Authentication and Authorization](#authentication-and-authorization)
- [JWT Claims](#jwt-claims)
- [JWKS and Key Rotation](#jwks-and-key-rotation)
- [Configuration](#configuration)
- [Database](#database)
- [Database Migrations](#database-migrations)
- [Upload Service](#upload-service)
- [Running Locally](#running-locally)
- [Running Tests](#running-tests)
- [Docker](#docker)
- [Health Checks](#health-checks)
- [Logging and Request IDs](#logging-and-request-ids)
- [Security](#security)
- [API Overview](#api-overview)
- [Deployment](#deployment)
- [Production Checklist](#production-checklist)
- [Current Implementation Notes](#current-implementation-notes)

---

# Overview

The Promotion Service is responsible for promotional and communication content used by Livetse clients.

It owns the persistence and delivery rules for:

```text
Announcements
Banners
Advertising Campaigns
Advertising Assets
Advertising Statistics
```

It does **not** issue authentication tokens.

Authentication is delegated to an external Identity/Auth Service. Clients send the access token directly to this service using the standard HTTP Bearer authentication scheme.

The Promotion Service acts as a **Resource Server**:

```text
Client
   |
   | Authorization: Bearer <JWT>
   |
   v
Promotion Service
   |
   |-- Verify RS256 signature
   |-- Resolve signing key by kid
   |-- Validate exp
   |-- Optionally validate issuer/audience
   |-- Extract verified user claims
   |
   +--> Business modules
```

---

# Features

## Authentication

- RS256 JWT verification.
- JWKS-based public key discovery.
- `kid`-based signing key selection.
- Automatic JWKS refresh for unknown/rotated keys.
- Static RSA public key fallback.
- JWT expiration validation.
- Optional issuer validation.
- Optional audience validation.
- Configurable clock leeway.
- Role-based admin authorization.
- No private signing keys are stored by this service.

## Database

- PostgreSQL.
- SQLAlchemy 2 async engine.
- `asyncpg` driver.
- Connection pooling.
- Pool pre-ping.
- Connection recycling.
- Async sessions.
- Alembic database migrations.
- Production integrity constraints.
- PostgreSQL GIN indexes for announcement targeting arrays.

## Uploads

- Shared asynchronous HTTP client.
- Connection pooling.
- Configurable connect/read timeouts.
- MIME-type validation.
- Maximum file-size validation.
- Filename sanitization.
- Configurable upload folders.
- Sanitized upstream errors.
- Best-effort cleanup for failed database writes.

## Runtime

- Async FastAPI application.
- Graceful startup/shutdown lifecycle.
- Structured JSON logging.
- Request ID propagation.
- Security response headers.
- GZip response compression.
- Trusted Host middleware.
- Explicit CORS configuration.
- Liveness and readiness endpoints.
- Docker image running as non-root.
- Configurable Uvicorn worker count.
- CI compile and test checks.

---

# Technology Stack

| Component | Technology |
|---|---|
| Language | Python 3.12 |
| HTTP framework | FastAPI |
| ASGI server | Uvicorn |
| Validation | Pydantic v2 |
| Configuration | pydantic-settings |
| ORM | SQLAlchemy 2 |
| Database | PostgreSQL |
| PostgreSQL driver | asyncpg |
| Migrations | Alembic |
| HTTP client | httpx |
| JWT | PyJWT + cryptography |
| Authentication | RS256 / JWKS |
| Testing | pytest + pytest-asyncio |
| Container | Docker |

The exact package versions are pinned in:

```text
requirements.txt
requirements-dev.txt
```

---

# Architecture

High-level request flow:

```text
                           +---------------------+
                           |   Identity Service  |
                           |                     |
                           | JWT / JWKS endpoint |
                           +----------+----------+
                                      |
                                      | public signing keys
                                      v
+-------------+             +---------+----------+
|             |   HTTP      |                    |
| Web / App / +------------>| Promotion Service  |
| Extension   | Bearer JWT  |                    |
|             |             +-----+--------+-----+
+-------------+                   |        |
                                  |        |
                     +------------+        +----------------+
                     |                                      |
                     v                                      v
            +--------+---------+                   +--------+--------+
            |                  |                   |                 |
            |   PostgreSQL     |                   | Upload Service  |
            |                  |                   |                 |
            +------------------+                   +-----------------+
```

Internal application flow:

```text
FastAPI Router
     |
     v
Service Layer
     |
     +------------------+
     |                  |
     v                  v
Repository         Upload Client
     |
     v
PostgreSQL
```

The business modules use a simple layered architecture:

```text
router.py / admin.py
        |
        v
    service.py
        |
        v
      repo.py
        |
        v
     model.py
```

Pydantic request and response contracts live in:

```text
schema.py
```

---

# Project Structure

```text
.
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       ├── 20260809_0001_initial_schema.py
│       └── 20260809_0002_production_hardening.py
│
├── app/
│   ├── api/
│   │   └── router.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── jwks.py
│   │   ├── logging.py
│   │   ├── middleware.py
│   │   ├── redis.py
│   │   └── security.py
│   │
│   ├── events/
│   │   ├── consumer.py
│   │   └── publisher.py
│   │
│   ├── modules/
│   │   ├── announcements/
│   │   │   ├── admin.py
│   │   │   ├── model.py
│   │   │   ├── repo.py
│   │   │   ├── router.py
│   │   │   ├── schema.py
│   │   │   ├── service.py
│   │   │   └── README.md
│   │   │
│   │   ├── banners/
│   │   │   ├── admin.py
│   │   │   ├── model.py
│   │   │   ├── repo.py
│   │   │   ├── router.py
│   │   │   ├── schema.py
│   │   │   ├── service.py
│   │   │   └── README.md
│   │   │
│   │   └── ads/
│   │       ├── admin.py
│   │       ├── model.py
│   │       ├── repo.py
│   │       ├── router.py
│   │       ├── schema.py
│   │       ├── service.py
│   │       └── README.md
│   │
│   ├── services/
│   │   └── upload_client.py
│   │
│   ├── shared/
│   │   ├── auth.py
│   │   ├── base_model.py
│   │   ├── enums.py
│   │   └── utils.py
│   │
│   └── models_registry.py
│
├── scripts/
│   └── pre_migration_check.sql
│
├── tests/
│   ├── conftest.py
│   ├── test_app_contract.py
│   ├── test_auth.py
│   ├── test_schemas.py
│   └── test_upload_validation.py
│
├── .env.example
├── .dockerignore
├── .gitignore
├── Dockerfile
├── Makefile
├── alembic.ini
├── main.py
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

---

# Business Modules

## Announcements

Path:

```text
app/modules/announcements
```

Responsibilities:

- Public announcements.
- Private/targeted announcements.
- Announcement scheduling.
- User targeting based on verified JWT claims.
- Announcement history.
- Admin CRUD operations.
- Optional announcement image upload.

See:

```text
app/modules/announcements/README.md
```

---

## Banners

Path:

```text
app/modules/banners
```

Responsibilities:

- Scheduled banners.
- Platform-based banner delivery.
- Banner ordering.
- Admin CRUD operations.
- Image upload.
- Image metadata persistence.
- Safe image replacement and cleanup.

See:

```text
app/modules/banners/README.md
```

---

## Ads

Path:

```text
app/modules/ads
```

Responsibilities:

- Ad campaigns.
- Ad assets.
- Platform-specific ad delivery.
- Daily views/click statistics.
- Bulk statistics upsert.
- Asset image upload.

See:

```text
app/modules/ads/README.md
```

---

# Authentication and Authorization

## Client Request

Authenticated requests must send:

```http
Authorization: Bearer <access-token>
```

Example:

```bash
curl \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  https://promotion.example.com/announcements/history?section=DASHBOARD&visibility=PRIVATE
```

The token is issued externally.

The Promotion Service does not:

- authenticate passwords;
- generate access tokens;
- refresh access tokens;
- store JWT private keys.

---

# JWT Verification Flow

For a request containing a Bearer token:

```text
Authorization Header
        |
        v
Extract token
        |
        v
Read JWT header
        |
        +--> alg must equal RS256
        |
        v
Read kid
        |
        v
Resolve public key
        |
        +--> JWKS
        |
        +--> static RSA public key fallback
        |
        v
Verify RSA signature
        |
        v
Validate required claims
        |
        +--> id
        +--> exp (default)
        |
        v
Validate issuer/audience if configured
        |
        v
Build CurrentUser
```

Tokens using an algorithm other than `RS256` are rejected.

---

# JWT Claims

A typical token payload can look like:

```json
{
  "id": "673b335fc932fc7671ee73d7",
  "phoneNumber": "09000000000",
  "dataTier": "GOLD",
  "role": "VIP",
  "liveTreadAccess": true,
  "userDataGroup": "COMPLETE",
  "device": "DESKTOP",
  "iat": 1786250439,
  "exp": 1786263039
}
```

The verified token is converted into:

```python
CurrentUser(
    id=...,
    phoneNumber=...,
    dataTier=...,
    role=...,
    liveTreadAccess=...,
    userDataGroup=...,
    device=...,
    iat=...,
    exp=...,
)
```

## Normalization

The authentication layer currently normalizes:

```text
role      -> uppercase
dataTier  -> uppercase
```

Examples:

```text
admin -> ADMIN
Gold  -> GOLD
gold  -> GOLD
```

`liveTreadAccess` supports boolean values and defensively accepts common legacy representations such as:

```text
true
false
"true"
"false"
"1"
"0"
"yes"
"no"
```

---

# User Authentication vs Admin Authorization

Two authentication dependencies are available.

## Optional Authentication

```python
get_current_user
```

Behavior:

```text
No Authorization header
    -> returns None

Valid token
    -> returns CurrentUser

Invalid / expired token
    -> HTTP 401
```

This is currently used by announcement history so public history can be accessed anonymously while private history can use JWT targeting.

---

## Required Authentication

```python
require_current_user
```

Behavior:

```text
Missing token
    -> HTTP 401

Invalid token
    -> HTTP 401

Valid token
    -> CurrentUser
```

---

## Admin Authorization

Admin routes use:

```python
require_admin
```

The verified JWT `role` must exist in:

```env
ADMIN_ROLES=ADMIN,SUPER_ADMIN
```

Example:

```text
role=ADMIN
    -> allowed

role=SUPER_ADMIN
    -> allowed

role=VIP
    -> 403 Forbidden

role=USER
    -> 403 Forbidden
```

A valid token does not automatically grant administrative privileges.

---

# JWKS and Key Rotation

The preferred authentication configuration is:

```env
JWT_JWKS_URL=https://auth.example.com/.well-known/jwks.json
```

Expected JWKS structure:

```json
{
  "keys": [
    {
      "kty": "RSA",
      "kid": "signing-key-id",
      "use": "sig",
      "alg": "RS256",
      "n": "...",
      "e": "AQAB"
    }
  ]
}
```

Only compatible RSA signing keys are accepted.

The JWKS client:

1. downloads public keys;
2. indexes them by `kid`;
3. caches them;
4. uses the JWT `kid` to select the signing key;
5. immediately refreshes JWKS once when an unknown `kid` is received.

This supports normal identity-service key rotation without redeploying the Promotion Service.

Cache lifetime:

```env
JWT_JWKS_CACHE_TTL_SECONDS=300
```

Minimum accepted value:

```text
30 seconds
```

---

# Static RSA Public Key Fallback

If a JWKS endpoint is unavailable, configure either:

```env
JWT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"
```

or:

```env
JWT_PUBLIC_KEY_PATH=/run/secrets/auth-public-key.pem
```

JWKS should generally be preferred because it supports key rotation.

Never configure the Identity Service **private key** in this service.

---

# Configuration

Configuration is provided through environment variables using `pydantic-settings`.

Local environment files are resolved in this order:

```text
APP_ENV_FILE
.env.<APP_ENV>
.env
app/.env.<APP_ENV>
app/.env
```

Production systems should inject configuration through the deployment platform or secret manager instead of committing `.env` files.

---

## Application Configuration

| Variable | Default | Description |
|---|---:|---|
| `APP_NAME` | `livetse-promotion-service` | Service name |
| `APP_ENV` | `development` | `development`, `test`, `staging`, `production` |
| `APP_VERSION` | `1.1.0` | Application version |
| `BASE_URL` | empty | Optional public service URL |
| `ENABLE_DOCS` | environment-dependent | Enable OpenAPI/Swagger docs |

Interactive docs are enabled by default outside production.

In production, they are disabled unless explicitly enabled.

When enabled:

```text
/docs
/redoc
/openapi.json
```

---

## PostgreSQL Configuration

| Variable | Default | Description |
|---|---:|---|
| `DATABASE_URL` | required | Async PostgreSQL connection URL |
| `DB_POOL_SIZE` | `10` | SQLAlchemy pool size |
| `DB_MAX_OVERFLOW` | `10` | Overflow connections |
| `DB_POOL_TIMEOUT` | `30` | Pool wait timeout |
| `DB_POOL_RECYCLE` | `1800` | Connection recycle interval |
| `AUTO_CREATE_SCHEMA` | `false` | Development-only schema creation |

Required URL format:

```text
postgresql+asyncpg://USER:PASSWORD@HOST:5432/DATABASE
```

Example:

```env
DATABASE_URL=postgresql+asyncpg://promotion_user:password@localhost:5432/promotion
```

Production refuses:

```env
AUTO_CREATE_SCHEMA=true
```

Use Alembic instead.

---

## JWT Configuration

| Variable | Default | Description |
|---|---:|---|
| `JWT_JWKS_URL` | empty | Preferred JWKS URL |
| `JWT_PUBLIC_KEY` | empty | Static PEM public key |
| `JWT_PUBLIC_KEY_PATH` | empty | Path to static PEM key |
| `JWT_ISSUER` | empty | Optional expected `iss` |
| `JWT_AUDIENCE` | empty | Optional expected `aud` |
| `JWT_REQUIRE_EXP` | `true` | Require token expiration |
| `JWT_LEEWAY_SECONDS` | `10` | Clock-skew tolerance |
| `JWT_JWKS_CACHE_TTL_SECONDS` | `300` | JWKS cache TTL |
| `JWT_JWKS_CONNECT_TIMEOUT` | `3` | JWKS connect timeout |
| `JWT_JWKS_READ_TIMEOUT` | `5` | JWKS read timeout |
| `ADMIN_ROLES` | `ADMIN,SUPER_ADMIN` | Admin-authorized JWT roles |

Production requires at least one verification-key source:

```text
JWT_JWKS_URL

or

JWT_PUBLIC_KEY

or

JWT_PUBLIC_KEY_PATH
```

---

## Upload Service Configuration

| Variable | Default |
|---|---:|
| `UPLOAD_SERVICE_URL` | required |
| `UPLOAD_SERVICE_API_KEY` | required |
| `UPLOAD_CONNECT_TIMEOUT` | `5` |
| `UPLOAD_READ_TIMEOUT` | `60` |
| `MAX_UPLOAD_SIZE_MB` | `10` |
| `ALLOWED_UPLOAD_CONTENT_TYPES` | JPEG, PNG, WebP, GIF |
| `BANNERS_UPLOAD_FOLDER` | `banners` |
| `ANNOUNCEMENTS_UPLOAD_FOLDER` | `announcements` |
| `ADS_UPLOAD_FOLDER` | `ads` |

Example:

```env
UPLOAD_SERVICE_URL=https://upload.example.com
UPLOAD_SERVICE_API_KEY=replace-with-a-long-secret

MAX_UPLOAD_SIZE_MB=10
ALLOWED_UPLOAD_CONTENT_TYPES=image/jpeg,image/png,image/webp,image/gif
```

Production requires the upload API key to contain at least 16 characters.

---

## HTTP / Security Configuration

| Variable | Default | Description |
|---|---|---|
| `TRUSTED_HOSTS` | `*` | Allowed HTTP host names |
| `CORS_ORIGINS` | empty | Browser CORS origins |
| `LOG_LEVEL` | `INFO` | Application log level |
| `LOG_JSON` | `true` | JSON structured logs |

Production does not allow:

```text
TRUSTED_HOSTS=*
```

or wildcard CORS origins.

Example:

```env
TRUSTED_HOSTS=promotion.example.com
CORS_ORIGINS=https://app.example.com,https://admin.example.com
```

---

# Database

The service uses PostgreSQL through SQLAlchemy's asynchronous engine.

Main tables:

```text
announcements
banners
ad_campaigns
ad_assets
ad_stats
```

Relationships:

```text
ad_campaigns
     |
     | 1:N
     v
ad_assets
     |
     | 1:N
     v
ad_stats
```

Deleting an ad campaign cascades its database assets.

Deleting an asset cascades its database statistics.

---

# Database Connection Pool

Each Uvicorn worker owns its own SQLAlchemy connection pool.

Approximate maximum number of PostgreSQL connections per service replica:

```text
WEB_CONCURRENCY × (DB_POOL_SIZE + DB_MAX_OVERFLOW)
```

For example:

```text
WEB_CONCURRENCY=2
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=10
```

Worst-case burst capacity:

```text
2 × (10 + 10) = 40 connections
```

Account for:

- number of replicas;
- PostgreSQL `max_connections`;
- other application services;
- administrative connections;
- monitoring;
- migration jobs.

---

# Database Migrations

Alembic is the authoritative production schema-management mechanism.

Current revisions:

```text
20260809_0001_initial_schema
20260809_0002_production_hardening
```

---

## Fresh Database

Run:

```bash
alembic upgrade head
```

---

## Existing Database Created by `create_all()`

Older versions of this service could create tables automatically through SQLAlchemy.

For those databases:

### 1. Take a backup

Create a database snapshot or verified backup before adoption.

### 2. Audit legacy data

Run:

```text
scripts/pre_migration_check.sql
```

All invalid-row counts should be zero before hardening constraints are applied.

### 3. Mark the old schema as baseline

```bash
alembic stamp 20260809_0001
```

### 4. Apply production hardening

```bash
alembic upgrade head
```

Do **not** blindly run:

```bash
alembic stamp head
```

on an old database.

Doing so would mark hardening migrations as executed without actually applying the database constraints.

---

# Migration Deployment Strategy

Migrations should run as a separate deployment job:

```text
Build image
    |
    v
Run Alembic migration job
    |
    v
Verify migration
    |
    v
Deploy / roll application replicas
```

Avoid allowing every application replica to run database migrations on startup.

---

# Upload Service

The shared upload integration lives in:

```text
app/services/upload_client.py
```

The service sends:

```http
POST /upload
X-API-Key: <secret>
Content-Type: multipart/form-data
```

Multipart fields:

```text
file
folder
```

A successful upstream response is expected to contain:

```json
{
  "data": {
    "url": "https://...",
    "name": "image.jpg",
    "folder": "banners",
    "size": 120000,
    "type": "image/jpeg"
  }
}
```

At minimum:

```text
data.url
```

must exist.

---

## Deleting Uploaded Files

The upload client supports:

```http
DELETE /folders/{folder}/files/{filename}
```

This is currently used by the Banners module for image lifecycle management.

---

## Upload Validation

Allowed MIME types are configured using:

```env
ALLOWED_UPLOAD_CONTENT_TYPES=image/jpeg,image/png,image/webp,image/gif
```

Maximum file size:

```env
MAX_UPLOAD_SIZE_MB=10
```

Invalid content type:

```http
415 Unsupported Media Type
```

Oversized file:

```http
413 Payload Too Large
```

Upload Service errors are sanitized before returning them to external callers.

Possible upstream-related responses:

```text
502 Upload service unavailable/rejected request
504 Upload service timeout
```

The Upload Service API key and upstream response details are never intentionally exposed in API errors.

---

# Running Locally

## Requirements

- Python 3.12+
- PostgreSQL
- reachable Upload Service
- Auth Service JWKS endpoint or RSA public key

---

## Create virtual environment

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

---

## Install dependencies

```bash
pip install -r requirements-dev.txt
```

---

## Create local environment

For example:

```text
.env.development
```

```env
APP_ENV=development

DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/promotion

JWT_JWKS_URL=http://localhost:8080/.well-known/jwks.json
ADMIN_ROLES=ADMIN,SUPER_ADMIN

UPLOAD_SERVICE_URL=http://localhost:9000
UPLOAD_SERVICE_API_KEY=local-development-api-key

AUTO_CREATE_SCHEMA=false

TRUSTED_HOSTS=localhost,127.0.0.1
CORS_ORIGINS=http://localhost:3000

ENABLE_DOCS=true
LOG_JSON=false
```

---

## Run migrations

```bash
alembic upgrade head
```

---

## Start development server

Using Make:

```bash
make run
```

or directly:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Swagger:

```text
http://localhost:8000/docs
```

---

# Running Tests

Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

Run:

```bash
make test
```

This executes:

```text
python compile checks
pytest
```

Directly:

```bash
python -m compileall -q app main.py alembic
pytest -q
```

Test areas include:

- application route contract;
- JWT authentication;
- RS256 algorithm enforcement;
- JWKS key selection;
- admin authorization;
- schema validation;
- upload validation.

---

# Docker

## Build

```bash
docker build -t livetse-promotion-service:1.1.0 .
```

The runtime container uses:

```text
python:3.12-slim
```

and runs the application as an unprivileged operating-system user.

---

## Run migrations

Use the same image that will be deployed:

```bash
docker run --rm \
  --env-file .env.production \
  livetse-promotion-service:1.1.0 \
  alembic upgrade head
```

---

## Run application

```bash
docker run --rm \
  -p 8000:8000 \
  --env-file .env.production \
  -e WEB_CONCURRENCY=2 \
  livetse-promotion-service:1.1.0
```

Runtime command:

```text
uvicorn main:app
```

with configurable:

```text
PORT
WEB_CONCURRENCY
FORWARDED_ALLOW_IPS
```

---

# Reverse Proxy

The service is expected to run behind a trusted ingress/reverse proxy in production.

TLS should normally terminate at the ingress.

Example topology:

```text
Internet
   |
   v
HTTPS Load Balancer / Ingress
   |
   v
Promotion Service container
```

`FORWARDED_ALLOW_IPS` should only contain trusted proxy addresses/networks.

Avoid:

```env
FORWARDED_ALLOW_IPS=*
```

when the application can receive traffic directly from untrusted networks.

---

# Health Checks

## Liveness

```http
GET /health/live
```

Example:

```json
{
  "status": "ok",
  "service": "livetse-promotion-service",
  "version": "1.1.0"
}
```

Liveness indicates that the application process is responding.

---

## Readiness

```http
GET /health/ready
```

The current readiness check verifies PostgreSQL connectivity by running:

```sql
SELECT 1
```

Healthy response:

```json
{
  "status": "ready"
}
```

Database unavailable:

```http
503 Service Unavailable
```

Current readiness does not actively probe the Auth JWKS endpoint or Upload Service.

---

# Logging and Request IDs

The service provides request-level access logging through:

```text
RequestContextMiddleware
```

A request can provide:

```http
X-Request-ID: my-request-id
```

If no request ID is provided, the service generates a UUID.

The same request ID is returned:

```http
X-Request-ID: my-request-id
```

Example structured log:

```json
{
  "timestamp": "2026-08-09T12:00:00+00:00",
  "level": "INFO",
  "logger": "app.access",
  "message": "request completed",
  "request_id": "e1170b0c-6e14-4f25-b9ad-6883479ac108",
  "method": "GET",
  "path": "/banners/",
  "status_code": 200,
  "duration_ms": 12.41
}
```

Production logs are intended to be collected from stdout by the container platform.

---

# Security Response Headers

Every application response receives:

```text
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: no-referrer
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

---

# GZip

Responses larger than approximately:

```text
1024 bytes
```

are eligible for GZip compression.

---

# CORS

CORS is only enabled when at least one origin is configured.

Example:

```env
CORS_ORIGINS=https://app.example.com,https://admin.example.com
```

Allowed methods:

```text
GET
POST
PUT
DELETE
OPTIONS
```

Allowed headers include:

```text
Authorization
Content-Type
X-Request-ID
```

---

# API Overview

## Health

```text
GET /health/live
GET /health/ready
```

---

## Announcements

Public/user:

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

## Banners

Public:

```text
GET /banners/
```

Admin:

```text
GET    /banners/admin
GET    /banners/admin/{banner_id}
POST   /banners/admin
POST   /banners/admin/upload
PUT    /banners/admin/{banner_id}
PUT    /banners/admin/{banner_id}/upload
DELETE /banners/admin/{banner_id}
```

---

## Ads

Public:

```text
GET /ads/
```

Campaign admin:

```text
GET    /ads/admin
GET    /ads/admin/{campaign_id}
POST   /ads/admin
PUT    /ads/admin/{campaign_id}
DELETE /ads/admin/{campaign_id}
```

Asset admin:

```text
GET    /ads/admin/{campaign_id}/assets
GET    /ads/admin/assets/{asset_id}
POST   /ads/admin/{campaign_id}/assets
POST   /ads/admin/{campaign_id}/assets/upload
DELETE /ads/admin/assets/{asset_id}
```

Stats admin:

```text
POST /ads/admin/stats

GET /ads/admin/assets/{asset_id}/stats
GET /ads/admin/{campaign_id}/stats
```

See individual module README files for request and response details.

---

# Common HTTP Status Codes

| Code | Meaning |
|---:|---|
| `200` | Successful request |
| `201` | Resource created |
| `401` | Authentication missing, invalid, or expired |
| `403` | Authenticated user lacks required role |
| `404` | Requested entity not found |
| `413` | Uploaded file too large |
| `415` | Unsupported upload content type |
| `422` | Request validation failed |
| `500` | Unexpected server error |
| `502` | Upload Service unavailable/rejected request |
| `503` | Service dependency not ready |
| `504` | Upload Service timeout |

---

# Startup and Shutdown

During application startup:

```text
1. Verify PostgreSQL connectivity
2. Optionally create schema in development
3. Start shared Upload Service HTTP client
4. Start JWKS HTTP client
5. Begin serving traffic
```

On shutdown:

```text
1. Close JWKS HTTP client
2. Close Upload Service HTTP client
3. Dispose SQLAlchemy engine
```

This prevents leaking HTTP/database connections during graceful container shutdown.

---

# Security

## JWT

The application:

- accepts only `RS256`;
- does not trust JWT claims before signature verification;
- resolves JWKS keys using `kid`;
- verifies expiration by default;
- supports issuer/audience verification;
- never requires an RSA private key.

---

## Secrets

Never commit:

```text
DATABASE password
UPLOAD_SERVICE_API_KEY
private RSA keys
real production .env files
```

Use:

- Kubernetes Secrets;
- Docker secrets;
- Vault;
- cloud secret managers;
- protected deployment variables.

---

## Database

Production should use a dedicated PostgreSQL user with only permissions required by this service.

Migration permissions may be granted through a separate deployment identity if desired.

---

## Network

Recommended production controls:

```text
Internet
   |
   v
WAF / Load Balancer
   |
   v
Ingress
   |
   v
Promotion Service
   |
   +--> PostgreSQL on private network
   |
   +--> Upload Service on trusted network
   |
   +--> Auth/JWKS over trusted HTTPS
```

Admin endpoints should additionally be protected by normal infrastructure-level security controls where appropriate.

---

# Deployment

Recommended deployment sequence:

```text
1. Build immutable Docker image
2. Run unit/contract tests
3. Backup database when required
4. Run pre-migration audit for legacy DB
5. Run Alembic migration job
6. Deploy application replicas
7. Verify /health/live
8. Verify /health/ready
9. Verify JWKS authentication
10. Verify Upload Service connectivity
11. Monitor logs/errors
```

---

# Production Checklist

## Environment

- [ ] `APP_ENV=production`
- [ ] production `.env` is not committed
- [ ] secrets are stored in a secret manager
- [ ] `ENABLE_DOCS=false` unless explicitly required

## Database

- [ ] `DATABASE_URL` uses `postgresql+asyncpg://`
- [ ] database credentials are production-only
- [ ] `AUTO_CREATE_SCHEMA=false`
- [ ] backup/snapshot completed when required
- [ ] Alembic migrations applied successfully
- [ ] DB pool sized against PostgreSQL capacity

## Authentication

- [ ] `JWT_JWKS_URL` configured where possible
- [ ] JWKS endpoint uses HTTPS
- [ ] static public key fallback verified if used
- [ ] `JWT_ISSUER` configured if issuer contract exists
- [ ] `JWT_AUDIENCE` configured if audience contract exists
- [ ] `JWT_REQUIRE_EXP=true`
- [ ] `ADMIN_ROLES` matches Auth Service roles
- [ ] no private signing key exists in this service

## Uploads

- [ ] Upload Service reachable
- [ ] `UPLOAD_SERVICE_API_KEY` rotated from development
- [ ] file size limit reviewed
- [ ] MIME allow-list reviewed
- [ ] module upload folders configured

## HTTP

- [ ] `TRUSTED_HOSTS` contains real production hosts
- [ ] no wildcard trusted hosts
- [ ] `CORS_ORIGINS` contains approved origins only
- [ ] no production wildcard CORS
- [ ] TLS enabled at ingress
- [ ] trusted proxy addresses configured

## Monitoring

- [ ] stdout logs collected
- [ ] JSON log parsing configured
- [ ] `X-Request-ID` propagated through gateway
- [ ] `/health/live` monitored
- [ ] `/health/ready` monitored
- [ ] 5xx rate monitored
- [ ] PostgreSQL pool utilization monitored
- [ ] JWKS/Auth failures monitored
- [ ] Upload Service failures monitored

---

# Current Implementation Notes

These notes describe the current codebase and are important when extending the service.

## Redis and Events

The following files currently exist as placeholders:

```text
app/core/redis.py
app/events/publisher.py
app/events/consumer.py
```

No Redis or event-bus behavior is currently wired into the application runtime.

`REDIS_URL` therefore has no active runtime effect at this time.

---

## API Aggregator

```text
app/api/router.py
```

currently contains no router composition logic.

Business routers are registered directly in:

```text
main.py
```

---

## Readiness Scope

`/health/ready` currently checks PostgreSQL only.

It does not proactively check:

```text
JWKS/Auth Service
Upload Service
```

These external integrations fail when they are actually used.

---

## Announcement Subscription Types

Announcements contain:

```text
subscription_types
```

but the current PRIVATE-announcement targeting predicate does **not** evaluate this field against JWT claims.

Current private targeting uses:

```text
dataTier
liveTreadAccess
userDataGroup
device
```

---

## Announcement Upload Metadata

The Announcement database model stores only:

```text
image_url
```

It does not currently persist:

```text
image_name
image_folder
image_size
image_type
```

Therefore successful announcement deletion or image replacement cannot automatically remove the previously referenced uploaded object.

---

## Ads Upload Metadata

Ad assets also currently store only:

```text
image_url
```

and not the remote upload object's folder/name metadata.

Deleting an ad asset removes the database resource but does not currently remove its uploaded file from the Upload Service.

---

# Development Guidelines

When adding a new module, follow the existing structure:

```text
app/modules/example/
├── __init__.py
├── model.py
├── schema.py
├── repo.py
├── service.py
├── router.py
├── admin.py
└── README.md
```

Recommended responsibilities:

```text
model.py
    SQLAlchemy persistence model only

schema.py
    Request/response validation contracts

repo.py
    Database queries only

service.py
    Business rules and external-service orchestration

router.py
    Public/user HTTP API

admin.py
    Administrator HTTP API
```

Do not place authentication logic independently inside each business module.

Reuse:

```python
get_current_user
require_current_user
require_admin
```

from the shared/core authentication layer.

---

# License

Internal Livetse service.

Add the organization's final licensing and ownership policy here if the repository is distributed beyond the internal engineering environment.