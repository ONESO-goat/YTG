from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel, Field
from sqlmodel import Session

from agent.bot import ScreenClassifier
from db import get_session
from helpers import clock
from helpers.config import Config
from helpers.security import get_current_user
from models.models import Guardian, User
from models.schemas import GameEvent, ScanResult, SessionPublic
from routes.deps import accessible_session, can_be_monitored_by, guardian_for
from services.errors import Forbidden, NotFound, ServiceError
from services.progress_service import ProgressService
from services.session_services import YTGSessionService

router = APIRouter(prefix="/sessions", tags=["Monitoring Sessions"])
dev_router = APIRouter(prefix="/dev", tags=["Development"])

session_service = YTGSessionService()
classifier = ScreenClassifier(Config.ai_backend)

MAX_SCAN_BYTES = 15 * 1024 * 1024


class StartSessionRequest(BaseModel):
    # Defaults to the guardian the current user belongs to
    guardian_id: str | None = None


class StartSessionResponse(BaseModel):
    session: SessionPublic
    events: list[GameEvent]


class GrantRequest(BaseModel):
    points: int = Field(default=0, ge=0, le=100_000)
    xp: int = Field(default=0, ge=0, le=100_000)


class SimulateRequest(BaseModel):
    category: str = Field(default="hate speech", min_length=1, max_length=60)
    scans: int = Field(default=8, ge=0, le=100)


def _monitoring_guardian(session: Session, user: User, guardian_id: str | None) -> Guardian:
    if guardian_id is None:
        guardian, _ = guardian_for(session, user)
        if not guardian:
            raise ServiceError("You aren't part of a guardian yet")
    else:
        guardian = session.get(Guardian, guardian_id)
    if not guardian or not can_be_monitored_by(session, guardian, user):
        raise Forbidden("You can't start a session under this guardian")
    return guardian


@router.get("/me", response_model=SessionPublic | None)
def get_my_session(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return session_service.get_users_session(session=session, user=user)


@router.post("/start", response_model=StartSessionResponse)
def start_session(
    payload: StartSessionRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    guardian = _monitoring_guardian(session, user, payload.guardian_id)
    ytg_session, outcome = session_service.start_session(session, user, guardian)
    return StartSessionResponse(session=SessionPublic.model_validate(ytg_session), events=outcome.events)


@router.post("/{session_id}/stop", response_model=SessionPublic)
def stop_session(
    session_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)
):
    return session_service.stop_session(session, accessible_session(session, session_id, user))


@router.get("/{session_id}", response_model=SessionPublic)
def get_session_by_id(
    session_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)
):
    return accessible_session(session, session_id, user)


# A plain `def` so FastAPI runs it in a worker thread: the AI call can take seconds and would
# otherwise block every other request
@router.post("/{session_id}/scan", response_model=ScanResult)
def process_scan(
    session_id: str,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    ytg_session = accessible_session(session, session_id, user)
    if ytg_session.user_id != user.id:
        raise Forbidden("Only the monitored user can send scans")

    image_bytes = file.file.read(MAX_SCAN_BYTES + 1)
    if not image_bytes:
        raise ServiceError("Uploaded file is empty")
    if len(image_bytes) > MAX_SCAN_BYTES:
        raise ServiceError("Screenshot is too large", status_code=413)
    return session_service.process_scan(session, classifier, ytg_session, image_bytes)


# ------------------------------------------------------------------------------
# Development helpers, only available while the AI is stubbed
# ------------------------------------------------------------------------------
def _require_stub():
    if classifier.backend != "stub":
        raise NotFound("Not available with a real AI backend")


@dev_router.post("/simulate", dependencies=[Depends(_require_stub)])
def simulate_flagged_content(payload: SimulateRequest, user: User = Depends(get_current_user)):
    """Make the next `scans` scans of the current user come back flagged. 0 clears it."""
    if payload.scans == 0:
        classifier.stub.clear(user.id)
    else:
        classifier.stub.simulate(user.id, payload.category, payload.scans)
    return {"remaining": classifier.stub.remaining(user.id), "category": payload.category}


@dev_router.post("/grant", dependencies=[Depends(_require_stub)])
def grant(
    payload: GrantRequest, user: User = Depends(get_current_user), session: Session = Depends(get_session)
):
    """Give the current user points and XP, to try out levels and the shop without waiting."""
    outcome = ProgressService().grant(session, user, clock.now(), payload.points, payload.xp)
    session.commit()
    return {"currency": user.currency, "events": outcome.events}
