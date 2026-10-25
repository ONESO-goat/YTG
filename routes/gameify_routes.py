from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from db import get_session
from helpers.security import get_current_user, require_admin
from models.models import Reward, RewardType, User, UserWonReward
from models.schemas import OwnedRewardPublic, PurchaseResult, RewardPublic
from services.errors import NotFound
from services.gameify_service import REFUND_WINDOW, Gameify, add_reward

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
    return session.exec(select(Reward).order_by(Reward.cost)).all()  # type: ignore[arg-type]


@router.get("/me/rewards", response_model=list[OwnedRewardPublic])
def my_rewards(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    owned = session.exec(
        select(UserWonReward)
        .where(UserWonReward.user_id == user.id)
        .order_by(UserWonReward.purchased_at.desc())  # type: ignore[union-attr]
    ).all()
    return [
        OwnedRewardPublic(
            id=o.id,
            order_id=o.order_id,
            reward=RewardPublic.model_validate(o.reward),
            purchased_at=o.purchased_at,
            refundable_until=o.purchased_at + REFUND_WINDOW if o.purchased_at else None,
        )
        for o in owned
        if o.reward
    ]


@router.post("/rewards/{reward_id}/buy", response_model=PurchaseResult)
def buy_reward(
    reward_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)
):
    outcome = gameify_service.buy_reward(session=session, user=user, reward_id=reward_id)
    return PurchaseResult(message="Purchase complete", currency=user.currency, events=outcome.events)


@router.post("/me/rewards/{owned_id}/refund", response_model=PurchaseResult)
def refund_reward(
    owned_id: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)
):
    amount = gameify_service.refund_reward(session=session, user=user, owned_id=owned_id)
    return PurchaseResult(message=f"Refunded {amount} points", currency=user.currency, events=[])


# ------------------------------------------------------------------------------
# Admin (X-Admin-Key)
# ------------------------------------------------------------------------------
@router.post(
    "/rewards",
    status_code=status.HTTP_201_CREATED,
    response_model=RewardPublic,
    dependencies=[Depends(require_admin)],
)
def create_reward(payload: CreateRewardRequest, session: Session = Depends(get_session)):
    return add_reward(session, payload.name, payload.reward_amount, payload.reward_cost, payload.reward_type)


@router.put("/users/{user_id}/points", dependencies=[Depends(require_admin)])
def set_user_points(user_id: str, payload: PointsRequest, session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise NotFound("User not found")
    gameify_service.set_points(session=session, user=user, amount=payload.amount)
    return {"currency": user.currency}
