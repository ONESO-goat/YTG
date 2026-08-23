# routes/session_routes.py


from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlmodel import Session

from agent.bot import ScreenClassifier
from fastapi_config import get_session
from models.guardian_session import GuardianSession
from services.guardian_services import GuardianServices
from services.user_service import UserService
from services.session_services import YTGSessionService

router = APIRouter(prefix="/sessions", tags=["Guardian Sessions"])

session_service = YTGSessionService()
guardian_service = GuardianServices()
user_service = UserService()

# Instantiate the ScreenClassifier (can also be passed via dependency injection if needed)
classifier = ScreenClassifier("ollama")


# ------------------------------------------------------------------------------
# Request Schemas
# ------------------------------------------------------------------------------
class CreateSessionRequest(BaseModel):
    user_id: str
    guardian_id: str


class AddEventRequest(BaseModel):
    content: str
    time_duration: int | None = None


@router.get("/")
def fetch_all_session(session:Session=Depends(get_session)):
    return session_service.get_all_sessions(session=session)
# ------------------------------------------------------------------------------
# Session Endpoints
# ------------------------------------------------------------------------------
@router.post("/create", status_code=status.HTTP_201_CREATED)
def get_or_create_session(
    payload: CreateSessionRequest,
    session: Session = Depends(get_session),
):
    user = user_service.get_user_by_id(session, user_id=payload.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{payload.user_id}' not found",
        )

    guardian = guardian_service.get_guardian_by_id(
        session, guardian_id=payload.guardian_id
    )
    if not guardian:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Guardian '{payload.guardian_id}' not found",
        )

    ytg_session = session_service.get_or_create(
        session=session, user=user, guardian=guardian
    )
    return ytg_session


@router.get("/{session_id}")
def get_session_by_id(session_id: str, session: Session = Depends(get_session)):
    ytg_session, msg = session_service.get_YTGSession(
        session=session, session_id=session_id
    )
    if not ytg_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
    return ytg_session

@router.get("/user/get/{user_id}")
def get_users_session(user_id: str, session: Session = Depends(get_session)):
    user = user_service.get_user_by_id(
        session=session, user_id=user_id
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"User under id '{user_id}' does not exist"
        )
    
    users_sessions = session_service.get_users_session(session=session, user=user)
    if not users_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"User has no session"
        )
    return users_sessions


@router.get("/guardian/{guardian_id}")
def get_sessions_by_guardian(
    guardian_id: str,
    session: Session = Depends(get_session),
):
    guardian = guardian_service.get_guardian_by_id(session, guardian_id=guardian_id)
    if not guardian:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Guardian '{guardian_id}' not found",
        )

    return session_service.get_all_sessions_under_guardian(
        session=session, guardian=guardian
    )


@router.post("/{guardian_id}/on")
def turn_guardian_on(guardian_id:str, session:Session=Depends(get_session)):
    
    new_sessions, mes = session_service.turn_on_guardian(session=session, guardian_id=guardian_id)
    if new_sessions is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=mes)
    return new_sessions

@router.post("/{guardian_id}/off")
def turn_guardian_off(guardian_id:str, session:Session=Depends(get_session)):
    
    successful, mes = session_service.turn_off_guardian(session=session, guardian_id=guardian_id)
    if not successful:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=mes)
    return {"message": mes}

@router.delete("/{session_id}")
def delete_session(session_id: str, session: Session = Depends(get_session)):
    sess, msg = session_service.get_YTGSession(session=session, session_id=session_id)
    if not sess:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)

    session_service.delete_session(session=session, session_id=session_id)
    return {"message": f"Session '{session_id}' successfully deleted"}


# ------------------------------------------------------------------------------
# Image Processing & Event Flow
# ------------------------------------------------------------------------------
@router.post("/{session_id}/scan")
async def process_scan(
    session_id: str,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    ytg_session, msg = session_service.get_YTGSession(
        session=session, session_id=session_id
    )
    if not ytg_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty"
        )

    try:
        scan_result = session_service.process_scan(
            session=session,
            classifier=classifier,
            session_row=ytg_session,
            image_bytes=image_bytes,
        )
    except ValueError as ex:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ex))

    return scan_result


@router.post("/{session_id}/events")
def add_event(
    session_id: str,
    payload: AddEventRequest,
    session: Session = Depends(get_session),
):
    ytg_session, msg = session_service.get_YTGSession(
        session=session, session_id=session_id
    )
    if not ytg_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)

    session_service.add_event(
        session=session,
        sm_row=ytg_session,
        content=payload.content,
        time_duration=payload.time_duration,
    )
    return {"message": "Event added successfully", "events": ytg_session.events}


@router.post("/{session_id}/flush")
def flush_events(session_id: str, session: Session = Depends(get_session)):
    ytg_session, msg = session_service.get_YTGSession(
        session=session, session_id=session_id
    )
    if not ytg_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)

    try:
        session_service.flush_wipe_events(session=session, sm_row=ytg_session)
    except ValueError as ex:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ex))

    return {"message": "Events flushed and converted into reports successfully"}