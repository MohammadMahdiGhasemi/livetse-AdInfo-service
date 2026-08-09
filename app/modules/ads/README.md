# Ads Module

The Ads module manages advertising campaigns, campaign assets, platform delivery, and daily performance statistics.

It provides:

- campaign CRUD;
- campaign scheduling;
- platform-specific ad assets;
- public active-ad delivery;
- asset image upload;
- daily view/click statistics;
- bulk statistics upsert;
- campaign-level statistics queries.

Module path:

```text
app/modules/ads/
```

---

# Domain Model

The Ads domain contains three entities:

```text
AdCampaign
AdAsset
AdStats
```

Relationship:

```text
AdCampaign
     |
     | 1:N
     v
AdAsset
     |
     | 1:N
     v
AdStats
```

---

# Campaign

A campaign defines:

```text
client
active state
start date
expiration date
```

Example:

```json
{
  "client_name": "Example Company",
  "start_at": "2026-08-09T00:00:00Z",
  "expire_at": "2026-09-01T00:00:00Z",
  "is_active": true
}
```

---

# Asset

An asset belongs to a campaign and defines what should be displayed on a specific platform.

Fields include:

```text
campaign_id
platform
title
image_url
link_url
```

---

# Statistics

Statistics are stored per:

```text
asset + date
```

Example:

```json
{
  "asset_id": "c96274ae-3dfc-41b1-8c82-47089b31942c",
  "date": "2026-08-09",
  "views_count": 2500,
  "clicks_count": 125
}
```

The combination:

```text
asset_id + date
```

is unique.

---

# Architecture

```text
                         Ads Module

                      +----------------+
                      |  HTTP Routers  |
                      +--------+-------+
                               |
             +-----------------+------------------+
             |                 |                  |
             v                 v                  v
        CampaignService    AssetService       StatsService
             |                 |                  |
             v                 v                  v
        CampaignRepo       AssetRepo          StatsRepo
             |                 |                  |
             +-----------------+------------------+
                               |
                               v
                           PostgreSQL

AssetService
     |
     +--> UploadServiceClient
```

---

# Supported Platforms

Ads support:

```text
extension
app
landing
```

Defined by:

```python
AdPlatform
```

---

# Database Tables

## `ad_campaigns`

| Column | Type | Required |
|---|---|---:|
| `id` | UUID | yes |
| `client_name` | VARCHAR(255) | yes |
| `start_at` | TIMESTAMPTZ | yes |
| `expire_at` | TIMESTAMPTZ | yes |
| `is_active` | BOOLEAN | yes |
| `created_at` | TIMESTAMPTZ | yes |
| `updated_at` | TIMESTAMPTZ | yes |

Constraint:

```text
expire_at > start_at
```

Index:

```text
ix_ad_campaign_active_time
```

on:

```text
is_active
start_at
expire_at
```

---

## `ad_assets`

| Column | Type | Required |
|---|---|---:|
| `id` | UUID | yes |
| `campaign_id` | UUID | yes |
| `platform` | VARCHAR(50) | yes |
| `title` | VARCHAR(255) | no |
| `image_url` | TEXT | yes |
| `link_url` | TEXT | yes |
| `created_at` | TIMESTAMPTZ | yes |
| `updated_at` | TIMESTAMPTZ | yes |

Foreign key:

```text
campaign_id -> ad_campaigns.id
```

with:

```text
ON DELETE CASCADE
```

Indexes exist on:

```text
campaign_id
platform
```

---

## `ad_stats`

| Column | Type | Required |
|---|---|---:|
| `id` | UUID | yes |
| `asset_id` | UUID | yes |
| `views_count` | INTEGER | yes |
| `clicks_count` | INTEGER | yes |
| `date` | DATE | yes |

Foreign key:

```text
asset_id -> ad_assets.id
```

with:

```text
ON DELETE CASCADE
```

Unique constraint:

```text
(asset_id, date)
```

Database checks:

```text
views_count >= 0
clicks_count >= 0
```

Indexes:

```text
asset_id
date
```

---

# Public API

## Get Active Ads by Platform

```http
GET /ads/?platform={platform}
```

No authentication is required.

Example:

```http
GET /ads/?platform=extension
```

The query returns assets whose parent campaign satisfies:

```text
campaign.is_active = true
campaign.start_at <= now
campaign.expire_at >= now
asset.platform = requested platform
```

Ordering:

```text
asset.created_at DESC
```

Example response:

```json
[
  {
    "id": "c96274ae-3dfc-41b1-8c82-47089b31942c",
    "campaign_id": "a74c00b5-e014-4211-966d-62ce287767b7",
    "platform": "extension",
    "title": "Example Advertisement",
    "image_url": "https://cdn.example.com/ad.jpg",
    "link_url": "https://example.com/campaign",
    "created_at": "2026-08-09T08:00:00Z",
    "updated_at": "2026-08-09T08:00:00Z"
  }
]
```

---

# Admin Authentication

All admin routes require:

```http
Authorization: Bearer <RS256 JWT>
```

and an allowed admin role.

Configured through:

```env
ADMIN_ROLES=ADMIN,SUPER_ADMIN
```

---

# Campaign API

## List Campaigns

```http
GET /ads/admin
```

Filters:

| Name | Type |
|---|---|
| `client_name` | string |
| `is_active` | boolean |
| `start_at` | datetime |
| `expire_at` | datetime |
| `page` | integer |
| `size` | integer |

Example:

```http
GET /ads/admin?client_name=Acme&is_active=true&page=1&size=20
```

Filter semantics:

```text
client_name
    case-insensitive substring match

is_active
    exact boolean match

start_at
    campaign.start_at >= supplied value

expire_at
    campaign.expire_at <= supplied value
```

Ordering:

```text
created_at DESC
```

Pagination:

```text
page >= 1
1 <= size <= 100
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

---

# Get Campaign

```http
GET /ads/admin/{campaign_id}
```

Not found:

```json
{
  "detail": "Campaign not found"
}
```

---

# Create Campaign

```http
POST /ads/admin
Content-Type: application/json
```

Example:

```json
{
  "client_name": "Example Company",
  "start_at": "2026-08-09T00:00:00Z",
  "expire_at": "2026-09-09T00:00:00Z",
  "is_active": true
}
```

Response:

```http
201 Created
```

---

# Update Campaign

```http
PUT /ads/admin/{campaign_id}
```

All fields are optional.

Example:

```json
{
  "expire_at": "2026-10-01T00:00:00Z",
  "is_active": false
}
```

The service validates the final campaign date range after combining existing and updated values.

Required invariant:

```text
expire_at > start_at
```

---

# Delete Campaign

```http
DELETE /ads/admin/{campaign_id}
```

Example response:

```json
{
  "message": "Campaign deleted",
  "id": "a74c00b5-e014-4211-966d-62ce287767b7"
}
```

Database relationships cascade deletion to:

```text
campaign assets
asset statistics
```

Remote upload cleanup is discussed in [Current Implementation Notes](#current-implementation-notes).

---

# Asset API

## List Campaign Assets

```http
GET /ads/admin/{campaign_id}/assets
```

Parameters:

```text
page
size
```

Example:

```http
GET /ads/admin/a74c00b5-e014-4211-966d-62ce287767b7/assets?page=1&size=20
```

The parent campaign is validated before assets are returned.

Unknown campaign:

```http
404 Not Found
```

---

# Get Asset

```http
GET /ads/admin/assets/{asset_id}
```

Unknown asset:

```http
404 Not Found
```

---

# Create Asset without Upload

Current endpoint:

```http
POST /ads/admin/{campaign_id}/assets
Content-Type: multipart/form-data
```

Although this route does not require an uploaded file, it currently accepts **form fields**, not JSON.

Fields:

| Field | Required | Default |
|---|---:|---|
| `platform` | yes | — |
| `title` | no | `null` |
| `image_url` | no | `""` |
| `link_url` | no | `""` |

Example:

```bash
curl -X POST \
  http://localhost:8000/ads/admin/a74c00b5-e014-4211-966d-62ce287767b7/assets \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "platform=landing" \
  -F "title=Homepage Advertisement" \
  -F "image_url=https://cdn.example.com/ad.jpg" \
  -F "link_url=https://example.com"
```

Valid platforms:

```text
extension
app
landing
```

---

# Create Asset with Upload

```http
POST /ads/admin/{campaign_id}/assets/upload
Content-Type: multipart/form-data
```

Fields:

| Field | Required |
|---|---:|
| `file` | yes |
| `platform` | yes |
| `title` | no |
| `link_url` | no |

Example:

```bash
curl -X POST \
  http://localhost:8000/ads/admin/a74c00b5-e014-4211-966d-62ce287767b7/assets/upload \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@advertisement.webp" \
  -F "platform=extension" \
  -F "title=Extension Advertisement" \
  -F "link_url=https://example.com"
```

Uploads use:

```env
ADS_UPLOAD_FOLDER=ads
```

The returned Upload Service URL is stored in:

```text
image_url
```

If the upload succeeds but the subsequent database insert fails, the service performs best-effort cleanup of the new remote object when its `name` and `folder` are present in the upload response.

---

# Delete Asset

```http
DELETE /ads/admin/assets/{asset_id}
```

Example response:

```json
{
  "message": "Asset deleted",
  "id": "c96274ae-3dfc-41b1-8c82-47089b31942c"
}
```

Database statistics for that asset are removed through cascading foreign-key behavior.

---

# Statistics API

Stats are stored per asset/day.

---

# Bulk Upsert Stats

```http
POST /ads/admin/stats
Content-Type: application/json
```

Example:

```json
{
  "stats": [
    {
      "asset_id": "c96274ae-3dfc-41b1-8c82-47089b31942c",
      "date": "2026-08-09",
      "views_count": 2500,
      "clicks_count": 125
    },
    {
      "asset_id": "b7283587-4940-4b6a-afd5-9ea123b8e478",
      "date": "2026-08-09",
      "views_count": 3100,
      "clicks_count": 201
    }
  ]
}
```

Each referenced asset is validated before the upsert is performed.

Unknown asset:

```http
404 Not Found
```

---

# Upsert Semantics

Uniqueness key:

```text
asset_id + date
```

If no existing row exists:

```text
INSERT
```

If a row already exists:

```text
UPDATE views_count
UPDATE clicks_count
```

This is implemented using PostgreSQL:

```text
INSERT ... ON CONFLICT DO UPDATE
```

If duplicate `(asset_id, date)` pairs occur within the same incoming request, the service deduplicates them before writing.

The last item for a duplicate key is retained.

---

# Statistics Validation

Both values must be non-negative:

```text
views_count >= 0
clicks_count >= 0
```

This is enforced at both:

```text
Pydantic validation layer
PostgreSQL constraint layer
```

---

# Get Asset Statistics

```http
GET /ads/admin/assets/{asset_id}/stats
```

Parameters:

```text
page
size
```

Example:

```http
GET /ads/admin/assets/c96274ae-3dfc-41b1-8c82-47089b31942c/stats?page=1&size=20
```

Ordering:

```text
date DESC
```

Response:

```json
{
  "items": [
    {
      "id": "3cae08ff-0be3-442d-a574-e5bfc9786944",
      "asset_id": "c96274ae-3dfc-41b1-8c82-47089b31942c",
      "views_count": 2500,
      "clicks_count": 125,
      "date": "2026-08-09"
    }
  ],
  "total": 1,
  "page": 1,
  "size": 20,
  "pages": 1
}
```

---

# Get Campaign Statistics

```http
GET /ads/admin/{campaign_id}/stats
```

This returns statistics for all assets belonging to the campaign.

Example:

```http
GET /ads/admin/a74c00b5-e014-4211-966d-62ce287767b7/stats?page=1&size=20
```

Ordering:

```text
date DESC
```

---

# Validation

## Campaign Client Name

```text
1..255 characters
```

## Campaign Time Range

```text
expire_at > start_at
```

## Platform

Allowed:

```text
extension
app
landing
```

## Statistics

```text
views_count >= 0
clicks_count >= 0
```

---

# Upload Validation

Global upload validation applies.

Defaults:

```text
maximum size = 10 MB

allowed types:
image/jpeg
image/png
image/webp
image/gif
```

Configuration:

```env
MAX_UPLOAD_SIZE_MB
ALLOWED_UPLOAD_CONTENT_TYPES
```

---

# Error Responses

| HTTP | Meaning |
|---:|---|
| `401` | Missing/invalid/expired JWT |
| `403` | Valid JWT without admin role |
| `404` | Campaign or asset not found |
| `413` | Upload too large |
| `415` | Unsupported image content type |
| `422` | Invalid platform/data/date range/count |
| `502` | Upload Service rejected/unavailable |
| `504` | Upload Service timed out |

---

# Current Implementation Notes

## No Asset Update Endpoint

The current Ads API supports:

```text
create asset
get asset
list assets
delete asset
```

but does not currently expose:

```text
PUT /ads/admin/assets/{asset_id}
```

If asset metadata or image replacement is required, an update endpoint should be implemented explicitly.

---

## Asset Creation Uses Form Data

The non-upload create route:

```text
POST /ads/admin/{campaign_id}/assets
```

currently uses FastAPI `Form(...)` parameters.

Therefore its request content type is:

```text
multipart/form-data
```

or form-compatible encoding, not application/json.

---

## Empty Image/Link Strings

The current non-upload asset create endpoint defaults:

```text
image_url = ""
link_url = ""
```

The database requires non-NULL values, but empty strings satisfy that database constraint.

If business rules require valid URLs, URL validation should be added to the schema/API layer.

---

## Remote Upload Metadata Is Not Persisted

`AdAsset` currently stores:

```text
image_url
```

but does not store:

```text
image_name
image_folder
image_size
image_type
```

Therefore after a successful asset creation, remote-upload metadata is no longer available from the database.

Consequences:

```text
DELETE asset
    -> deletes database record
    -> does not currently delete uploaded file

DELETE campaign
    -> cascades database asset/stat rows
    -> does not currently delete uploaded files
```

The create-upload flow can still clean up a newly uploaded object when the database insert immediately fails because the upload response metadata remains available in memory.

If full upload lifecycle management is required, persist upload metadata on `AdAsset` similarly to the Banners module.

---

# Environment Variables

Module-specific:

```env
ADS_UPLOAD_FOLDER=ads
```

Shared upload configuration:

```env
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
app/modules/ads/
├── __init__.py
├── admin.py
├── model.py
├── repo.py
├── router.py
├── schema.py
├── service.py
└── README.md
```

Related files:

```text
app/services/upload_client.py
app/shared/enums.py
app/core/security.py
app/shared/auth.py
```

---

# Endpoint Summary

## Public

```text
GET /ads/
```

## Campaigns

```text
GET    /ads/admin
GET    /ads/admin/{campaign_id}
POST   /ads/admin
PUT    /ads/admin/{campaign_id}
DELETE /ads/admin/{campaign_id}
```

## Assets

```text
GET    /ads/admin/{campaign_id}/assets
GET    /ads/admin/assets/{asset_id}
POST   /ads/admin/{campaign_id}/assets
POST   /ads/admin/{campaign_id}/assets/upload
DELETE /ads/admin/assets/{asset_id}
```

## Statistics

```text
POST /ads/admin/stats

GET /ads/admin/assets/{asset_id}/stats
GET /ads/admin/{campaign_id}/stats
```