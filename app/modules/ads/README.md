# Ads Module

The Ads module manages scheduled campaigns, multiple images/assets per campaign, page/platform placement positions, uploads, and daily statistics.

## Placement model

Each `AdAsset` belongs to one campaign and contains:

```text
campaign_id
platform
position
title
image_url
link_url
```

Supported platforms:

```text
landing
app
extension
```

Example:

```text
landing position 1 -> campaign X / image A
landing position 2 -> campaign Y / image B
landing position 3 -> campaign X / image C
```

`GET /ads/?platform=landing` returns active assets ordered by `position ASC`.

By default, overlapping active campaigns cannot reserve the same `platform + position`. Configure with:

```env
ADS_POSITION_CONFLICT_CHECK_ENABLED=true
ADS_MIN_POSITION=1
ADS_MAX_POSITION=100
```

A campaign also cannot have duplicate `platform + position` assets.

## Admin asset operations

```text
GET    /ads/admin/{campaign_id}/assets
GET    /ads/admin/assets/{asset_id}
POST   /ads/admin/{campaign_id}/assets
POST   /ads/admin/{campaign_id}/assets/upload
PUT    /ads/admin/assets/{asset_id}
DELETE /ads/admin/assets/{asset_id}
```

Both create endpoints require `platform` and `position`.

Example update:

```json
{
  "platform": "landing",
  "position": 4
}
```

See the root `README.md` for complete configuration, deployment and API behavior.
