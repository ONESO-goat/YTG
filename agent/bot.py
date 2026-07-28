from .engine import Engine
from helpers.prompt import Prompts
from datetime import datetime
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from models.models import Guardian, GuardianSettings

class ScreenClassifier:
    def __init__(self) -> None:
        
        self.engine = Engine()
        self.prompts = Prompts()

    
    def overview(self, 
                 image_overview:str, 
                 guardian_settings:'GuardianSettings|None', 
                 guardian_restrictions:list[str])->dict[str, Any]:
        
        
        overview = self.engine._generate(
            text=image_overview,
            system_prompt=self.prompts.agent_purpose(
                restricted_categories=guardian_restrictions if guardian_restrictions else self.default_restrictions,
                strictness=guardian_settings.strictness if guardian_settings else "harsh"
            ),
            return_json=True
        )
        """
        returns {{
  "flagged": boolean,
  "category": string | null,
  "confidence": number,
  "description": string,
  "source_context": string | null
}}"""   

        if not overview:
            return {
            "flagged": False,
            "category": None,
            "confidence": 0.0,
            "description": "No content matching configured restrictions.",
            "source_context": None
        }
            
        if overview['flagged']:
            overview['send_warning'] = True
        else: 
            overview['send_warning'] = False
        return overview
    
    
    def _breakdown_overview(self, user, classification_result: dict, include_name:bool=False):
        img_summary = classification_result.get('image_summary', {})
        confidence = (
            classification_result.get('confidence', 0.0) * 0.5
            + img_summary.get('confidence', 0.0) * 0.5
        )
        formatted_time = datetime.now().strftime("%m-%d-%y %I:%M %P")
        if include_name:
            dependent = f"Dependent: ** {user.name} **"
        else:
            dependent = ""
            
        return f"""
{dependent}                
Timestamp: {formatted_time}

Category validated: ** {classification_result.get('category')} **

description: {classification_result.get('description')}
confidence: {confidence}

info:
    summary: {img_summary.get('summary')}
    visible text summarized: {img_summary.get('visible_text')}
    detailed description: {img_summary.get('detailed_description')}
""".strip()

    @property
    def default_restrictions(self)->list[str]:
        return [
            "hate",
            "hate speech",
            "death",
            "gore",
            "graphic content",
            "porn",
            "spam",
            "racism",
            "sexism",
            "potential scam",
            "looksmax"
        ]