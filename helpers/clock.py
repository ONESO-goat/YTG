"""The current time, in one place so tests can control it.

Always call `clock.now()` through the module (not `from helpers.clock import now`), so patching
`helpers.clock.now` affects every caller.
"""

from datetime import UTC, datetime


def now() -> datetime:
    """Naive UTC, matching how timestamps are stored in SQLite."""
    return datetime.now(UTC).replace(tzinfo=None)
