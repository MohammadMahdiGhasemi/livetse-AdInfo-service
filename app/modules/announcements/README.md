# Announcements Module

Announcement management for the Livetse AdInfo platform. Time-bounded, targetable messages shown on landing, dashboard, extension, and mobile.

## Overview

An announcement is a message (text + optional link / image / button) that appears in one or more product sections. Announcements can be:

- **PUBLIC** — visible to anyone, no auth required.
- **PRIVATE** — only delivered to users whose JWT claims match all of the configured targeting dimensions. Each dimension is evaluated against the JWT below.

### JWT payload (the source of truth)

```json
{
  "id": "68480b5dcf9fa59816338de9",
  "phoneNumber": "09920628450",
  "dataTier": "GOLD",
  "liveTreadAccess": true,
  "userDataGroup": "STANDARD",
  "device": "DESKTOP",
  "iat": 1783404133,
  "exp": 1783418533
}
```

Notes:

- `dataTier` is one of `STANDARD`, `SILVER`, `GOLD` — UPPERCASE. Mixed-case values (`Gold`) are normalized at decode time.
- `liveTreadAccess` is a true boolean. Tokens issued by older services used `"True"`/`"False"` strings; they are defensively coerced to booleans.
- `role` is no longer consulted for targeting.

### Targeting rule (PRIVATE)

A user must match **all** of the configured dimensions for the announcement to be returned.

| Field | Unrestricted when | Otherwise user matches when |
|-------|-------------------|------------------------------|
| `target_data_tiers` (TEXT[]) | empty `[]` | `user.dataTier` is in the array |
| `target_live_tread_access` (BOOL, NULL allowed) | `NULL` | `user.liveTreadAccess == target_live_tread_access` |
| `target_user_data_groups` (TEXT[]) | empty `[]` | `user.userDataGroup` is in the array |
| `target_devices` (TEXT[]) | empty `[]` | `user.device` is in the array |

Final boolean: `data_tier_matched AND live_tread_access_matched AND user_data_group_matched AND device_matched`. All filtering happens at the database level using the `cardinality = 0 OR value = ANY(arr)` pattern backed by GIN indexes, plus `IS NULL` / `IS :bool` for the nullable boolean.

> `role` is not used in any query, DTO, service, or repository.

## Setup

### Environment Variables

Add to your `.env.test` (or relevant env file):

```env
JWT_SECRET=<shared-secret-with-token-issuer>
ANNOUNCEMENTS_UPLOAD_FOLDER=announcements
```

If `JWT_SECRET` is not set, the service generates a temporary one at startup and prints `[WARN]`. User JWTs from other services will then fail validation.

### Database

The `announcements` table is created automatically via SQLAlchemy. Columns:

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `text` | TEXT | Announcement body, required |
| `link` | TEXT | Optional URL |
| `button_text` | VARCHAR(100) | Optional call-to-action label |
| `image_url` | TEXT | Full URL to served image |
| `sections` | TEXT[] | Any of `LANDING`, `DASHBOARD`, `EXTENSION`, `MOBILE` |
| `visibility` | ENUM | `PUBLIC` or `PRIVATE` |
| `subscription_types` | TEXT[] | Subscription plans this applies to (empty = all) |
| `target_data_tiers` | TEXT[] | Allowed JWT `dataTier` values (empty = all) |
| `target_live_tread_access` | BOOL NULL | Required `liveTreadAccess` value (NULL = unrestricted) |
| `target_user_data_groups` | TEXT[] | Allowed JWT `userDataGroup` values (empty = all) |
| `target_devices` | TEXT[] | Allowed JWT `device` values (empty = all) |
| `display_start_at` | TIMESTAMPTZ | Display start time |
| `display_expire_at` | TIMESTAMPTZ | Display end time |
| `is_active` | BOOLEAN | Master enable flag |
| `created_at` | TIMESTAMPTZ | Record creation time |
| `updated_at` | TIMESTAMPTZ | Last modification time |

Indexes:

- B-tree: `ix_announcements_visibility`, `ix_announcements_is_active`, `ix_announcements_display_start_at`, `ix_announcements_display_expire_at`, `ix_announcements_created_at`, `ix_announcements_target_live_tread_access`, `ix_announcements_active_visibility_start` (composite `(is_active, visibility, display_start_at)`).
- GIN (PostgreSQL ARRAY containment): `ix_announcements_sections_gin`, `ix_announcements_subscription_types_gin`, `ix_announcements_target_data_tiers_gin`, `ix_announcements_target_user_data_groups_gin`, `ix_announcements_target_devices_gin`.

## API Endpoints

### Public

#### Get Latest Announcements

```
GET /announcements/latest?section=DASHBOARD&limit=5
```

| Param | Type | Required | Default | Values |
|-------|------|----------|---------|--------|
| `section` | string | Yes | — | `LANDING`, `DASHBOARD`, `EXTENSION`, `MOBILE` |
| `limit` | int | No | 5 | 1–50 |

Returns active PUBLIC announcements matching the section within their time window, sorted by `display_start_at DESC, created_at DESC`.

#### Get Announcement History

```
GET /announcements/history?section=DASHBOARD&visibility=PUBLIC&page=1&limit=20
GET /announcements/history?section=DASHBOARD&visibility=PRIVATE&page=1&limit=20
```

| Param | Type | Required | Default | Values |
|-------|------|----------|---------|--------|
| `section` | string | Yes | — | `LANDING`, `DASHBOARD`, `EXTENSION`, `MOBILE` |
| `visibility` | string | No | `PUBLIC` | `PUBLIC`, `PRIVATE` |
| `page` | int | No | 1 | ≥ 1 |
| `limit` | int | No | 20 | 1–100 |

- `visibility=PUBLIC` (or omitted): no auth, returns PUBLIC history (expired items included).
- `visibility=PRIVATE`: requires `Authorization: Bearer <jwt>`; applies the four-dimension targeting filter using the JWT.

### Admin

All admin endpoints require:
```
Authorization: Bearer <ADMIN_PASSWORD>
```

#### List Announcements (filters: data_tier instead of role)

```
GET /announcements/admin?section=DASHBOARD&visibility=PRIVATE&is_active=true&data_tier=GOLD&live_tread_access=true&page=1&size=20
```

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `section` | string | No | — |
| `visibility` | string | No | — |
| `is_active` | bool | No | — |
| `subscription_type` | string | No | — |
| `data_tier` | string | No | — (`STANDARD` / `SILVER` / `GOLD`) |
| `live_tread_access` | bool | No | — |
| `user_data_group` | string | No | — |
| `device` | string | No | — |
| `display_start_at` | ISO 8601 | No | — |
| `display_expire_at` | ISO 8601 | No | — |
| `page` | int | No | 1 |
| `size` | int | No | 20 (max 100) |

#### Create Announcement (JSON)

```jsonc
// PUBLIC
{
  "text": "New update is available",
  "sections": ["DASHBOARD"],
  "visibility": "PUBLIC",
  "display_start_at": "2026-07-08T00:00:00Z",
  "display_expire_at": "2026-07-20T00:00:00Z",
  "is_active": true
}

// PRIVATE — STANDARD users only
{
  "text": "Message for standard users",
  "sections": ["DASHBOARD"],
  "visibility": "PRIVATE",
  "target_data_tiers": ["STANDARD"],
  "target_live_tread_access": null,
  "display_start_at": "2026-07-08T00:00:00Z",
  "display_expire_at": "2026-07-20T00:00:00Z",
  "is_active": true
}

// PRIVATE — GOLD users with live tread access
{
  "text": "Gold + LTA",
  "sections": ["DASHBOARD"],
  "visibility": "PRIVATE",
  "target_data_tiers": ["GOLD"],
  "target_live_tread_access": true,
  "display_start_at": "2026-07-08T00:00:00Z",
  "display_expire_at": "2026-07-20T00:00:00Z",
  "is_active": true
}
```

`tier` values are normalized to uppercase at validation time. Bad values (`Platinum`, etc.) are rejected with 422.

#### Create / Update (multipart)

Same JSON fields, comma-separated for array fields, `target_live_tread_access` accept `true`/`false` as strings.

## Files

```
app/modules/announcements/
├── __init__.py
├── model.py        # SQLAlchemy model
├── schema.py       # Pydantic schemas (with tier normalization + LTA coercion)
├── repo.py         # Database queries (incl. targeting-builder)
├── service.py      # Business logic + upload integration
├── router.py       # Public API (/latest, /history)
├── admin.py        # Admin API (CRUD + filterable list)
└── README.md

app/shared/
├── auth.py         # JWT decode (uses dataTier, liveTreadAccess; legacy bool-coercion)
└── enums.py        # AnnouncementSection, AnnouncementVisibility, DataTier, ...
```
