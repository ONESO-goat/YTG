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