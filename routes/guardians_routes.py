# routes/guardians_routes.py


from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session

from fastapi_config import get_session
from models.models import GuardianType, UserType, RelationshipType
from services.guardian_services import GuardianServices
from services.user_service import UserService

router = APIRouter(prefix="/guardians", tags=["Guardians"])
guardian_service = GuardianServices()
user_service = UserService()


# ------------------------------------------------------------------------------
# Request Schemas
# ------------------------------------------------------------------------------
class CreateGuardianRequest(BaseModel):
    owner_id: str
    name: str = Field(..., min_length=1, max_length=120)
    guardian_type: GuardianType = GuardianType.PERSONAL


class AddConnectionRequest(BaseModel):
    user_id_or_username: str
    relationship: RelationshipType

class DeleteReportRequest(BaseModel):
    user_id:str
class AddConnectionRequestNumberId(BaseModel):
    user_number_id: int
    relationship: RelationshipType

class ChangeCodeRequest(BaseModel):
    code: int

class NewRestriction(BaseModel):
    restriction: str
class UpdateGuardianSettingsRequest(BaseModel):
    warning_message: str | None = None
    applause_message: str | None = None
    strictness: str | None = None
    reports_enabled: bool | None = None
    points_loss_enabled: bool
    base_points_lost: int


# ------------------------------------------------------------------------------
# Guardian Management Endpoints
# ------------------------------------------------------------------------------
@router.get("/all")
def get_all_guardians(session: Session = Depends(get_session)):
    return guardian_service.get_all_guardians(session)


@router.post("/create", status_code=status.HTTP_201_CREATED)
def create_guardian(
    payload: CreateGuardianRequest, 
    session: Session = Depends(get_session)
):
    user = user_service.get_user_by_id(session, user_id=payload.owner_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"User '{payload.owner_id}' not found"
        )

    guardian, msg = guardian_service.create_guardian(
        session=session,
        user=user,
        name=payload.name,
        guardian_type=payload.guardian_type,
    )

    if not guardian:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    return guardian


@router.get("/{guardian_id}")
def get_guardian(guardian_id: str, session: Session = Depends(get_session)):
    guardian = guardian_service.get_guardian_by_id(session, guardian_id=guardian_id)
    if not guardian:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Guardian '{guardian_id}' does not exist: {guardian.owner_id if guardian else 'actually isnt there'}",
        )
    return guardian


@router.get("/owner/{user_id}")
def get_guardian_by_owner(user_id: str, session: Session = Depends(get_session)):
    user = user_service.get_user_by_id(session, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"User '{user_id}' not found"
        )

    guardian = guardian_service.get_guardian_by_owner(session, user=user)
    if not guardian:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No Guardian found for owner '{user_id}'",
        )
    return guardian


@router.delete("/{guardian_id}")
def delete_guardian(guardian_id: str, session: Session = Depends(get_session)):
    success, msg = guardian_service.delete_guardian(
        session=session, guardian_id=guardian_id
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    return {"message": f"Guardian '{guardian_id}' successfully deleted"}


# ------------------------------------------------------------------------------
# Connections Endpoints
# ------------------------------------------------------------------------------
@router.get("/{guardian_id}/connections")
def get_guardian_connections(
    guardian_id: str, 
    session: Session = Depends(get_session)
):
    guardian = guardian_service.get_guardian_by_id(session, guardian_id=guardian_id)
    if not guardian:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Guardian '{guardian_id}' does not exist",
        )

    return guardian_service.get_all_connections(session, guardian=guardian)


@router.post("/{guardian_id}/connections/add", status_code=status.HTTP_201_CREATED)
def add_connection(
    guardian_id: str,
    payload: AddConnectionRequestNumberId,
    session: Session = Depends(get_session),
):
    guardian = guardian_service.get_guardian_by_id(session, guardian_id=guardian_id)
    if not guardian:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Guardian '{guardian_id}' does not exist",
        )
    
    user = user_service.get_user_by_number_id(session=session, number_id=payload.user_number_id)
    # user = user_service.get_user_by_username(session, username=payload.user_number_id)
    # if not user:
    #     user = user_service.get_user_by_id(session, user_id=payload.user_id_or_username)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{payload.user_number_id}' does not exist",
        )

    connection, msg = guardian_service.add_connection(
        session=session,
        guardian=guardian,
        user=user,
        connection_type=payload.relationship,
    )
    if not connection:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    return connection


@router.delete("/{guardian_id}/connections/{user_id}")
def remove_connection(
    guardian_id: str, 
    user_id: str|int, 
    session: Session = Depends(get_session)
):
    guardian = guardian_service.get_guardian_by_id(session, guardian_id=guardian_id)
    if not guardian:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Guardian '{guardian_id}' does not exist",
        )

    if isinstance(user_id, int):
        user = user_service.get_user_by_number_id(session, number_id=user_id)
    else:
        user = user_service.get_user_by_id(session, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' does not exist",
        )

    success, msg = guardian_service.remove_connection(
        session=session, guardian=guardian, user=user
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    return {"message": f"Connection between Guardian '{guardian_id}' and user '{user_id}' removed"}


# ------------------------------------------------------------------------------
# Settings & Security Endpoints
# ------------------------------------------------------------------------------
@router.put("/{guardian_id}/code")
def change_guardian_code(
    guardian_id: str,
    payload: ChangeCodeRequest,
    session: Session = Depends(get_session),
):
    guardian = guardian_service.get_guardian_by_id(session, guardian_id=guardian_id)
    if not guardian:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Guardian '{guardian_id}' does not exist",
        )

    updated_guardian, msg = guardian_service.change_code(
        session=session, guardian=guardian, code=payload.code
    )
    if not updated_guardian:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    return updated_guardian


@router.post("/{guardian_id}/restrictions/remove")
def remove_restriction(
    guardian_id:str,
    payload: NewRestriction,
    session:Session=Depends(get_session)
):
    restrictions, mes = guardian_service.remove_from_guardian_restrictions(session=session,
                                                  guardian_id=guardian_id,
                                                  restriction=payload.restriction)
    if restrictions is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=mes)
    return restrictions

@router.post("/{guardian_id}/restrictions/add")
def add_restriction(
    guardian_id:str,
    payload: NewRestriction,
    session:Session=Depends(get_session)
):
    restrictions, mes = guardian_service.add_to_guardian_restrictions(session=session,
                                                  guardian_id=guardian_id,
                                                  restriction=payload.restriction)
    if restrictions is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=mes)
    return restrictions

@router.get("/{guardian_id}/settings")
def get_guardian_settings(
    guardian_id: str, 
    session: Session = Depends(get_session)
):
    guardian = guardian_service.get_guardian_by_id(session, guardian_id=guardian_id)
    if not guardian:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Guardian '{guardian_id}' does not exist",
        )

    settings, msg = guardian_service.get_or_create_guardian_settings(
        session=session, guardian=guardian
    )
    if not settings:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    return settings


@router.patch("/{guardian_id}/settings/update")
def update_guardian_settings(
    guardian_id: str,
    payload: UpdateGuardianSettingsRequest,
    session: Session = Depends(get_session),
):
    guardian = guardian_service.get_guardian_by_id(session, guardian_id=guardian_id)
    if not guardian:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Guardian '{guardian_id}' does not exist",
        )

    settings, msg = guardian_service.update_guardian_settings(
        session=session,
        guardian=guardian,
        warning_message=payload.warning_message,
        applause_message=payload.applause_message,
        strictness=payload.strictness,
        apply_penalty=payload.points_loss_enabled,
        enable_reports=payload.reports_enabled,
        amount_of_points_to_lose=payload.base_points_lost
    )
    if not settings:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    return settings


@router.get("/restrictions/get/{guardian_id}")
def fetch_restrictions(guardian_id:str, session:Session=Depends(get_session)):
    guardian = guardian_service.get_guardian_by_id(session=session, guardian_id=guardian_id)
    if not guardian:
        raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Guardian '{guardian_id}' does not exist",
            )
    restrictions, mes = guardian_service.get_or_create_guardian_restrictions(session=session, guardian=guardian)
    if not restrictions:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=mes)
    
    return restrictions.restrictions

@router.get("/reports/{given_id}")
def get_reports(given_id:str, session:Session=Depends(get_session)):
    reports, mes = guardian_service.get_reports_by_guardian_id(session=session, guardian_id=given_id)
    if reports is None:
        reports, mes = guardian_service.get_reports_by_owner_id(session=session, owner_id=given_id)
        if reports is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"The given id '{given_id}' is not associated with any guardian or user. DETAILS: {mes}")
    return reports

@router.get("/reports/get/{report_id}")
def fetch_report(report_id:str, session:Session=Depends(get_session)):
    report, mes = guardian_service.get_report(session=session, report_id=report_id)
    if not report:
        raise HTTPException(
            status_code=404,
            detail=mes
        )
    return report

@router.delete("/reports/delete/{report_id}")
def fetch_delete_report(report_id:str, user_making_request:DeleteReportRequest, session:Session=Depends(get_session)):
    user = user_service.get_user_by_id(session=session, user_id=user_making_request.user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User of id '{user_making_request.user_id}' does not exist"
        )
    sucess, mes = guardian_service.delete_report_by_id(session=session, user_making_request_id=user.id, report_id=report_id)
    if not sucess:
        raise HTTPException(
            status_code=400,
            detail=mes
        )
    return "Successfully removed report"