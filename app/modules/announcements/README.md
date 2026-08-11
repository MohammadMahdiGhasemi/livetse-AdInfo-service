# Announcements Module

Announcements support scheduling, sections, public/private visibility, user targeting, optional images, and an explicit notification type.

Allowed types are exactly:

```text
info
warning
error
success
```

`info` is the creation default. `danger` is not accepted.

Example:

```json
{
  "text": "Maintenance starts tonight.",
  "type": "warning",
  "sections": ["LANDING"],
  "visibility": "PUBLIC",
  "display_start_at": "2026-08-11T18:00:00Z",
  "display_expire_at": "2026-08-12T02:00:00Z"
}
```

The admin list can filter by type:

```http
GET /announcements/admin?type=warning
```

Main endpoints:

```text
GET    /announcements/latest
GET    /announcements/history
GET    /announcements/admin
GET    /announcements/admin/{id}
POST   /announcements/admin
POST   /announcements/admin/upload
PUT    /announcements/admin/{id}
PUT    /announcements/admin/{id}/upload
DELETE /announcements/admin/{id}
```

See the root `README.md` for complete configuration, targeting rules and production deployment.
