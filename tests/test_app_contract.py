import pytest


def test_health_routes_are_registered():
    pytest.importorskip("asyncpg")
    from main import app

    paths = {route.path for route in app.routes}
    assert "/health/live" in paths
    assert "/health/ready" in paths
    assert "/announcements/latest" in paths
    assert "/banners/" in paths
    assert "/ads/" in paths
