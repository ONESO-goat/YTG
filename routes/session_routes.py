from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlmodel import Session

from agent.bot import ScreenClassifier
from fastapi_config import get_session
from helpers.config import Config
from helpers.security import get_current_user, require_admin
from models.models import Guardian, User
from models.schemas import ScanResult, SessionPublic
from routes.auth import build_me
from routes.deps import accessible_session, bad_request, can_be_monitored_by, forbidden
from services.session_services import SessionInactiveError, YTGSessionService

router = APIRouter(prefix="/sessions", tags=["Monitoring Sessions"])
dev_router = APIRouter(prefix="/dev", tags=["Development"])

session_service = YTGSessionService()
classifier = ScreenClassifier(Config.ai_backend)

MAX_SCAN_BYTES = 15 * 1024 * 1024


class StartSessionRequest(BaseModel):
    # Defaults to the guardian the current user belongs to
    guardian_id: str | None = None


class SimulateRequest(BaseModel):
    category: str = Field(default="hate speech", min_length=1, max_length=60)
    scans: int = Field(default=8, ge=0, le=100)


def _monitoring_guardian(session: Session, user: User, guardian_id: str | None) -> Guardian:
    if guardian_id is None:
        me = build_me(session, user)
        if not me.guardian:
            raise bad_request("You aren't part of a guardian yet")
        guardian_id = me.guardian.id
    guardian = session.get(Guardian, guardian_id)
    if not guardian or not can_be_monitored_by(session, guardian, user):
        raise forbidden("You can't start a session under this guardian")
    return guardian


@router.get("/me", response_model=SessionPublic | None)
def get_my_session(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return session_service.get_users_session(session=session, user=user)


@router.post("/start", response_model=SessionPublic)
def start_session(
    payload: StartSessionRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    guardian = _monitoring_guardian(session, user, payload.guardian_id)
    if not guardian.on:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Monitoring is turned off for this guardian")
    ytg_session, _ = session_service.get_or_create(session=session, user=user, guardian=guardian)
    ytg_session.start()
    session.commit()
    session.refresh(ytg_session)
    return ytg_session


@router.post("/{session_id}/stop", response_model=SessionPublic)
def stop_session(session_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    ytg_session = accessible_session(session, session_id, user)
    ytg_session.end()
    session.commit()
    session.refresh(ytg_session)
    return ytg_session


@router.get("/{session_id}", response_model=SessionPublic)
def get_session_by_id(session_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return accessible_session(session, session_id, user)


@router.post("/{session_id}/scan", response_model=ScanResult)
async def process_scan(
    session_id: str,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    ytg_session = accessible_session(session, session_id, user)
    if ytg_session.user_id != user.id:
        raise forbidden("Only the monitored user can send scans")

    image_bytes = await file.read(MAX_SCAN_BYTES + 1)
    if not image_bytes:
        raise bad_request("Uploaded file is empty")
    if len(image_bytes) > MAX_SCAN_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Screenshot is too large")

    try:
        return session_service.process_scan(
            session=session, classifier=classifier, session_row=ytg_session, image_bytes=image_bytes
        )
    except SessionInactiveError as ex:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(ex))
    except ValueError as ex:
        raise bad_request(str(ex))


@router.post("/settle", dependencies=[Depends(require_admin)])
def settle_all_sessions(session: Session = Depends(get_session)):
    """End-of-day settlement: turn each session's day into points and reset its counters."""
    try:
        count = session_service.end_of_the_day_disprute_all(session)
    except ValueError as ex:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(ex))
    return {"message": f"{count} sessions settled"}


# ------------------------------------------------------------------------------
# Development helpers, only available while the AI is stubbed
# ------------------------------------------------------------------------------
def _require_stub():
    if classifier.backend != "stub":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not available with a real AI backend")


@dev_router.post("/simulate", dependencies=[Depends(_require_stub)])
def simulate_flagged_content(payload: SimulateRequest, user: User = Depends(get_current_user)):
    """Make the next `scans` scans of the current user come back flagged. 0 clears it."""
    if payload.scans == 0:
        classifier.stub.clear(user.id)
    else:
        classifier.stub.simulate(user.id, payload.category, payload.scans)
    return {"remaining": classifier.stub.remaining(user.id), "category": payload.category}
