from models.models import GuardianReport, User
from sqlmodel import Session


def create_report(session:Session, guardian, content:str=""):
    if not guardian or not content:
        return None, "Guardian and content are required for reports"
    
    gr = GuardianReport(
        content=content,
        guardian_id=guardian.id,
        send_to=guardian.owner
    )
    session.add(gr)
    session.commit()
    return gr, f"New report: {content}"


def delete_report(session:Session, user_id: str, report_id:str)->tuple[bool, str]:
    """Delete reports to avoid cluter in alerts"""
    if not session or report_id:
        return False, "Guardian and content are required for reports"
    
    report = session.get(GuardianReport, report_id)
    if not report:
        return False, f"This report with id '{report_id}' doesnt exist"
    
    if report.send_to_id != user_id:
        return False, f"Only the owner can remove reports"
    
    session.delete(report)
    session.commit()
    return True, f"Report now gone"