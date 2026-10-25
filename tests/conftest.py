import io
import os
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_db_path = ROOT / "tests" / ".test.db"
if _db_path.exists():
    _db_path.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"
os.environ["AI_BACKEND"] = "stub"
os.environ["ADMIN_API_KEY"] = "test-admin-key"
os.environ["JWT_SECRET"] = "test-secret-that-is-long-enough-for-hs256"
os.environ["RATE_LIMITS"] = "off"
os.environ["LOG_LEVEL"] = "WARNING"

from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

import main  # noqa: E402

ADMIN = {"X-Admin-Key": "test-admin-key"}


@pytest.fixture(scope="session")
def client():
    with TestClient(main.app) as c:
        yield c
    if _db_path.exists():
        _db_path.unlink()


def random_png(seed: int | None = None) -> bytes:
    rng = random.Random(seed)
    img = Image.new("L", (64, 48))
    img.putdata([rng.randint(0, 255) for _ in range(64 * 48)])
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


_counter = 0


def signup(client, user_type="individual", password="Password123"):
    global _counter
    _counter += 1
    name = f"user{_counter}_{random.randint(0, 99999)}"
    r = client.post(
        "/auth/signup",
        json={"username": name, "email": f"{name}@example.com", "password": password, "user_type": user_type},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    return {"Authorization": f"Bearer {body['access_token']}"}, body["user"]


from helpers import clock as clock_module  # noqa: E402


class Clock:
    def __init__(self):
        self.now = datetime(2026, 1, 1, 12, 0, 0)

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += timedelta(seconds=seconds)


_current_clock: Clock | None = None


@pytest.fixture(autouse=True)
def clock(monkeypatch):
    """Every test runs on a controllable clock."""
    global _current_clock
    _current_clock = Clock()
    monkeypatch.setattr(clock_module, "now", _current_clock)
    return _current_clock


SCAN_INTERVAL = 5  # seconds between scans, like the real client


def scan(client, headers, session_id, seed):
    _current_clock.advance(SCAN_INTERVAL)
    r = client.post(
        f"/sessions/{session_id}/scan",
        headers=headers,
        files={"file": ("frame.png", random_png(seed), "image/png")},
    )
    assert r.status_code == 200, r.text
    return r.json()


def personal_setup(client):
    headers, user = signup(client, "individual")
    r = client.post("/guardians", headers=headers, json={"name": "Mine"})
    assert r.status_code == 201, r.text
    guardian = r.json()
    r = client.post("/sessions/start", headers=headers, json={})
    assert r.status_code == 200, r.text
    return headers, user, guardian, r.json()["session"]
