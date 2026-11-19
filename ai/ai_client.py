"""
AI Client module with configurable LLM providers (Gemini, local fallback).
Validates and parses structured JSON responses.
"""

from typing import Dict, Any, Optional
import os
import json
import re
from config.settings import GEMINI_API_KEY, GEMINI_MODEL, AI_PROVIDER


class AIClient:
    """Configurable client for AI interactions with structured JSON parsing."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", GEMINI_API_KEY)
        self.model = model or os.getenv("GEMINI_MODEL", GEMINI_MODEL)
        self.provider = os.getenv("AI_PROVIDER", AI_PROVIDER).lower()

    @staticmethod
    def extract_json(raw_text: str) -> Dict[str, Any]:
        """Extract and parse JSON safely from LLM output."""
        cleaned = raw_text.strip()
        # Remove markdown code blocks if present
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        # Find first { and last }
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1:
            cleaned = cleaned[start : end + 1]

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse AI JSON response: {str(e)}\nRaw output: {raw_text[:200]}")

    def generate_json_response(self, prompt: str) -> Dict[str, Any]:
        """Generate response via configured provider, or raise if unavailable."""
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            raise ValueError("No valid GEMINI_API_KEY configured.")

        from google import genai
        client = genai.Client(api_key=self.api_key)
        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "temperature": 0.2,
            },
        )
        return self.extract_json(response.text)
