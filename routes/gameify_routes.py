# routes/gamify_routes.py

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from fastapi_config import get_session
from models.models import Reward, RewardType
from services.gameify_service import Gameify, MaxedCurrencyError, add_reward
from services.user_service import UserService

router = APIRouter(prefix="/gameify", tags=["Gameify & Rewards"])
gameify_service = Gameify()
user_service = UserService()


# ------------------------------------------------------------------------------
# Request Schemas
# ------------------------------------------------------------------------------
class UpdatePointsRequest(BaseModel):
    amount: int = Field(..., ge=0)


class AddPointsRequest(BaseModel):
    amount: int = Field(..., gt=0)


class RemovePointsRequest(BaseModel):
    amount: int = Field(..., gt=0)


class CreateRewardRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    reward_amount: int = Field(..., gt=0)
    reward_cost: int = Field(..., gt=0)
    reward_type: RewardType = RewardType.GIFT_CARD


class BuyRefundRewardRequest(BaseModel):
    reward_id: str


# ------------------------------------------------------------------------------
# Points Management Endpoints
# ------------------------------------------------------------------------------
@router.put("/users/{user_id}/points")
def set_user_points(
    user_id: str,
    payload: UpdatePointsRequest,
    session: Session = Depends(get_session),
):
    user = user_service.get_user_by_id(session, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found",
        )

    gameify_service.update_points(session=session, user=user, amount=payload.amount)
    return {"message": "Points updated successfully", "currency": user.currency}


@router.post("/users/{user_id}/points/add")
def add_user_points(
    user_id: str,
    payload: AddPointsRequest,
    session: Session = Depends(get_session),
):
    user = user_service.get_user_by_id(session, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found",
        )

    try:
        gameify_service.add_points(session=session, user=user, amount=payload.amount)
    except MaxedCurrencyError as ex:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ex))

    return {"message": "Points added successfully", "currency": user.currency}


@router.post("/users/{user_id}/points/remove")
def remove_user_points(
    user_id: str,
    payload: RemovePointsRequest,
    session: Session = Depends(get_session),
):
    user = user_service.get_user_by_id(session, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found",
        )

    if user.currency < payload.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient currency balance to deduct this amount",
        )

    gameify_service.remove_points(session=session, user=user, amount=payload.amount)
    return {"message": "Points removed successfully", "currency": user.currency}


# ------------------------------------------------------------------------------
# Reward Store Endpoints
# ------------------------------------------------------------------------------
@router.get("/rewards")
def get_all_rewards(session: Session = Depends(get_session)):
    return session.exec(select(Reward)).all()


@router.get("/rewards/{reward_id}")
def get_reward_by_id(reward_id: str, session: Session = Depends(get_session)):
    reward = gameify_service.get_reward(session, reward_id=reward_id)
    if not reward:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reward '{reward_id}' not found",
        )
    return reward


@router.post("/rewards", status_code=status.HTTP_201_CREATED)
def create_new_reward(
    payload: CreateRewardRequest,
    session: Session = Depends(get_session),
):
    try:
        add_reward(
            session=session,
            name=payload.name,
            reward_amount=payload.reward_amount,
            reward_cost=payload.reward_cost,
            reward_type=payload.reward_type,
        )
    except ValueError as ex:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ex))

    return {"message": f"Reward '{payload.name}' successfully created"}


@router.post("/users/{user_id}/rewards/buy")
def buy_reward(
    user_id: str,
    payload: BuyRefundRewardRequest,
    session: Session = Depends(get_session),
):
    user = user_service.get_user_by_id(session, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found",
        )

    success, msg = gameify_service.buy_reward(
        session=session, user=user, reward_id=payload.reward_id
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    return {"message": msg, "currency": user.currency}


@router.post("/users/{user_id}/rewards/refund")
def refund_reward(
    user_id: str,
    payload: BuyRefundRewardRequest,
    session: Session = Depends(get_session),
):
    user = user_service.get_user_by_id(session, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found",
        )

    success, msg = gameify_service.refund_reward(
        session=session, user=user, reward_id=payload.reward_id
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    return {"message": "Reward refunded successfully", "currency": user.currency}