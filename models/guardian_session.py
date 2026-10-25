from datetime import datetime

from sqlalchemy import Index
from sqlmodel import Field, SQLModel

from .helper import create_id, utcnow_naive


class GuardianSession(SQLModel, table=True):
    """A user's monitoring state under one guardian. Daily stats live in models/progress.py."""

    __tablename__ = "guardian_session"
    __table_args__ = (Index("ix_guardian_session_user_guardian", "user_id", "guardian_id"),)

    id: str = Field(default_factory=create_id, primary_key=True)

    user_id: str = Field(foreign_key="user.id")
    guardian_id: str = Field(foreign_key="guardian.id")
    active: bool = Field(default=False)

    # Current warning episode
    warning_active: bool = Field(default=False)
    warning_started_at: datetime | None = Field(default=None, nullable=True)
    last_flag_category: str | None = Field(default=None, nullable=True)
    penalized_this_episode: bool = Field(default=False)
    episode_penalties: int = Field(default=0)
    last_penalty_at: datetime | None = Field(default=None, nullable=True)
    # When the user moved away from flagged content, and how long they must stay away
    tracking_start_at: datetime | None = Field(default=None)
    target_duration_seconds: int = Field(default=0)

    # Start of the current clean minute
    minute_timer: datetime | None = Field(default=None, nullable=True)

    # Perceptual hash of the last screenshot, see agent/frames.py
    last_frame_hash: str | None = Field(default=None, nullable=True)
    same_image_counter: int = Field(default=0)
    total_same_image_counter_for_whole_session: int = Field(default=0)
    # How many times the session was stopped for an idle screen
    shutdown_counter: int = Field(default=0)

    last_scan_at: datetime | None = Field(default=None)
    last_active_at: datetime | None = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=utcnow_naive)

    def start(self):
        self.active = True
        self.last_active_at = utcnow_naive()

    def end(self):
        self.active = False
