from datetime import datetime, timedelta, timezone

from sqlalchemy import update
from sqlmodel import Session, select

from models.models import Reward, RewardType, User, UserWonReward
from .progress_service import MAX_STREAK_FREEZES, Outcome, ProgressService

progress_service = ProgressService()

REFUND_WINDOW = timedelta(hours=24)
# Refunds return this share of the cost, so buying and refunding can't be used to shuffle points around
REFUND_RATE = 5 / 6

# The starter catalog. A dedicated, engaged user earns roughly 700-800 points a day
# (see services/progress_service.py), so a $5 card is about a month of good habits.
STARTER_REWARDS = [
    ("Streak freeze", RewardType.STREAK_FREEZE, 0, 500),
    ("$5 gift card of your choice!", RewardType.GIFT_CARD, 5, 20_000),
    ("$25 gift card of your choice!", RewardType.GIFT_CARD, 25, 95_000),
    ("$100 gift card of your choice!", RewardType.GIFT_CARD, 100, 360_000),
]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ShopError(Exception):
    pass


class Gameify:
    def set_points(self, session: Session, user: User, amount: int):
        user.currency = amount
        session.commit()

    def get_reward(self, session: Session, reward_id: str) -> Reward | None:
        return session.get(Reward, reward_id)

    def _spend(self, session: Session, user: User, amount: int) -> None:
        """Deduct points in one conditional UPDATE, so two purchases racing each other can't overspend."""
        result = session.exec(  # type: ignore[call-overload]
            update(User)
            .where(User.id == user.id, User.currency >= amount)  # type: ignore[arg-type]
            .values(currency=User.currency - amount)
        )
        if result.rowcount != 1:
            raise ShopError("You don't have enough points for this")
        session.refresh(user)

    def buy_reward(self, session: Session, user: User, reward_id: str) -> Outcome:
        reward = self.get_reward(session, reward_id)
        if not reward:
            raise ShopError("That reward doesn't exist")

        progress = progress_service.progress(session, user)
        if reward.type == RewardType.STREAK_FREEZE and progress.streak_freezes >= MAX_STREAK_FREEZES:
            raise ShopError(f"You can hold at most {MAX_STREAK_FREEZES} streak freezes")

        self._spend(session, user, reward.cost)
        if reward.type == RewardType.STREAK_FREEZE:
            # Freezes go straight into the streak, there is nothing to hold on to
            progress.streak_freezes += 1
        else:
            session.add(UserWonReward(user_id=user.id, reward_id=reward.id, purchased_at=_utcnow()))
        outcome = progress_service.record_purchase(session, user, _utcnow())
        session.commit()
        session.refresh(user)
        return outcome

    def refund_reward(self, session: Session, user: User, owned_id: str) -> int:
        """Refund an owned reward bought within the refund window. Returns the points given back."""
        owned = session.get(UserWonReward, owned_id)
        if not owned or owned.user_id != user.id or not owned.reward:
            raise ShopError("You don't own that reward")
        if owned.purchased_at is None or _utcnow() - owned.purchased_at > REFUND_WINDOW:
            raise ShopError("Rewards can only be refunded within 24 hours of buying them")

        amount = int(owned.reward.cost * REFUND_RATE)
        user.currency += amount
        session.delete(owned)
        session.commit()
        session.refresh(user)
        return amount


def sync_starter_rewards(session: Session) -> None:
    """Make sure the starter catalog exists with current prices. Rewards are matched by name."""
    existing = {r.name: r for r in session.exec(select(Reward)).all()}
    for name, reward_type, amount, cost in STARTER_REWARDS:
        reward = existing.get(name)
        if reward is None:
            session.add(Reward(name=name, type=reward_type, amount=amount, cost=cost))
        else:
            reward.type, reward.amount, reward.cost = reward_type, amount, cost
    session.commit()


def add_reward(session: Session, name: str, reward_amount: int, reward_cost: int, reward_type: RewardType = RewardType.GIFT_CARD):
    try:
        session.add(Reward(name=name, type=RewardType(reward_type), amount=reward_amount, cost=reward_cost))
        session.commit()
    except Exception as ex:
        session.rollback()
        raise ValueError(f"Could not add reward: {ex}")
