from models.models import (Guardian, 
                           User, 
                           GuardianType, 
                           GuardianReport, 
                           GuardianSettings, 
                           STRICTNESS_MULTIPLIERS,
                           default_restrictions_on_creation)

from models.guardian_session import GuardianSession
from .reports_service import create_report
from .guardian_services import GuardianServices
import time
from .gameify_service import Gameify
from sqlmodel import Session, select
from agent.bot import ScreenClassifier
import random
from datetime import datetime

guardian_services = GuardianServices()
gameify_service = Gameify()
STILL_VIEWING_THRESHOLD_SECONDS = 30 
ALERT_COUNT_THRESHOLD = 5 

class YTGSessionService:
    
    def turn_off_guardian(self, session:Session, guardian_id:str)->tuple[bool, str]:
            """Turn off the guardian. When turned off, the sessions are automatically deleted"""
            guardian_data, mes = guardian_services.get_guardian_data(session, guardian_id=guardian_id)
                    
            guardian = guardian_data.get("guardian")
            
            if not guardian:
                return False, mes
                    
            if not guardian.on:
                return False, "Guardian is already off"
            
            sessions = self.get_all_sessions_under_guardian(session=session, guardian=guardian)
            if not sessions:
                guardian.on = False
                session.commit()
                return True, "No sessions found under the guardian. Turned off"
            
            # sess_count = 0
            # for running_session in sessions:
            #     session.delete(running_session)
            #     sess_count += 1
            guardian.on = False
            session.commit()
            session.refresh(guardian)
            return True, f"Guardian is now off, removed {len(sessions)} sessions"
                    
    def turn_on_guardian(self, session:Session, guardian_id:str)->tuple[list[GuardianSession]|None, str]:
            """Turn on the guardian. When turned on, the sessions are automatically set"""
            try:
                guardian_data, mes = guardian_services.get_guardian_data(session, guardian_id=guardian_id)
                
                guardian = guardian_data.get("guardian")
        
                if not guardian:
                    return None, mes
                
                if guardian.on:
                    return None, f"Guardian is already running: {guardian.on}"
                
                
                connections = guardian_services.get_all_connections(session=session, guardian=guardian)
                new_sessions = []
                for connection in connections:
                    user = session.get(User, connection.user_id)
                    if not user:
                        continue
                    s, was_created = self.get_or_create(
                        session=session,
                        user=user, 
                        guardian=guardian
                    )
                    s.active = True
                    new_sessions.append(s)
                guardian.on = True
         
                session.commit()
                session.refresh(guardian)
                return new_sessions, f"{len(new_sessions)} new sessions set"
            
            except Exception as ex:
                session.rollback()
                raise ex

    def get_all_sessions(self, session:Session):
        statement = select(GuardianSession)
        return session.exec(statement).all()
    
    def get_all_sessions_under_guardian(self, session:Session, guardian):
        return session.exec(
            select(GuardianSession)
            .where(GuardianSession.guardian_id == guardian.id)).all()
    
    def get_YTGSession(self, session:Session, session_id:str)->tuple[GuardianSession|None, str]:
        if not session or not session_id:
            return None, "Session and ID are required"
        sess = session.get(GuardianSession, session_id)
        if not sess:
            return None, f"No session under the id '{session_id}'"
        return sess, "success"
    
    def get_or_create(self, session: Session, user: 'User', guardian: 'Guardian') -> tuple[GuardianSession,bool]:
        existing = session.exec(
            select(GuardianSession).where(
                GuardianSession.user_id == user.id,
                GuardianSession.guardian_id == guardian.id,
            )
        ).first()
        if existing:
            session.refresh(existing)
            return existing, False

        row = GuardianSession(user_id=user.id, guardian_id=guardian.id)
        session.add(row)
        session.commit()
        session.refresh(row)
        return row, True

    def end_of_the_day_disprute_guardian(self, session:Session, guardian:Guardian):
        try:
            if not guardian:
                return False,"Guardian is required"
            
            all_sessions = self.get_all_sessions_under_guardian(session=session, guardian=guardian)
            if not all_sessions:
                return True, "empty List"
            
            for sess in all_sessions:
                user = session.get(User, sess.user_id)
                if not user:
                    continue
                #points = sess.points_pending
                total_warning_count = sess.total_alerts
                warnings_ignored_count = sess.amount_of_warnings_ignored
                warnings_listened_count = sess.amount_of_warnings_listened
                
                result = gameify_service.compute_daily_settlement(
                    avoided_count=warnings_listened_count,
                    ignored_count=warnings_ignored_count,
                    amount_of_warnings=total_warning_count
                )
                gameify_service.add_points(session=session, user=user, amount=result.get("totoal", 0))
                sess.reset()
            session.commit()
            session.refresh(guardian)
        except Exception as ex:
            session.rollback()
            raise ValueError(f"Dangerous error occured during session daily reset: {ex}")
        
    def end_of_the_day_disprute_all(self, session:Session):
            try:
                
                all_sessions = self.get_all_sessions(session=session)
                if not all_sessions:
                    return True, "empty List"
                count = 0
                
                for sess in all_sessions:
                   
                    time.sleep(0.1)
                    user = session.get(User, sess.user_id)
                    if not user:
                        continue
                    total_warning_count = sess.total_alerts
                    warnings_ignored_count = sess.amount_of_warnings_ignored
                    warnings_listened_count = sess.amount_of_warnings_listened
                    
                    result = gameify_service.compute_daily_settlement(
                        avoided_count=warnings_listened_count,
                        ignored_count=warnings_ignored_count,
                        amount_of_warnings=total_warning_count
                    )
                    gameify_service.add_points(session=session, user=user, amount=result.get("total", 0))
                    sess.reset()
                    count+=1
                session.commit()
                return count
  
            except Exception as ex:
                session.rollback()
                raise ValueError(f"CRITIAL Dangerous error occured during session daily reset: {ex}")
            
            
    def get_users_session(self, session:Session, user: 'User'):
        statement = session.exec(select(GuardianSession).where(GuardianSession.user_id == user.id)).first()
        return statement
    
    def process_scan(
        self,
        session: Session,
        classifer: ScreenClassifier,
        session_row: GuardianSession,
        image_bytes: bytes,
    ) -> dict:
        stuff, mes = guardian_services.get_guardian_data(
            session=session, 
            guardian_id=session_row.guardian_id
            )
        
        guardian:Guardian|None = stuff.get("guardian")
        if not guardian:
            raise ValueError("Guardian does not exist during session process")

        settings = stuff.get("settings")
        restrictions = stuff.get("restrictions")
            
            
        classification = classifer.engine._classify_image(image_bytes=image_bytes, return_json=True)
        if restrictions:
            active_restrictions = [*restrictions.default_restrictions, *restrictions.restrictions]
        else:
            active_restrictions = default_restrictions_on_creation()
            
        overview = classifer.overview(
            image_overview=classification.get("summary", ""),
            guardian_settings=settings or None,
            guardian_restrictions=active_restrictions)
        
        overview["image_summary"] = classification

        was_already_warning = session_row.warning_active

        user = session.get(User, session_row.user_id)
        if not user or not settings:
            raise ValueError("User or settings are missing during scanning process")
        
        penalty_applied = 0
        if overview["flagged"]:
            session_row.warning_active = True
            session_row.tracking_start_at = None
            session_row.total_alerts += 1
            session_row.minute_timer = None
            
            if not was_already_warning:
                is_family_account = guardian.guardian_type == GuardianType.FAMILY
                # If it's a family account, include the name of the person in this alert. 
                # If its individual, skip the name.
                # This is for parents or caregivers to know who is facing the issue,
                # while individual people dont have to see their name spammed through out
                    
                breakdown = classifer._breakdown_overview(
                    user=user, 
                    classification_result=overview, 
                    include_name=is_family_account)
                
                self.add_event(session=session, content=breakdown, sm_row=session_row)
                if settings and settings.reports_enabled:
                    create_report(session=session,guardian=guardian,content=breakdown)
                    
                penalty_applied = self.apply_point_penalty_if_needed(
                session=session, 
                sm_row=session_row, 
                guardian_settings=settings, 
                user=user)
            
                
                
        elif was_already_warning:
            # If the user wasnt flagged and already has a warning, start the timer on how long
            # they avoid this type of content
            
            # session_row.tracking_start_at = datetime.utcnow()
            # session_row.target_duration_seconds = 180
            self.start_avoidance_timer(session, session_row)
        
        completed = False
        if not overview['flagged'] and not was_already_warning:
            # If the user havent faced any warning or flags, a minute timer is set that rewards th user 10 points
            # this means the user can get 600 points per hour if 100% clean
            if session_row.minute_timer is None:
                session_row.minute_timer = datetime.now()
            if session_row.minute_passed() and session_row.points_gain_daily_limit >= 10:
                gameify_service.add_points(session=session, user=user, amount=10)
                session_row.minute_timer = datetime.now()
                session_row.points_gain_daily_limit -= 10
                completed = True
        else:     
            completed = self.update_and_check_timer(session=session, sm_row=session_row)

        session.commit()

        return {
            "flagged": overview["flagged"],
            "description": overview.get("description"),
            "warning_active": session_row.warning_active,
            "points_awarded": completed,
            "points_lost": penalty_applied
        }
    
    def update_and_check_timer(self, session:Session, sm_row: 'GuardianSession'):
            """Runs silently inside your main loop to check the stopwatch status."""
            if not sm_row.warning_active or sm_row.tracking_start_at is None:
                return False
    
            elapsed = (datetime.utcnow() - sm_row.tracking_start_at).total_seconds()
            if elapsed >= sm_row.target_duration_seconds:
                user = session.get(User, sm_row.user_id)
                if not user:
                    return False
                sm_row.warning_active = False
                sm_row.tracking_start_at = None
                if sm_row.points_gain_daily_limit <= 0:
                    session.commit()
                    return True # Reached daily limt
                sm_row.points_gain_daily_limit -= 25
                user.currency += 25
                session.commit()
                return True
            return False
        
    def delete_session(self, session:Session, session_id:str):
        """_summary_

        Session auto delete after cycles. GuardianSessions are the connection between the user and the 
        agent. This is called when the user logs out, away for some time, etc.
        
        Args:
            session (Session): the session
            session_id (str): GuardianSession id
        """
        sess, mes = self.get_YTGSession(session=session, session_id=session_id)
        if not sess:
            return None, mes
        session.delete(sess)
        session.commit()
        
    def trigger_warning(self, sm_row: GuardianSession) -> None:
        if not sm_row.warning_active:
            sm_row.warning_started_at = datetime.utcnow()
            sm_row.penalized_this_episode = False
        sm_row.warning_active = True
        sm_row.tracking_start_at = None

    def start_avoidance_timer(self, session:Session, sm_row: GuardianSession, target_seconds: int = 2) -> None:
        """For testing, 2-3 seconds"""
        if sm_row.warning_active and sm_row.tracking_start_at is None:
            sm_row.tracking_start_at = datetime.utcnow()
            sm_row.target_duration_seconds = target_seconds
            session.commit()
            
    def add_event(self, 
                  session:Session, 
                  sm_row:GuardianSession, 
                  content:str, 
                  time_duration:int|None=None):
            if time_duration is None:
                time_duration = random.randint(140, 300)
            sm_row.events.append({
                "content": content,
                "should_avoid": True,
                "time_to_wait":  time_duration
            })
            session.commit()
            
    def flush_wipe_events(self, session:Session, sm_row: "GuardianSession"):
            """If the user ignores the agents warning, it just wipes out the events"""
            if len(sm_row.events) <= 0:
                return
            
            guardian = session.get(Guardian, sm_row.guardian_id)
            if not guardian:
                raise ValueError(f"Guardian of id '{sm_row.guardian_id}' does not exist")
            
            owner = guardian.owner
            for event in sm_row.events:
                recap = GuardianReport(
                    content=event['content'],
                    send_to=owner
                )
                session.add(recap)
            
            sm_row.total_alerts = 0
            sm_row.events = []
            session.commit()
            
            
    def apply_point_penalty_if_needed(
        self, session: Session, sm_row: GuardianSession, guardian_settings: GuardianSettings, user: User
    ) -> int:
        """Returns points actually deducted (0 if none)."""
        if not guardian_settings.points_loss_enabled:
            return 0
        if sm_row.penalized_this_episode:
            return 0  # already penalized for this specific warning episode

        still_viewing = (
            sm_row.warning_active
            and sm_row.tracking_start_at is not None
            and (datetime.utcnow() - sm_row.tracking_start_at).total_seconds() >= STILL_VIEWING_THRESHOLD_SECONDS
        )
        too_many_alerts = sm_row.total_alerts >= ALERT_COUNT_THRESHOLD

        if not (still_viewing or too_many_alerts):
            return 0

        multiplier = STRICTNESS_MULTIPLIERS.get(guardian_settings.strictness, 1.5)
        penalty = round(guardian_settings.base_points_lost * multiplier)

        actual_deducted = min(penalty, user.currency)  # floor at 0, never go negative
        if actual_deducted > 0:
            gameify_service.remove_points(session=session, user=user, amount=actual_deducted)

        sm_row.penalized_this_episode = True
        session.add(sm_row)
        session.commit()
        return actual_deducted