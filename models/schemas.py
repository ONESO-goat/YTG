"""Response shapes sent to the frontend. These never include password hashes."""
from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from models.models import GuardianType, RelationshipType, RewardType, UserType


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    number_id: int
    username: str
    name: str
    email: str
    user_type: UserType
    currency: int


class UserSummary(BaseModel):
    """What other people (guardian owners, connections) get to see about a user."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    number_id: int
    username: str
    name: str
    user_type: UserType
    currency: int


class GuardianPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    guardian_type: GuardianType
    owner_id: Optional[str]
    on: bool


class ConnectionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    guardian_id: str
    user_id: str
    user_name: Optional[str]
    relationship_with_owner: RelationshipType


class SessionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    guardian_id: str
    active: bool
    warning_active: bool
    total_alerts: int
    amount_of_warnings_ignored: int
    amount_of_warnings_listened: int
    points_gain_daily_limit: int
    streak: int
    last_scan_at: Optional[datetime]
    created_at: datetime


class ReportPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    content: str
    guardian_id: Optional[str]
    send_to_id: Optional[str]
    updated_at: date
    created_at: Optional[datetime]


class RewardPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    type: RewardType
    amount: int
    cost: int


class OwnedRewardPublic(BaseModel):
    id: str
    order_id: int
    reward: RewardPublic


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class MeResponse(BaseModel):
    user: UserPublic
    # The guardian the user owns, or for dependents the guardian they are connected to
    guardian: Optional[GuardianPublic]
    is_guardian_owner: bool
    connection: Optional[ConnectionPublic]


class MemberOverview(BaseModel):
    connection: ConnectionPublic
    user: UserSummary
    session: Optional[SessionPublic]


class ScanResult(BaseModel):
    flagged: bool
    description: str
    category: Optional[str] = None
    warning_active: bool
    points_awarded: int
    points_lost: int
    currency: int
    shutdown: bool
    analysis_failed: bool = False


class HealthResponse(BaseModel):
    status: str
    ai_backend: str


def to_public(model: type[BaseModel], obj: Any) -> Any:
    return model.model_validate(obj, from_attributes=True)
