import io
import os
import random
import sys
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
