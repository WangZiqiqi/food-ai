"""
LLM translated note - translated note
"""

import os
import json
import requests
from typing import List, Dict, Optional, Any
from dotenv import load_dotenv

# translated note
load_dotenv()


class LLMClient:
    """LLM translated note - translated note Poe API"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 120,
        max_retries: int = 3
    ):
        """
        translated note LLM translated note
        
        Args:
            api_key: API Key,translated note None translated note
            api_url: API URL,translated note None translated note
            model: translated note,translated note None translated note
            timeout: translated note(translated note)
            max_retries: translated note
        """
        self.api_key = api_key or os.getenv("POE_API_KEY")
        self.api_url = api_url or os.getenv("POE_API_URL", "https://api.poe.com/v1/chat/completions")
        self.model = model or os.getenv("POE_MODEL", "minimax-m2.7")
        self.timeout = timeout
        self.max_retries = max_retries
        
        if not self.api_key:
            raise ValueError("API Key translated note,translated note .env translated note POE_API_KEY")
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        translated note(translated note)
        
        Args:
            messages: translated note,translated note [{"role": "user", "content": "..."}]
            temperature: translated note
            max_tokens: translated note token translated note
            **kwargs: translated note
            
        Returns:
            API translated note
        """
        import time
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            **kwargs
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout
                )
                response.raise_for_status()
                return response.json()
            except requests.exceptions.Timeout as e:
                last_error = e
                print(f"    Warning: API translated note (translated note {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # translated note
            except requests.exceptions.RequestException as e:
                last_error = e
                print(f"    Warning: API translated note (translated note {attempt + 1}/{self.max_retries}): {str(e)[:50]}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
        
        raise Exception(f"LLM API translated note (translated note{self.max_retries}translated note): {str(last_error)}")
    
    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        translated note
        
        Args:
            prompt: translated note
            system_prompt: translated note
            temperature: translated note
            max_tokens: translated note token translated note
            
        Returns:
            translated note
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = self.chat(messages, temperature, max_tokens, **kwargs)
        
        # translated note
        try:
            return response["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise Exception(f"translated note LLM translated note: {str(e)}, translated note: {response}")
    
    def extract_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        **kwargs
    ) -> Dict[str, Any]:
        """
        translated note JSON translated note
        
        Args:
            prompt: translated note
            system_prompt: translated note
            temperature: translated note
            
        Returns:
            translated note JSON translated note
        """
        content = self.complete(prompt, system_prompt, temperature, **kwargs)
        return self._parse_json_with_repair(
            content,
            system_prompt=system_prompt,
            temperature=temperature,
            **kwargs,
        )

    def _parse_json_with_repair(
        self,
        content: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        **kwargs
    ) -> Dict[str, Any]:
        """Parse JSON content and optionally ask the model to repair invalid JSON."""

        # translated note JSON
        try:
            # translated note
            return json.loads(content)
        except json.JSONDecodeError:
            # translated note markdown translated note
            import re
            
            # translated note ```json ... ``` translated note ``` ... ```
            patterns = [
                r'```json\s*(.*?)\s*```',
                r'```\s*(.*?)\s*```',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, content, re.DOTALL)
                if match:
                    try:
                        return json.loads(match.group(1))
                    except json.JSONDecodeError:
                        continue
            
            # translated note {...} translated note [...]
            patterns = [
                r'(\{[\s\S]*\})',
                r'(\[[\s\S]*\])',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, content)
                if match:
                    try:
                        return json.loads(match.group(1))
                    except json.JSONDecodeError:
                        continue

            repaired = self._repair_json_response(content, system_prompt, temperature, **kwargs)
            if repaired is not None:
                return repaired

            raise Exception(f"translated note JSON translated note: {content[:200]}...")

    def _repair_json_response(
        self,
        content: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Ask the model to rewrite a malformed response as strict JSON."""
        repair_prompt = (
            "Convert the following response into valid JSON only. "
            "Do not add explanation, markdown, or surrounding text. "
            "Preserve the original structure and values as much as possible.\n\n"
            "Response to convert:\n"
            f"{content}"
        )
        repaired = self.complete(
            repair_prompt,
            system_prompt=system_prompt or "You repair malformed model output into strict JSON.",
            temperature=0,
            max_tokens=4000,
            **kwargs,
        )
        try:
            return self._parse_json_with_repair(repaired, None, temperature, **kwargs)
        except Exception:
            return None


# translated note
_default_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """translated note LLM translated note"""
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client


def reset_llm_client():
    """translated note"""
    global _default_client
    _default_client = None
