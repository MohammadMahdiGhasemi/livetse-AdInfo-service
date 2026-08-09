# Banners Module

The Banners module manages scheduled promotional banners for Livetse clients.

It provides:

- platform-specific banner delivery;
- active-time-window filtering;
- ordering through `sort_order`;
- administrative CRUD operations;
- external image upload;
- persisted upload metadata;
- safe image replacement;
- best-effort remote file cleanup.

Module path:

```text
app/modules/banners/
```

---

# Overview

A banner is a promotional image associated with:

```text
title
image
destination URL
platform
display window
sort order
active state
```

Example:

```json
{
  "title": "Summer Campaign",
  "image_url": "https://cdn.example.com/banner.jpg",
  "alt_text": "Summer campaign",
  "link_url": "https://example.com/summer",
  "platform": "landing",
  "start_at": "2026-08-09T00:00:00Z",
  "expire_at": "2026-09-01T00:00:00Z",
  "sort_order": 0,
  "is_active": true
}
```

---

# Architecture

```text
Client
   |
   v
router.py / admin.py
   |
   v
BannerService
   |
   +-------------------+
   |                   |
   v                   v
BannerRepository   UploadServiceClient
   |                   |
   v                   v
PostgreSQL         Upload Service
```

---

# Platforms

Supported values:

```text
landing
extension
```

Defined by:

```python
BannerPlatform
```

Invalid platform values return:

```http
422 Unprocessable Entity
```

---

# Database Model

Table:

```text
banners
```

| Column | Type | Required | Description |
|---|---|---:|---|
| `id` | UUID | yes | Primary key |
| `title` | VARCHAR(255) | yes | Banner title |
| `image_url` | TEXT | yes | Public image URL |
| `image_name` | VARCHAR(255) | no | Remote upload filename |
| `image_folder` | VARCHAR(100) | no | Remote upload folder |
| `image_size` | INTEGER | no | File size |
| `image_type` | VARCHAR(100) | no | MIME type |
| `alt_text` | VARCHAR(255) | no | Accessibility text |
| `link_url` | TEXT | yes | Destination URL |
| `platform` | VARCHAR(50) | yes | Banner platform |
| `start_at` | TIMESTAMPTZ | yes | Start time |
| `expire_at` | TIMESTAMPTZ | yes | Expiration time |
| `is_active` | BOOLEAN | yes | Activation flag |
| `sort_order` | INTEGER | yes | Display ordering |
| `created_at` | TIMESTAMPTZ | yes | Creation time |
| `updated_at` | TIMESTAMPTZ | yes | Modification time |

Constraints:

```text
expire_at > start_at
sort_order >= 0
```

Index:

```text
idx_banner_active_time
```

on:

```text
is_active
start_at
expire_at
```

---

# Public API

## Get Active Banners

```http
GET /banners/?platform={platform}
```

Authentication is not required.

Example:

```http
GET /banners/?platform=landing
```

The service returns banners satisfying:

```text
is_active = true
platform = requested platform
start_at <= now
expire_at >= now
```

Ordering:

```text
sort_order ASC
```

Example response:

```json
[
  {
    "title": "Summer Campaign",
    "image_url": "https://cdn.example.com/banner.jpg",
    "alt_text": "Summer campaign",
    "link_url": "https://example.com/summer",
    "platform": "landing",
    "start_at": "2026-08-09T00:00:00Z",
    "expire_at": "2026-09-01T00:00:00Z",
    "sort_order": 0,
    "is_active": true,
    "id": "4289bd99-f900-4442-8fb1-2abb0cef104e",
    "created_at": "2026-08-08T14:00:00Z",
    "updated_at": "2026-08-08T14:00:00Z"
  }
]
```

---

# Admin Authentication

Every admin endpoint requires:

```http
Authorization: Bearer <RS256 JWT>
```

The token must be valid and its normalized `role` must exist in:

```env
ADMIN_ROLES=ADMIN,SUPER_ADMIN
```

Valid JWT with a non-admin role:

```http
403 Forbidden
```

---

# List Banners

```http
GET /banners/admin
```

Parameters:

| Name | Default | Range |
|---|---:|---|
| `page` | `1` | `>= 1` |
| `size` | `20` | `1..100` |

Example:

```http
GET /banners/admin?page=1&size=20
```

Response:

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "size": 20,
  "pages": 0
}
```

Items are ordered by:

```text
sort_order ASC
```

---

# Get Banner

```http
GET /banners/admin/{banner_id}
```

Not found:

```http
404 Not Found
```

```json
{
  "detail": "Banner not found"
}
```

---

# Create Banner with JSON

```http
POST /banners/admin
Content-Type: application/json
Authorization: Bearer <JWT>
```

Example:

```json
{
  "title": "Summer Campaign",
  "image_url": "https://cdn.example.com/banner.jpg",
  "alt_text": "Summer campaign",
  "link_url": "https://example.com/summer",
  "platform": "landing",
  "start_at": "2026-08-09T00:00:00Z",
  "expire_at": "2026-09-01T00:00:00Z",
  "sort_order": 0,
  "is_active": true
}
```

Response:

```http
201 Created
```

`image_url` should normally be supplied when using the JSON route.

The schema technically permits an empty `image_url` because the same model is reused by the upload flow before the final upload URL is known.

---

# Create Banner with Image Upload

```http
POST /banners/admin/upload
Content-Type: multipart/form-data
```

Fields:

| Field | Required |
|---|---:|
| `file` | yes |
| `title` | yes |
| `alt_text` | no |
| `link_url` | yes |
| `platform` | yes |
| `start_at` | yes |
| `expire_at` | yes |
| `sort_order` | no |
| `is_active` | no |

Example:

```bash
curl -X POST \
  http://localhost:8000/banners/admin/upload \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@banner.jpg" \
  -F "title=Summer Campaign" \
  -F "alt_text=Summer campaign banner" \
  -F "link_url=https://example.com/summer" \
  -F "platform=landing" \
  -F "start_at=2026-08-09T00:00:00+00:00" \
  -F "expire_at=2026-09-01T00:00:00+00:00" \
  -F "sort_order=0" \
  -F "is_active=true"
```

Folder:

```env
BANNERS_UPLOAD_FOLDER=banners
```

The Upload Service response metadata is persisted in:

```text
image_url
image_name
image_folder
image_size
image_type
```

---

# Upload Lifecycle

## Creation

```text
Upload image
    |
    v
Receive image metadata
    |
    v
Insert banner in PostgreSQL
```

If the database insert fails after the upload succeeds:

```text
best-effort delete newly uploaded file
```

---

## Replacement

Banner image replacement intentionally uploads the new image **before** deleting the old image.

Flow:

```text
Existing banner points to old image
           |
           v
Upload replacement image
           |
           v
Update PostgreSQL record
           |
           +-- DB failure
           |      |
           |      v
           |   delete newly uploaded image
           |
           +-- DB success
                  |
                  v
           delete old image best-effort
```

This avoids leaving a live banner pointing to an image that was deleted before the replacement was successfully committed.

---

# Update Banner with JSON

```http
PUT /banners/admin/{banner_id}
```

Every field is optional.

Example:

```json
{
  "title": "Updated Campaign",
  "sort_order": 5,
  "is_active": false
}
```

The service validates the final time range after combining existing and new values.

---

# Update Banner with New File

```http
PUT /banners/admin/{banner_id}/upload
Content-Type: multipart/form-data
```

Required:

```text
file
```

Optional:

```text
title
alt_text
link_url
platform
start_at
expire_at
sort_order
is_active
```

Example:

```bash
curl -X PUT \
  http://localhost:8000/banners/admin/4289bd99-f900-4442-8fb1-2abb0cef104e/upload \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@new-banner.webp" \
  -F "title=Updated Summer Campaign"
```

---

# Delete Banner

```http
DELETE /banners/admin/{banner_id}
```

Database deletion is performed first.

After the database row is removed, the remote image is deleted on a best-effort basis when:

```text
image_name
AND
image_folder
```

are available.

Successful response:

```json
{
  "message": "Banner deleted",
  "id": "4289bd99-f900-4442-8fb1-2abb0cef104e"
}
```

If remote cleanup fails, the database deletion remains successful and the orphaned upload is logged.

This behavior is intentional: an orphaned upload is safer than deleting an image first and then failing to delete the corresponding database resource.

---

# Validation

## Title

```text
1..255 characters
```

## Alt text

Maximum:

```text
255 characters
```

## Link URL

Must contain at least one character.

## Sort Order

```text
sort_order >= 0
```

## Time Range

```text
expire_at > start_at
```

## Platform

```text
landing
extension
```

---

# Upload Validation

Default accepted MIME types:

```text
image/jpeg
image/png
image/webp
image/gif
```

Maximum size:

```text
10 MB
```

Configurable using:

```env
MAX_UPLOAD_SIZE_MB
ALLOWED_UPLOAD_CONTENT_TYPES
```

---

# Error Responses

| HTTP | Meaning |
|---:|---|
| `401` | Missing, invalid, or expired JWT |
| `403` | User does not have an allowed admin role |
| `404` | Banner not found |
| `413` | File exceeds upload limit |
| `415` | Unsupported MIME type |
| `422` | Invalid request/platform/time range |
| `502` | Upload Service unavailable/rejected request |
| `504` | Upload Service timed out |

---

# Environment Variables

```env
BANNERS_UPLOAD_FOLDER=banners

UPLOAD_SERVICE_URL=https://upload.example.com
UPLOAD_SERVICE_API_KEY=...

MAX_UPLOAD_SIZE_MB=10
ALLOWED_UPLOAD_CONTENT_TYPES=image/jpeg,image/png,image/webp,image/gif
```

Authentication:

```env
JWT_JWKS_URL=https://auth.example.com/.well-known/jwks.json
ADMIN_ROLES=ADMIN,SUPER_ADMIN
```

---

# Files

```text
app/modules/banners/
├── __init__.py
├── admin.py
├── model.py
├── repo.py
├── router.py
├── schema.py
├── service.py
└── README.md
```

Related:

```text
app/services/upload_client.py
app/core/security.py
app/shared/auth.py
```

---