import uuid
import random

UUIDString = str 
def create_id()->UUIDString:
    return str(uuid.uuid4())

def create_number_id():
    return random.randint(1000000000, 9999999999)

def utcnow_naive():
    """Current UTC time without tzinfo, matching how timestamps are stored in SQLite."""
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(tzinfo=None)
