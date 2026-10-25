"""Response shapes sent to the frontend. These never include password hashes."""

from datetime import date, datetime

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
    owner_id: str | None
    on: bool


class ConnectionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    guardian_id: str
    user_id: str
    user_name: str | None
    relationship_with_owner: RelationshipType


class SessionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    guardian_id: str
    active: bool
    warning_active: bool
    last_scan_at: datetime | None
    created_at: datetime


class ReportPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    content: str
    guardian_id: str | None
    send_to_id: str | None
    updated_at: date
    created_at: datetime | None


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
    purchased_at: datetime | None
    refundable_until: datetime | None


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class MeResponse(BaseModel):
    user: UserPublic
    # The guardian the user owns, or for dependents the guardian they are connected to
    guardian: GuardianPublic | None
    is_guardian_owner: bool
    connection: ConnectionPublic | None


class GameEvent(BaseModel):
    # level_up | achievement | goal | streak | freeze_used
    type: str
    title: str
    description: str
    icon: str
    points: int = 0
    xp: int = 0


class StreakInfo(BaseModel):
    current: int
    best: int
    freezes: int
    max_freezes: int
    done_today: bool
    at_risk: bool


class TodayStats(BaseModel):
    day: date
    clean_minutes: int
    goal_minutes: int
    goal_completed: bool
    minute_points: int
    minute_points_cap: int
    avoidance_bonuses_left: int
    points_earned: int
    points_lost: int
    xp_earned: int
    warnings_total: int
    warnings_heeded: int
    warnings_ignored: int


class ProgressSummary(BaseModel):
    level: int
    title: str
    xp: int
    xp_into_level: int
    xp_for_next_level: int
    streak: StreakInfo
    today: TodayStats
    show_on_leaderboard: bool
    timezone: str


class AchievementPublic(BaseModel):
    code: str
    name: str
    description: str
    icon: str
    points: int
    target: int
    progress: int
    unlocked_at: datetime | None


class LeaderboardEntry(BaseModel):
    rank: int
    name: str
    username: str
    level: int
    weekly_xp: int
    streak: int
    is_me: bool


class Leaderboard(BaseModel):
    scope: str
    entries: list[LeaderboardEntry]
    # Set when the current user isn't among `entries`
    me: LeaderboardEntry | None
    # False when the user can't appear on this board (opted out, or a dependent on the global board)
    visible: bool


class MemberOverview(BaseModel):
    connection: ConnectionPublic
    user: UserSummary
    session: SessionPublic | None
    progress: ProgressSummary


class ScanResult(BaseModel):
    flagged: bool
    description: str
    category: str | None = None
    warning_active: bool
    points_awarded: int
    points_lost: int
    xp_awarded: int
    currency: int
    events: list[GameEvent]
    shutdown: bool
    # The screen hasn't changed since the last scan
    idle: bool = False
    analysis_failed: bool = False


class PurchaseResult(BaseModel):
    message: str
    currency: int
    events: list[GameEvent]


class HealthResponse(BaseModel):
    status: str
    ai_backend: str
