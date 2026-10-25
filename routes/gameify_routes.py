from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from fastapi_config import get_session
from helpers.security import get_current_user, require_admin
from models.models import Reward, RewardType, User, UserWonReward
from models.schemas import OwnedRewardPublic, RewardPublic
from routes.deps import bad_request, not_found
from services.gameify_service import Gameify, MaxedCurrencyError, add_reward

router = APIRouter(prefix="/gameify", tags=["Gameify & Rewards"])
gameify_service = Gameify()


class PointsRequest(BaseModel):
    amount: int = Field(..., ge=0)


class CreateRewardRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    reward_amount: int = Field(..., ge=0)
    reward_cost: int = Field(..., gt=0)
    reward_type: RewardType = RewardType.GIFT_CARD


# ------------------------------------------------------------------------------
# Shop
# ------------------------------------------------------------------------------
@router.get("/rewards", response_model=list[RewardPublic])
def list_rewards(_: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return session.exec(select(Reward).order_by(Reward.cost)).all()


@router.get("/me/rewards", response_model=list[OwnedRewardPublic])
def my_rewards(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    owned = session.exec(select(UserWonReward).where(UserWonReward.user_id == user.id)).all()
    return [
        OwnedRewardPublic(id=o.id, order_id=o.order_id, reward=RewardPublic.model_validate(o.reward))
        for o in owned
        if o.reward
    ]


@router.post("/rewards/{reward_id}/buy")
def buy_reward(reward_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    success, msg = gameify_service.buy_reward(session=session, user=user, reward_id=reward_id)
    if not success:
        raise bad_request(msg)
    return {"message": msg, "currency": user.currency}


@router.post("/rewards/{reward_id}/refund")
def refund_reward(reward_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    try:
        success, msg = gameify_service.refund_reward(session=session, user=user, reward_id=reward_id)
    except MaxedCurrencyError as ex:
        raise bad_request(str(ex))
    if not success:
        raise bad_request(msg)
    return {"message": "Reward refunded", "currency": user.currency}


# ------------------------------------------------------------------------------
# Admin (X-Admin-Key)
# ------------------------------------------------------------------------------
@router.post("/rewards", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_reward(payload: CreateRewardRequest, session: Session = Depends(get_session)):
    try:
        add_reward(
            session=session,
            name=payload.name,
            reward_amount=payload.reward_amount,
            reward_cost=payload.reward_cost,
            reward_type=payload.reward_type,
        )
    except ValueError as ex:
        raise bad_request(str(ex))
    return {"message": f"Reward '{payload.name}' created"}


@router.put("/users/{user_id}/points", dependencies=[Depends(require_admin)])
def set_user_points(user_id: str, payload: PointsRequest, session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise not_found(f"User '{user_id}' not found")
    gameify_service.update_points(session=session, user=user, amount=payload.amount)
    return {"currency": user.currency}
