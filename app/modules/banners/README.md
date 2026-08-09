# Banners Module

Banner management service for the Livetse Promotion platform. Handles CRUD operations for promotional banners with image upload via the Livetse Upload Service.

## Overview

Banners are displayed on the landing page and browser extension. Each banner has a scheduled time window (`start_at` → `expire_at`), a platform target, and an image stored in WordPress via the Upload Service.

## Setup

### Environment Variables

Add to your `.env.test` (or relevant env file):

```env
# Upload Service connection
UPLOAD_SERVICE_URL=http://localhost:8000
UPLOAD_SERVICE_API_KEY=your-upload-service-api-key
BANNERS_UPLOAD_FOLDER=banners
```

### Database

The `banners` table is created automatically via SQLAlchemy models. Columns:

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `title` | VARCHAR(255) | Banner title |
| `image_url` | TEXT | Full URL to served image |
| `image_name` | VARCHAR(255) | Original filename in WordPress |
| `image_folder` | VARCHAR(100) | WordPress folder name |
| `image_size` | INTEGER | File size in bytes |
| `image_type` | VARCHAR(100) | MIME type |
| `alt_text` | VARCHAR(255) | Image alt text |
| `link_url` | TEXT | Click-through URL |
| `platform` | VARCHAR(50) | `landing` or `extension` |
| `start_at` | TIMESTAMPTZ | Display start time |
| `expire_at` | TIMESTAMPTZ | Display end time |
| `is_active` | BOOLEAN | Enable/disable banner |
| `sort_order` | INTEGER | Display priority (lower = first) |
| `created_at` | TIMESTAMPTZ | Record creation time |
| `updated_at` | TIMESTAMPTZ | Last modification time |

Index: `idx_banner_active_time` on `(is_active, start_at, expire_at)`.

## API Endpoints

### Public

#### Get Active Banners

```
GET /banners/?platform={platform}
```

Returns banners that are active and within their time window, sorted by `sort_order`.

| Param | Type | Required | Values |
|-------|------|----------|--------|
| `platform` | string | Yes | `landing`, `extension` |

**Response** `200`:
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "Summer Sale",
    "image_url": "https://example.com/wp-json/cue/v1/serve/banners/sale.jpg",
    "alt_text": "Summer sale banner",
    "link_url": "https://example.com/sale",
    "platform": "landing",
    "start_at": "2024-06-01T00:00:00Z",
    "expire_at": "2024-08-31T23:59:59Z",
    "sort_order": 0,
    "is_active": true,
    "created_at": "2024-05-15T10:30:00Z",
    "updated_at": "2024-05-15T10:30:00Z"
  }
]
```

---

### Admin

All admin endpoints require the `Authorization` header:

```
Authorization: Bearer {RS256_JWT}
```

#### List All Banners (Paginated)

```
GET /banners/admin?page=1&size=20
```

| Param | Type | Default | Range |
|-------|------|---------|-------|
| `page` | int | 1 | ≥ 1 |
| `size` | int | 20 | 1–100 |

**Response** `200`:
```json
{
  "items": [...],
  "total": 45,
  "page": 1,
  "size": 20,
  "pages": 3
}
```

---

#### Get Banner by ID

```
GET /banners/admin/{banner_id}
```

**Response** `200`: Banner object  
**Response** `404`: `{"detail": "Banner not found"}`

---

#### Create Banner (JSON)

```
POST /banners/admin
Content-Type: application/json

{
  "title": "Summer Sale",
  "image_url": "https://example.com/image.jpg",
  "alt_text": "Summer sale",
  "link_url": "https://example.com/sale",
  "platform": "landing",
  "start_at": "2024-06-01T00:00:00Z",
  "expire_at": "2024-08-31T23:59:59Z",
  "sort_order": 0,
  "is_active": true
}
```

**Response** `201`: Banner object

---

#### Create Banner (with file upload)

```
POST /banners/admin/upload
Content-Type: multipart/form-data

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | Yes | Image file |
| `title` | string | Yes | Banner title |
| `link_url` | string | Yes | Click-through URL |
| `platform` | string | Yes | `landing` or `extension` |
| `start_at` | string | Yes | ISO 8601 datetime |
| `expire_at` | string | Yes | ISO 8601 datetime |
| `alt_text` | string | No | Image alt text |
| `sort_order` | int | No | Default: 0 |
| `is_active` | bool | No | Default: true |

**Response** `201`:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Summer Sale",
  "image_url": "https://example.com/wp-json/cue/v1/serve/banners/sale.jpg",
  "image_name": "sale.jpg",
  "image_folder": "banners",
  "image_size": 1048576,
  "image_type": "image/jpeg",
  "link_url": "https://example.com/sale",
  "platform": "landing",
  "start_at": "2024-06-01T00:00:00Z",
  "expire_at": "2024-08-31T23:59:59Z",
  "sort_order": 0,
  "is_active": true,
  "created_at": "2024-05-15T10:30:00Z"
}
```

---

#### Update Banner (JSON)

```
PUT /banners/admin/{banner_id}
Content-Type: application/json

{
  "title": "Updated Title",
  "sort_order": 5
}
```

All fields are optional — only provided fields are updated.

**Response** `200`: Updated banner object  
**Response** `404`: `{"detail": "Banner not found"}`

---

#### Update Banner (with new file)

```
PUT /banners/admin/{banner_id}/upload
Content-Type: multipart/form-data
```

Same fields as create upload. The old image is automatically deleted from WordPress.

**Response** `200`: Updated banner object with new image metadata

---

#### Delete Banner

```
DELETE /banners/admin/{banner_id}
```

Automatically deletes the associated image from WordPress.

**Response** `200`:
```json
{
  "message": "Banner deleted",
  "id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response** `404`: `{"detail": "Banner not found"}`

---

## cURL Examples

### Create banner with image upload

```bash
curl -X POST http://localhost:8000/banners/admin/upload \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@banner.jpg" \
  -F "title=Summer Sale" \
  -F "link_url=https://example.com/sale" \
  -F "platform=landing" \
  -F "start_at=2024-06-01T00:00:00Z" \
  -F "expire_at=2024-08-31T23:59:59Z" \
  -F "alt_text=Summer sale banner" \
  -F "sort_order=0"
```

### Get active banners

```bash
curl http://localhost:8000/banners/?platform=landing
```

### Update banner title

```bash
curl -X PUT http://localhost:8000/banners/admin/{banner_id} \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Winter Sale"}'
```

### Delete banner

```bash
curl -X DELETE http://localhost:8000/banners/admin/{banner_id} \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

## Error Responses

| Status | Meaning |
|--------|---------|
| `401` | Missing `Authorization` header |
| `403` | Invalid password |
| `404` | Banner not found |
| `422` | Validation error (invalid date, missing fields, etc.) |
| `502` | Upload Service unreachable |

## Architecture

```
Client Request
      │
      ▼
admin.py (FastAPI Router)
      │
      ▼
BannerService
      │
      ├──▶ BannerRepository (PostgreSQL)
      │
      └──▶ UploadServiceClient (WordPress)
               │
               ▼
         Upload Service → WordPress CUE Plugin
```

- **Create with upload**: File → Upload Service → WordPress → URL saved to DB
- **Update with upload**: Delete old image → Upload new → Update DB
- **Delete**: Delete image from WordPress → Delete DB record

## Files

```
app/modules/banners/
├── __init__.py
├── model.py        # SQLAlchemy model
├── schema.py       # Pydantic schemas
├── repo.py         # Database queries
├── service.py      # Business logic + upload integration
├── router.py       # Public API endpoints
└── admin.py        # Admin API endpoints

app/services/
└── upload_client.py  # HTTP client for Upload Service
```
