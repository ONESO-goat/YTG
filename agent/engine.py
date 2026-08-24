import ollama
from helpers.config import Config
from helpers.prompt import Prompts
import json
import base64
import json
from google.genai import types

from typing import Any
import base64
from google import genai
            
class Engine:
    def __init__(self, api_key:str|None=Config().gemini_api_key, ai_to_use:str="ollama") -> None:
        if ai_to_use not in ['gemini', 'ollama']:
            raise ValueError(f"'{ai_to_use}' is not a valid AI")
        
        self.ollama_model = Config.ollama_qwen_2_dot_5
        self.description_reader_ollama_model = Config.ollama_vision_model
        self.backend = ai_to_use
        self.ollama_client = ollama.Client(host='http://127.0.0.1:11434')

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
                self.ollama_client.show(self.ollama_model)
                print(f"✓ Using Ollama ({self.ollama_model})")
            except Exception as ex:
                print(f"⚠ Ollama model '{self.ollama_model}' not found: {type(ex).__name__}: {ex}")
         
    

    def _is_the_same_image(self,
                        new_image_bytes: bytes, 
                        previous_images: list[bytes],
                        system_prompt: str|None = None, 
                        return_json: bool = False
                       ) -> bool:
    
        if not previous_images or not new_image_bytes:
            return False
            
        if system_prompt is None:
            system_prompt = Prompts().is_the_same_image()
            
        previous_image = previous_images[-1]
        
        if self.backend == 'gemini':
            try:
                user_content = types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text="Here is the NEW image to evaluate:"),
                        types.Part.from_bytes(data=new_image_bytes, mime_type="image/png"),
                        types.Part.from_text(text="Here is the PREVIOUS image for comparison:"),
                        types.Part.from_bytes(data=previous_image, mime_type="image/png")
                    ]
                )
                        
                response = self.client.models.generate_content(
                    model=self.llm, 
                    contents=[user_content], 
                    config=types.GenerateContentConfig( 
                        system_instruction=system_prompt,
                        response_mime_type="application/json" if return_json else None
                    )
                )
                        
                content = response.text or ""
                
                if return_json:
                    parsed = json.loads(content or '{}')
                    return parsed # or handle json return as needed
                    
                return "true" in content.lower().strip()
                
            except Exception as e:
                print(f"[engine.classify_image gemini] ⚠️ Gemini error: {e}")
                return False
                
        else:  # Ollama
            try:
                encoded_new = base64.b64encode(new_image_bytes).decode('utf-8')
                encoded_prev = base64.b64encode(previous_image).decode('utf-8')
                    
                messages = [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user", 
                        "content": "Please compare these two images. The first is the NEW image, the second is the PREVIOUS image.",
                        "images": [encoded_new, encoded_prev]
                    }
                ]
                        
                response = self.ollama_client.chat(
                    model=self.ollama_model,
                    messages=messages,
                    format="json" if return_json else None,
                    options={'temperature': 0.2, "num_ctx": 8192},
                    
                )
                        
                content = response['message']['content'] or ""
                
                if return_json:
                    return json.loads(content or '{}')
                    
                return "true" in content.lower().strip()
                            
            except Exception as e:
                print(f"⚠️ [engine.classify_image] Ollama error: {e}")
                return False
            
    def _classify_image(self, 
                        image_bytes: bytes, 
                        restrictions: list[str], 
                        return_json: bool = True) -> Any:
        """
        Classifies an image using the specified system prompt.
        """
        if not image_bytes:
            return None
        
        system_prompt = Prompts.image_classification_prompt(restrictions=restrictions)
        
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
                encoded_image = base64.b64encode(image_bytes).decode('utf-8')
            
                m = [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user", 
                        "content": "Please analyze this image.",
                        "images": [encoded_image]
                    }
                ]
                
                response = self.ollama_client.chat(
                    model=self.ollama_model,
                    messages=m,
                    format="json" if return_json else None,
                    options={'temperature': 0.2, "num_ctx": 8192}
                )
                
                content = response['message']['content']
                if return_json:
                    content = json.loads(response['message']['content'] or '[]')
                return content
                    
            except Exception as e:
                print(f"⚠️ [engine.classify_image] Ollama error: {e}")
                return '[]'

    def _generate(self, 
                 text:str, 
                 system_prompt:str, 
                 return_json:bool=False,
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

                response = self.ollama_client.chat(
                    model=self.ollama_model,
                    messages=m,
                    format="json" if return_json else None,
                    options={'temperature': 0.2, "num_ctx": 8192}
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
        
            