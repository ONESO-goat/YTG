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
    active: bool = Field(default=False)
    
    warning_active: bool = Field(default=False)
    tracking_start_at: Optional[datetime] = Field(default=None)  # see #2
    target_duration_seconds: int = Field(default=0)
    
    
    total_alerts: int = Field(default=0)
    amount_of_warnings_ignored: int = Field(default=0)
    amount_of_warnings_listened: int = Field(default=0)
    
    penalized_this_episode: bool = Field(default=False)
    
    events: list = Field(default_factory=list, sa_column=Column(MutableList.as_mutable(JSON)))

    points_pending: int = Field(default=0)

    last_scan_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    last_active_at: datetime = Field(default=None, nullable=True)
    
    streak: int = Field(default=0)
    
    def reset(self):
        self.warning_active = False
        self.tracking_start_at = None
        self.target_duration_seconds = 0
        
        self.total_alerts = 0
        self.amount_of_warnings_listened = 0
        self.amount_of_warnings_ignored = 0
        self.penalized_this_episode = False
        
        self.events = []
        self.points_pending = 0
        
        self.last_scan_at = None
        
        self.last_active_at = datetime.now().today()
        
    def start(self):
        self.check_for_streak()
        if not self.active:
            self.last_active_at = datetime.now().today()
        
        self.active = True
        
    def end(self):
        self.active = False
        
    def check_for_streak(self):
        if not self.last_active_at: return
        
        today = datetime.today()
        time_distance = (today - self.last_active_at).total_seconds() / 3600
        
        # Must wait at least 12 hours (prevents spamming), but less than 36 hours
        if 12 <= time_distance <= 36:
            self.streak += 1
            self.last_active_at = today
        # Missed the window
        elif time_distance > 36:
            self.streak = 1
  