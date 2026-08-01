from sqlmodel import SQLModel, Field, Relationship, JSON, Column
from .helper import create_id, create_number_id
from sqlalchemy.ext.mutable import MutableList
from enum import Enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


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

class CreatedFirstFewRewards(SQLModel, table=True):
    code: int = Field(default=1, primary_key=True)
    yes: bool = Field(default=True)

class UserSettings(SQLModel, table=True):
    __tablename__ = "user_settings"

    id: str = Field(default_factory=create_id, primary_key=True)
    language: str = Field(default=AvailableLanguages.ENGLISH.value)

    user_id: Optional[str] = Field(default=None, foreign_key="user.id", unique=True)
    user: Optional["User"] = Relationship(back_populates="settings")


class UserHistory(SQLModel, table=True):
    __tablename__ = "user_history"

    id: str = Field(default_factory=create_id, primary_key=True)

    user_id: Optional[str] = Field(default=None, foreign_key="user.id", unique=True)
    user: Optional["User"] = Relationship(back_populates="history")


class User(SQLModel, table=True):
    id: str = Field(default_factory=create_id, primary_key=True)
    number_id: int = Field(default_factory=create_number_id, unique=True)

    username: str
    name: str
    email: str
    password: str
    user_type: UserType = Field(default=UserType.INDIVIDUAL)

    currency: int = Field(default=0)

    settings: Optional["UserSettings"] = Relationship(back_populates="user")

    history: Optional["UserHistory"] = Relationship(back_populates="user")

    connections: list["GuardianConnection"] = Relationship(back_populates="user")
    guardian: Optional["Guardian"] = Relationship(back_populates="owner")
    rewards: list["UserWonReward"] = Relationship(back_populates="user")

    device_ip: Optional["DeviceID"] = Relationship(
        back_populates="user"
    )

    recent_activity: Optional["RecentActivity"] = Relationship(back_populates="user")


class UserWonReward(SQLModel, table=True):
    id: str = Field(default_factory=create_id, primary_key=True)
    order_id: int = Field(default_factory=create_number_id, unique=True)

    user_id: str = Field(default=None, foreign_key="user.id")
    user: Optional["User"] = Relationship(back_populates="rewards")

    reward_id: str = Field(default=None, foreign_key="reward.id")
    reward: Optional["Reward"] = Relationship()


class GuardianReport(SQLModel, table=True):
    id: str = Field(default_factory=create_id, primary_key=True)

    content: str 
    
    guardian_id: Optional[str] = Field(default=None, foreign_key="guardian.id")
    
    send_to_id: Optional[str] = Field(default=None, foreign_key="user.id")
    send_to: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "GuardianReport.send_to_id"}
    )
    
    timestamp: datetime = Field(default=datetime.now().today())


class Guardian(SQLModel, table=True):
    id: str = Field(default_factory=create_id, primary_key=True)

    name: str
    guardian_type: GuardianType = Field(default=GuardianType.PERSONAL)

    owner_id: Optional[str] = Field(default=None, foreign_key="user.id")
    owner: Optional["User"] = Relationship(back_populates="guardian")
    code: Optional[int] = Field(default=None)
    on: bool = Field(default=False)
    connections: list["GuardianConnection"] = Relationship(back_populates="guardian")

    guardian_settings: Optional["GuardianSettings"] = Relationship(back_populates="guardian")

    restrictions: Optional["GuardianRestrictions"] = Relationship(back_populates="guardian")


class GuardianConnection(SQLModel, table=True):
    __tablename__ = "guardian_connection"

    id: str = Field(default_factory=create_id, primary_key=True)

    guardian_id: str = Field(default=None, foreign_key="guardian.id")
    guardian: Optional["Guardian"] = Relationship(back_populates="connections")

    user_id: str = Field(default=None, foreign_key="user.id")
    user_name: str = Field(default=None)
    user: Optional["User"] = Relationship(back_populates="connections")
    
    relationship_with_owner: RelationshipType = Field(default=RelationshipType.IS_OWNER)


class GuardianSettings(SQLModel, table=True):
    __tablename__ = "guardian_settings"

    id: str = Field(default_factory=create_id, primary_key=True)

    strictness: str = Field(default=StrictnessLevel.NORMAL.value)
    language: str = Field(default=AvailableLanguages.ENGLISH.value)
    custom_warning_messages: dict = Field(default_factory=lambda: Messages().model_dump(), sa_type=JSON)
    points_loss_enabled: bool = Field(default=False)
    base_points_lost: int = Field(default=5)
    
    guardian_id: Optional[str] = Field(default=None, foreign_key="guardian.id", unique=True)
    guardian: Optional["Guardian"] = Relationship(back_populates="guardian_settings")


class DeviceID(SQLModel, table=True):
    __tablename__ = "device_ip"

    id: str = Field(default_factory=create_id, primary_key=True)
    ip_address: Optional[str] = Field(default=None)
    
    user_id: Optional[str] = Field(default=None, foreign_key="user.id", unique=True)
    user: Optional["User"] = Relationship(
        back_populates="device_ip"
    )


class GuardianRestrictions(SQLModel, table=True):
    __tablename__ = "guardian_restrictions"

    id: str = Field(default_factory=create_id, primary_key=True)

    guardian_id: Optional[str] = Field(default=None, foreign_key="guardian.id", unique=True)
    guardian: Optional["Guardian"] = Relationship(back_populates="restrictions")
   
    restrictions: list = Field(
        default_factory=list, 
        sa_column=Column(MutableList.as_mutable(JSON)))


class RecentActivity(SQLModel, table=True):
    __tablename__ = "recent_activity"

    id: str = Field(default_factory=create_id, primary_key=True)

    user_id: Optional[str] = Field(default=None, foreign_key="user.id")
    user: Optional["User"] = Relationship(back_populates="recent_activity")

    activities: list = Field(default_factory=list, sa_type=JSON)