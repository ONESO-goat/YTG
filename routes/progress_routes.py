from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from db import get_session
from helpers import clock
from helpers.security import get_current_user
from models.models import GuardianType, User, UserType
from models.progress import UserProgress
from models.schemas import AchievementPublic, Leaderboard, LeaderboardEntry, ProgressSummary
from routes.deps import guardian_for
from services.errors import NotFound, ServiceError
from services.guardian_services import GuardianServices
from services.progress_service import ProgressService, level_for_xp, valid_timezone

router = APIRouter(prefix="/progress", tags=["Progress"])
progress_service = ProgressService()
guardian_service = GuardianServices()

LEADERBOARD_SIZE = 20


class PreferencesRequest(BaseModel):
    timezone: str | None = Field(default=None, max_length=64)
    show_on_leaderboard: bool | None = None


@router.get("/me", response_model=ProgressSummary)
def my_progress(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    summary = progress_service.summary(session, user, clock.now())
    session.commit()
    return summary


@router.get("/me/achievements", response_model=list[AchievementPublic])
def my_achievements(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    achievements = progress_service.achievements(session, user)
    session.commit()
    return achievements


@router.patch("/me/preferences", response_model=ProgressSummary)
def update_preferences(
    payload: PreferencesRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    progress = progress_service.progress(session, user)
    if payload.timezone is not None:
        if not valid_timezone(payload.timezone):
            raise ServiceError(f"Unknown timezone '{payload.timezone}'")
        progress.timezone = payload.timezone
    if payload.show_on_leaderboard is not None:
        if payload.show_on_leaderboard and user.user_type == UserType.DEPENDENT:
            raise ServiceError("Family members can only appear on their family's leaderboard")
        progress.show_on_leaderboard = payload.show_on_leaderboard
    session.commit()
    return progress_service.summary(session, user, clock.now())


def _family_member_ids(session: Session, user: User) -> list[str] | None:
    guardian, _ = guardian_for(session, user)
    if not guardian or guardian.guardian_type != GuardianType.FAMILY:
        return None
    return [c.user_id for c in guardian_service.get_connections(session, guardian)]


@router.get("/leaderboard", response_model=Leaderboard)
def leaderboard(
    scope: Literal["family", "global"] = Query(default="global"),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    progress_service.progress(session, user)  # so the current user always has a row
    if scope == "family":
        ids = _family_member_ids(session, user)
        if ids is None:
            raise NotFound("You aren't part of a family guardian")
        visible = user.id in ids
    else:
        rows = session.exec(
            select(UserProgress.user_id)
            .join(User, User.id == UserProgress.user_id)  # type: ignore[arg-type]
            .where(UserProgress.show_on_leaderboard == True, User.user_type != UserType.DEPENDENT)  # noqa: E712
        ).all()
        ids = list(rows)
        visible = user.id in ids

    now = clock.now()
    weekly = progress_service.weekly_xp(session, list({*ids, user.id}), now.date())
    users = {u.id: u for u in session.exec(select(User).where(User.id.in_({*ids, user.id}))).all()}  # type: ignore[attr-defined]
    progress_rows = {
        p.user_id: p
        for p in session.exec(select(UserProgress).where(UserProgress.user_id.in_({*ids, user.id}))).all()  # type: ignore[attr-defined]
    }

    def entry(user_id: str, rank: int) -> LeaderboardEntry:
        u = users[user_id]
        p = progress_rows.get(user_id) or UserProgress(user_id=user_id)
        streak = progress_service.streak_view(p, progress_service.local_day(p, now))["current"]
        return LeaderboardEntry(
            rank=rank,
            name=u.name,
            username=u.username,
            level=level_for_xp(p.xp),
            weekly_xp=weekly.get(user_id, 0),
            streak=streak,
            is_me=user_id == user.id,
        )

    ranked = sorted(
        (uid for uid in ids if uid in users), key=lambda uid: (-weekly.get(uid, 0), users[uid].name.lower())
    )
    entries = [entry(uid, i + 1) for i, uid in enumerate(ranked[:LEADERBOARD_SIZE])]
    me_entry = None
    if not any(e.is_me for e in entries):
        my_rank = ranked.index(user.id) + 1 if user.id in ranked else 0
        me_entry = entry(user.id, my_rank)
    session.commit()
    return Leaderboard(scope=scope, entries=entries, me=me_entry, visible=visible)
