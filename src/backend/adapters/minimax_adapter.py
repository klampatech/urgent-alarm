#!/usr/bin/env python3
"""
MiniMax Language Model Adapter

Implements ILanguageModelAdapter using MiniMax API for natural language parsing.
"""

import os
import json
from typing import Optional

from .llm_adapter import ILanguageModelAdapter, ParsedReminder, LLMParseError


class MiniMaxAdapter(ILanguageModelAdapter):
    """
    Adapter for MiniMax API.

    Environment variables:
    - MINIMAX_API_KEY: API key for MiniMax service
    - MINIMAX_BASE_URL: Base URL for API (default: https://api.minimax.chat/v1)
    - MINIMAX_MODEL: Model name (default: abab6.5s-chat)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.api_key = api_key or os.environ.get('MINIMAX_API_KEY')
        self.base_url = base_url or os.environ.get('MINIMAX_BASE_URL', 'https://api.minimax.chat/v1')
        self.model = model or os.environ.get('MINIMAX_MODEL', 'abab6.5s-chat')

    def is_available(self) -> bool:
        """Check if MiniMax API is configured."""
        return bool(self.api_key)

    def parse_reminder(self, input_text: str) -> ParsedReminder:
        """
        Parse reminder using MiniMax LLM.

        Sends the input to MiniMax with a parsing prompt and extracts
        structured reminder data from the response.
        """
        if not self.is_available():
            raise LLMParseError("MiniMax API key not configured")

        # Build prompt for parsing
        prompt = self._build_parse_prompt(input_text)

        try:
            response = self._call_api(prompt)
            parsed = self._extract_parsed_data(response, input_text)
            return parsed
        except Exception as e:
            raise LLMParseError(f"MiniMax parsing failed: {e}")

    def _build_parse_prompt(self, input_text: str) -> str:
        """Build the prompt for extracting reminder fields."""
        return f"""Extract the following fields from this reminder input:

Input: "{input_text}"

Extract:
- destination: Where the user needs to go
- arrival_time: When they need to arrive (in ISO format or natural like "9am", "2:30pm")
- drive_duration: How many minutes of driving (if mentioned)
- reminder_type: "countdown_event" if there's a destination/time, "simple_countdown" if just a timer

Respond with JSON:
{{"destination": "...", "arrival_time": "...", "drive_duration": N, "reminder_type": "..."}}"""

    def _call_api(self, prompt: str) -> str:
        """Make API call to MiniMax."""
        import requests

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }

        payload = {
            'model': self.model,
            'messages': [
                {'role': 'user', 'content': prompt}
            ],
            'temperature': 0.3,
        }

        response = requests.post(
            f'{self.base_url}/text/chatcompletion_v2',
            headers=headers,
            json=payload,
            timeout=10
        )

        if response.status_code != 200:
            raise Exception(f"API error: {response.status_code} {response.text}")

        data = response.json()
        return data['choices'][0]['message']['content']

    def _extract_parsed_data(self, response: str, raw_input: str) -> ParsedReminder:
        """Extract parsed data from LLM response."""
        import re

        # Try to extract JSON from response
        json_match = re.search(r'\{[^{}]*\}', response)
        if not json_match:
            raise LLMParseError("No valid JSON in response")

        data = json.loads(json_match.group())

        # Calculate confidence based on how many fields were found
        confidence = 0.0
        if data.get('destination'):
            confidence += 0.3
        if data.get('arrival_time'):
            confidence += 0.3
        if data.get('drive_duration'):
            confidence += 0.3
        confidence = min(confidence, 1.0)

        return ParsedReminder(
            destination=data.get('destination', raw_input),
            arrival_time=data.get('arrival_time'),
            drive_duration=data.get('drive_duration'),
            reminder_type=data.get('reminder_type', 'countdown_event'),
            confidence=confidence,
            raw_input=raw_input,
        )