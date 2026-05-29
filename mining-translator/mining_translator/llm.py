"""LLM backend abstraction supporting Claude and OpenAI-compatible APIs."""

import json
import logging
from . import config

logger = logging.getLogger(__name__)


class TranslationError(Exception):
    """Raised when LLM API call fails."""
    pass


def translate_text(
    source_text: str,
    target_lang: str,
    system_prompt: str,
    user_prompt: str,
    backend: str = None,
) -> str:
    """Call LLM to translate and extract terms. Returns raw response text."""
    backend = backend or config.DEFAULT_BACKEND

    if backend == "claude":
        return _call_claude(system_prompt, user_prompt)
    else:
        return _call_openai(system_prompt, user_prompt, backend)


def _call_claude(system_prompt: str, user_prompt: str) -> str:
    if not config.ANTHROPIC_API_KEY:
        raise TranslationError(
            "ANTHROPIC_API_KEY not set. Set the environment variable or configure in config.py."
        )

    try:
        from anthropic import Anthropic
    except ImportError:
        raise TranslationError("anthropic package not installed. Run: pip install anthropic")

    client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=config.MAX_TOKENS,
        temperature=config.TRANSLATION_TEMPERATURE,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    content = response.content
    if isinstance(content, list):
        return content[0].text
    return content


def _call_openai(system_prompt: str, user_prompt: str, backend: str) -> str:
    api_key = config.OPENAI_API_KEY
    if not api_key:
        raise TranslationError(
            "OPENAI_API_KEY not set. Set the environment variable or configure in config.py."
        )

    try:
        from openai import OpenAI
    except ImportError:
        raise TranslationError("openai package not installed. Run: pip install openai")

    client = OpenAI(api_key=api_key, base_url=config.OPENAI_BASE_URL)
    response = client.chat.completions.create(
        model=config.OPENAI_MODEL,
        max_tokens=config.MAX_TOKENS,
        temperature=config.TRANSLATION_TEMPERATURE,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    return response.choices[0].message.content
