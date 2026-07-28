import ollama
from helpers.config import Config
from helpers.prompt import Prompts
import json
from typing import Any
from google import genai
            
class Engine:
    def __init__(self, api_key:str|None=Config().gemini_api_key, ai_to_use:str="gemini") -> None:
        if ai_to_use not in ['gemini', 'ollama']:
            raise ValueError(f"'{ai_to_use}' is not a valid AI")
        
        self.ollama_model = 'qwen3:0.6b'
        self.backend = ai_to_use
        if self.backend == 'gemini' and api_key:
            # Use Gemini
            
            
            self.client = genai.Client(api_key=api_key)
            self.llm = Config.gemini_model
            
            print(f"✓ Gemini Backend Initialized: {self.client}")
            
        else:
            # Use Ollama

            self.backend = 'ollama'
            
            # Check if Ollama is available
            try:
                ollama.show(self.ollama_model)
                print(f"✓ Using Ollama ({self.ollama_model})")
                
            except:
                print(f"⚠ Ollama model '{self.ollama_model}' not found")
                print("  Run: ollama pull qwen3:0.6b")
    
    
    def _classify_image(self, 
                        image_bytes: bytes, 
                        system_prompt: str=Prompts().image_classification_prompt(), 
                        return_json: bool = False) -> Any:
        """
        Classifies an image using the specified system prompt.
        """
        if not image_bytes or not system_prompt:
            return None
        
        if self.backend == 'gemini':
            try:
                from google.genai import types
                
                user_content = types.Content(
                    role="user",
                    parts=[types.Part.from_bytes(data=image_bytes, mime_type="image/png")]
                )
                
                response = self.client.models.generate_content(
                    model=self.llm, 
                    contents=[user_content], 
                    config=types.GenerateContentConfig( 
                        system_instruction=system_prompt,
                        response_mime_type="application/json" if return_json else None
                    )
                )
                
                content = response.text 
                if return_json:
                    content = json.loads(response.text or '[]')
                return content
            except Exception as e:
                print(f"[engine.classify_image gemini] ⚠️ Gemini error: {e}")
                return '[]'
        
        else:  # Ollama
            try:
                m = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"<<<IMAGE>>>\n{image_bytes}\n<<<IMAGE>>>"}
                ]
                
                response = ollama.chat(
                    model=self.ollama_model,
                    messages=m,
                    format="json" if return_json else None,
                    options={'temperature': 0.2}
                )
                
                content = response['message']['content']
                if return_json:
                    content = json.loads(response['message']['content'])
                return content
                
            except Exception as e:
                print(f"⚠️ [engine.classify_image] Ollama error: {e}")
                return '[]'

    def _generate(self, 
                 text:str, 
                 system_prompt:str, 
                 return_json:bool=False, 
                 image_bytes:bytes|None=None,
                 _use_ollama:bool=False,
                 _ignore_text:bool=False,
                 )->Any:
        """
        For this project, text will be an image of the users screen.
        Text is the description of the image, and system_prompt is the prompt to classify the image.
        """
        if not text and not _ignore_text or not system_prompt:
            return 
        m = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"<<<DATA>>>\n{text}\n<<<DATA>>>" if text else ""}
        ]
        
        
        err = {
            "content": text,
            "logic": "",
            "error": True
        } if return_json else ""
        if self.backend == 'gemini' and not _use_ollama:
            try:
                from google.genai import types
                
                # For Gemini, we convert the messages to their content format
                # Note: Gemini 2.0+ handles system_instruction separately
                
                parts = [types.Part.from_text(text=f"<<<TEXT>>>\n{text}\n<<<TEXT>>>")] if text else []

                if image_bytes:
                    parts.append(
                        types.Part.from_bytes(
                            data=image_bytes,
                            mime_type="image/png"  # or "image/jpeg"
                        )
                    )
                    
                user_content = types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=f"<<<TEXT>>>\n{text}\n<<<TEXT>>>")]
                )
                
                response = self.client.models.generate_content(
                    model=self.llm, 
                    contents=[user_content], 
                    config=types.GenerateContentConfig( 
                        system_instruction=system_prompt,
                        response_mime_type="application/json" if return_json else None
                    )
                )
                
                content = response.text 
                if return_json:
                    content = json.loads(response.text or '[]')
                return content
            except Exception as e:
                print(f"[engine.generate gemini] ⚠️ Gemini error: {e}")
                if "429" in str(e):
                    print(" ⚠️⚠️⚠️ RAN OUT OF GEMINI TOKENS")
                    self.backend = "ollama"
                    return err
                
                if "503" in str(e):
                    print("⚠️ Gemini service unavailable, switching to ollama, please hold...")
                    # self.backend = 'ollama'
                    # return self._generate(text=text, 
                    #                      system_prompt=system_prompt, 
                    #                      return_json=return_json, 
                    #                      _use_ollama=True)  # Retry with Ollama
                    return err
                return '[]'
        
        else:  # Ollama
            try:

                response = ollama.chat(
                    model=self.ollama_model,
                    messages=m,
                    format="json" if return_json else None,
                    options={'temperature': 0.2}
                )
                content = response['message']['content']
                if return_json:
                    content = json.loads(response['message']['content'])
                return content
                
            except Exception as e:
                print(f"⚠️ [engine.generate] Ollama error: {e}")
                
                return '[]'
            
    
    def _parse_json(self, text: str, default: Any = None) -> Any:
        """Robust JSON parsing."""
        if not text or text.strip() == '':
            return default if default is not None else []
        
        text = text.strip()
        
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        
        # Try to parse
        try:
            parsed = json.loads(text)
            return parsed
        except json.JSONDecodeError as e:
            print(f"⚠ JSON parse error: {e}")
            print(f"  Raw text: {text[:200]}...")
            return default if default is not None else []
        
            