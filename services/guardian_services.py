from models.models import (GuardianConnection, 
                           User, 
                           Guardian, 
                           UserType, 
                           GuardianSettings, 
                           GuardianRestrictions, 
                           GuardianType,
                           RelationshipType,
                           GuardianReport,
                           default_restrictions_on_creation
                           )
from .reports_service import create_report, delete_report
from sqlmodel import Session, select, func
from typing import Any


class GuardianServices:
    
    def get_guardian_data(self, session:Session, guardian_id: str)->tuple[dict[str,Any], str]:
        """Get guardian, guardian settings, guardian restrictions"""
        
        guardian = self.get_guardian_by_id(session, guardian_id=guardian_id)
        if not guardian:
            return {
                "guardian": None,
                "settings": None,
                "restrictions": None
                }, f"Guadian with id '{guardian_id}' not found"
            
        settings, _ = self.get_or_create_guardian_settings(session, guardian=guardian)
        restrictions, _ = self.get_or_create_guardian_restrictions(session=session, guardian=guardian)
        return {
                "guardian": guardian,
                "settings": settings,
                "restrictions": restrictions
            }, "success"
        
        
        
        
    def get_all_guardians(self, session:Session):
        statement = select(Guardian)
        return session.exec(statement).all()
    
    def get_all_connections(self, session:Session, guardian:Guardian):
        if not guardian:
            raise ValueError("Guardian is required")
        return session.exec(
            select(GuardianConnection).where(GuardianConnection.guardian_id == guardian.id)
        ).all()
        
    def validate_connection(self, session:Session, guardian:Guardian, user:User):
        if not guardian or not user:
            raise ValueError("Guardian and user are required")
        return session.exec(
            select(GuardianConnection).where(
                GuardianConnection.guardian_id == guardian.id,
                GuardianConnection.user_id == user.id
            )
        ).first()

    def get_guardian_by_owner(self, session:Session, user:User):
        if not user:
            return None
        return session.exec(
            select(Guardian).where(Guardian.owner_id == user.id)
        ).first()
        
    def get_guardian_by_id(self, session:Session, guardian_id:str):
        if not guardian_id:
            return None
        return session.get(Guardian, guardian_id)
    
    def create_guardian(self, session:Session, user:User, name:str, guardian_type:GuardianType=GuardianType.PERSONAL):
        if not user:
            return None, "User is required"
        
        if not name or not guardian_type:
            return None, "Guardian name and type are required"

        if user.user_type == UserType.DEPENDENT:
            return None, "Cannot make guardian as a DEPENDENT"
        
        if self.get_guardian_by_owner(session, user=user):
            return None, "User already owns a Guardian"

        guardian = Guardian(
            name=name,
            owner_id=user.id,
            guardian_type=guardian_type

        )
        session.add(guardian)
        session.flush()  # populates Guardian.id
        settings = GuardianSettings(guardian=guardian)
        restrictions = GuardianRestrictions(guardian=guardian)
        
        guardian.guardian_settings = settings
        guardian.restrictions = restrictions
        
        session.add_all([settings, restrictions])
        session.commit()
        
        create_report(
            session=session, 
            guardian=guardian, 
            content=f"I am pleased to guide you away from the horrors that await in our journey {user.name.capitalize()}!")
        session.refresh(guardian)
        return guardian, "success"
    
    def delete_guardian(self, session:Session, guardian_id:str):
        try:
            guardian = self.get_guardian_by_id(session=session, guardian_id=guardian_id)
            if not guardian:
                return False, f"Guardian {guardian_id} does not exist"
            all_connections = session.exec(
                select(GuardianConnection).where(GuardianConnection.guardian_id == guardian.id)
            ).all()
            for connection in all_connections:
                session.delete(connection)
            settings = session.exec(
                select(GuardianSettings).where(GuardianSettings.guardian_id == guardian.id)
            ).first()
            if settings:
                session.delete(settings)
                
            restrictions = session.exec(
                select(GuardianRestrictions).where(GuardianRestrictions.guardian_id == guardian.id)
            ).first()
            if restrictions:
                session.delete(restrictions)

            session.delete(guardian)
            session.commit()
            return True, "success"
        except Exception as ex:
            session.rollback()
            raise ex
    
    def change_guardian_type(self,session, guardian:Guardian, new_type:GuardianType)->tuple[Guardian|None, str]:
        if not guardian or new_type:
            return None, "Guardian and typing is required"
        guardian.guardian_type = new_type
        session.commit()
        return guardian, "success"
    
    def add_connection(self, session:Session, guardian:Guardian, user:User, connection_type:RelationshipType):
        if not guardian or not user:
            return None, "Guardian and user are required"
        
        if guardian.guardian_type == GuardianType.PERSONAL:
            return None, "Cannot add connections for personal accounts"
                    
        if len(self.get_all_connections(session=session, guardian=guardian)) >= 7:
            return None, "Maximum number of connections reached for this Guardian"
        
        if connection_type not in RelationshipType:
            return None, f"Invalid connection type: {connection_type}"
        
        if session.exec(
            select(GuardianConnection).where(
                GuardianConnection.guardian_id == guardian.id,
                GuardianConnection.user_id == user.id
            )
        ).first():
            return None, f"Connection already exists between Guardian '{guardian.id}' and user '{user.id}'"
        
        connection = GuardianConnection(
            guardian=guardian,
            user=user,
            user_name=user.name,
            relationship_with_owner=connection_type
        )
        
        session.add(connection)
        session.commit()
        session.refresh(connection)
        settings, mes = self.get_or_create_guardian_settings(session, guardian=guardian)
        if settings and settings.reports_enabled:
            create_report(session=session, 
                        guardian=guardian, 
                        content=f"{user.username} ({user.number_id}) fell into the guardians control!")
        return connection, "success"
    
    def remove_connection(self, session:Session, guardian:Guardian, user:User)->tuple[bool, str]:
        if not guardian or not user:
            return False, "Guardian and user are required"
        
        connection = session.exec(
            select(GuardianConnection).where(
                GuardianConnection.guardian_id == guardian.id,
                GuardianConnection.user_id == user.id
            )
        ).first()
        
        if not connection:
            return False, f"No connection exists between Guardian {guardian.id} and user {user.id}"
        
        session.delete(connection)
        session.commit()
        settings, mes = self.get_or_create_guardian_settings(session, guardian=guardian)
        if settings and settings.reports_enabled:
            create_report(session=session, 
                              guardian=guardian, 
                              content=f"The guardian has disowned {user.username} ({user.number_id}) as requested by the owner.")
        return True, "success"
    
    
    def change_code(self, session:Session, guardian:Guardian, code:int)->tuple[Guardian|None, str]:
        if not guardian:
            return None, "Guardian is required"

        guardian.code = code
        session.commit()

        return guardian, "success"
    
    def get_user_connection_if_any(self, session:Session, user:User)->tuple[None|GuardianConnection, str]:
        if not session or not user:
            return None, "User and session are required"
        
        statement = session.exec(
            select(GuardianConnection)
            .where(GuardianConnection.user_id==user.id)).first()

        msg = "The user doesn't have a connection: 404" if not statement else "success" 
        # 404 for quick check in tsx files: if (text.includes("404"))
        
        return statement, msg
    
    def get_or_create_guardian_restrictions(self, session:Session, guardian:Guardian):
        if not guardian:
            return None, "Guardian is requried"
        
        
        restrictions = session.exec(
                    select(GuardianRestrictions)
                    .where(GuardianRestrictions.guardian_id==guardian.id)).first()
        if not restrictions:
            restrictions = GuardianRestrictions(guardian=guardian)
            session.add(restrictions)
            session.commit()
            session.refresh(restrictions)
        return restrictions, "success"
        
    def get_or_create_guardian_settings(self, session:Session, guardian:Guardian)->tuple[GuardianSettings|None, str]:
        if not guardian:
            return None, "Guardian is required"
        
        settings = session.exec(
            select(GuardianSettings).where(GuardianSettings.guardian_id == guardian.id)
        ).first()
        
        if not settings:
            settings = GuardianSettings(guardian=guardian)
            session.add(settings)
            session.commit()
            session.refresh(settings)
        
        return settings, "success"
    
    def remove_from_guardian_restrictions(self, 
                                          session:Session, 
                                          guardian_id:str, 
                                          restriction: str)->tuple[list[str]|None,str]:
            guardian = self.get_guardian_by_id(session, guardian_id=guardian_id)
            if not guardian:
                return None, f"Guardian does not exist under the id {guardian_id}"
            
            restrictions, mes = self.get_or_create_guardian_restrictions(session, guardian=guardian)
            
            if restriction not in restrictions.restrictions:
                return None, f"{restriction} is not inside current restrictions"
         
            restrictions.restrictions.remove(restriction)
            session.commit()
            return restrictions.restrictions, f"Successfully removed '{restriction}' from guardian restrictions"
        
    def add_to_guardian_restrictions(self, session:Session, guardian_id:str, restriction: str)->tuple[list[str]|None,str]:
        guardian = self.get_guardian_by_id(session, guardian_id=guardian_id)
        if not guardian:
            return None, f"Guardian does not exist under the id {guardian_id}"
        
        restrictions, mes = self.get_or_create_guardian_restrictions(session, guardian=guardian)
        if restriction in restrictions.restrictions:
            return None, f"{restriction} is already inside current restrictions"
        
        if len(restrictions.restrictions) >= 25:
            return None, f"Restrictions reached maxed amount of restrictions: size = {len(restrictions.restrictions)}"
        
        if restriction in default_restrictions_on_creation():
            return None, f"{restriction} is already configured into the system, you are all set."
        
        restrictions.restrictions.append(restriction)
        session.commit()
        return restrictions.restrictions, f"Successfully added '{restriction}' to guardian restrictions"
    
    
    def update_guardian_settings(self, 
                                session:Session, 
                                guardian:Guardian, 
                                warning_message:str|None=None,
                                applause_message:str|None=None,
                                strictness:str|None=None, 
                                language:str|None=None,
                                enable_reports:bool|None=None,
                                apply_penalty:bool|None=None,
                                amount_of_points_to_lose:int|None=None):
        if not guardian:
            return None, "Guardian is required"
        
        settings, mes = self.get_or_create_guardian_settings(session=session, guardian=guardian)
        if not settings:
            return None, mes
        
        if warning_message is not None or applause_message is not None:
            valid, mes = self._validate_applause_and_warning_message(warning_message=warning_message,applause=applause_message)
            if not valid:
                return None, mes
            
            messages_dict = dict(settings.custom_warning_messages)
            if warning_message is not None:
                messages_dict['warning'] = warning_message
            if applause_message is not None:
                messages_dict['applause'] = applause_message
                
            settings.custom_warning_messages = messages_dict
            
        if strictness:
            settings.strictness = strictness
        if language:
            settings.language = language
        if apply_penalty is not None:
            settings.points_loss_enabled = apply_penalty
        if amount_of_points_to_lose is not None:
            settings.base_points_lost = amount_of_points_to_lose
        if enable_reports is not None:
            settings.reports_enabled = enable_reports
        
        session.add(settings)
        session.commit()
        session.refresh(settings)
        return settings, "success"
    
    def get_report(self, session:Session, report_id:str)->tuple[GuardianReport|None, str]:
        if not session or not report_id:
            return None, "session and report id are required"
        report = session.get(GuardianReport, report_id)
        if not report:
            return None, f"Report of id '{report_id}' does not exist"
        return report, "success"
    
    def delete_report_by_id(self, session:Session, user_making_request_id:str, report_id:str):
        success, mes = delete_report(session, user_id=user_making_request_id, report_id=report_id)
        return success, mes
    
    def get_reports_by_guardian_id(self, session:Session, guardian_id:str)->tuple[list[dict[str,Any]]|None, str]:
        if not guardian_id:
            return None, "Guardian id is required"
        
        guardian = self.get_guardian_by_id(session, guardian_id=guardian_id)
        if not guardian:
            return None, f"Guadian of id {guardian_id} does not exist"
        
        reports = session.exec(
            select(GuardianReport)
            .where(GuardianReport.guardian_id==guardian.id)).all()
        result = []
        for report in reports:
            result.append(
                report.model_dump()
            )
        return result, ""
    
    def get_reports_by_owner_id(self, session:Session, owner_id:str)->tuple[list[dict[str,Any]]|None, str]:
            if not owner_id:
                return None, "User id is required"
            
            owner = session.get(User, owner_id)
            if not owner:
                return None, f"User of id {owner_id} does not exist"
            
            reports = session.exec(
                select(GuardianReport)
                .where(GuardianReport.send_to_id==owner.id)).all()
            result = []
            for report in reports:
                result.append(
                    report.model_dump()
                )
            return result, ""
    
    def _validate_applause_and_warning_message(self, 
                                               warning_message:str|None=None, 
                                               applause:str|None=None)->tuple[bool, str]:
        
        if not warning_message and not applause:
            return False, "Warning message or appluase are required"
        
        if warning_message is not None and not 12 <= len(warning_message) <= 120:
            return False, f"The warning message of length {len(warning_message)} falls outside the valid range. length requirement is between 12-120"
        
        if applause is not None and not 12 <= len(applause) <= 120:
            return False,  f"The appluase message of length {len(applause)} falls outside the valid range. length requirement is between 12-120"
        
        # TODO: AI AGENT detects if the messages are civil and make sense
        return True, "Messages are valid"
        
        
        
        