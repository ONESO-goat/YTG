from .engine import Engine
from helpers.prompt import Prompts
from datetime import datetime
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from models.models import GuardianSettings

class ScreenClassifier:
    def __init__(self, ai_to_use:str) -> None:
        
        self.engine = Engine(ai_to_use=ai_to_use)
        self.prompts = Prompts()

    def is_the_same_screen(self, recent_screen_shots: list[str|bytes]) -> bool:
        """Avoid users staying on the same screen,
          or finding some gimmick to trick the system like switching tabs constantly"""
        l = len(recent_screen_shots)
        confidence:float = 0.0
        # convert bytes back to image here
 
        if l < 2:
            return False
        
        if recent_screen_shots[0] - recent_screen_shots[1] < 5:
            return True
        # check wheater the last image  and the new image are the same right away.
        # Save speed. Issue could be if the user went back to the image 

        # list size will be 6 (6 bytes) max. 
        left, right = 0, l - 1
        while left < right:
            first_last_similarity_distance = recent_screen_shots[left] - recent_screen_shots[right] 
            if left+1 < l and right-1 > left+1:

                if recent_screen_shots[left+1] - recent_screen_shots[right] < 5:
                    confidence += 1.0
                if recent_screen_shots[left+1] - recent_screen_shots[left] < 5:
                    confidence += 1.0
                if recent_screen_shots[right-1] - recent_screen_shots[left] < 5:
                    confidence += 1.0

            if first_last_similarity_distance < 5:
                confidence += 1.0
            left+=1
            right-=1

        return confidence > 3.0

            

            
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