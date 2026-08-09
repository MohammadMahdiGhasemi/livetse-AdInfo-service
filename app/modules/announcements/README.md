# Announcements Module

The Announcements module manages scheduled public and targeted communications for Livetse clients.

It supports:

- public announcements;
- authenticated private announcements;
- JWT-based user targeting;
- multiple UI sections;
- announcement history;
- scheduling;
- admin filtering;
- CRUD operations;
- optional image upload.

Module path:

```text
app/modules/announcements/
```

---

# Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Announcement Visibility](#announcement-visibility)
- [Sections](#sections)
- [JWT Targeting](#jwt-targeting)
- [Targeting Rules](#targeting-rules)
- [Database Model](#database-model)
- [Indexes](#indexes)
- [Public API](#public-api)
- [Admin API](#admin-api)
- [Creating Announcements](#creating-announcements)
- [Uploading Images](#uploading-images)
- [Validation](#validation)
- [Error Responses](#error-responses)
- [Current Implementation Notes](#current-implementation-notes)
- [Files](#files)

---

# Overview

An announcement represents a time-bounded message that can appear in one or more product sections.

Example:

```json
{
  "text": "A new version is now available.",
  "button_text": "Update",
  "link": "https://example.com/download",
  "sections": ["DASHBOARD", "LANDING"],
  "visibility": "PUBLIC",
  "display_start_at": "2026-08-09T10:00:00Z",
  "display_expire_at": "2026-08-15T10:00:00Z",
  "is_active": true
}
```

Announcements can be:

```text
PUBLIC
PRIVATE
```

---

# Architecture

```text
HTTP Request
     |
     v
router.py / admin.py
     |
     v
AnnouncementService
     |
     +-----------------------+
     |                       |
     v                       v
AnnouncementRepository   UploadServiceClient
     |
     v
PostgreSQL
```

Responsibilities:

```text
router.py
    Public/user-facing endpoints

admin.py
    Administrator endpoints

service.py
    Business logic and upload orchestration

repo.py
    PostgreSQL query logic and targeting predicates

schema.py
    Request/response validation

model.py
    SQLAlchemy Announcement table
```

---

# Announcement Visibility

## PUBLIC

Public announcements do not require authentication.

They can be retrieved through:

```text
GET /announcements/latest
GET /announcements/history
```

when public visibility is requested.

---

## PRIVATE

Private announcements require a valid Bearer JWT.

The service verifies the JWT and evaluates user claims against the announcement's targeting fields.

Example request:

```http
GET /announcements/history?section=DASHBOARD&visibility=PRIVATE
Authorization: Bearer <JWT>
```

---

# Sections

Supported sections:

```text
LANDING
DASHBOARD
EXTENSION
MOBILE
```

An announcement must belong to at least one section.

Example:

```json
{
  "sections": [
    "LANDING",
    "DASHBOARD"
  ]
}
```

Section membership is stored as a PostgreSQL array.

---

# JWT Targeting

The module does not decode or trust JWT data itself.

Authentication is provided by:

```text
app/shared/auth.py
```

Only verified claims are provided to the Announcement module.

A typical verified user can contain:

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

The targeting logic currently uses:

```text
dataTier
liveTreadAccess
userDataGroup
device
```

The following JWT claims are not used for private-announcement matching:

```text
id
phoneNumber
role
iat
exp
```

They may still be used by authentication or other application logic.

---

# Data Tier

Supported canonical tier values are:

```text
STANDARD
SILVER
GOLD
```

Incoming targeting values are normalized to uppercase.

Examples:

```text
gold     -> GOLD
Gold     -> GOLD
 GOLD    -> GOLD
```

Unsupported values are rejected during schema validation.

Example invalid value:

```text
PLATINUM
```

Result:

```http
422 Unprocessable Entity
```

---

# Targeting Rules

Private announcements contain four active targeting dimensions.

| Announcement field | JWT claim | Unrestricted value |
|---|---|---|
| `target_data_tiers` | `dataTier` | `[]` |
| `target_live_tread_access` | `liveTreadAccess` | `null` |
| `target_user_data_groups` | `userDataGroup` | `[]` |
| `target_devices` | `device` | `[]` |

All configured dimensions are combined using logical `AND`.

Conceptually:

```text
tier matches
AND
liveTreadAccess matches
AND
userDataGroup matches
AND
device matches
```

---

## Example 1 — Gold users

```json
{
  "visibility": "PRIVATE",
  "target_data_tiers": ["GOLD"],
  "target_live_tread_access": null,
  "target_user_data_groups": [],
  "target_devices": []
}
```

Matches:

```json
{
  "dataTier": "GOLD"
}
```

Does not match:

```json
{
  "dataTier": "SILVER"
}
```

---

## Example 2 — Gold desktop users

```json
{
  "visibility": "PRIVATE",
  "target_data_tiers": ["GOLD"],
  "target_live_tread_access": null,
  "target_user_data_groups": [],
  "target_devices": ["DESKTOP"]
}
```

Requires:

```text
dataTier == GOLD
AND
device == DESKTOP
```

---

## Example 3 — Live-trading users only

```json
{
  "visibility": "PRIVATE",
  "target_data_tiers": [],
  "target_live_tread_access": true,
  "target_user_data_groups": [],
  "target_devices": []
}
```

Only users whose verified JWT contains:

```json
{
  "liveTreadAccess": true
}
```

will match.

---

## Example 4 — Unrestricted Private Announcement

```json
{
  "visibility": "PRIVATE",
  "target_data_tiers": [],
  "target_live_tread_access": null,
  "target_user_data_groups": [],
  "target_devices": []
}
```

Any authenticated user can match.

---

# Subscription Types

The model also contains:

```text
subscription_types
```

Example:

```json
{
  "subscription_types": [
    "MONTHLY",
    "ANNUAL"
  ]
}
```

This field can currently be stored and used by the admin list filter.

However, **the current private-delivery targeting predicate does not compare `subscription_types` against a JWT claim**.

Therefore it should not currently be treated as an active user-delivery restriction.

---

# Database Model

Table:

```text
announcements
```

| Column | Type | Required | Description |
|---|---|---:|---|
| `id` | UUID | yes | Primary key |
| `text` | TEXT | yes | Announcement message |
| `link` | TEXT | no | Optional destination URL |
| `button_text` | VARCHAR(100) | no | CTA text |
| `image_url` | TEXT | no | Optional image URL |
| `sections` | TEXT[] | yes | Target UI sections |
| `visibility` | ENUM | yes | `PUBLIC` or `PRIVATE` |
| `subscription_types` | TEXT[] | yes | Subscription metadata/filter |
| `target_data_tiers` | TEXT[] | yes | Allowed data tiers |
| `target_live_tread_access` | BOOLEAN | no | `true`, `false`, or `null` |
| `target_user_data_groups` | TEXT[] | yes | Allowed user data groups |
| `target_devices` | TEXT[] | yes | Allowed devices |
| `display_start_at` | TIMESTAMPTZ | yes | Start time |
| `display_expire_at` | TIMESTAMPTZ | yes | Expiration time |
| `is_active` | BOOLEAN | yes | Master activation switch |
| `created_at` | TIMESTAMPTZ | yes | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | yes | Update timestamp |

Database constraint:

```text
display_expire_at > display_start_at
```

---

# Indexes

Scalar indexes:

```text
ix_announcements_visibility
ix_announcements_is_active
ix_announcements_display_start_at
ix_announcements_display_expire_at
ix_announcements_created_at
ix_announcements_target_live_tread_access
```

Composite index:

```text
ix_announcements_active_visibility_start
```

Columns:

```text
is_active
visibility
display_start_at
```

GIN indexes:

```text
ix_announcements_sections_gin
ix_announcements_subscription_types_gin
ix_announcements_target_data_tiers_gin
ix_announcements_target_user_data_groups_gin
ix_announcements_target_devices_gin
```

These support PostgreSQL array membership queries used by delivery and admin filtering.

---

# Public API

## Get Latest Public Announcements

```http
GET /announcements/latest
```

Query parameters:

| Name | Type | Required | Default |
|---|---|---:|---:|
| `section` | enum | yes | — |
| `limit` | integer | no | `5` |

`limit` range:

```text
1..50
```

Example:

```http
GET /announcements/latest?section=DASHBOARD&limit=5
```

No authentication required.

The query returns announcements satisfying:

```text
is_active = true
visibility = PUBLIC
section matches
display_start_at <= now
display_expire_at >= now
```

Ordering:

```text
display_start_at DESC
created_at DESC
```

Example response:

```json
[
  {
    "id": "80c34e1a-2ca1-4678-a363-fd44ef8fcdf6",
    "text": "New dashboard features are available.",
    "link": "https://example.com/features",
    "button_text": "View",
    "image_url": "https://cdn.example.com/announcement.jpg",
    "sections": ["DASHBOARD"],
    "visibility": "PUBLIC",
    "subscription_types": [],
    "display_start_at": "2026-08-09T08:00:00Z",
    "display_expire_at": "2026-08-12T08:00:00Z",
    "created_at": "2026-08-09T07:00:00Z",
    "updated_at": "2026-08-09T07:00:00Z"
  }
]
```

Targeting configuration and `is_active` are intentionally not exposed through the public response model.

---

# Announcement History

```http
GET /announcements/history
```

Parameters:

| Name | Type | Required | Default |
|---|---|---:|---|
| `section` | enum | yes | — |
| `visibility` | enum | no | `PUBLIC` |
| `page` | integer | no | `1` |
| `limit` | integer | no | `20` |

`limit` range:

```text
1..100
```

---

## Public History

```http
GET /announcements/history?section=DASHBOARD
```

Equivalent to:

```http
GET /announcements/history?section=DASHBOARD&visibility=PUBLIC
```

Authentication is not required.

Public history contains:

```text
active announcements
PUBLIC visibility
matching section
display_start_at <= now
```

Expired announcements are intentionally included in history.

Future announcements are excluded.

---

## Private History

```http
GET /announcements/history?section=DASHBOARD&visibility=PRIVATE
Authorization: Bearer <JWT>
```

Authentication is required.

The query includes:

```text
is_active = true
visibility = PRIVATE
section matches
display_start_at <= now
JWT targeting matches
```

Like public history, expired announcements may remain visible in history.

Future announcements are excluded.

---

## Pagination Response

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "size": 20,
  "pages": 0
}
```

---

# Optional Authentication Behavior

The history endpoint uses optional Bearer authentication.

Behavior:

```text
No Authorization header
    + PUBLIC
    -> allowed

No Authorization header
    + PRIVATE
    -> 401

Valid Authorization header
    -> verified CurrentUser

Invalid/expired Authorization header
    -> 401
```

Even for a public-history request, if the caller explicitly sends an invalid Bearer token, authentication validation will fail with `401`.

---

# Admin API

All admin endpoints require:

```http
Authorization: Bearer <RS256 JWT>
```

The verified role must be included in:

```env
ADMIN_ROLES=ADMIN,SUPER_ADMIN
```

---

## List Announcements

```http
GET /announcements/admin
```

Supported filters:

| Name | Type |
|---|---|
| `section` | `LANDING`, `DASHBOARD`, `EXTENSION`, `MOBILE` |
| `visibility` | `PUBLIC`, `PRIVATE` |
| `is_active` | boolean |
| `subscription_type` | string |
| `data_tier` | string |
| `live_tread_access` | boolean |
| `user_data_group` | string |
| `device` | string |
| `display_start_at` | ISO-8601 datetime |
| `display_expire_at` | ISO-8601 datetime |
| `page` | integer |
| `size` | integer |

Example:

```http
GET /announcements/admin?visibility=PRIVATE&data_tier=GOLD&device=DESKTOP&page=1&size=20
```

Pagination:

```text
page >= 1
1 <= size <= 100
```

Date filter semantics:

```text
display_start_at >= supplied display_start_at

display_expire_at <= supplied display_expire_at
```

### Current response behavior

The list endpoint currently uses:

```text
PaginatedAnnouncementResponse
```

whose item model is the public `AnnouncementResponse`.

Therefore list items currently do **not** expose:

```text
target_data_tiers
target_live_tread_access
target_user_data_groups
target_devices
is_active
```

Use the admin get-by-ID endpoint when the full targeting configuration is required.

---

# Get Announcement by ID

```http
GET /announcements/admin/{announcement_id}
```

Example:

```bash
curl \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  http://localhost:8000/announcements/admin/80c34e1a-2ca1-4678-a363-fd44ef8fcdf6
```

This endpoint returns the full admin response, including targeting fields and `is_active`.

Not found:

```http
404 Not Found
```

```json
{
  "detail": "Announcement not found"
}
```

---

# Creating Announcements

## Create with JSON

```http
POST /announcements/admin
Content-Type: application/json
Authorization: Bearer <JWT>
```

### Public example

```json
{
  "text": "Scheduled maintenance tonight.",
  "link": "https://status.example.com",
  "button_text": "Status",
  "image_url": null,
  "sections": [
    "DASHBOARD",
    "MOBILE"
  ],
  "visibility": "PUBLIC",
  "subscription_types": [],
  "target_data_tiers": [],
  "target_live_tread_access": null,
  "target_user_data_groups": [],
  "target_devices": [],
  "display_start_at": "2026-08-09T18:00:00Z",
  "display_expire_at": "2026-08-10T04:00:00Z",
  "is_active": true
}
```

---

## Private example

```json
{
  "text": "Exclusive feature available for GOLD desktop users.",
  "sections": [
    "DASHBOARD"
  ],
  "visibility": "PRIVATE",
  "subscription_types": [],
  "target_data_tiers": [
    "GOLD"
  ],
  "target_live_tread_access": null,
  "target_user_data_groups": [],
  "target_devices": [
    "DESKTOP"
  ],
  "display_start_at": "2026-08-09T18:00:00Z",
  "display_expire_at": "2026-08-15T18:00:00Z",
  "is_active": true
}
```

---

# Create with Image Upload

```http
POST /announcements/admin/upload
Content-Type: multipart/form-data
Authorization: Bearer <JWT>
```

Fields:

| Field | Required | Format |
|---|---:|---|
| `file` | yes | image |
| `text` | yes | string |
| `sections` | yes | comma-separated |
| `visibility` | yes | `PUBLIC` / `PRIVATE` |
| `display_start_at` | yes | ISO-8601 |
| `display_expire_at` | yes | ISO-8601 |
| `link` | no | string |
| `button_text` | no | string |
| `image_url` | no | fallback URL |
| `subscription_types` | no | comma-separated |
| `target_data_tiers` | no | comma-separated |
| `target_live_tread_access` | no | boolean-like string |
| `target_user_data_groups` | no | comma-separated |
| `target_devices` | no | comma-separated |
| `is_active` | no | boolean |

Example:

```bash
curl -X POST \
  http://localhost:8000/announcements/admin/upload \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@announcement.jpg" \
  -F "text=Gold users announcement" \
  -F "sections=DASHBOARD,MOBILE" \
  -F "visibility=PRIVATE" \
  -F "target_data_tiers=GOLD" \
  -F "target_devices=DESKTOP" \
  -F "display_start_at=2026-08-09T18:00:00+00:00" \
  -F "display_expire_at=2026-08-15T18:00:00+00:00" \
  -F "is_active=true"
```

Uploaded files use:

```env
ANNOUNCEMENTS_UPLOAD_FOLDER=announcements
```

---

# Update Announcement

JSON:

```http
PUT /announcements/admin/{announcement_id}
```

All fields are optional.

Example:

```json
{
  "text": "Updated announcement text",
  "target_data_tiers": [
    "GOLD",
    "SILVER"
  ],
  "is_active": true
}
```

The service validates the **final** date range after combining existing and supplied values.

This means updating only `display_start_at` cannot create an invalid range relative to the existing `display_expire_at`.

---

# Update with Image Upload

```http
PUT /announcements/admin/{announcement_id}/upload
Content-Type: multipart/form-data
```

A new file is required.

Other fields are optional.

Example:

```bash
curl -X PUT \
  http://localhost:8000/announcements/admin/80c34e1a-2ca1-4678-a363-fd44ef8fcdf6/upload \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@replacement.jpg" \
  -F "text=Updated text"
```

If the database write fails after a successful upload, the module performs best-effort cleanup of the newly uploaded object when the Upload Service returns `name` and `folder`.

---

# Delete Announcement

```http
DELETE /announcements/admin/{announcement_id}
```

Successful response:

```json
{
  "message": "Announcement deleted",
  "id": "80c34e1a-2ca1-4678-a363-fd44ef8fcdf6"
}
```

---

# Validation

## Text

Required on creation:

```text
min length = 1
```

---

## Button Text

Maximum:

```text
100 characters
```

---

## Sections

At least one section is required.

Invalid:

```json
{
  "sections": []
}
```

---

## Time Window

Required invariant:

```text
display_expire_at > display_start_at
```

Invalid ranges return:

```http
422 Unprocessable Entity
```

The database also enforces the same invariant using:

```text
ck_announcement_time_range
```

---

## Data Tiers

Allowed:

```text
STANDARD
SILVER
GOLD
```

Duplicates are normalized/deduplicated.

Example input:

```json
{
  "target_data_tiers": [
    "gold",
    "GOLD",
    "silver"
  ]
}
```

Normalized representation:

```json
[
  "GOLD",
  "SILVER"
]
```

---

# Upload Validation

Global Upload Service validation applies.

Default content types:

```text
image/jpeg
image/png
image/webp
image/gif
```

Default size limit:

```text
10 MB
```

Configured using:

```env
MAX_UPLOAD_SIZE_MB
ALLOWED_UPLOAD_CONTENT_TYPES
```

---

# Error Responses

| HTTP | Meaning |
|---:|---|
| `401` | Missing/invalid/expired authentication |
| `403` | Authenticated user is not an admin |
| `404` | Announcement does not exist |
| `413` | Uploaded image too large |
| `415` | Unsupported image MIME type |
| `422` | Invalid schema, enum, tier, section, or date range |
| `502` | Upload Service failure |
| `504` | Upload Service timeout |

---

# Current Implementation Notes

## No private latest endpoint

The current public `latest` endpoint returns only:

```text
PUBLIC
```

announcements.

Private announcements are retrieved through:

```text
GET /announcements/history?visibility=PRIVATE
```

---

## History includes expired announcements

Both public and private history require:

```text
display_start_at <= now
```

but intentionally do not require:

```text
display_expire_at >= now
```

Therefore expired announcements can remain in history.

---

## Role does not control targeting

The JWT:

```text
role
```

is used for authorization elsewhere, including admin access.

It is not currently part of private-announcement targeting.

---

## Subscription types do not control delivery

`subscription_types` is persisted and searchable by admins but is not currently included in the private delivery predicate.

---

## Uploaded image metadata is not persisted

The Announcement model stores:

```text
image_url
```

but not:

```text
image_name
image_folder
image_size
image_type
```

Consequences:

- newly uploaded files can be cleaned up when the subsequent DB create/update fails, because the upload response is still available in memory;
- after a successful DB write, the module cannot later determine the remote filename/folder from the database;
- deleting an announcement does not delete its remote image;
- replacing an existing announcement image does not automatically delete the previous remote image.

If full upload lifecycle management is required, add upload metadata columns similar to the Banners module.

---

# Environment Variables

Module-specific:

```env
ANNOUNCEMENTS_UPLOAD_FOLDER=announcements
```

Authentication-related:

```env
JWT_JWKS_URL=https://auth.example.com/.well-known/jwks.json
ADMIN_ROLES=ADMIN,SUPER_ADMIN
```

Upload-related:

```env
UPLOAD_SERVICE_URL=https://upload.example.com
UPLOAD_SERVICE_API_KEY=...
MAX_UPLOAD_SIZE_MB=10
ALLOWED_UPLOAD_CONTENT_TYPES=image/jpeg,image/png,image/webp,image/gif
```

---

# Files

```text
app/modules/announcements/
├── __init__.py
├── admin.py
├── model.py
├── repo.py
├── router.py
├── schema.py
├── service.py
└── README.md
```

Related shared files:

```text
app/shared/auth.py
app/shared/enums.py
app/core/security.py
app/core/jwks.py
app/services/upload_client.py
```