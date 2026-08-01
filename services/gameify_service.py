from models.models import User, Reward, UserWonReward, RewardType, CreatedFirstFewRewards
import time
from sqlmodel import Session
from sqlmodel import Session, select, func
import random

class MaxedCurrencyError(Exception):
    pass

class Gameify:
    def update_points(self, session:Session, user:User, amount:int):
        user.currency = amount
        session.commit()
        
    def add_points(self, session:Session, user:User, amount:int):
        if user.currency > 100000:
            raise MaxedCurrencyError("User reached the maxed amount of currency")
        user.currency += amount
        session.commit()
        
    def remove_points(self, session:Session, user:User, amount:int):
        user.currency = max(0, user.currency - amount)
        session.commit()
        
    def get_reward(self, session:Session, reward_id:str):
        return session.get(Reward, reward_id)
    
    def refund_reward(self, session:Session, user:'User', reward_id:str):
        if not user or not reward_id:
            return False, "User and reward id are required"
        
        reward = self.get_reward(session, reward_id=reward_id)
        if not reward:
            return False, f"{reward_id} does not exist"

        
        won_reward = session.exec(select(UserWonReward).where(
            UserWonReward.user_id==user.id,
            UserWonReward.reward_id==reward.id)).first()
        if not won_reward:
            return False, f"User doesnt have this item"
        
        self.add_points(session=session, user=user, amount=int(reward.cost/1.2))
        session.delete(won_reward)
        session.commit()
        return True, "success"
    
    def buy_reward(self, session:Session, user:'User', reward_id:str):
        if not user or not reward_id:
            return False, "User and reward id are required"
        
        reward = self.get_reward(session, reward_id=reward_id)
        if not reward:
            return False, f"'{reward_id}' does not exist"
        
        if not self.can_afford(user, reward):
            return False, f"Cannot affrod item"
        
        won_reward = UserWonReward(
            user=user,
            reward=reward
        )
        self.remove_points(session=session, user=user, amount=reward.cost)
        session.add(won_reward)
        session.commit()
        return True, f"{user.username} bought {reward.name} for {reward.cost}"
        
    def compute_daily_settlement(
        self,
        avoided_count: int,
        ignored_count: int,
        amount_of_warnings: int,
        daily_baseline: int = 1000,
        per_avoidance_bonus: int = 25,
        avoided_decay: float = 0.04,   # % multiplier lost per avoided warning
        ignored_decay: float = 0.12,   # % multiplier lost per ignored warning
        multiplier_floor: float = 0.05,
        streak_bonus_per_day: int = 20,
        streak_days: int = 0,
    ) -> dict:
        raw_points = avoided_count * per_avoidance_bonus

        decay = (avoided_count * avoided_decay) + (ignored_count * ignored_decay)
        multiplier = max(multiplier_floor, 1.0 - decay)

        baseline_component = round(daily_baseline * multiplier)
        streak_component = min(streak_days, 10) * streak_bonus_per_day  # cap so it doesn't run away
        
        if amount_of_warnings in [0,1]:
            total_alerts_reward = 100
        elif amount_of_warnings >= 10:
            total_alerts_reward = 0
        else:
            c = ((( amount_of_warnings * 100 ) / 100) * 10) + 10
            total_alerts_reward = max(0, 100 - c)
        
        total = raw_points + baseline_component + streak_component + total_alerts_reward
        return {
            "raw_points": raw_points,
            "multiplier": multiplier,
            "baseline_component": baseline_component,
            "streak_component": streak_component,
            "total": total,
        }
        
    def can_afford(self, user:'User', reward: 'Reward'):
        return user.currency >= reward.cost
    
    def _card_activation_code(self):
        """We are using a fake appilication, so for now well make fake gift cards"""
        return random.randint(1,10)




def _add_rewards(session:Session):
    """Adding the test rewards for MVP"""

    if not session:
        raise ValueError("Session is required")
    already_done = session.get(CreatedFirstFewRewards, 1)
    if already_done:
        return
    try:
        starters = [
            ("$5 gift card of your choice!", RewardType.GIFT_CARD, 5, 310000), 
            ("$25 gift card of your choice!", RewardType.GIFT_CARD, 25, 1820000),
            ("$100 gift card of your choice!", RewardType.GIFT_CARD, 100, 3650000),
            ("Streak freeze", RewardType.STREAK_FREEZE, 0, 10000)
           
            ]
        for reward in starters:
            time.sleep(0.1)
            reward_name  = reward[0]
            reward_type = reward[1]
            reward_amount = reward[2]
            reward_cost = reward[3]

            session.add(
                Reward(
                    name=reward_name,
                    type=reward_type,
                    amount=reward_amount,
                    cost=reward_cost
                )
            )
        n = CreatedFirstFewRewards()
        session.add(n)
        session.commit()
    except Exception as ex:
        session.rollback()
        raise ValueError(f"An error occured when adding rewards to system: {ex}")

def add_reward(session:Session, name:str, reward_amount:int, reward_cost:int, reward_type:str|RewardType=RewardType.GIFT_CARD):
    if not session:
        raise ValueError("Session is required")
    
    if reward_type not in RewardType:
        raise ValueError(f"{reward_type} is not available")
    try:

        session.add(
                Reward(
                    name=name,
                    type=RewardType(reward_type),
                    amount=reward_amount,
                    cost=reward_cost
                )
            )
        session.commit()
    except Exception as ex:
        session.rollback()
        raise ValueError(f"An error occured when adding rewards to system: {ex}")