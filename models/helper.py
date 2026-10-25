import random
import uuid
from datetime import UTC, datetime

UUIDString = str


def create_id() -> UUIDString:
    return str(uuid.uuid4())


def create_number_id() -> int:
    return random.randint(1000000000, 9999999999)


def utcnow_naive() -> datetime:
    """Current UTC time without tzinfo, matching how timestamps are stored in SQLite."""
    return datetime.now(UTC).replace(tzinfo=None)
