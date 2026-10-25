from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel
from sqlalchemy.ext.mutable import MutableList
from sqlmodel import JSON, Column, Field, Relationship, SQLModel

from .helper import create_id, create_number_id, utcnow_naive


def default_restrictions_on_creation() -> list[str]:
    return [
        # Original safety categories
        "hate speech",
        "violence",
        "gore",
        "extreme ideologies",
        # Harassment and toxicity
        "harassment",
        "bullying",
        "doxxing",
        # Security and guardrail bypasses
        "prompt injection",
        "jailbreak",
        "system prompt extraction",
        # Harmful and illegal content
        "self-harm",
        "illegal acts",
        "weapons manufacturing",
    ]


class Messages(BaseModel):
    warning: str = "Hey, I see that this content seems harmful. Please avoid it!"
    applause: str = "Great work friend! We are proud of you"


class AvailableLanguages(Enum):
    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    DUTCH = "nl"
    RUSSIAN = "ru"
    CHINESE = "zh"
    JAPANESE = "ja"
    KOREAN = "ko"


class StrictnessLevel(Enum):
    WEAK = "weak"
    NORMAL = "normal"
    HARSH = "harsh"


STRICTNESS_MULTIPLIERS = {
    StrictnessLevel.WEAK.value: 1.2,
    StrictnessLevel.NORMAL.value: 1.5,
    StrictnessLevel.HARSH.value: 2.0,
}


class UserType(Enum):
    CAREGIVER = "caregiver"
    INDIVIDUAL = "individual"
    DEPENDENT = "dependent"


class GuardianType(Enum):
    FAMILY = "family"
    PERSONAL = "personal"
    DEPENDENT = "dependent"


class RewardType(Enum):
    GIFT_CARD = "gift_card"
    STREAK_FREEZE = "streak_freeze"


class RelationshipType(Enum):
    OFFSPRING = "offspring"
    FRIEND = "friend"
    SUPERVISOR = "supervisor"
    IS_OWNER = "owner"


class Reward(SQLModel, table=True):
    id: str = Field(default_factory=create_id, primary_key=True)
    name: str
    type: RewardType
    amount: int
    cost: int


class UserSettings(SQLModel, table=True):
    __tablename__ = "user_settings"

    id: str = Field(default_factory=create_id, primary_key=True)
    language: str = Field(default=AvailableLanguages.ENGLISH.value)

    user_id: str | None = Field(default=None, foreign_key="user.id", unique=True)
    user: Optional["User"] = Relationship(back_populates="settings")


class User(SQLModel, table=True):
    id: str = Field(default_factory=create_id, primary_key=True)
    number_id: int = Field(default_factory=create_number_id, unique=True)

    username: str = Field(index=True)
    name: str
    email: str = Field(index=True)
    password: str
    user_type: UserType = Field(default=UserType.INDIVIDUAL)
    # Bumped on password change; tokens issued before that stop working
    token_version: int = Field(default=0)

    currency: int = Field(default=0)

    settings: Optional["UserSettings"] = Relationship(back_populates="user")
    connections: list["GuardianConnection"] = Relationship(back_populates="user")
    guardian: Optional["Guardian"] = Relationship(back_populates="owner")
    rewards: list["UserWonReward"] = Relationship(back_populates="user")


class UserWonReward(SQLModel, table=True):
    id: str = Field(default_factory=create_id, primary_key=True)
    order_id: int = Field(default_factory=create_number_id, unique=True)

    user_id: str = Field(default=None, foreign_key="user.id", index=True)
    user: Optional["User"] = Relationship(back_populates="rewards")

    reward_id: str = Field(default=None, foreign_key="reward.id")
    reward: Optional["Reward"] = Relationship()
    purchased_at: datetime | None = Field(default=None, nullable=True)


class GuardianReport(SQLModel, table=True):
    id: str = Field(default_factory=create_id, primary_key=True)

    content: str

    guardian_id: str | None = Field(default=None, foreign_key="guardian.id", index=True)

    send_to_id: str | None = Field(default=None, foreign_key="user.id")
    send_to: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "GuardianReport.send_to_id"}
    )

    updated_at: date = Field(default_factory=date.today)
    created_at: datetime | None = Field(default_factory=utcnow_naive, nullable=True)


class Guardian(SQLModel, table=True):
    id: str = Field(default_factory=create_id, primary_key=True)

    name: str
    guardian_type: GuardianType = Field(default=GuardianType.PERSONAL)

    owner_id: str | None = Field(default=None, foreign_key="user.id", index=True)
    owner: Optional["User"] = Relationship(back_populates="guardian")
    on: bool = Field(default=False)
    connections: list["GuardianConnection"] = Relationship(back_populates="guardian")

    guardian_settings: Optional["GuardianSettings"] = Relationship(back_populates="guardian")

    restrictions: Optional["GuardianRestrictions"] = Relationship(back_populates="guardian")


class GuardianConnection(SQLModel, table=True):
    __tablename__ = "guardian_connection"

    id: str = Field(default_factory=create_id, primary_key=True)

    guardian_id: str = Field(default=None, foreign_key="guardian.id", index=True)
    guardian: Optional["Guardian"] = Relationship(back_populates="connections")

    user_id: str = Field(default=None, foreign_key="user.id", index=True)
    user_name: str = Field(default=None)
    user: Optional["User"] = Relationship(back_populates="connections")

    relationship_with_owner: RelationshipType = Field(default=RelationshipType.IS_OWNER)


class GuardianSettings(SQLModel, table=True):
    __tablename__ = "guardian_settings"

    id: str = Field(default_factory=create_id, primary_key=True)

    strictness: str = Field(default=StrictnessLevel.NORMAL.value)
    language: str = Field(default=AvailableLanguages.ENGLISH.value)
    custom_warning_messages: dict = Field(default_factory=lambda: Messages().model_dump(), sa_type=JSON)
    # Ignoring a warning costs points unless the guardian owner turns it off
    points_loss_enabled: bool = Field(default=True)
    base_points_lost: int = Field(default=5)
    reports_enabled: bool = Field(default=True)

    guardian_id: str | None = Field(default=None, foreign_key="guardian.id", unique=True)
    guardian: Optional["Guardian"] = Relationship(back_populates="guardian_settings")


class GuardianRestrictions(SQLModel, table=True):
    __tablename__ = "guardian_restrictions"

    id: str = Field(default_factory=create_id, primary_key=True)

    guardian_id: str | None = Field(default=None, foreign_key="guardian.id", unique=True)
    guardian: Optional["Guardian"] = Relationship(back_populates="restrictions")

    default_restrictions: list = Field(
        default_factory=default_restrictions_on_creation,
        sa_column=Column(MutableList.as_mutable(JSON)),
    )
    restrictions: list = Field(default_factory=list, sa_column=Column(MutableList.as_mutable(JSON)))

    is_active: bool = Field(default=True)
    updated_at: date = Field(default_factory=date.today)
