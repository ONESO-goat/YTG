from sqlmodel import SQLModel, Field, JSON, Column
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.mutable import MutableList
from .helper import create_id

class GuardianSession(SQLModel, table=True):
    __tablename__ = "guardian_session"

    id: str = Field(default_factory=create_id, primary_key=True)

    user_id: str = Field(foreign_key="user.id")
    guardian_id: str = Field(foreign_key="guardian.id")

    warning_active: bool = Field(default=False)
    tracking_start_at: Optional[datetime] = Field(default=None)  # see #2
    target_duration_seconds: int = Field(default=0)
    total_alerts: int = Field(default=0)
    penalized_this_episode: bool = Field(default=False)
    
    events: list = Field(default_factory=list, sa_column=Column(MutableList.as_mutable(JSON)))

    points_pending: int = Field(default=0)

    last_scan_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)