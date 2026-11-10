"""Numerical contract tests; these do not replace live Redis/Caddy integration tests."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def sliding_window_reference(timestamps_ms, now_ms, window_ms=60_000, limit=120):
    active = [t for t in timestamps_ms if t > now_ms - window_ms]
    return len(active) < limit


def test_rate_limit_numerical_boundary_120_and_121_requests():
    events = [10_000 + i for i in range(120)]
    assert sliding_window_reference(events, 10_200, limit=120) is False
    assert sliding_window_reference(events[:119], 10_200, limit=120) is True


def test_rate_limit_window_reopens_after_sixty_seconds():
    events = [1_000 + i for i in range(120)]
    assert sliding_window_reference(events, 61_001, limit=120) is True


def test_caddy_routes_api_and_health_to_backend_and_frontend_uses_https_same_origin():
    caddy = (ROOT / "Caddyfile").read_text()
    app = (ROOT / "frontend/app.js").read_text()
    assert "@api path /api/* /health" in caddy
    assert "reverse_proxy 127.0.0.1:8010" in caddy
    assert "reverse_proxy 127.0.0.1:5173" in caddy
    assert 'window.location.protocol === "https:" ? ""' in app
    assert 'const API="http://127.0.0.1:8010"' not in app


def test_redis_rate_limiter_is_atomic_lua_and_fails_closed():
    main = (ROOT / "backend/app/main.py").read_text()
    assert "_RATE_LIMIT_LUA" in main
    assert "redis.call('ZREMRANGEBYSCORE'" in main
    assert "redis.call('ZCARD'" in main
    assert "request.app.state.redis.eval" in main
    assert 'status_code=503' in main
