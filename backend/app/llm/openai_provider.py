from __future__ import annotations

from dataclasses import dataclass, field

from ..core.config import Settings
from .prompts import SYSTEM_PROMPT


@dataclass(frozen=True)
class ProviderAnswer:
    text: str
    token_usage: dict[str, int] = field(default_factory=dict)


class OpenAIAnswerProvider:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate(self, prompt: str) -> ProviderAnswer:
        from openai import OpenAI

        client = OpenAI(api_key=self.settings.openai_api_key, max_retries=self.settings.openai_max_retries)
        response = client.chat.completions.create(
            model=self.settings.openai_model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=self.settings.openai_max_output_tokens,
            timeout=self.settings.openai_timeout_seconds,
        )
        usage = response.usage
        return ProviderAnswer(
            text=response.choices[0].message.content or "",
            token_usage={
                "prompt_tokens": getattr(usage, "prompt_tokens", 0) if usage else 0,
                "completion_tokens": getattr(usage, "completion_tokens", 0) if usage else 0,
                "total_tokens": getattr(usage, "total_tokens", 0) if usage else 0,
            },
        )
